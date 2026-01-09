# dtd_solver/tests_smoke.py
# Very small smoke tests you can run with:
#   python -m dtd_solver.tests_smoke
#
# These are not full unit tests, but they quickly tell you if
# the solver, metrics and plotting are wired correctly.

from __future__ import annotations

from dtd_solver.types import BoardSpec, PartSpec, Trim
from dtd_solver.run import run_shelves
from dtd_solver.validate import validate_solution, raise_on_errors


def test_basic_fit() -> None:
    board = BoardSpec(
        name="DTD",
        raw_w=2800,
        raw_h=2070,
        trim=Trim(10, 10, 10, 10),
    )

    parts = [
        PartSpec("A", 500, 500, qty=4, can_rotate=True),
        PartSpec("B", 1000, 400, qty=2, can_rotate=False),
    ]

    res, _ = run_shelves(board, parts, kerf=3, time_limit_s=5, show_plot=False)
    sol = res.solution

    issues = validate_solution(sol)
    raise_on_errors(issues)

    assert sol.num_sheets() >= 1
    assert res.total_cut is not None
    assert res.total_cut > 0


def test_rotation_respected() -> None:
    board = BoardSpec(
        name="DTD",
        raw_w=2000,
        raw_h=1200,
        trim=Trim(0, 0, 0, 0),
    )

    # Tall piece that only fits if rotated, but rotation is forbidden
    parts = [
        PartSpec("Tall", 1300, 900, qty=1, can_rotate=False),
    ]

    res, _ = run_shelves(board, parts, kerf=3, time_limit_s=5, show_plot=False)
    sol = res.solution

    # Should not place it, because it does not fit without rotation
    if sol.sheets:
        assert len(sol.sheets[0].placements) == 0


def main() -> None:
    print("Running smoke tests...")
    test_basic_fit()
    test_rotation_respected()
    print("OK")


if __name__ == "__main__":
    main()

