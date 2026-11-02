import base64
import json
import logging
import queue
import threading

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import site_cache
from .config import (
    DEFAULT_FILL_GAPS, DEFAULT_RADIUS,
    LOW_COVERAGE_THRESHOLD, MAX_RADIUS_M, STATIC_DIR, ZEELAND_BOUNDS,
)
from .dive_sites import SITE_KEYS, SITES
from .i18n import DEFAULT_LANG, LANG_NAMES, LANGS, TR, normalize_lang
from .terrain import (
    PipelineError, crop_grid, generate_terrain, load_elevation_grid, render_terrain,
)

log = logging.getLogger(__name__)


NDJSON = "application/x-ndjson"

app = FastAPI(title="Bathymetry Explorer")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class GenerateRequest(BaseModel):
    lat: float
    lon: float
    radius: float = DEFAULT_RADIUS
    fill_gaps: bool = DEFAULT_FILL_GAPS


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "app.html").read_text()


@app.get("/api/config")
def api_config():
    return {
        "bounds": ZEELAND_BOUNDS,
        "sites": SITES,
        "lowCoverageThreshold": LOW_COVERAGE_THRESHOLD,
        "langs": LANGS,
        "defaultLang": DEFAULT_LANG,
        "langNames": LANG_NAMES,
    }


@app.get("/api/strings")
def api_strings(lang: str = DEFAULT_LANG):
    return TR[normalize_lang(lang)]


def _ndjson_line(obj) -> str:
    return json.dumps(obj) + "\n"


def _ndjson_error(message: str, status_code: int) -> StreamingResponse:
    """Single-event error stream, so the client parses validation errors
    the same way as mid-pipeline ones."""
    return StreamingResponse(
        iter([_ndjson_line({"type": "error", "message": message})]),
        media_type=NDJSON, status_code=status_code,
    )


def _validate(req: GenerateRequest) -> str | None:
    """Translated error message, or None if the request is valid."""
    b = ZEELAND_BOUNDS
    if not (b["south"] <= req.lat <= b["north"] and b["west"] <= req.lon <= b["east"]):
        return "This tool only covers Zeeland. Pick a location on the map."
    if req.radius <= 0:
        return "Radius must be greater than 0m."
    if req.radius > MAX_RADIUS_M:
        return f"Maximum radius is {MAX_RADIUS_M}m."
    return None


def _result_event(result: dict) -> dict:
    return {
        "type": "result",
        "png_base64": base64.b64encode(result["png_bytes"]).decode("ascii"),
        "scene3d": result["scene3d"],
        "stats": result["stats"],
    }


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    """Stream progress events and then the result as NDJSON.
    Serve from site_cache where possible, otherwise run pipeline
    """
    error = _validate(req)
    if error:
        return _ndjson_error(error, 400)

    is_known_site = site_cache.site_key(req.lat, req.lon) in SITE_KEYS
    is_default = site_cache.is_default_settings(req.radius, req.fill_gaps)

    if is_known_site and is_default:
        cached = site_cache.load(req.lat, req.lon)
        if cached is not None:
            events = [
                {"type": "progress", "stage": "cache_hit", "status": "active"},
                {"type": "result", **cached},
            ]
            return StreamingResponse(map(_ndjson_line, events), media_type=NDJSON)

    def run_pipeline(on_progress):
        if not is_known_site:
            return generate_terrain(
                lat=req.lat, lon=req.lon, radius=req.radius,
                fill_gaps=req.fill_gaps, on_progress=on_progress,
            )
        grid = site_cache.load_grid(req.lat, req.lon)
        if grid is None:
            # Fetch the full radius so later requests for this site can be served from cache
            grid = load_elevation_grid(
                lat=req.lat, lon=req.lon, radius=DEFAULT_RADIUS,
                on_progress=on_progress,
            )
            site_cache.save_grid(req.lat, req.lon, grid)
        if req.radius != DEFAULT_RADIUS:
            grid = crop_grid(grid, req.radius)
        return render_terrain(grid, fill_gaps=req.fill_gaps, on_progress=on_progress)

    def event_stream():
        events: queue.Queue = queue.Queue()
        outcome = {}

        def on_progress(stage, status, **extra):
            events.put({"type": "progress", "stage": stage, "status": status, **extra})

        def worker():
            try:
                outcome["result"] = run_pipeline(on_progress)
            except PipelineError as e:
                outcome["error"] = str(e)
            except Exception:
                log.exception("terrain generation failed")
                outcome["error"] = (
                    "Something went wrong while generating the map. "
                    "Try a different location or radius.")
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()

        while (event := events.get()) is not None:
            yield _ndjson_line(event)

        if "error" in outcome:
            yield _ndjson_line({"type": "error", "message": outcome["error"]})
            return

        result = outcome["result"]
        if is_default and is_known_site:
            site_cache.save(req.lat, req.lon, result)
        yield _ndjson_line(_result_event(result))

    return StreamingResponse(event_stream(), media_type=NDJSON)
