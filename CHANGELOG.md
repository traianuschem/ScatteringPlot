# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [5.6.0] - 2025-01-09

### Neue Features

#### Export-Optimierung
- **16:10 Standard-Format**: Export-Dialog verwendet nun standardmäßig 25.4 cm × 15.875 cm (16:10)
- **Optimiert für Publikationen**: Ideale Größe für wissenschaftliche Veröffentlichungen
- `tight_layout=True` bereits als Standard aktiv für optimale Legend/Axis-Positionierung

#### Gruppenspezifische Farbpaletten
- **Pro-Gruppe Farbpaletten**: Jede Gruppe kann eine eigene Farbpalette haben
- **Kontextmenü**: Rechtsklick auf Gruppe → "Farbpalette wählen"
- **Fallback**: Verwendet globale Farbpalette wenn nicht gesetzt
- **Alle Paletten verfügbar**: TUBAF, Matplotlib Colormaps, User-definierte Paletten
- **Persistierung**: Wird in Sessions gespeichert

#### Auto-Gruppierung überarbeitet
- **NEU**: Erstellt für jedes ausgewählte Dataset eine eigene Gruppe
- **Automatische Stack-Faktoren**: 10^0, 10^1, 10^2, ... (Zehnerpotenzen)
- **Gruppen-Name**: Dataset-Name wird als Gruppen-Name verwendet
- **Optimale Trennung**: Perfekt für Log-Log-Plots
- **Anpassbar**: Stack-Faktoren können nachträglich per Doppelklick geändert werden

#### Programmweite Standard-Plot-Einstellungen
- **Persistente Defaults**: Plot-Einstellungen permanent als Standard speichern
- **Button**: "⭐ Als Programmstandard speichern" im Design-Manager
- **Auto-Load**: Beim nächsten Programmstart werden Einstellungen geladen
- **Speicherort**: `~/.tubaf_scatter_plots/config.json`
- **Umfang**: Legend, Grid, Font-Settings, aktuelles Design

#### Umfassendes Logging-System
- **Python logging Modul**: Professionelles Logging-Framework
- **Console Handler**: INFO+ Level für wichtige Aktionen
- **File Handler**: DEBUG+ Level für vollständige Logs
- **Log-Dateien**: `~/.tubaf_scatter_plots/logs/scatterplot_YYYYMMDD.log`
- **Format**: `[HH:MM:SS] LEVEL Message`
- **Vollständig**: Alle Aktionen nachvollziehbar

### Verbesserungen

- **Logging in allen Modulen**: scatter_plot.py, design_manager.py, user_config.py
- **Globale Farbpaletten-Fix**: Änderung setzt jetzt alle Gruppen-Paletten zurück
- **Plot Design Persistenz**: current_plot_design wird in Sessions gespeichert
- **Detaillierte Log-Ausgaben**: Startup, Config-Laden, Daten-Laden, Gruppen-Operations

### Fixes

- **Standard-Design Problem**: Durch Logging jetzt debuggbar
- **Farbpaletten-Persistenz**: Gruppen-Farbpaletten werden korrekt gespeichert/geladen
- **Globale Palette**: Setzt jetzt korrekt alle Gruppen-Paletten zurück

### Umbenannt

- **Programmname**: "TUBAF Scattering Plot Tool" → "ScatterForge Plot"
- **Version**: 5.2 → 5.6
- **Window Title**: Zeigt jetzt "ScatterForge Plot v5.6"
- **About Dialog**: Aktualisiert mit neuen Features

---

## [5.3.0] - 2024-11-xx

### Neue Features

#### Erweiterte Schriftart-Optionen
- Bold, Italic, Underline für alle Text-Elemente
- Titel, Achsenbeschriftungen, Ticks, Legende individuell anpassbar
- Font-Dialog mit allen Optionen an einem Ort

#### Bearbeitbare Standard-Designs
- Standard-Designs können bearbeitet werden
- Änderungen werden gespeichert
- Wiederherstellen durch Löschen möglich

#### Interaktive Annotations & Referenzlinien
- Draggable Annotations (per Maus verschiebbar)
- Tree-Integration mit eigener Sektion
- Context-Menü für Bearbeiten/Löschen
- Auto-Labels für Referenzlinien

---

## [5.2.0] - 2024-10-xx

### Neue Features

#### Plot-Designs System
- 5 vordefinierte Designs
- Benutzerdefinierte Designs speichern
- Ein-Klick-Anwendung
- Design-Manager Tab

#### Annotations und Referenzlinien
- Textfelder mit Position, Größe, Farbe, Rotation
- Vertikale/Horizontale Referenzlinien
- Ideal für Kratky/Porod-Plots

#### Math Text für Exponenten
- Unicode → Math Text Konvertierung
- Schriftarten-unabhängig
- Optional aktivierbar

---

## [5.1.0] - 2024-09-xx

### Neue Features

- Erweiterte Legenden-Einstellungen
- Grid-Einstellungen (Major/Minor)
- Font-Einstellungen für alle Elemente
- Export-Dialog überarbeitet

---

## [5.0.0] - 2024-08-xx

### Neue Features

- Modulare Architektur
- Verbessertes Daten-Management
- Session-Verwaltung
- Auto-Stil-Erkennung

---

## [4.2.0] - 2024-07-xx

### Neue Features

- Checkbox-Sichtbarkeit für Datasets
- Drag & Drop verbessert
- Kontextmenü erweitert

---

## [4.0.0] - 2024-06-xx

### Große Änderungen

- **Qt6 Migration**: Komplette Umstellung von Tkinter auf Qt6
- Dark Mode Support
- Bessere Performance
- Natives Look & Feel

---

## [3.0.0] - 2024-05-xx

### Features

- Tkinter-basierte GUI
- Basis-Plot-Funktionalität
- Einfache Gruppierung

---

[5.6.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.3...v5.6
[5.3.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.2...v5.3
[5.2.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.1...v5.2
[5.1.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.0...v5.1
[5.0.0]: https://github.com/traianuschem/ScatteringPlot/compare/v4.2...v5.0
[4.2.0]: https://github.com/traianuschem/ScatteringPlot/compare/v4.0...v4.2
[4.0.0]: https://github.com/traianuschem/ScatteringPlot/compare/v3.0...v4.0
[3.0.0]: https://github.com/traianuschem/ScatteringPlot/releases/tag/v3.0
