# dtd_solver/compat_packingsolver.py
# Compatibility helpers to compare with fontanf/packingsolver-style inputs.
# This allows you to:
# - load rectangle lists that were prepared for packingsolver
# - map them to PartSpec
#
# Goal: make it easier to benchmark our solver vs packingsolver on the same data.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import json

from .types import PartSpec


@dataclass(frozen=True)
class PackingSolverRect:
    id: str
    w: int
    h: int
    can_rotate: bool = True


def load_packingsolver_json(path: str | Path) -> List[PartSpec]:
    """
    Load a minimal subset of packingsolver-style JSON:
    [
      {"id": "A", "w": 500, "h": 300, "quantity": 4, "can_rotate": true},
      ...
    ]
    and convert to PartSpec.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    parts: List[PartSpec] = []
    for item in data:
        name = str(item.get("id") or item.get("name") or "")
        w = int(item["w"])
        h = int(item["h"])
        qty = int(item.get("quantity", 1))
        can_rotate = bool(item.get("can_rotate", True))
        parts.append(PartSpec(name=name, w=w, h=h, qty=qty, can_rotate=can_rotate))

    return parts

