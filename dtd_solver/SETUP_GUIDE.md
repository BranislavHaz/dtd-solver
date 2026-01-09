# DTD Solver - Príručka spustenia

## 📋 Popis projektu

**dtd_solver** je Python projekt na optimalizáciu rezania dosiek pre woodworking/DTD (drevotriesku). Projekt implementuje:

- **Baseline CP-SAT solver** - 2-stage guillotine packing algoritmom (police-based packing)
- **Support pre rotáciu dielov** - selektívne rotácie podľa potreby
- **Optimalizácia rezov** - minimalizácia dĺžky rezov
- **Matplotlib vizualizácia** - grafické zobrazenie rozmiestnenia dielov na dosiek

## 🛠️ Požiadavky

- **Python 3.12+**
- **pip** (Python package manager)
- Nainštalované knižnice: `ortools`, `matplotlib`

## 📦 Inštalácia

### 1. Vytvorenie virtuálneho prostredia

```bash
cd /home/branislav/Dokumenty/pg
python3 -m venv dtd_solver/venv
```

### 2. Aktivácia virtuálneho prostredia

```bash
source dtd_solver/venv/bin/activate
```

### 3. Inštalácia závislostí

```bash
cd dtd_solver
pip install ortools matplotlib
```

## 🚀 Spustenie

### Spustenie s vstavanými príkladmi

Všetci príkazy MUSIA byť spustené z rodičovského adresára (`/home/branislav/Dokumenty/pg`) kvôli konfliktom s názvom modulu `types.py`:

```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --example
```

Dostanete výstup ako:
```
Used sheets: 2
Total cut length (internal + trim-charged): 12345 mm
Total waste area: 56789 mm²
```

A otvorí sa grafické okno s vizualizáciou rezania.

### Spustenie s CSV súborom

Vytvorte CSV súbor `parts.csv` vo formáte:
```csv
name,w,h,qty,can_rotate
Bok,720,560,2,0
Polica,564,500,4,1
Dvierka,715,397,4,0
```

Potom spustite:
```bash
python -m dtd_solver.main --parts parts.csv --board 2800x2070 --trim 10,10,10,10 --kerf 3.2
```

### Dostupné argumenty

```bash
python -m dtd_solver.main --help
```

Kľúčové parametre:
- `--board WxH` - Veľkosť dosky (mm), default: 2800x2070
- `--trim l,r,t,b` - Okraje na orez (ľavo,vpravo,hore,dole) v mm, default: 10,10,10,10
- `--kerf FLOAT` - Šírka rezu (mm), default: 3.2
- `--time FLOAT` - Limit na riešenie v sekundách, default: 10.0
- `--parts FILE` - Cesta k CSV súboru s dielmi
- `--example` - Použiť vstavané príklady
- `--no_labels` - Skryť popisky v grafe
- `--no_dims` - Skryť rozmery v grafe
- `--grid` - Zobraziť mriežku v grafe

## 📂 Štruktúra projektu

```
dtd_solver/
├── __init__.py              # Package inicializácia
├── main.py                  # Hlavný vstupný bod (CLI)
├── cli.py                   # Alternatívny CLI s CSV exportom
├── types.py                 # Dátové štruktúry
├── solver_shelf_cp_sat.py   # CP-SAT solver (Google OR-Tools)
├── metrics.py               # Výpočet metrik (rezanie, odpad)
├── plotting.py              # Matplotlib vizualizácia
├── run.py                   # High-level runner
├── io_csv.py                # CSV import/export
├── validate.py              # Validácia riešení
├── utils.py                 # Pomocné funkcie
├── sample_data.py           # Generovanie testovacích dát
├── config.py                # Konfigurácia
└── venv/                    # Virtuálne prostredie
```

## 🔧 Príklad kódu z Pythonu

```python
from dtd_solver.types import BoardSpec, PartSpec, Trim
from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves

# Vytvor dosku
board = BoardSpec(
    name="Standardna DTD",
    raw_w=2800,
    raw_h=2070,
    trim=Trim(10, 10, 10, 10)
)

# Vytvor diely
parts = [
    PartSpec("Bok", 720, 560, qty=2, can_rotate=False),
    PartSpec("Polica", 564, 500, qty=4, can_rotate=True),
]

# Vytvor solver parametre
params = SolverParams(
    kerf=3,
    time_limit_s=10.0,
    max_sheets=20,
)

# Vyriešiš problém
solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)

# Vypíš výsledky
print(f"Počet dosiek: {solution.num_sheets()}")
print(f"Dĺžka rezania: {solution.total_cut_length()} mm")
print(f"Odpad: {solution.total_waste_area()} mm²")
```

## ⚠️ Známe problémy

### 1. Konflikt modulu `types.py`
Projekt má svoj súbor `types.py`, ktorý konfliktuje so Python štandardným modulom. 
**Riešenie:** Vždy spúšťajte z rodičovského adresára `/home/branislav/Dokumenty/pg`.

### 2. Matplotlib v CLI
Keď spustíte `python -m dtd_solver.main`, otvorí sa interaktívne matplotlib okno. 
Ak chcete bez vizualizácie, použite `run.py` s `show_plot=False`.

## 📝 Aktuálny stav projektu

- ✅ **Základný solver** - 2-stage shelf packing s CP-SAT
- ✅ **Vizualizácia** - Matplotlib grafy
- ✅ **CSV support** - Import/export dielov
- 🔄 **Plánované**: Hybrid 3-stage guillotine tree solver

## 🐛 Debugging

Ak chcete vidieť viac detalov:

```bash
# Spustite s detailným výstupom
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from dtd_solver.main import main
main(['--example'])
"
```

## 📞 Ďalšia pomoc

Všetky moduly majú docstrings. Skúste:
```bash
python -c "import dtd_solver; help(dtd_solver.solve_from_partspecs_iterative_shelves)"
```
