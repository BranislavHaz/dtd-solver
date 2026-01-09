# dtd_solver/solver_hybrid_tree_stub.py
# Hybrid2 with:
# - two-level cuts (3 zones)
# - allocation
# - zone pack cache
# - NEW: shelves fallback guard + per-sheet wall-time budget + early stop
#
# Goal:
# - speed in seconds, not minutes
# - never worse than shelves on a sheet (prevents extra sheets)
# - stop searching once "good enough" is reached

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .types import BoardSpec, Cut, InstancePart, Placement, SheetResult, Solution
from .metrics import compute_sheet_metrics
from .solver_shelf_cp_sat import SolverParams, _solve_one_sheet_shelves, _generate_shelf_cuts_from_placements
from .zone_allocation import Zone, allocate_parts_to_zones, group_parts_by_zone
from .zone_pack_cache import ZonePackCache, ZonePackResult


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class HybridParams:
    kerf: int = 4
    time_limit_s: float = 12.0
    max_sheets: int = 50

    # Candidate generation
    grid_step: int = 120
    max_candidates: int = 10
    max_candidates_2: int = 6

    # Packing inside zones
    region_max_shelves: int = 18
    inject_unassigned_cap: int = 16

    # Search control
    max_patterns_per_sheet: int = 60

    # Cache sizing
    cache_max_items: int = 512

    # NEW: hard wall-time budget per sheet (seconds)
    # hybrid will stop exploring patterns after this time and return best found.
    sheet_wall_time_s: float = 2.2

    # NEW: shelves fallback time for the same sheet (seconds)
    shelves_fallback_time_s: float = 0.7

    # NEW: per-zone CP-SAT time cap (seconds) used on cache misses
    zone_time_cap_s: float = 0.8


def _zero_trim():
    from .types import Trim
    return Trim(0, 0, 0, 0)


def _make_region_board(name: str, w: int, h: int) -> BoardSpec:
    return BoardSpec(name=name, raw_w=w, raw_h=h, trim=_zero_trim())


def _offset_placements(placements: List[Placement], dx: int, dy: int, sheet_index: int) -> List[Placement]:
    return [
        Placement(
            part_uid=p.part_uid,
            sheet_index=sheet_index,
            x=p.x + dx,
            y=p.y + dy,
            w=p.w,
            h=p.h,
            rotated=p.rotated,
        )
        for p in placements
    ]


def _offset_cuts(cuts: List[Cut], dx: int, dy: int, sheet_index: int, stage_add: int = 0) -> List[Cut]:
    out: List[Cut] = []
    for c in cuts:
        if c.orientation == "V":
            out.append(Cut(sheet_index, "V", c.coord + dx, c.a0 + dy, c.a1 + dy, c.stage + stage_add))
        else:
            out.append(Cut(sheet_index, "H", c.coord + dy, c.a0 + dx, c.a1 + dx, c.stage + stage_add))
    return out


def _part_fits_rect(p: InstancePart, w: int, h: int) -> bool:
    if p.can_rotate:
        return (p.w <= w and p.h <= h) or (p.h <= w and p.w <= h)
    return p.w <= w and p.h <= h


def _candidate_positions(parts: List[InstancePart], L: int, kerf: int, step: int, cap: int) -> List[int]:
    cand = set()
    for p in parts:
        cand.add(p.w)
        cand.add(p.h)
    if step > 0:
        for x in range(step, L, step):
            cand.add(x)

    good = []
    for x in cand:
        a = x
        b = L - x - kerf
        if a >= 50 and b >= 50:
            good.append(x)
    good = sorted(good)

    if len(good) <= cap:
        return good

    # even sampling
    out = []
    for i in range(cap):
        idx = int(round(i * (len(good) - 1) / (cap - 1)))
        out.append(good[idx])
    return sorted(set(out))


def _zone_kind(rect: Rect) -> str:
    mx = max(rect.w, rect.h)
    mn = max(1, min(rect.w, rect.h))
    return "strip" if (mx / mn) >= 2.2 else "block"


def _build_zones_from_rects(rects: List[Rect]) -> List[Zone]:
    return [Zone(id=f"Z{i+1}", w=r.w, h=r.h, kind=_zone_kind(r)) for i, r in enumerate(rects)]


def _inject_unassigned(assigned: List[InstancePart], unassigned: List[InstancePart], rect: Rect, cap: int) -> List[InstancePart]:
    if cap <= 0:
        return list(assigned)
    fits = [p for p in unassigned if _part_fits_rect(p, rect.w, rect.h)]
    fits.sort(key=lambda p: p.w * p.h, reverse=True)
    return list(assigned) + fits[:cap]


@dataclass(frozen=True)
class TwoCutPattern:
    first_dir: str
    first_pos: int
    second_target: str
    second_dir: str
    second_pos: int


def _rects_from_pattern(W: int, H: int, kerf: int, pat: TwoCutPattern) -> Optional[Tuple[List[Rect], List[Cut]]]:
    cuts: List[Cut] = []
    if pat.first_dir == "V":
        x = pat.first_pos
        wA = x
        wB = W - x - kerf
        if wA <= 0 or wB <= 0:
            return None
        A = Rect(0, 0, wA, H)
        B = Rect(x + kerf, 0, wB, H)
        cuts.append(Cut(0, "V", x, 0, H, 0))
    else:
        y = pat.first_pos
        hA = y
        hB = H - y - kerf
        if hA <= 0 or hB <= 0:
            return None
        A = Rect(0, 0, W, hA)
        B = Rect(0, y + kerf, W, hB)
        cuts.append(Cut(0, "H", y, 0, W, 0))

    T = A if pat.second_target == "A" else B

    if pat.second_dir == "V":
        x2 = pat.second_pos
        w1 = x2
        w2 = T.w - x2 - kerf
        if w1 <= 0 or w2 <= 0:
            return None
        R1 = Rect(T.x, T.y, w1, T.h)
        R2 = Rect(T.x + x2 + kerf, T.y, w2, T.h)
        cuts.append(Cut(0, "V", T.x + x2, T.y, T.y + T.h, 1))
        other = B if pat.second_target == "A" else A
        rects = [other, R1, R2]
    else:
        y2 = pat.second_pos
        h1 = y2
        h2 = T.h - y2 - kerf
        if h1 <= 0 or h2 <= 0:
            return None
        R1 = Rect(T.x, T.y, T.w, h1)
        R2 = Rect(T.x, T.y + y2 + kerf, T.w, h2)
        cuts.append(Cut(0, "H", T.y + y2, T.x, T.x + T.w, 1))
        other = B if pat.second_target == "A" else A
        rects = [other, R1, R2]

    for r in rects:
        if r.w <= 0 or r.h <= 0:
            return None
    return rects, cuts


# ----------------------------
# Cache-aware zone packing
# ----------------------------

_ZONE_CACHE: Optional[ZonePackCache] = None


def _pack_zone_shelves_cached(
    rect: Rect,
    parts: List[InstancePart],
    params: HybridParams,
    cache: ZonePackCache,
) -> Tuple[List[Placement], List[InstancePart], List[Cut]]:
    kerf = int(params.kerf)
    cached = cache.get(rect.w, rect.h, kerf, parts)
    if cached is not None:
        placed = set(cached.placed_uids)
        remaining = [p for p in parts if p.uid not in placed]
        return list(cached.placements_local), remaining, list(cached.cuts_local)

    boardZ = _make_region_board(f"ZONE_{rect.w}x{rect.h}", rect.w, rect.h)
    sp = SolverParams(
        kerf=kerf,
        time_limit_s=float(params.zone_time_cap_s),
        max_sheets=1,
        cut_weight=1,
        max_shelves=int(params.region_max_shelves),
        shelf_count_weight=0,
    )
    pls_local, rem = _solve_one_sheet_shelves(parts, boardZ, sp)
    cuts_local = _generate_shelf_cuts_from_placements(pls_local, boardZ, sheet_index=0)
    placed_uids = tuple(sorted(p.part_uid for p in pls_local))
    cache.put(rect.w, rect.h, kerf, parts, ZonePackResult(pls_local, placed_uids, cuts_local))
    return pls_local, rem, cuts_local


def _sheet_candidate_shelves(
    board: BoardSpec,
    parts: List[InstancePart],
    params: HybridParams,
    sheet_index: int,
) -> Tuple[SheetResult, List[InstancePart], int]:
    """Fast shelves candidate for fallback guard."""
    W, H = board.usable_w, board.usable_h
    full = _make_region_board("FULL", W, H)
    sp = SolverParams(
        kerf=int(params.kerf),
        time_limit_s=float(params.shelves_fallback_time_s),
        max_sheets=1,
        cut_weight=1,
        max_shelves=int(params.region_max_shelves),
        shelf_count_weight=0,
    )
    pls0_local, rem0 = _solve_one_sheet_shelves(parts, full, sp)
    cuts0_local = _generate_shelf_cuts_from_placements(pls0_local, full, sheet_index=0)
    pls0 = _offset_placements(pls0_local, 0, 0, sheet_index)
    cuts0 = _offset_cuts(cuts0_local, 0, 0, sheet_index, stage_add=0)
    sh = SheetResult(sheet_index=sheet_index, board=board, placements=pls0, cuts=cuts0)
    compute_sheet_metrics(sh)
    placed_area = sum(p.w * p.h for p in sh.placements)
    return sh, rem0, placed_area


def _build_sheet_for_pattern(
    board: BoardSpec,
    parts: List[InstancePart],
    params: HybridParams,
    pat: TwoCutPattern,
    sheet_index: int,
) -> Tuple[SheetResult, List[InstancePart], int]:
    global _ZONE_CACHE
    if _ZONE_CACHE is None or _ZONE_CACHE.max_items != int(params.cache_max_items):
        _ZONE_CACHE = ZonePackCache(max_items=int(params.cache_max_items))

    W, H = board.usable_w, board.usable_h
    tmp = _rects_from_pattern(W, H, int(params.kerf), pat)
    if tmp is None:
        sh = SheetResult(sheet_index=sheet_index, board=board, placements=[], cuts=[])
        compute_sheet_metrics(sh)
        return sh, parts, 0

    rects, explicit_cuts = tmp
    zones = _build_zones_from_rects(rects)

    allocation = allocate_parts_to_zones(parts, zones)
    by_zone = group_parts_by_zone(parts, allocation)
    unassigned = by_zone.get("__UNASSIGNED__", [])

    placements_all: List[Placement] = []
    cuts_all: List[Cut] = [Cut(sheet_index, c.orientation, c.coord, c.a0, c.a1, c.stage) for c in explicit_cuts]

    remaining_global = set(p.uid for p in parts)

    zone_order = sorted(
        list(enumerate(zones)),
        key=lambda iz: (0 if iz[1].kind == "strip" else 1, -(iz[1].w * iz[1].h)),
    )

    for zi, z in zone_order:
        rect = rects[zi]
        assigned_parts = by_zone.get(z.id, [])
        candidates = _inject_unassigned(assigned_parts, unassigned, rect, cap=int(params.inject_unassigned_cap))

        pls_local, _rem_local, cuts_local = _pack_zone_shelves_cached(rect, candidates, params, cache=_ZONE_CACHE)

        placed_uids = set(p.part_uid for p in pls_local)
        for uid in placed_uids:
            remaining_global.discard(uid)

        if placed_uids:
            unassigned = [p for p in unassigned if p.uid not in placed_uids]

        placements_all.extend(_offset_placements(pls_local, rect.x, rect.y, sheet_index))
        cuts_all.extend(_offset_cuts(cuts_local, rect.x, rect.y, sheet_index, stage_add=2))

    remaining_parts = [p for p in parts if p.uid in remaining_global]
    sh = SheetResult(sheet_index=sheet_index, board=board, placements=placements_all, cuts=cuts_all)
    compute_sheet_metrics(sh)
    placed_area = sum(p.w * p.h for p in sh.placements)
    return sh, remaining_parts, placed_area


def _better_by_area_then_waste_cut(a: SheetResult, a_area: int, b: SheetResult, b_area: int) -> bool:
    """True if a is better than b."""
    if a_area != b_area:
        return a_area > b_area
    wa = a.waste_area if a.waste_area is not None else 10**18
    wb = b.waste_area if b.waste_area is not None else 10**18
    if wa != wb:
        return wa < wb
    ca = a.total_cut_length() if a.total_cut_length() is not None else 10**18
    cb = b.total_cut_length() if b.total_cut_length() is not None else 10**18
    return ca < cb


def _choose_best_sheet_twolevel(
    board: BoardSpec,
    parts: List[InstancePart],
    params: HybridParams,
    sheet_index: int,
) -> Tuple[SheetResult, List[InstancePart]]:
    W, H = board.usable_w, board.usable_h
    kerf = int(params.kerf)

    # 1) Always compute a fast shelves fallback candidate
    best_sheet, best_remaining, best_area = _sheet_candidate_shelves(board, parts, params, sheet_index)

    # Early stop: if shelves already placed everything, return it.
    if not best_remaining:
        return best_sheet, best_remaining

    # 2) Hybrid search under wall-time budget
    t0 = time.perf_counter()
    deadline = t0 + float(params.sheet_wall_time_s)

    cand_x1 = _candidate_positions(parts, W, kerf, int(params.grid_step), int(params.max_candidates))
    cand_y1 = _candidate_positions(parts, H, kerf, int(params.grid_step), int(params.max_candidates))

    tried = 0

    def time_up() -> bool:
        return time.perf_counter() >= deadline

    def try_pattern(pat: TwoCutPattern):
        nonlocal best_sheet, best_remaining, best_area, tried
        if time_up():
            return
        tried += 1
        if tried > int(params.max_patterns_per_sheet):
            return

        sh, rem, area = _build_sheet_for_pattern(board, parts, params, pat, sheet_index)

        if _better_by_area_then_waste_cut(sh, area, best_sheet, best_area):
            best_sheet, best_remaining, best_area = sh, rem, area

    # Enumerate patterns; break if time is up.
    for x1 in cand_x1:
        if time_up():
            break
        wA = x1
        wB = W - x1 - kerf
        if wA <= 50 or wB <= 50:
            continue

        cand_y2 = _candidate_positions(parts, H, kerf, int(params.grid_step), int(params.max_candidates_2))
        cand_x2_A = _candidate_positions(parts, wA, kerf, int(params.grid_step), int(params.max_candidates_2))
        cand_x2_B = _candidate_positions(parts, wB, kerf, int(params.grid_step), int(params.max_candidates_2))

        for y2 in cand_y2:
            if time_up():
                break
            try_pattern(TwoCutPattern("V", x1, "A", "H", y2))
        for x2 in cand_x2_A:
            if time_up():
                break
            try_pattern(TwoCutPattern("V", x1, "A", "V", x2))

        for y2 in cand_y2:
            if time_up():
                break
            try_pattern(TwoCutPattern("V", x1, "B", "H", y2))
        for x2 in cand_x2_B:
            if time_up():
                break
            try_pattern(TwoCutPattern("V", x1, "B", "V", x2))

        # Early stop: if current best placed everything, stop searching
        if not best_remaining:
            break

    for y1 in cand_y1:
        if time_up() or not best_remaining:
            break
        hA = y1
        hB = H - y1 - kerf
        if hA <= 50 or hB <= 50:
            continue

        cand_x2 = _candidate_positions(parts, W, kerf, int(params.grid_step), int(params.max_candidates_2))
        cand_y2_A = _candidate_positions(parts, hA, kerf, int(params.grid_step), int(params.max_candidates_2))
        cand_y2_B = _candidate_positions(parts, hB, kerf, int(params.grid_step), int(params.max_candidates_2))

        for x2 in cand_x2:
            if time_up():
                break
            try_pattern(TwoCutPattern("H", y1, "A", "V", x2))
        for y2 in cand_y2_A:
            if time_up():
                break
            try_pattern(TwoCutPattern("H", y1, "A", "H", y2))

        for x2 in cand_x2:
            if time_up():
                break
            try_pattern(TwoCutPattern("H", y1, "B", "V", x2))
        for y2 in cand_y2_B:
            if time_up():
                break
            try_pattern(TwoCutPattern("H", y1, "B", "H", y2))

    return best_sheet, best_remaining


def solve_iterative_hybrid_twolevel(
    board: BoardSpec,
    parts: List[InstancePart],
    params: Optional[HybridParams] = None,
) -> Solution:
    params = params or HybridParams()
    remaining = list(parts)
    sol = Solution(board=board, sheets=[])

    sheet_idx = 0
    while remaining and sheet_idx < params.max_sheets:
        sh, remaining2 = _choose_best_sheet_twolevel(board, remaining, params, sheet_index=sheet_idx)
        if not sh.placements:
            break
        sol.sheets.append(sh)
        remaining = remaining2
        sheet_idx += 1

    return sol


def solve_from_partspecs_iterative_hybrid_twolevel(
    board: BoardSpec,
    partspecs,
    params: Optional[HybridParams] = None,
) -> Solution:
    from .types import expand_parts
    return solve_iterative_hybrid_twolevel(board, expand_parts(partspecs), params=params)
