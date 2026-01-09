# dtd_solver/plotting.py
# Minimal matplotlib visualization: draw all used sheets in one figure.
# (No PDF export for now, as requested.)

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .types import BoardSpec, Placement, SheetResult, Solution


@dataclass(frozen=True)
class PlotStyle:
    show_labels: bool = True
    show_dims: bool = True
    show_trim_frame: bool = True
    show_grid: bool = False
    font_size: int = 7
    padding_mm: int = 20  # empty margin around each sheet in drawing units
    max_cols: int = 2     # layout of multiple sheets in a single figure


def _hash_color(key: str) -> Tuple[float, float, float]:
    """Deterministic pastel-ish color from a string."""
    h = 2166136261
    for ch in key.encode("utf-8"):
        h ^= ch
        h *= 16777619
        h &= 0xFFFFFFFF
    # map to [0.3..0.9] range for readability
    r = 0.3 + ((h >> 0) & 0xFF) / 255 * 0.6
    g = 0.3 + ((h >> 8) & 0xFF) / 255 * 0.6
    b = 0.3 + ((h >> 16) & 0xFF) / 255 * 0.6
    return (r, g, b)


def _sheet_title(sheet: SheetResult) -> str:
    b = sheet.board
    uw, uh = b.usable_w, b.usable_h
    bits = [f"Sheet {sheet.sheet_index + 1}", f"{b.name}", f"usable {uw}×{uh}"]
    if sheet.total_cut_length() is not None:
        bits.append(f"cut {sheet.total_cut_length():,} mm")
    if sheet.waste_area is not None:
        bits.append(f"waste {sheet.waste_area:,} mm²")
    return " | ".join(bits)


def plot_solution(
    sol: Solution,
    style: Optional[PlotStyle] = None,
    figsize: Optional[Tuple[float, float]] = None,
) -> plt.Figure:
    """
    Draw all sheets in one matplotlib figure.
    Coordinates are in 'usable' trimmed space (0..usable_w, 0..usable_h).
    """
    style = style or PlotStyle()

    n = len(sol.sheets)
    if n == 0:
        raise ValueError("Solution has no sheets to plot")

    cols = min(style.max_cols, n)
    rows = (n + cols - 1) // cols

    if figsize is None:
        # heuristic sizing: ~6x4 per sheet
        figsize = (6 * cols, 4.5 * rows)

    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    # flatten axes to list
    ax_list: List[plt.Axes] = []
    if isinstance(axes, plt.Axes):
        # Single axis case
        ax_list = [axes]
    elif hasattr(axes, "ravel"):
        # 2D array of axes
        ax_list = list(axes.ravel())
    else:
        # Already a list
        ax_list = list(axes)

    for ax in ax_list[n:]:
        ax.axis("off")

    for idx, sheet in enumerate(sol.sheets):
        ax = ax_list[idx]
        board = sheet.board
        W, H = board.usable_w, board.usable_h

        # Frame of usable board
        frame = Rectangle((0, 0), W, H, fill=False, linewidth=1.2)
        ax.add_patch(frame)

        # Optionally show outer raw frame with trim margins (visual reference)
        if style.show_trim_frame:
            raw_W, raw_H = board.raw_w, board.raw_h
            tl, tr, tt, tb = board.trim.left, board.trim.right, board.trim.top, board.trim.bottom
            # Draw raw frame offset so usable area is at (tl, tb) inside raw
            # But we plot in usable coords; so raw frame is from (-tl, -tb) size (raw_W, raw_H)
            raw_frame = Rectangle((-tl, -tb), raw_W, raw_H, fill=False, linewidth=0.8, linestyle="--")
            ax.add_patch(raw_frame)

        # Draw parts
        for pl in sheet.placements:
            color = _hash_color(pl.part_uid.split("#", 1)[0])  # group by base name
            rect = Rectangle((pl.x, pl.y), pl.w, pl.h, facecolor=color, edgecolor="black", linewidth=0.8)
            ax.add_patch(rect)

            if style.show_labels or style.show_dims:
                lines: List[str] = []
                if style.show_labels:
                    lines.append(pl.part_uid)
                if style.show_dims:
                    lines.append(f"{pl.w}×{pl.h}" + (" R" if pl.rotated else ""))
                text = "\n".join(lines)

                ax.text(
                    pl.x + pl.w / 2,
                    pl.y + pl.h / 2,
                    text,
                    ha="center",
                    va="center",
                    fontsize=style.font_size,
                    color="black",
                )

        # Draw internal cut segments if provided
        if sheet.cuts:
            for c in sheet.cuts:
                if c.orientation == "V":
                    ax.plot([c.coord, c.coord], [c.a0, c.a1], linewidth=1.0)
                else:
                    ax.plot([c.a0, c.a1], [c.coord, c.coord], linewidth=1.0)

        ax.set_title(_sheet_title(sheet), fontsize=10)
        ax.set_aspect("equal", adjustable="box")

        # Expand limits a bit so labels aren't clipped
        pad = style.padding_mm
        ax.set_xlim(-pad, W + pad)
        ax.set_ylim(-pad, H + pad)

        if style.show_grid:
            ax.grid(True, linewidth=0.3)
        else:
            ax.grid(False)

        # Use mm-like axes but hide tick labels for cleanliness
        ax.tick_params(labelbottom=False, labelleft=False, bottom=False, left=False)

    fig.tight_layout()
    return fig


def show_solution(sol: Solution, style: Optional[PlotStyle] = None) -> None:
    """Convenience wrapper: plot and show."""
    fig = plot_solution(sol, style=style)
    plt.show()


def save_solution_png(
    sol: Solution,
    path: str,
    style: Optional[PlotStyle] = None,
    dpi: int = 200,
) -> None:
    """Optional helper: save figure to PNG."""
    fig = plot_solution(sol, style=style)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

