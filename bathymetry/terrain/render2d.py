import io
import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from mpl_toolkits.axes_grid1 import make_axes_locatable  # noqa: E402

from .colors import (  # noqa: E402
    PLOT_BG, PLOT_BORDER, PLOT_TEXT, PLOT_TEXT_DIM, PLOT_WARN,
    color_range, land_colormap, terrain_rgba, water_colormap,
)

MAX_GAP_DOTS = 4000


def _depth_levels(elevation):
    """Major (every 10 m) and minor (every 5 m in between) contour levels,
    anchored to multiples of 10 like the 3D scene. 0 is skipped since the
    waterline is drawn separately."""
    elev_min = float(np.nanmin(elevation))
    elev_max = float(np.nanmax(elevation))
    start = 10 * math.floor(elev_min / 10)
    major = [lvl for lvl in np.arange(start, elev_max + 1e-6, 10) if lvl != 0]
    minor = [lvl for lvl in np.arange(start + 5, elev_max + 1e-6, 10) if lvl != 0]
    return major, minor


def _remove_labels_over_land(texts, transform, is_land):
    for text in texts:
        x, y = text.get_position()
        col, row = ~transform * (x, y)
        r, c = int(round(row)), int(round(col))
        if 0 <= r < is_land.shape[0] and 0 <= c < is_land.shape[1] and is_land[r, c]:
            text.remove()


def _draw_colorbar(ax, vmin, vmax):
    """Two strips (water below 0, land above) on a linear elevation axis."""
    cbar_ax = make_axes_locatable(ax).append_axes("right", size="4%", pad=0.35)
    v_deep, v_above = color_range(vmin, vmax)
    water_cmap, water_norm = water_colormap(vmin)
    land_cmap, land_norm = land_colormap(vmax)

    cbar_ax.imshow(np.linspace(v_deep, 0.0, 128).reshape(-1, 1), aspect="auto",
                   cmap=water_cmap, norm=water_norm, extent=[0, 1, v_deep, 0.0], origin="lower")
    cbar_ax.imshow(np.linspace(0.0, v_above, 128).reshape(-1, 1), aspect="auto",
                   cmap=land_cmap, norm=land_norm, extent=[0, 1, 0.0, v_above], origin="lower")
    cbar_ax.axhline(0.0, color=PLOT_TEXT, linewidth=0.8, alpha=0.6, zorder=4)
    for label, y in (("Land", v_above / 2), ("Water", v_deep / 2)):
        cbar_ax.text(0.5, y, label, ha="center", va="center", rotation=90,
                     color=PLOT_TEXT, fontsize=7, zorder=4)

    cbar_ax.set_xticks([])
    cbar_ax.set_ylim(v_deep, v_above)
    cbar_ax.yaxis.tick_right()
    cbar_ax.yaxis.set_label_position("right")
    cbar_ax.set_ylabel("Elevation above NAP (m)", color=PLOT_TEXT_DIM)
    cbar_ax.yaxis.set_major_formatter(lambda v, pos: f"{v:+.1f}")
    cbar_ax.tick_params(colors=PLOT_TEXT_DIM, labelsize=8.5)
    for spine in cbar_ax.spines.values():
        spine.set_color(PLOT_BORDER)


def render_png(elevation, is_land, gap_mask, transform, bounds, vmin, vmax) -> bytes:
    """Render the 2D map: shaded terrain, waterline, depth contours, gap
    markers and a colour bar."""
    height, width = elevation.shape
    minx, miny, maxx, maxy = bounds
    left, top = transform * (0, 0)
    right, bottom = transform * (width, height)
    extent = [left, right, bottom, top]

    fig, ax = plt.subplots(figsize=(10, 10), facecolor=PLOT_BG)
    ax.set_facecolor(PLOT_BG)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.imshow(terrain_rgba(elevation, is_land, vmin, vmax), extent=extent, origin="upper")

    # waterline follows land/water classification
    valid = ~np.isnan(elevation)
    if valid.any() and is_land[valid].any() and (~is_land[valid]).any():
        land_for_contour = np.where(valid, is_land.astype(float), np.nan)
        ax.contour(land_for_contour, levels=[0.5], extent=extent, origin="upper",
                   colors=PLOT_TEXT, linewidths=1.2, alpha=0.9, zorder=2)

    # depth contours
    major, minor = _depth_levels(elevation)
    label_fmt = lambda lvl: f"{abs(lvl):.0f}m"
    for levels, lw, alpha, fontsize in ((minor, 0.7, 0.35, 6.5), (major, 1.3, 0.75, 8)):
        if not levels:
            continue
        cs = ax.contour(elevation, levels=levels, extent=extent, origin="upper",
                        colors="white", linewidths=lw, alpha=alpha, linestyles="solid", zorder=2)
        labels = ax.clabel(cs, fmt=label_fmt, fontsize=fontsize, colors="white", inline=True)
        _remove_labels_over_land(labels, transform, is_land)

    legend_handles = []
    if gap_mask.any():
        gap_rows, gap_cols = np.where(gap_mask)
        if len(gap_rows) > MAX_GAP_DOTS:
            idx = np.linspace(0, len(gap_rows) - 1, MAX_GAP_DOTS).astype(int)
            gap_rows, gap_cols = gap_rows[idx], gap_cols[idx]
        gap_x, gap_y = transform * (gap_cols + 0.5, gap_rows + 0.5)
        ax.scatter(gap_x, gap_y, s=4, color=PLOT_WARN, marker=".", linewidths=0, zorder=3)
        legend_handles.append(Line2D([], [], color=PLOT_WARN, marker="o", linestyle="None",
                                     markersize=6, label="No data (interpolated)"))

    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(PLOT_BORDER)
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.9,
              facecolor=PLOT_BG, edgecolor=PLOT_BORDER, labelcolor=PLOT_TEXT)

    _draw_colorbar(ax, vmin, vmax)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor=PLOT_BG, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return buf.getvalue()
