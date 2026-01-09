# 📚 DTD Solver - Index a Prehľad

**Verzia:** 1.0  
**Dátum:** 9. januára 2026  
**Status:** ✅ **PLNE FUNKČNÝ**

---

## 🎯 Rýchly Orientačný Prehľad

Ak chceš **rýchlo začať**, skonči na túto sekciu:

### 👨‍💻 Absolútne Prvé (30 sekúnd)
```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate
python -m dtd_solver.main --example
```
✅ **Výsledok:** Vidíš počet dosiek, rezania a graf s vizualizáciou

---

## 📖 Dokumentácia - Kde Čo Nájsť

### 🟢 **ZAČNI TU** - Ak si úplne nový
1. **[README_DTD_SOLVER.md](README_DTD_SOLVER.md)** ← Čítaj TÚ NAJSKÔR!
   - Rýchly start (30 sekúnd)
   - Všetkých 5 spôsobov spustenia
   - Časté problémy & riešenia

### 🟡 **POTOM** - Ak chceš viac detailov
2. **[dtd_solver/QUICK_START.md](dtd_solver/QUICK_START.md)**
   - Detailnejšie príklady
   - Vysvetlenie algoritmu
   - Pokročilé parametre

3. **[dtd_solver/SETUP_GUIDE.md](dtd_solver/SETUP_GUIDE.md)**
   - Úplná inštalácia
   - Troubleshooting
   - Štruktúra projektu

### 🔵 **EXPERT** - Ak chceš programovať
4. **[dtd_solver/HOW_TO_RUN.py](dtd_solver/HOW_TO_RUN.py)** (spustiteľný!)
   - Úplné kódy príkladov
   - Vysvetlenie API
   - Pokročilé použitie

5. **[dtd_solver/README_DEV.md](dtd_solver/README_DEV.md)**
   - Vývojové poznámky
   - Plán rozvoja
   - Architektúra

---

## 🗺️ Mapa Projektu

```
📁 /home/branislav/Dokumenty/pg/
│
├── 📄 README_DTD_SOLVER.md          ← 👈 ČÍTAJ PRVÚ!
├── 📄 README.txt (NOVÝ)             ← Ty si čítaš
│
└── 📁 dtd_solver/                   ← Hlavný projekt
    │
    ├── 📄 QUICK_START.md            ← Sprievodca
    ├── 📄 SETUP_GUIDE.md            ← Inštalácia
    ├── 📄 README_DEV.md             ← Dev Notes
    │
    ├── 🐍 main.py                   ← CLI: --example
    ├── 🐍 cli.py                    ← CLI: --parts & --out
    ├── 🐍 HOW_TO_RUN.py             ← Príklady (SPUSTITEĽNÝ)
    │
    ├── 🐍 types.py                  ← Dátové štruktúry
    ├── 🐍 solver_shelf_cp_sat.py    ← Solver (OPRAVENÝ!)
    ├── 🐍 metrics.py                ← Výpočty
    ├── 🐍 plotting.py               ← Grafy
    ├── 🐍 run.py                    ← Runner
    │
    ├── 🚀 venv/                     ← Virtuálne prostredie ✅
    │
    └── 📋 Ostatné Python súbory...
```

---

## ✅ Čo Je Hotovo

| Položka | Status | Poznámka |
|---------|--------|----------|
| **Inštalácia** | ✅ | ortools, matplotlib, venv |
| **Solver** | ✅ | CP-SAT, shelf-based packing |
| **CSV Import** | ✅ | Čítanie dielov |
| **Vizualizácia** | ✅ | Matplotlib grafy |
| **Dokumentácia** | ✅ | 4 súbory + README |
| **Oprava Bugov** | ✅ | NewOptionalIntervalVar fix |

---

## 🎓 5 Spôsobov Spustenia

### 1. Vstavané Príklady (Najjednoduché)
```bash
python -m dtd_solver.main --example
```

### 2. S CSV Súborom
```bash
python -m dtd_solver.main --parts parts.csv
```

### 3. S Parametrami
```bash
python -m dtd_solver.main \
  --example \
  --board 3000x2100 \
  --kerf 4.0 \
  --time 30
```

### 4. Python API (Bez Matplotlib)
```python
from dtd_solver.types import BoardSpec, PartSpec
from dtd_solver.solver_shelf_cp_sat import solve_from_partspecs_iterative_shelves, SolverParams

board = BoardSpec("DTD", 2800, 2070)
parts = [PartSpec("Item", 100, 200, qty=10)]
sol = solve_from_partspecs_iterative_shelves(board, parts, params=SolverParams())
print(f"Sheets: {sol.num_sheets()}")
```

### 5. CLI s Exportom
```bash
python -m dtd_solver.cli --parts parts.csv --out output/
```

---

## 🔍 Čo Je Nové / Opravené

### Oprava: solver_shelf_cp_sat.py (Lines 165-190)
**Problem:** NewOptionalIntervalVar API v ortools 9.14 vyžaduje affine výrazy  
**Riešenie:** Pre-kalkulácia `inflated_w` ako IntVar pred použitím  
**Status:** ✅ Opravené a testované

### Nová Dokumentácia
1. **QUICK_START.md** - Podrobný sprievodca (6KB)
2. **README_DTD_SOLVER.md** - Úplný návod (8KB)
3. **HOW_TO_RUN.py** - Spustiteľné príklady (12KB)

---

## ⚡ Rýchly Test

```bash
cd /home/branislav/Dokumenty/pg
source dtd_solver/venv/bin/activate

# Test 1: Import OK?
python -c "from dtd_solver.types import BoardSpec; print('✓ OK')"

# Test 2: Solver OK?
python << 'EOF'
import sys
sys.path.insert(0, '/home/branislav/Dokumenty/pg')
from dtd_solver.types import BoardSpec, PartSpec
from dtd_solver.solver_shelf_cp_sat import SolverParams, solve_from_partspecs_iterative_shelves

board = BoardSpec("Test", 2800, 2070)
parts = [PartSpec("P", 100, 200, qty=5)]
sol = solve_from_partspecs_iterative_shelves(board, parts, params=SolverParams())
print(f"✓ Solver OK - {sol.num_sheets()} sheets")
EOF

# Test 3: Example?
python -m dtd_solver.main --example
```

---

## 🛠️ Ako som to Rozbehol

1. **Vytvorenie venv** (z rodičovského adresára)
   ```bash
   python3 -m venv dtd_solver/venv
   ```

2. **Inštalácia závislostí**
   ```bash
   pip install ortools matplotlib
   ```

3. **Oprava Solver API** (Lines 165-190)
   - Zmena `NewOptionalIntervalVar` call
   - Pre-kalkulácia `inflated_w`

4. **Testovanie**
   - ✅ Solver funguje
   - ✅ Výstup je korektný
   - ✅ Matplotlib OK

5. **Dokumentácia**
   - QUICK_START.md
   - SETUP_GUIDE.md
   - HOW_TO_RUN.py

---

## 📊 Výsledky Testov

```
Input:
  Board: 2800×2070 mm (usable: 2780×2050)
  Parts: Bok (2400×560, qty=2), Polica (560×500, qty=6), atď.

Output:
  Sheets: 2
  Cut length: 12,880 mm
  Waste area: 7,030,000 mm²

Status: ✅ SUCCESS
```

---

## 📞 Pomoc a Otázky

### "Ako spustím projekt?"
→ Čítaj [README_DTD_SOLVER.md](README_DTD_SOLVER.md)

### "Chcem svoj CSV súbor"
→ Čítaj sekcia "CSV Format" v [README_DTD_SOLVER.md](README_DTD_SOLVER.md)

### "Chcem programovať"
→ Čítaj [dtd_solver/HOW_TO_RUN.py](dtd_solver/HOW_TO_RUN.py) a spusti ho

### "Má chybu!"
→ Čítaj "Časté Problémy" v [README_DTD_SOLVER.md](README_DTD_SOLVER.md)

---

## 🎯 Ďalšie Kroky

1. **Skúš spustiť príklady** ← NAJSKÔR!
   ```bash
   cd /home/branislav/Dokumenty/pg
   source dtd_solver/venv/bin/activate
   python -m dtd_solver.main --example
   ```

2. **Vytvor svoj CSV** ← POTOM
   ```bash
   # Napiš parts.csv s tvojimi dielmi
   python -m dtd_solver.main --parts parts.csv
   ```

3. **Skúmaj kód** ← NAPOKON
   ```bash
   # Čítaj HOW_TO_RUN.py
   python dtd_solver/HOW_TO_RUN.py
   ```

---

## 💾 Súbory na Čítanie (Podľa Poradia)

| Poradie | Súbor | Dĺžka | Čas |
|---------|-------|-------|-----|
| 1️⃣ | **[README_DTD_SOLVER.md](README_DTD_SOLVER.md)** | 8 KB | 5-10 min |
| 2️⃣ | **[dtd_solver/QUICK_START.md](dtd_solver/QUICK_START.md)** | 6 KB | 5-10 min |
| 3️⃣ | **[dtd_solver/SETUP_GUIDE.md](dtd_solver/SETUP_GUIDE.md)** | 5 KB | 3-5 min |
| 4️⃣ | **[dtd_solver/HOW_TO_RUN.py](dtd_solver/HOW_TO_RUN.py)** | 12 KB | 10 min |
| 5️⃣ | **[dtd_solver/README_DEV.md](dtd_solver/README_DEV.md)** | 2 KB | 2 min |

---

## ✨ Zhrnutie

### 🎯 Cieľ
Spustiteľný solver na optimalizáciu rezania dosiek pre woodworking

### ✅ Dosiahnuté
- Solver funguje (CP-SAT)
- Všetky závislosti nainštalované
- Dokumentácia hotová
- Opravy aplikované

### 🚀 Ďalej Vieš
- Aktivovať venv: `source dtd_solver/venv/bin/activate`
- Spustiť príklad: `python -m dtd_solver.main --example`
- Čítať dokumentáciu: [README_DTD_SOLVER.md](README_DTD_SOLVER.md)

---

## 📜 Licencia & Poznámka

Projekt je bez explicitnej licencie. Môžeš ho používať a modifikovať na svoje potreby.

Ak máš otázky, najskôr si prečítaj dokumentáciu v projektových súboroch.

---

## 🎉 Hotovo!

Projekt **dtd_solver** je plne funkčný a spustiteľný! 

**Začni tu:** [README_DTD_SOLVER.md](README_DTD_SOLVER.md)

---

**Vytvorené:** 9. januára 2026  
**Stav:** ✅ Plne funkčné  
**Podpora:** V dokumentácii v projektových súboroch
