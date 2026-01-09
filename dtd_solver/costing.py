# dtd_solver/costing.py
# Cutting cost utilities:
# - compute per-sheet and total costs from cut lengths
# - supports separate pricing for internal cuts vs trim-charged cuts (optional)
#
# Notes:
# - "internal" cut length comes from SheetResult.cuts (segments produced by solver/postprocess)
# - "trim-charged" length comes from metrics.compute_trim_charged_length (already stored on SheetResult)
# - If your cutting center prices "per mm of cut", this maps directly.
# - If they price per meter, pass price_per_mm = price_per_meter / 1000.

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .types import SheetResult, Solution


@dataclass(frozen=True)
class PriceModel:
    # Base price per mm of cut length (all charged cuts)
    price_per_mm: float

    # Optional different rates
    price_per_mm_internal: Optional[float] = None
    price_per_mm_trim: Optional[float] = None

    # Optional fixed cost per used sheet (handling, setup)
    price_per_sheet: float = 0.0

    # Optional minimum billable cut length per sheet (e.g., 10 meters minimum)
    min_billable_mm_per_sheet: int = 0

    def rate_internal(self) -> float:
        return self.price_per_mm_internal if self.price_per_mm_internal is not None else self.price_per_mm

    def rate_trim(self) -> float:
        return self.price_per_mm_trim if self.price_per_mm_trim is not None else self.price_per_mm


@dataclass(frozen=True)
class SheetCost:
    sheet_index: int
    cut_internal_mm: int
    cut_trim_mm: int
    cut_total_mm: int
    billable_mm: int
    cost_cuts: float
    cost_sheet_fee: float
    cost_total: float


@dataclass(frozen=True)
class SolutionCost:
    sheets: List[SheetCost]
    total_cut_internal_mm: int
    total_cut_trim_mm: int
    total_cut_mm: int
    total_billable_mm: int
    total_cost_cuts: float
    total_cost_sheet_fees: float
    total_cost: float


def _require_metrics(sheet: SheetResult) -> None:
    if sheet.cut_length_internal is None or sheet.cut_length_trim_charged is None:
        raise ValueError(
            f"Sheet {sheet.sheet_index}: metrics not computed. "
            f"Call compute_sheet_metrics(...) before costing."
        )


def compute_sheet_cost(sheet: SheetResult, price: PriceModel) -> SheetCost:
    _require_metrics(sheet)

    internal = int(sheet.cut_length_internal or 0)
    trim = int(sheet.cut_length_trim_charged or 0)
    total = internal + trim

    # Minimum billable length per sheet (if any)
    billable = max(total, int(price.min_billable_mm_per_sheet))

    # If min billable is used, we allocate the extra to internal proportionally for reporting,
    # but charge on total billable (simpler + matches "minimum" billing).
    # Cuts cost is computed using rates on actual components, then add "top-up" at base rate if needed.
    cost_internal = internal * price.rate_internal()
    cost_trim = trim * price.rate_trim()
    cost_cuts = cost_internal + cost_trim

    if billable > total:
        # Top-up at base rate (or you can change this to internal rate)
        cost_cuts += (billable - total) * price.price_per_mm

    cost_sheet_fee = float(price.price_per_sheet)
    cost_total = cost_cuts + cost_sheet_fee

    return SheetCost(
        sheet_index=sheet.sheet_index,
        cut_internal_mm=internal,
        cut_trim_mm=trim,
        cut_total_mm=total,
        billable_mm=billable,
        cost_cuts=cost_cuts,
        cost_sheet_fee=cost_sheet_fee,
        cost_total=cost_total,
    )


def compute_solution_cost(sol: Solution, price: PriceModel) -> SolutionCost:
    sheet_costs: List[SheetCost] = []
    t_int = 0
    t_trim = 0
    t_total = 0
    t_bill = 0
    t_cost_cuts = 0.0
    t_cost_sheet = 0.0

    for sh in sol.sheets:
        sc = compute_sheet_cost(sh, price)
        sheet_costs.append(sc)
        t_int += sc.cut_internal_mm
        t_trim += sc.cut_trim_mm
        t_total += sc.cut_total_mm
        t_bill += sc.billable_mm
        t_cost_cuts += sc.cost_cuts
        t_cost_sheet += sc.cost_sheet_fee

    return SolutionCost(
        sheets=sheet_costs,
        total_cut_internal_mm=t_int,
        total_cut_trim_mm=t_trim,
        total_cut_mm=t_total,
        total_billable_mm=t_bill,
        total_cost_cuts=t_cost_cuts,
        total_cost_sheet_fees=t_cost_sheet,
        total_cost=t_cost_cuts + t_cost_sheet,
    )

