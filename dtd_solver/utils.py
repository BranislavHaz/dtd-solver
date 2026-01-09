# dtd_solver/utils.py
# Small utilities used across the project:
# - timing context manager
# - stable sorting helpers
# - simple JSON export for solutions (placements + cuts + metrics)
#
# Keeps dependencies minimal (stdlib only).

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .types import Cut, Placement, SheetResult, Solution


@contextmanager
def timer(label: str = "timer") -> Iterator[Dict[str, float]]:
    """
    Usage:
      with timer("solve") as t:
          ...
      print(t["seconds"])
    """
    t0 = time.perf_counter()
    payload: Dict[str, float] = {}
    try:
        yield payload
    finally:
        payload["seconds"] = time.perf_counter() - t0


def _to_jsonable(obj: Any) -> Any:
    """Convert dataclasses and other objects to JSON-serializable structures."""
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def solution_to_dict(sol: Solution) -> Dict[str, Any]:
    """
    Convert Solution to a JSON-friendly dict.
    Keeps only essential fields + metrics.
    """
    out: Dict[str, Any] = {
        "board": {
            "name": sol.board.name,
            "raw_w": sol.board.raw_w,
            "raw_h": sol.board.raw_h,
            "usable_w": sol.board.usable_w,
            "usable_h": sol.board.usable_h,
            "trim": {
                "left": sol.board.trim.left,
                "right": sol.board.trim.right,
                "top": sol.board.trim.top,
                "bottom": sol.board.trim.bottom,
            },
            "thickness": sol.board.thickness,
        },
        "sheets": [],
        "objective_value": sol.objective_value,
        "totals": {
            "num_sheets": sol.num_sheets(),
            "total_waste_area_mm2": sol.total_waste_area(),
            "total_cut_length_mm": sol.total_cut_length(),
        },
    }

    for sh in sol.sheets:
        out["sheets"].append(
            {
                "sheet_index": sh.sheet_index,
                "placements": [
                    {
                        "part_uid": pl.part_uid,
                        "x": pl.x,
                        "y": pl.y,
                        "w": pl.w,
                        "h": pl.h,
                        "rotated": bool(pl.rotated),
                    }
                    for pl in sh.placements
                ],
                "cuts": [
                    {
                        "orientation": c.orientation,
                        "coord": c.coord,
                        "a0": c.a0,
                        "a1": c.a1,
                        "length": c.length(),
                        "stage": c.stage,
                    }
                    for c in sh.cuts
                ],
                "metrics": {
                    "waste_area_mm2": sh.waste_area,
                    "cut_internal_mm": sh.cut_length_internal,
                    "cut_trim_charged_mm": sh.cut_length_trim_charged,
                    "cut_total_mm": sh.total_cut_length(),
                },
            }
        )

    return out


def save_solution_json(sol: Solution, path: str | Path, *, indent: int = 2) -> None:
    """Save solution (placements+cutter+metrics) into JSON for debugging/integration."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = solution_to_dict(sol)
    with path.open("w", encoding="utf-8") as f:
        json.dump(_to_jsonable(payload), f, ensure_ascii=False, indent=indent)


def sort_placements_readable(placements: List[Placement]) -> List[Placement]:
    """
    Stable readable ordering: by sheet, then y, then x, then part uid.
    Helpful for debugging diffs.
    """
    return sorted(placements, key=lambda p: (p.sheet_index, p.y, p.x, p.part_uid))


def sort_cuts_readable(cuts: List[Cut]) -> List[Cut]:
    """
    Stable readable ordering: by sheet, stage, orientation, coord, a0, a1.
    """
    return sorted(cuts, key=lambda c: (c.sheet_index, c.stage, c.orientation, c.coord, c.a0, c.a1))

