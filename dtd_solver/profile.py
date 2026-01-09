# dtd_solver/profile.py
# Simple profiling helpers for solver runs.
# Not a full profiler, but enough to understand where time is spent.

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PhaseTimer:
    name: str
    start: float = field(default_factory=time.perf_counter)
    elapsed: float = 0.0

    def stop(self) -> None:
        self.elapsed = time.perf_counter() - self.start


class Profiler:
    def __init__(self) -> None:
        self.phases: Dict[str, PhaseTimer] = {}

    def start(self, name: str) -> None:
        self.phases[name] = PhaseTimer(name=name)

    def stop(self, name: str) -> None:
        if name in self.phases:
            self.phases[name].stop()

    def report(self) -> str:
        lines = ["--- Solver profile ---"]
        total = 0.0
        for name, pt in self.phases.items():
            total += pt.elapsed
            lines.append(f"{name:20s}: {pt.elapsed:8.3f} s")
        lines.append(f"{'TOTAL':20s}: {total:8.3f} s")
        return "\n".join(lines)

