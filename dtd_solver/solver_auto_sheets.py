# dtd_solver/solver_auto_sheets.py
# Automatically find minimum number of sheets needed for all parts
# Uses binary search to find the optimal sheet count

from __future__ import annotations

from typing import List, Optional
import math
from .types import BoardSpec, InstancePart, Solution
from .solver_bottomleft import solve_bottomleft


def solve_auto_sheets(
    board: BoardSpec,
    parts: List[InstancePart],
    time_limit_s: float = 60.0,
    max_sheets_cap: int = 50,
    cut_weight: int = 2,
    max_shelves: int = 18,
) -> Solution:
    """
    Automatically find minimum number of sheets needed.
    Uses binary search: tries to pack all parts with increasing sheet counts.
    Starts from a reasonable lower bound based on total area.
    
    Returns the best solution with minimum number of sheets.
    """
    
    # Calculate total area of all parts
    total_parts_area = sum(p.w * p.h for p in parts)
    board_usable_area = board.usable_w * board.usable_h
    
    # Lower bound: minimum sheets needed based on area (using ceiling, not floor)
    min_sheets_start = max(2, math.ceil(total_parts_area / board_usable_area))
    
    print(f"[AUTO] Total parts area: {total_parts_area:,} mm²", flush=True)
    print(f"[AUTO] Board usable area: {board_usable_area:,} mm²", flush=True)
    print(f"[AUTO] Theoretical minimum sheets: {total_parts_area / board_usable_area:.2f} → {min_sheets_start}", flush=True)
    print(f"[AUTO] Starting search from {min_sheets_start} sheets...", flush=True)
    
    best_sol = None
    
    # Try sheet counts from calculated minimum upward until we succeed in placing all parts
    for num_sheets_try in range(min_sheets_start, max_sheets_cap + 1):
        print(f"[AUTO] Trying with {num_sheets_try} sheets...", flush=True)
        
        params = SolverParams(
            kerf=4,  # Default kerf, will be overridden by caller if needed
            time_limit_s=time_limit_s,
            max_sheets=num_sheets_try,
            cut_weight=cut_weight,
            max_shelves=max_shelves,
        )
        
        sol = solve_iterative_shelves(board, parts, params=params)
        
        # Check if all parts were placed
        total_placed = sum(len(sheet.placements) for sheet in sol.sheets)
        
        if total_placed == len(parts):
            print(f"[AUTO] ✓ Success! All {len(parts)} parts placed in {num_sheets_try} sheets", flush=True)
            best_sol = sol
            break  # Found minimum, stop searching
        else:
            print(f"[AUTO] Only placed {total_placed}/{len(parts)} parts", flush=True)
    
    if best_sol is None:
        print(f"[AUTO] WARNING: Could not fit all parts even with {max_sheets_cap} sheets!", flush=True)
        # Return best attempt
        params = SolverParams(
            kerf=4,
            time_limit_s=time_limit_s,
            max_sheets=max_sheets_cap,
            cut_weight=cut_weight,
            max_shelves=max_shelves,
        )
        best_sol = solve_iterative_shelves(board, parts, params=params)
    
    return best_sol
