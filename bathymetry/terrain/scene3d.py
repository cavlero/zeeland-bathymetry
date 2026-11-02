import math

import numpy as np
import rasterio # noqa: E402

from .colors import TERRAIN_COLORS

TARGET_POINTS = 300
VERTICAL_EXAGGERATION = 3.0
CONTOUR_STEP_M = 5.0


def _block_mean(a: np.ndarray, step: int) -> np.ndarray:
    """NaN-aware mean over non-overlapping step x step blocks. Rows/cols
    that don't fill a whole block are dropped."""
    h = (a.shape[0] // step) * step
    w = (a.shape[1] // step) * step
    blocks = a[:h, :w].reshape(h // step, step, w // step, step)
    return np.nanmean(blocks, axis=(1, 3))


def downsample(elevation, is_land, transform):
    """Return (elev_ds, is_land_ds, xs_ds, ys_ds) at roughly TARGET_POINTS
    rows. xs/ys are RD New coordinates of each block centre."""
    step = max(1, elevation.shape[0] // TARGET_POINTS)
    # float64 keeps the averaged heights stable when rounded for the client
    elev_ds = _block_mean(elevation.astype(np.float64), step)
    # Majority vote per block
    is_land_ds = _block_mean(is_land.astype(np.float32), step) >= 0.5

    rows, cols = np.indices(elev_ds.shape)
    centre_offset = (step - 1) / 2
    xs, ys = rasterio.transform.xy(transform, rows * step + centre_offset, cols * step + centre_offset)
    xs_ds = np.array(xs).reshape(elev_ds.shape)
    ys_ds = np.array(ys).reshape(elev_ds.shape)
    return elev_ds, is_land_ds, xs_ds, ys_ds


def build_scene(elev_ds, is_land_ds, xs_ds, ys_ds, x_center, y_center) -> dict:
    """JSON-serialisable scene. Coordinates are metres relative to the site.

    The grid has no rotation, so x only varies by column and y by row; the
    two 1D axes are sent instead of a full coordinate grid.
    """
    z_min = float(np.nanmin(elev_ds))
    z_max = float(np.nanmax(elev_ds))
    return {
        "xs": [round(float(v) - x_center, 3) for v in xs_ds[0, :]],
        "ys": [round(float(v) - y_center, 3) for v in ys_ds[:, 0]],
        "elevation": [
            [None if math.isnan(v) else round(float(v), 3) for v in row]
            for row in elev_ds.tolist()
        ],
        "is_land": [[int(v) for v in row] for row in is_land_ds.tolist()],
        "z_min": z_min,
        "z_max": z_max,
        "grid_step": CONTOUR_STEP_M,
        "grid_start": float(10 * np.floor(z_min / 10)),
        "vertical_exaggeration": VERTICAL_EXAGGERATION,
        "colors": TERRAIN_COLORS,
    }
