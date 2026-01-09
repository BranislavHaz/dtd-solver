# dtd_solver/solver_hybrid_tree_stub.py
# Hybrid guillotine-friendly solver — TWO-LEVEL CUT (3 zones) + zone allocation.
#
# What this version adds vs. the previous "one-cut hybrid":
# 1) Two-level cut: 2 cuts -> 3 zones (guillotine-safe)
#    - We try patterns like:
#        V@x then (H@y in left)   -> 3 zones
#        V@x then (H@y in right)
#        H@y then (V@x in bottom)
#        H@y then (V@x in top)
#      and also allow the 2nd cut orientation to be either H or V within the chosen side.
#
# 2) Allocation BEFORE packing:
#    - We build Zone objects for the 3 rectangles (strip/block)
#    - We allocate parts to zones (zone_allocation.py) first
#    - Then we pack each zone with CP-SAT shelves restricted to its assigned parts,
#      plus we opportunistically add some unassigned parts that fit (still allocation-first).
#
# 3) More precise scoring:
#    - Candidate layout is scored by:
#        (waste_area, total_cut_length, -placed_count, -placed_area)
#      i.e. primarily waste, then cut length, then pack amount.
#
# Still guillotine-friendly:
# - The first two cuts are explicit full segments
# - Inside each zone we use shelves (guillotine) and generate internal cut segments
#
# NOTE:
# This is still not the final “true CP-SAT tree” where the entire cut-tree is optimized at once,
# but it already produces competitor-like “zones + compact blocks” behavior on many jobs.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .types import BoardSpec, Cut, InstancePart, Placement, SheetResult, Solution
from .metrics import compute_sheet_metrics
from .solver_shelf_cp_sat import SolverParams, _solve_one_sheet_shelves, _generate_shelf_cuts_from_placements
from .zone_allocation import Zone, allocate_parts_to_zones, group_parts_by_zone


# ----------------------------
# Basic rectangle helper
# ----------------------------

@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def top(self) -> int:
        return self.y + self.h


# ----------------------------
# Parameters
# ----------------------------

@dataclass(frozen=True)
class HybridParams:
    kerf: int = 4
    time_limit_s: float = 40.0
    max_sheets: int = 50
    max_patterns_per_sheet: int = 80

    # Candidate generation
    grid_step: int = 50
    max_candidates: int = 24       # for first cut positions per orientation
    max_candidates_2: int = 18     # for second cut positions per orientation

    # Packing inside zones (shelves)
    region_max_shelves: int = 18

    # How many "unassigned" parts may be injected into a zone attempt
    inject_unassigned_cap: int = 24

    # Prefer lower cut length when waste is equal-ish
    prefer_lower_cut_length: bool = True

    # If two layouts have very similar waste (<= this), break ties on cut length
    waste_tie_mm2: int = 150_000  # ~0.15 m^2


# ----------------------------
# Internal helpers
# ----------------------------

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
            out.append(
                Cut(
                    sheet_index=sheet_index,
                    orientation="V",
                    coord=c.coord + dx,
                    a0=c.a0 + dy,
                    a1=c.a1 + dy,
                    stage=c.stage + stage_add,
                )
            )
        else:
            out.append(
                Cut(
                    sheet_index=sheet_index,
                    orientation="H",
                    coord=c.coord + dy,
                    a0=c.a0 + dx,
                    a1=c.a1 + dx,
                    stage=c.stage + stage_add,
                )
            )
    return out


def _part_fits_rect(p: InstancePart, w: int, h: int) -> bool:
    if p.can_rotate:
        return (p.w <= w and p.h <= h) or (p.h <= w and p.w <= h)
    return p.w <= w and p.h <= h


def _candidate_positions(parts: List[InstancePart], L: int, kerf: int, step: int, cap: int) -> List[int]:
    """
    Candidates in 1D (cut position along width or height).
    Include: part dims, grid. Keep feasible positions leaving positive space on both sides.
    """
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


def _pack_zone_shelves(
    rect: Rect,
    parts: List[InstancePart],
    params: HybridParams,
    time_limit_s: float,
) -> Tuple[List[Placement], List[InstancePart], List[Cut]]:
    """
    Pack ONE zone with shelves solver (one "sheet" inside the zone).
    Returns (placements_local, remaining_parts, cuts_local).
    """
    boardZ = _make_region_board(f"ZONE_{rect.w}x{rect.h}", rect.w, rect.h)
    sp = SolverParams(
        kerf=int(params.kerf),
        time_limit_s=float(time_limit_s),
        max_sheets=1,
        cut_weight=1,
        max_shelves=int(params.region_max_shelves),
        shelf_count_weight=0,
    )
    pls_local, rem = _solve_one_sheet_shelves(parts, boardZ, sp)
    cuts_local = _generate_shelf_cuts_from_placements(pls_local, boardZ, sheet_index=0)
    return pls_local, rem, cuts_local


def _zone_kind(rect: Rect) -> str:
    """
    Heuristic: very elongated zones are "strip", else "block".
    """
    mx = max(rect.w, rect.h)
    mn = max(1, min(rect.w, rect.h))
    aspect = mx / mn
    return "strip" if aspect >= 2.2 else "block"


def _build_zones_from_rects(rects: List[Rect]) -> List[Zone]:
    zones: List[Zone] = []
    for i, r in enumerate(rects):
        zones.append(Zone(id=f"Z{i+1}", w=r.w, h=r.h, kind=_zone_kind(r)))
    return zones


def _inject_unassigned(
    assigned: List[InstancePart],
    unassigned: List[InstancePart],
    rect: Rect,
    cap: int,
) -> List[InstancePart]:
    """
    Add some unassigned parts that fit in this zone to the candidate list,
    but without turning this into fully sequential "leftovers" packing.
    We pick largest-fitting first (by area).
    """
    cand = list(assigned)
    if cap <= 0 or not unassigned:
        return cand

    fits = [p for p in unassigned if _part_fits_rect(p, rect.w, rect.h)]
    fits.sort(key=lambda p: p.w * p.h, reverse=True)
    cand.extend(fits[:cap])
    return cand

def _inject_from_pool(
    assigned: List[InstancePart],
    pool_remaining: List[InstancePart],
    rect: Rect,
    cap: int,
) -> List[InstancePart]:
    """Inject additional candidates from the *global* remaining pool.

    Prevents the hybrid failure mode where a big block zone is left empty
    because suitable parts were pre-assigned to other zones.
    """
    cand = list(assigned)
    if cap <= 0 or not pool_remaining:
        return cand

    have = {p.uid for p in cand}
    fits = [p for p in pool_remaining if p.uid not in have and _part_fits_rect(p, rect.w, rect.h)]
    fits.sort(key=lambda p: p.w * p.h, reverse=True)
    cand.extend(fits[:cap])
    return cand



# ----------------------------
# Two-level cut patterns (3 zones)
# ----------------------------

@dataclass(frozen=True)
class TwoCutPattern:
    """
    First cut splits root into A and B.
    Second cut splits either A or B into two zones, producing 3 zones total.
    """
    first_dir: str          # "V" or "H"
    first_pos: int
    second_target: str      # "A" or "B"
    second_dir: str         # "V" or "H"
    second_pos: int


def _rects_from_pattern(W: int, H: int, kerf: int, pat: TwoCutPattern) -> Optional[Tuple[List[Rect], List[Cut]]]:
    """
    Returns (zone_rects, explicit_cuts) in usable coords, or None if invalid.
    Zone rects are non-overlapping and cover a subset (kerf gaps removed).
    """
    cuts: List[Cut] = []

    if pat.first_dir == "V":
        x = pat.first_pos
        wA = x
        wB = W - x - kerf
        if wA <= 0 or wB <= 0:
            return None
        A = Rect(0, 0, wA, H)
        B = Rect(x + kerf, 0, wB, H)
        # first cut segment spans full height
        cuts.append(Cut(sheet_index=0, orientation="V", coord=x, a0=0, a1=H, stage=0))
    else:
        y = pat.first_pos
        hA = y
        hB = H - y - kerf
        if hA <= 0 or hB <= 0:
            return None
        A = Rect(0, 0, W, hA)               # bottom
        B = Rect(0, y + kerf, W, hB)        # top
        cuts.append(Cut(sheet_index=0, orientation="H", coord=y, a0=0, a1=W, stage=0))

    # Choose target rect
    T = A if pat.second_target == "A" else B

    if pat.second_dir == "V":
        x2 = pat.second_pos
        # x2 is local to target rect width
        w1 = x2
        w2 = T.w - x2 - kerf
        if w1 <= 0 or w2 <= 0:
            return None
        R1 = Rect(T.x, T.y, w1, T.h)
        R2 = Rect(T.x + x2 + kerf, T.y, w2, T.h)
        cuts.append(Cut(sheet_index=0, orientation="V", coord=T.x + x2, a0=T.y, a1=T.y + T.h, stage=1))
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
        cuts.append(Cut(sheet_index=0, orientation="H", coord=T.y + y2, a0=T.x, a1=T.x + T.w, stage=1))
        other = B if pat.second_target == "A" else A
        rects = [other, R1, R2]

    # sanity: all rects positive
    for r in rects:
        if r.w <= 0 or r.h <= 0:
            return None

    return rects, cuts


# ----------------------------
# Build a sheet for a given pattern
# ----------------------------

def _build_sheet_for_pattern(
    board: BoardSpec,
    parts: List[InstancePart],
    params: HybridParams,
    pat: TwoCutPattern,
    sheet_index: int,
) -> Tuple[SheetResult, List[InstancePart]]:
    W, H = board.usable_w, board.usable_h
    kerf = int(params.kerf)

    tmp = _rects_from_pattern(W, H, kerf, pat)
    if tmp is None:
        # fallback empty
        sh = SheetResult(sheet_index=sheet_index, board=board, placements=[], cuts=[])
        compute_sheet_metrics(sh)
        return sh, parts

    rects, explicit_cuts = tmp
    zones = _build_zones_from_rects(rects)

    # Allocate parts to zones BEFORE packing
    allocation = allocate_parts_to_zones(parts, zones)
    by_zone = group_parts_by_zone(parts, allocation)
    unassigned = by_zone.get("__UNASSIGNED__", [])

    # Pack each zone with its assigned parts (plus a limited injection from unassigned)
    placements_all: List[Placement] = []
    cuts_all: List[Cut] = []

    # explicit cuts first (fix sheet_index)
    for c in explicit_cuts:
        cuts_all.append(
            Cut(
                sheet_index=sheet_index,
                orientation=c.orientation,
                coord=c.coord,
                a0=c.a0,
                a1=c.a1,
                stage=c.stage,
            )
        )

    # Time split across zones
    t_zone = min(0.6, max(0.2, params.time_limit_s / 12.0))


    remaining_global = set(p.uid for p in parts)

    # pack order: strip zones first (helps keep long parts together)
    zone_order = sorted(list(enumerate(zones)), key=lambda iz: (0 if iz[1].kind == "strip" else 1, -(iz[1].w * iz[1].h)))

    for zi, z in zone_order:
        rect = rects[zi]
        assigned_parts = [p for p in by_zone.get(z.id, []) if p.uid in remaining_global]

        # Global pool of still-unplaced parts (key to filling big empty gaps)
        pool_remaining = [p for p in parts if p.uid in remaining_global]

        # Strip zones are kept strict (only their assigned parts), block zones may 'top up'
        if z.kind == "strip":
            candidates = assigned_parts
        else:
            candidates = _inject_from_pool(
                assigned_parts, pool_remaining, rect, cap=int(params.inject_unassigned_cap)
            )


        pls_local, rem_local, cuts_local = _pack_zone_shelves(rect, candidates, params, time_limit_s=t_zone)

        # Determine which candidates got placed (by uid)
        placed_uids = set(p.part_uid for p in pls_local)
        # Update remaining_global
        for uid in placed_uids:
            remaining_global.discard(uid)

        # Update unassigned list by removing those we placed
        if placed_uids:
            unassigned = [p for p in unassigned if p.uid not in placed_uids]

        # Offset placements/cuts into sheet space
        pls = _offset_placements(pls_local, rect.x, rect.y, sheet_index)
        cuts = _offset_cuts(cuts_local, rect.x, rect.y, sheet_index, stage_add=2)  # inside zones after explicit cuts

        placements_all.extend(pls)
        cuts_all.extend(cuts)

    remaining_parts = [p for p in parts if p.uid in remaining_global]

    sheet = SheetResult(sheet_index=sheet_index, board=board, placements=placements_all, cuts=cuts_all)
    compute_sheet_metrics(sheet)
    return sheet, remaining_parts


# ----------------------------
# Choose best pattern for one sheet
# ----------------------------

def _score_sheet(sh: SheetResult) -> Tuple[int, int, int, int]:
    """
    Lower is better for first two components.
    """
    waste = int(sh.waste_area if sh.waste_area is not None else 10**18)
    cut = int(sh.total_cut_length() if sh.total_cut_length() is not None else 10**18)
    placed_count = len(sh.placements)
    placed_area = sum(p.w * p.h for p in sh.placements)
    # minimize waste, minimize cut, maximize placed_count, maximize placed_area
    return (waste, cut, -placed_count, -placed_area)


def _better_sheet(a: SheetResult, b: Optional[SheetResult], params: HybridParams) -> bool:
    if b is None:
        return True
    if a.waste_area is None or b.waste_area is None:
        return _score_sheet(a) < _score_sheet(b)

    # primary: waste
    if a.waste_area + params.waste_tie_mm2 < b.waste_area:
        return True
    if b.waste_area + params.waste_tie_mm2 < a.waste_area:
        return False

    # within tie band: prefer lower cut length
    if params.prefer_lower_cut_length:
        ta = a.total_cut_length()
        tb = b.total_cut_length()
        if ta is not None and tb is not None and ta != tb:
            return ta < tb

    # fallback: score tuple
    return _score_sheet(a) < _score_sheet(b)


def _choose_best_sheet_twolevel(
    board: BoardSpec,
    parts: List[InstancePart],
    params: HybridParams,
    sheet_index: int,
) -> Tuple[SheetResult, List[InstancePart]]:
    tried = 0
    W, H = board.usable_w, board.usable_h
    kerf = int(params.kerf)

    # Baseline: no explicit two cuts (full-board shelves)
    full = _make_region_board("FULL", W, H)
    sp = SolverParams(
        kerf=kerf,
        time_limit_s=float(params.time_limit_s),
        max_sheets=1,
        cut_weight=1,
        max_shelves=int(params.region_max_shelves),
        shelf_count_weight=0,
    )
    pls0_local, rem0 = _solve_one_sheet_shelves(parts, full, sp)
    cuts0_local = _generate_shelf_cuts_from_placements(pls0_local, full, sheet_index=0)
    pls0 = _offset_placements(pls0_local, 0, 0, sheet_index)
    cuts0 = _offset_cuts(cuts0_local, 0, 0, sheet_index, stage_add=0)
    best_sheet = SheetResult(sheet_index=sheet_index, board=board, placements=pls0, cuts=cuts0)
    compute_sheet_metrics(best_sheet)
    best_remaining = rem0

    # Candidate positions for first cut
    cand_x1 = _candidate_positions(parts, W, kerf, int(params.grid_step), int(params.max_candidates))
    cand_y1 = _candidate_positions(parts, H, kerf, int(params.grid_step), int(params.max_candidates))

    # For second cuts we use a smaller cap (and possibly the same step)
    # Positions are local to the chosen target rect dimensions; we’ll generate on the fly.

    def try_pattern(pat: TwoCutPattern):
        nonlocal best_sheet, best_remaining, tried
        tried += 1
        if tried > params.max_patterns_per_sheet:
            return
        sh, rem = _build_sheet_for_pattern(board, parts, params, pat, sheet_index)

        if _better_sheet(sh, best_sheet, params):
            best_sheet, best_remaining = sh, rem

    # Enumerate patterns:
    # First cut V@x: A=left, B=right; second cut inside A or B with H or V.
    for x1 in cand_x1:
        # Need rect dims to generate second candidates; compute quickly
        wA = x1
        wB = W - x1 - kerf
        if wA <= 50 or wB <= 50:
            continue

        # second inside left (A)
        cand_y2_A = _candidate_positions(parts, H, kerf, int(params.grid_step), int(params.max_candidates_2))
        cand_x2_A = _candidate_positions(parts, wA, kerf, int(params.grid_step), int(params.max_candidates_2))
        for y2 in cand_y2_A:
            try_pattern(TwoCutPattern("V", x1, "A", "H", y2))
        for x2 in cand_x2_A:
            try_pattern(TwoCutPattern("V", x1, "A", "V", x2))

        # second inside right (B)
        cand_y2_B = cand_y2_A  # same H candidates (height)
        cand_x2_B = _candidate_positions(parts, wB, kerf, int(params.grid_step), int(params.max_candidates_2))
        for y2 in cand_y2_B:
            try_pattern(TwoCutPattern("V", x1, "B", "H", y2))
        for x2 in cand_x2_B:
            try_pattern(TwoCutPattern("V", x1, "B", "V", x2))

    # First cut H@y: A=bottom, B=top; second cut inside A or B with V or H.
    for y1 in cand_y1:
        hA = y1
        hB = H - y1 - kerf
        if hA <= 50 or hB <= 50:
            continue

        # second inside bottom (A)
        cand_x2_A = _candidate_positions(parts, W, kerf, int(params.grid_step), int(params.max_candidates_2))
        cand_y2_A = _candidate_positions(parts, hA, kerf, int(params.grid_step), int(params.max_candidates_2))
        for x2 in cand_x2_A:
            try_pattern(TwoCutPattern("H", y1, "A", "V", x2))
        for y2 in cand_y2_A:
            try_pattern(TwoCutPattern("H", y1, "A", "H", y2))

        # second inside top (B)
        cand_x2_B = cand_x2_A
        cand_y2_B = _candidate_positions(parts, hB, kerf, int(params.grid_step), int(params.max_candidates_2))
        for x2 in cand_x2_B:
            try_pattern(TwoCutPattern("H", y1, "B", "V", x2))
        for y2 in cand_y2_B:
            try_pattern(TwoCutPattern("H", y1, "B", "H", y2))

    return best_sheet, best_remaining


# ----------------------------
# Public API (iterative sheets)
# ----------------------------

def solve_iterative_hybrid_twolevel(
    board: BoardSpec,
    parts: List[InstancePart],
    params: Optional[HybridParams] = None,
) -> Solution:
    params = params or HybridParams(kerf=4)
    remaining = list(parts)
    sol = Solution(board=board, sheets=[])

    sheet_idx = 0
    while remaining and sheet_idx < params.max_sheets:
        sheet, remaining2 = _choose_best_sheet_twolevel(board, remaining, params, sheet_index=sheet_idx)

        if not sheet.placements:
            break

        sol.sheets.append(sheet)
        remaining = remaining2
        sheet_idx += 1

    return sol


def solve_from_partspecs_iterative_hybrid_twolevel(
    board: BoardSpec,
    partspecs,
    params: Optional[HybridParams] = None,
) -> Solution:
    from .types import expand_parts
    parts = expand_parts(partspecs)
    return solve_iterative_hybrid_twolevel(board, parts, params=params)
