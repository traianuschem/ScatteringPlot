# Changelog — Version 8.0

## Version 8.0.0 — ScatterForge Plot (MAJOR RELEASE)

**Release Date:** 24. September 2026
**Status:** Stable Release — Weitere Glatter-Auswertungen (Phase 6); Abschluss des GIFT-Moduls

Mit Phase 6 ist das GIFT-Modul (v7.8–v7.14: IFT, GIFT mit Strukturfaktoren, BSSA,
Parallelisierung, DREAM, Explorer, weitere Strukturfaktoren) vollständig; das rechtfertigt
den Sprung auf **8.0.0**. Bugfixes folgen als 8.0.x.

Phase 6 des GIFT-Moduls (Planung: `docs/GIFT/PLAN.md`): Querschnitts- und Dicken-IFT,
Größenverteilungen per IFT und DECON (radiales Kontrastprofil aus p(r), auch für
polydisperse Teilchen).

Quellen (`GIFT/0_Sources/`):
- [G79] Glatter, *J. Appl. Cryst.* **12** (1979) 166 — Interpretation von p(r)
- [G80a] Glatter, *J. Appl. Cryst.* **13** (1980) 7 — Größenverteilungen per IFT
- [G80b] Glatter, *J. Appl. Cryst.* **13** (1980) 577 — lamellare und zylindrische Teilchen
- [G81] Glatter, *J. Appl. Cryst.* **14** (1981) 101 — Faltungswurzel (DECON)
- [GH84] Glatter & Hainisch, *J. Appl. Cryst.* **17** (1984) 435 — Überlappungsintegrale,
  Stufenmodell
- [MG98] Mittelbach & Glatter, *J. Appl. Cryst.* **31** (1998) 600 — DECON für
  polydisperse Teilchen

### ✨ IFT-Arten (`analysis/gift/kernels.py`)

Die IFT hat eine wählbare **Auswertung** (Dialog: IFT-Gruppe, Einstellung `IFTSettings.kind`).
Alle Arten verwenden dieselbe Maschinerie: Spline-Basis, λ-Wahl (Wendepunkt oder Evidenz),
Fehler, Kennzahlen, Explorer, GIFT mit S(q), DREAM (inkl. Dmax-Variation über eine
verallgemeinerte Skalierungstabelle) und Export.

| Art | Ergebnis | Kern | Kenngrößen |
|---|---|---|---|
| `pddf` | p(r) | 4π sin(qr)/(qr) | I(0), Rg (wie bisher) |
| `cross_section` | p_c(r), lange Zylinder | (π/q)·2π J₀(qr) [G80b Gl. 15b] | I_c(0), R_c; homogen R = √2·R_c |
| `thickness` | p_t(r), Lamellen | (2π/q²)·2 cos(qr) [G80b Gl. 15a] | I_t(0), R_t; homogen T = √12·R_t; p_t(0) ≠ 0 (Basis links frei) |
| `size_sphere` / `size_sphere_n` | D_V(R) bzw. D_N(R), Kugeln | v^k(R)·[3(sin x − x cos x)/x³]² [G80a Gl. 1] | Rg des Ensembles, I(0) |
| `size_cylinder` / `_n` | D_V(R) / D_N(R), lange Zylinder | (π/q)·v^k·[2J₁(x)/x]² | R_c des Ensembles |
| `size_lamella` / `_n` | D_V(T) / D_N(T), Lamellen | (2π/q²)·v^k·[sin(x/2)/(x/2)]² | R_t des Ensembles |

- **Größenverteilungen** (`sizes.py`): Primärgröße ist wahlweise die Volumenverteilung D_V
  oder die **Anzahlverteilung D_N**. Letztere ist in [G80a] die Primärgröße und wird
  direkt bestimmt, ohne instabile Division durch R³. Die übrigen Verteilungen (D_V, D_N,
  D_I) werden abgeleitet. Momente ⟨R⟩_V, σ_V, ⟨R⟩_N, σ_N mit Fehlern. Eine aus D_V
  abgeleitete D_N wird nur für R ≥ π/q_max und D_V ≥ 2σ ausgewertet.
- **Negative Werte** in D(R) werden, wie in [G80a], nicht unterdrückt: Sie sind für sehr
  schmale Verteilungen nötig. Eine falsche Formannahme verschiebt D(R), bricht die
  Rechnung aber nicht ab.
- **Grenzen:** Bei Radius-Verteilungen ist der größte Abstand 2·R_max. Die Grenze π/q_min,
  die Shannon-Kanäle und der Dmax-Vorschlag rechnen das mit (π/(2 q_min)); das entspricht
  R_max < π/(α·h₁) in [G80a].
- **Guinier** passend zur Art: ln(qI) für Querschnitte, ln(q²I) für Dicken [G80b Gl. 11].
  Ist der Anfangsbereich für das Rauschen zu flach, wird er vergrößert.
- **Export:** Jede Art hat eine eigene Dateikennung (`probe-xs_GIFT_pr.dat`, `-thk`,
  `-sizeS`, `-sizeSn`, …). Die Kopfzeilen enthalten Art, äquivalente Größe bzw.
  Verteilungsmomente, bei Größenverteilungen auch Spalten für die abgeleiteten
  Verteilungen. Die Provenance speichert `kind`, und „Aus Sidecar laden“ stellt die Art
  wieder her.

### 🧅 DECON (`analysis/gift/decon.py`, Tab „DECON“)

Radiales Kontrastprofil als Faltungswurzel von p(r). Die Geometrie folgt aus der Art: Kugel
für p(r), Zylinderquerschnitt für p_c(r), symmetrische Lamelle für p_t(r).

- **Überlappungsintegrale exakt** [GH84 Anhang]: V_ik(r) = r^(dim−1)·[μ(e_i,e_k) −
  μ(e_i,e_{k−1}) − μ(e_{i−1},e_k) + μ(e_{i−1},e_{k−1})]. Dabei ist μ das Schnittvolumen zweier
  Kugeln, die Schnittfläche zweier Kreise bzw. die Schnittlänge zweier Strecken.
  Geprüft: homogene Kugel (10⁻¹⁰), Kreisscheibe nach Porod (10⁻¹⁵), Strecke (exakt),
  Fourier-Konsistenz p(r) ↔ Amplitude für alle Geometrien, auch polydispers (10⁻⁶).
- **Basis:**
  - Standard sind kubische B-Splines [MG98 §2.2], intern in 4 feine Stufen je
    Knotenintervall zerlegt.
  - Wahlweise äquidistante Stufen [G81].
  - Die Stufenbreite entspricht standardmäßig dem Knotenabstand der IFT [G81 §III.1].
- **Anpassung** [G81 Gl. 7–19]:
  - gewichtete kleinste Quadrate gegen p(r) ± σ, linearisiert und iterativ gelöst
    (Levenberg-Marquardt);
  - Stabilisierung B + λK;
  - Startprofil konstant mit ∫p̃ = ∫p [G81 Gl. 5].
  - Zusätzlich werden weitere Startprofile gerechnet, um mehrdeutige Lösungen zu erkennen;
    solche Alternativen werden gezeigt und exportiert.
- **λ nach der Wendepunkt-Methode** [G81 §III.2]: Gewählt wird das Plateau von N_c vor dem
  steilen Anstieg der Abweichung. Anders als in der IFT zählt der linke Scanrand nicht als
  Plateau, weil die Lösung dort ungeglättet ist. Ohne inneres Plateau wird die stärkste
  Glättung gewählt, bei der p(r) noch beschrieben wird.
- **Polydispersität** [MG98 §2.3]:
  - Die Überlappungsmatrix wird über eine Anzahlverteilung gemittelt,
    V^P(r) = ∫ D(P,x) x^(2dim−1) V(r/x) dx. Verfügbar sind eine verschobene
    Schulz-Verteilung (Modus 1, [MG98 Gl. 10]) und eine Gauß-Verteilung.
  - Der Scan P = 0–40 % bestimmt die Breite aus dem Minimum der mittleren Abweichung
    [MG98 Fig. 2d]; P = σ·√(2 ln 2).
  - Das Profil gilt dann für die häufigste Teilchengröße.
  - Der Scan läuft im Dialog im Hintergrund, etwa 0.5–2 min.
- **Stufenmodell** [GH84 §II]: 2–4 Stufen mit variablen Breiten (Gitter + Simplex), mit
  derselben Polydispersität. Ergibt direkt Kern- und Außenradius.
- **Kontrolle:**
  - MD(p) = √(χ²/M) gegen p(r) [G81 Gl. 20]. Ein großer Wert zeigt fehlende Symmetrie
    bzw. Polydispersität an [G81 „Test der Symmetrie“].
  - MD(I) gegen die entschmierte IFT-Kurve bzw. den GIFT-Fit [MG98].
- **Export:** `_GIFT_decon.dat` mit x, Δρ, σ, Alternativen und Stufenmodell. Der Kopf
  nennt P und die Stufengrenzen. Dazu kommt die Provenance-Aktivität `decon`.

### 🚩 Neue Flags

| Flag | Bedeutung |
|---|---|
| `size_distribution.negative` (Warnung) | D(R) zu > 10 % negativ: sehr schmale Verteilung, falsche Formannahme oder ungeeignetes R_max/λ [G80a] |
| `cross_section_lowq.rising` (Warnung) | q·I bzw. q²·I steigt am Anfang des Fitbereichs: endliche Länge/Fläche, q_min erhöhen; quantitativ nur für Länge/Querschnitt ≥ 10 [G80b] |
| `decon_ambiguous.several` (Warnung) | weitere, deutlich verschiedene Profile beschreiben p(r) ähnlich gut |
| `decon_fit.worse` / `worse_poly` (Warnung) | MD(p) > 3: Polydispersität (→ P-Scan) bzw. auch mit Polydispersität keine Symmetrie [G81] |
| `decon_poly.found` (Info) / `.boundary` (Warnung) | gefundene Polydispersität bzw. Minimum am Rand des Scanbereichs |

### 🔎 Validierung und Befunde

- **Querschnitt, Dicke, Größenverteilungen:** R_c, R_t, I_c(0), I_t(0), p_t(0) = T sowie
  Mittelwert und Breite von D_V und D_N werden aus simulierten Daten auf 1–2 % (Breite
  von D_N: 15 %) zurückgewonnen, ebenso R_c eines endlichen Zylinders (L = 20 R). Ist
  q_min zu klein, meldet `cross_section_lowq` das, und R_c ist dann falsch.
- **DECON monodispers:** Kern-Schale mit Kontrastumkehr (Kern −0.6) auf ±0.1. Das
  Stufenmodell trifft Grenzen und Kontraste exakt (6.0/10.0 nm, −0.60), wie in [GH84].
- **DECON polydispers** [MG98-Simulation]:
  - Schulz-Verteilung σ = 0.1 / 0.2 / 0.3: der P-Scan findet 0.10 / 0.20 / 0.27–0.29.
  - Profil und Stufenmodell (6.1/9.9 nm, −0.59) stimmen bis σ = 0.2.
  - Die monodisperse Auswertung versagt dort (MD(p) 20–80 statt 1–4).
- **SasView-Referenz Kern-Schale + Sticky Hard Sphere** (vom Nutzer bereitgestellt):
  - GIFT: φ = 0.100, R_HS = 50.6 nm, τ = 0.400.
  - DECON: Kern:Schale 2.00.
  - Stufenmodell: 33/50.6 nm, Verhältnis 2.0.
- **Symmetrische Doppelschicht:** Das glatte Profil ist mehrdeutig; das Flag meldet es, und
  die richtige Lösung ist unter den Alternativen. Das Stufenmodell trifft 2.0/3.0 nm.
- **ESRF-Daten:**
  - **20 °C:** Der P-Scan findet P = 28 % mit deutlichem Minimum. p(r) wird einschließlich
    des Ausläufers beschrieben (MD(p) 1.25; monodispers 10). Profil: dichter Kern bis
    ≈ 22–25 nm, dazu eine Hülle mit sehr geringem Kontrast (Stufenmodell: 5 % des Kerns,
    außen ≈ 57 nm).
  - **60 °C und 20 °C nach Heizen:** Das Minimum liegt am Rand (P ≥ 40 %). Die Teilchen
    sind dort stark polydispers oder nicht kugelsymmetrisch; das Flag meldet es.
  - **Größenverteilung „homogene Kugeln“:** stark negativ, die Form passt nicht.

### 📦 Neue / geänderte Dateien (8.0.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/kernels.py` | **neu** — Transformationskerne (9 Arten), Vorwärtswerte, Beschriftungen |
| `analysis/gift/sizes.py` | **neu** — Verteilungen und Momente |
| `analysis/gift/decon.py` | **neu** — DECON (exakte Überlappungsintegrale, Polydispersität, Stufenmodell) |
| `analysis/gift/splines.py` | `left_free` (p(0) frei) |
| `analysis/gift/transform.py` | Designmatrix je Art, `make_basis`, `moment_vectors` |
| `analysis/gift/ift.py` | `IFTSettings.kind`, Rg/I(0) je Art, Regularisierung mit freiem linken Rand |
| `analysis/gift/likelihood.py`, `uncertainty.py` | Skalierungstabelle und Posterior-Prädiktion für alle Arten |
| `analysis/gift/explorer.py`, `batch.py` | Kennzahlen und Dmax-Vorschlag je Art |
| `analysis/gift/diagnostics.py` | Grenzen je Art, Guinier 1D/2D, neue Flags |
| `analysis/gift/pipeline.py` | Art in Provenance/Export, `run_decon_analysis`, `run_step_model_analysis` |
| `dialogs/gift_dialog.py` | Auswahl der Art, Beschriftungen/Plots, DECON-Tab mit Hintergrund-Worker |
| `i18n/translations/de.json`, `en.json` | Texte |
| `tests/analysis/test_gift_kinds.py`, `test_gift_decon.py` | **neu** — 13 + 10 Tests |
| `core/version.py` | `7.14.0` → `8.0.0`; `analysis.gift` 0.7.0 → 0.8.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 150 Tests (≈ 150 s).

---

## Version 8.0.1 — Bugfix

**Release Date:** 24. September 2026

### 🐞 Fix: Fehlerspalte fälschlich verworfen, wenn einzelne σ = 0 sind

Im GIFT-Dialog wurde die Fehlerspalte eines Datensatzes komplett verworfen (Anzeige
„keine Fehlerspalte — wird geschätzt"), sobald **ein einziger** Datenpunkt σ ≤ 0 hatte —
z. B. bei ASAXS-Separationsergebnissen, bei denen einzelne q-Bins eine degenerierte
Varianz von genau 0 ergeben. Die Spaltenzuordnung selbst (`col_x`/`col_y`/`col_err`) war
davon nicht betroffen und funktionierte bereits korrekt.

- `dataset_arrays()` (`dialogs/gift_dialog.py`) schließt jetzt nur noch die einzelnen
  Punkte mit σ ≤ 0 aus (analog zur bestehenden Behandlung von q ≤ 0 / nicht-finiten
  Werten), statt die gesamte Fehlerspalte zu verwerfen.
- Betroffen waren u. a. ESRF-ASAXS-Separationsdateien mit vereinzelten σ = 0 Punkten.

| Datei | Änderungen |
|-------|------------|
| `dialogs/gift_dialog.py` | `dataset_arrays()`: σ ≤ 0 punktweise statt spaltenweise ausschließen |
| `core/version.py` | `8.0.0` → `8.0.1` |

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v8.0 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben.

---

*Letzte Aktualisierung: 2026-09-24*
