# 🚀 DTD Solver - Úplný sprievodca spustením

## ✅ Status: Projekt je spustiteľný a funguje!

Projekt **dtd_solver** je teraz plne funkčný. Nižšie nájdeš všetko, čo potrebuješ vedieť na spustenie a prácu s ním.

---

## 📋 Rýchly start (3 kroky)

### 1️⃣ Aktivuj virtuálne prostredie
```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
```

### 2️⃣ Spusti príklad
```bash
python -m dtd_solver.main --example
```

### 3️⃣ Uvidíš výsledok
```
Used sheets: 2
Total cut length (internal + trim-charged): 12,880 mm
Total waste area: 7,030,000 mm²
```
A otvorí sa **matplotlib okno** s vizualizáciou rezov.

---

## 📚 Čo je to dtd_solver?

**dtd_solver** je Python riešiteľ optimalizácie rezania dosiek (DTD - drevotrieskové dosky) pre woodworking projekty. Pomáha:

✅ **Minimalizovať odpad** - optimálne rozmiestnenie dielov na dosku  
✅ **Počítať rezanie** - odhad dĺžky rezov  
✅ **Vizualizovať** - grafické zobrazenie rozmiestnenia  
✅ **Rotovať diely** - selektívne rotácie podľa potreby  

### Algoritmus
- **CP-SAT solver** (Google OR-Tools)
- **2-stage shelf packing** - horizontálne police, v každej police umiestnenie zľava doprava
- Plánované: 3-stage hybrid guillotine tree

---

## 🛠️ Inštalácia (už hotovo ✓)

Virtuálne prostredie je už vytvorené v:
```
/home/branislav/Dokumenty/pg/dtd_solver/venv/
```

Ak by si ho potreboval obnoviť:
```bash
cd /home/branislav/Dokumenty/pg
python3 -m venv dtd_solver/venv
source dtd_solver/venv/bin/activate
cd dtd_solver
pip install ortools matplotlib
```

---

## 🎯 Spustenie - 5 spôsobov

### 📌 **Spôsob 1: Vstavané príklady (najjednoduchšie)**
```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --example
```
✅ Spustí fixné príklady a ukáže graf

---

### 📌 **Spôsob 2: S vlastným CSV súborom**

Vytvor `parts.csv`:
```csv
name,w,h,qty,can_rotate
Bok,720,560,2,0
Polica,564,500,4,1
Dvierka,715,397,4,0
Podstava,564,120,6,1
```

Potom spusti:
```bash
python -m dtd_solver.main --parts parts.csv --board 2800x2070 --trim 10,10,10,10 --kerf 3.2
```

---

### 📌 **Spôsob 3: Z Python kódu (bez matplotlib)**

```python
import sys
sys.path.insert(0, '/home/branislav/Dokumenty/pg')

from dtd_solver.types import BoardSpec, PartSpec, Trim
from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves

# Doska
board = BoardSpec(
    name="Standard",
    raw_w=2800,
    raw_h=2070,
    trim=Trim(10, 10, 10, 10)
)

# Diely
parts = [
    PartSpec("Bok", 720, 560, qty=2, can_rotate=False),
    PartSpec("Polica", 564, 500, qty=4, can_rotate=True),
]

# Riešiť
params = SolverParams(kerf=3, time_limit_s=10.0)
solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)

# Výsledky
print(f"Dosiek: {solution.num_sheets()}")
print(f"Rezanie: {solution.total_cut_length()} mm")
print(f"Odpad: {solution.total_waste_area()} mm²")
```

---

### 📌 **Spôsob 4: CLI s CSV exportom**

```bash
python -m dtd_solver.cli --parts parts.csv --out output_dir/
```
Vyexportuje CSV súbory s detailmi každého listu.

---

### 📌 **Spôsob 5: Priamo zo zdrojového skriptu**

```bash
python dtd_solver/example_simple.py
```
Jednoduchý skript bez matplotlib zobrazenia.

---

## ⚙️ Parametre príkazového riadka

```bash
python -m dtd_solver.main --help
```

Najdôležitejšie:
| Parameter | Default | Popis |
|-----------|---------|-------|
| `--board WxH` | 2800x2070 | Veľkosť dosky v mm |
| `--trim l,r,t,b` | 10,10,10,10 | Okraje na orez (mm) |
| `--kerf FLOAT` | 3.2 | Šírka rezu (mm) |
| `--time FLOAT` | 10.0 | Čas na riešenie (sekundy) |
| `--parts FILE` | - | CSV súbor s dielmi |
| `--example` | - | Použiť vstavané príklady |
| `--no_labels` | - | Skryť popisky v grafe |
| `--no_dims` | - | Skryť rozmery v grafe |
| `--grid` | - | Zobrazovať mriežku |

---

## 📁 Štruktúra projektu

```
dtd_solver/
├── __init__.py                 # Export verejného API
├── main.py                     # CLI s matplotlib
├── cli.py                      # CLI s CSV exportom
├── example_simple.py           # Jednoduchý príklad (nový)
├── example_end_to_end.py       # Komplexný príklad
│
├── types.py                    # Dátové štruktúry (Board, Part, Placement)
├── solver_shelf_cp_sat.py      # Solver algoritmus (OR-Tools)
├── metrics.py                  # Výpočty (rezanie, odpad)
├── plotting.py                 # Matplotlib vizualizácia
├── run.py                      # High-level runner
├── validate.py                 # Validácia riešení
├── io_csv.py                   # CSV I/O
│
├── sample_data.py              # Generovanie testovacích dát
├── debug.py                    # Debugovanie
├── profile.py                  # Profiling výkonu
│
├── config.py                   # Konfigurácia
├── utils.py                    # Pomocné funkcie
├── compat_packingsolver.py     # Kompatibilita s iným solverom
├── roadmap.py                  # Plán rozvoja
│
├── venv/                       # Virtuálne prostredie ✓
├── README_DEV.md               # Dev poznámky (staré)
├── SETUP_GUIDE.md              # Komplexný návod (nový)
└── .gitignore
```

---

## 🐛 Opravy a zmeny

V tomto reláze bola opravená chyba v `solver_shelf_cp_sat.py`:
- **Problem**: NewOptionalIntervalVar API v novšej verzii ortools (9.14) vyžaduje "affine" (lineárne) výrazy
- **Riešenie**: Pre-kalkulácia `inflated_w` ako IntVar pred použitím v intervaloch
- **Súbor**: [solver_shelf_cp_sat.py](solver_shelf_cp_sat.py#L165-L190)

---

## 💡 Príklady použitia

### Príklad 1: Jednoduchý kus nábytku
```bash
python -m dtd_solver.main \
  --example \
  --board 2800x2070 \
  --trim 10,10,10,10 \
  --kerf 3.2 \
  --time 20
```

### Príklad 2: Vlastný projekt
```bash
# Vytvor parts.csv
cat > parts.csv << EOF
name,w,h,qty,can_rotate
Skrina_bok,2400,560,2,0
Skrina_polica,560,500,6,1
Mensie_dvierka,400,400,4,0
EOF

# Spusti solver
python -m dtd_solver.main \
  --parts parts.csv \
  --board 2800x2070 \
  --kerf 3.0 \
  --cut_weight 2
```

### Príklad 3: Vrstvenie v Python kóde
```python
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
    show_plot=True
)
```

---

## 🔍 Ako to funguje?

1. **Načítaj vstupy** - doska a zoznam dielov
2. **Spusti optimizátor** - OR-Tools CP-SAT solver
   - Priradi diely na police (shelf = horizontálny pás)
   - V každej police rozmiesť zľava doprava
   - Zvážovať rotácie
3. **Vypočítaj metriky**
   - Vnútorné rezanie (horizontálne a vertikálne)
   - Odsúčasťovanie kde diely dotýkajú okrajov
   - Odpad (nepoužitá plocha)
4. **Vizualizuj** - matplotlib zobrazenie
5. **Exportuj** - CSV alebo print výstupy

---

## ⚠️ Poznámky a limitácie

### Virtuálne prostredie
- Vždy aktivuj: `source dtd_solver/venv/bin/activate`
- Spúšťaj z rodičovského adresára: `/home/branislav/Dokumenty/pg`
- Je to kvôli `types.py` konfliktu so štandardným Python modulom

### Matplotlib
- `--example` otvorí interaktívne okno
- Nezavieraj terminal kým máš okno otvorené
- Ak chceš len výsledky bez grafu, použij Python API priamo

### Solver
- Rieši sa iteratívne - jedna doska za raz
- Čas riešenia: `--time` sekundy na dosku
- Maximálne dosky: `--max_sheets` (safety cap)

### Aktuálny algoritmus
- 2-stage shelf packing (nie 3-stage)
- Aproximácia vnútorného rezania
- Presné rezanie okrajov

### Budúce vylepšenia
- 3-stage hybrid guillotine tree
- Presné výpočty rezania
- PDF export

---

## 🎓 Čítaj ďalej

```bash
# Dokumentácia modulov
python -c "import dtd_solver; help(dtd_solver)"

# Príklady v kóde
cat example_end_to_end.py
cat sample_data.py

# Vývojové poznámky
cat README_DEV.md
```

---

## ✨ Zhrnutie - Ako rozbehneš projekt

**Rýchlo:**
```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --example
```

**So svojimi dielmi:**
```bash
# Vytvor CSV
echo "name,w,h,qty,can_rotate" > parts.csv
echo "Diely,100,200,10,1" >> parts.csv

# Spusti solver
python -m dtd_solver.main --parts parts.csv
```

**V Python kóde:**
```python
from dtd_solver.types import BoardSpec, PartSpec
from dtd_solver.solver_shelf_cp_sat import solve_from_partspecs_iterative_shelves, SolverParams

board = BoardSpec("DTD", 2800, 2070)
parts = [PartSpec("Item", 100, 200, qty=10)]
sol = solve_from_partspecs_iterative_shelves(board, parts, params=SolverParams())
print(f"Sheets: {sol.num_sheets()}")
```

---

**Tešime sa, že ti projekt funguje!** 🎉

Ak máš ďalšie otázky, prečítaj si [SETUP_GUIDE.md](SETUP_GUIDE.md) alebo skúmaj dokumentáciu v kóde.
