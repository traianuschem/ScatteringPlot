# TUBAF Scattering Plot Tool

Ein Python-basiertes Darstellungsprogramm für Streukurven mit grafischer Benutzeroberfläche.

## Features

### Datenverwaltung
- **Grafische Benutzeroberfläche** mit Tkinter
- **Drag & Drop**: Ziehen Sie Datensätze zwischen Gruppen per Drag & Drop
- **Flexible Datenformate**: Unterstützt Tab-, Komma- und Semikolon-getrennte ASCII-Dateien
- **Gruppenverwaltung**: Organisieren Sie Datensätze in Gruppen (z.B. Messdaten + Fitdaten)
- **Kontextmenü**: Rechtsklick für schnellen Zugriff auf Bearbeitungsfunktionen

### Visualisierung
- **Gestackte Ansicht**: Log-Log-Plots mit vertikalem Stacking mittels Multiplikationsfaktoren
- **Fehlervisualisierung**: Fehler werden als transparente Flächen um die Daten dargestellt
- **TUBAF-Farbpalette**: Offizielle TUBAF Corporate Design Farben
- **Individuelle Anpassung**: Farben, Linientypen und Marker für jeden Datensatz änderbar
- **Individuelle Labels**: Datensätze können umbenannt werden
- **4K Display-Unterstützung**: Scharfe Darstellung auf High-DPI Displays

### Stil-Einstellungen
- **Linientyp**: Durchgezogen, gestrichelt, gepunktet, etc.
- **Marker**: Kreise, Quadrate, Dreiecke, Kreuze, etc.
- **Größen**: Linienbreite und Markergröße anpassbar
- **Grid-Optionen**: Anpassbare Grid-Darstellung

### Export & Session
- **PNG Export**: Mit einstellbarer DPI (72-1200 dpi)
- **SVG Export**: Vektorgrafik für hochwertige Publikationen
- **Session speichern/laden**: Speichern Sie Ihre Arbeit inkl. aller Einstellungen

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

1. **Neue Gruppe erstellen**
   - Klicken Sie auf "➕ Neue Gruppe"
   - Geben Sie einen Namen ein (z.B. "Probe A - Messung")
   - Geben Sie einen Stack-Faktor ein (z.B. 1, 10, 100)

2. **Daten laden**
   - Klicken Sie auf "📁 Daten laden"
   - Wählen Sie Datendateien aus
   - Weisen Sie einer Gruppe zu

3. **Drag & Drop verwenden**
   - Ziehen Sie Datensätze zwischen Gruppen
   - Organisieren Sie Ihre Daten intuitiv

4. **Anpassungen vornehmen**
   - **Rechtsklick** auf Gruppe/Datensatz für Kontextmenü
   - **Farbe ändern**: Individuelle Farben für Gruppen und Datensätze
   - **Stil ändern**: Linientyp, Marker, Größen anpassen
   - **Umbenennen**: Labels für bessere Lesbarkeit ändern
   - **Doppelklick** auf Gruppe: Stack-Faktor ändern
   - **Doppelklick** auf Datensatz: Schnell umbenennen

5. **Plot-Einstellungen**
   - Menü → Plot → Einstellungen
   - X/Y-Achsen Labels anpassen
   - Grid-Optionen einstellen
   - Schriftgrößen ändern

6. **Exportieren**
   - Menü → Datei → Exportieren als PNG (mit DPI-Auswahl)
   - Menü → Datei → Exportieren als SVG

7. **Session speichern**
   - Menü → Datei → Session speichern
   - Alle Einstellungen und Gruppierungen werden gespeichert
   - Später wieder laden mit: Datei → Session laden

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
