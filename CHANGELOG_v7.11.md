# Changelog — Version 7.11

## Version 7.11.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — Parallelisierung der GIFT-Rechnung

Phase 3c des GIFT-Moduls (Planung: `GIFT/PLAN.md`).

### ✨ Neue Features & Verbesserungen (7.11.0)

#### 1. Prozess-Pool (`analysis/gift/parallel.py`)

- Persistenter `multiprocessing.Pool` im Start-Modus `spawn` (Windows). Er wird einmal
  angelegt und über alle Rechnungen wiederverwendet; das Anlegen dauert ≈ 0.2 s.
- **Kein erneuter Import des Hauptprogramms in den Workern.** Unter `spawn` führt jeder
  neue Prozess sonst das Hauptmodul erneut aus: in der App `scatter_plot.py` mit PySide6,
  unter `python -m unittest` sogar den Test-Runner. Beim Anlegen des Pools werden
  `__main__.__file__`/`__spec__` kurz ausgeblendet; ein Test prüft, dass die Worker
  kein PySide6 laden.
- BLAS/OpenMP ist pro Worker auf einen Thread begrenzt, damit die Kerne nicht überbelegt
  werden.
- Fortschritt und Abbruch laufen über eine Queue und ein Event, die beim Start an die
  Worker übergeben werden. Der Pool bleibt nach einem Abbruch nutzbar.

#### 2. Parallele BSSA-Mehrfachstarts

- Die Mehrfachstarts aus v7.10 laufen jetzt im Pool. Seriell und parallel führen
  denselben Code aus.
- **Bitgleich unabhängig von der Worker-Zahl:** Parameter, MD, Zahl der Auswertungen,
  Starts und BSSA-Verlauf stimmen für 1, 3, 4 und 8 Worker exakt überein. Die Seeds
  hängen an den Starts; im Pool rechnet BLAS einfädig.
- **Befund:** Eine Rechnung im Hauptprozess mit mehrfädigem BLAS weicht in der 6.–7.
  Stelle ab, weil sich die Summationsreihenfolge in den Matrixprodukten ändert. Die
  BSSA-Trajektorien laufen dadurch auseinander. Deshalb laufen die Starts **immer im
  Pool**, auch mit nur einem Prozess. `n_workers = 0` rechnet ausdrücklich im
  Hauptprozess (Diagnosemodus, nicht bitgleich).
- **Laufzeit** (RMSA, 8 Starts, SasView-Kurve, 12-Kern-Rechner): 11.4 s → **5.5 s**.
  Den Rest bestimmen die nachfolgenden λ-Zyklen, die aus einem einzelnen Lauf bestehen.
- Dialog: neues Feld **„Prozesse“** (Standard: Kerne − 1, höchstens 8; 0 =
  Hauptprozess). Die Fortschrittsanzeige fasst alle Worker zusammen (Summe der
  Auswertungen, bestes MD).
- Das Sidecar dokumentiert `n_workers` und den Hinweis, dass das Ergebnis davon
  unabhängig ist.

#### 3. Vektorisierte Batch-Likelihood (`IFTProblem.md_batch`)

- Die MD für K Strukturfaktoren wird in einem Schritt berechnet: gestapelte
  BLAS-Matrixprodukte und Cholesky-Zerlegungen (K × N × N), in Blöcken. Ungültige
  Parametersätze ergeben ∞.
- Abweichung zur Einzelrechnung ≤ 10⁻⁶ (reine Rundung).
- Beschleunigung ×2–3 bei typischen Größen (N ≈ 25); bei großen Basen (N ≈ 120) kein
  Gewinn, weil die Einzelrechnung dort schon BLAS-gebunden ist.
- Die Funktion ist die Schnittstelle für DREAM und das Parameterscreening (Phase 3d).

### 📦 Neue / geänderte Dateien (7.11.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/parallel.py` | **neu** — WorkerPool, `get_pool()`, Fortschritt/Abbruch, verborgenes `__main__`, BLAS-Begrenzung |
| `analysis/gift/gift.py` | BSSA-Starts als picklebare Aufgaben (`_Search`, `_start_task`), `GIFTSettings.n_workers`, `GIFTResult.n_workers` |
| `analysis/gift/ift.py` | `IFTProblem.md_batch()` |
| `analysis/gift/pipeline.py` | Sidecar: `n_workers`, Hinweis zur Unabhängigkeit |
| `dialogs/gift_dialog.py` | Feld „Prozesse“, Warnungsunterdrückung beim Neuzeichnen |
| `i18n/translations/de.json`, `en.json` | `gift.workers`, `gift.workers_tooltip` |
| `tests/analysis/test_gift_parallel.py` | **neu** — 6 Tests (Worker ohne Hauptmodul, Wiederverwendung, Bitgleichheit 1 vs. 3 Worker, Fortschritt/Abbruch, Batch = Einzel) |
| `core/version.py` | `7.10.0` → `7.11.0`; `analysis.gift` 0.3.0 → 0.4.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 81 Tests (≈ 31 s).

### ⚠️ Hinweise

- Bitgleichheit gilt auf demselben Rechner mit derselben numpy/BLAS-Version. Auf
  anderer Hardware oder mit einer anderen BLAS-Bibliothek können Ergebnisse in den
  letzten Stellen abweichen. Das Sidecar dokumentiert die Bibliotheksversionen.
- Stirbt ein Worker-Prozess, erzeugt `multiprocessing` einen Ersatz, dann allerdings
  ohne ausgeblendetes Hauptmodul (langsamerer Start, funktional unkritisch).

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.11 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben.

---

*Letzte Aktualisierung: 2026-09-23*
