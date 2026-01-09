# dtd_solver/example_end_to_end.py
# End-to-end example script:
# - define board + parts in code (or load CSV via cli.py)
# - run baseline shelves solver
# - validate
# - compute metrics + compute cutting cost
# - show plot
#
# Run:
#   python -m dtd_solver.example_end_to_end

from __future__ import annotations

from dtd_solver.types import BoardSpec, PartSpec, Trim
from dtd_solver.run import run_shelves
from dtd_solver.costing import PriceModel, compute_solution_cost


def main() -> None:
    # Typical DTD board (example)
    board = BoardSpec(
        name="DTD_18",
        raw_w=2800,
        raw_h=2070,
        thickness=18,
        trim=Trim(left=10, right=10, top=10, bottom=10),
    )

    # Example parts (replace with your real list / CSV)
    parts = [
        PartSpec("Vysoka_skrina_bok", 2400, 560, qty=2, can_rotate=False),
        PartSpec("Vysoka_skrina_polica", 560, 500, qty=6, can_rotate=True),
        PartSpec("Mala_skrina_bok", 720, 560, qty=2, can_rotate=False),
        PartSpec("Dvierka", 715, 397, qty=4, can_rotate=False),
        PartSpec("Podstava", 564, 120, qty=6, can_rotate=True),
    ]

    # Run solver (baseline shelves)
    res, fig = run_shelves(
        board,
        parts,
        kerf=3,               # mm
        time_limit_s=10.0,    # seconds per sheet
        max_sheets=20,
        cut_weight=1,         # increase to prioritize fewer/shorter cuts
        shelf_count_weight=0,
        out_dir=None,         # or "out" to export CSVs
        show_plot=True,
    )

    sol = res.solution

    # Pricing model: e.g. 0.003 EUR/mm == 3 EUR/m
    price = PriceModel(
        price_per_mm=0.003,
        # If trim cuts are priced differently, set these:
        # price_per_mm_internal=0.003,
        # price_per_mm_trim=0.003,
        price_per_sheet=0.0,
        min_billable_mm_per_sheet=0,
    )

    cost = compute_solution_cost(sol, price)

    print("\n=== COST SUMMARY ===")
    print(f"Sheets used: {sol.num_sheets()}")
    print(f"Total cut (internal): {cost.total_cut_internal_mm:,} mm")
    print(f"Total cut (trim-charged): {cost.total_cut_trim_mm:,} mm")
    print(f"Total cut (billable): {cost.total_billable_mm:,} mm")
    print(f"Total cost: {cost.total_cost:,.2f}")

    for sc in cost.sheets:
        print(
            f"- Sheet {sc.sheet_index + 1}: cut={sc.cut_total_mm:,} mm "
            f"(internal {sc.cut_internal_mm:,} + trim {sc.cut_trim_mm:,}), "
            f"billable={sc.billable_mm:,} mm, cost={sc.cost_total:,.2f}"
        )

    # Show plot if created
    if fig is not None:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()

