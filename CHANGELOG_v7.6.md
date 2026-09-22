# Changelog — Version 7.6

## Version 7.6.0 — ScatterForge Plot (RELEASE)

**Release Date:** 22. September 2026
**Status:** Stable Release — Neuer Plot-Typ „Significance" (Signifikanz-Subplot)

### ✨ Neue Features & Verbesserungen (7.6.0)

#### 1. Neuer Plot-Typ: Significance

Zeigt neben den gewohnten I(q)-Daten (Hauptplot, log-log, inkl. Fehlerband) einen
zweiten Achsen-Bereich mit der punktweisen Signifikanz |I(q)/σ(q)|, um direkt
abzulesen, bis zu welchem q-Wert eine Kurve noch statistisch belastbar ist.

- **Plot-Typ „Significance"** in `core/constants.py` registriert (q / nm⁻¹ vs.
  I / a.u., log-log) — der Hauptplot verhält sich wie „Log-Log" und benötigt keine
  Sonderbehandlung im Rendering
- **Signifikanz-Subplot** (`ax_sub`, geteilte log-q-Achse mit dem Hauptplot, analog
  zum ASAXS-Cross-Term-Subplot): pro Datensatz eine dünne Rohkurve |I/σ| plus eine
  dicke, über ein gleitendes Median-Fenster geglättete Kurve — robust gegen
  einzelne Ausreißer-Rauschspitzen (`_render_significance_subplot()`,
  `_rolling_median()` in `scatter_plot.py`)
- **Gestrichelte σ-Referenzlinien** im Subplot (Standard: 3σ/2σ/1σ), jeweils mit
  Beschriftung am linken Rand
- **Einstellbar über das Options-Panel** (nur sichtbar im Significance-Modus):
  - Glättungsfenster (Punkte, ungerade, Standard 9)
  - σ-Schwellenwerte (kommagetrennt, Standard „3,2,1")
- **`subplot_target` pro Gruppe** wird respektiert: Steht eine Gruppe auf „nur
  Hauptplot", erscheint ihre Signifikanzkurve nicht im Subplot (konsistent mit dem
  bestehenden PDDF/ASAXS-Subplot-Routing-Mechanismus)

### 📦 Neue / geänderte Dateien (7.6.0)

| Datei | Änderungen |
|-------|------------|
| `core/constants.py` | `'Significance'` zu `PLOT_TYPES` hinzugefügt |
| `scatter_plot.py` | Neuer Layout-Zweig für `ax_sub` (Significance), `_render_significance_subplot()`, `_rolling_median()`, `_get_significance_thresholds()`, Einbindung in Gruppen-/Unassigned-Render-Loop, neue Options-Felder (Fenster/Schwellen) samt Sichtbarkeits-Umschaltung in `change_plot_type()`, `q_types`-Erweiterung für Referenzlinien-Umrechnung |
| `i18n/translations/de.json` | `options.significance_window*`, `options.significance_thresholds*` |
| `i18n/translations/en.json` | `options.significance_window*`, `options.significance_thresholds*` |
| `core/version.py` | `7.5.0` → `7.6.0` |

### 🔑 Neue i18n-Keys (7.6.0)

```
options.significance_window    options.significance_window_tooltip
options.significance_thresholds    options.significance_thresholds_tooltip
```

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.6 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die fachliche Anforderung
(Signifikanz-Visualisierung zur Bestimmung des vertrauenswürdigen q-Bereichs einer
Streukurve) stammt vom Projektinhaber.

---

*Letzte Aktualisierung: 2026-09-22*
