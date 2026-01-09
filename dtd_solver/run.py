# dtd_solver/run.py
# High-level convenience runner that ties together:
# - solver (currently: baseline shelves)
# - validation
# - metrics + summary
# - optional CSV export
# - matplotlib visualization (all sheets in one figure)
#
# This is meant to be called from your own scripts or future API layer.
# Example:
#   from dtd_solver.run import run_shelves
#   sol = run_shelves(board, partspecs, kerf=3, time_limit_s=10, out_dir="out", show_plot=True)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .types import BoardSpec, PartSpec, Solution, expand_parts
from .solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves
from .metrics import compute_solution_metrics
from .plotting import PlotStyle, plot_solution
from .validate import raise_on_errors, validate_solution
from .io_csv import export_all


@dataclass(frozen=True)
class RunResult:
    solution: Solution
    total_waste_area: Optional[int]
    total_cut_internal: Optional[int]
    total_cut_trim_charged: Optional[int]
    total_cut: Optional[int]


def run_shelves(
    board: BoardSpec,
    partspecs: List[PartSpec],
    *,
    kerf: int = 3,
    time_limit_s: float = 10.0,
    max_sheets: int = 20,
    cut_weight: int = 1,
    shelf_count_weight: int = 0,
    validate: bool = True,
    out_dir: Optional[str | Path] = None,
    export_prefix: str = "solution",
    show_plot: bool = True,
    plot_style: Optional[PlotStyle] = None,
):
    """
    Run the baseline shelves solver end-to-end.

    Returns RunResult. If show_plot=True, returns (RunResult, fig).
    """
    params = SolverParams(
        kerf=int(kerf),
        time_limit_s=float(time_limit_s),
        max_sheets=int(max_sheets),
        cut_weight=int(cut_weight),
        shelf_count_weight=int(shelf_count_weight),
    )

    sol = solve_from_partspecs_iterative_shelves(board, partspecs, params=params)

    if validate:
        issues = validate_solution(sol, check_cuts=True)
        raise_on_errors(issues)

    totals = compute_solution_metrics(sol.sheets) if sol.sheets else None
    res = RunResult(
        solution=sol,
        total_waste_area=totals.waste_area if totals else None,
        total_cut_internal=totals.cut_length_internal if totals else None,
        total_cut_trim_charged=totals.cut_length_trim_charged if totals else None,
        total_cut=totals.cut_length_total if totals else None,
    )

    # Export CSVs if requested
    if out_dir is not None:
        export_all(sol, out_dir=Path(out_dir), prefix=export_prefix)

    # Plot if requested
    if show_plot:
        fig = plot_solution(sol, style=plot_style or PlotStyle())
        return res, fig

    return res

