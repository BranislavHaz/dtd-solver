# dtd_solver/zone_pack_cache.py
# LRU cache for "pack one zone" results.
#
# Why:
# Hybrid2 tries many patterns. Each pattern packs 3 zones with CP-SAT shelves.
# Many patterns repeat the same (zone_w, zone_h) and very similar part-sets.
# Without caching, you re-run CP-SAT hundreds of times => minutes.
# With caching, repeated packs become O(1) => seconds.
#
# Design:
# - Key = (zone_w, zone_h, kerf, signature(parts))
# - signature(parts) is a stable hash of the multiset of (w,h,can_rotate) for the candidate list.
# - Value stores:
#     placements_local  (list[Placement] with sheet_index=0, local coords)
#     placed_uids       (set[str])
#     cuts_local        (list[Cut] local coords)
#
# Note:
# Remaining parts are derived by filtering the passed-in list by placed_uids.
# This avoids storing object references that might not be identical across calls.

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .types import Cut, InstancePart, Placement


@dataclass(frozen=True)
class ZonePackResult:
    placements_local: List[Placement]
    placed_uids: Tuple[str, ...]
    cuts_local: List[Cut]


class ZonePackCache:
    """
    Simple LRU cache (manual) with a hard max size.
    Works well because zone pack results are reusable many times.
    """

    def __init__(self, max_items: int = 256):
        self.max_items = int(max_items)
        self._store: Dict[Tuple[int, int, int, str], ZonePackResult] = {}
        self._order: List[Tuple[int, int, int, str]] = []  # LRU order, oldest first

    @staticmethod
    def signature(parts: List[InstancePart]) -> str:
        """
        Create a stable signature for a multiset of parts, ignoring UID and name,
        because hybrid patterns often pass the same shapes but different instance IDs.
        """
        # Represent each part by sorted dims + rotate flag
        reps = []
        for p in parts:
            a = min(p.w, p.h)
            b = max(p.w, p.h)
            reps.append((a, b, 1 if p.can_rotate else 0))
        reps.sort()

        h = hashlib.blake2b(digest_size=16)
        # Feed bytes deterministically
        for a, b, r in reps:
            h.update(a.to_bytes(2, "little", signed=False))
            h.update(b.to_bytes(2, "little", signed=False))
            h.update(bytes([r]))
        return h.hexdigest()

    def _touch(self, key: Tuple[int, int, int, str]) -> None:
        # Move key to the end (most recently used)
        try:
            idx = self._order.index(key)
            self._order.pop(idx)
        except ValueError:
            pass
        self._order.append(key)

    def get(self, zone_w: int, zone_h: int, kerf: int, parts: List[InstancePart]) -> Optional[ZonePackResult]:
        key = (int(zone_w), int(zone_h), int(kerf), self.signature(parts))
        res = self._store.get(key)
        if res is not None:
            self._touch(key)
        return res

    def put(self, zone_w: int, zone_h: int, kerf: int, parts: List[InstancePart], res: ZonePackResult) -> None:
        key = (int(zone_w), int(zone_h), int(kerf), self.signature(parts))
        if key in self._store:
            self._store[key] = res
            self._touch(key)
            return

        self._store[key] = res
        self._order.append(key)

        # Evict if needed
        while len(self._order) > self.max_items:
            old = self._order.pop(0)
            self._store.pop(old, None)

    def clear(self) -> None:
        self._store.clear()
        self._order.clear()

    def stats(self) -> Tuple[int, int]:
        """
        Returns (items_in_cache, max_items).
        """
        return (len(self._store), self.max_items)
