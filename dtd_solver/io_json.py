# dtd_solver/io_json.py
# Load your competitor-style JSON (like the uploaded data.json) into our BoardSpec + PartSpec list.
#
# Expected JSON shape (as in your file):
# {
#   "panels": [{"w": 2800, "h": 2100}],
#   "items": [{"id": "...", "w": 2100, "h": 580, "count": 2, "can_rotate": true}, ...],
#   "settings": {"kerf": 4, "trim": 15}
# }

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .types import BoardSpec, PartSpec, Trim


@dataclass(frozen=True)
class JsonLoadResult:
    board: BoardSpec
    parts: List[PartSpec]
    kerf: int


def load_job_json(path: str | Path, *, board_name: str = "DTD") -> JsonLoadResult:
    """
    Load job definition from JSON and convert to (BoardSpec, [PartSpec], kerf).
    - Uses the first entry in "panels" as the board size.
    - "settings.trim" is applied on all 4 sides equally.
    - "items[].count" -> PartSpec.qty
    - "items[].can_rotate" -> PartSpec.can_rotate
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    panels = data.get("panels") or []
    if not panels:
        raise ValueError("JSON missing 'panels' (need at least one panel size).")

    p0 = panels[0]
    raw_w = int(p0["w"])
    raw_h = int(p0["h"])

    settings = data.get("settings") or {}
    kerf = int(settings.get("kerf", 3))

    trim_val = int(settings.get("trim", 0))
    trim = Trim(left=trim_val, right=trim_val, top=trim_val, bottom=trim_val)

    board = BoardSpec(name=board_name, raw_w=raw_w, raw_h=raw_h, trim=trim)

    items = data.get("items") or []
    if not items:
        raise ValueError("JSON missing 'items'.")

    parts: List[PartSpec] = []
    for it in items:
        pid = str(it.get("id") or it.get("name") or "").strip()
        if not pid:
            raise ValueError(f"Item missing id/name: {it}")
        w = int(it["w"])
        h = int(it["h"])
        qty = int(it.get("count", it.get("qty", 1)))
        can_rotate = bool(it.get("can_rotate", True))
        parts.append(PartSpec(name=pid, w=w, h=h, qty=qty, can_rotate=can_rotate))

    return JsonLoadResult(board=board, parts=parts, kerf=kerf)


def dump_as_parts_csv(parts: List[PartSpec], path: str | Path) -> None:
    """
    Optional helper: write the loaded JSON parts into our CSV format (name,w,h,qty,can_rotate).
    """
    import csv

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "w", "h", "qty", "can_rotate"])
        for p in parts:
            w.writerow([p.name, p.w, p.h, p.qty, int(bool(p.can_rotate))])
