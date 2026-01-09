# dtd_solver/solver_shelf_cp_sat.py
# Baseline CP-SAT solver (OR-Tools) for panel-saw-friendly 2-stage guillotine packing:
# - "Shelves" (horizontal bands), and within each shelf, parts are placed left-to-right.
# - Selective rotation per part (can_rotate).
# - Trim is handled by working in usable coordinates only (0..usable_w, 0..usable_h).
# - Kerf is enforced between adjacent parts in a shelf and between shelves.
#
# This is intentionally a *working baseline* that we can extend later toward mixed 3-stage
# (hybrid guillotine trees like your competitor output). It already supports:
# - multiple sheets (iterative: pack best subset onto one sheet, remove, repeat)
# - metric-ready: placements + generated cut segments for internal cut length
# - trim-charged length computed elsewhere (metrics.py)
#
# NOTE: This solver packs a subset of remaining parts per sheet (maximize used area),
# then repeats until all parts are packed.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from .types import (
    BoardSpec,
    Cut,
    InstancePart,
    Placement,
    SheetResult,
    Solution,
    expand_parts,
)
from .metrics import compute_sheet_metrics


@dataclass(frozen=True)
class SolverParams:
    kerf: int = 3  # mm
    time_limit_s: float = 10.0
    max_sheets: int = 50

    # Objective weights for single-sheet packing:
    # maximize used area - cut_weight * (approx internal cut length)
    cut_weight: int = 1  # mm-equivalent penalty per mm cut length (tune)

    # Limit shelves to keep model small; if None, uses len(parts)
    max_shelves: Optional[int] = None

    # If True, also penalize number of shelves (helps reduce horizontal cuts)
    shelf_count_weight: int = 0


def _solve_one_sheet_shelves(
    parts: List[InstancePart],
    board: BoardSpec,
    params: SolverParams,
) -> Tuple[List[Placement], List[InstancePart]]:
    """
    Pack a subset of parts onto ONE usable sheet using shelf structure.
    Returns (placements, remaining_parts_after_removal).
    """
    W, H = board.usable_w, board.usable_h
    kerf = max(0, int(params.kerf))

    n = len(parts)
    if n == 0:
        return [], []

    max_shelves = params.max_shelves if params.max_shelves is not None else n
    max_shelves = max(1, min(max_shelves, n))

    m = cp_model.CpModel()

    # Whether part i is packed on this sheet
    use = [m.NewBoolVar(f"use[{i}]") for i in range(n)]

    # Rotation decision (only meaningful if part can rotate)
    rot = []
    for i, p in enumerate(parts):
        if p.can_rotate and p.w != p.h:
            rot_i = m.NewBoolVar(f"rot[{i}]")
        else:
            rot_i = m.NewConstant(0)
        rot.append(rot_i)

    # Effective dims (w_i, h_i) as IntVars via linearization:
    # w = w0 + rot*(h0-w0)
    # h = h0 + rot*(w0-h0)
    w_eff = []
    h_eff = []
    for i, p in enumerate(parts):
        wv = m.NewIntVar(0, max(p.w, p.h), f"w[{i}]")
        hv = m.NewIntVar(0, max(p.w, p.h), f"h[{i}]")
        m.Add(wv == p.w + (p.h - p.w) * rot[i])
        m.Add(hv == p.h + (p.w - p.h) * rot[i])
        w_eff.append(wv)
        h_eff.append(hv)

    # Shelf assignment: each used part chooses exactly one shelf in [0..max_shelves-1]
    in_shelf = [[m.NewBoolVar(f"in_shelf[{i},{s}]") for s in range(max_shelves)] for i in range(n)]
    for i in range(n):
        m.Add(sum(in_shelf[i][s] for s in range(max_shelves)) == use[i])

    # Shelf heights and y positions (stacked top-down in usable coordinates with kerf between shelves)
    shelf_h = [m.NewIntVar(0, H, f"shelf_h[{s}]") for s in range(max_shelves)]
    shelf_used = [m.NewBoolVar(f"shelf_used[{s}]") for s in range(max_shelves)]

    # shelf_used if any part assigned
    for s in range(max_shelves):
        m.Add(sum(in_shelf[i][s] for i in range(n)) >= 1).OnlyEnforceIf(shelf_used[s])
        m.Add(sum(in_shelf[i][s] for i in range(n)) == 0).OnlyEnforceIf(shelf_used[s].Not())

    # Shelf heights = max h_eff of parts in shelf (or 0 if unused)
    for s in range(max_shelves):
        for i in range(n):
            # if part i in shelf s -> shelf_h[s] >= h_eff[i]
            m.Add(shelf_h[s] >= h_eff[i]).OnlyEnforceIf(in_shelf[i][s])
        m.Add(shelf_h[s] == 0).OnlyEnforceIf(shelf_used[s].Not())

    # Enforce a canonical order: used shelves should be "packed" at low indices (symmetry break)
    # shelf_used[s] >= shelf_used[s+1]
    for s in range(max_shelves - 1):
        m.Add(shelf_used[s] >= shelf_used[s + 1])

    # Compute shelf y bottoms cumulatively: y0[0]=0, y0[s]=sum_{t<s}(shelf_h[t] + kerf if shelf_used[t+1..] ?)
    # We'll implement with cumulative variables.
    shelf_y0 = [m.NewIntVar(0, H, f"shelf_y0[{s}]") for s in range(max_shelves)]
    m.Add(shelf_y0[0] == 0)
    for s in range(1, max_shelves):
        # y0[s] = y0[s-1] + shelf_h[s-1] + (kerf if shelf_used[s] and shelf_used[s-1] else 0)
        # Since used shelves are contiguous from 0, we can approximate kerf presence by shelf_used[s]
        add_kerf = m.NewIntVar(0, kerf, f"kerf_between[{s-1},{s}]")
        if kerf == 0:
            m.Add(add_kerf == 0)
        else:
            # kerf between shelves is present if shelf_used[s] == 1 (because shelves are contiguous)
            m.Add(add_kerf == kerf).OnlyEnforceIf(shelf_used[s])
            m.Add(add_kerf == 0).OnlyEnforceIf(shelf_used[s].Not())
        m.Add(shelf_y0[s] == shelf_y0[s - 1] + shelf_h[s - 1] + add_kerf)

    # Total height constraint: last shelf bottom + its height <= H
    total_height = m.NewIntVar(0, H, "total_height")
    # total_height = shelf_y0[last] + shelf_h[last]
    m.Add(total_height == shelf_y0[max_shelves - 1] + shelf_h[max_shelves - 1])
    m.Add(total_height <= H)

    # X positions within shelf: each used part has x in [0..W-w]
    x = [m.NewIntVar(0, W, f"x[{i}]") for i in range(n)]
    y = [m.NewIntVar(0, H, f"y[{i}]") for i in range(n)]

    # Tie y[i] to shelf_y0[s] if in shelf s
    for i in range(n):
        # If not used, keep at 0
        m.Add(x[i] == 0).OnlyEnforceIf(use[i].Not())
        m.Add(y[i] == 0).OnlyEnforceIf(use[i].Not())

        # If in shelf s: y = shelf_y0[s]
        for s in range(max_shelves):
            m.Add(y[i] == shelf_y0[s]).OnlyEnforceIf(in_shelf[i][s])

        # If used: must fit within usable width and height
        m.Add(x[i] + w_eff[i] <= W).OnlyEnforceIf(use[i])
        m.Add(y[i] + h_eff[i] <= H).OnlyEnforceIf(use[i])

    # No-overlap within each shelf in 1D using optional intervals
    # Pre-calculate inflated widths
    inflated_w = []
    for i in range(n):
        infl = m.NewIntVar(0, W + kerf, f"infl_w[{i}]")
        m.Add(infl == w_eff[i] + kerf)
        inflated_w.append(infl)
    
    for s in range(max_shelves):
        intervals = []
        for i in range(n):
            # Create interval with affine expressions
            start = x[i]
            duration = inflated_w[i]
            end = m.NewIntVar(0, W + kerf, f"end[{i},{s}]")
            m.Add(end == x[i] + inflated_w[i])

            itv = m.NewOptionalIntervalVar(
                start,
                duration,
                end,
                in_shelf[i][s],
                f"itv[{i},{s}]",
            )
            intervals.append(itv)
        m.AddNoOverlap(intervals)

        # Also ensure shelf_h bounds: if part in shelf then h_eff <= shelf_h (already), and part must not exceed shelf_h:
        for i in range(n):
            m.Add(y[i] + h_eff[i] <= shelf_y0[s] + shelf_h[s]).OnlyEnforceIf(in_shelf[i][s])

    # Objective: maximize used area minus penalty for (approx) internal cut length.
    # Used area:
    area_terms = []
    for i, p in enumerate(parts):
        a = p.w * p.h
        area_terms.append(a * use[i])

    used_area = m.NewIntVar(0, W * H, "used_area")
    m.Add(used_area == sum(area_terms))

    # Approx cut length for shelf model:
    # Horizontal cuts between used shelves: (num_shelves_used - 1) * W
    # Vertical cuts within shelf: for each shelf, (num_parts_in_shelf - 1) * shelf_h[s]
    num_shelves_used = m.NewIntVar(0, max_shelves, "num_shelves_used")
    m.Add(num_shelves_used == sum(shelf_used))

    horiz_cut_len = m.NewIntVar(0, (max_shelves - 1) * W, "horiz_cut_len")
    m.Add(horiz_cut_len == (num_shelves_used - 1) * W)

    vert_cut_len_terms = []
    for s in range(max_shelves):
        count_in_s = m.NewIntVar(0, n, f"count_in_shelf[{s}]")
        m.Add(count_in_s == sum(in_shelf[i][s] for i in range(n)))
        # (count-1) * shelf_h, but if count==0 then it's 0; if count==1 then 0
        cuts_in_s = m.NewIntVar(0, max(0, n - 1), f"cuts_in_shelf[{s}]")
        # cuts_in_s = max(0, count_in_s - 1) since count is int >=0
        m.Add(cuts_in_s + 1 <= count_in_s + n).OnlyEnforceIf(shelf_used[s])  # loose, keep below
        # Better: cuts_in_s = count_in_s - 1 if count_in_s>=1 else 0
        m.Add(cuts_in_s == count_in_s - 1).OnlyEnforceIf(shelf_used[s])
        m.Add(cuts_in_s == 0).OnlyEnforceIf(shelf_used[s].Not())

        vert_len_s = m.NewIntVar(0, (n - 1) * H, f"vert_len_s[{s}]")
        m.AddMultiplicationEquality(vert_len_s, [cuts_in_s, shelf_h[s]])
        vert_cut_len_terms.append(vert_len_s)

    vert_cut_len = m.NewIntVar(0, (n - 1) * H * max_shelves, "vert_cut_len")
    m.Add(vert_cut_len == sum(vert_cut_len_terms))

    approx_cut_len = m.NewIntVar(0, 10**9, "approx_cut_len")
    m.Add(approx_cut_len == horiz_cut_len + vert_cut_len)

    # Penalize shelves a bit if desired
    shelf_pen = params.shelf_count_weight * num_shelves_used
    cut_pen = params.cut_weight * approx_cut_len

    # Maximize used_area - cut_pen - shelf_pen
    # CP-SAT minimizes; so minimize -(used_area) + ...
    obj = m.NewIntVar(-10**12, 10**12, "obj")
    m.Add(obj == -used_area + cut_pen + shelf_pen)
    m.Minimize(obj)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(params.time_limit_s)
    solver.parameters.num_search_workers = 2

    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # If nothing fits (shouldn't happen unless all parts bigger than board),
        # return empty to avoid infinite loop.
        return [], parts

    # Extract placements for used parts
    placements: List[Placement] = []
    used_ids: List[int] = []
    for i, p in enumerate(parts):
        if solver.Value(use[i]) == 1:
            xi = int(solver.Value(x[i]))
            yi = int(solver.Value(y[i]))
            ri = int(solver.Value(rot[i])) == 1
            wi = int(solver.Value(w_eff[i]))
            hi = int(solver.Value(h_eff[i]))
            placements.append(
                Placement(
                    part_uid=p.uid,
                    sheet_index=0,  # caller sets real index
                    x=xi,
                    y=yi,
                    w=wi,
                    h=hi,
                    rotated=ri,
                )
            )
            used_ids.append(i)

    # Remaining parts
    used_set = set(used_ids)
    remaining = [p for i, p in enumerate(parts) if i not in used_set]

    return placements, remaining


def _generate_shelf_cuts_from_placements(
    placements: List[Placement],
    board: BoardSpec,
    sheet_index: int,
) -> List[Cut]:
    """
    Generate *internal* cut segments consistent with shelf packing:
    - identify shelves by unique y values
    - horizontal cuts between shelves across full usable width
    - vertical cuts between adjacent parts inside each shelf across shelf height

    This is a deterministic post-process; it does not model kerf explicitly in the cut line.
    """
    if not placements:
        return []

    W, H = board.usable_w, board.usable_h

    # Group by shelf y
    by_y: Dict[int, List[Placement]] = {}
    for pl in placements:
        by_y.setdefault(pl.y, []).append(pl)

    shelves = sorted(by_y.items(), key=lambda t: t[0])  # (y0, list)
    cuts: List[Cut] = []

    # Shelf extents: height = max(h) in shelf
    shelf_info: List[Tuple[int, int, List[Placement]]] = []
    for y0, pls in shelves:
        h = max(pl.h for pl in pls)
        shelf_info.append((y0, h, pls))

    # Horizontal cuts between shelves (at boundary y = y0 + h)
    for k in range(len(shelf_info) - 1):
        y0, h, _ = shelf_info[k]
        y_cut = y0 + h
        cuts.append(
            Cut(
                sheet_index=sheet_index,
                orientation="H",
                coord=y_cut,
                a0=0,
                a1=W,
                stage=1,
            )
        )

    # Vertical cuts inside each shelf between adjacent parts
    for y0, h, pls in shelf_info:
        pls_sorted = sorted(pls, key=lambda p: p.x)
        # Create cut at boundary between consecutive parts: x = prev.right
        for a, b in zip(pls_sorted, pls_sorted[1:]):
            x_cut = a.x + a.w
            cuts.append(
                Cut(
                    sheet_index=sheet_index,
                    orientation="V",
                    coord=x_cut,
                    a0=y0,
                    a1=y0 + h,
                    stage=2,
                )
            )

    return cuts


def solve_iterative_shelves(
    board: BoardSpec,
    parts: List[InstancePart],
    params: Optional[SolverParams] = None,
) -> Solution:
    """
    Iteratively pack shelves per sheet until all parts are placed or max_sheets reached.
    """
    params = params or SolverParams()
    remaining = list(parts)
    solution = Solution(board=board, sheets=[])

    sheet_idx = 0
    while remaining and sheet_idx < params.max_sheets:
        pls, remaining2 = _solve_one_sheet_shelves(remaining, board, params)

        # If solver couldn't place anything, stop to avoid infinite loop
        if not pls:
            break

        # Assign real sheet index
        pls = [
            Placement(
                part_uid=pl.part_uid,
                sheet_index=sheet_idx,
                x=pl.x,
                y=pl.y,
                w=pl.w,
                h=pl.h,
                rotated=pl.rotated,
            )
            for pl in pls
        ]

        cuts = _generate_shelf_cuts_from_placements(pls, board, sheet_idx)

        sheet = SheetResult(sheet_index=sheet_idx, board=board, placements=pls, cuts=cuts)
        compute_sheet_metrics(sheet)  # fills waste + cut lengths (internal + trim-charged)

        solution.sheets.append(sheet)
        remaining = remaining2
        sheet_idx += 1

    if remaining:
        # Leave unplaced parts as-is; caller can handle/report.
        # (In later iterations we can add a "force pack all or fail" mode.)
        pass

    return solution


# Convenience: accept PartSpec list directly
def solve_from_partspecs_iterative_shelves(
    board: BoardSpec,
    partspecs,
    params: Optional[SolverParams] = None,
) -> Solution:
    parts = expand_parts(partspecs)
    return solve_iterative_shelves(board, parts, params=params)

