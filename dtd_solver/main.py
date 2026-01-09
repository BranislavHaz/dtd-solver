# dtd_solver/main.py
# Simple runnable entrypoint for the current baseline solver:
# - reads a very simple CSV format (optional)
# - solves with iterative shelf CP-SAT
# - shows matplotlib plot of all sheets in one figure
#
# You can run:
#   python -m dtd_solver.main --example
# or:
#   python -m dtd_solver.main --board 2800x2070 --trim 10,10,10,10 --kerf 3.2 --parts parts.csv
#
# CSV format for parts (header required):
#   name,w,h,qty,can_rotate
# Example:
#   Bok,720,560,2,0
#   Polica,564,500,4,1

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib
try:
    matplotlib.use('Qt5Agg')  # Try Qt5 backend first
except Exception:
    try:
        matplotlib.use('TkAgg')  # Fallback to Tk
    except Exception:
        pass  # Use default backend

from .types import BoardSpec, PartSpec, Trim
from .solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves
from .plotting import PlotStyle, show_solution, save_solution_png


def _parse_board(s: str) -> Tuple[int, int]:
    s = s.lower().replace(" ", "")
    if "x" not in s:
        raise ValueError("Board must be like 2800x2070")
    a, b = s.split("x", 1)
    return int(float(a)), int(float(b))


def _parse_trim(s: str) -> Trim:
    # "l,r,t,b" in mm
    vals = [v.strip() for v in s.split(",") if v.strip() != ""]
    if len(vals) != 4:
        raise ValueError("Trim must be 'left,right,top,bottom' (e.g. 10,10,10,10)")
    l, r, t, b = (int(float(x)) for x in vals)
    return Trim(left=l, right=r, top=t, bottom=b)


def _parse_bool(s: str) -> bool:
    s = str(s).strip().lower()
    if s in ("1", "true", "yes", "y", "t"):
        return True
    if s in ("0", "false", "no", "n", "f"):
        return False
    raise ValueError(f"Invalid bool: {s}")


def read_parts_csv(path: Path) -> List[PartSpec]:
    parts: List[PartSpec] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"name", "w", "h"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"CSV must contain at least columns: {sorted(required)}")
        for row in reader:
            name = row["name"].strip()
            w = int(float(row["w"]))
            h = int(float(row["h"]))
            qty = int(float(row.get("qty", "1") or "1"))
            can_rotate = _parse_bool(row.get("can_rotate", "1") or "1")
            parts.append(PartSpec(name=name, w=w, h=h, qty=qty, can_rotate=can_rotate))
    return parts


def example_parts() -> List[PartSpec]:
    # A tiny example reminiscent of your screenshots (replace with your real CSV soon)
    return [
        PartSpec("Vysoka_skrina_bok", 2400, 560, qty=2, can_rotate=False),
        PartSpec("Vysoka_skrina_polica", 560, 500, qty=6, can_rotate=True),
        PartSpec("Mala_skrina_bok", 720, 560, qty=2, can_rotate=False),
        PartSpec("Dvierka", 715, 397, qty=4, can_rotate=False),
        PartSpec("Podstava", 564, 120, qty=6, can_rotate=True),
    ]


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DTD panel saw cutting solver (baseline shelves CP-SAT)")
    p.add_argument("--board", type=str, default="2800x2070", help="Raw board WxH in mm, e.g. 2800x2070")
    p.add_argument("--trim", type=str, default="10,10,10,10", help="Trim l,r,t,b in mm, e.g. 10,10,10,10")
    p.add_argument("--kerf", type=float, default=3.2, help="Saw kerf in mm")
    p.add_argument("--time", type=float, default=10.0, help="Time limit per sheet solve (seconds)")
    p.add_argument("--max_sheets", type=int, default=20, help="Safety cap on number of sheets")
    p.add_argument("--cut_weight", type=int, default=1, help="Penalty weight for internal cut length (baseline approx)")
    p.add_argument("--parts", type=str, default="", help="Path to parts CSV")
    p.add_argument("--example", action="store_true", help="Use built-in example parts")
    p.add_argument("--no_labels", action="store_true", help="Hide part labels in plot")
    p.add_argument("--no_dims", action="store_true", help="Hide dimensions in plot")
    p.add_argument("--grid", action="store_true", help="Show grid in plot")
    p.add_argument("--output", type=str, default="solution.png", help="Output PNG file path (default: solution.png)")
    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = build_argparser().parse_args(argv)

    raw_w, raw_h = _parse_board(args.board)
    trim = _parse_trim(args.trim)

    board = BoardSpec(name="DTD", raw_w=raw_w, raw_h=raw_h, trim=trim)

    if args.example:
        parts = example_parts()
    else:
        if not args.parts:
            raise SystemExit("Provide --parts parts.csv or use --example")
        parts = read_parts_csv(Path(args.parts))

    params = SolverParams(
        kerf=int(round(args.kerf)),
        time_limit_s=float(args.time),
        max_sheets=int(args.max_sheets),
        cut_weight=int(args.cut_weight),
    )

    sol = solve_from_partspecs_iterative_shelves(board, parts, params=params)

    # Print summary
    print(f"Used sheets: {sol.num_sheets()}")
    total_cut = sol.total_cut_length()
    total_waste = sol.total_waste_area()
    if total_cut is not None:
        print(f"Total cut length (internal + trim-charged): {total_cut:,} mm")
    if total_waste is not None:
        print(f"Total waste area: {total_waste:,} mm²")

    # Plot
    style = PlotStyle(
        show_labels=not args.no_labels,
        show_dims=not args.no_dims,
        show_grid=bool(args.grid),
    )
    
    # Save to PNG file
    output_file = args.output
    save_solution_png(sol, output_file, style=style)
    print(f"\nNárezový plán uložený do: {output_file}")
    
    # Try to show (might fail without GUI)
    try:
        show_solution(sol, style=style)
    except Exception as e:
        print(f"Nie je možné zobraziť obrázok v termináli ({e})")


if __name__ == "__main__":
    main()

