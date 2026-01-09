# dtd_solver/logger.py
# Lightweight logging utilities for the solver.
# Allows you to turn on/off detailed solver diagnostics without polluting stdout.

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class Logger:
    enabled: bool = True
    prefix: str = "[DTD]"

    def info(self, msg: str) -> None:
        if self.enabled:
            print(f"{self.prefix} {msg}", file=sys.stdout)

    def warn(self, msg: str) -> None:
        if self.enabled:
            print(f"{self.prefix} WARNING: {msg}", file=sys.stderr)

    def error(self, msg: str) -> None:
        print(f"{self.prefix} ERROR: {msg}", file=sys.stderr)


# Global default logger
LOGGER = Logger(enabled=True)


def set_enabled(flag: bool) -> None:
    LOGGER.enabled = bool(flag)


def get_logger() -> Logger:
    return LOGGER

