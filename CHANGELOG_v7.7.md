# Changelog — Version 7.7

## Version 7.7.0 — ScatterForge Plot (RELEASE)

**Release Date:** 22. September 2026
**Status:** Stable Release — Titel- und Achsen-Dialog jetzt subplot-fähig

### ✨ Neue Features & Verbesserungen (7.7.0)

#### 1. Achsen und Limits-Dialog: neuer Bereich „Subplot-Achse"

Seit dem PDDF-, ASAXS-Cross-Term- und dem neuen Significance-Plot (v7.6) gibt es
regelmäßig eine zweite, untere Achse (`ax_sub`). Bisher ließen sich deren
Beschriftung, Limits und Skala nicht über die UI steuern — nur der Hauptplot war
konfigurierbar. Der „Achsen und Limits"-Dialog hat dafür jetzt einen eigenen
Bereich:

- **Y-Achsentitel-Override** für den Subplot (Platzhalter zeigt den aktuellen
  automatischen Titel, z. B. „P(r)", „$I_{cross}$ / cm⁻¹" oder „|I(q)| / σ(q)")
- **Y-Limits** (Min/Max) und **Automatische Skalierung**-Checkbox, analog zum
  Hauptplot
- **Y-Achsen-Skala** (Auto / Linear / Logarithmisch) für den Subplot
- **PDDF-Sonderfall:** Der P(r)-Subplot hat eine unabhängige r-Achse (kein
  gemeinsames X mit dem Hauptplot) — dafür zusätzlich **X-Achsentitel-Override**
  sowie **X-Min/X-Max**
- **ASAXS/Significance:** Die X-Achse ist mit dem Hauptplot gekoppelt (geteilte
  q-Achse); der Dialog zeigt hierfür einen Hinweistext statt eigener X-Controls
- Bereich ist deaktiviert/informativ, wenn der aktuelle Plot-Typ gar keinen
  Subplot hat
- Eigener „Subplot-Einstellungen zurücksetzen"-Button

#### 2. Titel-Editor: optionaler Subplot-Titel

- Neues Feld „Subplot-Titel" (nur relevant/sichtbar, wenn der aktuelle Plot-Typ
  einen Subplot hat) — wird per `ax_sub.set_title()` gerendert, unabhängig vom
  Haupttitel, der bei aktivem Subplot weiterhin als figurweiter `fig.suptitle()`
  läuft
- Nutzt Farbe/Fett/Kursiv des Haupttitels (Schriftgröße automatisch etwas
  kleiner)

### 📦 Neue / geänderte Dateien (7.7.0)

| Datei | Änderungen |
|-------|------------|
| `dialogs/axes_dialog.py` | Neuer Konstruktor-Parameter `subplot_kind`/`sub_axis_limits`/`sub_default_ylabel`, neue Gruppe „Subplot-Achse", `get_sub_axis_limits()`, `reset_sub_limits()` |
| `dialogs/title_editor_dialog.py` | Neuer Konstruktor-Parameter `subplot_kind`, neue Gruppe „Subplot-Titel", `subplot_text` in `get_settings()` |
| `scatter_plot.py` | Neues `self.sub_axis_limits`, `title_settings['subplot_text']`, Helper `_get_active_subplot_kind()`/`_get_default_sub_ylabel()`, Anwendung der Subplot-Limits/-Skala/-Titel in `update_plot()`, Übergabe an beide Dialoge in `show_axes_settings()`/`show_title_editor()`, Session-Persistenz (`sub_axis_limits`, `title_settings.subplot_text`) mit Backward-Compat für ältere Sessions |
| `i18n/translations/de.json`, `en.json` | `axes.subplot.*`, `title_editor.subplot.*` |
| `core/version.py` | `7.6.0` → `7.7.0` |

### ⚠️ Bekannte Einschränkung

Die neuen Subplot-Achseneinstellungen werden (wie schon `axis_limits` zuvor
nicht durchgängig) aktuell **nicht** in Plot-Designs (Design-Manager) oder den
gespeicherten Standard-Plot-Einstellungen mitgespeichert — nur in
Session-Dateien (Speichern/Laden). Das kann bei Bedarf in einem Folge-Release
ergänzt werden.

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.7 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Der Anstoß dafür kam aus
der Praxis: Nach Einführung des Significance-Subplots (v7.6) fiel auf, dass die
bestehenden Einstellungsdialoge nicht für Subplots ausgelegt waren.

---

*Letzte Aktualisierung: 2026-09-22*
