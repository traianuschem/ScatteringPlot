# TUBAF Scattering Plot Tool v5.0

Professionelles Python-Tool für Streudaten-Analyse mit moderner Qt6-basierter GUI und modularer Architektur.

## Was ist neu in Version 5.0?

### Große Refaktorierung - Modulare Architektur
Version 5.0 bringt eine komplette Umstrukturierung der Code-Basis für bessere Wartbarkeit und Erweiterbarkeit:

- **Modularisierung**: Hauptprogramm von 1583 auf 799 Zeilen reduziert (50% Reduktion)
- **Klare Separation**: Code in spezialisierte Module aufgeteilt
  - `core/` - Datenmodelle und Konstanten
  - `dialogs/` - Alle Dialog-Fenster
  - `utils/` - Hilfsfunktionen
  - `config/` - Konfigurationsdaten
- **Vorbereitet für Zukunft**: Basis für kommende Features (Undo/Redo, Internationalisierung, etc.)
- **Repository-Cleanup**: Alte Backup-Dateien entfernt, saubere Struktur

### Technische Verbesserungen
- Qt6 (PySide6) basierte GUI für moderne, responsive Benutzeroberfläche
- Permanenter Dark Mode für angenehmes Arbeiten
- Verbesserte Code-Organisation und Lesbarkeit
- Optimierte Import-Struktur

## Features

### Plot-Typen
- **Log-Log**: Klassische doppelt-logarithmische Darstellung
- **Porod-Plot**: I·q⁴ vs q für Porod-Analyse
- **Kratky-Plot**: I·q² vs q für strukturelle Charakterisierung
- **Guinier-Plot**: ln(I) vs q² für Radius of Gyration
- **PDDF-Modus**: Mit separatem Subplot für Pair Distance Distribution Function

### Datenverwaltung
- **"Nicht zugeordnet" Sektion**: Dateien erst laden, dann per Drag & Drop zuordnen
- **Drag & Drop**: Intuitive Datensatz-Organisation zwischen Gruppen
- **Flexible Datenformate**: Automatische Erkennung (Tab, Komma, Semikolon)
- **Gruppenverwaltung**: Mit individuellen Stack-Faktoren für gestackte Darstellung
- **Kontextmenü**: Rechtsklick für schnellen Zugriff auf alle Funktionen

### Stil-System
- **Stil-Vorlagen**: Vordefinierte Stile (Messung, Fit, Simulation, Theorie)
- **Auto-Erkennung**: Automatische Stil-Zuweisung basierend auf Dateinamen
- **Design-Manager**: Zentrale Verwaltung von Stilen, Farben und Auto-Regeln
- **Individuelle Anpassung**: Linientyp, Marker, Größen pro Datensatz
- **Farbschema-Manager**: TUBAF + alle matplotlib colormaps + eigene Schemata

### Visualisierung
- **Gruppen-Header in Legende**: Klare Struktur mit Stack-Faktoren
- **Individuelle Legendeneinträge**: Jeder Datensatz separat sichtbar
- **Fehlervisualisierung**: Transparente Flächen um Daten
- **Achsenbereiche**: Manuell oder automatisch einstellbar
- **Legende-Position**: Frei wählbar
- **4K Display-Unterstützung**: DPI-Awareness für scharfe Darstellung
- **Dark Mode**: Permanenter Dark Mode für angenehme Darstellung

### Export & Session
- **PNG Export**: Mit DPI-Einstellung (72-1200), Wert wird gespeichert
- **SVG Export**: Vektorgrafik für Publikationen
- **Session speichern/laden**: Komplette Arbeitsumgebung inkl. Plot-Typ

## Installation

### Voraussetzungen
- Python 3.8 oder höher
- PySide6 (Qt6 für Python)
- NumPy
- Matplotlib

### Schritt-für-Schritt Installation

1. **Repository klonen oder herunterladen**
```bash
git clone <repository-url>
cd ScatteringPlot
```

2. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

Oder manuell:
```bash
pip install PySide6 numpy matplotlib
```

### Benötigte Pakete:
- **PySide6** (≥6.0): Qt6 GUI-Framework
- **numpy**: Numerische Berechnungen
- **matplotlib**: Plot-Funktionalität

## Verwendung

### Programm starten

```bash
python scatter_plot.py
```

Oder direkt ausführbar (Linux/Mac):
```bash
./scatter_plot.py
```

### Workflow

1. **Daten laden (vereinfacht!)**
   - Klicken Sie auf "📁 Laden" oder Menü → Datei → Daten laden
   - Dateien werden in "Nicht zugeordnet" abgelegt
   - **Auto-Stil-Erkennung** wendet passende Stile an

2. **Gruppen erstellen**
   - Klicken Sie auf "➕ Gruppe"
   - Namen und Stack-Faktor eingeben (z.B. "Probe A", Faktor 1)

3. **Drag & Drop zuordnen**
   - Ziehen Sie Dateien aus "Nicht zugeordnet" auf Gruppen
   - Verschieben Sie zwischen Gruppen
   - Zurück zu "Nicht zugeordnet" möglich

4. **Plot-Typ wählen**
   - Dropdown: Log-Log, Porod, Kratky, Guinier, PDDF
   - Achsenbeschriftung passt sich automatisch an

5. **Farbschema wählen**
   - Dropdown: TUBAF, viridis, tab10, Set1, ... (über 30 Schemata!)
   - Oder eigenes Schema im Design-Manager erstellen

6. **Anpassungen**
   - **Rechtsklick** → Farbe/Stil ändern, Umbenennen
   - **Doppelklick** Gruppe → Stack-Faktor bearbeiten
   - **Doppelklick** "Nicht zugeordnet" → Ein-/Ausklappen
   - Menü → Design → Stil anwenden (Messung/Fit/etc.)

7. **Erweiterte Einstellungen**
   - Plot → Erweiterte Einstellungen
     - Achsenbereiche (Min/Max oder Auto)
     - Legende-Position
     - Schriftgrößen
   - Design → Design-Manager
     - Stil-Vorlagen verwalten
     - Farbschemata erstellen
     - Auto-Erkennungs-Regeln anpassen

8. **Speichern**
   - Session speichern (JSON) → Alles inkl. Plot-Typ
   - PNG Export (mit DPI-Merken)
   - SVG Export

### Datenformat

Die Datendateien sollten folgendes Format haben:

**2 Spalten** (x, y):
```
# Kommentarzeilen beginnen mit #
0.1    100.5
0.2    85.3
0.3    72.1
...
```

**3 Spalten** (x, y, y_err):
```
# q [nm^-1]    Intensität [a.u.]    Fehler [a.u.]
0.1    100.5    5.2
0.2    85.3     4.8
0.3    72.1     3.9
...
```

**Unterstützte Trennzeichen:**
- Tab (`\t`)
- Komma (`,`)
- Semikolon (`;`)
- Leerzeichen

Kommentarzeilen (beginnend mit `#` oder `%`) werden automatisch übersprungen.

## Beispieldaten erstellen

Um Beispieldaten zu generieren:

```bash
python utils/data_loader.py
```

Dies erstellt einen Ordner `example_data/` mit Testdateien.

## TUBAF Farbpalette anpassen

Die TUBAF-Farben können in der Datei `config/tu_freiberg_colors.py` angepasst werden:

```python
TUBAF_COLORS = [
    '#003A5D',  # TUBAF Dunkelblau
    '#0088CC',  # TUBAF Hellblau
    # ... weitere Farben
]
```

Die offiziellen Farben finden Sie unter:
https://tu-freiberg.de/zuv/d5/corporate-design/farbdefinition

## Beispiel-Workflow

1. Gruppe "Probe A - Messung" mit Stack-Faktor 1 erstellen
2. Messdaten (mit Fehlern) laden
3. Gruppe "Probe A - Fit" mit Stack-Faktor 1 erstellen
4. Fit-Daten laden
5. Gruppe "Probe B - Messung" mit Stack-Faktor 10 erstellen
6. Weitere Messdaten laden
7. Plot aktualisieren

Resultat: Alle Gruppen werden im selben Log-Log-Plot dargestellt, wobei Probe B um Faktor 10 vertikal verschoben ist.

## Shortcuts und Tastenkombinationen

- **Doppelklick** auf Gruppe: Stack-Faktor bearbeiten
- **Doppelklick** auf Datensatz: Umbenennen
- **Rechtsklick**: Kontextmenü öffnen
- **Drag & Drop**: Datensätze zwischen Gruppen verschieben
- **Matplotlib-Toolbar**: Zoom, Pan, Home, Back, Forward, Save

## Menü-Übersicht

### Datei
- Daten laden
- Session speichern (.json)
- Session laden
- Exportieren als PNG (mit DPI-Auswahl)
- Exportieren als SVG
- Beenden

### Plot
- Aktualisieren
- Erweiterte Einstellungen (Achsenlimits, Legende-Position)

### Design
- Stil anwenden → Messung / Fit / Simulation / Theorie
- Farbschema → TUBAF + matplotlib colormaps
- Design-Manager (Stil-Vorlagen, Farbschemata, Auto-Regeln)

### Hilfe
- Über

## Projekt-Struktur

Version 5.0 verwendet eine modulare Architektur für bessere Wartbarkeit:

```
ScatteringPlot/
├── scatter_plot.py              # Hauptprogramm und GUI (799 Zeilen)
│
├── core/                        # Kern-Module
│   ├── __init__.py
│   ├── models.py               # DataSet und DataGroup Klassen
│   └── constants.py            # PLOT_TYPES und andere Konstanten
│
├── dialogs/                     # Dialog-Fenster
│   ├── __init__.py
│   ├── settings_dialog.py      # Plot-Einstellungen (Achsenlimits)
│   ├── group_dialog.py         # Gruppe erstellen Dialog
│   └── design_manager.py       # Design-Manager (Stile, Farben, Regeln)
│
├── utils/                       # Hilfsfunktionen
│   ├── __init__.py
│   ├── data_loader.py          # Daten laden und Beispieldaten erstellen
│   └── user_config.py          # Benutzer-Konfiguration verwalten
│
├── config/                      # Konfigurationsdaten
│   ├── __init__.py
│   └── tu_freiberg_colors.py   # TUBAF Farbdefinitionen
│
├── features/                    # Zukünftige erweiterte Features
│   └── __init__.py             # (Undo/Redo, Annotationen, etc.)
│
├── i18n/                        # Zukünftige Internationalisierung
│   └── __init__.py             # (Deutsch, Englisch)
│
├── ui/                          # Zukünftige Custom UI-Komponenten
│   └── __init__.py
│
├── requirements.txt             # Python-Abhängigkeiten
├── README.md                    # Diese Datei
├── .user_config.json           # Benutzer-Einstellungen (automatisch erstellt)
└── example_data/               # Beispieldaten (optional)
    ├── messung1.dat
    ├── messung2.dat
    └── fit1.csv
```

### Architektur-Prinzipien

**Separation of Concerns:**
- `core/` - Reine Datenmodelle ohne GUI-Logik
- `dialogs/` - Alle Dialog-Fenster zentral organisiert
- `utils/` - Wiederverwendbare Hilfsfunktionen
- `config/` - Konfigurationsdaten getrennt vom Code

**Vorteile der modularen Struktur:**
- Einfachere Wartung und Fehlersuche
- Klare Verantwortlichkeiten jedes Moduls
- Bessere Testbarkeit
- Vorbereitung für zukünftige Features
- Reduzierte Code-Duplikation

## Migration von Version 4.2

Version 5.0 ist vollständig rückwärtskompatibel:
- Session-Dateien (.json) aus v4.2 funktionieren weiterhin
- Keine Änderungen an Datenformaten
- Alle Features aus v4.2 sind erhalten
- Benutzer-Konfiguration wird automatisch migriert

## Entwicklung und Erweiterung

### Code-Struktur

**Hauptklassen:**
- `ScatterPlotApp` (scatter_plot.py): Haupt-GUI-Anwendung
- `DataSet` (core/models.py): Einzelner Datensatz mit Stil
- `DataGroup` (core/models.py): Gruppe von Datensätzen mit Stack-Faktor
- `PlotSettingsDialog` (dialogs/settings_dialog.py): Achsenlimits-Dialog
- `DesignManagerDialog` (dialogs/design_manager.py): Stil- und Farbverwaltung

### Neue Features hinzufügen

Für neue Features verwenden Sie die vorbereiteten Ordner:
- `features/` - Komplexe neue Funktionen (z.B. Undo/Redo-System)
- `dialogs/` - Neue Dialog-Fenster
- `utils/` - Neue Hilfsfunktionen

### Geplante Features (zukünftige Versionen)

Version 5.x wird erweitert um:
- Undo/Redo-Funktion
- Umfassende Grid-Einstellungen (Typ, Dicke, Farbe, Major/Minor)
- Font-Anpassung für Achsen, Legende, Titel
- Verbesserter Drag & Drop mit Multi-Select
- Erweiterte Export-Optionen (transparenter Hintergrund)
- Daten-Extraktion mit Markern und Referenzlinien
- Textfelder in Plots
- Umfassende Legenden-Einstellungen
- Englische Sprachunterstützung (i18n)

## Technische Details

**Framework:** PySide6 (Qt6 für Python)
**Plot-Engine:** Matplotlib mit QtAgg Backend
**Python-Version:** 3.8+
**Architektur:** Modulares Design mit klarer Separation

## Fehlerbehebung

### Programm startet nicht
- Prüfen Sie, ob alle Abhängigkeiten installiert sind: `pip list | grep -E "PySide6|numpy|matplotlib"`
- Verwenden Sie Python 3.8 oder höher: `python --version`

### Daten werden nicht geladen
- Prüfen Sie das Datenformat (siehe Abschnitt "Datenformat")
- Stellen Sie sicher, dass Kommentarzeilen mit `#` oder `%` beginnen
- Prüfen Sie die Konsole auf Fehlermeldungen

### Plot zeigt nichts an
- Klicken Sie auf "🔄 Aktualisieren" oder Menü → Plot → Aktualisieren
- Prüfen Sie, ob Datensätze Gruppen zugeordnet sind
- Prüfen Sie die Achsenlimits (Plot → Erweiterte Einstellungen)

## Lizenz

Siehe LICENSE-Datei im Repository.

## Kontakt

TU Bergakademie Freiberg
Institut für Experimentelle Physik

---

**Version:** 5.0
**Letzte Aktualisierung:** November 2025
**Framework:** PySide6 (Qt6)
