# dtd_solver/io_csv.py
# CSV import/export helpers:
# - export placements per sheet
# - export cut list per sheet (for pricing / verification)
#
# (No PDF export; plotting is handled in plotting.py.)

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Optional

from .types import BoardSpec, Cut, Placement, SheetResult, Solution


def export_placements_csv(
    solution: Solution,
    path: str | Path,
) -> None:
    """
    Write placements into a CSV file.
    Coordinates are in usable (trimmed) space.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sheet_index",
        "part_uid",
        "x",
        "y",
        "w",
        "h",
        "rotated",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for sheet in solution.sheets:
            for pl in sheet.placements:
                w.writerow(
                    {
                        "sheet_index": pl.sheet_index,
                        "part_uid": pl.part_uid,
                        "x": pl.x,
                        "y": pl.y,
                        "w": pl.w,
                        "h": pl.h,
                        "rotated": int(bool(pl.rotated)),
                    }
                )


def export_cuts_csv(
    solution: Solution,
    path: str | Path,
) -> None:
    """
    Write internal cut segments into a CSV file.
    Coordinates are in usable (trimmed) space:
      - orientation V: coord=x, a0=y0, a1=y1
      - orientation H: coord=y, a0=x0, a1=x1
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sheet_index",
        "stage",
        "orientation",
        "coord",
        "a0",
        "a1",
        "length",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for sheet in solution.sheets:
            for c in sheet.cuts:
                w.writerow(
                    {
                        "sheet_index": c.sheet_index,
                        "stage": c.stage,
                        "orientation": c.orientation,
                        "coord": c.coord,
                        "a0": c.a0,
                        "a1": c.a1,
                        "length": c.length(),
                    }
                )


def export_summary_csv(solution: Solution, path: str | Path) -> None:
    """
    One-row-per-sheet summary (useful for quick costing).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sheet_index",
        "board_name",
        "raw_w",
        "raw_h",
        "usable_w",
        "usable_h",
        "waste_area_mm2",
        "cut_internal_mm",
        "cut_trim_charged_mm",
        "cut_total_mm",
        "num_parts",
        "num_cuts",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for sheet in solution.sheets:
            board = sheet.board
            w.writerow(
                {
                    "sheet_index": sheet.sheet_index,
                    "board_name": board.name,
                    "raw_w": board.raw_w,
                    "raw_h": board.raw_h,
                    "usable_w": board.usable_w,
                    "usable_h": board.usable_h,
                    "waste_area_mm2": sheet.waste_area if sheet.waste_area is not None else "",
                    "cut_internal_mm": sheet.cut_length_internal if sheet.cut_length_internal is not None else "",
                    "cut_trim_charged_mm": sheet.cut_length_trim_charged if sheet.cut_length_trim_charged is not None else "",
                    "cut_total_mm": sheet.total_cut_length() if sheet.total_cut_length() is not None else "",
                    "num_parts": len(sheet.placements),
                    "num_cuts": len(sheet.cuts),
                }
            )


def export_all(solution: Solution, out_dir: str | Path, prefix: str = "solution") -> None:
    """
    Export placements, cuts, and per-sheet summary into out_dir.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    export_placements_csv(solution, out_dir / f"{prefix}_placements.csv")
    export_cuts_csv(solution, out_dir / f"{prefix}_cuts.csv")
    export_summary_csv(solution, out_dir / f"{prefix}_summary.csv")

