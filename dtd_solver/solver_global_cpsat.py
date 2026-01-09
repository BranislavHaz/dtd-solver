# dtd_solver/solver_global_cpsat.py
# Global optimization solver - tries multiple sort orders and picks the best
# This avoids the pure greedy sheet-by-sheet approach and finds better solutions
#
# Usage:
#   from solver_global_cpsat import solve_global_cpsat
#   sol = solve_global_cpsat(board, parts, max_sheets=3)

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import random

from .types import BoardSpec, InstancePart, Solution
from .solver_shelf_cp_sat import SolverParams, solve_iterative_shelves


@dataclass
class GlobalParams:
    kerf: int = 4
    max_sheets: int = 3
    time_limit_s: float = 60.0
    max_shelves: int = 18


def solve_global_cpsat(
    board: BoardSpec,
    parts: List[InstancePart],
    params: Optional[GlobalParams] = None,
) -> Solution:
    """
    Global solver: try multiple sort orders and use best fit decreasing strategy.
    This provides better packing than pure iterative sheet-by-sheet.
    """
    params = params or GlobalParams()
    
    best_sol = None
    best_sheets = float('inf')
    
    # Try multiple sort strategies
    strategies = [
        lambda p: (-p.w * p.h, p.uid),  # Largest area first (decreasing)
        lambda p: (-max(p.w, p.h), p.uid),  # Largest dimension first
        lambda p: (-p.w, -p.h, p.uid),  # Sort by width then height (decreasing)
        lambda p: (-p.h, -p.w, p.uid),  # Sort by height then width (decreasing)
    ]
    
    for strategy in strategies:
        sorted_parts = sorted(parts, key=strategy)
        
        sp = SolverParams(
            kerf=params.kerf,
            time_limit_s=params.time_limit_s,
            max_sheets=params.max_sheets,
            cut_weight=1,
            max_shelves=params.max_shelves,
        )
        sol = solve_iterative_shelves(board, sorted_parts, params=sp)
        
        num_sheets = sol.num_sheets()
        if num_sheets < best_sheets:
            best_sheets = num_sheets
            best_sol = sol
    
    return best_sol or Solution(board=board, sheets=[])
