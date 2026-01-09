# dtd_solver/types.py
# Core data structures for DTD cutting (panel saw / guillotine planning).
# Keep this file dependency-light so it can be imported everywhere.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


# ----------------------------
# Inputs
# ----------------------------

@dataclass(frozen=True)
class Trim:
    """Trim margins in millimeters (material to remove around raw board)."""
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0

    def usable_size(self, raw_w: int, raw_h: int) -> Tuple[int, int]:
        w = raw_w - self.left - self.right
        h = raw_h - self.top - self.bottom
        if w <= 0 or h <= 0:
            raise ValueError(f"Trim too large for board: raw=({raw_w},{raw_h}), trim={self}")
        return w, h


@dataclass(frozen=True)
class BoardSpec:
    """Raw board specification (before trim)."""
    name: str
    raw_w: int
    raw_h: int
    thickness: int = 18
    trim: Trim = field(default_factory=Trim)

    @property
    def usable_w(self) -> int:
        return self.trim.usable_size(self.raw_w, self.raw_h)[0]

    @property
    def usable_h(self) -> int:
        return self.trim.usable_size(self.raw_w, self.raw_h)[1]


@dataclass(frozen=True)
class PartSpec:
    """A requested rectangle piece."""
    name: str
    w: int
    h: int
    qty: int = 1

    # Rotation constraints (grain / decor)
    can_rotate: bool = True

    # Optional metadata (edge banding etc.)
    meta: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.w <= 0 or self.h <= 0:
            raise ValueError(f"Invalid part size for {self.name}: {self.w}x{self.h}")
        if self.qty <= 0:
            raise ValueError(f"qty must be >= 1 for {self.name}")


@dataclass(frozen=True)
class InstancePart:
    """A single instance (expanded from qty)."""
    uid: str              # unique id, e.g. "Spodna_60_bok#3"
    name: str             # base name
    w: int
    h: int
    can_rotate: bool


def expand_parts(parts: Iterable[PartSpec]) -> List[InstancePart]:
    """Expand qty into unique instances (stable order)."""
    out: List[InstancePart] = []
    for p in parts:
        for k in range(1, p.qty + 1):
            uid = f"{p.name}#{k}"
            out.append(InstancePart(uid=uid, name=p.name, w=p.w, h=p.h, can_rotate=p.can_rotate))
    return out


# ----------------------------
# Outputs / solution objects
# ----------------------------

@dataclass(frozen=True)
class Placement:
    """Placed part on a sheet in usable (trimmed) coordinates."""
    part_uid: str
    sheet_index: int
    x: int
    y: int
    w: int
    h: int
    rotated: bool = False

    def right(self) -> int:
        return self.x + self.w

    def top(self) -> int:
        return self.y + self.h


@dataclass(frozen=True)
class Cut:
    """
    A guillotine cut segment.
    Coordinates are in usable (trimmed) space of the sheet:
      - For vertical cut: x is fixed, segment runs [y0, y1]
      - For horizontal cut: y is fixed, segment runs [x0, x1]
    Length is computed as abs(y1-y0) or abs(x1-x0).
    """
    sheet_index: int
    orientation: str  # "V" or "H"
    coord: int        # x for V, y for H
    a0: int           # y0 for V, x0 for H
    a1: int           # y1 for V, x1 for H
    stage: int = 0    # optional: cut stage/order group

    def length(self) -> int:
        return abs(self.a1 - self.a0)

    def __post_init__(self):
        if self.orientation not in ("V", "H"):
            raise ValueError("Cut.orientation must be 'V' or 'H'")
        if self.a0 == self.a1:
            raise ValueError("Cut segment length is zero (a0 == a1)")


@dataclass
class SheetResult:
    """One used sheet: placements + cut list + summary metrics."""
    sheet_index: int
    board: BoardSpec
    placements: List[Placement] = field(default_factory=list)
    cuts: List[Cut] = field(default_factory=list)

    # Metrics (filled by solver/postprocess)
    waste_area: Optional[int] = None
    cut_length_internal: Optional[int] = None
    cut_length_trim_charged: Optional[int] = None

    def total_cut_length(self) -> Optional[int]:
        if self.cut_length_internal is None and self.cut_length_trim_charged is None:
            return None
        return (self.cut_length_internal or 0) + (self.cut_length_trim_charged or 0)


@dataclass
class Solution:
    """Full solution across multiple sheets."""
    board: BoardSpec
    sheets: List[SheetResult] = field(default_factory=list)

    # Global totals (filled by solver)
    objective_value: Optional[int] = None

    def num_sheets(self) -> int:
        return len(self.sheets)

    def total_waste_area(self) -> Optional[int]:
        vals = [s.waste_area for s in self.sheets if s.waste_area is not None]
        return sum(vals) if vals and len(vals) == len(self.sheets) else None

    def total_cut_length(self) -> Optional[int]:
        vals = [s.total_cut_length() for s in self.sheets]
        return sum(v for v in vals if v is not None) if all(v is not None for v in vals) else None


# ----------------------------
# Helper utilities
# ----------------------------

def effective_dims(part: InstancePart, rotated: bool) -> Tuple[int, int]:
    if rotated:
        return part.h, part.w
    return part.w, part.h


def check_no_overlap(placements: List[Placement]) -> None:
    """
    Simple validator: raise if any overlap detected (per sheet).
    This is useful for unit tests and sanity checks.
    """
    by_sheet: Dict[int, List[Placement]] = {}
    for pl in placements:
        by_sheet.setdefault(pl.sheet_index, []).append(pl)

    for sheet_idx, pls in by_sheet.items():
        for i in range(len(pls)):
            a = pls[i]
            ax0, ay0, ax1, ay1 = a.x, a.y, a.right(), a.top()
            for j in range(i + 1, len(pls)):
                b = pls[j]
                bx0, by0, bx1, by1 = b.x, b.y, b.right(), b.top()
                # overlap if rectangles intersect with positive area
                if (ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0):
                    raise ValueError(
                        f"Overlap on sheet {sheet_idx}: {a.part_uid} ({ax0},{ay0},{ax1},{ay1}) "
                        f"with {b.part_uid} ({bx0},{by0},{bx1},{by1})"
                    )

