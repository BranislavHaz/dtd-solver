# dtd_solver/zone_allocation.py
# Zone allocation heuristics for hybrid guillotine planning.
#
# Goal:
# - Decide WHICH parts go to WHICH zone (strip vs block) BEFORE packing,
#   instead of packing region A first and "leftovers" region B.
#
# This module is solver-agnostic: it only takes part sizes + zone sizes
# and returns an assignment. The packing is done elsewhere (CP-SAT shelves inside each zone).
#
# The idea:
# - "Strip zone" is typically meant for long/tall parts (e.g., cabinet sides).
# - "Block zones" are for smaller pieces.
# - Assignment prioritizes feasibility + efficiency + reduced expected cut length.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .types import InstancePart


@dataclass(frozen=True)
class Zone:
    """A rectangular zone (usable coords local to the sheet)."""
    id: str
    w: int
    h: int
    kind: str  # "strip" or "block"


@dataclass(frozen=True)
class Assigned:
    zone_id: str
    part_uids: List[str]


@dataclass(frozen=True)
class AllocationResult:
    """Mapping part_uid -> zone_id (or None if unassigned)."""
    part_to_zone: Dict[str, Optional[str]]
    zones: List[Zone]


def _fits_in_zone(p: InstancePart, z: Zone) -> bool:
    # If can_rotate, allow either orientation.
    if p.can_rotate:
        return (p.w <= z.w and p.h <= z.h) or (p.h <= z.w and p.w <= z.h)
    return (p.w <= z.w and p.h <= z.h)


def _efficiency_score(pw: int, ph: int, zw: int, zh: int) -> float:
    """
    Higher is better. Measures how well a part "fills" a zone in at least one dimension,
    helping reduce fragmentation and internal cuts.
    """
    # Normalize fill ratios
    r1 = pw / max(1, zw)
    r2 = ph / max(1, zh)
    # Prefer parts that use a lot of one dimension (strip behavior) or both (block fill).
    return max(r1, r2) * 0.7 + (r1 * r2) * 0.3


def _best_orient_for_zone(p: InstancePart, z: Zone) -> Optional[Tuple[int, int, bool]]:
    """
    Returns (w_eff, h_eff, rotated) for best fit in zone, or None if doesn't fit.
    """
    # no rotate
    if p.w <= z.w and p.h <= z.h:
        best = (p.w, p.h, False)
    else:
        best = None

    if p.can_rotate and p.h <= z.w and p.w <= z.h:
        cand = (p.h, p.w, True)
        if best is None:
            best = cand
        else:
            # choose orientation that improves efficiency
            bscore = _efficiency_score(best[0], best[1], z.w, z.h)
            cscore = _efficiency_score(cand[0], cand[1], z.w, z.h)
            if cscore > bscore:
                best = cand

    return best


def allocate_parts_to_zones(
    parts: List[InstancePart],
    zones: List[Zone],
    *,
    prefer_strip_for_long: bool = True,
    long_ratio: float = 0.82,
) -> AllocationResult:
    """
    Greedy allocation:
    1) Compute for each part the best zone based on:
       - feasibility
       - zone kind preference (strip vs block)
       - efficiency score
    2) Assign parts in descending "difficulty" (largest first).
    3) If a part fits multiple zones, prefer:
       - strip zone for long/tall parts (when prefer_strip_for_long)
       - otherwise the zone where it fills best.

    IMPORTANT:
    This does NOT enforce per-zone capacity exactly (that's done by packing solver),
    but it strongly reduces the chance that strip-worthy parts get scattered.

    long_ratio:
      if max_dim / min_dim >= long_ratio_threshold (approx), classify as "long".
      For example, 2100x580 => 3.62 => definitely long.
    """
    # Precompute zone lists by kind
    strip_zones = [z for z in zones if z.kind == "strip"]
    block_zones = [z for z in zones if z.kind == "block"]

    # Difficulty ordering: big area first, then max dimension
    def difficulty(p: InstancePart) -> Tuple[int, int]:
        return (p.w * p.h, max(p.w, p.h))

    parts_sorted = sorted(parts, key=difficulty, reverse=True)

    part_to_zone: Dict[str, Optional[str]] = {p.uid: None for p in parts_sorted}

    for p in parts_sorted:
        # classify long
        mx = max(p.w, p.h)
        mn = max(1, min(p.w, p.h))
        aspect = mx / mn
        is_long = aspect >= (1.0 / max(1e-6, (1.0 - long_ratio))) if long_ratio < 1.0 else aspect >= 3.0
        # The above maps long_ratio like 0.82 -> aspect >= ~5.55; that’s too strict.
        # Use a more practical rule:
        is_long = aspect >= 2.2  # typical "strip" feel

        candidates: List[Tuple[float, str]] = []  # (score, zone_id)

        # Choose which zones to prefer
        if prefer_strip_for_long and is_long and strip_zones:
            primary = strip_zones + block_zones
        else:
            primary = block_zones + strip_zones

        for z in primary:
            best = _best_orient_for_zone(p, z)
            if best is None:
                continue
            w_eff, h_eff, _rot = best

            eff = _efficiency_score(w_eff, h_eff, z.w, z.h)

            # Kind bias
            bias = 0.0
            if z.kind == "strip" and is_long:
                bias += 0.20
            if z.kind == "block" and not is_long:
                bias += 0.10

            # Additional bias: if part nearly matches zone height/width (reduces later cuts)
            near = 0.0
            if abs(h_eff - z.h) <= 10 or abs(w_eff - z.w) <= 10:
                near += 0.10

            score = eff + bias + near
            candidates.append((score, z.id))

        if not candidates:
            part_to_zone[p.uid] = None
            continue

        candidates.sort(reverse=True, key=lambda t: t[0])
        part_to_zone[p.uid] = candidates[0][1]

    return AllocationResult(part_to_zone=part_to_zone, zones=zones)


def group_parts_by_zone(
    parts: List[InstancePart],
    allocation: AllocationResult,
) -> Dict[str, List[InstancePart]]:
    """
    Return mapping zone_id -> list of parts assigned to that zone.
    Unassigned parts go under key "__UNASSIGNED__".
    """
    by: Dict[str, List[InstancePart]] = {z.id: [] for z in allocation.zones}
    by["__UNASSIGNED__"] = []

    for p in parts:
        zid = allocation.part_to_zone.get(p.uid, None)
        if zid is None:
            by["__UNASSIGNED__"].append(p)
        else:
            by.setdefault(zid, []).append(p)

    return by
