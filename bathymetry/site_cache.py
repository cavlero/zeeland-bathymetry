import base64
import json

import numpy as np
from rasterio.transform import from_origin  # noqa: E402

from .config import CACHE_DIR, DEFAULT_FILL_GAPS, DEFAULT_RADIUS

_GRID_ARRAYS = ("elevation", "gap_mask", "vaargeul_valid", "ahn_valid")
_GRID_META = ("x_center", "y_center", "height", "width", "n_gap",
              "coverage", "source_files")


def site_key(lat: float, lon: float) -> tuple[float, float]:
    """Coordinates rounded to 6 decimals (~0.1 m), stable across JSON round trips."""
    return round(lat, 6), round(lon, 6)


def is_default_settings(radius, fill_gaps) -> bool:
    """Whether a request matches the render cache exactly."""
    return radius == DEFAULT_RADIUS and fill_gaps == DEFAULT_FILL_GAPS


def _stem(lat, lon) -> str:
    lat, lon = site_key(lat, lon)
    return f"{lat:.6f}_{lon:.6f}"


def _render_path(lat, lon):
    return CACHE_DIR / f"{_stem(lat, lon)}.json"


def _grid_npz_path(lat, lon):
    return CACHE_DIR / f"{_stem(lat, lon)}_grid.npz"


def _grid_meta_path(lat, lon):
    return CACHE_DIR / f"{_stem(lat, lon)}_grid_meta.json"


def load(lat, lon) -> dict | None:
    """Cached {"png_base64", "scene3d", "stats"}, or None."""
    path = _render_path(lat, lon)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save(lat, lon, result) -> dict:
    """Cache a render_terrain() result."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "png_base64": base64.b64encode(result["png_bytes"]).decode("ascii"),
        "scene3d": result["scene3d"],
        "stats": result["stats"],
    }
    _render_path(lat, lon).write_text(json.dumps(payload))
    return payload


def load_grid(lat, lon) -> dict | None:
    """Cached elevation grid or None."""
    npz_path, meta_path = _grid_npz_path(lat, lon), _grid_meta_path(lat, lon)
    if not (npz_path.is_file() and meta_path.is_file()):
        return None
    try:
        arrays = np.load(npz_path)
        meta = json.loads(meta_path.read_text())
        left, bottom, right, top = meta["bounds"]
        return {
            **{k: meta[k] for k in _GRID_META},
            **{k: arrays[k] for k in _GRID_ARRAYS},
            "bounds": (left, bottom, right, top),
            "transform": from_origin(left, top, meta["px"], meta["py"]),
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def save_grid(lat, lon, grid) -> None:
    """Cache a load_elevation_grid() result"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(_grid_npz_path(lat, lon), **{k: grid[k] for k in _GRID_ARRAYS})
    transform = grid["transform"]
    meta = {
        **{k: grid[k] for k in _GRID_META},
        "bounds": list(grid["bounds"]),
        "px": transform.a,
        "py": -transform.e,
    }
    _grid_meta_path(lat, lon).write_text(json.dumps(meta))
