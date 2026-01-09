#!/usr/bin/env python3
"""
Simple runner that shows how to use dtd_solver WITHOUT interactive matplotlib.
Run from /home/branislav/Dokumenty/pg parent directory.
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Import from dtd_solver package
    from dtd_solver.types import BoardSpec, PartSpec, Trim
    from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves
    from dtd_solver.metrics import compute_solution_metrics
    
    # Create board specification
    print("=" * 70)
    print("DTD SOLVER - Simple Example")
    print("=" * 70)
    
    board = BoardSpec(
        name="Standard DTD Board",
        raw_w=2800,
        raw_h=2070,
        thickness=18,
        trim=Trim(left=10, right=10, top=10, bottom=10)
    )
    
    print(f"\n📋 Board: {board.name}")
    print(f"   Raw size: {board.raw_w} × {board.raw_h} mm")
    print(f"   Usable size: {board.usable_w} × {board.usable_h} mm (after trim)")
    
    # Create example parts
    parts = [
        PartSpec("Vysoka_skrina_bok", 2400, 560, qty=2, can_rotate=False),
        PartSpec("Vysoka_skrina_polica", 560, 500, qty=6, can_rotate=True),
        PartSpec("Mala_skrina_bok", 720, 560, qty=2, can_rotate=False),
        PartSpec("Dvierka", 715, 397, qty=4, can_rotate=False),
        PartSpec("Podstava", 564, 120, qty=6, can_rotate=True),
    ]
    
    print(f"\n📦 Parts ({len(parts)} types):")
    total_qty = 0
    for p in parts:
        total_qty += p.qty
        print(f"   - {p.name:30s} {p.w:4d}×{p.h:4d} mm, qty={p.qty}, rotate={p.can_rotate}")
    print(f"   Total pieces: {total_qty}")
    
    # Solver parameters
    params = SolverParams(
        kerf=3,              # 3mm saw kerf
        time_limit_s=10.0,   # 10 seconds per sheet
        max_sheets=20,       # Max 20 sheets
        cut_weight=1,        # Penalize cut length
    )
    
    print(f"\n⚙️  Solver Parameters:")
    print(f"   Kerf: {params.kerf} mm")
    print(f"   Time limit: {params.time_limit_s}s per sheet")
    print(f"   Max sheets: {params.max_sheets}")
    print(f"   Cut weight: {params.cut_weight}")
    
    # Solve
    print(f"\n🔨 Solving... (this may take a few seconds)")
    solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)
    
    # Results
    print(f"\n✅ Solution found!")
    print(f"   Used sheets: {solution.num_sheets()}")
    
    num_sheets = solution.num_sheets()
    for sheet_idx in range(num_sheets):
        sheet = solution.sheets[sheet_idx]
        print(f"\n   📄 Sheet {sheet_idx + 1}:")
        print(f"      Placements: {len(sheet.placements)}")
        if sheet.total_cut_length() is not None:
            print(f"      Cut length: {sheet.total_cut_length():,} mm")
        if sheet.waste_area is not None:
            print(f"      Waste area: {sheet.waste_area:,} mm²")
    
    total_cut = solution.total_cut_length()
    total_waste = solution.total_waste_area()
    
    print(f"\n📊 Total Metrics:")
    if total_cut is not None:
        print(f"   Total cut length: {total_cut:,} mm")
    if total_waste is not None:
        print(f"   Total waste area: {total_waste:,} mm²")
    
    print("\n" + "=" * 70)
    print("✓ Success! To visualize the layout, run:")
    print("  python -m dtd_solver.main --example")
    print("=" * 70)
