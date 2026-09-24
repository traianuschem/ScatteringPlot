# Changelog — Version 7.12

## Version 7.12.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — Statistische Absicherung der IFT/GIFT-Parameter (DREAM)

Phase 3d des GIFT-Moduls (Planung: `docs/GIFT/PLAN.md` §2.3).

### ✨ Neue Features & Verbesserungen (7.12.0)

#### 1. Marginale Likelihood (`analysis/gift/likelihood.py`)

- Bayes'sche IFT nach Hansen (2000): Die Spline-Koeffizienten c werden bei festen
  nichtlinearen Parametern θ = (S(q)-Parameter, λ, Dmax) **analytisch herausintegriert**:
  log p(I|θ) = −½χ²(ĉ) − ½λĉᵀKĉ − ½ log det(B+λK) + ½ log det(λK) + const.
  Der Sampler muss damit nur 2–5 Größen abtasten statt 25–150 Koeffizienten.
- Geprüft gegen die direkte Gauß-Marginale N(0, Σ_σ + A(λK)⁻¹Aᵀ) (Abweichung < 10⁻⁶).
- **Dmax als Parameter ohne neue Quadratur:** Die Knoten skalieren mit Dmax, daher
  ψ_ν(q; Dmax) = Dmax·g_ν(q·Dmax). g_ν und g_ν' werden einmal tabelliert und kubisch
  (Hermite) interpoliert; relativer Fehler 2·10⁻⁹ gegenüber der Quadratur.
- λ wird wie in der IFT relativ abgetastet (log₁₀ λ_rel), der Untergrund wie in der IFT
  herausprojiziert (flache Priorverteilung). Optional eine gaußsche Priorverteilung je
  Parameter (z. B. φ aus der Einwaage).
- Batch-fähig; die Auswertung läuft im Prozess-Pool aus v7.11 in Blöcken fester Größe.

#### 2. DREAM(ZS)-Sampler (`analysis/gift/dream.py`)

- Eigene numpy-Implementierung nach ter Braak & Vrugt (2008) / Vrugt (2016), keine neue
  Abhängigkeit: Differential-Evolution-Vorschläge aus einem Archiv vergangener Zustände,
  Randomized Subspace Sampling mit adaptiven CR-Wahrscheinlichkeiten, Snooker-Updates,
  γ = 1 für Sprünge zwischen Modi, Ausreißer-Ketten (IQR), periodische Randbehandlung.
- **Zwei Phasen:** Einlauf (mit Adaption) bis R̂ < Ziel, danach Sampling ohne Adaption,
  bis R̂ < Ziel über die Stichprobe *nach* dem Einlauf und mindestens 5000 Zustände
  vorliegen. Beim Übergang werden die Priorpunkte aus dem Archiv entfernt.
- **Befund:** Die zunächst geplante Standardregel (R̂ über die zweite Hälfte, Archiv mit
  Priorpunkten) meldete bei GIFT zu früh Konvergenz, als eine Kette noch im Dmax-Ausläufer
  lag (95 %-Obergrenze 28.9 nm statt 20.4 nm im langen Referenzlauf). Mit der
  Zwei-Phasen-Logik stimmen kurze Läufe mit dem Referenzlauf (120 000 Auswertungen)
  überein; die Akzeptanzrate steigt von 6 % auf 12–30 %.
- Validierung (Plan Test 9): korrelierte Gaußverteilung (Mittelwert, Kovarianz),
  bimodale Verteilung (Gewicht 1/3 und zwei erkannte Modi), Haario-Banane (lange Läufe
  treffen σ(x₂) = 13.17 gegenüber analytisch 13.19).

#### 3. Unsicherheitsanalyse (`analysis/gift/uncertainty.py`, `screening.py`)

- Ablauf: **LHS-Screening** der Posterior-Landschaft (100·d Punkte, parallel) → Archiv und
  Startpunkte für DREAM (beste Screening-Punkte und BSSA-/IFT-Optimum) → DREAM →
  **Posterior-Prädiktion** (400 Ziehungen θ, je Ziehung c ~ N(ĉ, (B+λK)⁻¹)).
- Ergebnisse: Median, 68-/95-%-Intervalle, MAP, Korrelationsmatrix, Zahl der Modi je
  Parameter (1D-KDE), Bänder für p(r), I_fit(q), P(q), S(q), Verteilungen von Rg und I(0).
- Standard-Priorgrenzen: S(q)-Parameter wie der BSSA-Suchbereich, log λ_rel = Optimum
  ± 4 Dekaden, Dmax = 0.75 … 1.5 × Dmax; π/q_min optional als Dmax-Obergrenze (sonst
  nur Flag).
- Optional σ ← σ·√MD (wird als Flag und im Sidecar vermerkt).
- **Bitgleich für jede Worker-Zahl ≥ 1** (alle Zufallszahlen im Hauptprozess, feste
  Blockgröße, einfädiges BLAS im Pool); geprüft für 1/3/4/8 Worker.

#### 4. Flags (`diagnostics.diagnose_uncertainty`)

| Flag | Kriterium |
|---|---|
| `dream_convergence` | R̂ ≥ Ziel nach dem Budget (bzw. Einlauf nicht abgeschlossen) |
| `dream_identifiability` | Posterior-σ > 0.8 × Prior-σ |
| `dream_boundary` | > 10 % der Posterior-Masse in den äußeren 2 % des Priorbereichs |
| `dream_correlation` | \|ρ\| > 0.9 (z. B. φ–R_HS–z bei der RMSA [F00]) |
| `dream_multimodal` | mehrere getrennte Modi eines Parameters |
| `dream_reference` | BSSA-Optimum außerhalb des 95-%-Intervalls (Warnung) bzw. gewähltes λ/Dmax außerhalb (Hinweis) |
| `dream_dmax_qmin` | Dmax-Posterior vs. π/q_min (Median darüber: Warnung; 97.5 % darüber: Hinweis) |
| `dream_sigma`, `dream_acceptance` | σ skaliert; Akzeptanzrate < 5 % |

#### 5. Dialog

- Neue Gruppe **„Unsicherheit (DREAM)“**: Tabelle der abtastbaren Größen (abtasten,
  Grenzen, gaußsche Priorverteilung μ/σ), „Standardgrenzen“, π/q_min als Dmax-Grenze,
  σ-Skalierung, Ketten, Budget, R̂-Ziel, Seed, Knopf **„Unsicherheit bestimmen“**
  (Hintergrund-Thread, Fortschritt mit R̂ und Akzeptanz, abbrechbar).
- Neuer Tab **„Unsicherheit“** mit Übersicht (Tabelle Optimum/Median/68 %/95 %/R̂/MAP,
  Rg und I(0) mit Intervall), Corner-Plot, Ketten (Einlauf grau) und Bändern.
- Ergebnisse und Flag-Liste enthalten die DREAM-Werte. Während einer Rechnung bleibt
  die Analyse unverändert; spätere Änderungen verwerfen ein veraltetes DREAM-Ergebnis.
- „Einstellungen aus Sidecar…“ stellt auch die DREAM-Einstellungen wieder her, wiederholt
  die Analyse automatisch und vergleicht die Posterior-Mediane (bitgleich reproduziert).
- „Übernehmen“ rechnet eine reine IFT nur noch neu, wenn sich Einstellungen geändert
  haben (sonst ginge ein DREAM-Ergebnis verloren).
- Korrektur: Der I(q)-Plot erzeugte bei jedem Neuzeichnen eine tight_layout-Warnung.

#### 6. Export und Provenance

- `<stem>_GIFT_dream.npz`: Ketten, log-Dichten, Akzeptanz, Einlauf, R̂-Verlauf,
  Screening, Bänder, Rg-/I(0)-Stichproben, `record_id`.
- `<stem>_GIFT_pr_band.dat`: r, Median, 2.5/16/84/97.5-%-Quantile von p(r) (wird von
  ScatteringPlot per Namen als P(r) erkannt).
- Sidecar: Aktivitäten `screening` und `dream` (Priorverteilung, Einstellungen, Seeds,
  R̂, Akzeptanz, Intervalle, Korrelationen, Modi), DREAM-Flags, Reproduzierbarkeit
  (DREAM-Seed, SeedSequence-Entropie für Screening und Prädiktion, Blockgröße). Der
  Header aller Ergebnisdateien enthält eine DREAM-Zeile.

### 📊 Beispiele

| Daten | Ergebnis (Median [95 %]) | Sollwert |
|---|---|---|
| Kugel R = 10 nm, 2 % Rauschen, IFT | Dmax 19.58 [19.28, 20.43] nm, Rg 7.746 [7.744, 7.749] nm | 20 nm, 7.746 nm |
| Kugel + S_ave (φ 0.15, R_HS 10, μ 0.4), GIFT | φ 0.148 [0.143, 0.151], R_HS 10.0 [9.82, 10.19], μ 0.393 [0.368, 0.413], Dmax 19.6 [19.2, 20.3] | alle im Intervall |
| SasView RMSA (R 140 Å), φ fest | R_HS 14.00 [13.99, 14.02] nm, z 19.04 [18.97, 19.16], Dmax 27.86 nm | 14 nm, 19, 28 nm |
| dieselbe Kurve, φ frei | φ 0.2005 [0.1988, 0.2025]; Flag φ–R_HS (+0.95), φ–z (−0.93) | Mehrdeutigkeit nach [F00] |

Laufzeit: 5–10 s (HS, N = 25), ≈ 30 s (RMSA, N = 120, 500 Punkte). Bei HS bringt der
Pool nur ≈ 1.3× (Auswertung ≈ 0.3 ms, Prozesswechsel pro Generation ähnlich teuer); er
lohnt sich bei teureren Modellen (Phase 5: HNC/RY).

### 📦 Neue / geänderte Dateien (7.12.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/likelihood.py` | **neu** — ScaledBasisTable, ParameterSpace, MarginalLikelihood, Pool-Auswertung |
| `analysis/gift/dream.py` | **neu** — DREAM(ZS), Gelman-Rubin R̂, Latin Hypercube |
| `analysis/gift/screening.py` | **neu** — LHS-Screening |
| `analysis/gift/uncertainty.py` | **neu** — UncertaintySettings/-Result, run_uncertainty, Posterior-Prädiktion, Modi |
| `analysis/gift/diagnostics.py` | `diagnose_uncertainty()` |
| `analysis/gift/pipeline.py` | `IFTAnalysis.uncertainty`, `all_flags`, `run_uncertainty_analysis()`, Export von npz/Band, Sidecar-Aktivitäten |
| `dialogs/gift_dialog.py` | Gruppe und Tab „Unsicherheit“, `_DreamWorker`, Sidecar-Wiederholung mit DREAM |
| `i18n/translations/de.json`, `en.json` | `gift.dream_*`, DREAM-Flags |
| `tests/analysis/test_gift_dream.py` | **neu** — 16 Tests |
| `core/version.py` | `7.11.0` → `7.12.0`; `analysis.gift` 0.4.0 → 0.5.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 97 Tests (≈ 66 s).

### ⚠️ Hinweise

- Die Intervalle gelten unter der Annahme korrekter Fehlerbalken. Bei geschätztem σ
  oder MD ≠ 1 ist „σ mit √MD skalieren“ sinnvoll.
- Das von DREAM bevorzugte λ (Evidenz-Maximum) liegt typischerweise 0.5–1 Dekade unter
  dem Wendepunkt-λ; das Flag `dream_reference` (Hinweis) macht das sichtbar.
- Bei den S_ave-Parametern gelten die Intervalle für scheinbare Modellparameter [W99].

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.12 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben.

---

*Letzte Aktualisierung: 2026-09-23*
