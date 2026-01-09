# 🚀 DTD Solver - Úplný Sprievodca

## ✅ Stav: Projekt je plne funkčný a spustiteľný!

Gratulujem! Projekt **dtd_solver** je teraz kompletne nainštalovaný a spustiteľný.

---

## 📋 RÝCHLY START (30 sekúnd)

### Krok 1: Aktivuj virtuálne prostredie
```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
```

### Krok 2: Spusti príklad
```bash
python -m dtd_solver.main --example
```

### Krok 3: Uvidíš výsledky
```
Used sheets: 2
Total cut length (internal + trim-charged): 12,880 mm
Total waste area: 7,030,000 mm²
```

✨ Otvorí sa aj **matplotlib okno** s grafickou vizualizáciou rezov!

---

## 🎯 Čo je dtd_solver?

**Optimalizátor rezania dosiek** pre woodworking/DTD (drevotrieskové dosky) projekty.

**Vstup:**
- 📏 Veľkosť dosky (napr. 2800×2070 mm)
- 📦 Zoznam dielov s rozmermi (napr. 10× polica 560×500 mm)
- ⚙️ Parametre rezania (kerf, trim, čas)

**Výstup:**
- 📊 Počet potrebných dosiek
- 🔪 Dĺžka rezov (minimalizovaná)
- 📐 Rozmiestnenie dielov na doske
- 🗑️ Veľkosť odpadu

---

## 🚀 Spustenie - Jednotlivé Spôsoby

### 1️⃣ Spôsob: Vstavané Príklady (Najjednoduchšie!)

```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --example
```

✅ Otvorí sa graf s vizualizáciou  
✅ Vypíše počet dosiek, rezanie a odpad

---

### 2️⃣ Spôsob: Vlastný CSV Súbor

**1. Vytvor `parts.csv`:**
```csv
name,w,h,qty,can_rotate
Bok,720,560,2,0
Polica,564,500,4,1
Dvierka,715,397,4,0
```

**2. Spusti solver:**
```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --parts parts.csv --board 2800x2070 --trim 10,10,10,10 --kerf 3.2
```

---

### 3️⃣ Spôsob: Vlastné Parametre

```bash
python -m dtd_solver.main \
  --example \
  --board 3000x2100 \
  --trim 5,5,5,5 \
  --kerf 4.0 \
  --time 20 \
  --no_labels
```

**Dostupné parametre:**

| Parameter | Default | Popis |
|-----------|---------|-------|
| `--board WxH` | 2800x2070 | Veľkosť dosky (mm) |
| `--trim l,r,t,b` | 10,10,10,10 | Okraje na orez (l,r,t,b) |
| `--kerf FLOAT` | 3.2 | Šírka rezu (mm) |
| `--time FLOAT` | 10.0 | Čas na riešenie (sekundy) |
| `--max_sheets INT` | 20 | Maximálne dosky |
| `--cut_weight INT` | 1 | Penalizácia za rezanie |
| `--parts FILE` | - | Cesta k CSV |
| `--example` | - | Použiť príklady |
| `--no_labels` | - | Skryť popisky |
| `--no_dims` | - | Skryť rozmery |
| `--grid` | - | Zobraziť mriežku |

---

### 4️⃣ Spôsob: Python API (Bez Matplotlib)

```python
import sys
sys.path.insert(0, '/home/branislav/Dokumenty/pg')

from dtd_solver.types import BoardSpec, PartSpec, Trim
from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves

# Doska
board = BoardSpec(
    name="Moja doska",
    raw_w=2800,
    raw_h=2070,
    trim=Trim(10, 10, 10, 10)
)

# Diely
parts = [
    PartSpec("Bok", 720, 560, qty=2, can_rotate=False),
    PartSpec("Polica", 564, 500, qty=4, can_rotate=True),
    PartSpec("Dvierka", 715, 397, qty=4, can_rotate=False),
]

# Solver parametre
params = SolverParams(
    kerf=3,              # 3mm saw kerf
    time_limit_s=10.0,   # 10 sekúnd na dosku
    max_sheets=20,       # Max 20 dosiek
    cut_weight=1,        # Penalizácia rezov
)

# Riešiť
solution = solve_from_partspecs_iterative_shelves(board, parts, params=params)

# Výsledky
print(f"Dosiek: {solution.num_sheets()}")
print(f"Rezanie: {solution.total_cut_length()} mm")
print(f"Odpad: {solution.total_waste_area()} mm²")

# Detail - každá doska
for i in range(solution.num_sheets()):
    sheet = solution.sheets[i]
    print(f"\nDoska {i+1}:")
    print(f"  Dielov: {len(sheet.placements)}")
    print(f"  Rezanie: {sheet.total_cut_length()} mm")
    print(f"  Odpad: {sheet.waste_area} mm²")
```

---

### 5️⃣ Spôsob: CLI s CSV Exportom

```bash
python -m dtd_solver.cli --parts parts.csv --out output/
```

✅ Vyexportuje CSV súbory s detailami každej dosky

---

## 💾 Formát CSV (parts.csv)

```csv
name,w,h,qty,can_rotate
Bok_vysokej_skrine,2400,560,2,0
Polica_vysokej_skrine,560,500,6,1
Bok_malej_skrine,720,560,2,0
Dvierka,715,397,4,0
Podstava,564,120,6,1
```

| Stĺpec | Popis | Povinný |
|--------|-------|---------|
| `name` | Názov dielu | ✅ |
| `w` | Šírka (mm) | ✅ |
| `h` | Výška (mm) | ✅ |
| `qty` | Počet kusov | ❌ (default: 1) |
| `can_rotate` | Dá sa rotovať? (1=áno, 0=nie) | ❌ (default: 1) |

---

## 📂 Projektová Štruktúra

```
/home/branislav/Dokumenty/pg/dtd_solver/
│
├── 📄 Dokumentácia
│   ├── QUICK_START.md          ← Podrobný sprievodca
│   ├── SETUP_GUIDE.md          ← Inštalácia a setup
│   ├── HOW_TO_RUN.py           ← Príklady kódu
│   └── README_DEV.md           ← Dev poznámky
│
├── 🐍 Hlavný Kód
│   ├── main.py                 ← CLI s matplotlib
│   ├── cli.py                  ← CLI s CSV export
│   ├── run.py                  ← High-level API
│   │
│   ├── types.py                ← Dátové štruktúry
│   ├── solver_shelf_cp_sat.py  ← Solver algoritmus
│   ├── metrics.py              ← Výpočty (rezanie, odpad)
│   ├── plotting.py             ← Matplotlib grafika
│   ├── validate.py             ← Validácia riešení
│   │
│   ├── sample_data.py          ← Generovanie testov
│   ├── io_csv.py               ← CSV import/export
│   ├── config.py               ← Konfigurácia
│   ├── utils.py                ← Pomocné funkcie
│   └── __init__.py             ← Package export
│
├── 🚀 Spustiteľné
│   ├── example_simple.py       ← Jednoduchý príklad
│   ├── example_end_to_end.py   ← Komplexný príklad
│   └── test_quick.py           ← Rýchly test
│
├── 🔧 Prostredie
│   ├── venv/                   ← Virtuálne prostredie ✅
│   │   ├── bin/python          ← Python interpreter
│   │   └── lib/                ← Balíčky (ortools, matplotlib)
│   │
│   └── __pycache__/            ← Cache (ignore)
│
└── 📋 Konfigurácia
    └── .gitignore              ← Git ignore pravidlá
```

---

## ⚠️ Dôležité Poznamienky

### 1. Virtuálne Prostredie
- **Vždy aktivuj pred spustením:**
  ```bash
  source dtd_solver/venv/bin/activate
  ```
- Deaktivuj príkazom `deactivate`

### 2. Adresár Spustenia
- **Vždy spúšťaj z rodičovského adresára:**
  ```bash
  cd /home/branislav/Dokumenty/pg
  python -m dtd_solver.main --example
  ```
- ⚠️ NIKDY z `dtd_solver/` priečinka!
- **Dôvod:** Konflikt `types.py` s Python štandardným modulom

### 3. Matplotlib Okno
- `--example` otvorí interaktívne okno
- Zatvrť okno a terminal sa ukončí
- Ak chceš bez okna, použi Python API priamo

### 4. CSV Formát
- Záhlavie je **povinné**
- Hodnoty musia byť **čísla**
- Názvy dielov: **bez čiarok** (alebo v úvodzovkách)

---

## 🔨 Ako Funguje Algoritmus?

### 1️⃣ **Vstup & Transformácia**
```
Doska 2800×2070 mm → Usable 2780×2050 mm (po trim)
Diely: 10× Bok, 6× Polica, ...
```

### 2️⃣ **Optimalizácia (CP-SAT Solver)**
```
Model:
  - Shelf-based packing (horizontálne pásy)
  - Umiestnenie dielov v policy (zľava doprava)
  - Selektívna rotácia (ak je dovolená)
  - Spacing (kerf between parts)

Objektív:
  Maximalizuj: used_area - cut_length_penalty
```

### 3️⃣ **Iterácia**
```
Doska 1: Zmesti sa 80% dielov
Doska 2: Zmesti sa zvyšných 20% dielov
Výstup: 2 dosky
```

### 4️⃣ **Metriky**
```
Rezanie:    Dĺžka rezov (horizontálne + vertikálne)
Odpad:      Nepoužitá plocha
Dosiek:     Počet potrebných dosiek
```

---

## 🐛 Časté Problémy & Riešenia

### ❌ "ImportError: cannot import name 'MappingProxyType'"
```bash
# ❌ ZĽAVAITE: Spúšťate z dtd_solver/ adresára!
cd dtd_solver
python -m dtd_solver.main --example  # CHYBA!

# ✅ SPRÁVNE: Spustite z rodičovského adresára
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --example  # OK!
```

### ❌ "ModuleNotFoundError: No module named 'ortools'"
```bash
# Čínite, že ste v inom prostredí
source dtd_solver/venv/bin/activate  # Aktivujte venv!
python -m dtd_solver.main --example
```

### ❌ "No such file or directory: parts.csv"
```bash
# CSV musí existovať v aktuálnom adresári
ls parts.csv  # Skontroluj

# Alebo zadaj cestu
python -m dtd_solver.main --parts /path/to/parts.csv
```

### ❌ "Matplotlib window freezes terminal"
```bash
# To je normálne - matplotlib blokuje kým máš okno otvorené
# Zatvor matplotlib okno a terminal bude libre
```

---

## 📊 Príklady Výstupu

### Vstavané Príklady
```
Used sheets: 2
Total cut length (internal + trim-charged): 12,880 mm
Total waste area: 7,030,000 mm²
```

### S Vlastnými Parametrami
```
Used sheets: 1
Total cut length (internal + trim-charged): 8,920 mm
Total waste area: 3,450,000 mm²
```

---

## 💡 Ďalšie Tipy

### Testovanie s Veľkými Problémami
```python
from dtd_solver.sample_data import generate_random_parts

# Vygeneruj 50 náhodných dielov
parts = generate_random_parts(n_unique=50)

# Zvyšok rovnaký...
```

### Zmena Prioritety (Rezanie vs. Odpad)
```python
# Preferuj menšie rezanie
params = SolverParams(cut_weight=5)

# Preferuj menej dosiek (podskupina)
params = SolverParams(shelf_count_weight=10)
```

### Debug & Profiling
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python -m dtd_solver.main --example --time 30
```

---

## 📖 Ďalšia Dokumentácia

1. **QUICK_START.md** - Podrobný sprievodca (ČÍTAJ TOTO!)
2. **SETUP_GUIDE.md** - Inštalácia a troubleshooting
3. **HOW_TO_RUN.py** - Príklady kódu (spustiteľný!)
4. **README_DEV.md** - Vývojové poznámky

---

## ✨ Zhrnutie

| | |
|---|---|
| **Spustenie** | `python -m dtd_solver.main --example` |
| **S CSV** | `python -m dtd_solver.main --parts parts.csv` |
| **V Pythone** | Importuj `dtd_solver` a použi API |
| **Adresár** | `/home/branislav/Dokumenty/pg` |
| **Prostredie** | `source dtd_solver/venv/bin/activate` |

---

## 🎉 Gratulácia!

Tvoj projekt **dtd_solver** je plne funkčný a spustiteľný! 

Ak máš otázky alebo potrebuješ viac detailov, skúmaj dokumentáciu v kóde alebo spusti príklady.

**Vždy pamätaj:**
- ✅ Aktivuj `venv`
- ✅ Spúšťaj z `/home/branislav/Dokumenty/pg`
- ✅ Čítaj dokumentáciu v projektových súboroch

Tešíme sa na tvoje projekty! 🚀
