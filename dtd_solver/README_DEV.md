# dtd_solver/README_DEV.md
# (Plain markdown stored as .md, but you asked for "python súbory" each turn earlier.
# If you strictly want only .py files, skip this. Otherwise keep it as a dev note.)

"""
DEVELOPER NOTES (baseline)

Folder suggestion:
  dtd_solver/
    __init__.py
    types.py
    metrics.py
    plotting.py
    solver_shelf_cp_sat.py
    main.py

Run quick demo:
  python -m dtd_solver.main --example

Run with CSV:
  python -m dtd_solver.main --board 2800x2070 --trim 10,10,10,10 --kerf 3.2 --parts parts.csv

Parts CSV format:
  name,w,h,qty,can_rotate

Key metrics:
- internal cut length: derived from generated Cut segments (shelf-based)
- trim charged length: sum of border contact lengths (only where parts touch usable border)

IMPORTANT LIMITATION (current solver):
- This is 2-stage shelf packing, not the hybrid guillotine tree visible in your competitor plan.
- It is a stable base: we can replace solver_shelf_cp_sat.py with a hybrid-tree CP-SAT/MIP model later
  while keeping types/metrics/plotting intact.
"""

