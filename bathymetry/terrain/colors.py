import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize

TERRAIN_COLORS = {
    "deep": "#123a52",
    "shallow": "#7fd0e3",
    "sand": "#dbc48c",
    "above": "#6e4a30",
}

WATER_BREAK, LAND_BREAK = -1.0, 1.0

PLOT_BG = "#0a1120"
PLOT_BORDER = "#232a3d"
PLOT_TEXT = "#e8edf5"
PLOT_TEXT_DIM = "#93a1b8"
PLOT_WARN = "#fb2424"


def color_range(vmin: float, vmax: float) -> tuple[float, float]:
    """Widen (vmin, vmax) so both ramps always have a non-empty span."""
    return min(vmin, WATER_BREAK - 0.1), max(vmax, LAND_BREAK + 0.1)


def water_colormap(vmin: float):
    """deep -> shallow, clamped at WATER_BREAK."""
    v_deep, _ = color_range(vmin, 0.0)
    norm = Normalize(vmin=v_deep, vmax=WATER_BREAK, clip=True)
    cmap = LinearSegmentedColormap.from_list(
        "water", [TERRAIN_COLORS["deep"], TERRAIN_COLORS["shallow"]])
    return cmap, norm


def land_colormap(vmax: float):
    """sand -> above, clamped at LAND_BREAK so low polders stay sand-coloured."""
    _, v_above = color_range(0.0, vmax)
    norm = Normalize(vmin=LAND_BREAK, vmax=v_above, clip=True)
    cmap = LinearSegmentedColormap.from_list(
        "land", [TERRAIN_COLORS["sand"], TERRAIN_COLORS["above"]])
    return cmap, norm


def terrain_rgba(elevation, is_land, vmin, vmax, alpha=0.92) -> np.ndarray:
    """(rows, cols, 4) RGBA image. NaN cells are fully transparent."""
    water_cmap, water_norm = water_colormap(vmin)
    land_cmap, land_norm = land_colormap(vmax)
    filled = np.nan_to_num(elevation, nan=0.0)

    rgba = np.where(
        is_land[..., None],
        land_cmap(land_norm(filled)),
        water_cmap(water_norm(filled)),
    )
    rgba[..., 3] = np.where(np.isnan(elevation), 0.0, alpha)
    return rgba
