# ScatterForge Plot v7.0.0dev

**Professionelles Tool für wissenschaftliche Streudaten-Analyse und Publikationsreife Visualisierung**

![Version](https://img.shields.io/badge/version-7.0.0dev-orange)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)

## 📄 Abstract

ScatterForge Plot ist eine umfassende, Qt6-basierte Desktop-Anwendung für die professionelle Visualisierung und Analyse von Streudaten (SAXS/SANS/XRD). Das Tool wurde speziell für Naturwissenschaftler und Ingenieure entwickelt und bietet vollständige Kontrolle über alle Aspekte der wissenschaftlichen Datenvisualisierung.

**Kernfunktionalität:**
- **7 Plot-Typen** für verschiedene Analysen (Log-Log, Porod, Kratky, Guinier, Bragg Spacing, 2-Theta, PDDF)
- **LaTeX/MathText-Unterstützung** für wissenschaftliche Notation in Legenden, Achsenbeschriftungen und Annotations
- **Mehrsprachige Benutzeroberfläche** (Deutsch/Englisch) mit vollständiger i18n-Unterstützung
- **Advanced Export-System** mit Live-Vorschau, XMP-Metadaten und 5 Formaten (PNG, SVG, PDF, EPS, TIFF)
- **Umfassender Kurven-Editor** mit 13 Marker-Stilen, flexiblen Fehlerbalken (transparente Fläche oder Balken mit Caps)
- **Gruppen-Management** mit individuellen Stack-Faktoren, Drag & Drop und automatischer Farbpaletten-Verwaltung
- **Session-Verwaltung** für vollständige Projektzustände mit allen Formatierungen und Einstellungen
- **Keyboard Shortcuts** für effizienten Workflow
- **30+ Farbpaletten** (TUBAF Corporate Design, Matplotlib Colormaps) mit gruppenspezifischen Zuweisungen

Das Tool eignet sich besonders für die Erstellung publikationsreifer Grafiken mit präziser Kontrolle über Layout, Formatierung und wissenschaftliche Metadaten.

---

## 🎉 Neue Features in v7.0.0dev

Version 7.0 ist ein **Major Release** mit **LaTeX-Unterstützung**, **Internationalisierung** und **wissenschaftlichem Metadaten-Management**:

### 📝 LaTeX/MathText-Unterstützung
- **Wissenschaftliche Notation** mit voller LaTeX/MathText-Syntax:
  - **Legenden**: Mathematische Ausdrücke wie `I·q^{2}`, `R_g`, `σ_{exp}`
  - **Achsenbeschriftungen**: Einheiten und Variablen (z.B. `q / nm^{-1}`, `I(q) / a.u.`)
  - **Annotations**: Formeln und wissenschaftliche Bezeichnungen
- **Live-Vorschau** im Editor für sofortiges Feedback
- **Bold-Support** in Legenden mit korrekter MathText-Formatierung
- **Intelligente Verkettung** von Text und Math-Bereichen
- **Automatische Konvertierung** von Unicode-Exponenten zu MathText

### 🌍 Mehrsprachigkeit (i18n)
- **Vollständige Lokalisierung** der Benutzeroberfläche:
  - 🇩🇪 **Deutsch** (Standard)
  - 🇬🇧 **Englisch** (vollständig übersetzt)
- **Alle Dialoge übersetzt**: Export, Kurven-Editor, Legenden, Achsen, Grid, Gruppen, etc.
- **Sprachumschaltung** ohne Neustart im Einstellungen-Dialog
- **Persistent**: Sprachwahl wird gespeichert
- **JSON-basiertes i18n-System** für einfache Erweiterbarkeit

### 📊 Advanced Export Dialog mit Live-Vorschau
- **Echtzeit-Vorschau** des Exports während der Konfiguration
- **Wissenschaftliche Metadaten-Integration**:
  - Autor, Institution, Projekt, Beschreibung
  - Copyright, Lizenz, Keywords
  - **XMP-Sidecar-Dateien** (.xmp) für alle Formate
  - **Eingebettete Metadaten** in PDF/PNG/TIFF
- **Umfangreiche Export-Optionen**:
  - 5 Formate: **PNG, SVG, PDF, EPS, TIFF** (TIFF neu!)
  - DPI-Auswahl bis 1200
  - Flexible Größenanpassung (16:10, 4:3, Custom)
  - Transparenz-Option für PNG
- **Dark Mode Support** für alle UI-Elemente
- **Accordion-Layout** für übersichtliche Organisation

### ⌨️ Umfassende Keyboard Shortcuts
- **Schneller Workflow** ohne Maus:
  - `Strg+O`: Daten laden
  - `Strg+S`: Session speichern
  - `Strg+E`: Export-Dialog
  - `Strg+G`: Neue Gruppe erstellen
  - `Entf`: Ausgewählte Elemente löschen
  - `F5`: Plot aktualisieren
- **Kontextmenü-Integration**: Shortcuts werden angezeigt
- **Konsistente Bedienung** über alle Dialoge

### 🔧 Konsolidierte Menüstruktur (v7.0)
- **Reorganisierte Menüs** für bessere Übersichtlichkeit
- **Erweiterte Editoren**:
  - Achsen-Dialog jetzt mit integrierten Achsenlimits
  - Titel-Editor für Plot-Titel-Anpassung
  - Plot-Limits-Editor für Datensatz-spezifische Grenzen
- **Tree-Reihenfolge bestimmt Legende**: Drag & Drop im Tree ändert direkt die Legendenreihenfolge
- **Multiplikationsfaktoren** direkt im Gruppennamen sichtbar

### 🧪 Verbesserungen für XRD/SAXS-Analyse
- **XRD-Referenz Design** im Kurven-Editor
- **Bragg Spacing Plot-Typ**: d = 2π/q für Realraum-Darstellung
- **2-Theta Plot-Typ**: Winkel-basierte Darstellung (konfigurierbare Wellenlänge)
- **Verbesserte Referenzlinien** für Peak-Markierung

---

## 🌟 Highlights aus v6.x

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
- **7 Plot-Typen**: Log-Log, Porod, Kratky, Guinier, Bragg Spacing, 2-Theta, PDDF
- **Stack-Modus**: Kurven mit individuellen Stack-Faktoren trennen (nicht-kumulativ!)
- **Fehlerbalken**: 2 Darstellungsarten (transparente Fläche oder Balken)
- **Annotations & Referenzlinien**: Interaktiv verschiebbar (Drag & Drop)
- **LaTeX/MathText**: Vollständige Unterstützung für wissenschaftliche Notation in Legenden, Achsen, Annotations
- **Live-Vorschau**: Für MathText-Formatierung und Export

### Kurven-Gestaltung
- **Umfassender Kurven-Editor**: Alle visuellen Eigenschaften in einem Dialog
- **Schnellfarben**: Direkter Zugriff auf Palette-Farben
- **Stil-Vorlagen**: Messung, Fit, Simulation, Theorie mit Auto-Erkennung
- **Marker & Linien**: 13 Marker-Stile, 5 Linien-Stile
- **Farben**: 30+ Farbpaletten (TUBAF, Matplotlib) + eigene Schemata
- **Gruppen-Bearbeitung**: Alle Kurven einer Gruppe gleichzeitig formatieren

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
- **Export-Formate**: PNG, SVG, PDF, EPS, TIFF (neu in v7.0!)
- **Live-Vorschau**: Echtzeit-Ansicht während Export-Konfiguration
- **Wissenschaftliche Metadaten**: XMP-Sidecar-Dateien + eingebettete Metadaten
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

### Internationalisierung & Bedienbarkeit
- **Mehrsprachigkeit**: Vollständige Übersetzung (Deutsch/Englisch)
- **Keyboard Shortcuts**: Umfassende Tastaturkürzel für schnellen Workflow
- **Sprachumschaltung**: Live-Wechsel ohne Neustart
- **i18n-System**: JSON-basiert, einfach erweiterbar

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

## 📝 LaTeX/MathText-Unterstützung (v7.0)

ScatterForge Plot unterstützt vollständig LaTeX/MathText-Syntax für wissenschaftliche Notation:

### Anwendungsbereiche

**Legenden:**
```
μ_exp → μ_{exp}
I·q^2 → I·q^{2}
R_g → R_{g}
Sample α → Sample α
```

**Achsenbeschriftungen:**
```
q / nm^-1 → q / nm^{-1}
I(q) / a.u. → I(q) / a.u.
d / Å → d / Å
```

**Annotations:**
```
Peak bei q* = 0.5 nm^-1 → Peak bei q^{*} = 0.5 nm^{-1}
Form-Faktor P(q) → Form-Faktor P(q)
```

### Features

- **Live-Vorschau**: Sofortige Anzeige der formatierten Ausgabe im Editor
- **Intelligente Verkettung**: Automatische Kombination von Text und Math-Bereichen
- **Bold-Support**: Fettdruck funktioniert auch mit MathText
- **Automatische Konvertierung**: Unicode-Exponenten (², ³) werden zu MathText konvertiert
- **Fehlerbehandlung**: Ungültige Syntax wird angezeigt

### Beispiele

| Eingabe | Ausgabe (gerendert) |
|---------|---------------------|
| `Sample_1` | Sample₁ |
| `I·q^{2}` | I·q² |
| `R_g = 5.3 nm` | Rg = 5.3 nm |
| `\alpha = 45°` | α = 45° |
| `10^{-3}` | 10⁻³ |

**Verwendung:**
```
1. Legenden → Legende bearbeiten... → LaTeX/MathText aktivieren
2. Achsen → Achsen-Einstellungen... → LaTeX in Labels verwenden
3. Annotations → Text mit MathText-Syntax eingeben
```

---

## 🌍 Mehrsprachigkeit (v7.0)

ScatterForge Plot ist vollständig mehrsprachig mit Unterstützung für:

### Unterstützte Sprachen

- 🇩🇪 **Deutsch** (Standard)
- 🇬🇧 **Englisch**

### Sprachumschaltung

**Im Programm:**
```
1. Einstellungen → Einstellungen...
2. Sprache auswählen (Deutsch/English)
3. Änderung wird sofort angewendet (kein Neustart nötig!)
```

**Persistenz:**
- Sprachwahl wird in `~/.tubaf_scatter_plots/config.json` gespeichert
- Beim nächsten Start wird die gewählte Sprache geladen

### Übersetzte Bereiche

- **Hauptfenster**: Alle Menüs, Buttons, Kontextmenüs
- **Dialoge**: Export, Kurven-Editor, Legenden, Achsen, Grid, Gruppen, etc.
- **Meldungen**: Fehlermeldungen, Bestätigungen, Informationen
- **Tooltips**: Hilfetexte für alle UI-Elemente

### i18n-System

- **JSON-basiert**: Einfache Erweiterung für neue Sprachen
- **Strukturiert**: Getrennte Dateien für verschiedene Module
- **Fallback**: Deutsche Texte wenn Übersetzung fehlt

**Dateien:**
```
i18n/
├── de.json  (Deutsch)
├── en.json  (Englisch)
└── __init__.py  (i18n Manager)
```

---

## 📊 Advanced Export Dialog (v7.0)

Der neue Export-Dialog bietet professionelle Export-Optionen mit Live-Vorschau und wissenschaftlichen Metadaten:

### Live-Vorschau

- **Echtzeit-Ansicht** während der Konfiguration
- **Interaktive Anpassung**: Änderungen werden sofort sichtbar
- **Zoom & Pan**: Vorschau-Navigation
- **Exakte Darstellung**: Was Sie sehen, wird exportiert

### Export-Formate

| Format | Verwendung | Metadaten-Support |
|--------|------------|-------------------|
| **PNG** | Präsentationen, Web | Eingebettet (tEXt chunks) |
| **TIFF** | Publikationen, Druck | Eingebettet (TIFF tags) |
| **PDF** | Dokumente, Publikationen | Eingebettet (PDF Info) + XMP |
| **SVG** | Vektorgrafik, Bearbeitung | XML-Attribute + XMP |
| **EPS** | LaTeX-Dokumente | Kommentare + XMP |

**Alle Formate** erhalten zusätzlich eine `.xmp` Sidecar-Datei mit vollständigen Metadaten.

### Wissenschaftliche Metadaten

**Benutzer-Metadaten:**
```
Datei → Benutzer-Metadaten...
→ Autor, Institution, E-Mail
→ Projekt, Beschreibung
→ Copyright, Lizenz
→ Keywords
```

**Automatische Metadaten:**
- Datum & Zeit der Erstellung
- Software-Version (ScatterForge Plot v7.0.0dev)
- Plot-Typ, verwendete Datasets
- Achsenbeschriftungen, Legendeneinträge

**XMP-Sidecar-Dateien (.xmp):**
- Standardisiertes XML-Format (Adobe XMP)
- Vollständige Metadaten-Sicherung
- Unabhängig vom Bildformat
- Kompatibel mit Metadaten-Browsern

### Export-Optionen

**Größe & Auflösung:**
```
- Vordefinierte Formate: 16:10 (25.4×15.875 cm), 4:3, Custom
- DPI: 300, 600, 900, 1200
- Individuelle Breite/Höhe
```

**Erweiterte Optionen:**
```
- PNG Transparenz (für Overlay-Grafiken)
- Tight Layout (automatische Rand-Optimierung)
- DPI-Einstellung für alle Formate
```

**Verwendung:**
```
1. Strg+E oder Datei → Exportieren...
2. Format und Optionen wählen
3. Metadaten prüfen/anpassen (optional)
4. Live-Vorschau prüfen
5. Exportieren
```

---

## 🎨 Plot-Typen

| Typ | X-Achse | Y-Achse | Beschreibung |
|-----|---------|---------|--------------|
| **Log-Log** | q [nm⁻¹] | I [a.u.] | Standard Streukurven (beide Achsen logarithmisch) |
| **Porod** | q [nm⁻¹] | I·q⁴ [a.u.] | Porod-Analyse (Grenzflächenstruktur) |
| **Kratky** | q [nm⁻¹] | I·q² [a.u.] | Kratky-Plot (Kompaktheit) |
| **Guinier** | q² [nm⁻²] | ln(I) | Guinier-Approximation (Trägheitsradius) |
| **Bragg Spacing** | d [nm] | I [a.u.] | Realraum-Darstellung (d = 2π/q) |
| **2-Theta** | 2θ [°] | I [a.u.] | Winkel-Darstellung (konfigurierbare Wellenlänge) |
| **PDDF** | q [nm⁻¹] | I [a.u.] + p(r) | Paardistanzverteilungsfunktion |

---

## ⌨️ Keyboard Shortcuts (v7.0)

ScatterForge Plot bietet umfassende Tastaturkürzel für einen effizienten Workflow:

### Haupt-Aktionen

| Shortcut | Aktion | Beschreibung |
|----------|--------|--------------|
| `Strg+O` | Daten laden | Öffnet Dateiauswahl-Dialog |
| `Strg+S` | Session speichern | Speichert aktuellen Projektzustand |
| `Strg+Shift+S` | Session speichern als... | Speichert unter neuem Namen |
| `Strg+L` | Session laden | Lädt gespeicherte Session |
| `Strg+E` | Exportieren | Öffnet Export-Dialog mit Live-Vorschau |
| `Strg+Q` | Beenden | Schließt Anwendung |

### Gruppen & Daten

| Shortcut | Aktion | Beschreibung |
|----------|--------|--------------|
| `Strg+G` | Neue Gruppe | Erstellt neue Datengruppe |
| `Strg+A` | Auto-Gruppieren | Automatische Gruppierung mit Stack-Faktoren |
| `Entf` | Löschen | Löscht ausgewählte Datasets/Gruppen |
| `F2` | Umbenennen | Benennt ausgewähltes Element um |

### Plot & Ansicht

| Shortcut | Aktion | Beschreibung |
|----------|--------|--------------|
| `F5` | Plot aktualisieren | Rendert Plot neu |
| `Strg+1` bis `Strg+7` | Plot-Typ wechseln | 1=Log-Log, 2=Porod, 3=Kratky, etc. |
| `Strg+Plus` | Zoom In | Vergrößert Plot-Ansicht |
| `Strg+Minus` | Zoom Out | Verkleinert Plot-Ansicht |
| `Strg+0` | Zoom Reset | Setzt Zoom zurück |

### Editoren & Dialoge

| Shortcut | Aktion | Beschreibung |
|----------|--------|--------------|
| `Strg+K` | Kurven-Editor | Öffnet Kurven-Einstellungen |
| `Strg+T` | Titel bearbeiten | Öffnet Titel-Editor |
| `Strg+U` | Achsen-Einstellungen | Öffnet Achsen-Dialog |
| `Strg+I` | Grid-Einstellungen | Öffnet Grid-Dialog |
| `Strg+M` | Legende bearbeiten | Öffnet Legenden-Editor |
| `Esc` | Dialog schließen | Schließt aktiven Dialog |

### Kontextmenü-Aktionen

**Mit ausgewähltem Dataset:**
- `Strg+C`: Farbe kopieren
- `Strg+V`: Farbe einfügen
- `Strg+R`: Stil zurücksetzen

**Hinweise:**
- Alle Shortcuts werden in den Menüs und Tooltips angezeigt
- Shortcuts funktionieren kontextabhängig
- Dialoge können mit `Enter` (OK) oder `Esc` (Abbrechen) geschlossen werden

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

Dieses Projekt ist unter der GPL-3.0 Lizenz lizenziert. Siehe [LICENSE](LICENSE) Datei für Details.

---

## 👥 Autoren

- **Richard Neubert** - *Initial work*
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
  author = {Richard Neubert},
  title = {ScatterForge Plot: Professional Scattering Data Visualization Tool},
  year = {2025},
  version = {7.0.0dev},
  url = {https://github.com/traianuschem/ScatteringPlot}
}
```

---

## 🏆 Highlights v7.0.0dev

- 📝 **LaTeX/MathText-Unterstützung** - Wissenschaftliche Notation in Legenden, Achsen und Annotations
- 🌍 **Mehrsprachigkeit** - Vollständige Deutsch/Englisch-Übersetzung mit i18n-System
- 📊 **Advanced Export mit Live-Vorschau** - Echtzeit-Vorschau + XMP-Metadaten
- ⌨️ **Keyboard Shortcuts** - Effizienter Workflow mit Tastaturkürzeln
- 🎨 **Konsolidierte UI** - Tree-Reihenfolge bestimmt Legende, erweiterte Editoren
- 🧪 **XRD/SAXS-Optimierungen** - Bragg Spacing, 2-Theta, verbesserte Referenzlinien
- 📐 **Wissenschaftliche Metadaten** - XMP-Sidecar + eingebettete Metadaten für Publikationen
- 🖼️ **TIFF-Export** - Zusätzliches Format für hochwertige wissenschaftliche Grafiken

---

**Made with ❤️ for the scientific community**

*Version 7.0.0dev - Dezember 2025*
