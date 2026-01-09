#!/usr/bin/env python3
"""Quick test to check if dtd_solver works."""

from dtd_solver.types import BoardSpec, PartSpec
from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves

def main():
    # Create board
    board = BoardSpec(
        name="DTD",
        raw_w=2800,
        raw_h=2070,
        trim=__import__('dtd_solver.types', fromlist=['Trim']).Trim(10, 10, 10, 10)
    )

    # Create example parts
    parts = [
        PartSpec("Vysoka_skrina_bok", 2400, 560, qty=2, can_rotate=False),
        PartSpec("Vysoka_skrina_polica", 560, 500, qty=6, can_rotate=True),
        PartSpec("Mala_skrina_bok", 720, 560, qty=2, can_rotate=False),
        PartSpec("Dvierka", 715, 397, qty=4, can_rotate=False),
        PartSpec("Podstava", 564, 120, qty=6, can_rotate=True),
    ]

    # Create solver params
    params = SolverParams(
        kerf=3,
        time_limit_s=10.0,
        max_sheets=20,
        cut_weight=1,
    )

    # Solve
    print("Starting solver...")
    sol = solve_from_partspecs_iterative_shelves(board, parts, params=params)

    # Print results
    print(f"Used sheets: {sol.num_sheets()}")
    total_cut = sol.total_cut_length()
    total_waste = sol.total_waste_area()
    if total_cut is not None:
        print(f"Total cut length (internal + trim-charged): {total_cut:,} mm")
    if total_waste is not None:
        print(f"Total waste area: {total_waste:,} mm²")
    
    print("✓ Solver completed successfully!")

if __name__ == "__main__":
    main()
