import logging

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds
from scipy.ndimage import distance_transform_edt

from ..config import RD_CRS, WGS84_CRS
from . import sources
from .errors import PipelineError

log = logging.getLogger(__name__)

def _read_window_resampled(paths, dst_shape, dst_transform, bounds):
    """Read every tile in `paths` over `bounds` and resample onto
    the destination grid. Earlier tiles win where they overlap

    Returns (merged_array, used_paths), where used_paths refer to the tiles used
    """
    minx, miny, maxx, maxy = bounds
    out = np.full(dst_shape, np.nan, dtype=np.float32)
    used = []

    for path in paths:
        try:
            with rasterio.Env(**sources.GDAL_STREAMING_ENV), rasterio.open(path) as src:
                crs = src.crs
                if crs is not None and crs.to_string() != RD_CRS:
                    q_bounds = transform_bounds(RD_CRS, crs, minx, miny, maxx, maxy)
                else:
                    q_bounds = bounds
                window = from_bounds(*q_bounds, transform=src.transform)
                native = src.read(1, window=window).astype(np.float32)
                native_transform = src.window_transform(window)
                nodata = src.nodata
        except Exception as e:
            # skip instead of fail
            log.warning("skipping unreadable tile %s: %s", path, e)
            continue

        if nodata is not None:
            native[native == nodata] = np.nan
        # maximum valid elevation 1000 meters
        native[native > 1000] = np.nan

        if native.size == 0 or np.all(np.isnan(native)):
            continue

        tile_out = np.full(dst_shape, np.nan, dtype=np.float32)
        reproject(
            source=native,
            destination=tile_out,
            src_transform=native_transform,
            src_crs=crs,
            src_nodata=np.nan,
            dst_transform=dst_transform,
            dst_crs=RD_CRS,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        out = np.where(np.isnan(out), tile_out, out)
        used.append(path)

    return out, used


def _coverage_pct(valid: np.ndarray) -> float:
    return 100 * np.count_nonzero(valid) / valid.size


def load_elevation_grid(lat, lon, radius, on_progress=None):
    """Fetch the AHN/vaargeul tiles around (lat, lon) and merge them.

    on_progress(stage, status, **extra), if given, is called around each
    download so the caller can stream progress to the client.
    """
    def emit(stage, status, **extra):
        if on_progress:
            on_progress(stage, status, **extra)

    x_center, y_center = Transformer.from_crs(WGS84_CRS, RD_CRS, always_xy=True).transform(lon, lat)
    minx, maxx = x_center - radius, x_center + radius
    miny, maxy = y_center - radius, y_center + radius
    bounds = (minx, miny, maxx, maxy)

    vaargeul_paths = sources.vaargeul_paths()
    ahn_paths = sources.ahn_paths(minx, miny, maxx, maxy)

    # first vaargeul tile sets the grid resolution.
    with rasterio.Env(**sources.GDAL_STREAMING_ENV), rasterio.open(vaargeul_paths[0]) as src:
        px, py = src.res
    height = max(1, round((maxy - miny) / py))
    width = max(1, round((maxx - minx) / px))
    transform = from_origin(minx, maxy, px, py)
    shape = (height, width)

    emit("download_vaargeul", "start")
    bathy, vaargeul_used = _read_window_resampled(vaargeul_paths, shape, transform, bounds)
    emit("download_vaargeul", "done", files=[sources.display_path(p) for p in vaargeul_used])

    emit("download_ahn", "start")
    ahn, ahn_used = _read_window_resampled(ahn_paths, shape, transform, bounds)
    emit("download_ahn", "done", files=[sources.display_path(p) for p in ahn_used])

    emit("merge", "start")

    vaargeul_valid = ~np.isnan(bathy)
    ahn_valid = ~np.isnan(ahn)

    # AHN where it has data, vaargeul only below NAP
    elevation = np.where(ahn_valid, ahn, np.nan)
    elevation = np.where(~ahn_valid & vaargeul_valid & (bathy < 0), bathy, elevation)

    n_gap = int(np.isnan(elevation).sum())
    if n_gap == elevation.size:
        raise PipelineError(
            "No elevation data at this location. Try a larger radius, or pick a spot inside the surveyed area.")

    return {
        "x_center": x_center, "y_center": y_center,
        "bounds": bounds, "transform": transform, "height": height, "width": width,
        "elevation": elevation, "gap_mask": np.isnan(elevation), "n_gap": n_gap,
        "coverage": {
            "vaargeul": _coverage_pct(vaargeul_valid),
            "ahn": _coverage_pct(ahn_valid),
        },
        "vaargeul_valid": vaargeul_valid,
        "ahn_valid": ahn_valid,
        "source_files": {
            "vaargeul": [sources.display_path(p) for p in vaargeul_used],
            "ahn": [sources.display_path(p) for p in ahn_used],
        },
    }


def crop_grid(grid, new_radius):
    """Slice `grid` down to `new_radius` around its center, without
    re-fetching. new_radius must be <= the radius grid was built with."""
    transform = grid["transform"]
    px, py = transform.a, -transform.e

    col0, row0 = (round(v) for v in ~transform * (grid["x_center"] - new_radius, grid["y_center"] + new_radius))
    col1, row1 = (round(v) for v in ~transform * (grid["x_center"] + new_radius, grid["y_center"] - new_radius))
    row0, col0 = max(row0, 0), max(col0, 0)
    row1, col1 = min(row1, grid["height"]), min(col1, grid["width"])
    window = (slice(row0, row1), slice(col0, col1))

    elevation = grid["elevation"][window]

    # bounds of exact pixels so mesh coordinates line up with cropped array
    left, top = transform * (col0, row0)
    right, bottom = transform * (col1, row1)

    return {
        **grid,
        "bounds": (left, bottom, right, top),
        "transform": from_origin(left, top, px, py),
        "height": elevation.shape[0], "width": elevation.shape[1],
        "elevation": elevation, "gap_mask": grid["gap_mask"][window], "n_gap": int(grid["gap_mask"][window].sum()),
        "vaargeul_valid": grid["vaargeul_valid"][window], "ahn_valid": grid["ahn_valid"][window],
        "coverage": {
            "vaargeul": _coverage_pct(grid["vaargeul_valid"][window]),
            "ahn": _coverage_pct(grid["ahn_valid"][window]),
        },
    }


def _nearest_known_indices(missing: np.ndarray):
    _, (rows, cols) = distance_transform_edt(missing, return_distances=True, return_indices=True)
    return rows, cols


def fill_gaps(z: np.ndarray, iterations: int = 600) -> np.ndarray:
    """Fill NaN cells smoothly by seeding from nearest known cell, relaxing towards
    avg of 4 neighbours (Jacobi), known cells remain fixed.
    Faster than Delaunay on large gaps, leaves no triangulation artifacts.
    """
    missing = np.isnan(z)
    if not missing.any():
        return z.copy()

    known = ~missing
    if known.sum() < 4:
        return np.nan_to_num(z, nan=0.0)

    nearest_r, nearest_c = _nearest_known_indices(missing)
    filled = np.where(missing, z[nearest_r, nearest_c], z).astype(np.float32)
    known_vals = np.where(known, z, 0).astype(np.float32)

    for _ in range(iterations):
        # Edge padding so boundary cells don't pull from the opposite edge.
        p = np.pad(filled, 1, mode="edge")
        neighbor_avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4.0
        filled = np.where(missing, neighbor_avg, known_vals)

    return filled


def classify_land_water(ahn_valid: np.ndarray, gap_mask: np.ndarray) -> np.ndarray:
    """Boolean is_land grid to ensure the area behind the dikes (below NAP) is not
    visualized as water by default.
    Classify cell as land when it's from AHN. Gap cells take label of nearest
    known cell (similar to fill_gaps)
    """
    is_land = ahn_valid.copy()
    if not gap_mask.any() or gap_mask.all():
        return is_land

    nearest_r, nearest_c = _nearest_known_indices(gap_mask)
    return np.where(gap_mask, is_land[nearest_r, nearest_c], is_land)
