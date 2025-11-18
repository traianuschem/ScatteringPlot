# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [6.1.0] - 2025-01-18

### 🎉 Major Release - Umfassende Plot-Formatierung

Version 6.1 bringt **professionelle Kurven-Gestaltung** mit vollständiger Kontrolle über alle visuellen Aspekte.

### ✨ Neu

#### Umfassender Kurven-Editor (v6.0/6.1)
- **Alle visuellen Eigenschaften** in einem Dialog:
  - Farbe (Farbwähler + Schnellauswahl)
  - Marker (13 Stile, Größe 0-20 pt)
  - Linie (5 Stile, Breite 0-10 pt)
  - Fehlerbalken (Darstellung, Transparenz, Caps, Linienbreite)
- **Live-Vorschau** der Farbauswahl
- **Kontextmenü**: Rechtsklick → "🎨 Kurve bearbeiten..."

#### Schnellfarben-Menü (v6.0/6.1)
- **Direkter Zugriff** auf Farben der aktuellen Farbpalette
- **Intelligente Palette-Auswahl**:
  - Berücksichtigt globale Farbpalette
  - Berücksichtigt Gruppen-Farbpalette
  - Zeigt bis zu 10 Farben als Schnellauswahl
- **Kontextmenü**: Rechtsklick → "Schnellfarben" → Farbe wählen
- **Sofortige Anwendung**: Keine Dialog-Bestätigung nötig

#### Flexible Fehlerbalken-Darstellung (v6.0/6.1)
- **Zwei Darstellungsarten**:
  - **Transparente Fläche** (`fill_between`):
    - Ideal für dichte Messpunkte
    - Zeigt Fehlerbereich als zusammenhängende Fläche
    - Standard für "Messung"-Stil
  - **Balken mit Caps** (`errorbar`):
    - Klassische wissenschaftliche Darstellung
    - Gut für wenige, weit auseinander liegende Punkte
    - Standard für "Fit", "Simulation", "Theorie"
- **Konfigurierbare Parameter**:
  - Transparenz: 0-100% (Standard: 30% für Flächen, 70% für Balken)
  - Cap-Größe: 0-10 pt (nur bei Balken, Standard: 3)
  - Linienbreite: 0.1-5 pt (nur bei Balken, Standard: 1.0)
- **Intelligente UI**: Zeigt nur relevante Parameter je nach gewähltem Stil

#### Erweiterte Stil-Vorlagen
- **Fehlerbalken-Einstellungen** in Stil-Vorlagen integriert:
  - "Messung": `errorbar_style='fill'`, `errorbar_alpha=0.3`
  - "Fit": `errorbar_style='bars'`
  - "Simulation": `errorbar_style='bars'`
  - "Theorie": `errorbar_style='bars'`
- **Auto-Stil-Erkennung** wendet jetzt auch Fehlerbalken-Einstellungen an
- **apply_style_preset()** übernimmt Fehlerbalken-Parameter

### 🔧 Verbessert
- **Plot-Funktion**: Unterstützt beide Fehlerbalken-Darstellungen
- **DataSet-Modell**: Erweitert um `errorbar_style` Property
- **Serialisierung**: Vollständige Speicherung aller Fehlerbalken-Parameter in Sessions
- **Dialog-Layout**: Optimierte Darstellung im Kurven-Editor
- **Kontextmenü**: Umstrukturiert für bessere Übersicht

### 📦 Technisch
- Neue Datei: `dialogs/curve_settings_dialog.py` (umfassender Kurven-Editor)
- Erweitert: `core/models.py` (Fehlerbalken-Properties: `errorbar_style`, `errorbar_alpha`)
- Erweitert: `utils/user_config.py` (Stil-Vorlagen mit Fehlerbalken-Einstellungen)
- Erweitert: `scatter_plot.py` (Kontextmenü, Plot-Funktion, Handler-Funktionen)
- Aktualisiert: Plot-Funktion mit bedingter Fehlerbalken-Darstellung (`fill` vs `bars`)

---

## [5.7.0] - 2024-12-xx

### ✨ Neu

#### Erweiterte Legenden-Verwaltung
- **Legendeneditor** mit individueller Formatierung:
  - Einträge umbenennen (Display-Labels unabhängig von Dataset-Namen)
  - Formatierung: fett, kursiv (pro Eintrag)
  - Reihenfolge ändern (Drag & Drop im Tree)
- **Unbegrenzte Skalierungsfaktoren** für Gruppen:
  - Nicht mehr auf vordefinierte Werte beschränkt
  - Beliebige Dezimalzahlen als Stack-Faktor
  - Doppelklick auf Gruppe zum Ändern
- **Automatische Farbvereinheitlichung** bei Gruppierung:
  - Optional: Einheitliche Farbe für alle Datasets einer Gruppe
  - Kontextmenü: "Einheitliche Farbe setzen..."

#### Individuelle Plotgrenzen (v5.7)
- **Pro Datensatz** X/Y-Limits setzen:
  - X-Min, X-Max, Y-Min, Y-Max individuell konfigurierbar
  - Nur Datenpunkte im Bereich werden geplottet
- **Dialog**: "Plotgrenzen setzen..." im Kontextmenü
- **Anwendungen**:
  - Unerwünschte Bereiche ausblenden
  - Zoom auf interessanten Bereich
  - Pro Datensatz individuell
- **Serialisierung**: Wird in Sessions gespeichert

#### Erweiterte Achsen- und Tick-Einstellungen
- **Tick-Parameter**: Major/Minor Ticks separat steuerbar
- **Custom Labels**: Achsenbeschriftungen anpassen
- **Scientific Notation**: Ein/Ausschalten per Checkbox
- **Unit-Format-Konvertierung**: nm ↔ Å (automatische Umrechnung)
- **Dialog**: Achsen → Achsen-Einstellungen...

### 🔧 Verbessert
- **Grid-Dialog**: Unit-Format-Konvertierung integriert
- **Legendenfarben**: Synchronisation mit Kurvenfarben
- **Reihenfolge**: Legendeneinträge in korrekter Plot-Reihenfolge

### 🐛 Behoben
- **Grid-Dialog NameError**: AttributeError bei Grid-Einstellungen behoben
- **Unit-Format**: Konvertierung zwischen nm und Å funktioniert korrekt
- **Legendenfarben-Synchronisation**: Farben werden korrekt aktualisiert

---

## [5.6.0] - 2025-01-09

### 🎉 Major Release - Export & Gruppierung

### ✨ Neu

#### Export-Optimierung
- **16:10 Standard-Format**: 25.4 cm × 15.875 cm (optimal für Publikationen)
- **Hohe Auflösung**: Bis 1200 DPI
- **Format-Vorlagen**: PNG, SVG, PDF, EPS
- **tight_layout**: Automatische Optimierung der Layout-Positionierung

#### Gruppenspezifische Farbpaletten
- **Pro-Gruppe Farbpaletten**: Jede Gruppe kann eigene Farbpalette haben
- **Kontextmenü**: Rechtsklick auf Gruppe → "Farbpalette wählen"
- **Fallback**: Globale Farbpalette wenn nicht gesetzt
- **Alle Paletten**: TUBAF, Matplotlib Colormaps, User-definiert
- **Persistierung**: Wird in Sessions gespeichert

#### Auto-Gruppierung überarbeitet
- **Ein Dataset = Eine Gruppe**: Erstellt für jedes ausgewählte Dataset eigene Gruppe
- **Automatische Stack-Faktoren**: 10^0, 10^1, 10^2, ... (Zehnerpotenzen)
- **Gruppen-Name**: Dataset-Name wird als Gruppen-Name verwendet
- **Optimale Trennung**: Perfekt für Log-Log-Plots
- **Anpassbar**: Stack-Faktoren nachträglich änderbar (Doppelklick)

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
- **Rotation**: Täglich neue Datei, alte bleiben erhalten

### 🔧 Verbessert
- **Logging in allen Modulen**: scatter_plot.py, design_manager.py, user_config.py
- **Plot Design Persistenz**: current_plot_design wird in Sessions gespeichert
- **Detaillierte Log-Ausgaben**: Startup, Config-Laden, Daten-Laden, Gruppen-Operations

### 🐛 Behoben
- **Globale Farbpaletten-Fix**: Änderung setzt alle Gruppen-Paletten zurück
- **Standard-Design Problem**: Durch Logging debuggbar
- **Farbpaletten-Persistenz**: Gruppen-Farbpaletten korrekt gespeichert/geladen

### Umbenannt
- **Programmname**: "TUBAF Scattering Plot Tool" → "ScatterForge Plot"
- **Window Title**: Zeigt "ScatterForge Plot v5.6"
- **About Dialog**: Aktualisiert mit neuen Features

---

## [5.3.0] - 2024-11-xx

### ✨ Neu

#### Erweiterte Schriftart-Optionen
- **Bold, Italic, Underline** für alle Text-Elemente
- **Individuell anpassbar**: Titel, Achsenbeschriftungen, Ticks, Legende
- **Font-Dialog**: Alle Optionen an einem Ort

#### Bearbeitbare Standard-Designs
- **Standard-Designs** können bearbeitet werden
- **Änderungen** werden gespeichert
- **Wiederherstellen**: Durch Löschen möglich

#### Interaktive Annotations & Referenzlinien
- **Draggable Annotations**: Per Maus verschiebbar
- **Tree-Integration**: Eigene Sektion "Annotations & Referenzlinien"
- **Context-Menü**: Bearbeiten/Löschen
- **Auto-Labels**: Für Referenzlinien

---

## [5.2.0] - 2024-10-xx

### ✨ Neu

#### Plot-Designs System
- **5 vordefinierte Designs**: Standard, Präsentation, Publikation, Poster, Minimalistisch
- **Benutzerdefinierte Designs**: Speichern und verwalten
- **Ein-Klick-Anwendung**: Design wechseln
- **Design-Manager Tab**: Zentrale Verwaltung

#### Annotations und Referenzlinien
- **Textfelder**: Position, Größe, Farbe, Rotation
- **Vertikale/Horizontale Referenzlinien**: Ideal für Kratky/Porod-Plots

#### Math Text für Exponenten
- **Unicode → Math Text**: Automatische Konvertierung
- **Schriftarten-unabhängig**: Funktioniert mit allen Fonts
- **Optional aktivierbar**: Per Checkbox

---

## [5.1.0] - 2024-09-xx

### ✨ Neu

- **Erweiterte Legenden-Einstellungen**: Position, Spalten, Transparenz
- **Grid-Einstellungen**: Major/Minor Grid separat steuerbar
- **Font-Einstellungen**: Für alle Text-Elemente
- **Export-Dialog**: Überarbeitet und optimiert

---

## [5.0.0] - 2024-08-xx

### 🎉 Major Release - Modulare Architektur

### ✨ Neu

- **Modulare Architektur**: Saubere Code-Struktur
- **Verbessertes Daten-Management**: DataSet und DataGroup Klassen
- **Session-Verwaltung**: Projektzustände speichern/laden
- **Auto-Stil-Erkennung**: Basierend auf Dateinamen

---

## [4.2.0] - 2024-07-xx

### ✨ Neu

- **Checkbox-Sichtbarkeit**: Für Datasets
- **Drag & Drop**: Verbessert
- **Kontextmenü**: Erweitert

---

## [4.0.0] - 2024-06-xx

### 🎉 Major Release - Qt6 Migration

### Große Änderungen

- **Qt6 Migration**: Komplette Umstellung von Tkinter auf Qt6 (PySide6)
- **Dark Mode Support**: Permanenter dunkler Modus
- **Bessere Performance**: Schnellere Plots und UI-Reaktionen
- **Natives Look & Feel**: Plattform-spezifisches Aussehen

---

## [3.0.0] - 2024-05-xx

### ✨ Features

- **Tkinter-basierte GUI**: Erste grafische Benutzeroberfläche
- **Basis-Plot-Funktionalität**: Log-Log Plots
- **Einfache Gruppierung**: Datasets organisieren

---

## Versions-Links

[6.1.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.7...v6.1
[5.7.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.6...v5.7
[5.6.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.3...v5.6
[5.3.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.2...v5.3
[5.2.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.1...v5.2
[5.1.0]: https://github.com/traianuschem/ScatteringPlot/compare/v5.0...v5.1
[5.0.0]: https://github.com/traianuschem/ScatteringPlot/compare/v4.2...v5.0
[4.2.0]: https://github.com/traianuschem/ScatteringPlot/compare/v4.0...v4.2
[4.0.0]: https://github.com/traianuschem/ScatteringPlot/compare/v3.0...v4.0
[3.0.0]: https://github.com/traianuschem/ScatteringPlot/releases/tag/v3.0

---

## Legende

- ✨ **Neu**: Neue Features
- 🔧 **Verbessert**: Verbesserungen an bestehenden Features
- 🐛 **Behoben**: Bugfixes
- 🎉 **Major Release**: Große Version mit vielen Änderungen
- 📦 **Technisch**: Technische Änderungen (API, Struktur, ...)
- 🗑️ **Entfernt**: Entfernte Features

---

## Versions-Schema

ScatterForge Plot folgt [Semantic Versioning](https://semver.org/lang/de/):

- **Major** (X.0.0): Große Änderungen, möglicherweise inkompatibel
- **Minor** (0.X.0): Neue Features, abwärtskompatibel
- **Patch** (0.0.X): Bugfixes, abwärtskompatibel

**Beispiel**: Version 6.1.0
- **6**: Major Version (umfassende Plot-Formatierung)
- **1**: Minor Version (Fehlerbalken-Darstellung)
- **0**: Patch Version

---

**Für detaillierte Informationen zu jedem Release, siehe [GitHub Releases](https://github.com/traianuschem/ScatteringPlot/releases)**
