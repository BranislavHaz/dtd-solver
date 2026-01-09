# dtd_solver/debug.py
# Debug / inspection helpers:
# - pretty-print placements and cuts
# - quick ASCII summaries
# - helpful when tuning solver parameters

from __future__ import annotations

from typing import Iterable, List

from .types import Cut, Placement, SheetResult, Solution


def print_placements(placements: Iterable[Placement]) -> None:
    for p in placements:
        print(
            f"[S{p.sheet_index}] {p.part_uid:20s} "
            f"x={p.x:4d} y={p.y:4d} w={p.w:4d} h={p.h:4d} "
            f"{'R' if p.rotated else ' '}"
        )


def print_cuts(cuts: Iterable[Cut]) -> None:
    for c in cuts:
        axis = "x" if c.orientation == "V" else "y"
        print(
            f"[S{c.sheet_index}] {c.orientation} cut @ {axis}={c.coord:4d} "
            f"seg=({c.a0:4d}..{c.a1:4d}) len={c.length():4d} stage={c.stage}"
        )


def print_sheet(sheet: SheetResult) -> None:
    print(f"=== Sheet {sheet.sheet_index + 1} ===")
    print(f"Parts: {len(sheet.placements)}  Cuts: {len(sheet.cuts)}")
    if sheet.cut_length_internal is not None:
        print(f"Cut internal: {sheet.cut_length_internal:,} mm")
    if sheet.cut_length_trim_charged is not None:
        print(f"Cut trim-charged: {sheet.cut_length_trim_charged:,} mm")
    if sheet.waste_area is not None:
        print(f"Waste: {sheet.waste_area:,} mm²")
    print("-- Placements --")
    print_placements(sheet.placements)
    print("-- Cuts --")
    print_cuts(sheet.cuts)


def print_solution(sol: Solution) -> None:
    print(f"Sheets: {sol.num_sheets()}")
    for sh in sol.sheets:
        print_sheet(sh)
    if sol.total_cut_length() is not None:
        print(f"TOTAL CUT: {sol.total_cut_length():,} mm")
    if sol.total_waste_area() is not None:
        print(f"TOTAL WASTE: {sol.total_waste_area():,} mm²")

