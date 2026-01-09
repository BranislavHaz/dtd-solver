# dtd_solver/cli.py
# A slightly nicer CLI than main.py:
# - supports CSV input
# - optional CSV export folder
# - prints per-sheet + total costing info (waste + cut lengths)
# - shows matplotlib figure (all sheets)
#
# Run:
#   python -m dtd_solver.cli --parts parts.csv --out out/
#
# CSV parts format (header required):
#   name,w,h,qty,can_rotate

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Optional, Tuple

from .types import BoardSpec, PartSpec, Trim
from .run import run_shelves
from .plotting import PlotStyle


def _parse_board(s: str) -> Tuple[int, int]:
    s = s.lower().replace(" ", "")
    if "x" not in s:
        raise ValueError("Board must be like 2800x2070")
    a, b = s.split("x", 1)
    return int(float(a)), int(float(b))


def _parse_trim(s: str) -> Trim:
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
            name = (row.get("name") or "").strip()
            if not name:
                continue
            w = int(float(row["w"]))
            h = int(float(row["h"]))
            qty = int(float(row.get("qty", "1") or "1"))
            can_rotate = _parse_bool(row.get("can_rotate", "1") or "1")
            parts.append(PartSpec(name=name, w=w, h=h, qty=qty, can_rotate=can_rotate))
    return parts


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DTD panel saw cutting solver (baseline shelves CP-SAT)")
    p.add_argument("--board", type=str, default="2800x2070", help="Raw board WxH in mm, e.g. 2800x2070")
    p.add_argument("--trim", type=str, default="10,10,10,10", help="Trim l,r,t,b in mm")
    p.add_argument("--kerf", type=float, default=3.2, help="Saw kerf in mm")
    p.add_argument("--time", type=float, default=10.0, help="Time limit per sheet (seconds)")
    p.add_argument("--max_sheets", type=int, default=20, help="Safety cap on sheets")
    p.add_argument("--cut_weight", type=int, default=1, help="Penalty weight for internal cut length (approx)")
    p.add_argument("--shelf_weight", type=int, default=0, help="Penalty weight for number of shelves")
    p.add_argument("--parts", type=str, required=True, help="Path to parts CSV")
    p.add_argument("--out", type=str, default="", help="Output directory for CSV exports (optional)")
    p.add_argument("--no_plot", action="store_true", help="Do not show matplotlib plot")
    p.add_argument("--no_labels", action="store_true", help="Hide part labels in plot")
    p.add_argument("--no_dims", action="store_true", help="Hide part dims in plot")
    p.add_argument("--grid", action="store_true", help="Show grid in plot")
    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = build_argparser().parse_args(argv)

    raw_w, raw_h = _parse_board(args.board)
    trim = _parse_trim(args.trim)
    board = BoardSpec(name="DTD", raw_w=raw_w, raw_h=raw_h, trim=trim)

    parts = read_parts_csv(Path(args.parts))
    if not parts:
        raise SystemExit("No parts found in CSV.")

    style = PlotStyle(
        show_labels=not args.no_labels,
        show_dims=not args.no_dims,
        show_grid=bool(args.grid),
    )

    out_dir = args.out.strip() or None

    result = run_shelves(
        board,
        parts,
        kerf=int(round(args.kerf)),
        time_limit_s=float(args.time),
        max_sheets=int(args.max_sheets),
        cut_weight=int(args.cut_weight),
        shelf_count_weight=int(args.shelf_weight),
        validate=True,
        out_dir=out_dir,
        export_prefix="solution",
        show_plot=not args.no_plot,
        plot_style=style,
    )

    # run_shelves returns (RunResult, fig) if show_plot else RunResult
    if isinstance(result, tuple):
        res, fig = result
    else:
        res, fig = result, None

    sol = res.solution
    print(f"Sheets used: {sol.num_sheets()}")
    if res.total_cut is not None:
        print(f"Total cut length (internal + trim-charged): {res.total_cut:,} mm")
        print(f"  internal: {res.total_cut_internal:,} mm")
        print(f"  trim-charged: {res.total_cut_trim_charged:,} mm")
    if res.total_waste_area is not None:
        print(f"Total waste: {res.total_waste_area:,} mm²")

    # Per sheet details
    for sh in sol.sheets:
        print(
            f"- Sheet {sh.sheet_index + 1}: parts={len(sh.placements)}, cuts={len(sh.cuts)}, "
            f"cut_total={sh.total_cut_length():,} mm, waste={sh.waste_area:,} mm²"
        )

    # If plotting is enabled, show the figure
    if fig is not None:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()

