# ScatterForge Plot v6.1

**Professionelles Tool für Streudaten-Analyse mit Qt6-basierter GUI**

ScatterForge Plot ist ein leistungsstarkes, benutzerfreundliches Tool zur Visualisierung und Analyse von Streudaten. Entwickelt für Naturwissenschaftler und Ingenieure, bietet es umfangreiche Funktionen für die Darstellung von SAXS/SANS-Daten und anderen Streumessungen mit präziser Kontrolle über alle Aspekte der Plot-Formatierung.

![Version](https://img.shields.io/badge/version-6.1-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🎉 Neue Features in v6.1

Version 6.1 bringt **umfassende Plot-Formatierung** und **professionelle Kurven-Gestaltung**:

### 🎨 Kurven-Editor
- **Umfassender Dialog** für alle visuellen Eigenschaften jeder Kurve
- **Farbauswahl** mit Farbwähler PLUS Schnellauswahl aus aktueller Palette
- **Marker-Stile**: 13 verschiedene Marker (Kreis, Quadrat, Dreieck, Stern, ...)
- **Linien-Stile**: 5 Stile (durchgezogen, gestrichelt, strich-punkt, gepunktet)
- **Fehlerbalken-Kontrolle**: Vollständige Anpassung aller Parameter

### 📊 Flexible Fehlerbalken-Darstellung
- **Transparente Fläche** (`fill_between`): Ideal für dichte Messpunkte
- **Balken mit Caps** (`errorbar`): Klassische Darstellung für einzelne Punkte
- **Konfigurierbare Parameter**:
  - Transparenz (0-100%)
  - Cap-Größe (nur bei Balken)
  - Linienbreite (nur bei Balken)
- **Standard für Messdaten**: Transparente Fläche mit 30% Transparenz

### ⚡ Schnellfarben-Menü
- **Direkter Zugriff** auf Farben der aktuellen Farbpalette
- **Intelligente Palette-Auswahl**: Berücksichtigt Gruppen-Paletten
- **Kontextmenü-Integration**: Rechtsklick → Schnellfarben → Farbe wählen

### 📐 Erweiterte Plot-Formatierung
- **Individuelle Plotgrenzen** pro Datensatz (X/Y-Min/Max)
- **Erweiterte Achsen-Einstellungen**: Ticks, Labels, Scientific Notation
- **Grid-Anpassung**: Major/Minor Grid mit Unit-Format-Konvertierung
- **Legendeneditor**: Individuelle Formatierung jedes Eintrags

---

## 📋 Hauptfeatures

### Visualisierung
- **5 Plot-Typen**: Log-Log, Porod, Kratky, Guinier, PDDF
- **Stack-Modus**: Kurven mit individuellen Stack-Faktoren trennen (nicht-kumulativ!)
- **Fehlerbalken**: 2 Darstellungsarten (transparente Fläche oder Balken)
- **Annotations & Referenzlinien**: Drag & Drop im Plot
- **Math Text**: LaTeX-Style für wissenschaftliche Notation (z.B. `I·q^2`, `10^{-3}`)

### Kurven-Gestaltung
- **Umfassender Kurven-Editor**: Alle visuellen Eigenschaften in einem Dialog
- **Schnellfarben**: Direkter Zugriff auf Palette-Farben
- **Stil-Vorlagen**: Messung, Fit, Simulation, Theorie mit Auto-Erkennung
- **Marker & Linien**: Vollständige Kontrolle über Darstellung
- **Farben**: 30+ Farbpaletten + eigene Schemata

### Daten-Management
- **Drag & Drop**: Datasets zwischen Gruppen verschieben
- **Gruppen-System**: Datasets organisieren mit individuellen Stack-Faktoren
- **Auto-Gruppierung**: Automatische Gruppenerstellung (10^0, 10^1, 10^2, ...)
- **Session-Verwaltung**: Komplette Projektzustände speichern/laden
- **Individuelle Plotgrenzen**: X/Y-Limits pro Datensatz

### Design & Export
- **Farbschema-Manager**:
  - TUBAF-Farben (Corporate Design)
  - 30+ Matplotlib Colormaps (tab10, viridis, plasma, ...)
  - Eigene Paletten erstellen
  - Gruppenspezifische Paletten
- **Plot-Designs**: 5 vordefinierte + eigene erstellen und als Standard speichern
- **Export-Formate**: PNG, SVG, PDF, EPS
- **16:10 Standard-Format**: 25.4 cm × 15.875 cm (optimal für Publikationen)
- **Hohe Auflösung**: Bis 1200 DPI

### Legenden & Grid
- **Legendeneditor**:
  - Individuelle Formatierung (fett, kursiv)
  - Anpassbare Einträge
  - Position, Spalten, Transparenz
- **Grid-Einstellungen**:
  - Major/Minor Grid separat steuerbar
  - Linienstile und Farben
  - Unit-Format-Konvertierung (nm ↔ Å)

### Einstellungen & Debug
- **Standard-Einstellungen**: Programmweite Defaults speichern
- **Logging-System**: Alle Aktionen werden aufgezeichnet
- **Log-Dateien**: `~/.tubaf_scatter_plots/logs/scatterplot_YYYYMMDD.log`
- **Debug-Level**: Console (INFO+), Datei (DEBUG+)

---

## 🛠️ Installation

### Voraussetzungen
- Python 3.8 oder höher
- PySide6 (Qt6 für Python)
- Matplotlib
- NumPy

### Installation

```bash
# Repository klonen
git clone https://github.com/traianuschem/ScatteringPlot.git
cd ScatteringPlot

# Abhängigkeiten installieren
pip install -r requirements.txt

# Programm starten
python scatter_plot.py
```

### Requirements

```
PySide6>=6.5.0
matplotlib>=3.7.0
numpy>=1.24.0
```

---

## 📖 Schnellstart

### 1. Daten laden

```
1. Klick auf "📁 Laden" oder Datei → Daten laden...
2. Mehrere .dat/.csv/.txt Dateien auswählen
3. Datasets erscheinen in "Nicht zugeordnet"
```

### 2. Kurve formatieren (NEU in v6.1!)

**Umfassender Kurven-Editor:**
```
1. Rechtsklick auf Datensatz → "🎨 Kurve bearbeiten..."
2. Dialog öffnet sich mit allen Einstellungen:
   - Farbe: Farbwähler + Schnellauswahl aus Palette
   - Marker: Stil und Größe
   - Linie: Stil und Breite
   - Fehlerbalken: Darstellung (Fläche/Balken), Transparenz, etc.
3. OK → Plot wird aktualisiert
```

**Schnellfarben (NEU in v6.1!):**
```
1. Rechtsklick auf Datensatz → "Schnellfarben"
2. Farbe aus aktueller Palette wählen
3. Farbe wird sofort angewendet
```

### 3. Gruppen erstellen

**Manuelle Gruppierung:**
```
1. Klick auf "➕ Gruppe"
2. Name und Stack-Faktor eingeben
3. Datasets per Drag & Drop in Gruppe ziehen
```

**Auto-Gruppierung:**
```
1. Datasets in "Nicht zugeordnet" auswählen (Strg+Click)
2. Klick auf "🔢 Auto-Gruppieren"
3. Automatische Gruppenerstellung mit Stack-Faktoren (10^0, 10^1, ...)
```

### 4. Farbpaletten

**Globale Farbpalette:**
```
Dropdown "Farbschema" → Palette auswählen
```

**Gruppenspezifische Farbpalette:**
```
Rechtsklick auf Gruppe → "Farbpalette wählen"
```

### 5. Plot-Formatierung

**Legende anpassen:**
```
Legende → Legende bearbeiten...
- Einträge umbenennen
- Formatierung (fett, kursiv)
- Position, Spalten, Transparenz
```

**Grid einstellen:**
```
Grid → Grid-Einstellungen...
- Major/Minor Grid
- Linienstile und Farben
- Unit-Format (nm ↔ Å)
```

**Achsen anpassen:**
```
Achsen → Achsen-Einstellungen...
- Tick-Parameter
- Labels anpassen
- Scientific Notation
```

### 6. Export

```
1. Datei → Exportieren...
2. Format, DPI, Größe einstellen (Standard: 16:10)
3. Speichern
```

### 7. Standard-Einstellungen speichern

```
1. Plot-Einstellungen nach Wunsch anpassen
2. Design → Design-Manager...
3. Tab "Plot-Designs"
4. "⭐ Als Programmstandard speichern"
5. Beim nächsten Start werden diese Einstellungen geladen
```

---

## 🎨 Plot-Typen

| Typ | X-Achse | Y-Achse | Beschreibung |
|-----|---------|---------|--------------|
| **Log-Log** | q [nm⁻¹] | I [a.u.] | Standard Streukurven (beide Achsen logarithmisch) |
| **Porod** | q [nm⁻¹] | I·q⁴ [a.u.] | Porod-Analyse (Grenzflächenstruktur) |
| **Kratky** | q [nm⁻¹] | I·q² [a.u.] | Kratky-Plot (Kompaktheit) |
| **Guinier** | q² [nm⁻²] | ln(I) | Guinier-Approximation (Trägheitsradius) |
| **PDDF** | q [nm⁻¹] | I [a.u.] + p(r) | Paardistanzverteilungsfunktion |

---

## 📐 Kurven-Editor (v6.1)

Der neue umfassende Kurven-Editor bietet vollständige Kontrolle über alle visuellen Eigenschaften:

### Farbe
- **Farbwähler**: Beliebige RGB-Farbe auswählen
- **Schnellauswahl**: Farben aus aktueller Farbpalette
  - Zeigt automatisch die aktive Palette (global oder Gruppe)
  - Bis zu 10 Farben als Schnellauswahl
- **Farbe zurücksetzen**: Automatische Farbzuweisung

### Marker
- **Stile**: Kreis (o), Quadrat (s), Dreieck (^,v,<,>), Raute (D), Stern (*), Plus (+), Kreuz (x), Punkt (.), Pixel (,)
- **Größe**: 0-20 pt (Standard: 4)
- **Kein Marker**: Nur Linie anzeigen

### Linie
- **Stile**: Durchgezogen (-), Gestrichelt (--), Strich-Punkt (-.), Gepunktet (:), Keine Linie
- **Breite**: 0-10 pt (Standard: 2)

### Fehlerbalken (v6.1)
- **Darstellung**:
  - **Transparente Fläche** (`fill_between`): Beste Darstellung für dichte Datenpunkte
  - **Balken mit Caps** (`errorbar`): Klassische Darstellung mit konfigurierbaren Endkappen
- **Transparenz**: 0-100% (Standard: 30% für Flächen)
- **Cap-Größe**: 0-10 pt (nur bei Balken, Standard: 3)
- **Linienbreite**: 0.1-5 pt (nur bei Balken, Standard: 1.0)

**Standard für Messdaten**: Transparente Fläche mit 30% Transparenz

---

## 🎯 Fehlerbalken-Darstellung (v6.1)

### Transparente Fläche (`fill`)

**Vorteile:**
- Übersichtlich bei vielen Datenpunkten
- Zeigt Fehlerbereich als zusammenhängende Fläche
- Ideal für Messkurven mit kleinen Fehlerbalken

**Anwendung:**
```
Rechtsklick → Kurve bearbeiten → Fehlerbalken
→ Darstellung: "Transparente Fläche"
→ Transparenz: 0.3 (30%)
```

**Wird verwendet für Stil:**
- "Messung" (Standard)

### Balken mit Caps (`bars`)

**Vorteile:**
- Klassische wissenschaftliche Darstellung
- Gut für wenige, weit auseinander liegende Punkte
- Zeigt exakte Fehlerbalken-Länge

**Anwendung:**
```
Rechtsklick → Kurve bearbeiten → Fehlerbalken
→ Darstellung: "Balken mit Caps"
→ Cap-Größe: 3 pt
→ Linienbreite: 1.0 pt
```

**Wird verwendet für Stile:**
- "Fit", "Simulation", "Theorie"

---

## 🗂️ Dateiformat

Unterstützte Formate: `.dat`, `.txt`, `.csv`

### Beispiel (2 Spalten):
```
# q / nm^-1    I / a.u.
0.1            1000.5
0.2            856.3
0.3            723.1
```

### Beispiel (3 Spalten mit Fehler):
```
# q / nm^-1    I / a.u.    I_err
0.1            1000.5      15.2
0.2            856.3       12.8
0.3            723.1       10.5
```

**Hinweise:**
- Spalten durch Whitespace (Leerzeichen oder Tab) getrennt
- Kommentare mit `#`
- Dezimaltrennzeichen: Punkt (`.`)
- Fehler in 3. Spalte sind optional

---

## ⚙️ Konfiguration

Alle Einstellungen werden gespeichert in: `~/.tubaf_scatter_plots/`

### Dateien

| Datei | Inhalt |
|-------|--------|
| `config.json` | Hauptkonfiguration, Standard-Plot-Einstellungen |
| `color_schemes.json` | Benutzerdefinierte Farbpaletten |
| `style_presets.json` | Benutzerdefinierte Stil-Vorlagen |
| `logs/` | Tägliche Log-Dateien |

### Standard-Einstellungen

**Programmweite Defaults speichern:**
1. Plot nach Wunsch einstellen (Legende, Grid, Fonts, ...)
2. Design → Design-Manager...
3. "⭐ Als Programmstandard speichern"

**Beim nächsten Start werden geladen:**
- Legenden-Einstellungen
- Grid-Einstellungen
- Font-Einstellungen
- Aktives Plot-Design

---

## 🔧 Erweiterte Funktionen

### Auto-Stil-Erkennung

Datasets werden automatisch basierend auf Dateinamen gestylt:

| Keyword im Dateinamen | Stil | Eigenschaften |
|----------------------|------|---------------|
| `fit`, `fitted`, `anpassung` | Fit | Durchgezogene Linie, keine Marker |
| `messung`, `measure`, `data` | Messung | Marker (o), transparente Fehlerfläche |
| `sim`, `simulation` | Simulation | Gestrichelte Linie (--) |
| `theo`, `theory`, `theorie` | Theorie | Strich-Punkt (-.) |

**Beispiele:**
- `sample1_messung.dat` → Stil "Messung"
- `fit_result.dat` → Stil "Fit"
- `simulation_001.dat` → Stil "Simulation"

### Gruppen-Stack-Faktoren

**WICHTIG: Nicht-kumulativ!** Jede Gruppe hat einen eigenen Multiplikator:

```
Gruppe A (Stack-Faktor: ×1):     y_plot = y_original × 1
Gruppe B (Stack-Faktor: ×10):    y_plot = y_original × 10
Gruppe C (Stack-Faktor: ×100):   y_plot = y_original × 100
```

**Auto-Gruppierung** erstellt automatisch Faktoren: 10^0, 10^1, 10^2, 10^3, ...

### Individuelle Plotgrenzen (v5.7+)

**Pro Datensatz X/Y-Limits setzen:**
```
Rechtsklick auf Datensatz → "Plotgrenzen setzen..."
→ X-Min, X-Max, Y-Min, Y-Max eingeben
→ Nur Datenpunkte in diesem Bereich werden geplottet
```

**Anwendung:**
- Unerwünschte Bereiche ausblenden
- Auf interessanten Bereich zoomen
- Pro Datensatz individuell

### Legendeneditor (v5.7+)

**Individuelle Formatierung:**
```
Legende → Legende bearbeiten...
→ Einträge umbenennen
→ Formatierung: fett, kursiv
→ Reihenfolge ändern (Drag & Drop im Tree)
```

**Globale Einstellungen:**
```
Legende → Legende-Einstellungen...
→ Position (9 vordefinierte Positionen)
→ Spalten (1-4)
→ Transparenz (0-100%)
→ Rahmen, Schatten
```

### Session-Format

Sessions speichern:
- Alle Datasets mit Pfaden
- Gruppen mit Stack-Faktoren
- Plot-Einstellungen (Legende, Grid, Fonts)
- Annotations & Referenzlinien
- Aktives Plot-Design
- **Kurvenformatierung** (Farben, Marker, Fehlerbalken)
- **Individuelle Plotgrenzen**

**Format**: JSON (`.scatterforge`)

---

## 🐛 Debugging

### Log-Dateien

Alle Aktionen werden geloggt:

```bash
# Log-Verzeichnis öffnen
cd ~/.tubaf_scatter_plots/logs

# Heutiges Log anzeigen
cat scatterplot_$(date +%Y%m%d).log
```

### Log-Levels

```
[14:23:45] INFO     Lade 3 Datei(en)...                    # Wichtige Aktionen
[14:23:45] DEBUG    Geladen: file1.dat (1024 Datenpunkte) # Details
[14:23:46] WARNING  Keine Datasets ausgewählt              # Warnungen
[14:23:47] ERROR    Fehler beim Laden: ...                 # Fehler
```

**Log-Rotation**: Täglich neue Datei, alte Logs bleiben erhalten

---

## 💡 Tipps & Tricks

### Workflow für Publikationen

1. **Daten laden** und nach Wunsch gruppieren
2. **Farben anpassen**: Schnellfarben für konsistente Palette
3. **Fehlerbalken einstellen**: Transparente Fläche (30%) für Messungen
4. **Legende formatieren**: Einträge umbenennen, Formatierung anpassen
5. **Grid & Achsen**: Nach Journal-Vorgaben einstellen
6. **Als Standard speichern**: Design → "Als Programmstandard speichern"
7. **Exportieren**: 16:10 Format, 600 DPI, PDF

### Schnelle Farbänderung

**Innerhalb einer Palette:**
```
Rechtsklick → Schnellfarben → Farbe wählen (sofort angewendet)
```

**Komplett eigene Farbe:**
```
Rechtsklick → Kurve bearbeiten → Farbwähler
```

### Konsistente Formatierung

**Für alle Datasets:**
1. Standard-Stil definieren: Rechtsklick → "Stil anwenden" → "Messung"
2. Oder individuelle Anpassung für besondere Kurven

**Für neue Sessions:**
- Design-Manager → "Als Programmstandard speichern"

---

## 📚 Dokumentation

Weitere Dokumentation:
- [CHANGELOG.md](CHANGELOG.md) - Detaillierte Versionshistorie
- Log-Dateien: `~/.tubaf_scatter_plots/logs/`

---

## 🤝 Mitwirken

Contributions sind willkommen! Bitte:

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Changes committen (`git commit -m 'Add AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request öffnen

---

## 📝 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.

---

## 👥 Autoren

- **TUBAF Team** - *Initial work*
- **Contributors** - [Liste der Contributors](https://github.com/traianuschem/ScatteringPlot/contributors)

---

## 📧 Kontakt

Bei Fragen oder Problemen:
- Issue erstellen: [GitHub Issues](https://github.com/traianuschem/ScatteringPlot/issues)
- Log-Dateien prüfen: `~/.tubaf_scatter_plots/logs/`

---

## 🎓 Zitation

Wenn Sie ScatterForge Plot in Ihrer Forschung verwenden, zitieren Sie bitte:

```bibtex
@software{scatterforge_plot,
  author = {TUBAF Team},
  title = {ScatterForge Plot: Professional Scattering Data Visualization Tool},
  year = {2025},
  version = {6.1},
  url = {https://github.com/traianuschem/ScatteringPlot}
}
```

---

## 🏆 Highlights v6.1

- 🎨 **Umfassender Kurven-Editor** - Alle visuellen Eigenschaften in einem Dialog
- ⚡ **Schnellfarben-Menü** - Direkter Zugriff auf Palette-Farben
- 📊 **Flexible Fehlerbalken** - Transparente Fläche ODER Balken mit Caps
- 📐 **Individuelle Plotgrenzen** - X/Y-Limits pro Datensatz
- 🎯 **Erweiterte Plot-Formatierung** - Achsen, Grid, Legende mit voller Kontrolle
- 💾 **Standard-Einstellungen** - Einmal einstellen, immer verwenden

---

**Made with ❤️ for the scientific community**

*Version 6.1 - Januar 2025*
