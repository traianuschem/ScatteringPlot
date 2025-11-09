# ScatterForge Plot v5.6

**Professionelles Tool für Streudaten-Analyse mit Qt6-basierter GUI**

ScatterForge Plot ist ein leistungsstarkes, benutzerfreundliches Tool zur Visualisierung und Analyse von Streudaten. Entwickelt für wissenschaftliche Anwendungen, bietet es umfangreiche Funktionen für die Darstellung von SAXS/SANS-Daten und anderen Streumessungen.

![Version](https://img.shields.io/badge/version-5.6-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)


---

## 🚀 Neue Features in v5.6

- **Export-Optimierung**: Standard 16:10 Format (25.4 cm × 15.875 cm) für wissenschaftliche Publikationen
- **Gruppenspezifische Farbpaletten**: Jede Gruppe kann eine eigene Farbpalette haben
- **Auto-Gruppierung**: Automatische Gruppenerstellung mit Stack-Faktoren (10^0, 10^1, 10^2, ...)
- **Programmweite Standard-Einstellungen**: Plot-Designs permanent als Standard speichern
- **Umfassendes Logging-System**: Vollständige Nachvollziehbarkeit aller Aktionen

---

## 📋 Features

### Visualisierung
- **Multiple Plot-Typen**: Log-Log, Porod, Kratky, Guinier, PDDF
- **Stack-Modus**: Kurven mit individuellen Stack-Faktoren trennen
- **Fehlerbalken**: Automatische Darstellung von Y-Fehlerbalken
- **Annotations & Referenzlinien**: Texte und Linien im Plot platzieren
- **Math Text**: LaTeX-Style Exponenten und Indizes

### Daten-Management
- **Drag & Drop**: Datasets zwischen Gruppen verschieben
- **Gruppen-System**: Datasets in Gruppen organisieren mit individuellen Stack-Faktoren
- **Auto-Gruppierung**: Ausgewählte Datasets automatisch gruppieren
- **Session-Verwaltung**: Komplette Projektzustände speichern/laden
- **Auto-Stil-Erkennung**: Automatische Zuweisung von Stilen basierend auf Dateinamen

### Design & Export
- **Farbschema-Manager**: TUBAF-Farben, 30+ Matplotlib Colormaps, eigene Paletten
- **Plot-Designs**: 5 vordefinierte Designs + eigene erstellen
- **Stil-Vorlagen**: Messung, Fit, Simulation, Theorie
- **Export-Formate**: PNG, SVG, PDF, EPS mit konfigurierbarer Auflösung
- **16:10 Standard-Format**: Optimal für wissenschaftliche Publikationen

### Einstellungen
- **Legend-Einstellungen**: Position, Schriftgröße, Spalten, Transparenz
- **Grid-Einstellungen**: Major/Minor Grid mit individuellen Stilen
- **Font-Einstellungen**: Komplette Kontrolle über alle Schriftarten
- **Standard-Einstellungen**: Programmweite Defaults für alle neuen Sessions

### Entwicklung & Debug
- **Logging-System**: Alle Aktionen werden in Log-Dateien aufgezeichnet
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

### 2. Gruppen erstellen

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
3. Automatische Gruppenerstellung mit Stack-Faktoren
```

### 3. Farbpaletten

**Globale Farbpalette:**
```
Dropdown "Farbschema" → Palette auswählen
```

**Gruppenspezifische Farbpalette:**
```
Rechtsklick auf Gruppe → "Farbpalette wählen"
```

### 4. Export

```
1. Datei → Exportieren...
2. Format, DPI, Größe einstellen
3. Speichern
```

### 5. Standard-Einstellungen

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
| **Log-Log** | q [nm⁻¹] | I [a.u.] | Standard Streukurven |
| **Porod** | q [nm⁻¹] | I·q⁴ [a.u.] | Porod-Analyse |
| **Kratky** | q [nm⁻¹] | I·q² [a.u.] | Kratky-Plot |
| **Guinier** | q² [nm⁻²] | ln(I) | Guinier-Approximation |
| **PDDF** | q [nm⁻¹] | I [a.u.] + p(r) | Paardistanzverteilungsfunktion |

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

---

## 🔧 Erweiterte Funktionen

### Auto-Stil-Erkennung

Datasets werden automatisch basierend auf Dateinamen gestylt:

| Keyword | Stil | Beschreibung |
|---------|------|--------------|
| `fit` | Durchgezogene Linie | Fit-Kurven |
| `messung`, `measure` | Marker | Messdaten |
| `sim`, `simulation` | Gestrichelte Linie | Simulationen |
| `theo`, `theorie` | Strich-Punkt | Theoretische Kurven |

### Gruppen-Stack-Faktoren

**Nicht-kumulativ!** Jede Gruppe hat einen eigenen Multiplikator:

```
Gruppe A (Stack-Faktor: ×1):    y_plot = y_original × 1
Gruppe B (Stack-Faktor: ×10):   y_plot = y_original × 10
Gruppe C (Stack-Faktor: ×100):  y_plot = y_original × 100
```

### Session-Format

Sessions speichern:
- Alle Datasets mit Pfaden
- Gruppen mit Stack-Faktoren
- Plot-Einstellungen
- Annotations & Referenzlinien
- Aktives Plot-Design

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
[14:23:45] INFO     Lade 3 Datei(en)...          # Wichtige Aktionen
[14:23:45] DEBUG    Geladen: file1.dat (1024 Datenpunkte)  # Details
[14:23:46] WARNING  Keine Datasets ausgewählt    # Warnungen
[14:23:47] ERROR    Fehler beim Laden: ...       # Fehler
```

---

## 📚 Dokumentation

Weitere Dokumentation:
- [CHANGELOG.md](CHANGELOG.md) - Versionshistorie
- [DOCUMENTATION.md](DOCUMENTATION.md) - Ausführliche Dokumentation

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
  version = {5.6},
  url = {https://github.com/traianuschem/ScatteringPlot}
}
```

---

**Made with ❤️ for the scientific community**
