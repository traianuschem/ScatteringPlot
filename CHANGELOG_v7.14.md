# Changelog — Version 7.14

## Version 7.14.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — Weitere Strukturfaktoren für GIFT

Phase 5 des GIFT-Moduls (Planung: `docs/GIFT/PLAN.md`). Umfang nach Absprache: S_eff nach
Vrij (Schulz-Verteilung wie in der Quelle), Stäbchen, klebrige harte Kugeln (Baxter),
fraktales Aggregat; keine Kombinationen. HNC/Rogers-Young ist zurückgestellt; DECON,
Größenverteilung sowie Querschnitts- und Dicken-IFT folgen in Phase 6.

### ✨ Neue Strukturfaktoren (`analysis/gift/sf_models.py`)

| Modell | Parameter | Umsetzung | Validierung |
|---|---|---|---|
| **S_eff nach Vrij** (`hs_vrij`) | φ, R_HS, μ (Schulz, rel. Standardabweichung) | PY-Lösung für Mischungen harter Kugeln (Baxter-Faktorisierung; Vrijs Lösung für Streuamplituden), Amplituden homogener Kugeln, Schulz-Verteilung mit 24 Gauß-Legendre-Knoten, S_eff = I/(n·P̄) [W99 Gl. 4–7] | 1 Komponente = PY exakt (10⁻¹⁵); zwei identische Spezies = eine; Kompressibilität der Mischung = PY-Zustandsgleichung (10⁻⁹); S_eff(0) steigt mit μ wie in [W99 Fig. 2/3]; GIFT gewinnt φ, R, μ zurück |
| **Klebrige harte Kugeln** (`sticky`) | φ, R_HS, τ (= SasView `stickiness`), δ (= SasView `perturb`, standardmäßig fest 0.05, editierbar) | Portierung von sasmodels `stickyhardsphere` (Menon et al. 1991, BSD-3) | identisch mit sasmodels (10⁻¹⁴) inkl. der sasmodels-Testwerte; GIFT gewinnt φ, R, τ zurück |
| **Fraktales Aggregat** (`fractal`) | r₀ (frei, Startwert aus Rg), D_f, ξ | Teixeira (1988, Gl. 15), wie sasmodels `fractal_sq` | identisch mit sasmodels (10⁻⁸); GIFT gewinnt r₀, D_f, ξ zurück, wenn q_min·ξ ≲ 2 |
| **Stäbchen** (`rod`) | c, L, μ_L | Mean-Field nach van der Schoot [W99 Gl. 16–17], Längenverteilung mit Gauss-Hermite | S(0) = 1/(1+2c), c = 0 → 1, monoton wie [W99 Fig. 5] |

- Laufzeit je S(q)-Auswertung: Vrij ≈ 14 ms (24 Komponenten × 24 Komponenten je q),
  die übrigen < 0.5 ms. GIFT mit Vrij dauert daher ≈ 15–20 s (4 Starts im Pool), DREAM
  einige Minuten.
- **„Startwerte aus IFT“** folgt jetzt einer Regel je Parameter (`ParamSpec.start_rule`):
  Radien aus Rg (√(5/3)·Rg), ξ = 10·Radius, Stäbchenlänge = Dmax.
- DREAM, Explorer, Serie und Sidecar unterstützen die neuen Modelle ohne Sonderbehandlung.

### 🚩 Neue Flags

| Flag | Bedeutung |
|---|---|
| `gift_sticky.no_attraction` (Info) | τ läuft an die obere Grenze: keine Anziehung nachweisbar, das Modell entspricht harten Kugeln. Die allgemeine Randwarnung entfällt dann. |
| `gift_sticky_coupled` (Warnung) | δ und τ gleichzeitig frei (stark gekoppelt) |
| `gift_fractal.aggregate` (Info) | Zahl der Bausteine Γ(D+1)(ξ/r₀)^D und Rg des Aggregats; Hinweis auf die Kopplung r₀ ↔ p(r) |
| `gift_fractal.xi_unresolved` (Warnung) | q_min·ξ > 2: Guinier-Bereich der Aggregate nicht gemessen, ξ nicht bestimmbar |
| `gift_rod.degenerate` (Warnung) | siehe Befund unten |

### 🔎 Befunde

- **S_rod ist bei freiem p(r) kaum bestimmbar.** S_rod hängt nur über den
  Stäbchen-Formfaktor F(qL) von q ab, und das modellfreie p(r) kann den Strukturfaktor
  fast vollständig aufnehmen: Die MD ändert sich zwischen c = 0 und c = 10 um < 1 %. Das
  ist eine grundsätzliche Grenze der Kombination GIFT + S_rod, kein Programmfehler.
  Empfehlung (Flag): c aus der Konzentration vorgeben, c = (π/4)·n·L²·D.
- **Test an den ESRF-Daten** (20 °C / 60 °C / 20 °C nach Heizen, Dmax aus dem Vorschlag):
  - Klebrige Kugeln: τ läuft bei 20 °C und 60 °C an die obere Grenze, es ist also keine
    Anziehung nachweisbar. Nach dem Heizen ergibt sich τ ≈ 0.8, aber ohne Verbesserung
    gegenüber harten Kugeln.
  - Harte Kugeln (PY): MD 0.48 → 0.39 / 0.93 → 0.66 / 0.38 → 0.35 mit R_HS ≈ 114 / 95 /
    124 nm und φ ≈ 0.12–0.15, also schwache repulsive Korrelationen.
  - Vrij verbessert die MD weiter, aber mit hohem φ (0.37–0.53) und μ ≈ 0.2–0.3. Das ist
    vermutlich ein Hinweis auf die Kopplung φ ↔ μ und sollte mit DREAM geprüft werden.
  - Fraktal: ξ ist nicht auflösbar (q_min·ξ ≫ 2 bei q_min = 0.023 nm⁻¹); Aggregate
    größer als ~2/q_min ≈ 85 nm sind mit diesem q-Bereich nicht zu charakterisieren.

### 🛡️ Robustheit bei sehr kleinem λ

Der in v7.13 erweiterte λ-Scan kann λ_rel ≪ 10⁻¹⁴ liefern. Dort sind die
Normalgleichungen B + λK zu schlecht konditioniert:
- **GIFT-Zielfunktion** (`IFTProblem.md`/`md_batch`): Bei Kondition > ~10¹⁴ wird über QR
  des gestapelten Systems [Aw; √λ·Dᵀ] gelöst. Vorher war die Zielfunktion an allen
  Startpunkten ∞, und GIFT brach ab (ESRF „20 °C nach Heizen“, Dmax = 100 nm, fraktales
  Modell).
- **DREAM-Likelihood**: log det und ĉ über SVD, Dreiecksfaktor für die
  Posterior-Prädiktion per QR.
- GIFT-Zielfunktion, DREAM-Likelihood und IFT-Scan stimmen bis λ_rel = 10⁻²⁴ auf 10⁻⁶
  überein (Test). Gut konditionierte Fälle rechnen unverändert (bitgleich).

### 📦 Neue / geänderte Dateien (7.14.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/sf_models.py` | **neu** — Vrij (PY-Mischung, Schulz), Stäbchen, Baxter, Fraktal |
| `analysis/gift/structure_factors.py` | Registrierung `hs_vrij`, `sticky`, `fractal`, `rod`; `ParamSpec.start_rule` |
| `analysis/gift/ift.py` | `IFTProblem.md`/`md_batch`: QR-Rückfall bei schlechter Kondition |
| `analysis/gift/likelihood.py` | SVD-Rückfall (`_solve_svd`) |
| `analysis/gift/diagnostics.py` | Flags `gift_sticky`, `gift_sticky_coupled`, `gift_fractal`, `gift_rod` |
| `dialogs/gift_dialog.py` | Modellliste, Startwerte nach `start_rule` |
| `i18n/translations/de.json`, `en.json` | Modellnamen, neue Flags |
| `THIRD_PARTY_NOTICES.md` | sasmodels `stickyhardsphere` |
| `tests/analysis/test_gift_sf5.py` | **neu** — 13 Tests |
| `core/version.py` | `7.13.0` → `7.14.0`; `analysis.gift` 0.6.0 → 0.7.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 127 Tests.

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.14 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben.

---

*Letzte Aktualisierung: 2026-09-23*
