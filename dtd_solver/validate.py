# dtd_solver/validate.py
# Validation utilities:
# - check placements fit within usable area
# - check no-overlap per sheet
# - basic consistency checks for cuts (optional)
#
# Useful both during development and to sanity-check solver output.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .types import BoardSpec, Cut, Placement, SheetResult, Solution, check_no_overlap


@dataclass(frozen=True)
class ValidationIssue:
    level: str   # "ERROR" or "WARN"
    message: str
    sheet_index: Optional[int] = None
    part_uid: Optional[str] = None


def _fits(board: BoardSpec, pl: Placement) -> bool:
    W, H = board.usable_w, board.usable_h
    return (0 <= pl.x <= W) and (0 <= pl.y <= H) and (pl.x + pl.w <= W) and (pl.y + pl.h <= H)


def validate_placements(board: BoardSpec, placements: Iterable[Placement]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for pl in placements:
        if pl.w <= 0 or pl.h <= 0:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    message=f"Non-positive size for placement: {pl.w}x{pl.h}",
                    sheet_index=pl.sheet_index,
                    part_uid=pl.part_uid,
                )
            )
        if not _fits(board, pl):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    message=(
                        f"Placement out of usable bounds: "
                        f"x={pl.x}, y={pl.y}, w={pl.w}, h={pl.h}, usable={board.usable_w}x{board.usable_h}"
                    ),
                    sheet_index=pl.sheet_index,
                    part_uid=pl.part_uid,
                )
            )
    return issues


def validate_no_overlap(placements: Iterable[Placement]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    try:
        check_no_overlap(list(placements))
    except ValueError as e:
        issues.append(ValidationIssue(level="ERROR", message=str(e)))
    return issues


def validate_cuts(board: BoardSpec, cuts: Iterable[Cut]) -> List[ValidationIssue]:
    """
    Lightweight cut validation:
    - cut segments must lie within usable area bounds
    - segment length > 0 is already enforced in Cut.__post_init__
    """
    W, H = board.usable_w, board.usable_h
    issues: List[ValidationIssue] = []

    for c in cuts:
        if c.orientation == "V":
            if not (0 <= c.coord <= W):
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        message=f"Vertical cut coord x={c.coord} out of bounds [0,{W}]",
                        sheet_index=c.sheet_index,
                    )
                )
            if c.a0 < 0 or c.a1 < 0 or c.a0 > H or c.a1 > H:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        message=f"Vertical cut segment y=[{c.a0},{c.a1}] out of bounds [0,{H}]",
                        sheet_index=c.sheet_index,
                    )
                )
        else:  # "H"
            if not (0 <= c.coord <= H):
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        message=f"Horizontal cut coord y={c.coord} out of bounds [0,{H}]",
                        sheet_index=c.sheet_index,
                    )
                )
            if c.a0 < 0 or c.a1 < 0 or c.a0 > W or c.a1 > W:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        message=f"Horizontal cut segment x=[{c.a0},{c.a1}] out of bounds [0,{W}]",
                        sheet_index=c.sheet_index,
                    )
                )

    return issues


def validate_solution(sol: Solution, check_cuts: bool = True) -> List[ValidationIssue]:
    """
    Validate entire solution across sheets.
    Returns a list of issues (empty if OK).
    """
    issues: List[ValidationIssue] = []
    all_placements: List[Placement] = []

    for sheet in sol.sheets:
        # placements fit
        issues.extend(validate_placements(sheet.board, sheet.placements))
        all_placements.extend(sheet.placements)

        # cuts optional
        if check_cuts:
            issues.extend(validate_cuts(sheet.board, sheet.cuts))

    # overlaps across each sheet
    issues.extend(validate_no_overlap(all_placements))

    # warning if no sheets
    if not sol.sheets:
        issues.append(ValidationIssue(level="WARN", message="Solution has 0 sheets."))

    return issues


def raise_on_errors(issues: List[ValidationIssue]) -> None:
    errs = [i for i in issues if i.level.upper() == "ERROR"]
    if errs:
        msg = "\n".join(
            f"[{e.level}] sheet={e.sheet_index} part={e.part_uid} :: {e.message}" for e in errs
        )
        raise ValueError("Validation failed:\n" + msg)

