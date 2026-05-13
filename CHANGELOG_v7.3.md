# Changelog — Version 7.3

## Version 7.3.2 — ScatterForge Plot (RELEASE)

**Release Date:** 13. Mai 2026  
**Status:** Stable Release — Unified Curve & Preset Editor, i18n-Vollständigkeit

### ✨ Neue Features & Verbesserungen (7.3.2)

#### 1. Vereinheitlichter Kurven- und Stil-Vorlagen-Editor

Der `CurveSettingsDialog` wurde zum universellen Bearbeitungswerkzeug ausgebaut.
Der bisherige `StylePresetEditDialog` im Design-Manager wird jetzt vollständig durch
denselben Dialog im neuen `preset_mode` ersetzt — alle Einstellungen aus dem
Kontext-Menü „Kurve bearbeiten" sind damit auch für Stil-Vorlagen verfügbar.

**Neue Felder in Stil-Vorlagen (`design_manager → Stil-Vorlagen → Bearbeiten`):**
- Fehlerbalken: Darstellungsstil (Fläche / Balken), Cap-Größe, Linienbreite, Transparenz
- SNR-Qualitätsmarker: Schwellenwert, Marker-Typen, Transparenz, Fehlerbalken-Anzeige
- Name und Beschreibung der Vorlage direkt im Editor änderbar

**Verhalten im `preset_mode`:**
- Farb-Picker ausgeblendet (Vorlagen sind farblos)
- ASAXS- und Plotbereich-Abschnitte ausgeblendet
- SNR-Einstellungen immer verfügbar (keine Fehlerdaten-Abhängigkeit)
- Neue Vorlagen öffnen sofort den vollständigen Editor nach der Namenseingabe

**`apply_style_preset()` erweitert (`core/models.py`):**
- Wendet jetzt alle neuen Felder an: `show_errorbars`, `errorbar_capsize`,
  `errorbar_linewidth`, `snr_visualization`, `snr_threshold`, `snr_good_marker`,
  `snr_poor_marker`, `snr_poor_alpha`, `snr_show_errorbars`

#### 2. i18n-Vollständigkeit für CurveSettingsDialog

Alle bisher hardcodierten deutschen Strings im `CurveSettingsDialog` wurden durch
`tr()`-Aufrufe ersetzt. Neue Übersetzungsabschnitte in `de.json` und `en.json`:

| Schlüssel | Inhalt |
|-----------|--------|
| `curve_settings.quality.*` | SNR-Datenqualitäts-Sektion (11 Keys) |
| `curve_settings.subplot.*` | Plotbereich-Sektion (5 Keys) |
| `curve_settings.asaxs.*` | ASAXS-Term-Typ-Sektion (6 Keys) |
| `curve_settings.preset_title/info` | Fenstertitel und Info im Preset-Modus |
| `curve_settings.preset_meta.*` | Name/Beschreibung-Felder (4 Keys) |
| `curve_settings.error_bars.info_*` | Erklärungstexte je Darstellungsstil (3 Keys) |
| `curve_settings.error_bars.stem_*` | Stem-Plot-spezifische Labels |
| `design_manager.info/error/warning` | Fehlende Meldungs-Keys ergänzt |
| `design_manager.styles.select_style` | Auswahlhinweis |
| `design_manager.styles.custom` | Bezeichnung neuer Vorlagen |

#### 3. Bugfixes

- **Doppelter `errorbar_alpha`-Widget** im `CurveSettingsDialog` behoben
  (Zeile 6 war ein versehentliches Duplikat von Zeile 4)
- **`CurveSettingsDialog` scroll-fähig**: Inhalt wird jetzt in einem `QScrollArea`
  eingebettet, sodass der Dialog auch bei kleinen Bildschirmhöhen vollständig
  zugänglich bleibt

---

## Version 7.3.1 — ScatterForge Plot (RELEASE)

**Release Date:** 12. Mai 2026  
**Status:** Stable Release — ASAXS-Analyse, SNR-Qualitätsmarker, Subplot-Routing

### 🎉 Hauptfeatures (7.3.1)

#### 1. Neuer Plot-Typ: ASAXS

Spezialisierter Log-Log-Plot für anomale Kleinwinkelröntgenstreuung.

- **Plot-Typ „ASAXS"** in `core/constants.py` registriert (q / nm⁻¹ vs. I / cm⁻¹, log-log)
- **Auto-Erkennung** des Term-Typs aus dem Dateinamen:
  - `*_icross*` / `*_Icross*` → Cross-Term (I_cross)
  - `*_in_*` / `*_IN*` → Normal-SAXS (I_N)
  - `*_ia_*` / `*_IA*` → Anomaler Self-Term (I_A)
- **Manuelle Überschreibung** per Rechtsklick → „Kurve bearbeiten" → ASAXS-Abschnitt
- **Cross-Term-Filterung**: `filter_nonpositive` wird für erkannte Cross-Term-Datensätze
  automatisch deaktiviert (physikalisch korrekt — I_cross kann negativ sein)
- **Haupt-Plot**: Log-Log, nur positive Werte (auch für I_cross)
- **„± Subplot"-Button**: optionaler linearer Subplot mit vollständigem I_cross inkl.
  negativer Werte und `fill_between`-Fehlerband

#### 2. SNR-Qualitätsmarker (für alle Plot-Typen)

Statistische Datenpunkt-Visualisierung auf Basis des Signal-Rausch-Verhältnisses.

- **Aktivierung** pro Datensatz: Rechtsklick → „Kurve bearbeiten" → „Datenqualität"
- **Darstellung:**
  - Gute Punkte (SNR ≥ Schwellenwert): gefüllter Marker
  - Schlechte Punkte (SNR < Schwellenwert): offener Marker, gedimmt
- **Konfigurierbar per Datensatz:**
  - SNR-Schwellenwert (Standard: 1,0)
  - Marker-Stil für gute / schlechte Punkte (je 13 Stile)
  - Transparenz schlechter Punkte (0–100 %)
  - Optionale subtile Fehlerbalken auf alle sichtbaren Punkte
- Benötigt Fehlerdaten (3. Spalte) — Checkbox wird ohne Fehlerdaten deaktiviert

#### 3. Subplot-Routing per Gruppe

Gruppen können jetzt festlegen, in welchem Axes-Bereich ihre Daten dargestellt werden.

- **Neue Attribute** `DataGroup.subplot_target`: `'both'` | `'main'` | `'sub'`
- **Einstellbar** per Rechtsklick auf Gruppe → „Gruppe bearbeiten" → Abschnitt „Plotbereich"
- **Rendering**: Der Update-Plot-Loop leitet je nach `subplot_target` auf `ax_main`,
  `ax_sub` oder beide weiter — gilt für alle Fehlerbalken-Stile und SNR-Modus
- **Unified Subplot-Architektur**: PDDF und ASAXS nutzen jetzt dieselbe `ax_sub`-Variable

#### 4. Bugfix: Drag & Drop setzte alle Gruppenfarben zurück

`unify_group_colors()` überschrieb beim Hinzufügen eines Datensatzes per Drag & Drop
die manuell gesetzten Farben aller Datensätze in der Gruppe.

- **Fix**: Nur Datensätze ohne gesetzte Farbe (`color is None`) werden automatisch
  eingefärbt; bei allen bereits gefärbten Datensätzen passiert nichts.

### 📦 Neue / geänderte Dateien (7.3.1)

| Datei | Änderungen |
|-------|------------|
| `core/constants.py` | ASAXS zu `PLOT_TYPES` hinzugefügt |
| `core/models.py` | `DataSet`: `data_term`, `snr_*`-Attribute, `_auto_detect_asaxs_term()`; `DataGroup`: `subplot_target` |
| `scatter_plot.py` | ASAXS-Button, Dual-Panel-Layout (unified), SNR-Renderer, Cross-Term-Subplot, `unify_group_colors()`-Fix, Subplot-Routing |
| `dialogs/curve_settings_dialog.py` | SNR-Abschnitt, Plotbereich-Abschnitt, ASAXS-Abschnitt (mit group-Parameter) |
| `i18n/translations/de.json` | ASAXS-Plot-Typ-Beschriftungen |
| `i18n/translations/en.json` | ASAXS-Plot-Typ-Beschriftungen |
| `core/version.py` | `7.1.2` → `7.3.1` |

### 🔑 Neue i18n-Keys (7.3.1)

```
curve_settings.quality.*    curve_settings.subplot.*    curve_settings.asaxs.*
```

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**  
Der Programmcode für ScatterForge Plot v7.3 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die physikalische Spezifikation
der ASAXS-Separation und die fachliche Anforderungsanalyse stammen vom Projektinhaber.

---

*Letzte Aktualisierung: 2026-05-13*
