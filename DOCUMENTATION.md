# ScatterForge Plot - Technische Dokumentation

**Version 5.6** | **Letzte Aktualisierung**: 2025-01-09

Diese Dokumentation beschreibt die technische Architektur, Module und Implementierungsdetails von ScatterForge Plot.

---

## 📑 Inhaltsverzeichnis

1. [Architektur-Übersicht](#architektur-übersicht)
2. [Module-Dokumentation](#module-dokumentation)
3. [Datenmodelle](#datenmodelle)
4. [Konfigurations-System](#konfigurations-system)
5. [Logging-System](#logging-system)
6. [Session-Format](#session-format)
7. [Plot-System](#plot-system)
8. [Erweiterungen entwickeln](#erweiterungen-entwickeln)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Architektur-Übersicht

### Modulare Struktur

ScatterForge Plot folgt einer modularen Architektur mit klarer Trennung der Verantwortlichkeiten:

```
ScatteringPlot/
├── scatter_plot.py          # Hauptanwendung (Qt6 GUI)
├── core/                    # Kern-Komponenten
│   ├── models.py           # Datenmodelle (DataSet, DataGroup)
│   └── plot_manager.py     # Plot-Verwaltung
├── dialogs/                # GUI-Dialoge
│   ├── export_dialog.py    # Export-Einstellungen
│   ├── design_manager.py   # Design-Verwaltung
│   ├── font_dialog.py      # Schriftart-Einstellungen
│   └── ...
├── utils/                  # Hilfsfunktionen
│   ├── user_config.py      # Benutzer-Konfiguration
│   ├── data_loader.py      # Daten-Laden
│   ├── logger.py           # Logging-System (v5.6)
│   └── ...
└── resources/              # Ressourcen (optional)
```

### Technologie-Stack

| Komponente | Technologie | Version |
|------------|-------------|---------|
| **GUI-Framework** | PySide6 (Qt6) | ≥6.5.0 |
| **Plotting** | Matplotlib | ≥3.7.0 |
| **Numerik** | NumPy | ≥1.24.0 |
| **Backend** | matplotlib.backends.backend_qtagg | - |
| **Logging** | Python logging module | Standard |

### Datenfluss

```
1. Laden: Datei → data_loader.py → DataSet
2. Gruppierung: DataSet → DataGroup → groups[]
3. Transformation: DataGroup → Stack-Faktoren → plot_data
4. Rendering: plot_data → PlotManager → Matplotlib → Canvas
5. Export: Canvas → export_dialog.py → PNG/SVG/PDF/EPS
```

---

## Module-Dokumentation

### `scatter_plot.py` - Hauptanwendung

**Beschreibung**: Qt6-basierte Haupt-GUI-Anwendung

**Hauptklasse**: `ScatterPlotApp(QMainWindow)`

#### Wichtige Attribute

```python
self.datasets = []              # Liste aller geladenen Datasets
self.groups = []                # Liste aller Gruppen
self.config = UserConfig()      # Benutzer-Konfiguration
self.logger = Logger            # Logging-System (v5.6)

# Plot-Einstellungen
self.legend_settings = {...}    # Legend-Konfiguration
self.grid_settings = {...}      # Grid-Konfiguration
self.font_settings = {...}      # Schriftart-Konfiguration
self.current_plot_design = str  # Aktives Design

# UI-Komponenten
self.tree = QTreeWidget         # Dataset-/Gruppen-Baum
self.canvas = FigureCanvas      # Matplotlib Canvas
self.figure = Figure            # Matplotlib Figure
self.ax = Axes                  # Matplotlib Axes
```

#### Wichtige Methoden

**`__init__(self)`**
- Initialisiert Haupt-Fenster
- Lädt Benutzer-Konfiguration
- Richtet Logger ein (v5.6)
- Lädt Standard-Plot-Einstellungen (v5.4)
- Erstellt UI-Komponenten

**`load_data(self)`**
- Öffnet Datei-Dialog
- Lädt ausgewählte Dateien
- Erstellt DataSet-Objekte
- Fügt zu Tree-Widget hinzu
- Aktualisiert Plot

**`update_plot(self)`**
- Sammelt alle sichtbaren Datasets
- Wendet Plot-Typ-Transformationen an
- Wendet Stack-Faktoren an
- Wendet Farbschemata an (global/gruppenspezifisch, v5.4)
- Rendert Plot mit matplotlib
- Wendet Font/Grid/Legend-Einstellungen an

**`auto_group_by_magnitude(self)` (v5.6)**
- Erstellt für jedes ausgewählte Dataset eine eigene Gruppe
- Verwendet automatische Stack-Faktoren: 10^0, 10^1, 10^2, ...
- Gruppe-Name = Dataset-Name
- Optimiert für Log-Log-Plots

**`save_session(self)` / `load_session(self)`**
- Speichert/Lädt komplette Projektzustände
- JSON-Format
- Enthält: Datasets, Gruppen, Plot-Einstellungen, Annotations

---

### `core/models.py` - Datenmodelle

#### Klasse: `DataSet`

**Beschreibung**: Repräsentiert einen einzelnen Datensatz mit Stil-Informationen

```python
class DataSet:
    def __init__(self, filepath, name=None, apply_auto_style=True):
        self.filepath = Path(filepath)      # Pfad zur Datei
        self.name = str                     # Dataset-Name
        self.display_label = str            # Anzeige-Label

        # Daten
        self.data = np.ndarray              # Rohdaten (N×2 oder N×3)
        self.x = np.ndarray                 # X-Werte (q)
        self.y = np.ndarray                 # Y-Werte (Intensität)
        self.y_err = np.ndarray or None     # Fehlerbalken (optional)

        # Stil
        self.line_style = str or None       # '-', '--', '-.', ':'
        self.marker_style = str or None     # 'o', 's', '^', 'v', etc.
        self.color = str or None            # Hex-Farbe oder None
        self.line_width = float             # 1-5
        self.marker_size = float            # 1-10
        self.show_in_legend = bool          # In Legende anzeigen
```

**Methoden**:
- `load_data()`: Lädt Daten aus Datei
- `apply_auto_style()`: Wendet Stil basierend auf Dateiname an
- `apply_style_preset(preset_name)`: Wendet Stil-Vorlage an
- `get_plot_style()`: Gibt matplotlib-Format-String zurück
- `to_dict()` / `from_dict()`: Serialisierung

**Auto-Stil-Erkennung**:
```python
# Dateiname enthält → Stil
'fit'              → Durchgezogene Linie ('-')
'messung/measure'  → Marker ('o')
'sim/simulation'   → Gestrichelt ('--')
'theo/theorie'     → Strich-Punkt ('-.')
```

#### Klasse: `DataGroup`

**Beschreibung**: Repräsentiert eine Gruppe von Datasets mit gemeinsamen Eigenschaften

```python
class DataGroup:
    def __init__(self, name, stack_factor=1.0, color_scheme=None):
        self.name = str                     # Gruppen-Name
        self.datasets = []                  # Liste von DataSet-Objekten
        self.stack_factor = float           # Multiplikator für Y-Werte
        self.visible = bool                 # Sichtbarkeit
        self.collapsed = bool               # Tree-Zustand
        self.color_scheme = str or None     # Gruppenspezifische Palette (v5.4)
```

**Stack-Faktoren** (nicht-kumulativ!):
```python
# Beispiel: 3 Gruppen mit Stack-Faktoren 1, 10, 100
Gruppe A (×1):    y_plot = y_original × 1
Gruppe B (×10):   y_plot = y_original × 10
Gruppe C (×100):  y_plot = y_original × 100
```

**Methoden**:
- `add_dataset(dataset)`: Dataset hinzufügen
- `remove_dataset(dataset)`: Dataset entfernen
- `to_dict()` / `from_dict()`: Serialisierung

---

### `utils/user_config.py` - Konfigurationsverwaltung

**Beschreibung**: Verwaltet Benutzer-Konfiguration in `~/.tubaf_scatter_plots/`

#### Klasse: `UserConfig`

```python
class UserConfig:
    def __init__(self):
        self.config_dir = Path.home() / ".tubaf_scatter_plots"
        self.config_file = self.config_dir / "config.json"

        # Konfigurationen
        self.color_schemes = {}             # Farbpaletten
        self.style_presets = {}             # Stil-Vorlagen
        self.plot_designs = {}              # Plot-Designs
        self.default_plot_settings = {}     # Standard-Einstellungen (v5.4)
```

#### Wichtige Methoden

**`load_config()`**
- Lädt config.json
- Initialisiert Standard-Werte wenn nicht vorhanden

**`save_config()`**
- Speichert alle Einstellungen als JSON
- Erstellt Verzeichnis wenn nötig

**`save_default_plot_settings(legend, grid, font, design)` (v5.4)**
- Speichert Plot-Einstellungen als Programmstandard
- Persistiert in config.json
- Wird beim nächsten Start geladen

**`get_default_plot_settings()` (v5.4)**
- Gibt gespeicherte Standard-Einstellungen zurück
- Gibt None wenn keine vorhanden

**`get_style_by_filename(filepath)`**
- Erkennt Stil basierend auf Dateiname
- Gibt passende Stil-Vorlage zurück

#### Datei-Struktur

**`config.json`**:
```json
{
  "color_schemes": {
    "Custom 1": ["#FF0000", "#00FF00", "#0000FF"]
  },
  "style_presets": {
    "Messung": {
      "line_style": null,
      "marker_style": "o",
      "line_width": 2,
      "marker_size": 4
    }
  },
  "plot_designs": {
    "My Design": {
      "legend_settings": {...},
      "grid_settings": {...},
      "font_settings": {...}
    }
  },
  "default_plot_settings": {
    "legend_settings": {...},
    "grid_settings": {...},
    "font_settings": {...},
    "current_plot_design": "Standard"
  }
}
```

---

### `utils/logger.py` - Logging-System (v5.6)

**Beschreibung**: Zentrales Logging-System basierend auf Python's logging-Modul

#### Architektur

```
Logger "ScatterForge"
├── Console Handler (StreamHandler)
│   ├── Level: INFO+
│   ├── Format: [HH:MM:SS] LEVEL Message
│   └── Ausgabe: stdout
└── File Handler (FileHandler)
    ├── Level: DEBUG+
    ├── Format: [HH:MM:SS] LEVEL Message
    ├── Ausgabe: ~/.tubaf_scatter_plots/logs/scatterplot_YYYYMMDD.log
    └── Encoding: UTF-8
```

#### Funktionen

**`setup_logger(name='ScatteringPlot', level=logging.DEBUG, log_to_file=True)`**

Richtet Logger ein mit:
- Dual-Handler-System (Console + File)
- Timestamp-Format `[HH:MM:SS]`
- Automatische Log-Verzeichnis-Erstellung
- Tägliche Log-Dateien
- Verhindert doppelte Handler

**`get_logger()`**

Gibt konfigurierten Logger zurück.

#### Verwendung

```python
from utils.logger import setup_logger, get_logger

# In Hauptanwendung
logger = setup_logger('ScatterForge')
logger.info("Anwendung gestartet")

# In anderen Modulen
from utils.logger import get_logger
logger = get_logger()
logger.debug("Detaillierte Info")
logger.info("Wichtige Aktion")
logger.warning("Warnung")
logger.error("Fehler aufgetreten")
```

#### Log-Levels

| Level | Console | Datei | Verwendung |
|-------|---------|-------|------------|
| DEBUG | ❌ | ✅ | Detaillierte Debug-Infos |
| INFO | ✅ | ✅ | Wichtige Benutzer-Aktionen |
| WARNING | ✅ | ✅ | Warnungen |
| ERROR | ✅ | ✅ | Fehler |
| CRITICAL | ✅ | ✅ | Kritische Fehler |

#### Log-Dateien

**Speicherort**: `~/.tubaf_scatter_plots/logs/`

**Namenskonvention**: `scatterplot_YYYYMMDD.log`

**Beispiel-Log**:
```
[14:23:45] INFO     ScatterForge Plot v5.6 gestartet
[14:23:45] DEBUG    Log-Datei: /home/user/.tubaf_scatter_plots/logs/scatterplot_20250109.log
[14:23:45] DEBUG    Prüfe auf gespeicherte Standard-Plot-Einstellungen...
[14:23:45] INFO     Lade gespeicherte Standard-Plot-Einstellungen
[14:23:46] INFO     Lade 3 Datei(en)...
[14:23:46] DEBUG    Geladen: sample1.dat (1024 Datenpunkte)
[14:23:46] DEBUG    Geladen: sample2.dat (2048 Datenpunkte)
[14:23:46] DEBUG    Geladen: fit_result.dat (1024 Datenpunkte)
[14:23:47] INFO     Auto-Gruppierung erstellt 3 Gruppen
```

---

### `utils/data_loader.py` - Daten-Laden

**Beschreibung**: Lädt Streudaten aus verschiedenen Dateiformaten

#### Funktion: `load_scattering_data(filepath)`

**Parameter**:
- `filepath`: Pfad zur Datendatei (.dat, .txt, .csv)

**Rückgabe**:
- `np.ndarray`: Array mit Shape (N, 2) oder (N, 3)
  - Spalte 0: q-Werte
  - Spalte 1: Intensitäts-Werte
  - Spalte 2: Fehlerbalken (optional)

**Unterstützte Formate**:
```
# Kommentare (werden ignoriert)
# q / nm^-1    I / a.u.
0.1            1000.5
0.2            856.3

# Mit Fehlerbalken
# q / nm^-1    I / a.u.    I_err
0.1            1000.5      15.2
0.2            856.3       12.8
```

**Trennzeichen**: Whitespace, Tabs, Kommas

**Fehlerbehandlung**:
- Ignoriert Kommentarzeilen (#)
- Überspringt leere Zeilen
- ValueError bei ungültigen Daten

---

### `dialogs/export_dialog.py` - Export-Dialog

**Beschreibung**: Dialog für Export-Einstellungen

#### Klasse: `ExportDialog(QDialog)`

**Features**:
- Format-Auswahl: PNG, SVG, PDF, EPS
- DPI-Einstellung: 100-600 dpi
- Größe: Breite × Höhe in cm
- **Standard 16:10**: 25.4 cm × 15.875 cm (v5.4)
- Tight Layout: Checkbox

**Standard-Einstellungen**:
```python
{
    'format': 'png',
    'dpi': 300,
    'width': 10.0,      # inch (= 25.4 cm)
    'height': 6.25,     # inch (= 15.875 cm) → 16:10
    'tight_layout': True
}
```

**Export-Prozess**:
1. Benutzer öffnet Dialog
2. Wählt Format, DPI, Größe
3. Klickt "Speichern"
4. `save_figure()` wird aufgerufen
5. matplotlib speichert Figure

---

### `dialogs/design_manager.py` - Design-Manager

**Beschreibung**: Verwaltung von Plot-Designs und Standard-Einstellungen

#### Klasse: `DesignManagerDialog(QDialog)`

**Tabs**:
1. **Plot-Designs**: Verwaltung gespeicherter Designs
2. **Farbschema-Manager**: Eigene Farbpaletten erstellen
3. **Stil-Vorlagen**: Eigene Stil-Templates

#### Features (v5.4)

**"⭐ Als Programmstandard speichern"-Button**:
- Speichert aktuelle Plot-Einstellungen als Standard
- Persistiert in `config.json`
- Wird beim nächsten Programmstart automatisch geladen
- Umfasst:
  - Legend-Einstellungen
  - Grid-Einstellungen
  - Font-Einstellungen
  - Aktuelles Plot-Design

**Methode: `save_as_default()`**:
```python
def save_as_default(self):
    """Speichert aktuelle Einstellungen als Programmstandard"""
    logger = get_logger()
    logger.info("Speichere aktuelle Einstellungen als Programmstandard...")

    self.config.save_default_plot_settings(
        self.parent_app.legend_settings,
        self.parent_app.grid_settings,
        self.parent_app.font_settings,
        self.parent_app.current_plot_design
    )

    logger.info("Standard-Einstellungen erfolgreich gespeichert")
```

---

## Konfigurations-System

### Verzeichnis-Struktur

```
~/.tubaf_scatter_plots/
├── config.json              # Haupt-Konfiguration
├── color_schemes.json       # (deprecated, jetzt in config.json)
├── style_presets.json       # (deprecated, jetzt in config.json)
└── logs/                    # Log-Verzeichnis (v5.6)
    ├── scatterplot_20250109.log
    ├── scatterplot_20250108.log
    └── ...
```

### config.json Struktur

```json
{
  "color_schemes": {
    "TUBAF": ["#003560", "#C50E1F", ...],
    "Custom 1": ["#FF0000", "#00FF00", "#0000FF"]
  },

  "style_presets": {
    "Messung": {
      "line_style": null,
      "marker_style": "o",
      "line_width": 2,
      "marker_size": 4
    },
    "Fit": {
      "line_style": "-",
      "marker_style": null,
      "line_width": 2,
      "marker_size": 4
    }
  },

  "plot_designs": {
    "Standard": {
      "legend_settings": {
        "show": true,
        "location": "best",
        "fontsize": 10,
        "frameon": true,
        "framealpha": 0.8,
        "ncol": 1
      },
      "grid_settings": {
        "major": true,
        "minor": false,
        "major_alpha": 0.3,
        "minor_alpha": 0.15
      },
      "font_settings": {
        "title_size": 14,
        "title_bold": true,
        "label_size": 12,
        "tick_size": 10
      }
    }
  },

  "default_plot_settings": {
    "legend_settings": {...},
    "grid_settings": {...},
    "font_settings": {...},
    "current_plot_design": "Standard"
  }
}
```

### Einstellungs-Priorität

1. **Session-Einstellungen**: Gespeichert in .tsp-Dateien (höchste Priorität)
2. **Standard-Einstellungen**: Aus `default_plot_settings` in config.json
3. **Programm-Defaults**: Hardcodierte Werte in scatter_plot.py

---

## Session-Format

### Datei-Endung

`.tsp` (TUBAF Scattering Plot)

### JSON-Struktur

```json
{
  "version": "5.6",
  "groups": [
    {
      "name": "Sample 1",
      "stack_factor": 1.0,
      "visible": true,
      "collapsed": false,
      "color_scheme": "viridis",
      "datasets": [
        {
          "filepath": "/path/to/sample1.dat",
          "name": "sample1",
          "display_label": "Sample 1 - RT",
          "line_style": null,
          "marker_style": "o",
          "color": "#FF0000",
          "line_width": 2,
          "marker_size": 4,
          "show_in_legend": true
        }
      ]
    }
  ],
  "unassigned": [...],

  "plot_settings": {
    "plot_type": "log-log",
    "show_error_bars": true,
    "use_math_text": false,
    "x_label": "q / nm⁻¹",
    "y_label": "I / a.u.",
    "title": "Scattering Data",
    "x_limits": [null, null],
    "y_limits": [null, null],
    "color_scheme": "TUBAF"
  },

  "legend_settings": {...},
  "grid_settings": {...},
  "font_settings": {...},
  "current_plot_design": "Standard",

  "annotations": [
    {
      "type": "text",
      "text": "Peak",
      "x": 0.5,
      "y": 1000,
      "fontsize": 12,
      "color": "#000000"
    }
  ],

  "reference_lines": [
    {
      "type": "vertical",
      "position": 0.5,
      "linestyle": "--",
      "color": "#FF0000",
      "label": "Q-Peak"
    }
  ]
}
```

### Speichern/Laden

**Speichern**:
```python
def save_session(self):
    # Sammle alle Daten
    session_data = {
        'version': '5.6',
        'groups': [g.to_dict() for g in self.groups],
        'plot_settings': {...},
        # ...
    }

    # Speichere als JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)
```

**Laden**:
```python
def load_session(self):
    # Lade JSON
    with open(filepath, 'r', encoding='utf-8') as f:
        session_data = json.load(f)

    # Rekonstruiere Gruppen
    self.groups = [DataGroup.from_dict(g) for g in session_data['groups']]

    # Stelle Plot-Einstellungen wieder her
    self.plot_settings = session_data['plot_settings']
```

---

## Plot-System

### Plot-Typen

#### Log-Log
```python
ax.set_xscale('log')
ax.set_yscale('log')
xlabel = 'q / nm⁻¹'
ylabel = 'I / a.u.'
```

#### Porod
```python
ax.set_xscale('log')
ax.set_yscale('log')
y_plot = y * (x ** 4)  # I·q⁴
xlabel = 'q / nm⁻¹'
ylabel = 'I·q⁴ / a.u.'
```

#### Kratky
```python
ax.set_xscale('log')
ax.set_yscale('log')
y_plot = y * (x ** 2)  # I·q²
xlabel = 'q / nm⁻¹'
ylabel = 'I·q² / a.u.'
```

#### Guinier
```python
ax.set_xscale('linear')
ax.set_yscale('linear')
x_plot = x ** 2  # q²
y_plot = np.log(y)  # ln(I)
xlabel = 'q² / nm⁻²'
ylabel = 'ln(I)'
```

### Farbschema-System

#### Globales Farbschema

Wird auf alle Datasets angewendet, wenn Gruppe kein eigenes Schema hat.

```python
def update_plot(self):
    # Farbschema holen
    color_scheme = self.config.color_schemes.get(
        self.current_color_scheme,
        self.config.color_schemes['TUBAF']
    )

    # Auf Datasets anwenden
    for idx, dataset in enumerate(visible_datasets):
        color = color_scheme[idx % len(color_scheme)]
        dataset.color = color
```

#### Gruppenspezifisches Farbschema (v5.4)

Jede Gruppe kann eigenes Schema haben:

```python
# Priorität: Gruppen-Schema > Globales Schema
for group in self.groups:
    if group.color_scheme:
        # Verwende Gruppen-Schema
        colors = self.config.color_schemes[group.color_scheme]
    else:
        # Verwende globales Schema
        colors = self.config.color_schemes[self.current_color_scheme]

    # Wende auf Datasets in Gruppe an
    for idx, dataset in enumerate(group.datasets):
        dataset.color = colors[idx % len(colors)]
```

**Ändern über Kontextmenü**:
- Rechtsklick auf Gruppe
- "Farbpalette wählen"
- Auswahl aus allen verfügbaren Paletten

### Stack-Faktoren

**Nicht-kumulativ**: Jede Gruppe hat eigenen Multiplikator.

```python
# Beispiel
Gruppe A: stack_factor = 1     → y_plot = y_original × 1
Gruppe B: stack_factor = 10    → y_plot = y_original × 10
Gruppe C: stack_factor = 100   → y_plot = y_original × 100
```

**Auto-Gruppierung (v5.6)**:
```python
# Erstellt Gruppen mit automatischen Zehnerpotenzen
for idx, dataset in enumerate(selected_datasets):
    stack_factor = 10.0 ** idx  # 10^0, 10^1, 10^2, ...
    group = DataGroup(dataset.name, stack_factor)
```

---

## Erweiterungen entwickeln

### Neuen Plot-Typ hinzufügen

**1. Plot-Typ in Dropdown hinzufügen**:
```python
# In scatter_plot.py → create_controls()
self.plot_type_combo.addItem("Mein Plot-Typ")
```

**2. Transformations-Logik implementieren**:
```python
# In scatter_plot.py → update_plot()
elif self.plot_type == "Mein Plot-Typ":
    x_plot = transform_x(x)
    y_plot = transform_y(y)
    xlabel = 'Meine X-Achse'
    ylabel = 'Meine Y-Achse'
    ax.set_xscale('linear')  # oder 'log'
    ax.set_yscale('linear')  # oder 'log'
```

### Neue Farbpalette hinzufügen

**1. In UserConfig eintragen**:
```python
# In user_config.py → __init__()
self.color_schemes['Meine Palette'] = [
    '#FF0000',  # Rot
    '#00FF00',  # Grün
    '#0000FF',  # Blau
    # ...
]
```

**2. Persistent machen**:
```python
# Über GUI: Design-Manager → Farbschema-Manager
# Oder direkt in ~/.tubaf_scatter_plots/config.json
```

### Neuen Dialog hinzufügen

**1. Dialog-Klasse erstellen**:
```python
# In dialogs/my_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mein Dialog")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        # Widgets hinzufügen
        self.setLayout(layout)
```

**2. In Hauptanwendung einbinden**:
```python
# In scatter_plot.py
from dialogs.my_dialog import MyDialog

def show_my_dialog(self):
    dialog = MyDialog(self)
    if dialog.exec():
        # Änderungen übernehmen
        pass
```

**3. Menü-Eintrag hinzufügen**:
```python
# In scatter_plot.py → create_menu_bar()
my_action = QAction("Mein Dialog...", self)
my_action.triggered.connect(self.show_my_dialog)
edit_menu.addAction(my_action)
```

---

## Testing

### Manuelle Tests

**Test-Checklist für neue Features**:

1. **Daten laden**
   - [ ] Einzelne Datei laden
   - [ ] Multiple Dateien laden
   - [ ] Fehlerhafte Datei laden (Fehlerbehandlung)

2. **Gruppierung**
   - [ ] Manuelle Gruppe erstellen
   - [ ] Auto-Gruppierung
   - [ ] Drag & Drop zwischen Gruppen
   - [ ] Stack-Faktoren ändern

3. **Farbschemata**
   - [ ] Globales Schema ändern
   - [ ] Gruppenspezifisches Schema setzen
   - [ ] Eigene Palette erstellen

4. **Plot-Typen**
   - [ ] Alle Plot-Typen durchgehen
   - [ ] Mit/ohne Fehlerbalken
   - [ ] Mit/ohne Stack-Faktoren

5. **Export**
   - [ ] PNG Export
   - [ ] SVG Export
   - [ ] PDF Export
   - [ ] Verschiedene DPI-Werte

6. **Sessions**
   - [ ] Session speichern
   - [ ] Session laden
   - [ ] Session mit Annotations/Referenzlinien

7. **Standard-Einstellungen (v5.4)**
   - [ ] Als Standard speichern
   - [ ] Programm neu starten
   - [ ] Prüfen ob Einstellungen geladen

8. **Logging (v5.6)**
   - [ ] Console-Output prüfen (INFO+)
   - [ ] Log-Datei prüfen (DEBUG+)
   - [ ] Fehler-Logging testen

### Unit Tests (empfohlen)

```python
# tests/test_models.py
import pytest
from core.models import DataSet, DataGroup

def test_dataset_creation():
    ds = DataSet('test_data.dat')
    assert ds.name == 'test_data'
    assert ds.x is not None
    assert ds.y is not None

def test_group_stack_factor():
    group = DataGroup('Test', stack_factor=10.0)
    assert group.stack_factor == 10.0

def test_auto_style():
    ds_fit = DataSet('my_fit.dat')
    assert ds_fit.line_style == '-'

    ds_measure = DataSet('measurement.dat')
    assert ds_measure.marker_style == 'o'
```

### Integration Tests

```python
# tests/test_integration.py
def test_load_and_plot():
    app = ScatterPlotApp()
    app.load_data_from_files(['test1.dat', 'test2.dat'])
    app.update_plot()
    assert len(app.datasets) == 2

def test_session_roundtrip():
    app = ScatterPlotApp()
    app.load_data_from_files(['test.dat'])
    app.save_session('test.tsp')

    app2 = ScatterPlotApp()
    app2.load_session('test.tsp')
    assert len(app2.datasets) == 1
```

---

## Troubleshooting

### Häufige Probleme

#### Problem: Plot wird nicht aktualisiert

**Symptome**: Änderungen an Einstellungen werden nicht angezeigt

**Lösung**:
1. Prüfen ob `update_plot()` aufgerufen wird
2. Console-Log prüfen auf Fehler
3. Log-Datei prüfen: `~/.tubaf_scatter_plots/logs/scatterplot_YYYYMMDD.log`

```python
# Debug-Code einfügen
logger.debug(f"update_plot() aufgerufen: {len(self.datasets)} datasets")
```

#### Problem: Standard-Einstellungen werden nicht geladen

**Symptome**: Gespeicherte Standard-Einstellungen verschwinden nach Neustart

**Diagnose**:
```bash
# Config-Datei prüfen
cat ~/.tubaf_scatter_plots/config.json | grep -A 10 "default_plot_settings"

# Log-Datei prüfen
grep "Standard-Einstellungen" ~/.tubaf_scatter_plots/logs/scatterplot_*.log
```

**Mögliche Ursachen**:
- config.json beschädigt
- Keine Schreibrechte
- `save_default_plot_settings()` nicht aufgerufen

**Lösung**:
1. Log-Dateien prüfen auf Fehler
2. config.json manuell prüfen
3. Gegebenenfalls Verzeichnis neu erstellen

#### Problem: Daten können nicht geladen werden

**Symptome**: "Fehler beim Laden" Meldung

**Diagnose**:
```python
# In data_loader.py Debug-Output hinzufügen
logger.debug(f"Lade Datei: {filepath}")
logger.debug(f"Erste Zeile: {first_line}")
logger.debug(f"Daten-Shape: {data.shape}")
```

**Mögliche Ursachen**:
- Ungültiges Dateiformat
- Nicht-numerische Daten
- Falsche Trennzeichen

**Lösung**:
1. Datei manuell in Texteditor öffnen
2. Format prüfen (Kommentare mit #, Whitespace-getrennt)
3. Beispiel-Datei als Referenz verwenden

#### Problem: Auto-Gruppierung funktioniert nicht

**Symptome**: Keine Gruppen werden erstellt

**Diagnose**:
```bash
# Log-Datei prüfen
grep "Auto-Gruppierung" ~/.tubaf_scatter_plots/logs/scatterplot_*.log
```

**Mögliche Ursachen**:
- Keine Datasets ausgewählt
- Datasets bereits in Gruppen

**Lösung**:
1. Datasets aus Gruppen entfernen
2. In "Nicht zugeordnet" auswählen (Strg+Click)
3. "🔢 Auto-Gruppieren" klicken
4. Log prüfen auf Fehler

#### Problem: Farben werden nicht angewendet

**Symptome**: Alle Kurven haben gleiche Farbe

**Diagnose**:
```python
# In update_plot() Debug-Code
for dataset in visible_datasets:
    logger.debug(f"Dataset {dataset.name}: color={dataset.color}")
```

**Mögliche Ursachen**:
- Farbpalette leer
- Gruppenspezifische Palette überschreibt global
- color_scheme nicht gesetzt

**Lösung**:
1. Farbschema in Dropdown prüfen
2. Gruppenspezifische Paletten zurücksetzen (global anwenden)
3. Log-Dateien prüfen

#### Problem: Export schlägt fehl

**Symptome**: Fehler beim Speichern der Datei

**Mögliche Ursachen**:
- Keine Schreibrechte
- Ungültiger Dateiname
- Zu große Dateigröße (sehr hohe DPI)

**Lösung**:
1. Verzeichnis-Rechte prüfen
2. DPI reduzieren (z.B. 300 statt 600)
3. Anderes Format versuchen (SVG statt PNG)

### Debug-Tipps

**1. Logging aktivieren**:
```python
# In scatter_plot.py
from utils.logger import setup_logger
logger = setup_logger('ScatterForge', level=logging.DEBUG)
```

**2. Log-Dateien lesen**:
```bash
# Heutiges Log anzeigen
tail -f ~/.tubaf_scatter_plots/logs/scatterplot_$(date +%Y%m%d).log

# Nach Fehler suchen
grep ERROR ~/.tubaf_scatter_plots/logs/scatterplot_*.log

# Nach Aktion suchen
grep "Auto-Gruppierung" ~/.tubaf_scatter_plots/logs/scatterplot_*.log
```

**3. Python Debugger verwenden**:
```python
# Breakpoint setzen
import pdb; pdb.set_trace()

# Oder mit neuem Python
breakpoint()
```

**4. Qt Debug-Output**:
```bash
# Mit Debug-Output starten
QT_DEBUG_PLUGINS=1 python scatter_plot.py
```

---

## Performance-Optimierung

### Große Datasets

**Problem**: Langsames Rendering bei >10.000 Datenpunkten

**Lösungen**:
1. **Downsampling**:
```python
def downsample(x, y, max_points=5000):
    if len(x) > max_points:
        step = len(x) // max_points
        return x[::step], y[::step]
    return x, y
```

2. **Rasterization**:
```python
# In update_plot()
ax.plot(..., rasterized=True)
```

3. **Reduced Marker Size**:
```python
dataset.marker_size = 2  # Statt 4
```

### Viele Datasets

**Problem**: Langsame UI bei >50 Datasets

**Lösungen**:
1. **Lazy Loading**: Lade Daten erst beim Anzeigen
2. **Virtual Scrolling**: Nur sichtbare Items rendern
3. **Caching**: Plot-Daten cachen

---

## Anhang

### Keyboard Shortcuts

| Shortcut | Aktion |
|----------|--------|
| Strg+O | Daten laden |
| Strg+S | Session speichern |
| Strg+Shift+S | Session speichern als... |
| Strg+E | Export-Dialog |
| Strg+Q | Beenden |
| Entf | Ausgewählte Items löschen |

### Matplotlib Style Strings

**Linien-Stile**:
- `-`: Durchgezogen
- `--`: Gestrichelt
- `-.`: Strich-Punkt
- `:`: Gepunktet

**Marker**:
- `o`: Kreis
- `s`: Quadrat
- `^`: Dreieck oben
- `v`: Dreieck unten
- `D`: Diamant
- `*`: Stern
- `+`: Plus
- `x`: Kreuz

### Farbpaletten

**Vordefiniert**:
- TUBAF: TUBAF-Farben
- viridis, plasma, inferno, magma: Perceptually Uniform
- tab10, tab20: Kategorisch
- rainbow, jet: Spektral (nicht empfohlen)

**Benutzerdefiniert**:
Über Design-Manager → Farbschema-Manager erstellen

### Git-Repository

**GitHub**: https://github.com/traianuschem/ScatteringPlot

**Branches**:
- `main`: Stable releases
- `develop`: Development branch
- `feature/*`: Feature branches

**Tags**:
- `v5.6`: Current release
- `v5.3`, `v5.2`, etc.: Previous versions

---

## Änderungshistorie dieser Dokumentation

| Version | Datum | Änderungen |
|---------|-------|------------|
| 5.6 | 2025-01-09 | Initiale Dokumentation für v5.6 Release |

---

**Made with ❤️ for the scientific community**

**Fragen oder Probleme?** → [GitHub Issues](https://github.com/traianuschem/ScatteringPlot/issues)
