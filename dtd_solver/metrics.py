# dtd_solver/metrics.py
# Metrics for DTD cutting:
# - trim-charged cut length (only where a part touches the usable border)
# - internal cut length (sum of cut segments)
# - waste area (usable board area - sum(part areas))
#
# These metrics are solver-agnostic: they work for any placement/cut generator.

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .types import BoardSpec, Cut, Placement, SheetResult


@dataclass(frozen=True)
class Metrics:
    waste_area: int
    cut_length_internal: int
    cut_length_trim_charged: int

    @property
    def cut_length_total(self) -> int:
        return self.cut_length_internal + self.cut_length_trim_charged


def _validate_within_usable(board: BoardSpec, placements: Iterable[Placement]) -> None:
    W, H = board.usable_w, board.usable_h
    for pl in placements:
        if pl.x < 0 or pl.y < 0:
            raise ValueError(f"Negative placement for {pl.part_uid}: ({pl.x},{pl.y})")
        if pl.x + pl.w > W or pl.y + pl.h > H:
            raise ValueError(
                f"Placement out of usable bounds for {pl.part_uid}: "
                f"({pl.x},{pl.y},{pl.w},{pl.h}) usable=({W},{H})"
            )


def compute_waste_area(board: BoardSpec, placements: Iterable[Placement]) -> int:
    """
    Waste computed against the usable (trimmed) rectangle.
    Does NOT attempt to compute 'usable leftovers' shape, just area.
    """
    _validate_within_usable(board, placements)
    used = 0
    for pl in placements:
        used += pl.w * pl.h
    total = board.usable_w * board.usable_h
    waste = total - used
    if waste < 0:
        # Overlaps could cause this too, but should be prevented upstream.
        raise ValueError(f"Negative waste area (used={used} > total={total}).")
    return waste


def compute_internal_cut_length(cuts: Iterable[Cut]) -> int:
    """Sum of all provided cut segments lengths."""
    total = 0
    for c in cuts:
        total += c.length()
    return total


def compute_trim_charged_length(board: BoardSpec, placements: Iterable[Placement]) -> int:
    """
    Charged trim cut length:
      - count only border segments where the usable border touches a final part.
      - if border touches waste, that segment is NOT charged.
    With non-overlapping placements, the charged length can be computed as sum of
    projections of parts that touch each border.

    Assumptions:
      - placements are within usable bounds
      - placements do not overlap (not validated here)
      - coordinates are in usable space: x∈[0,W], y∈[0,H]
    """
    _validate_within_usable(board, placements)
    W, H = board.usable_w, board.usable_h

    charged = 0
    for pl in placements:
        # Left border: x == 0 contributes height
        if pl.x == 0:
            charged += pl.h
        # Right border: x+w == W contributes height
        if pl.x + pl.w == W:
            charged += pl.h
        # Bottom border: y == 0 contributes width
        if pl.y == 0:
            charged += pl.w
        # Top border: y+h == H contributes width
        if pl.y + pl.h == H:
            charged += pl.w

    return charged


def compute_sheet_metrics(sheet: SheetResult) -> Metrics:
    """
    Compute and return all key metrics for a sheet, based on its current placements and cuts.
    Also updates the SheetResult fields in-place.
    """
    waste = compute_waste_area(sheet.board, sheet.placements)
    internal = compute_internal_cut_length(sheet.cuts)
    trim_len = compute_trim_charged_length(sheet.board, sheet.placements)

    sheet.waste_area = waste
    sheet.cut_length_internal = internal
    sheet.cut_length_trim_charged = trim_len

    return Metrics(
        waste_area=waste,
        cut_length_internal=internal,
        cut_length_trim_charged=trim_len,
    )


def compute_solution_metrics(sheets: List[SheetResult]) -> Metrics:
    """
    Aggregate metrics across sheets.
    Returns totals (sum).
    """
    waste = 0
    internal = 0
    trim_len = 0
    for sh in sheets:
        m = compute_sheet_metrics(sh)
        waste += m.waste_area
        internal += m.cut_length_internal
        trim_len += m.cut_length_trim_charged
    return Metrics(waste_area=waste, cut_length_internal=internal, cut_length_trim_charged=trim_len)

