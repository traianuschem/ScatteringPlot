# Changelog — Version 7.5

## Version 7.5.0 — ScatterForge Plot (RELEASE)

**Release Date:** 27. August 2026
**Status:** Stable Release — ASAXS Symlog-Skala, PDDF-Subplot-Routing-Fixes

### ✨ Neue Features & Verbesserungen (7.5.0)

#### 1. Symlog-Skala für ASAXS-Hauptplot

Bisher zeigte der ASAXS-Hauptplot bei log-Skala nur positive I_cross-Werte; negative Werte
wurden komplett verworfen und waren nur im separaten linearen Subplot sichtbar.

- **Neue Y-Achsen-Skala „Symlog"** als ASAXS-Standard (`core/constants.py`, `yscale: 'symlog'`)
- **Feinsteuerung im Achsen-Dialog** (`dialogs/axes_dialog.py`): „Dekaden bis Null" und
  „Größe des linearen Bereichs" — nur sichtbar, wenn Symlog als Y-Skala gewählt ist
- **Automatische linthresh-Bestimmung** (`_compute_symlog_linthresh()` in `scatter_plot.py`):
  berechnet den Übergang zum linearen Nullbereich vom größten angezeigten |y|-Wert abwärts
  (statt vom kleinsten, verrauschten Wert), um den Plot nicht unnötig zu stauchen
- Cross-Term-Werte werden bei aktiver Symlog-Skala jetzt auch im Hauptplot inklusive
  negativer Werte gezeigt (bisher: dort nur positiv-gefiltert)

#### 2. PDDF-Subplot-Routing korrigiert

Der PDDF-Plot-Typ (I(q)-Hauptplot + P(r)-Subplot, siehe v7.3) zeigte bei gemischten Gruppen
— z. B. einem typischen GIFT/GNOM-Export aus SASview: Rohdaten und Fit im q-Raum zusammen
mit P(r) im r-Raum in derselben Gruppe — falsche Ergebnisse.

- **Pro-Datensatz-Routing statt Pro-Gruppen-Routing** (`scatter_plot.py`, `update_plot()`):
  bei `subplot_target == 'both'` (Standard, auch bei gemischten Gruppen) wird jeder Datensatz
  jetzt einzeln anhand `is_pr_data` dem Haupt- oder Subplot zugeordnet, statt wie bisher jeden
  Datensatz der Gruppe auf beiden Achsen zu duplizieren. Explizite Gruppen-Overrides
  („nur Hauptplot" / „nur Subplot") funktionieren weiterhin unverändert
- **Nicht-Positiv-Filter für P(r)-Daten deaktiviert** (`core/models.py`, `DataSet.__init__`):
  P(r)-Kurven beginnen bei r=0 und können im Tail-Bereich leicht negativ werden (normales
  GIFT/GNOM-Verhalten) — beides wurde bisher fälschlich herausgefiltert, analog zur bereits
  bestehenden Ausnahme für den ASAXS-Cross-Term

### 📦 Neue / geänderte Dateien (7.5.0)

| Datei | Änderungen |
|-------|------------|
| `core/constants.py` | ASAXS `yscale`: `'log'` → `'symlog'` |
| `dialogs/axes_dialog.py` | Symlog-Option im Y-Skala-Dropdown, Dekaden-/Linscale-Feinsteuerung |
| `scatter_plot.py` | `_compute_symlog_linthresh()`, Symlog-Anwendung auf Hauptplot-Y-Skala, Cross-Term im Hauptplot bei Symlog inkl. negativer Werte, Pro-Datensatz-Subplot-Routing für PDDF |
| `core/models.py` | `filter_nonpositive` für P(r)-Daten (`is_pr_data`) deaktiviert |
| `i18n/translations/de.json` | `axes.limits.y_scale_symlog`, `symlog_decades*`, `symlog_linscale*` |
| `i18n/translations/en.json` | `axes.limits.y_scale_symlog`, `symlog_decades*`, `symlog_linscale*` |
| `core/version.py` | `7.4.0` → `7.5.0` |

### 🔑 Neue i18n-Keys (7.5.0)

```
axes.limits.y_scale_symlog    axes.limits.symlog_decades*    axes.limits.symlog_linscale*
```

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.5 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die fachliche Anforderung
(ASAXS-Symlog-Darstellung, PDDF-Visualisierung von GIFT/GNOM-Fits) stammt vom Projektinhaber.

---

*Letzte Aktualisierung: 2026-08-27*
