# dtd_solver/config.py
# Centralized defaults and configuration helpers.
# Keeps "magic numbers" (kerf, trim defaults, weights) in one place.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .types import BoardSpec, Trim


@dataclass(frozen=True)
class Defaults:
    # Typical EU large-format board for DTD (adjust to your supplier)
    default_board_raw_w: int = 2800
    default_board_raw_h: int = 2070
    default_thickness: int = 18

    # Typical trim around uneven edges (mm)
    default_trim: Trim = Trim(left=10, right=10, top=10, bottom=10)

    # Typical panel saw kerf (mm)
    default_kerf: int = 3

    # Solver time budgets
    default_time_limit_s_per_sheet: float = 10.0
    default_max_sheets: int = 20

    # Baseline objective weights (shelves solver)
    # cut_weight penalizes internal cut length (approx) while maximizing used area
    default_cut_weight: int = 1
    default_shelf_count_weight: int = 0


DEFAULTS = Defaults()


def make_default_board(
    name: str = "DTD",
    *,
    raw_w: Optional[int] = None,
    raw_h: Optional[int] = None,
    thickness: Optional[int] = None,
    trim: Optional[Trim] = None,
) -> BoardSpec:
    """
    Convenience factory for a typical DTD board.
    """
    return BoardSpec(
        name=name,
        raw_w=int(raw_w if raw_w is not None else DEFAULTS.default_board_raw_w),
        raw_h=int(raw_h if raw_h is not None else DEFAULTS.default_board_raw_h),
        thickness=int(thickness if thickness is not None else DEFAULTS.default_thickness),
        trim=trim if trim is not None else DEFAULTS.default_trim,
    )


def clamp_int(v: float | int, lo: int, hi: int) -> int:
    """Clamp a numeric value to an int range."""
    x = int(round(float(v)))
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def parse_board_text(board_text: str) -> Tuple[int, int]:
    """
    Parse '2800x2070' -> (2800, 2070)
    """
    s = board_text.lower().replace(" ", "")
    if "x" not in s:
        raise ValueError("board_text must be like '2800x2070'")
    a, b = s.split("x", 1)
    return int(float(a)), int(float(b))


def parse_trim_text(trim_text: str) -> Trim:
    """
    Parse 'left,right,top,bottom' -> Trim(...)
    """
    vals = [v.strip() for v in trim_text.split(",") if v.strip() != ""]
    if len(vals) != 4:
        raise ValueError("trim_text must be 'left,right,top,bottom' (e.g. '10,10,10,10')")
    l, r, t, b = (int(float(x)) for x in vals)
    return Trim(left=l, right=r, top=t, bottom=b)

