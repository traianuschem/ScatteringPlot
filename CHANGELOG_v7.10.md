# Changelog — Version 7.10

## Version 7.10.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — GIFT für geladene Systeme (RMSA)

Phase 3b des GIFT-Moduls (Planung: `GIFT/PLAN.md`): Strukturfaktor für geladene Kugeln
mit abgeschirmtem Coulomb-Potential, nach Fritz, Bergmann & Glatter (2000).

### ✨ Neue Features & Verbesserungen (7.10.0)

#### 1. RMSA-Strukturfaktor (`analysis/gift/rmsa.py`)

- Mean-Spherical-Approximation nach **Hayter & Penfold (1981)**, analytisch über die
  Quartik für F, mit **Rescaling nach Hansen & Hayter (1982)**. Bei verdünnten, stark
  geladenen Systemen gäbe die MSA einen negativen Kontaktwert g(σ+). Dann wird der
  effektive Durchmesser σ' bei fester Kopplung vergrößert, bis g(σ'+) = 0.
- **Herkunft:** zeilengetreue Portierung von `hayter_msa.c` aus sasmodels 1.0.12
  (BSD-3-Clause; Hinweis in `rmsa.py` und `THIRD_PARTY_NOTICES.md`). Der OCR-Text der
  Originalarbeiten ist im Anhang mit den Quartik-Koeffizienten unlesbar. Die
  sasmodels-Fassung ist die direkte Übertragung von Hayters Fortran-Code.
- Physikalische Konstanten wie in sasmodels (vergleichbar mit SasView). Die
  Gegenionen der Makroionen gehen als einwertig in die Ionenstärke ein.
- **Laufzeit:** ≈ 0.2 ms pro S(q).
- **Validierung:**
  - sasmodels-Referenzwerte (R = 20.75 Å, z = 19, φ = 0.0192, salzfrei; mit
    Rescaling): Abweichung 3.7·10⁻⁶ bei 6-stelliger Tabellengenauigkeit
  - SasView-Kurve `sphere@hayter_msa` (R = 140 Å, φ = 0.2, z = 19, T = 318.16 K,
    1 mM Salz, ε_r = 71.08): Abweichung 1.6·10⁻⁸
  - Grenzfall z → 0 ergibt den PY-Strukturfaktor (Abweichung ∝ z²)
- Die Lösung existiert numerisch nicht für z ≲ 10⁻³ und nicht für einzelne Fälle mit
  z ≈ 200 bei hohem Salz. Die Ladungsgrenzen sind daher 0.01 … 200 e, ebenfalls wie in
  sasmodels; Parametersätze ohne Lösung ergeben MD = ∞.

#### 2. Modell „Geladene Kugeln, RMSA“ im GIFT-Dialog

- **Parameter:** φ, R_HS, Ladung z (frei); Temperatur T, Konzentration 1:1-Salz und
  ε_r (standardmäßig **fest**, einzeln freigebbar). Standard für ε_r ist Wasser bei
  25 °C (78.30, nach Malmberg & Maryott).
- **Abgeleitete Größen** in der Ergebnisanzeige und im Sidecar: Debye-Länge,
  κσ, Kontaktpotential βU(σ) und der Rescaling-Faktor σ'/σ.
- Neue Flags:
  - **Ladung und Salz gleichzeitig frei:** Warnung, weil beide nicht unabhängig
    bestimmbar sind [F00]
  - **Rescaling aktiv:** Hinweis
- Fritz et al. (2000) nennen das gemittelte RMSA-Modell instabil und werten monodispers
  aus. Das Modell ist daher bewusst monodispers.

#### 3. BSSA-Mehrfachstart

Bei geladenen Systemen hat die MD-Fläche ausgeprägte Nebenminima. Auf der SasView-Kurve
lag ein Tal bei φ → 0.005, R_HS → Rand, z ≈ 49 mit MD = 0.73; das globale Minimum liegt
bei MD ≈ 2·10⁻⁹. Ein einzelner BSSA-Lauf fand das globale Minimum nur in 1 von 5 Seeds.

- Im ersten Zyklus laufen jetzt mehrere unabhängige BSSA-Suchen: Lauf 0 ab den
  Startwerten, weitere ab zufälligen Punkten im Suchbereich. Die beste wird übernommen.
  Standard: **4 Starts** (harte Kugeln), **8 Starts** (RMSA).
- Neues Flag **„Mehrfachstart“**: meldet, in wie vielen Läufen das beste Minimum
  erreicht wurde. Nur 1 von n ergibt eine Warnung.
- Mit 8 Starts findet der völlig freie Fit das globale Minimum in 5 von 5 Seeds. Mit
  festem φ, etwa aus der Einwaage, ist die Suche vollständig robust.
- Seeds und Startpunkte stehen im Sidecar (`multistart`, `reproducibility`).

#### 4. Validierung GIFT für geladene Systeme

| Fall | Ergebnis |
|---|---|
| SasView `sphere@hayter_msa`, φ fest = 0.2 | R_HS = 14.00 nm, z = 19.00 ± 0.05 e, Rg exakt |
| wie oben, φ fest = 0.22 (10 % daneben) | kompensiert durch R_HS = 14.6 nm, z = 16 e; Rg bleibt exakt |
| Simulation nach Fritz 2000 (R = 2.5 nm, φ = 0.05, z = 25, 10 mM, 2 % Rauschen) | φ = 0.044–0.055, R_HS = 2.40–2.58 nm, z = 24–26 e; Rg auf 0.3 %; IFT ohne S(q): Rg = NaN, MD ≈ 70 |

### 📦 Neue / geänderte Dateien (7.10.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/rmsa.py` | **neu** — HP-MSA/RMSA (Portierung aus sasmodels) |
| `analysis/gift/structure_factors.py` | Modell `rmsa`; `ParamSpec.fixed_default`; `StructureFactorModel.info`, `default_starts` |
| `analysis/gift/gift.py` | Mehrfachstart, `fixed=None` → Modellstandard, `model_info`, `starts` |
| `analysis/gift/diagnostics.py` | Flags `gift_multistart`, `gift_rmsa_degenerate`, `gift_rmsa_rescaled` |
| `analysis/gift/pipeline.py` | Sidecar: `model_info`, `multistart`; Reproduzierbarkeit inkl. Startregeln |
| `dialogs/gift_dialog.py` | Modell RMSA, fixe Standardparameter, Anzeige der abgeleiteten Größen |
| `i18n/translations/de.json`, `en.json` | Modell- und Flag-Texte |
| `tests/analysis/test_gift_rmsa.py` | **neu** — 12 Tests (sasmodels-Werte, SasView-Kurve, PY-Grenzfall, Rescaling, GIFT) |
| `THIRD_PARTY_NOTICES.md` | **neu** — BSD-3-Hinweis sasmodels |
| `core/version.py` | `7.9.0` → `7.10.0`; `analysis.gift` 0.2.0 → 0.3.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 75 Tests (≈ 36 s).

### ⚠️ Bekannte Einschränkungen

- **Laufzeit:** Die Mehrfachstarts laufen noch sequentiell, bei RMSA mit 8 Starts etwa
  10 s. Die Parallelisierung folgt in Phase 3c.
- **Mehrdeutigkeit:** Bei freiem φ, R_HS und z bleibt die aus [F00] bekannte
  Mehrdeutigkeit bestehen. Die Flags weisen darauf hin; die statistische Aussage
  liefert DREAM in Phase 3d.
- **Weitere Closures:** HNC und Rogers-Young sind noch nicht enthalten (Phase 5).

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.10 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die SasView-Referenzkurven
stammen vom Projektinhaber; die RMSA-Numerik ist eine gekennzeichnete Portierung aus
sasmodels (BSD-3).

---

*Letzte Aktualisierung: 2026-09-23*
