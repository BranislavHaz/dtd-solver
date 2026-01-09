# dtd_solver/roadmap.py
# Project roadmap and TODOs as executable comments.
# (Kept as a .py so it stays in the same "python files only" workflow.)

"""
ROADMAP – What remains to reach "competitor-level" hybrid nesting.

CURRENT:
- Shelf CP-SAT solver (2-stage guillotine-ish)
- Exact trim-charged cut length
- Internal cut length from generated cut segments
- Visualization + costing + CSV export

NEXT MAJOR STEP:
Implement HybridGuillotinePlanner (solver_hybrid_tree_stub.py)

Key features to add:

1) Mixed-orientation guillotine tree
   - Node variables: orientation ∈ {H, V}, cut position
   - Tree depth ~3–5 (configurable)
   - Leaves represent either:
       a) one part
       b) empty waste

2) Part assignment
   - Each part must map to exactly one leaf
   - Leaf rectangle dims must match part dims (with rotation allowed)

3) Kerf
   - When node splits into a+b, require:
       a.rect.w + b.rect.w + kerf <= parent.rect.w   (for V)
       a.rect.h + b.rect.h + kerf <= parent.rect.h   (for H)

4) Objective
   Lexicographic:
     - minimize number of sheets
     - minimize waste area
     - minimize exact internal cut length (tree-based)
     - minimize trim-charged length

5) Multiple sheets
   - Iterate tree solver per sheet (like shelves version)
   - Or build a multi-sheet tree forest

6) Grain / decor constraints
   - Use per-part can_rotate
   - Later: enforce consistent grain direction per subtree if needed

7) Speed control
   - Limit nodes (max_nodes)
   - Fix some orientations early
   - Use symmetry breaking:
       * force first cut orientation
       * force cut positions ordering

This hybrid-tree CP-SAT is ~10–20× more complex than shelves,
but it is exactly what your competitor is doing.
"""

