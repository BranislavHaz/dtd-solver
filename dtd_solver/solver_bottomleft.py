# dtd_solver/solver_bottomleft.py
# Bottom-Left (BL) heuristic for 2D bin packing
# Places parts as low and left as possible, producing better layouts than shelves

from __future__ import annotations

from typing import List, Optional, Tuple
from .types import BoardSpec, InstancePart, Placement, SheetResult, Solution, Cut


def solve_bottomleft(
    board: BoardSpec,
    parts: List[InstancePart],
    kerf: int = 4,
    max_sheets: int = 50,
) -> Solution:
    """
    Bottom-Left (BL) heuristic: places parts as low as possible, then as left as possible.
    This typically produces layouts with fewer cuts than shelf-based packing.
    
    Parts should be pre-sorted (largest first recommended).
    """
    
    sol = Solution(board=board, sheets=[])
    W, H = board.usable_w, board.usable_h
    
    remaining = list(parts)
    sheet_idx = 0
    
    while remaining and sheet_idx < max_sheets:
        # Start new sheet
        placements: List[Placement] = []
        occupied = []  # List of (x, y, w, h) rectangles already placed
        
        # Try to place each part
        unplaced = []
        for part in remaining:
            # Try both orientations if rotatable
            orientations = []
            if part.can_rotate:
                orientations = [(part.w, part.h), (part.h, part.w)]
            else:
                orientations = [(part.w, part.h)]
            
            placed = False
            best_y = float('inf')
            best_x = float('inf')
            best_w, best_h = 0, 0
            
            for w, h in orientations:
                # Find bottom-left position for this orientation
                pos_x, pos_y = _find_bottomleft_position(occupied, W, H, w, h, kerf)
                
                if pos_x is not None and pos_y is not None:
                    # Check if this is better (lower, then more left)
                    if pos_y < best_y or (pos_y == best_y and pos_x < best_x):
                        best_y = pos_y
                        best_x = pos_x
                        best_w, best_h = w, h
                        placed = True
            
            if placed and best_y < H:
                # Place the part
                pl = Placement(
                    part_uid=part.uid,
                    x=best_x,
                    y=best_y,
                    w=best_w,
                    h=best_h,
                    rotated=(best_w, best_h) != (part.w, part.h)
                )
                placements.append(pl)
                occupied.append((best_x, best_y, best_w, best_h))
            else:
                unplaced.append(part)
        
        # Create sheet with placements
        sheet = SheetResult(
            sheet_index=sheet_idx,
            board=board,
            placements=placements,
            cuts=[]  # TODO: generate cuts
        )
        sol.sheets.append(sheet)
        
        remaining = unplaced
        sheet_idx += 1
    
    return sol


def _find_bottomleft_position(
    occupied: List[Tuple[int, int, int, int]],
    W: int,
    H: int,
    w: int,
    h: int,
    kerf: int,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Find bottom-left position for a rectangle (w, h) in bin (W, H).
    Returns (x, y) or (None, None) if doesn't fit.
    """
    
    if w > W or h > H:
        return None, None
    
    # Try positions from bottom-left
    # Generate candidate positions based on existing placements
    candidates = [(0, 0)]  # Always try bottom-left corner
    
    for ox, oy, ow, oh in occupied:
        # Try to place to the right of this placement
        candidates.append((ox + ow + kerf, oy))
        # Try to place above this placement
        candidates.append((ox, oy + oh + kerf))
    
    # Sort candidates by (y, x) to prioritize bottom, then left
    candidates.sort(key=lambda p: (p[1], p[0]))
    
    for x, y in candidates:
        # Check if part fits at (x, y)
        if x + w <= W and y + h <= H:
            # Check no overlap with occupied
            if not _overlaps(x, y, w, h, occupied, kerf):
                return x, y
    
    return None, None


def _overlaps(
    x: int,
    y: int,
    w: int,
    h: int,
    occupied: List[Tuple[int, int, int, int]],
    kerf: int,
) -> bool:
    """Check if rectangle (x, y, w, h) overlaps with any occupied rectangle."""
    for ox, oy, ow, oh in occupied:
        # Rectangles overlap if they don't satisfy any of the four separation conditions
        if not (
            x + w + kerf <= ox or      # new is to the left
            ox + ow + kerf <= x or      # new is to the right
            y + h + kerf <= oy or      # new is below
            oy + oh + kerf <= y        # new is above
        ):
            return True
    return False
