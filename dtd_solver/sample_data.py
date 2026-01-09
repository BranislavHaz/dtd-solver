# dtd_solver/sample_data.py
# Utilities to generate sample / random part lists for quick benchmarking and tuning.
# This helps you stress-test cut length vs waste trade-offs without needing real CSVs.

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .types import PartSpec


@dataclass(frozen=True)
class RandomPartsConfig:
    seed: int = 123
    n_unique: int = 25
    qty_range: Tuple[int, int] = (1, 4)

    # size ranges (mm)
    w_range: Tuple[int, int] = (80, 900)
    h_range: Tuple[int, int] = (80, 2400)

    # probability a part is NOT rotatable (grain constraint)
    p_no_rotate: float = 0.35

    # probability a part is "tall" (like cabinet sides)
    p_tall: float = 0.20
    tall_h_range: Tuple[int, int] = (1800, 2600)
    tall_w_range: Tuple[int, int] = (300, 650)

    # probability a part is "strip" (plinths / rails)
    p_strip: float = 0.15
    strip_h_range: Tuple[int, int] = (60, 180)
    strip_w_range: Tuple[int, int] = (400, 1200)


def generate_random_parts(cfg: RandomPartsConfig) -> List[PartSpec]:
    """
    Generate a list of PartSpec with qty, sizes and rotation constraints.
    Designed to resemble DTD job mixes: some tall sides, some strips, some random shelves/doors.
    """
    rnd = random.Random(cfg.seed)
    parts: List[PartSpec] = []

    for i in range(cfg.n_unique):
        r = rnd.random()

        if r < cfg.p_tall:
            w = rnd.randint(*cfg.tall_w_range)
            h = rnd.randint(*cfg.tall_h_range)
        elif r < cfg.p_tall + cfg.p_strip:
            w = rnd.randint(*cfg.strip_w_range)
            h = rnd.randint(*cfg.strip_h_range)
            # sometimes long strips are actually rotated; keep can_rotate likely true
        else:
            w = rnd.randint(*cfg.w_range)
            h = rnd.randint(*cfg.h_range)

        qty = rnd.randint(*cfg.qty_range)
        can_rotate = rnd.random() > cfg.p_no_rotate

        parts.append(
            PartSpec(
                name=f"P{i+1:02d}",
                w=int(w),
                h=int(h),
                qty=int(qty),
                can_rotate=bool(can_rotate),
            )
        )

    return parts


def scale_parts(parts: List[PartSpec], factor: float) -> List[PartSpec]:
    """
    Uniformly scale all dimensions by factor (useful for quick sensitivity tests).
    """
    out: List[PartSpec] = []
    for p in parts:
        out.append(
            PartSpec(
                name=p.name,
                w=max(1, int(round(p.w * factor))),
                h=max(1, int(round(p.h * factor))),
                qty=p.qty,
                can_rotate=p.can_rotate,
                meta=dict(p.meta),
            )
        )
    return out


def add_job_prefix(parts: List[PartSpec], prefix: str) -> List[PartSpec]:
    """
    Rename parts as "{prefix}_{name}" (useful if you merge multiple jobs).
    """
    return [
        PartSpec(
            name=f"{prefix}_{p.name}",
            w=p.w,
            h=p.h,
            qty=p.qty,
            can_rotate=p.can_rotate,
            meta=dict(p.meta),
        )
        for p in parts
    ]


def merge_parts(*part_lists: List[PartSpec]) -> List[PartSpec]:
    """
    Merge lists; if names collide, keeps them separate (does not aggregate).
    """
    out: List[PartSpec] = []
    for lst in part_lists:
        out.extend(lst)
    return out

