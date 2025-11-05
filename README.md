# TUBAF Scattering Plot Tool

Ein Python-basiertes Darstellungsprogramm für Streukurven mit grafischer Benutzeroberfläche.

## Features

- **Grafische Benutzeroberfläche** mit Tkinter
- **Flexible Datenformate**: Unterstützt Tab-, Komma- und Semikolon-getrennte ASCII-Dateien
- **Gruppenverwaltung**: Organisieren Sie Datensätze in Gruppen (z.B. Messdaten + Fitdaten)
- **Gestackte Ansicht**: Log-Log-Plots mit vertikalem Stacking mittels Multiplikationsfaktoren
- **Fehlervisualisierung**: Fehler werden als transparente Flächen um die Daten dargestellt
- **TUBAF-Farbpalette**: Standardmäßige Verwendung der TUBAF Corporate Design Farben

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
   - Klicken Sie auf "Neue Gruppe"
   - Geben Sie einen Namen ein (z.B. "Messung 1")
   - Geben Sie einen Stack-Faktor ein (z.B. 1, 10, 100)

2. **Daten laden**
   - Klicken Sie auf "Daten laden"
   - Wählen Sie die Gruppe aus
   - Wählen Sie eine oder mehrere Datendateien

3. **Plot anpassen**
   - Aktivieren/Deaktivieren Sie den Stack-Modus
   - Passen Sie X- und Y-Label an
   - Doppelklicken Sie auf eine Gruppe, um den Stack-Faktor zu ändern

4. **Plot aktualisieren**
   - Klicken Sie auf "Plot aktualisieren"

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

## Tastenkombinationen

- **Doppelklick** auf Gruppe: Stack-Faktor bearbeiten
- **Matplotlib-Toolbar**: Zoom, Pan, Speichern des Plots

## Struktur

```
ScatteringPlot/
├── scatter_plot.py      # Hauptprogramm mit GUI
├── data_loader.py       # Datenlade-Funktionen
├── config.py            # Konfiguration und Farben
├── requirements.txt     # Python-Abhängigkeiten
└── README.md           # Diese Datei
```

## Lizenz

Siehe LICENSE-Datei im Repository.

## Kontakt

TU Bergakademie Freiberg
