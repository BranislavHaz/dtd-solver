# dtd_solver/run_json.py
# Runner for competitor-style JSON input (like data.json) with solver mode switch.
#
# Modes:
#   --mode shelves   : baseline shelves CP-SAT on full sheet
#   --mode hybrid2   : hybrid TWO-LEVEL cut (3 zones) + allocation + shelves-in-zones
#
# Usage:
#   python -m dtd_solver.run_json --job data.json --mode hybrid2
#   python -m dtd_solver.run_json --job data.json --mode shelves
#
# Exports:
#   python -m dtd_solver.run_json --job data.json --mode hybrid2 --out out/
#
# Tuning (hybrid2):
#   python -m dtd_solver.run_json --job data.json --mode hybrid2 --time 60 --grid 50 --cand1 24 --cand2 18 --inject 24

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .io_json import load_job_json
from .plotting import PlotStyle, save_solution_png
from .io_csv import export_all
from .utils import save_solution_json
from .metrics import compute_solution_metrics
from .validate import validate_solution, raise_on_errors

from .solver_shelf_cp_sat import SolverParams, solve_iterative_shelves
from .solver_hybrid_tree_stub import HybridParams, solve_iterative_hybrid_twolevel
from .solver_global_cpsat import GlobalParams, solve_global_cpsat
from .solver_auto_sheets import solve_auto_sheets


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run DTD solver from competitor-style JSON (data.json).")
    p.add_argument("--job", type=str, required=True, help="Path to job JSON (panels/items/settings)")
    p.add_argument("--board_name", type=str, default="DTD", help="Board name label")

    p.add_argument("--mode", type=str, default="auto", choices=["shelves", "hybrid2", "global", "auto"], help="Solver mode")

    # Common controls
    p.add_argument("--time", type=float, default=60.0, help="Time limit per sheet (seconds)")
    p.add_argument("--max_sheets", type=int, default=3, help="Safety cap on number of sheets")
    p.add_argument("--kerf", type=int, default=-1, help="Override kerf (mm). -1 = use JSON settings")

    # Shelves tuning
    p.add_argument("--cut_weight", type=int, default=2, help="Shelves: penalty weight for internal cut length (approx)")
    p.add_argument("--shelf_weight", type=int, default=0, help="Shelves: penalty weight for number of shelves")
    p.add_argument("--max_shelves", type=int, default=18, help="Shelves: max shelves per sheet")

    # Hybrid2 tuning
    p.add_argument("--grid", type=int, default=100, help="Hybrid2: grid step for cut candidates (mm) — lower = more precise but slower")
    p.add_argument("--cand1", type=int, default=12, help="Hybrid2: max candidates for 1st cut per orientation")
    p.add_argument("--cand2", type=int, default=8, help="Hybrid2: max candidates for 2nd cut per orientation")
    p.add_argument("--inject", type=int, default=16, help="Hybrid2: how many unassigned parts to inject per zone")
    p.add_argument("--patterns", type=int, default=20, help="Hybrid2: max patterns (cut combinations) to try per sheet")
    p.add_argument("--waste_tie", type=int, default=150000, help="Hybrid2: waste tie band (mm^2) to break ties by cut length")

    # Output
    p.add_argument("--out", type=str, default="", help="Output directory for CSV + JSON exports (optional)")
    p.add_argument("--prefix", type=str, default="solution", help="Export filename prefix")

    # Plot
    p.add_argument("--no_plot", action="store_true", help="Do not show matplotlib plot")
    p.add_argument("--no_labels", action="store_true", help="Hide part labels in plot")
    p.add_argument("--no_dims", action="store_true", help="Hide part dimensions in plot")
    p.add_argument("--grid_plot", action="store_true", help="Show grid in plot")
    p.add_argument("--png", type=str, default="", help="Save plot as PNG file (optional, e.g. solution.png)")

    return p


def main(argv: Optional[list[str]] = None) -> None:
    args = build_argparser().parse_args(argv)

    job_path = Path(args.job)
    if not job_path.exists():
        raise SystemExit(f"Job JSON not found: {job_path}")

    loaded = load_job_json(job_path, board_name=args.board_name)
    board = loaded.board
    partspecs = loaded.parts
    kerf = loaded.kerf if int(args.kerf) < 0 else int(args.kerf)

    style = PlotStyle(
        show_labels=not args.no_labels,
        show_dims=not args.no_dims,
        show_grid=bool(args.grid_plot),
    )

    out_dir = args.out.strip() or None

    # Solve
    if args.mode == "shelves":
        from .types import expand_parts
        parts = expand_parts(partspecs)
        sp = SolverParams(
            kerf=int(kerf),
            time_limit_s=float(args.time),
            max_sheets=int(args.max_sheets),
            cut_weight=int(args.cut_weight),
            shelf_count_weight=int(args.shelf_weight),
            max_shelves=int(args.max_shelves),
        )
        sol = solve_iterative_shelves(board, parts, params=sp)
    elif args.mode == "hybrid2":
        from .types import expand_parts
        parts = expand_parts(partspecs)
        hp = HybridParams(
            kerf=int(kerf),
            time_limit_s=float(args.time),
            max_sheets=int(args.max_sheets),
            grid_step=int(args.grid),
            max_candidates=int(args.cand1),
            max_candidates_2=int(args.cand2),
            region_max_shelves=int(args.max_shelves),
            inject_unassigned_cap=int(args.inject),
            max_patterns_per_sheet=int(args.patterns),
            waste_tie_mm2=int(args.waste_tie),
        )
        sol = solve_iterative_hybrid_twolevel(board, parts, params=hp)
    elif args.mode == "global":
        from .types import expand_parts
        parts = expand_parts(partspecs)
        gp = GlobalParams(
            kerf=int(kerf),
            max_sheets=int(args.max_sheets),
            time_limit_s=float(args.time),
            max_shelves=int(args.max_shelves),
        )
        sol = solve_global_cpsat(board, parts, params=gp)
    else:  # auto mode - find minimum sheets automatically
        from .types import expand_parts
        parts = expand_parts(partspecs)
        sol = solve_auto_sheets(
            board,
            parts,
            time_limit_s=float(args.time),
            max_sheets_cap=int(args.max_sheets),
            cut_weight=int(args.cut_weight),
            max_shelves=int(args.max_shelves),
        )

    # Validate
    issues = validate_solution(sol, check_cuts=True)
    raise_on_errors(issues)

    totals = compute_solution_metrics(sol.sheets) if sol.sheets else None

    print(f"Mode: {args.mode}")
    print(f"Board: raw={board.raw_w}x{board.raw_h}  usable={board.usable_w}x{board.usable_h}  trim={board.trim}")
    print(f"Kerf: {kerf} mm")
    print(f"Sheets used: {sol.num_sheets()}")

    if totals is not None:
        print(f"Total cut length (internal + trim-charged): {totals.cut_length_total:,} mm")
        print(f"  internal: {totals.cut_length_internal:,} mm")
        print(f"  trim-charged: {totals.cut_length_trim_charged:,} mm")
        print(f"Total waste: {totals.waste_area:,} mm²")

    for sh in sol.sheets:
        print(
            f"- Sheet {sh.sheet_index + 1}: parts={len(sh.placements)}, cuts={len(sh.cuts)}, "
            f"cut_total={sh.total_cut_length():,} mm, waste={sh.waste_area:,} mm²"
        )

    # Exports
    if out_dir is not None:
        outp = Path(out_dir)
        outp.mkdir(parents=True, exist_ok=True)
        export_all(sol, out_dir=outp, prefix=args.prefix)
        save_solution_json(sol, outp / f"{args.prefix}.json")
        print(f"Exported CSV + JSON to: {outp}")

    # Save PNG if requested
    if args.png.strip():
        png_path = args.png.strip()
        save_solution_png(sol, png_path, style=style)
        print(f"Nárezový plán uložený do: {png_path}")

    # Plot
    if not args.no_plot:
        from .plotting import show_solution
        show_solution(sol, style=style)


if __name__ == "__main__":
    main()
