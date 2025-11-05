# TUBAF Scattering Plot Tool v3.0

Professionelles Python-Tool für Streudaten-Analyse mit erweiterter Funktionalität.

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
- **Kontextmenü**: Rechtsklick für schnellen Zugriff

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

### Export & Session
- **PNG Export**: Mit DPI-Einstellung (72-1200), Wert wird gespeichert
- **SVG Export**: Vektorgrafik für Publikationen
- **Session speichern/laden**: Komplette Arbeitsumgebung inkl. Plot-Typ

## Installation

1. **Repository klonen oder herunterladen**

2. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

Benötigte Pakete:
- numpy
- matplotlib

## Verwendung

### Programm starten

```bash
python scatter_plot.py
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
   - **Doppelklick** Gruppe → Stack-Faktor
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

Unterstützte Trennzeichen:
- Tab (`\t`)
- Komma (`,`)
- Semikolon (`;`)
- Leerzeichen

Kommentarzeilen (beginnend mit `#` oder `%`) werden automatisch übersprungen.

## Beispieldaten erstellen

Um Beispieldaten zu generieren:

```bash
python data_loader.py
```

Dies erstellt einen Ordner `example_data/` mit Testdateien.

## TUBAF Farbpalette anpassen

Die TUBAF-Farben können in der Datei `config.py` angepasst werden:

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
- Session speichern (.json)
- Session laden
- Exportieren als PNG (mit DPI-Auswahl)
- Exportieren als SVG
- Beenden

### Plot
- Aktualisieren
- Einstellungen (erweiterte Optionen)

### Hilfe
- Über

## Struktur

```
ScatteringPlot/
├── scatter_plot.py          # Hauptprogramm mit GUI (Version 2.0)
├── data_loader.py           # Datenlade-Funktionen
├── config.py                # Konfiguration (veraltet)
├── tu_freiberg_colors.py    # Offizielle TUBAF Farbpalette
├── tubaf_colors.py          # Alternative Farbdefinitionen
├── requirements.txt         # Python-Abhängigkeiten
├── README.md               # Diese Datei
└── example_data/           # Beispieldaten
    ├── messung1.dat
    ├── messung2.dat
    └── fit1.csv
```

## Lizenz

Siehe LICENSE-Datei im Repository.

## Kontakt

TU Bergakademie Freiberg
