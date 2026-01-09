# dtd_solver/__init__.py
"""
DTD Solver package (panel saw / guillotine-focused).

Current state:
- Baseline CP-SAT "shelves" solver (2-stage guillotine-like) with:
  - selective rotation (per part)
  - trim-aware usable area
  - kerf spacing (safe inflation)
  - internal cut length approximation via generated cut segments
  - trim-charged cut length (only where a part touches usable border)
  - matplotlib visualization of all sheets in one figure

Next steps (planned):
- Mixed 3-stage / hybrid guillotine tree (like your competitor output)
- Exact internal cut length from the guillotine tree cuts (not just shelf postprocess)
"""

from .types import (
    Trim,
    BoardSpec,
    PartSpec,
    InstancePart,
    expand_parts,
    Placement,
    Cut,
    SheetResult,
    Solution,
)

from .metrics import (
    Metrics,
    compute_sheet_metrics,
    compute_solution_metrics,
    compute_trim_charged_length,
    compute_internal_cut_length,
    compute_waste_area,
)

from .plotting import (
    PlotStyle,
    plot_solution,
    show_solution,
    save_solution_png,
)

from .solver_shelf_cp_sat import (
    SolverParams,
    solve_iterative_shelves,
    solve_from_partspecs_iterative_shelves,
)

__all__ = [
    # types
    "Trim",
    "BoardSpec",
    "PartSpec",
    "InstancePart",
    "expand_parts",
    "Placement",
    "Cut",
    "SheetResult",
    "Solution",
    # metrics
    "Metrics",
    "compute_sheet_metrics",
    "compute_solution_metrics",
    "compute_trim_charged_length",
    "compute_internal_cut_length",
    "compute_waste_area",
    # plotting
    "PlotStyle",
    "plot_solution",
    "show_solution",
    "save_solution_png",
    # solver
    "SolverParams",
    "solve_iterative_shelves",
    "solve_from_partspecs_iterative_shelves",
]

