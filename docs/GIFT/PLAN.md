# GIFT/IFT-Modul für ScatterForge Plot (ScatteringPlot) — Plan

Stand: 2026-09-24 · Status: Entwurf v6 (+ q-Fitbereich per Signifikanz-Voreinstellung)

## 0. Entscheidungen (Runde 1)
| Punkt | Entscheidung |
|---|---|
| Kollimation | **Pinhole (Punktkollimation)**. Keine Spalt-Entschmierung nötig; die Schnittstelle für einen Verschmierungsoperator bleibt als optionale Erweiterung erhalten. |
| Umfang | **Erst IFT, dann GIFT** |
| Dmax > π/q_min | **Nur warnen**, die Rechnung läuft trotzdem |
| Einbindung | **Direkt in ScatteringPlot** als Unterpaket, ohne Plugin-Loader |
| Probensysteme | **Geladen**. Ein RMSA-Strukturfaktor (Hayter-Penfold / Hansen-Hayter) wird Teil des GIFT-Kernumfangs (Phase 3b) und nicht erst „später“. |
| Ergebnisablage | Unterordner `GIFT/` neben der Datendatei, im Dialog änderbar |
| Parameter-Screening | MC-basierte statistische Absicherung der finalen Parameter mit **DREAM(ZS)** (§2.3). Abgetastet werden **S(q)-Parameter + log λ + Dmax**. Start **auf Knopfdruck** („Unsicherheit bestimmen“), nicht automatisch. |
| q-Fitbereich | Wählbar: **Voller Bereich**, **1σ / 2σ / 3σ** (aus der vorhandenen Signifikanzanalyse) oder **manuell** (§2.0) |
| Provenance | JSON-Sidecar nach dem Vorbild des JADE-DLS-`ProvenanceRecord` (§4.3): **gleiche Feldstruktur, eigene Schema-URI** `gift-provenance/v1.0` |
| Parallelisierung | Vektorisierung über Ketten und Parametersätze, zusätzlich ein Prozess-Pool für unabhängige Aufgaben (§5) |

## 1. Ziel
Modellfreie Berechnung der Paarabstandsverteilung p(r) aus 1D-SAXS-Daten nach Glatter
(IFT, 1977). Die Erweiterung auf wechselwirkende Systeme (GIFT, I = P(q)·S(q)) folgt
Brunner-Popela & Glatter (1997) und Weyerich et al. (1999). Für die Parametersuche wird
BSSA nach Bergmann, Fritz & Glatter (2000) verwendet. Das Modul ersetzt die
Moore-Inversion (Sinusreihe), die SasView verwendet.

Quellen (`GIFT/0_Sources/`):
- [G77] Glatter (1977). *J. Appl. Cryst.* **10**, 415 — IFT, λ-Wendepunkt, Rg/I(0)
- [BP97] Brunner-Popela & Glatter (1997). *J. Appl. Cryst.* **30**, 431 — GIFT-Grundlagen, S_ave(q)
- [W99] Weyerich, Brunner-Popela & Glatter (1999). *J. Appl. Cryst.* **32**, 197 — S_eff, S_lma, S_dec, S_rod
- [B00] Bergmann, Fritz & Glatter (2000). *J. Appl. Cryst.* **33**, 1212 — BSSA
  (die Datei heißt `Bergmann2004.pdf`)
- [F00] Fritz, Bergmann & Glatter (2000). *J. Chem. Phys.* **113**, 9733 — GIFT für geladene Teilchen (RMSA, HNC, RY)
- [HP81] Hayter & Penfold (1981). *Mol. Phys.* **42**, 109 — MSA, analytisch
- [HH82] Hansen & Hayter (1982). *Mol. Phys.* **46**, 651 — RMSA (Rescaling bei kleinem φ)
- [V79] Vrij (1979). *J. Chem. Phys.* **71**, 3267 — PY für polydisperse HS-Mischungen (S_eff)
- [G79] Glatter (1979). *J. Appl. Cryst.* **12**, 166 — Interpretation von p(r)
- [G80a] Glatter (1980). *J. Appl. Cryst.* **13**, 7 — Größenverteilungen per IFT
- [G80b] Glatter (1980). *J. Appl. Cryst.* **13**, 577 — lamellare/zylindrische Teilchen
- [G81] Glatter (1981). *J. Appl. Cryst.* **14**, 101 — Faltungswurzel (DECON)
- [GH84] Glatter & Hainisch (1984). *J. Appl. Cryst.* **17**, 435 — Überlappungsintegrale, Stufenmodell
- [MG98] Mittelbach & Glatter (1998). *J. Appl. Cryst.* **31**, 600 — DECON für polydisperse Teilchen
- extern, nicht im Ordner: Vrugt (2016). *Environ. Model. Softw.* **75**, 273 (DREAM);
  ter Braak & Vrugt (2008). *Stat. Comput.* **18**, 435 (DREAM(ZS));
  Hansen (2000). *J. Appl. Cryst.* **33**, 1415 (Bayes'sche IFT, marginale Likelihood)

## 2. Mathematischer Kern

### 2.0 q-Fitbereich (gilt für IFT, GIFT, Screening und DREAM)
Die Auswahl erfolgt über eine Combo-Box im Dialog. Der gewählte Bereich wird als
graue Schattierung im I(q)-Plot und im Signifikanz-Mini-Plot des Dialogs angezeigt.

| Modus | q_min | q_max |
|---|---|---|
| Voller Bereich | erster Datenpunkt | letzter Datenpunkt |
| 1σ / 2σ / 3σ | erster Datenpunkt (oder manuell) | letztes q, bis zu dem die **geglättete** Signifikanz \|I/σ\| ≥ nσ bleibt |
| Manuell | Eingabe | Eingabe (Spinboxen und Ziehen der Grenzlinien im Plot) |

- **Gleiche Rechnung wie im Significance-Plot:** `_rolling_median()` und die
  |I/σ|-Berechnung werden aus `scatter_plot.py` in `analysis/significance.py`
  ausgelagert. Plot und GIFT verwenden dann exakt denselben Code und dasselbe
  Glättungsfenster (Standardwert aus dem Options-Panel, im Dialog änderbar).
- **Robustes Abschneidekriterium:** q_max ist der letzte Punkt vor der ersten Stelle,
  ab der die geglättete Signifikanz für mindestens k aufeinanderfolgende Punkte unter
  nσ liegt (k = halbes Glättungsfenster). Einzelne Rauschspitzen nach dem Abfall
  verlängern den Bereich damit nicht.
- **Nur q_max wird automatisch gesetzt.** Bei kleinen q ist |I/σ| praktisch immer
  hoch. Probleme dort, etwa Beamstop-Rand oder Parasitärstreuung, erkennt das
  Signifikanzkriterium nicht; q_min bleibt daher „erster Punkt“ oder manuell.
- Nach dem Voreinstellen lassen sich beide Grenzen manuell nachjustieren. Der Modus
  wechselt dann auf „Manuell (ausgehend von 2σ)“.
- **Ohne Fehlerspalte** sind die σ-Voreinstellungen deaktiviert, mit Tooltip-Hinweis.
- **Kopplung an die Flags:** q_min bestimmt die Grenze π/q_min des Dmax-Flags, und
  (q_max − q_min) bestimmt die Zahl der Shannon-Kanäle. Beide Anzeigen aktualisieren
  sich live, wenn der Bereich geändert wird.
- **Zusätzliches Flag:** weniger als ~2–3 Shannon-Kanäle im gewählten Bereich, oder
  mehr als 50 % der Punkte verworfen.
- **Provenance:** Die Aktivität `preprocessing` speichert Modus, Schwelle n, Fenster,
  k, die resultierenden q_min/q_max und die Anzahl der verworfenen Punkte. Damit lässt
  sich der Schnitt exakt reproduzieren.
- **DREAM:** Der q-Bereich bleibt während des Samplings fest. Optional lassen sich zum
  Vergleich zwei Läufe (z. B. 3σ vs. 1σ) gegenüberstellen, um die Empfindlichkeit
  der Parameter auf den Schnitt zu zeigen.

### 2.1 IFT [G77]
1. **Basis:** N kubische B-Splines φ_ν(r) mit äquidistanten Knoten auf [0, Dmax].
   Standardwert N = 20–30, einstellbar; die Obergrenze liegt laut [G77] bei etwa 30–40.
2. **Transformation:** ψ_ν(q) = 4π ∫₀^Dmax φ_ν(r) sin(qr)/(qr) dr. Das Integral wird mit
   Gauss-Legendre-Quadratur pro Spline-Segment berechnet, vektorisiert über alle q.
   Die Designmatrix A (M×N) wird pro (q-Gitter, Dmax, N) gecacht. Bei Pinhole wird
   kein Verschmierungsoperator angewendet; die entschmierte Kurve ist dann gleich der
   Fitkurve.
3. **Stabilisierter Least-Squares-Fit:** (B + λK)c = b mit B = AᵀWA, b = AᵀW·I_exp,
   W = diag(1/σ²) und K aus ersten Differenzen der Koeffizienten [G77 Gl. 14/15];
   Standard mit Randbedingung c₀ = c_{N+1} = 0 (siehe §10).
4. **λ_opt nach der Wendepunkt-Methode:** λ wird logarithmisch gescannt. Für jeden Wert
   werden N_c(λ) und MD(λ) berechnet [G77 Gl. 16]. λ_opt ist das Minimum von
   |d log N_c / d log λ| vor dem steilen Anstieg von MD. Ohne Wendepunkt gibt es ein
   Flag, denn [G77] nennt das als Hinweis auf Inkonsistenz. Der Dialog zeigt die Kurven
   log N_c(λ) und MD(λ) wie in [G77] Fig. 2, und λ lässt sich manuell übersteuern.
5. **Fehler:** Cov(c) = (B+λK)⁻¹ B (B+λK)⁻¹ ergibt σ-Bänder für p(r) und I_fit(q).
6. **Abgeleitete Größen:** Rg und I(0) aus p(r) [G77 Gl. 19/20] mit Fehlern; zum
   Vergleich der Guinier-Rg.
7. **Optional:** konstanter Untergrund als zusätzliche Basisfunktion. Laut [G77]
   verursacht ein nicht berücksichtigter Untergrund einen Anstieg von p(r) bei r→0.

### 2.2 GIFT [BP97, W99, B00]
- **Modell:** I(q) = Σ c_ν ψ_ν(q) · S(q; d) [BP97 Gl. 5–7]
- **Innere Schleife:** Die Spalten von A werden mit S(q; d) skaliert und dann wird die
  IFT aus 2.1 gelöst, jeweils mit eigenem λ-Scan. Das dauert nur Millisekunden.
- **Äußere Schleife:** MD(d) [B00 Gl. 4] wird mit BSSA minimiert (Nelder-Mead-Simplex
  plus thermisches Rauschen −kT·log z [B00 Gl. 5], entspricht `amebsa` aus Numerical
  Recipes):
  - Start-T aus den MD-Werten der Anfangsvertices
  - Abkühlen T ← (1−0.2)·T nach j Schritten, mit j = 20–40 abhängig von der Zahl der
    S(q)-Parameter
  - Unphysikalische Parameter erhalten MD = ∞ (0 < φ < 0.6, R_HS > 0, 0 ≤ µ < 1 usw.)
  - Bei T = 0 bleibt ein reiner Simplex; danach folgt ein lokaler Polish-Schritt
  - Mit BSSA ist die zusätzliche d-Regularisierung (ω_d) aus [W99] laut [B00] nicht
    nötig. Sie wird trotzdem für S_eff als Option vorgesehen.
  - Startwerte kommen aus einer vorgeschalteten IFT: R_HS ≈ Dmax/2, φ vom Nutzer.
    [BP97] empfiehlt eher überschätzte Startwerte.
- **S(q)-Modelle (Registry, eines pro Klasse):**
  | Modell | Parameter | Quelle | Phase |
  |---|---|---|---|
  | HS-PY monodispers | φ, R_HS | Percus-Yevick analytisch [BP97 §2.4] | 3a |
  | **S_ave(q)** gemittelt (Standard) | φ, R_HS, µ = σ/R_HS (Gauß) | [BP97 Gl. 34], [W99 Gl. 8] | 3a |
  | S_eff(q) PY polydispers (Vrij) | φ, R_HS, µ (Schulz) | [W99], [V79] | 5 |
  | S_rod(q) Stäbchen (Mean-Field) | c, L, µ_L | [W99 Gl. 16–17] | 5 |
  | **RMSA geladen**, optional gemittelt über µ | φ, R_HS, z; **fest:** T, ε_r, Ionenstärke → κ | [HP81], [HH82], [F00] | **3b** |
  | HNC / Rogers-Young (geladen) | wie RMSA, RY zusätzlich mit Mischparameter α | [F00]; numerische Lösung der Ornstein-Zernike-Gleichung, aufwendig und daher ein Kandidat für den Prozess-Pool | 5 |
  - **Wichtig aus [F00]:** Ladung und Ionenstärke lassen sich nicht gleichzeitig
    bestimmen. Die Ionenstärke ist deshalb immer eine feste Eingabe, und der Dialog
    erlaubt nur eine der beiden Größen als freien Parameter. Zwischen z, R_HS und φ
    gibt es zusätzlich eine Mehrdeutigkeit, die die DREAM-Analyse (§2.3) direkt
    sichtbar macht.
  - Für S_ave(q) wird die Gaußverteilung mit Gauss-Hermite-Quadratur mit ~15–25
    Stützstellen diskretisiert (R > 0 abgeschnitten, bei festem Gesamt-φ). Das ist
    schnell und glatt.
  - Hinweis im Dialog wie in [W99]: Die S_ave-Parameter sind nur scheinbare
    Modellparameter. p(r) und P(q) sind das eigentliche Ergebnis.
- **Ausgabe:** S(q), P(q) = I_fit/S, p(r), die Parameter d und Unsicherheiten aus der
  Hesse-Matrix von MD am Minimum. Optional eine 2D-MD-Hyperfläche über zwei gewählte
  Parameter wie [B00] Fig. 4 und [BP97] Fig. 2, außerdem der BSSA-Verlauf (T, MD,
  Parameter über die Iterationen) wie [B00] Fig. 2/3.

### 2.3 Statistische Absicherung der Parameter mit DREAM (MCMC)
Ziel: Nach dem BSSA-Fit wird geprüft, wie gut die Parameter statistisch belegt sind.
Dazu gehören Glaubwürdigkeitsintervalle, Korrelationen und Mehrdeutigkeiten sowie
ein p(r)-Band, das auch die Unsicherheit von S(q) enthält.

- **Algorithmus:** DREAM(ZS) nach Vrugt / ter Braak. Die Vorschläge entstehen durch
  Differential Evolution aus einem Archiv Z vergangener Zustände; dazu kommen
  Randomized Subspace Sampling (Crossover CR mit Adaption), Snooker-Updates und die
  Behandlung von Ausreißer-Ketten. Die Implementierung erfolgt selbst in numpy
  (~300 Zeilen), damit keine neue Abhängigkeit nötig ist. Getestet wird gegen
  analytisch bekannte Posteriors: eine korrelierte Gaußverteilung, eine bimodale
  Verteilung und die Rosenbrock-„Banane“.
- **Likelihood (Kernidee):** Die Spline-Koeffizienten c hängen bei festen (d, λ, Dmax)
  linear und gaußförmig vom Modell ab. Sie lassen sich daher **analytisch
  herausintegrieren**; das ist die Bayes'sche IFT nach Hansen (2000):
  log p(I | d, λ, Dmax) = −½χ²(ĉ) − ½λ·ĉᵀKĉ − ½ log det(B+λK) + ½ log det(λK) + const.
  DREAM muss deshalb nur die wenigen nichtlinearen Parameter abtasten, nicht 30 und
  mehr Koeffizienten. Das ist schnell und statistisch sauber. K wird durch die
  Randbedingung p(0) = p(Dmax) = 0 bzw. einen kleinen Ridge-Term regulär gemacht.
- **Abgetastete Größen** (Standard laut Entscheidung: alle; im Dialog einzeln fixierbar):
  - GIFT: die freien S(q)-Parameter d (z. B. φ, R_HS, µ oder z)
  - optional log λ, statt es auf λ_opt festzuhalten
  - optional Dmax. Damit wird die Unsicherheit von Dmax berücksichtigt, und die
    Grenze π/q_min kann als Prior-Obergrenze oder nur als Flag dienen.
  - reine IFT: (log λ, Dmax). Das ergibt ein p(r)-, Rg- und I(0)-Band einschließlich
    der Unsicherheit von Dmax und λ.
- **Priors:** gleichverteilt innerhalb der physikalischen Grenzen aus dem Dialog;
  optional gaußförmig für bekannte Größen (z. B. φ aus der Einwaage).
- **Fehlerskalierung:** Ist MD am Optimum deutlich ≠ 1, kann σ optional mit √MD
  skaliert werden. Das wird als Flag gemeldet und im Provenance-Record vermerkt.
- **Ablauf:**
  1. Screening: Latin-Hypercube-Stichprobe über den Prior (einige hundert bis tausend
     Punkte, parallel). Daraus ergeben sich das Startarchiv Z und eine grobe
     MD-Landschaft.
  2. Burn-in mit Adaption der CR-Wahrscheinlichkeiten.
  3. Sampling bis R̂ < 1.1 für alle Parameter (Gelman-Rubin) oder bis zum
     Auswertungsbudget.
  4. Posterior-Prädiktion: Für ausgedünnte Proben (d, λ, Dmax) wird c ~ N(ĉ, Σ_c)
     gezogen. Daraus entstehen Bänder für p(r), I_fit(q), S(q) und P(q) sowie
     Verteilungen von Rg und I(0).
- **Ausgaben:** Median und 68/95 %-Intervalle, Korrelationsmatrix, Corner-Plot
  (Randverteilungen und 2D-Dichten), Trace-Plots, R̂ je Parameter, Akzeptanzrate,
  Vergleich BSSA-Optimum vs. Posterior-Modus. Die Ketten werden als `.npz` gespeichert.
- **Zusätzliche Flags:**
  | Flag | Kriterium |
  |---|---|
  | nicht konvergiert | R̂ > 1.1 nach dem Budget |
  | Parameter nicht bestimmbar | Posterior ≈ Prior (Breitenverhältnis > 0.8) |
  | Posterior am Rand | nennenswerte Masse an einer Prior-Grenze |
  | starke Korrelation | \|ρ\| > 0.9, z. B. z ↔ R_HS ↔ φ [F00] |
  | multimodal | mehrere getrennte Modi; BSSA-Optimum ≠ Hauptmodus |
  | Dmax-Posterior > π/q_min | Hinweis auf fehlende Information bei kleinen q |

## 3. Flags und Plausibilitätsprüfungen

| Flag | Kriterium | Stufe |
|---|---|---|
| **Dmax vs. q_min** | Dmax > π/q_min: Warnung mit dem Verhältnis Dmax·q_min/π; die Rechnung läuft weiter | ⚠ |
| Shannon-Kanäle | N_s = Dmax·(q_max − q_min)/π; Warnung, wenn N_s < ~3 oder N ≫ N_s | ⚠ |
| Wendepunkt nicht gefunden | kein Minimum von \|d log N_c/d log λ\| | ⚠ |
| Anpassungsgüte | MD ≫ 1 (Modell passt nicht) oder MD ≪ 1 (σ überschätzt) | ⚠ |
| Fehlerspalte fehlt | σ wird geschätzt, MD ist damit nur relativ aussagekräftig | ⚠ |
| p(r)-Ende | p(r) bei Dmax nicht → 0, also Dmax zu klein | ⚠ |
| p(r)-Ausläufer | lange Null-Region vor Dmax, also Dmax deutlich zu groß | ℹ |
| negative p(r) | signifikant < 0 (> 2σ), deutet auf Untergrund oder unberücksichtigtes S(q) hin (Hinweis auf GIFT) | ⚠ |
| Oszillationen bei großen r | typisch für i(r) mit Wechselwirkung [W99 Fig. 1b]; Vorschlag: GIFT verwenden | ℹ |
| Rg-Konsistenz | Rg(IFT) vs. Rg(Guinier) > 10 % | ℹ |
| GIFT-Parameter | am Rand der erlaubten Grenzen oder S(q) unphysikalisch [B00] | ⚠ |

Die Flags erscheinen im Dialog als Ampel-Liste und werden im Report (JSON) und im
Header der Ergebnisdateien festgehalten.

Hilfsfunktion **Dmax-Scan:** MD, Rg, I(0) und p(Dmax) über einen Dmax-Bereich; das
entspricht [G77] Fig. 10. Die π/q_min-Grenze wird als Linie eingezeichnet.

## 4. Architektur (direkt in ScatteringPlot)

```
ScatteringPlot/
  analysis/                         ← neu; GUI-frei, nur numpy/scipy, mit pytest testbar
    __init__.py
    gift/
      splines.py            B-Spline-Basis
    significance.py         |I/σ|, rolling median, q_max für nσ (aus scatter_plot.py ausgelagert)
      transform.py          Designmatrix A, Cache
      smearing.py           Operator-Schnittstelle (Pinhole = Identität), später erweiterbar
      ift.py                Löser, λ-Scan, Wendepunkt, Kovarianz
      structure_factors.py  Registry: HS-PY, S_ave, RMSA, (S_eff, S_rod)
      bssa.py               Boltzmann-Simplex-Simulated-Annealing
      likelihood.py         marginale Likelihood (c analytisch integriert), batch-fähig
      dream.py              DREAM(ZS)-Sampler, R̂, Posterior-Prädiktion
      screening.py          Latin-Hypercube-Screening der MD-Landschaft
      parallel.py           Prozess-Pool, Seed-Verwaltung (SeedSequence), BLAS-Thread-Limit
      provenance.py         ProvenanceRecord (portiert aus JADE-DLS, Qt-frei), Sidecar-Writer
      gift.py               innere/äußere Schleife
      diagnostics.py        Flags, Rg, I0, Shannon, Dmax-Scan
      results.py            Dataclasses, Export .dat/.json
  dialogs/
    gift_dialog.py                  ← neu: Parameter | Vorschau-Tabs | Flag-Liste
  tests/analysis/                   ← neu
  scatter_plot.py                   ← neues Menü „Analyse“ und Kontextmenü-Eintrag
  i18n/translations/{de,en}.json    ← Keys `gift.*`, `menu.analysis.*`
  CHANGELOG_v7.8.md, core/version.py
```

### 4.1 GUI-Ablauf
1. Einen Datensatz im Tree markieren und „Analyse → P(r) berechnen (IFT/GIFT) …“
   wählen (auch per Rechtsklick).
2. Nichtmodaler Dialog (analog zu `Plot2DDialog`):
   - Links die Einstellungen: q-Fitbereich (Voll / 1σ / 2σ / 3σ / manuell, §2.0),
     Dmax (mit Live-Anzeige von π/q_min und dem Flag), N Splines, λ (automatisch oder
     manuell), Untergrund an/aus, Modus IFT/GIFT, S(q)-Modell, Start- und
     Grenzwerte, Seed
   - Rechts Tabs: I(q) + Fit (log-log, Residuen), p(r) ± σ, λ-Kurven, S(q) & P(q),
     BSSA-Verlauf, Dmax-Scan, **Unsicherheit** (Corner-Plot, Traces, R̂, Posterior-Bänder),
     **Provenance** (Record-ID, Aktivitätenkette, Hashes als Baumansicht)
   - Unten die Flag-Liste
   - Die Rechnung läuft in einem `QThread` mit Fortschritt und Abbruch; bei der IFT
     aktualisiert sich die Vorschau live bei Parameteränderung (entprellt).
3. „Übernehmen“ schreibt die Ergebnisdateien, legt eine PDDF-Gruppe (Rohdaten + Fit +
   P(r)) an und schaltet den Plot-Typ auf PDDF.

### 4.2 Ergebnisse als Dateien
Sessions speichern nur Dateipfade, und die PDDF-Rollen werden über Dateinamen erkannt.
Deshalb werden die Ergebnisse standardmäßig im Unterordner `GIFT/` neben der
Datendatei abgelegt:
- `<stem>_GIFT_pr.dat` — r, p(r), σ_p → wird als P(r) erkannt (`_pr`)
- `<stem>_GIFT_fit-PDDF.dat` — q, I_fit, σ_fit → wird als PDDF-Fit erkannt
- `<stem>_GIFT_Sq.dat`, `<stem>_GIFT_Pq.dat` (nur GIFT)
- `<stem>_GIFT_prov.json` — **Provenance-Sidecar** (§4.3) mit allen Parametern,
  Flags, Ergebnissen und Hashes. Er ersetzt den früher geplanten `report.json`.
- `<stem>_GIFT.prov-w3c.json` — dieselbe Information als W3C PROV-JSON (optional)
- `<stem>_GIFT_dream.npz` — Ketten und Log-Likelihoods (nur mit DREAM)
- `<stem>_GIFT_pr_band.dat` — Posterior-Median und 2.5/16/84/97.5-%-Quantile von p(r) (nur mit DREAM)
- Jede Datei beginnt mit einem Kommentar-Header mit den Parametern, den Flags und der
  **`record_id`** des Sidecars. Die
  bestehenden Loader überspringen `#`-Zeilen.
- Zusätzlich wird eine neue Rolle `pddf_role='pofr'` explizit gesetzt, damit die
  Zuordnung nicht von der Namensheuristik abhängt.

### 4.3 Provenance-Sidecar (nach JADE-DLS)
Vorbild ist `JADE-DLS/ade_dls/gui/core/provenance.py`: ein PROV-DM-artiger Record mit
Agent, Eingangs-Entitäten (SHA-256), Aktivitätenkette (DAG über `used`) und
Output-Katalog (SHA-256, `wasGeneratedBy`, `wasDerivedFrom`). Jedes Artefakt trägt
die UUID4-`record_id`, dazu kommt eine zweite Serialisierung als W3C PROV-JSON. Das
Modul ist Qt-frei und wird nach `analysis/gift/provenance.py` portiert. Dabei wird es
verallgemeinert: Software-Name und Schema-URI werden Parameter.

**Schema** `…/schema/gift-provenance/v1.0` (gleiche Struktur wie JADE, damit dieselben
Werkzeuge beide lesen können):
- `agent`: ScatterForge-Version, Version des GIFT-Moduls, Git-Commit (falls
  ermittelbar), Plattform, Python-, numpy- und scipy-Versionen
- `input.entities`: Datendatei mit SHA-256, Spaltenzuordnung, Einheiten, Anzahl
  Punkte; ob σ gemessen oder geschätzt wurde
- `processing.activities`, eine Kette mit Zeitstempel, Parametern und
  `results_summary` pro Schritt:
  1. `data_loading` — Datei, Hash, Spalten
  2. `preprocessing` — q-Bereich, ausgeschlossene Punkte, σ-Schätzung/-Skalierung
  3. `ift` — Dmax, N, Basis, K-Typ, λ-Scan-Bereich, λ_opt (automatisch oder manuell),
     Untergrund; Ergebnisse MD, Rg, I(0), Flags
  4. `gift_bssa` — S(q)-Modell, feste Größen (T, ε_r, Ionenstärke), Startwerte,
     Grenzen, Abkühlschema, Seed, Anzahl Auswertungen, Optimum d, MD
  5. `screening` / `dream` — Priors, Ketten, Generationen, Seeds, R̂, Akzeptanz,
     Intervalle, Korrelationen, Flags
  6. `export` — geschriebene Dateien
- `output.catalog`: jede geschriebene Datei mit SHA-256 und `record_id`
- `flags`: die vollständige Flag-Liste mit Stufe und Wert, z. B. Dmax·q_min/π
- `reproducibility`: Master-Seed und `SeedSequence`-Spawn-Schlüssel sowie die Zahl
  der Worker. Die Ergebnisse sind dabei **unabhängig von der Worker-Zahl**, siehe §5.

**Funktionen:**
- **„Aus Sidecar wiederholen“:** Ein `_prov.json` wird geladen, der Dialog mit exakt
  diesen Einstellungen befüllt und die Rechnung neu gestartet. Anschließend werden
  der Hash der Eingangsdatei (unverändert?) und die Ergebnisse (gleich innerhalb der
  Toleranz?) verglichen.
- **„Sidecar prüfen“:** Die SHA-256 aller Katalogdateien werden gegen die Dateien auf
  der Platte verifiziert.
- In der ScatteringPlot-Session wird pro GIFT-Gruppe die `record_id` gespeichert, und
  der Tree-Tooltip zeigt sie an.
- Grundsatz aus JADE: Provenance darf nie einen erfolgreichen Export verhindern.
  Fehler beim Hashen werden geloggt und nicht als Ausnahme weitergereicht.

## 5. Effizienz und Parallelisierung
- Die Designmatrix wird einmal pro (q, Dmax, N) berechnet und gecacht.
- **Dmax als freier Parameter (DREAM) ohne Neuberechnung:** Bei äquidistanten Knoten
  gilt φ_ν(r) = φ̃_ν(r/Dmax) und damit ψ_ν(q; Dmax) = Dmax · g_ν(q·Dmax). Die N
  eindimensionalen Funktionen g_ν(x) werden einmal fein tabelliert, oder in
  geschlossener Form über Sinus- und Kosinusintegrale der Spline-Polynome berechnet,
  und dann nur interpoliert. Ein Wechsel von Dmax kostet so nur O(M·N) statt einer
  neuen Quadratur, und auch der Dmax-Scan profitiert davon.
- λ-Scan: B, b und K einmal aufstellen, dann eine verallgemeinerte Eigenzerlegung
  von (B, K). Jede λ-Lösung ist danach O(N²); ein Scan über 60 λ-Werte dauert unter 1 ms.
- GIFT: S(q) vektorisiert (Gauss-Hermite × q als 2D-numpy-Array). Pro BSSA-Schritt
  sind nur Spaltenskalierung, B = AᵀWA (M·N²) und der λ-Scan nötig. Erwartung: einige
  Sekunden für eine volle Anpassung, verglichen mit „10–30 min auf Pentium 200“ in [B00].
- **Stufe 1, Vektorisierung (größter Gewinn, kein Prozess-Overhead):**
  S(q) und die marginale Likelihood werden für einen ganzen Stapel von Parametersätzen
  gleichzeitig berechnet. Beispiele: alle DREAM-Ketten einer Generation, ein
  Screening-Block oder die Vertices eines Simplex. Dafür werden Arrays der Form
  (K, M, N), gestapeltes `np.einsum` für B = AᵀWA und `np.linalg.cholesky`/`solve` auf
  (K, N, N) verwendet. numpy/BLAS nutzen dabei ohnehin mehrere Kerne.
- **Stufe 2, Prozess-Pool (`concurrent.futures.ProcessPoolExecutor`)** für Aufgaben,
  die voneinander unabhängig sind:
  - mehrere unabhängige BSSA-Läufe mit verschiedenen Seeds. Das beschleunigt und
    prüft zugleich die Robustheit: Finden alle Läufe dasselbe globale Minimum?
    Falls nicht, wird ein Flag gesetzt.
  - Screening-Blöcke, Dmax-Scan, Batch über Messserien
  - teure S(q)-Modelle (HNC/RY: numerische OZ-Iteration), verteilt auf Chunks von
    Parametersätzen
- **Windows-Besonderheiten:** Der Start-Modus `spawn` erfordert Worker-Funktionen auf
  Modulebene, und in den Workern darf kein Qt importiert werden. Große Arrays (A, q,
  I, σ) werden einmal per Initializer übergeben. Pro Worker wird BLAS auf 1 Thread
  begrenzt (`OMP_NUM_THREADS`/`OPENBLAS_NUM_THREADS`/`MKL_NUM_THREADS` vor dem
  numpy-Import), um Überbelegung zu vermeiden. Die Anzahl der Worker ist einstellbar
  (Standard: Kerne − 1), und der Pool bleibt über mehrere Läufe hinweg bestehen.
- **Reproduzierbarkeit trotz Parallelität:** Alle Zufallsströme werden über
  `np.random.SeedSequence(master).spawn(...)` fest an Aufgaben gebunden, nicht an
  Worker. Die Ergebnisse sind damit identisch für 1 oder 16 Worker; das wird getestet.
- Die GUI bleibt über `QThread` bedienbar; Fortschritt und Abbruch werden an den Pool
  weitergereicht.
- **Erwartete Rechenzeit** (grob, M ≈ 500, N ≈ 30): eine Auswertung der Likelihood
  dauert ~0.2–1 ms, im Stapel weniger. Ein DREAM-Lauf mit 3–5 Parametern und
  ~30–50 k Auswertungen braucht damit ~10–60 s. Mit HNC/RY steigt der Aufwand pro
  Auswertung stark; dort lohnt sich der Pool am meisten.
- Keine Pflicht-Abhängigkeiten neu. `numba` wäre ein optionaler Beschleuniger für
  HNC/RY (Phase 5) und wird nur genutzt, wenn installiert.

## 6. Validierung (pytest)
1. Kugel mit Rg = 10 nm und D = 30 nm, 10 % Rauschen [G77 Fig. 7]: p(r) gegen die
   analytische Lösung; Rg-Fehler < 1–2 %.
2. Debye-Kette mit h₁Rg = 1.6 [G77 Fig. 9]: Rg-Fehler ≈ 2 %.
3. Stab mit D-Variation [G77 Fig. 10].
4. GIFT: Kugel R = 10 nm, S_ave mit φ = 0.15, R_HS = 10 nm, µ = 0.4, gestartet bei
   (0.18, 12, 0.5) [BP97 §3.2.1]. Rückgewinnung der Parameter und von p(r). Außerdem
   die MD-Tabelle aus [BP97 Tab. 1] qualitativ reproduzieren.
5. GIFT-Kreuztest [W99 §3.3]: Mit S_eff simulieren und mit S_ave auswerten; p(r) muss
   in der Form erhalten bleiben, Normierungsfaktor ≈ 0.92 (erst ab Phase 5).
6. BSSA: bekannte Testfunktionen (Rosenbrock, Rastrigin) und Reproduzierbarkeit über
   Seeds.
7. Kreuzvergleich mit SasView P(r) (Moore) an realen Daten.
8. RMSA gegen die Hayter-MSA aus sasmodels und die Beispiele in [HP81]/[HH82];
   Simulation nach [F00]: 5 % v/v, R = 2.5 nm, z = 25. Gegenprobe zur
   Nichtbestimmbarkeit von z und Ionenstärke: DREAM muss die starke Korrelation
   zeigen.
9. DREAM: Posterior einer korrelierten 2D-Gaußverteilung, einer bimodalen Verteilung
   und der Rosenbrock-Banane korrekt wiedergeben (KS-Test, Momente). Bei GIFT-
   Simulationen müssen die wahren Parameter in 95 % der Wiederholungen im
   95 %-Intervall liegen (Coverage-Test, Stichprobe).
10. Parallel: identische Ergebnisse für 1 und n Worker bei gleichem Master-Seed.
11. Provenance: Hashes stimmen, `record_id` steht in allen Dateien, „Wiederholen“
    reproduziert die Ergebnisse, und der PROV-JSON-Export ist mit dem `prov`-Paket
    einlesbar.

## 7. Phasen
| Phase | Inhalt | Ergebnis |
|---|---|---|
| 1 | `analysis/gift` IFT-Kern, `analysis/significance.py` (Refactoring + q-Bereichs-Voreinstellung), Flags, **Provenance-Kern** (Record, Sidecar, Hashes), Tests 1–3, 11 | rechenfähige, nachvollziehbare Bibliothek |
| 2 | `gift_dialog.py`, Menü, Datei-Export mit Sidecar, PDDF-Gruppe, Provenance-Tab, „Sidecar prüfen“, i18n, Changelog v7.8 | IFT in der GUI nutzbar |
| 3a | S(q)-Registry (HS-PY, S_ave), BSSA, GIFT-Modus im Dialog, Tests 4 und 6 | GIFT für ungeladene Systeme |
| 3b | RMSA (geladen) inkl. Eingabe der festen Größen (T, ε_r, Ionenstärke), Test 8 | GIFT für geladene Systeme |
| 3c | Vektorisierte Batch-Likelihood, `parallel.py` (Pool, Seeds), parallele BSSA-Mehrfachläufe, Test 10 | schneller und robuster Fit |
| 3d | Marginale Likelihood, LHS-Screening, DREAM(ZS), Posterior-Bänder, Unsicherheits-Tab, DREAM-Flags, Test 9, „Aus Sidecar wiederholen“ | statistisch abgesicherte Parameter |
| 4 | Dmax-Scan, MD-Hyperfläche, Batch über Messserien | Komfort |
| 5 | S_eff (Vrij-PY, Schulz), S_rod, klebrige harte Kugeln (Baxter), fraktales Aggregat (Teixeira) | erweiterte Modelle |
| 6 | Radiales Dichteprofil aus p(r) (DECON), Größenverteilung per IFT, Querschnitts- und Dicken-IFT | weitere Glatter-Auswertungen |
| später | HNC/Rogers-Young, instrumentelle Verschmierung, gemeinsame ASAXS-GIFT (mehrere Kurven, ein S(q)), Serie mit Metadaten | zurückgestellt |

## 8. Konventionen
- Einheiten wie in ScatteringPlot: q in nm⁻¹, r in nm.
- Fehlen Fehlerspalten, wird σ geschätzt und ein Flag gesetzt.
- Code-Stil, Changelog und AI-Transparency-Hinweis wie im bestehenden Repo.

## 9. Offene Punkte
- ~~Literatur für RMSA/geladene GIFT~~ liegt vor ([F00], [HP81], [HH82], [V79])
- ~~Rückfragen Runde 4~~ beantwortet (siehe §0)
- Referenzdaten für die Validierung (z. B. PCG/GIFT-Originalausgaben oder SasView-P(r) derselben Messung), falls vorhanden
- Implementierung auf eigenem Branch `feature/gift` in ScatteringPlot

## 10. Umsetzungsstand

### Phase 1 — umgesetzt (Branch `feature/gift` in ScatteringPlot, Commit `0378727`)
| Datei | Inhalt |
|---|---|
| `analysis/significance.py` | \|I/σ\|, gleitender Median (vektorisiert, identisch zur alten Schleife), σ-Abschneidekriterium, `select_q_range()` (voll / nσ / manuell) |
| `scatter_plot.py` | Significance-Plot nutzt jetzt `analysis.significance`; Ausgabe vorher/nachher geprüft (bitgleich) |
| `analysis/gift/splines.py` | geklemmte kubische B-Spline-Basis |
| `analysis/gift/transform.py` | Designmatrix (Gauss-Legendre, adaptive Stützstellen), LRU-Cache |
| `analysis/gift/smearing.py` | Operator-Schnittstelle (Pinhole = Identität) |
| `analysis/gift/ift.py` | IFT: verallgemeinerte Eigenzerlegung, λ-Scan, Wendepunkt-Methode, Kovarianz, Rg/I(0), Untergrund, σ-Schätzung |
| `analysis/gift/diagnostics.py` | Flags aus §3 inkl. Dmax·q_min/π, Guinier-Rg |
| `analysis/gift/provenance.py` | ProvenanceRecord (JADE-Struktur, eigenes Schema), W3C PROV-JSON, `verify_outputs/inputs()`, `load()` |
| `analysis/gift/pipeline.py` | `run_ift_analysis()` und `export_ift_results()` → `GIFT/`-Unterordner mit Sidecar |
| `tests/analysis/*` | 39 Tests (unittest, laufen auch unter pytest): `python -m unittest discover -s tests/analysis -t .` |

### Implementierungsentscheidungen, die vom Entwurf abweichen (mit Begründung)
1. **Basis:** Statt Splines, die vollständig in [0, Dmax] liegen, wird eine *geklemmte*
   B-Spline-Basis ohne ersten und letzten Spline verwendet. Die ursprüngliche Variante
   erzwang zusätzlich p′(0) = p″(0) = 0; p(r) ∝ r (Ketten) oder der steile Anstieg bei
   Stäbchen ließ sich damit nur über Oszillationen darstellen.
2. **Glättungsmatrix K:** Standard ist `dirichlet` (erste Differenzen mit c₀ = c_{N+1} = 0),
   nicht die reine Glatter-Form. Letztere bestraft einen konstanten Koeffizientenvektor
   nicht; fehlen Kleinwinkeldaten, bleibt dieser unbestimmt (negatives p(r), Rg undefiniert).
   Die Glatter-Form und eine Krümmungsvariante sind als Option verfügbar.
3. **λ-Skala und -Scan:** λ_rel = λ·tr(K)/tr(B), Scan über 10⁻¹⁴ … 10⁴ (8 Punkte/Dekade).
   Bei gut bestimmten Daten liegt das Plateau bei λ_rel ~ 10⁻¹², also weit unter dem
   ursprünglich geplanten Bereich.
4. **Wendepunkt-Regel (operationalisiert):** Kandidaten sind lokale Minima von
   |d log N_c/d log λ| < 0.3 (inkl. linkem Scanrand) mit MD ≤ 1.25·MD_min; gewählt wird
   das größte λ. Die Regel wurde gegen Alternativen (tiefstes Plateau, χ²-basierte
   Toleranz, Krümmungs-K) über jeweils 12–20 Rauschrealisierungen verglichen.
5. **Untergrund:** Wird nicht als unregularisierte Spalte angehängt, sondern analytisch
   herausprojiziert (numerisch stabil). Die Unsicherheit des Untergrunds ist
   erwartungsgemäß groß, da er mit einer p(r)-Spitze bei r → 0 korreliert ist [G77].
6. **Kovarianz:** über den linearen Lösungsoperator G (Cov = G·Gᵀ), gültig mit und ohne
   Untergrund.

### Erreichte Genauigkeit (synthetische Daten wie [G77])
| Fall | Ergebnis | [G77] |
|---|---|---|
| Kugel, h₁Rg = 0.2 … 20, 10 % Fehler, D = 30 nm | Rg-Fehler ≈ 0.3 % (Median), p(r)-L2 < 1 % | 1 % |
| Debye-Kette, h₁Rg = 1.6, 5 %, D = 4Rg | Rg-Fehler ≈ 10 % (Median, 20 Seeds) | 2 % |
| Stab, h₁Rg = 1.6, 5 %, D = 3–3.5Rg | Rg-Fehler ≈ 11–13 % (Median) | < 10 % |

In den Fällen mit h₁Rg = 1.6 ist Dmax·q_min/π ≈ 1.9–2.5, das Dmax-Flag schlägt also an.
Glatters bessere Werte ließen sich mit keiner der getesteten Regeln reproduzieren;
vermutlich unterscheiden sich λ-Normierung bzw. Basis im Original-Programm ITP. Die
DREAM-Analyse (Phase 3d) wird die tatsächliche Unsicherheit in diesen Fällen quantifizieren.

### Phase 2 — umgesetzt (ScatterForge Plot v7.8.0, Branch `feature/gift`, Commit `0378727`)
- `dialogs/gift_dialog.py`: nicht-modaler Dialog. Die IFT rechnet synchron mit
  entprellter Live-Vorschau (~ms); ein `QThread` folgt erst mit GIFT/DREAM.
- Menü „Analyse → P(r) berechnen (IFT/GIFT)…“ (`Strg+Umschalt+G`, da `Strg+G` schon
  „Neue Gruppe“ ist), Kontextmenü-Eintrag am Datensatz, „Analyse → Provenance-Sidecar
  prüfen…“.
- „Übernehmen“ legt die Gruppe „GIFT: <name>“ an (Daten/Fit/p(r) mit expliziten
  `pddf_role`) und wechselt in den PDDF-Plot. Die `record_id` hängt an der Gruppe
  (Tooltip, Session).
- „Einstellungen aus Sidecar…“ ist bereits umgesetzt (ursprünglich für Phase 3d
  geplant): Neuberechnung plus Hash-Vergleich der Datendatei.
- I ≤ 0 werden für die IFT standardmäßig verwendet (der Hauptplot filtert sie für die
  log-Darstellung). Die Auswahl ist im Sidecar dokumentiert.
- Flags haben `variant` + `params` für i18n (DE/EN); die deutsche Klartextmeldung bleibt
  im Sidecar.
- Getestet: 39 Unit-Tests sowie ein Offscreen-End-to-End-Test (alle q-Modi, manuelles λ,
  Dmax-Flag, Übernehmen, PDDF-Plot, Tooltip, Session, Sidecar prüfen/laden, Englisch).

### Test mit `0_Sources/Sphere_142.txt` (SasView-Simulation, R = 142 **Å**; als nm⁻¹ gelesen formal 142 nm)
- Die Datei ist exakt 29984·P_Kugel(q; 142 nm) + 0.001: rauschfrei, 1000 Punkte,
  q = 0.001 … 1 nm⁻¹, keine Fehlerspalte.
- Ergebnis mit den Voreinstellungen des Dialogs (Dmax = 391 nm, N = 155, σ geschätzt):
  Rg = 109.993 nm (Soll 109.99 nm), I(0) = 29984, p(r) deckungsgleich mit der
  analytischen Lösung. Das Flag „pr_tail“ zeigt korrekt, dass Dmax zu groß ist.
- Daraus entstandene Verbesserungen:
  - N-Vorschlag aus den Shannon-Kanälen
  - „N < N_s“ wird als Warnung statt als Info gemeldet
  - N-Bereich bis 200
  - σ-Modus „relativ annehmen“ für Simulationen
  - Regressionstest `TestLargeSphereSimulation`

### Phase 3a — umgesetzt (ScatterForge Plot v7.9.0, Branch `feature/gift`, Commit `11c432e`)
- `structure_factors.py`: HS-PY über die direkte Korrelationsfunktion (GL-Quadratur für
  x ≤ 1, geschlossene Form darüber), S_ave mit 21 Gauss-Hermite-Knoten; vektorisiert
  (K × M) als Vorbereitung für Phase 3c/3d.
- `bssa.py`: amebsa-Variante. **Abweichung:** Start-T aus Simplex *und* Zufallsprobe
  (10·n Punkte), da die Simplex-Streuung allein zu kleine Temperaturen lieferte
  (Doppelmulde: 48/50 globale Treffer vs. 0 beim reinen Nelder-Mead).
- `gift.py`: λ fest während der BSSA-Suche, danach Wendepunkt am Optimum und ggf.
  weitere Zyklen (max. 3). Größenparameter mit relativem Standard-Suchbereich ÷4…×4.
  Parameterfehler aus der χ²-Krümmung (Näherung bis DREAM).
- Validierung [BP97 §3.2.1] (Test 4): φ, R_HS, μ im Rahmen von 1–2σ zurückgewonnen, Rg auf
  < 0.2 %, p(r) auf < 0.5 %; ≈ 1–2 s pro Rechnung. BSSA-Tests (Test 6): Rosenbrock,
  Doppelmulde, Reproduzierbarkeit, Grenzen, Abbruch.
- Dialog: GIFT-Modus mit Parametertabelle, Startwerten aus IFT, Seed, QThread-Worker,
  Tabs „S(q) & P(q)“ und „BSSA-Verlauf“, GIFT-Flags; Sidecar-Wiederholung bitgleich.
- Nicht umgesetzt (bewusst): ω_d-Regularisierung der S(q)-Parameter [W99] — laut [B00] mit
  BSSA nicht nötig; wird mit S_eff (Phase 5) relevant.

### Test mit `Sphere_140+Hardsphere.txt` / `Sphere_140+haytermsa.txt` (SasView, R = 140 Å)
- **Einheiten:** SasView verwendet Å/Å⁻¹. Das ließ sich an der absoluten Intensität
  (I_P(0) = 0.2·Δρ²·V = 5747 cm⁻¹) erkennen. Daraus folgt die neue q-Einheit-Auswahl im
  Dialog; auch `Sphere_142` war tatsächlich R = 142 Å.
- **PY gegen sasmodels:** exakt (2.6·10⁻¹³).
- **GIFT (HS-PY):** φ = 0.2000, R_HS = 14.00 nm.
- **MSA-Kurve mit S_ave:** Rg korrekt, Parameter nur scheinbar. Referenz für RMSA
  (Phase 3b): sasmodels `hayter_msa` mit Ladung 19 e, T = 318.16 K, 0.001 M Salz,
  ε_r = 71.08.
- Beide Kurven liegen als Fixtures in `ScatteringPlot/tests/analysis/data/`.

### Phase 3b — umgesetzt (ScatterForge Plot v7.10.0, Branch `feature/gift`, Commit `5c84037`)
- `rmsa.py`: zeilengetreue Portierung von sasmodels `hayter_msa.c` (BSD-3, Hinweis in Datei
  und `THIRD_PARTY_NOTICES.md`). Grund: Der OCR-Anhang von [HP81] mit den
  Quartik-Koeffizienten ist unlesbar; sasmodels ist die direkte Übertragung von Hayters
  Fortran. Validiert gegen die sasmodels-Testwerte (3.7·10⁻⁶), die SasView-Kurve
  (1.6·10⁻⁸) und den PY-Grenzfall; 0.2 ms pro S(q).
- Modell `rmsa`: φ, R_HS, z frei; T, Salz, ε_r fest (Standard). Monodispers wie in [F00]
  (gemitteltes RMSA dort als instabil beschrieben).
- **Befund:** Die MD-Fläche hat bei freiem φ/R_HS/z ein großes Nebental (φ → 0, R_HS → Rand,
  z ↑). Deshalb wurde der **Mehrfachstart aus Phase 3c vorgezogen** (sequentiell; HS 4,
  RMSA 8 Starts) und ein Flag ergänzt, wie oft das beste Minimum gefunden wurde. φ fest
  (Einwaage) macht die Suche vollständig robust; das ist auch die Empfehlung aus [F00].
- Validierung [F00 §IV] (Test 8): Parameter im Rahmen der Fehler, Rg auf 0.3 %.
- Phase 3c reduziert sich damit auf die Parallelisierung (Mehrfachstarts, Screening,
  Dmax-Scan) und die vektorisierte Batch-Likelihood für DREAM.

### Phase 3c — umgesetzt (ScatterForge Plot v7.11.0, Branch `feature/gift`, Commit `d7dd9a4`)
- `parallel.py`: persistenter spawn-Pool. Beim Anlegen wird `__main__` ausgeblendet
  (Worker ohne PySide6/Test-Runner), BLAS einfädig, Fortschritt per Queue, Abbruch per
  Event.
- BSSA-Starts als picklebare Aufgaben. **Befund:** Nur wenn alle Starts im Pool laufen
  (einfädiges BLAS), sind die Ergebnisse unabhängig von der Worker-Zahl *bitgleich*; im
  Hauptprozess (mehrfädiges BLAS) weichen die BSSA-Trajektorien ab. `n_workers = 0`
  bleibt als Diagnosemodus. RMSA-Beispiel: 11.4 s → 5.5 s (8 Prozesse).
- `IFTProblem.md_batch`: ×2–3 bei N ≈ 25, kein Gewinn bei N ≈ 120 (dort schon BLAS-gebunden).
  Schnittstelle für DREAM/Screening.
- **Abweichung vom Plan:** `SeedSequence.spawn` wurde nicht verwendet. Die bestehenden
  deterministischen Seeds je Start (seed + 1000·k) erfüllen dieselbe Anforderung
  (Bindung an Aufgaben statt Worker) und bleiben mit den Sidecars aus v7.10 kompatibel.
- Screening, Dmax-Scan und Messserien nutzen den Pool ab Phase 3d bzw. 4.

### Phase 3d — umgesetzt (ScatterForge Plot v7.12.0, Branch `feature/gift`, Commit `255056d`)
- `likelihood.py`: marginale Likelihood nach [Hansen 2000] mit analytisch
  herausintegrierten Spline-Koeffizienten; geprüft gegen die direkte Gauß-Marginale
  (< 10⁻⁶). Dmax-Variation über die skalierte Tabelle g_ν(q·Dmax) wie in §5 geplant
  (Hermite-Interpolation, Fehler 2·10⁻⁹). Untergrund wie in der IFT herausprojiziert.
- `dream.py`: DREAM(ZS) in numpy (≈ 300 Zeilen). Test 9 (Gauß, bimodal, Banane) erfüllt.
- **Abweichung von §2.3 (Konvergenzregel):** Statt „R̂ < 1.1 über die zweite Hälfte“ gibt
  es zwei Phasen: Einlauf mit Adaption bis R̂ < Ziel, danach Sampling ohne Adaption bis
  R̂ < Ziel über die Zustände *nach* dem Einlauf und ≥ 5000 Zustände. Beim Übergang werden
  die Priorpunkte aus dem Archiv Z entfernt. Grund: Mit der einfachen Regel meldete
  ein GIFT-Lauf zu früh Konvergenz (eine Kette im Dmax-Ausläufer; 95 %-Grenze 28.9 statt
  20.4 nm im Referenzlauf mit 120 000 Auswertungen), und die weit gestreuten Priorpunkte
  im Archiv hielten die Akzeptanz bei 6 %.
- `screening.py`/`uncertainty.py`: LHS-Screening (100·d Punkte) → Archiv/Startpunkte
  (beste Punkte + BSSA-Optimum) → DREAM → Posterior-Prädiktion (400 Ziehungen, c ~ N(ĉ,
  (B+λK)⁻¹)) mit Bändern für p(r), I(q), P(q), S(q) und Verteilungen von Rg, I(0).
  Zufallszahlen: DREAM `default_rng(seed)`, Screening/Prädiktion `SeedSequence([seed, 1/2])`.
- Parallelität: Auswertungen je Generation im Pool, Blockgröße fest 2 → bitgleich für
  jede Worker-Zahl ≥ 1. **Befund:** Bei HS (0.3 ms pro Auswertung) bringt der Pool nur
  ≈ 1.3×, weil der Prozesswechsel pro Generation ähnlich viel kostet; der Gewinn kommt
  erst mit teuren S(q)-Modellen (Phase 5). Die Priorität lag daher auf der statistischen
  Effizienz (siehe Konvergenzregel).
- Flags aus §2.3 umgesetzt (`dream_*`); „Posterior ≈ Prior“ als σ_post/σ_prior > 0.8,
  „Rand“ als > 10 % Masse in den äußeren 2 %, Multimodalität per 1D-KDE; zusätzlich
  `dream_reference` (BSSA-Optimum bzw. gewähltes λ/Dmax außerhalb 95 %).
- Dialog: Gruppe „Unsicherheit (DREAM)“ und Tab „Unsicherheit“ (Übersicht, Corner-Plot,
  Ketten, Bänder); „Einstellungen aus Sidecar“ wiederholt DREAM automatisch (bitgleich).
- Nicht umgesetzt (bewusst): der optionale Vergleich zweier q-Schnitte (§2.0, „DREAM“)
  als eigene Funktion; er lässt sich mit zwei Läufen und den Sidecars durchführen.
- Validierung an der SasView-RMSA-Kurve: Sollwerte im 95-%-Intervall, bei freiem φ das
  Korrelations-Flag φ–R_HS (+0.95), φ–z (−0.93) wie in [F00] beschrieben; Dmax-Posterior
  27.86 nm (Kugeldurchmesser 28 nm).
- Tests: 97 (16 neu), ≈ 66 s.

### Phase 4 — umgesetzt (ScatterForge Plot v7.13.0, Branch `feature/gift`, Commit `04134b8`)
Anlass: Testlauf mit echten Daten (ASAXS-Normalterme, ESRF, 20/60/20 °C), bei dem p(r) nur
oszillierte. Vor der Umsetzung besprochen; Entscheidungen des Nutzers:
- Standard bleibt der Wendepunkt; andere λ wählbar (Evidenz-Maximum, aus DREAM).
- Kennzahlen SasView-kompatibel; Interpretationsunterschiede Moore vs. GIFT dokumentieren
  (`docs/GIFT/KENNZAHLEN.md`).
- 1D-Scans wie SasView, zusätzlich die 2D-Karte Dmax × λ.
- Artefakte bei kleinem q automatisch ausschließen (manuelle Grenzen haben Vorrang).
- Kontrastwechsel (negatives p(r), mehrere Maxima) nur als Info.
- Serienauswertung vorerst rudimentär (Metadaten-Auslese später).

Ursachen im Testfall: (1) Separationsartefakte im Beamstop-Bereich mit kleinem σ,
(2) Teilchen > π/q_min ohne Guinier-Bereich bei voreingestelltem Dmax = π/q_min,
(3) numerischer Verlust der kleinen Eigenwerte (β über ~20 Dekaden) und zu kurzer λ-Scan,
(4) Wendepunkt-Regel wählte bei flachem Randplateau den Scanrand.

Umgesetzt:
- `explorer.py`: Kennzahlen (Oszillation, Positive Fraction, 1σ-Positive, Maxima, MD,
  χ²/dof, N_g, log-Evidenz, Randanteil), 1D-Scans, Karte, „guter Bereich“,
  `suggest_dmax()`. Kugel: Oszillation 1.14 (SasView: ≈ 1.1).
- `significance.detect_lowq_artifacts()` + `auto_qmin` (Standard an).
- `ift.py`: SVD-Zerlegung, adaptive Scan-Erweiterung (nur bei MD₀ ≤ 2), Randplateau-Regel,
  Evidenz/N_g im Scan, `lam_method` (inflexion/evidence).
- Flags `lowq_artifacts`, `lowq_rise`, `guinier_missing`, `pr_smoothness` (mit Ursache),
  `pr_peaks`; `pr_negative` → Info.
- Dialog: Explorer-Tab (Klick übernimmt Werte), „Vorschlagen“, λ-Wahl, Kennzahlen,
  „λ und Dmax aus DREAM übernehmen“, „Serie…“.
- `batch.py` + `gift_batch_dialog.py`: Serie mit Dmax je Datensatz, CSV-Übersicht.

**Abweichungen vom ursprünglichen Plan (§4.1/§5):**
- Der „Dmax-Scan“ ist als Explorer mit Kennzahlen umgesetzt; die MD-Hyperfläche über
  zwei S(q)-Parameter (B00 Fig. 4) wurde nicht gebaut (der DREAM-Corner-Plot zeigt dieselbe
  Information statistisch sauberer).
- Die λ-Normierung λ_rel = λ·tr(K)/tr(B) bleibt (Kompatibilität); stattdessen wird der Scan
  bei Bedarf erweitert.
- Die „gut“-Kriterien sind Faustregeln: Oszillation ≤ 1.6, I(0) > 0, Randanteil ≤ 0.1,
  MD ≤ MD_ref + max(25 %, 3·√(2/M)) mit MD_ref = beste *glatte* Lösung. Ein kleineres MD,
  das nur ein oszillierendes/negatives p(r) erreicht (60 °C: Korrelationspeak bei
  q ≈ 0.39 nm⁻¹), schließt den glatten Bereich nicht aus.

Ergebnis Testserie (Dmax vorgeschlagen): 20 °C Rg 54 nm, 60 °C 56 nm, 20 °C nach Heizen 78 nm,
jeweils glattes p(r).
Tests: 114 (17 neu), ≈ 70 s.

Offen: Phase 5 (S_eff nach Vrij, S_rod, HNC/RY); Serien-Verfeinerung mit Metadaten.

### Phase 5 — Entscheidungen (vor der Umsetzung, 23.09.2026)
- Umfang: S_eff nach Vrij (polydisperse harte Kugeln, **Schulz-Verteilung** wie in der
  Quelle [V79, W99]), S_rod [W99], klebrige harte Kugeln (Baxter; Parametrisierung wie
  sasmodels `stickyhardsphere`), fraktaler Aggregat-Strukturfaktor (Teixeira 1988).
- Fraktal: Bausteinradius r₀ **frei** (Startwert aus Rg der IFT), keine feste Kopplung an
  p(r); die Korrelation zeigen DREAM und das Korrelations-Flag.
- Baxter: Topfbreite δ standardmäßig fest (0.05), aber editierbar und freigebbar.
- Keine Kombinationen von Strukturfaktoren.
- HNC/RY zurückgestellt; DECON, Größenverteilung und Querschnitts-/Dicken-IFT → Phase 6.

### Phase 5 — umgesetzt (ScatterForge Plot v7.14.0, Branch `feature/gift`, Commit `b3a986f`)
- `sf_models.py`: S_eff nach Vrij (PY-Mischung über Baxters Faktorisierung; Vrijs OCR-Text
  war nicht zuverlässig lesbar, die Baxter-Form ist äquivalent und unabhängig prüfbar),
  Schulz-Verteilung mit 24 Gauß-Legendre-Knoten (Gauß-Laguerre-Gewichte laufen für
  schmale Verteilungen über); Stäbchen [W99 Gl. 16–17]; Baxter (Port sasmodels, BSD-3);
  Fraktal (Teixeira).
- Validierung: Vrij — 1 Komponente = PY, identische Spezies, Kompressibilität der Mischung
  (10⁻⁹); Baxter und Fraktal — sasmodels (10⁻¹⁴ bzw. 10⁻⁸); GIFT-Rückgewinnung für Vrij,
  Baxter und Fraktal.
- **Befund S_rod:** bei freiem p(r) praktisch nicht bestimmbar (MD ändert sich zwischen
  c = 0 und c = 10 um < 1 %), weil S_rod nur über F(qL) von q abhängt. Umgesetzt wie
  beschlossen, mit Warn-Flag und der Empfehlung, c aus der Konzentration vorzugeben.
- **Robustheit:** Durch die Scan-Erweiterung aus Phase 4 konnten λ ≪ 10⁻¹⁴ in die
  GIFT-Suche gelangen (Cholesky von B + λK scheiterte → Zielfunktion überall ∞). QR- bzw.
  SVD-Rückfall in GIFT-Zielfunktion und DREAM-Likelihood.
- ESRF-Daten: keine Anziehung nachweisbar (τ → Grenze), schwache HS-Korrelationen
  (R_HS ≈ 95–124 nm, φ ≈ 0.12–0.15); Fraktal wegen q_min nicht auflösbar.
- Tests: 127 (13 neu).

### Phase 6 — umgesetzt (ScatterForge Plot v8.0.0, Branch `feature/gift`)
Versionierung ab 8.0.0: Bugfixes als 8.0.x.
Quellen ergänzt: [G79], [G80a], [G80b], [G81], [GH84], [MG98] (`GIFT/0_Sources/`).
- `kernels.py`: IFT-Arten `pddf`, `cross_section`, `thickness`, `size_sphere|cylinder|lamella`
  (D_V) und `…_n` (D_N, Primärgröße nach [G80a]); Kerne wie [G80a Gl. 1], [G80b Gl. 15].
  λ-Wahl, Explorer, GIFT, DREAM (mit Dmax), Export und Sidecar arbeiten mit jeder Art.
- `sizes.py`: D_V/D_N/D_I, Momente mit Fehlern; negative Werte nicht unterdrückt [G80a].
- `decon.py`: exakte Überlappungsintegrale [GH84 Anhang], Spline-Basis als feine Stufen
  [MG98] oder Stufen [G81], Wendepunkt-λ [G81] (Scanrand zählt nicht), Polydispersität
  (verschobene Schulz/Gauß, P-Scan über das MD-Minimum [MG98]), Stufenmodell mit variablen
  Breiten [GH84]. Kontrolle: MD(p) [G81] und MD(I) gegen die entschmierte Kurve [MG98].
- Flags: `size_distribution`, `cross_section_lowq` [G80b], `decon_ambiguous`, `decon_fit`,
  `decon_poly`.
- Validierung: Querschnitt/Dicke/Größen aus Simulationen auf 1–2 %; DECON-Stufenmodell exakt
  wie [GH84]; P-Scan findet σ = 0.1/0.2/0.3 wie [MG98]; SasView-Referenz Kern-Schale + Sticky:
  GIFT exakt, Kern:Schale 2.0, Stufen 33/50.6 nm.
- ESRF: 20 °C P = 28 %, dichter Kern bis ≈ 22–25 nm, Hülle mit geringem Kontrast
  (außen ≈ 57 nm); 60 °C und 20 °C nach Heizen P ≥ 40 % (stark polydispers/aggregiert).
- Tests: 150 (23 neu).
- Offen/optional: Formerkennung aus p(r) und f(r) = p(r)/r nach [G79] (Stäbchen: linearer
  Abfall, Lamellen: f(r) linear, Hohlkugeln: Plateau); R_min > 0 für Größenverteilungen;
  korrelierte Polydispersität (feste Schalendicke) [MG98 §4].
