import numpy as np

from .errors import PipelineError
from .grid import classify_land_water, fill_gaps as fill_grid_gaps, load_elevation_grid
from .render2d import render_png
from .scene3d import build_scene, downsample


def render_terrain(grid, fill_gaps=True, on_progress=None):
    """Render a grid from load_elevation_grid()

    Returns {"png_bytes", "scene3d", "stats"}.
    Raises PipelineError if there is nothing to render.
    """
    def emit(stage, status, **extra):
        if on_progress:
            on_progress(stage, status, **extra)

    elevation = grid["elevation"]
    gap_mask, n_gap = grid["gap_mask"], grid["n_gap"]

    if n_gap == elevation.size:
        raise PipelineError(
            "No elevation data at this location. Try a larger radius, or pick a spot inside the surveyed area.")

    is_land = classify_land_water(grid["ahn_valid"], gap_mask)

    if n_gap > 0 and fill_gaps:
        emit("fill_gaps", "start")
        elevation = fill_grid_gaps(elevation)

    emit("render_2d", "start")
    vmin = np.nanpercentile(elevation, 1)
    vmax = np.nanpercentile(elevation, 99)
    png_bytes = render_png(elevation, is_land, gap_mask, grid["transform"], grid["bounds"], vmin, vmax)

    emit("render_3d", "start")
    elev_ds, is_land_ds, xs_ds, ys_ds = downsample(elevation, is_land, grid["transform"])
    if np.all(np.isnan(elev_ds)):
        raise PipelineError(
            "Too little elevation data here to build a 3D model. Try a larger radius or turn on gap filling.")

    x_center, y_center = grid["x_center"], grid["y_center"]

    return {
        "png_bytes": png_bytes,
        "scene3d": build_scene(elev_ds, is_land_ds, xs_ds, ys_ds, x_center, y_center),
        "stats": {
            "x_center": x_center,
            "y_center": y_center,
            "coverage": grid["coverage"],
            "gap_pct": 100 * n_gap / elevation.size,
            "source_files": grid["source_files"],
        },
    }


def generate_terrain(lat, lon, radius=300, fill_gaps=True, on_progress=None):
    """Fetch and render in one go."""
    grid = load_elevation_grid(lat, lon, radius, on_progress=on_progress)
    return render_terrain(grid, fill_gaps=fill_gaps, on_progress=on_progress)


def get_coverage_stats(lat, lon, radius=300):
    """Data coverage around (lat, lon) without rendering."""
    grid = load_elevation_grid(lat, lon, radius)
    gap_pct = 100 * grid["n_gap"] / grid["elevation"].size
    return {
        "coverage": grid["coverage"],
        "combined_pct": 100 - gap_pct,
        "gap_pct": gap_pct,
        "source_files": grid["source_files"],
    }
