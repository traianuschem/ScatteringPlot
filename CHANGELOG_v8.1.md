# Changelog — Version 8.1

## Version 8.1.1 — Bugfix-Release

**Release Date:** 1. Oktober 2026

### 🐛 Fehlerbehebungen / Verbesserungen

- **ASAXS – Cauchy-Schwarz-Plot:** Neue Größe R = √(I_N·I_A) / |I_cross| im ASAXS-Dialog.
  Aus |I_cross| ≤ √(I_N·I_A) folgt R ≥ 1 für alle q; die Linie bei R = 1 und der rot
  hinterlegte Bereich darunter zeigen sofort, ob die Separation die Ungleichung verletzt.
  Der Infotext nennt den Anteil der Punkte mit R < 1. Fehlerfortpflanzung, q-Bereich,
  Übernahme als abgeleiteter Datensatz (Suffix `_CS`) und Export wie bei den übrigen Größen.
- **ASAXS – Korrelation c korrigiert:** Der Nenner enthielt fälschlich einen Faktor 2. Bei der
  Stuhrmann-Zerlegung I = I_N + 2f'·I_cross + (f'²+f''²)·I_A steht die 2 vor f', daher gilt
  |I_cross| ≤ √(I_N·I_A) und c = I_cross / √(I_N·I_A) mit |c| ≤ 1. Bereits als abgeleitete
  Datensätze übernommene Korrelationskurven sind um den Faktor 2 zu klein und müssen neu
  berechnet werden.

## Version 8.1.0 — ScatterForge Plot (MINOR RELEASE)

**Release Date:** 29. September 2026
**Status:** Stable Release — Flexibles Panel-Layout (freies Grid) statt fest gekoppelter Subplots;
neuer ASAXS-Dialog (I_A/I_N, I_cross/I_N, Korrelation)

Bisher war der Subplot fest an den Plot-Typ gekoppelt: „PDDF“ brachte immer einen
P(r)-Subplot mit, „Significance“ einen |I/σ|-Subplot, „ASAXS“ einen optionalen
linearen Cross-Term-Subplot. Es gab genau eine Zusatzachse, deren Inhalt nicht wählbar
war. Mit 8.1 besteht die Figur aus einem frei konfigurierbaren **Grid aus Panels**
(angelehnt an LabPlots Worksheet-Layout): Jedes Panel hat einen eigenen Typ, lässt
sich ein- und ausschalten, und Gruppen legen fest, in welchen Panels sie erscheinen.

### ✨ Neue Features

#### 1. Panels und Panel-Typen (`core/panel_types.py`, `core/plot_layout.py`)

- **Panel-Typen:** alle bisherigen Darstellungen (Log-Log, Porod, Kratky, dlnI/dlnq,
  Guinier, Bragg Spacing, 2-Theta, Azimuthal Profile, ASAXS) plus
  - **P(r)** – Paarabstandsverteilung auf eigener r-Achse, optional flächennormiert
    (ersetzt den PDDF-Subplot; zeigt auch p_c(r), p_t(r) und Größenverteilungen aus GIFT)
  - **Significance** – |I(q)/σ(q)| roh + median-geglättet mit σ-Schwellenlinien
  - **I linear** – I(q) mit linearer Y-Achse inkl. negativer Werte (ersetzt den
    ASAXS-„± Subplot“)
- **Freies Grid:** Zeilen × Spalten, Höhen-/Breitenverhältnisse, Panels können mehrere
  Zellen überspannen.
- **Geteilte X-Achse:** Panels mit gleicher X-Größe (z. B. q) lassen sich koppeln; beim
  oberen Panel werden X-Titel und Tick-Beschriftung dann ausgeblendet.
- **Pro Panel:** eigener Titel, Achsentitel, Limits, X-/Y-Skala (inkl. symlog),
  Legenden-Modus (alle Kurven / nur eigene / keine), Stack-Faktoren an/aus und
  typ-spezifische Optionen (P(r)-Normierung, Significance-Fenster und -Schwellen,
  dlnI/dlnq-Glättung).
- **Vorlagen:** Nur Hauptpanel, Haupt + P(r), Haupt + Significance, Haupt + I linear, 2 × 2.

#### 2. Bedienung

- **Panel-Liste** im linken Bereich: Häkchen schaltet Panels an/aus, „+“ fügt ein Panel
  eines beliebigen Typs hinzu (q-Panels unter dem Hauptpanel teilen automatisch dessen
  X-Achse), „−“ entfernt, „Layout…“ öffnet den neuen **Layout-Dialog** mit Grid-Vorschau.
- Die **Plot-Typ-Auswahl** bestimmt jetzt den Typ des Hauptpanels.
- **Gruppen:** Im Gruppen-Dialog und im Kontextmenü („Anzeigen in Panel“) wählt man
  „Automatisch“ oder beliebig viele Panels. Automatisch heißt: alle aktiven Panels, deren
  Typ die Daten darstellen kann – P(r)-Kurven landen nur im P(r)-Panel, Kurven ohne
  Fehler nicht im Significance-Panel. Der Tree zeigt die Zuordnung als Tooltip.
- **Achsen-Dialog:** Bereich „Weitere Panels“ mit Panel-Auswahl ersetzt den
  „Subplot-Achse“-Bereich. **Titel-Editor:** ein optionaler Titel je Panel.
- **Annotationen und Referenzlinien** lassen sich einem Panel zuordnen und in jedem
  Panel verschieben.
- Die Options-Widgets für P(r)-Normierung, Significance und dlnI/dlnq wandern aus dem
  Hauptfenster in die Panel-Optionen des Layout-Dialogs.

#### 3. GIFT-Anbindung

- „Übernehmen“ im P(r)-Dialog aktiviert bzw. ergänzt ein **P(r)-Panel**, statt den
  Plot-Typ auf „PDDF“ umzuschalten; das Glättungsfenster für den q-Fitbereich kommt aus
  dem Significance-Panel (Standard 9).

#### 4. ASAXS-Auswertung (`analysis/asaxs.py`, `dialogs/asaxs_dialog.py`)

Neuer, nicht-modaler Dialog (Menü **Analyse → ASAXS-Auswertung…** bzw. Rechtsklick auf
einen ASAXS-Datensatz oder eine Gruppe):

- **Proben-Erkennung:** Datensätze werden anhand von Term-Typ und Dateinamen-Suffix
  (`_IN`, `_IA`, `_Icross`) zu Proben gruppiert; die Zuordnung ist pro Probe per Auswahl
  korrigierbar.
- **Größen:**
  - **I_A / I_N** und **I_cross / I_N** – auf dem q-Gitter von I_N; bei abweichenden
    Gittern wird der Zähler linear in log q interpoliert (nur Überlappungsbereich)
  - **Korrelation** c = I_cross / √(I_N·I_A) – nach Cauchy-Schwarz |c| ≤ 1;
    der Dialog warnt, wenn |c| > 1 (Hinweis auf Probleme der Separation)
  - Gauß'sche Fehlerfortpflanzung, optionaler q-Bereich, Fehlerbänder, Log-Skala
- **Vorschau:** oben die Terme (symlog, damit negative I_cross-Werte sichtbar sind),
  unten die abgeleitete Größe (bei der Korrelation mit ±1-Linien).
- **Übernehmen** (aktuelle oder alle Proben) legt die Ergebnisse als **abgeleitete
  Datensätze** in einer neuen Gruppe an und zeigt sie in einem **Ratio-Panel** (wird
  bei Bedarf unter dem Hauptpanel mit gekoppelter q-Achse angelegt). Export als
  ASCII/CSV und PNG.

#### 5. Abgeleitete Datensätze ohne Datei

- `DataSet.from_arrays()` erzeugt Datensätze direkt aus Arrays; die Daten und ihre
  Herkunft (`derived_from`: Größe, Quelldateien, q-Bereich) werden **inline in der
  Session** gespeichert.
- Neuer Term-Typ **„Abgeleitet (Verhältnis/Korrelation)“** (`data_term = 'ratio'`) und
  Panel-Typ **Ratio**: Solche Kurven erscheinen automatisch nur im Ratio-Panel, nicht
  in I(q)-Panels.
- **2D-Projektionen** (Azimutalprofil, Sektorintegral) nutzen denselben Mechanismus und
  gehen damit nach dem Neuladen einer Session nicht mehr verloren (bisher Temp-Datei).

### 🩹 Fehlerbehebungen

- **Guinier mit Fehlerbalken:** Der Fehler wurde logarithmiert (negativ → Absturz
  „yerr must not contain negative values“). Jetzt korrekte Fehlerfortpflanzung
  σ(ln I) = σ(I)/I.
- P(r)-Kurven erscheinen nicht mehr fälschlich im ASAXS-Cross-Term- bzw.
  Significance-Subplot; der Cross-Term wird im Significance-Panel nicht mehr zusätzlich
  als Rohkurve gezeichnet.

### 🔄 Kompatibilität

- **Alte Sessions (≤ 8.0)** werden beim Laden automatisch übersetzt:
  PDDF → Log-Log + P(r)-Panel, Significance → Log-Log + Significance-Panel (gekoppelte
  X-Achse, Höhen 3 : 1), ASAXS → ASAXS + deaktiviertes „I linear“-Panel.
  Subplot-Achseneinstellungen und Subplot-Titel gehen in dieses Panel über, die
  Gruppen-Zuordnung „Haupt/Sub/Beide“ in die Panel-Zuordnung.
- Neue Sessions enthalten zusätzlich `plot_layout`; `plot_type`, `axis_limits` und
  `custom_xlabel/ylabel` werden weiter (für das Hauptpanel) geschrieben.
- Das Tastenkürzel für „PDDF“ wendet die Vorlage „Haupt + P(r)“ an.

### 📦 Neue / geänderte Dateien

| Datei | Änderungen |
|-------|------------|
| `core/panel_types.py` | **Neu:** Panel-Typ-Registry (Transformation, Achsen, akzeptierte Daten, Renderer) |
| `core/plot_layout.py` | **Neu:** `PanelSpec`, `PlotLayout` (Grid, Validierung, Vorlagen), Session-Migration |
| `dialogs/plot_layout_dialog.py` | **Neu:** Layout-Dialog mit Grid-Vorschau |
| `analysis/asaxs.py` | **Neu:** Verhältnisse, Korrelation, Interpolation, Term-Zuordnung |
| `dialogs/asaxs_dialog.py` | **Neu:** ASAXS-Dialog (Vorschau, Übernehmen, Export) |
| `dialogs/plot2d_dialog.py` | Projektionen als abgeleitete Datensätze (sessionfest) |
| `scatter_plot.py` | `update_plot()` in Panel-Rendering zerlegt; Panel-Liste; Routing; Sessions |
| `core/models.py` | `DataGroup.subplot_target` → `panel_ids`; `DataSet.from_arrays()`, Inline-Daten |
| `dialogs/axes_dialog.py`, `title_editor_dialog.py`, `curve_settings_dialog.py` | Panel-Bereiche statt Subplot |
| `i18n/translations/*.json` | Neue Texte (`panels`, `layout_dialog`, …) |
| `tests/test_plot_layout.py` | **Neu:** 20 Tests (Layout, Validierung, Migration, Transformationen) |
| `tests/test_derived_datasets.py` | **Neu:** abgeleitete Datensätze, Session-Roundtrip, Panel-Routing |
| `tests/analysis/test_asaxs.py` | **Neu:** Verhältnis/Korrelation inkl. Fehlerfortpflanzung und Interpolation |

Tests: `python -m unittest discover -s tests -t .`
