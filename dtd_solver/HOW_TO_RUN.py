#!/usr/bin/env python3
"""
DTD Solver - Dokumentácia a príklady spustenia
===============================================

Tento súbor obsahuje všetko čo potrebuješ vedieť o projekte dtd_solver.

RÝCHLY START
============

1. Aktivuj virtuálne prostredie:
   cd /home/branislav/Dokumenty/pg
   source dtd_solver/venv/bin/activate

2. Spusti príklad:
   python -m dtd_solver.main --example

3. Uvidíš výsledky a graf

PROJEKTOVÉ CIELE
================

dtd_solver optimalizuje rezanie dosiek pre woodworking/DTD projekty.

VSTUP:
  - Veľkosť dosky (napr. 2800x2070 mm)
  - Zoznam dielov s rozmermi (napr. 10x polica 560x500)
  - Parametre rezania (napr. kerf 3.2mm)

VÝSTUP:
  - Počet potrebných dosiek
  - Rozmiestnenie dielov na dosku
  - Dĺžka rezov (minimálne)
  - Veľkosť odpadu

INSTALÁCIA (JUŽ HOTOVO)
=======================

Virtuálne prostredie je v: /home/branislav/Dokumenty/pg/dtd_solver/venv

Ak by si ho potreboval obnoviť:
  cd /home/branislav/Dokumenty/pg
  python3 -m venv dtd_solver/venv
  source dtd_solver/venv/bin/activate
  pip install ortools matplotlib

SPUSTENIE - 5 SPÔSOBOV
======================

1. VSTAVANÉ PRÍKLADY (najjednoduchšie)
   ----
   cd /home/branislav/Dokumenty/pg
   source dtd_solver/venv/bin/activate
   python -m dtd_solver.main --example
   
   Výstup: Počet dosiek, dĺžka rezov, odpad + matplotlib graf

2. S VLASTNÝM CSV SÚBOROM
   ----
   # Vytvor parts.csv:
   name,w,h,qty,can_rotate
   Bok,720,560,2,0
   Polica,564,500,4,1
   
   # Spusti:
   python -m dtd_solver.main --parts parts.csv

3. S VLASTNÝMI PARAMETRAMI
   ----
   python -m dtd_solver.main \
     --example \
     --board 3000x2100 \
     --trim 5,5,5,5 \
     --kerf 4.0 \
     --time 20 \
     --no_labels
   
   Parametre:
     --board WxH           Doska v mm (default: 2800x2070)
     --trim l,r,t,b       Okraje na orez (default: 10,10,10,10)
     --kerf FLOAT         Šírka rezu v mm (default: 3.2)
     --time FLOAT         Čas na riešenie sekundy (default: 10.0)
     --max_sheets INT     Max dosiek (default: 20)
     --cut_weight INT     Penalizácia rezov (default: 1)
     --parts FILE         CSV súbor s dielmi
     --example            Vstavané príklady
     --no_labels          Skryť popisky v grafe
     --no_dims            Skryť rozmery v grafe
     --grid               Zobraziť mriežku

4. Z PYTHON KÓDU (bez matplotlib)
   ----
   import sys
   sys.path.insert(0, '/home/branislav/Dokumenty/pg')
   
   from dtd_solver.types import BoardSpec, PartSpec, Trim
   from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves
   
   board = BoardSpec(
       name="Moja doska",
       raw_w=2800,
       raw_h=2070,
       trim=Trim(10, 10, 10, 10)
   )
   
   parts = [
       PartSpec("Bok", 720, 560, qty=2, can_rotate=False),
       PartSpec("Polica", 564, 500, qty=4, can_rotate=True),
   ]
   
   params = SolverParams(
       kerf=3,
       time_limit_s=10.0,
       max_sheets=20,
       cut_weight=1
   )
   
   solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)
   
   print(f"Dosiek: {solution.num_sheets()}")
   print(f"Rezanie: {solution.total_cut_length()} mm")
   print(f"Odpad: {solution.total_waste_area()} mm²")

5. CLI S CSV EXPORTOM
   ----
   python -m dtd_solver.cli --parts parts.csv --out output/
   
   Vyexportuje podrobné CSV súbory s rozmiestnením na každej doske

PRÍKLADY - ÚPLNÝ KÓD
====================

PRÍKLAD 1: Jednoduchý kus nábytku
----
import sys
sys.path.insert(0, '/home/branislav/Dokumenty/pg')
from dtd_solver.types import BoardSpec, PartSpec, Trim
from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves

board = BoardSpec("DTD", 2800, 2070, trim=Trim(10, 10, 10, 10))

parts = [
    PartSpec("Vysoka_skrina_bok", 2400, 560, qty=2, can_rotate=False),
    PartSpec("Vysoka_skrina_polica", 560, 500, qty=6, can_rotate=True),
    PartSpec("Mala_skrina_bok", 720, 560, qty=2, can_rotate=False),
    PartSpec("Dvierka", 715, 397, qty=4, can_rotate=False),
    PartSpec("Podstava", 564, 120, qty=6, can_rotate=True),
]

params = SolverParams(kerf=3, time_limit_s=10.0)

solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)

print(f"Výsledok: {solution.num_sheets()} dosiek")
print(f"Rezanie: {solution.total_cut_length()} mm")
print(f"Odpad: {solution.total_waste_area()} mm²")

PRÍKLAD 2: Čítanie z CSV
----
from pathlib import Path
from dtd_solver.main import read_parts_csv

# CSV formát: name,w,h,qty,can_rotate
parts = read_parts_csv(Path("parts.csv"))

# Zvyšok rovnaký ako vyššie...

PRÍKLAD 3: Generovanie náhodných dielov
----
from dtd_solver.sample_data import generate_random_parts, RandomPartsConfig

cfg = RandomPartsConfig(
    seed=42,
    n_unique=20,  # 20 druhov dielov
    qty_range=(1, 5),  # 1-5 kusov každého druhu
)

parts = generate_random_parts(cfg)

# Zvyšok rovnaký ako vyššie...

PRÍKLAD 4: Run s exportom
----
from dtd_solver.run import run_shelves
from dtd_solver.types import BoardSpec, PartSpec
from pathlib import Path

board = BoardSpec("DTD", 2800, 2070)
parts = [PartSpec("Item", 100, 200, qty=10)]

result = run_shelves(
    board, parts,
    kerf=3.2,
    time_limit_s=30,
    out_dir=Path("output"),
    export_prefix="solution",
    show_plot=True
)

print(f"Waste area: {result.total_waste_area} mm²")
print(f"Cut length: {result.total_cut_internal} mm (internal)")
print(f"            {result.total_cut_trim_charged} mm (trim-charged)")

ŠTRUKTÚRA PROJEKTU
==================

Dôležité súbory:
  - types.py              : Dátové štruktúry (BoardSpec, PartSpec, Solution)
  - solver_shelf_cp_sat.py : Solver algoritmus (CP-SAT, OR-Tools)
  - main.py               : CLI s matplotlib grafom
  - cli.py                : CLI s CSV exportom
  - run.py                : High-level runner
  - metrics.py            : Výpočty (rezanie, odpad)
  - plotting.py           : Matplotlib vizualizácia
  - validate.py           : Validácia riešení

Pomocné súbory:
  - sample_data.py        : Generovanie testovacích dát
  - io_csv.py             : CSV import/export
  - config.py             : Konfigurácia
  - utils.py              : Pomocné funkcie

Virtuálne prostredie:
  - venv/                 : Všetky balíčky (ortools, matplotlib)

Dokumentácia:
  - QUICK_START.md        : Rýchly start (ČÍTAJ TOTO!)
  - SETUP_GUIDE.md        : Detailný návod
  - README_DEV.md         : Dev poznámky

ALGORITMUS - AKO TO FUNGUJE?
============================

1. VSTUP
   - Doska (veľkosť, trim, hrúbka)
   - Diely (rozmer, počet, či sa dá rotovať)
   - Parametre (kerf, čas na riešenie)

2. TRANSFORMÁCIA
   - Vypočítaj usable plochu (doska - trim)
   - Pre každy diely cyklus:
     - Výber do shelf, čo sa zmestí
     - Ľavej orientácii: w, h
     - Spravej: ak je can_rotate, skúsi (h, w)

3. OPTIMALIZÁCIA (CP-SAT)
   - Shelf-based model (horizontálne pásy)
   - Priradenie dielov na políce
   - X pozícia v police (kerf spacing)
   - Minimalizácia: -(used_area) + (cut_length_penalty)

4. ITERÁCIA
   - Riešia sa postupne dosky
   - Ak sa všetko nezmestí: ďalšia doska
   - Dokým nie sú všetky diely umiestnené

5. VÝSTUP
   - Umiestnenia (x, y, w, h orientácia)
   - Rezové čiary (horizontálne, vertikálne)
   - Metriky: rezanie, odpad

PARAMETRY SOLVEROM
==================

SolverParams:
  kerf=3                   # Šírka rezu v mm
  time_limit_s=10.0        # Čas na riešenie (sekundy)
  max_sheets=50            # Maximálne dosky
  cut_weight=1             # Penalizácia rezov (tuning)
  max_shelves=None         # Max políc (auto: len(parts))
  shelf_count_weight=0     # Penalizácia počtu políc

OTÁZKY & ODPOVEDE
=================

Q: Ako nainštalujem virtálne prostredie nanovo?
A: cd /home/branislav/Dokumenty/pg
   python3 -m venv dtd_solver/venv
   source dtd_solver/venv/bin/activate
   pip install ortools matplotlib

Q: Prečo musím spúšťať z /home/branislav/Dokumenty/pg ?
A: Projekt má types.py ktorý konfliktuje so Python štandardným modulom.
   Spustenie z rodičovského adresára izoluje tento konflikt.

Q: Ako zmeníš parametre dosky?
A: python -m dtd_solver.main \
     --board 3000x2100 \
     --trim 5,5,5,5 \
     --kerf 4.0

Q: Ako exportujem výsledky do CSV?
A: python -m dtd_solver.cli --parts parts.csv --out output_dir/

Q: Ako riešim bez matplotlib grafa?
A: Použij Python API priamo (príklady vyššie)
   Alebo cli.py s --out parametrom

Q: Čo znamenajú metriky?
A: - Used sheets: Koľko dosiek potrebuješ
   - Cut length: Dĺžka rezov v mm
   - Waste area: Nepoužitá plocha v mm²

ZNÁME PROBLÉMY & RIEŠENIA
========================

1. "ImportError: cannot import name 'MappingProxyType' from types"
   RIEŠENIE: Spusti z /home/branislav/Dokumenty/pg (nie z dtd_solver/)

2. "ModuleNotFoundError: No module named 'ortools'"
   RIEŠENIE: Aktivuj venv: source dtd_solver/venv/bin/activate

3. Matplotlib otvorí okno a zablokuje terminal
   RIEŠENIE: Zavri okno a proces sa ukončí. Ak chceš bez grafa,
   použi Python API (bez matplotlib).

BUDÚCNE VYLEPŠENIA
==================

Plánované zmeny:
  - 3-stage hybrid guillotine tree (ako konkurencia)
  - Presné výpočty rezania z cut tree
  - PDF export
  - Web API
  - Paralelizácia solverom
  - Heuristics pre veľké problémy

KONTAKT & POMOC
===============

- Dokumentácia: Všetky .py súbory majú docstrings
- Príklady: example_end_to_end.py, sample_data.py
- Dev notes: README_DEV.md
- Quick start: QUICK_START.md
- Setup guide: SETUP_GUIDE.md

POĎAKOVANIE
===========

Projekt je napísaný v Python s:
  - Google OR-Tools (CP-SAT solver)
  - Matplotlib (vizualizácia)
  - Python 3.12

LICENCIA
========

Prevádza sa bez explicitnej licencie. Môžeš ho používať a modifikovať
na svoje potreby.

---

Tešime sa, že ti projekt funguje! 🎉

Ak máš otázky, najskôr si prečítaj QUICK_START.md.
Ak potrebuješ viac detailov, skúmaj SETUP_GUIDE.md.
"""

# Aby sa tento súbor dal spustiť aj ako Python skript:
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/branislav/Dokumenty/pg')
    
    print(__doc__)
    
    print("\n" + "="*70)
    print("SKÚŠAM SOLVER...")
    print("="*70 + "\n")
    
    from dtd_solver.types import BoardSpec, PartSpec, Trim
    from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves
    
    board = BoardSpec("DTD", 2800, 2070, trim=Trim(10, 10, 10, 10))
    parts = [
        PartSpec("Bok", 720, 560, qty=2, can_rotate=False),
        PartSpec("Polica", 564, 500, qty=4, can_rotate=True),
    ]
    
    print("📋 Vstup:")
    print(f"   Doska: {board.raw_w}x{board.raw_h} mm (usable: {board.usable_w}x{board.usable_h})")
    print(f"   Diely: {len(parts)} typov, {sum(p.qty for p in parts)} kusov")
    
    params = SolverParams(kerf=3, time_limit_s=10.0)
    print(f"\n⚙️  Solver spúšťam... (kerf={params.kerf}, time={params.time_limit_s}s)")
    
    solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)
    
    print(f"\n✅ Výsledok:")
    print(f"   Dosiek: {solution.num_sheets()}")
    print(f"   Rezanie: {solution.total_cut_length()} mm")
    print(f"   Odpad: {solution.total_waste_area()} mm²")
    
    print("\n" + "="*70)
    print("🎉 Gratulujeme! Projekt funguje správne!")
    print("="*70)
