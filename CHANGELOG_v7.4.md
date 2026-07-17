# Changelog — Version 7.4

## Version 7.4.0 — ScatterForge Plot (RELEASE)

**Release Date:** 17. Juli 2026
**Status:** Stable Release — Flexible Spaltenzuordnung, dlnI/dlnq-Plot, Gruppen-Sichtbarkeit

### ✨ Neue Features & Verbesserungen (7.4.0)

#### 1. Flexible Spaltenzuordnung für Datendateien

Bisher wurden Datendateien starr nach Spaltenanzahl interpretiert (2 → x,y; 3 → x,y,y_err;
4 → x,y,x_err,y_err mit stillschweigend verworfenem x_err; >4 → nur die ersten 3 Spalten).
Das reichte nicht für Dateien mit abweichender Spaltenreihenfolge oder zusätzlichen,
nicht benötigten Spalten.

- **Neue Sektion „Datenspalten"** im „Kurve bearbeiten"-Dialog: erscheint automatisch bei
  Dateien mit mehr als 2 Spalten und bietet je eine Auswahl für X-, Y- und Fehler-Spalte
  („Keine" als Option für den Fehlerkanal)
- **Standardauswahl bleibt abwärtskompatibel**: ohne manuelle Änderung verhält sich jede
  Datei exakt wie zuvor (2 Spalten → x,y; 3 Spalten → x,y,y_err; ≥4 Spalten → x,y,y_err
  aus Spalte 4)
- **Rohdaten werden vollständig vorgehalten** (`DataSet.raw_data`), sodass eine Umstellung
  der Zuordnung ohne erneutes Einlesen der Datei sofort auf den Plot angewendet wird
- **Session-Persistenz**: gewählte Spaltenzuordnung wird gespeichert und beim Laden
  wiederhergestellt; alte Sessions ohne diese Angabe fallen auf das Standardverhalten zurück
- Nur für Einzel-Datensatz-Bearbeitung verfügbar (bei Gruppen-Bearbeitung ausgeblendet, da
  Spaltenlayout dateispezifisch ist)

**Neue/geänderte Funktionen (`utils/data_loader.py`):**
`load_raw_data()`, `default_column_mapping()`, `select_columns()` — `load_scattering_data()`
bleibt als abwärtskompatibler Wrapper erhalten.

#### 2. Neuer Plot-Typ: dlnI/dlnq

Werkzeug zur schnellen Identifikation versteckter Features (Schultern, Knicke) in
Streukurven, die im normalen Log-Log-Plot leicht übersehen werden.

- **Plot-Typ „dlnI/dlnq"** in `core/constants.py` registriert — stellt die logarithmische
  Ableitung d ln(I)/d ln(q) gegen q dar
- **Einstellbares Glättungsfenster** (Savitzky-Golay, Polynomordnung 2) direkt im
  Options-Panel, nur sichtbar im dlnI/dlnq-Modus — reduziert Rauschen in realen
  Messdaten, ohne echte Features zu verschlucken; automatischer Fallback auf kleinere
  bzw. keine Glättung bei sehr wenigen Datenpunkten
- **Fehlerbalken bewusst deaktiviert** für diesen Plot-Typ, da die Fehlerfortpflanzung
  durch Glättung und numerische Ableitung nicht trivial und potenziell irreführend wäre
- **Referenzlinien-Umrechnung** unterstützt (x-Achse bleibt q, wie bei Log-Log/Porod/Kratky)

#### 3. Gruppen im Plot ein-/ausblenden

Bisher ließen sich nur einzelne Kurven per Checkbox im Baum ein-/ausblenden — für ganze
Gruppen gab es trotz vorhandenem `DataGroup.visible`-Attribut keine Bedienoberfläche.

- **Checkbox auf Gruppen-Ebene** im Datensatz-Baum, analog zur bestehenden Kurven-Checkbox
- Deaktivieren blendet alle Kurven der Gruppe inkl. Legendeneintrag komplett aus dem Plot
  aus, unabhängig vom Sichtbarkeits-Status der einzelnen Kurven darin
- Funktioniert konsistent beim manuellen Erstellen einer Gruppe, beim Neuaufbau des Baums
  und beim Laden gespeicherter Sessions
- Nutzt die bereits bestehende Session-Persistenz von `DataGroup.visible`

### 📦 Neue / geänderte Dateien (7.4.0)

| Datei | Änderungen |
|-------|------------|
| `utils/data_loader.py` | `load_raw_data()`, `default_column_mapping()`, `select_columns()` neu; `load_scattering_data()` als Wrapper |
| `core/models.py` | `DataSet`: `raw_data`, `col_x`/`col_y`/`col_err`, `set_column_mapping()` |
| `core/constants.py` | `dlnI/dlnq` zu `PLOT_TYPES` hinzugefügt |
| `dialogs/curve_settings_dialog.py` | Neue Sektion „Datenspalten" (nur Einzel-Dataset-Modus, Dateien mit >2 Spalten) |
| `scatter_plot.py` | Spaltenzuordnung anwenden (`edit_curve_settings`), dlnI/dlnq-Transformation + Glättungsfenster-Widget, Gruppen-Sichtbarkeits-Checkbox (`rebuild_tree`, `create_group`, Session-Restore, `on_tree_item_changed`) |
| `i18n/translations/de.json` | `curve_settings.columns.*`, `options.dlnidlnq_smooth_window*` |
| `i18n/translations/en.json` | `curve_settings.columns.*`, `options.dlnidlnq_smooth_window*` |
| `core/version.py` | `7.3.2` → `7.4.0` |

### 🔑 Neue i18n-Keys (7.4.0)

```
curve_settings.columns.*    options.dlnidlnq_smooth_window*
```

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.4 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die fachliche Anforderung
(Spaltenauswahl, dlnI/dlnq-Analyse, Gruppen-Sichtbarkeit) stammt vom Projektinhaber.

---

*Letzte Aktualisierung: 2026-07-17*
