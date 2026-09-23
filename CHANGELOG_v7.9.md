# Changelog — Version 7.9

## Version 7.9.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — GIFT: generalisierte indirekte Fourier-Transformation mit Strukturfaktor

Phase 3a des GIFT-Moduls (Planung: `GIFT/PLAN.md`). Für konzentrierte, ungeladene Systeme
lassen sich Form- und Strukturfaktor jetzt gleichzeitig bestimmen:
I(q) = S(q)·P(q). P(q) bzw. p(r) bleibt dabei modellfrei; nur S(q) wird parametrisiert.

### ✨ Neue Features & Verbesserungen (7.9.0)

#### 1. Strukturfaktor-Modelle (`analysis/gift/structure_factors.py`)

| Modell | Parameter | Quelle |
|--------|-----------|--------|
| Harte Kugeln, gemittelt **S_ave** (empfohlen) | φ, R_HS, μ = σ_R/R_HS | Brunner-Popela & Glatter 1997 Gl. 34; Weyerich et al. 1999 Gl. 8 |
| Harte Kugeln, Percus-Yevick | φ, R_HS | Brunner-Popela & Glatter 1997 §2.4 |
| Kein (IFT) | — | — |

- **PY-Strukturfaktor:** berechnet als S = 1/(1 − n·ĉ(q)) über die polynomiale direkte
  Korrelationsfunktion. Für x = 2qR_HS ≤ 1 per Gauss-Legendre-Quadratur, sonst in
  geschlossener Form (Kinning & Thomas). Die geschlossene Form löscht bei kleinen x
  numerisch aus. Geprüft wurden S(0) = (1−φ)⁴/(1+2φ)² auf 12 Stellen sowie beide
  Zweige gegen eine adaptive Referenzquadratur.
- **S_ave:** gaußverteilte Radien bei festem φ, diskretisiert mit 21
  Gauss-Hermite-Knoten.
- Alle Modelle sind vektorisiert: Parameter-Arrays ergeben (K × M). Das ist die Grundlage
  für die geplante Batch-Auswertung mit DREAM.

#### 2. BSSA-Optimierer (`analysis/gift/bssa.py`)

Boltzmann-Simplex-Simulated-Annealing nach Bergmann, Fritz & Glatter (2000), entsprechend
`amebsa` aus Numerical Recipes:
- logarithmisch verteilte thermische Fluktuationen −T·ln(u)
- Abkühlen T ← 0.8·T nach j = 20–40 Zügen
- MD = ∞ außerhalb der physikalischen Grenzen
- abschließende Politur bei T = 0
- reproduzierbar über einen Seed

**Abweichung:** Die Start-Temperatur wird aus der Streuung der MD über den Startsimplex
*und* einer kleinen Zufallsprobe (10 Punkte je Parameter) bestimmt. Die Streuung allein
über den Startsimplex war auf Testflächen zu klein, um lokale Minima wieder zu verlassen.

#### 3. GIFT-Rechnung (`analysis/gift/gift.py`)

- **Innere Schleife:** stabilisierte IFT mit ψ̃_ν(q) = ψ_ν(q)·S(q) [BP97 Gl. 6].
- **Äußere Schleife:** BSSA über die S(q)-Parameter in normierten Koordinaten.
- **λ-Zyklen:** λ ist während der Suche fest. Danach wird es am Optimum per
  Wendepunkt-Methode neu bestimmt; bei Abweichung > 10^0.25 folgt ein weiterer Zyklus
  (max. 3).
- **Suchgrenzen:** Größenparameter (R_HS) suchen standardmäßig in [Start/4, Start·4].
  Benutzergrenzen haben Vorrang, die physikalischen Grenzen bleiben die äußere Schranke.
- **Parameterfehler:** aus der Krümmung von χ² am Optimum. Das ist eine Näherung; die
  statistisch saubere Analyse folgt mit DREAM (Phase 3d).
- **Validierung** am Beispiel aus Brunner-Popela & Glatter (1997), §3.2.1: Kugel mit
  R = 10 nm, S_ave mit φ = 0.15, R_HS = 10 nm, μ = 0.4, Start bei (0.18, 12, 0.5).

  | Rauschen | φ | R_HS | μ | Rg | p(r)-Abweichung |
  |---|---|---|---|---|---|
  | 2 % | 0.147 ± 0.002 | 10.07 ± 0.11 | 0.387 ± 0.009 | 7.737 nm (Soll 7.746) | 0.4 % |
  | 4 % | 0.149 ± 0.003 | 10.02 ± 0.20 | 0.373 ± 0.016 | 7.745 nm | 0.2 % |

  Laufzeit ≈ 1–2 s; Bergmann et al. (2000) nennen 10–30 min auf einem Pentium 200. Ohne
  S(q) liefert die IFT Rg ≈ 6.86 nm (−11 %) bei MD ≈ 40.

#### 4. Dialog: GIFT-Modus

- Neue Gruppe **„Strukturfaktor (GIFT)“** mit:
  - Modellwahl
  - Parametertabelle (Start, min, max, fix)
  - „Startwerte aus IFT“ (R_HS = √(5/3)·Rg der äquivalenten Kugel)
  - Seed
  - Hinweis zu den scheinbaren S_ave-Parametern [W99]
- **„GIFT starten“** rechnet im Hintergrund-Thread mit Fortschrittsanzeige (Auswertungen,
  T, MD, Zyklus) und Abbrechen-Knopf. Im GIFT-Modus gibt es keine automatische
  Live-Rechnung.
- **Neue Tabs:**
  - „S(q) & P(q)“: S(q) sowie Daten, S·P und P(q), wie BP97 Fig. 3
  - „BSSA-Verlauf“: MD und T über die Auswertungen sowie die normierten Parameter, wie
    B00 Fig. 2 und 3
- **Ergebnisse:** S(q)-Parameter ± Fehler und MD ohne S(q).
- **Neue Flags:**
  - Parameter am Rand der Grenzen
  - S(q) < 0
  - Verbesserung gegenüber S = 1
  - λ nicht stabil
  - Fehler nicht bestimmbar
  - Hinweis auf scheinbare Parameter
- **Übernehmen** schreibt zusätzlich `<name>_GIFT_Sq.dat` (q, S) und `<name>_GIFT_Pq.dat`
  (q, P, σ_P). Eine GIFT-Rechnung wird dafür nicht wiederholt. Liegen von einer früheren
  GIFT-Rechnung noch S(q)/P(q)-Dateien vor, werden sie nach bestätigtem Überschreiben
  entfernt.
- **„Einstellungen aus Sidecar…“** übernimmt auch Modell, Start, Grenzen, fixe
  Parameter und Seed. Der Rg-Vergleich folgt nach Abschluss der Hintergrundrechnung;
  bei gleichem Seed ist das Ergebnis bitgleich.

#### 5. q-Einheit der Datei (nm⁻¹ / Å⁻¹)

SasView rechnet in Å und Å⁻¹, ScatterForge in nm und nm⁻¹. Aus der Kurvenform allein ist
die Einheit nicht erkennbar, weil q·R skaleninvariant ist. Werden SasView-Daten als nm⁻¹
gelesen, sind alle Längen um den Faktor 10 zu groß; bei `Sphere_142.txt` war der Radius
tatsächlich 142 Å, erkennbar an der absoluten Intensität I(0) = Δρ²·V.

- Im Datenblock des Dialogs ist die q-Einheit der Datei wählbar (Å⁻¹ → ×10). Die Wahl
  wird im Sidecar festgehalten (`q_unit_file`, `q_conversion_factor`) und beim Laden
  eines Sidecars wiederhergestellt.
- Bei umgerechnetem q schreibt „Übernehmen“ zusätzlich `<name>_GIFT_data.dat` mit den
  verwendeten Eingangsdaten (q in nm⁻¹ und das verwendete σ). Diese Datei ersetzt in der
  PDDF-Gruppe die Originaldaten, sodass Daten und Fit dieselbe q-Achse haben.

#### 6. Unabhängige Referenzdaten aus SasView

Zwei rauschfreie SasView-Simulationen liegen als Test-Fixtures in `tests/analysis/data/`
(Herkunft und Parameter in `README.md` dort): `sphere@hardsphere` und
`sphere@hayter_msa` mit R = 140 Å, φ = 0.2.

- **Eigener PY-Strukturfaktor gegen sasmodels:** relative Abweichung 2.6·10⁻¹³.
- **GIFT mit HS-PY auf der Hardsphere-Kurve:** φ = 0.2000, R_HS = 14.00 nm,
  Rg = 10.844 nm (exakt).
- **GIFT mit S_ave auf der Hayter-MSA-Kurve:** Rg auf 0.01 % korrekt, obwohl die
  Parameter nur scheinbar sind (φ = 0.26, R_HS = 15.7 nm). Das bestätigt Weyerich et al.
  1999. Die IFT ohne S(q) liegt bei Rg um 4–8 % daneben.

#### 7. Fehlerbehebung: Export mit Nicht-ASCII-Zeichen

`np.savetxt` schrieb unter Windows in cp1252. Ein Umlaut oder „µ“ im Dateinamen der
Messung ließ „Übernehmen“ abstürzen. Alle Ergebnisdateien werden jetzt in UTF-8
geschrieben; ein Regressionstest deckt das ab.

#### 8. Provenance

- Neue Aktivität **`gift_bssa`** zwischen Vorverarbeitung und IFT. Sie enthält:
  - Modell mit Literaturangabe, Start, Benutzer- und effektive Grenzen, fixe Parameter
  - BSSA-Einstellungen inkl. Seed, λ-Zyklen
  - Ergebnisse (Parameter, Fehler mit Methode, MD mit/ohne S(q), Anzahl Auswertungen,
    λ-Verlauf)
- `reproducibility` enthält den Seed, die Seed-Regel pro Zyklus und den RNG.
- Der Export verändert den Record der Analyse nicht mehr, sondern schreibt eine Kopie.

### 📦 Neue / geänderte Dateien (7.9.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/structure_factors.py` | **neu** — PY, S_ave, Registry |
| `analysis/gift/bssa.py` | **neu** — BSSA |
| `analysis/gift/gift.py` | **neu** — GIFT-Rechnung, λ-Zyklen, Krümmungsfehler |
| `analysis/gift/ift.py` | `run_ift(..., structure_factor=)`, `IFTProblem` (schnelle MD bei festem λ), Formfaktor in `extras` |
| `analysis/gift/pipeline.py` | `run_ift_analysis(..., gift_settings=, progress=)`, Aktivität `gift_bssa`, Export S(q)/P(q), Export ohne Seiteneffekt |
| `analysis/gift/diagnostics.py` | `diagnose_gift()` |
| `dialogs/gift_dialog.py` | GIFT-Modus, Hintergrund-Thread, Tabs S(q) & P(q) und BSSA |
| `i18n/translations/de.json`, `en.json` | GIFT-Texte und -Flags |
| `tests/analysis/test_gift_gift.py` | **neu** — 20 Tests (PY, S_ave, BSSA, GIFT nach BP97, SasView-Referenz, Pipeline/Provenance) |
| `tests/analysis/data/*` | **neu** — SasView-Referenzkurven (Hardsphere, Hayter-MSA) mit Herkunftsbeschreibung |
| `core/version.py` | `7.8.0` → `7.9.0`; `analysis.gift` 0.1.0 → 0.2.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 63 Tests.

### ⚠️ Bekannte Einschränkungen

- **Noch keine geladenen Systeme:** RMSA folgt als Phase 3b.
- **Parameterfehler aus der MD-Krümmung** unterschätzen Korrelationen und
  Nichtlinearitäten. Die DREAM-Analyse folgt als Phase 3d.
- **S_ave-Parameter** sind nach Weyerich et al. (1999) nur scheinbare Parameter.

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.9 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die Methodik folgt den vom
Projektinhaber bereitgestellten Originalarbeiten von Glatter, Brunner-Popela, Weyerich
und Bergmann.

---

*Letzte Aktualisierung: 2026-09-23*
