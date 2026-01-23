# ScatterForge Plot v7.0.4

**Professionelles Tool für wissenschaftliche Streudaten-Analyse mit publikationsreifer Visualisierung**

![Version](https://img.shields.io/badge/version-7.0.4-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)

---

## 📄 Über ScatterForge Plot

ScatterForge Plot ist eine Qt6-basierte Desktop-Anwendung für die professionelle Visualisierung und Analyse von Streudaten (SAXS/SANS/XRD). Entwickelt für Naturwissenschaftler und Ingenieure, die publikationsreife Grafiken mit präziser Kontrolle über alle Aspekte benötigen.

### 🎯 Alleinstellungsmerkmale

**1. Intelligentes Gruppen-Management**
- Organisieren Sie Datensätze in Gruppen mit individuellen Stack-Faktoren
- Nicht-kumulative Multiplikatoren für perfekte Kurvenseparation
- Gruppenspezifische Farbpaletten und Batch-Formatierung
- Drag & Drop zwischen Gruppen, Auto-Gruppierung mit Zehnerpotenzen

**2. Wissenschaftliches Metadaten-System**
- XMP-Sidecar-Dateien (.xmp) für alle Export-Formate, die XMP nicht eingebettet unterstützen
- Eingebettete Metadaten (Autor, Institution, Projekt, Lizenz)
- Benutzer-Konfigurationssystem für dauerhafte Metadaten
- Volle Rückverfolgbarkeit für wissenschaftliche Publikationen

**3. LaTeX/MathText-Integration**
- Mathematische Notation in Legenden, Achsen und Annotations
- Live-Vorschau mit automatischer Konvertierung

---

## 📑 Inhaltsverzeichnis

- [Feature-Übersicht](#-feature-übersicht)
- [Was ist neu in v7.0](#-was-ist-neu-in-v70)
- [Installation](#-installation)
- [Schnellstart (5 Minuten)](#-schnellstart-5-minuten)
- [Benutzerhandbuch](#-benutzerhandbuch)
  - [1. Daten laden](#1-daten-laden)
  - [2. Plot-Typ wählen](#2-plot-typ-wählen)
  - [3. Gruppen organisieren](#3-gruppen-organisieren-alleinstellungsmerkmal)
  - [4. Kurven gestalten](#4-kurven-gestalten)
  - [5. Plot formatieren](#5-plot-formatieren)
  - [6. Exportieren](#6-exportieren-mit-metadaten)
  - [7. Sessions speichern](#7-sessions-speichern)
- [Feature-Referenz](#-feature-referenz)
- [Konfiguration](#-konfiguration)
- [Troubleshooting](#-troubleshooting)
- [Mitwirken & Lizenz](#-mitwirken--lizenz)

---

## 🎨 Feature-Übersicht

### Was kann ScatterForge Plot?

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **Plot-Typen** | 7 spezialisierte Darstellungen (Log-Log, Porod, Kratky, Guinier, Bragg Spacing, 2-Theta, PDDF) | ✅ |
| **Gruppen-Management** | Datasets organisieren mit Stack-Faktoren, Drag & Drop, Auto-Gruppierung | ✅ **USP** |
| **Metadaten-Export** | XMP-Sidecar + eingebettete Metadaten, Benutzer-Profil-System | ✅ **USP** |
| **LaTeX/MathText** | Wissenschaftliche Notation mit Live-Vorschau | ✅ v7.0 |
| **Mehrsprachigkeit** | Deutsch/Englisch | ✅ v7.0 |
| **Export-Formate** | PNG, SVG, PDF, EPS, TIFF mit Live-Vorschau | ✅ |
| **Fehlerbalken** | 2 Darstellungen: Transparente Fläche oder Balken mit Caps | ✅ |
| **Farbpaletten** | 30+ Paletten (TUBAF, Matplotlib), gruppenspezifisch | ✅ |
| **Keyboard Shortcuts** | Vollständige Tastatursteuerung | ✅ v7.0 |
| **Session-Verwaltung** | Komplette Projektzustände speichern/laden | ✅ |
| **Annotations** | Interaktiv verschiebbar, LaTeX-Support | ✅ |
| **Stil-Vorlagen** | Auto-Erkennung (Messung, Fit, Simulation, Theorie) | ✅ |
| **Dark Mode** | Vollständige Dark-Mode-Unterstützung | ✅ |

---

## 🎉 Was ist neu in v7.0?

**Major Release v7.0.4** mit wissenschaftlicher Text-Unterstützung und internationalem Support:

### Hauptfeatures v7.0

- 📝 **LaTeX/MathText**: Wissenschaftliche Notation überall (Legenden, Achsen, Annotations)
- 🌍 **Mehrsprachigkeit**: Vollständige Deutsch/Englisch-Lokalisierung
- 📊 **Advanced Export**: Live-Vorschau + XMP-Metadaten-System
- ⌨️ **Keyboard Shortcuts**: Effizienter Workflow
- 🔧 **UI-Verbesserungen**: Tree-Reihenfolge bestimmt Legende
- 🖼️ **TIFF-Export**: Zusätzliches hochwertiges Format
- 🐛 **Stabilitätsverbesserungen**: Kritische Bugfixes in v7.0.2-7.0.4

### Aktuelles Update v7.0.4 (23. Januar 2026)

**Kritische Session-Loading-Fixes:**
- ✅ Behebt QTreeWidgetItem-Deletion-Fehler beim Laden von Sessions
- ✅ Graceful Fallback für fehlende Datendateien auf verschiedenen PCs
- ✅ Sessions laden jetzt mit leeren Gruppen statt komplett zu scheitern
- ✅ Benutzer erhalten informative Warnung über fehlende Dateien

### Update v7.0.3 (23. Januar 2026)

**Neue Features:**
- ✅ Font-Auswahl für Achsenbeschriftungen und Tick-Labels
- ✅ Achsen-Tab im Plot-Design-Editor
- ✅ Vollständige Plot-Design-Übersetzungen

**Bug Fixes:**
- ✅ AttributeError in axes_dialog.py behoben
- ✅ Design-Namen-Übersetzungsprobleme gelöst

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.0.md](CHANGELOG_v7.0.md)

---

## 🛠️ Installation

### Voraussetzungen

- Python 3.8 oder höher
- PySide6 (Qt6 für Python)
- Matplotlib
- NumPy

### Installation via Git

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

```txt
PySide6>=6.5.0
matplotlib>=3.7.0
numpy>=1.24.0
```

---

## ⚡ Schnellstart (5 Minuten)

### Ihr erster Plot in 5 Schritten

```
1. ✅ Programm starten: python scatter_plot.py
2. 📁 Daten laden: Strg+O → .dat/.csv/.txt Dateien auswählen
3. 📊 Plot-Typ wählen: Dropdown "Log-Log" (Standard)
4. 🎨 Kurve formatieren: Rechtsklick auf Dataset → "Kurve bearbeiten"
5. 💾 Exportieren: Strg+E → Format wählen → Speichern
```

**Fertig!** Sie haben Ihren ersten wissenschaftlichen Plot erstellt.

### Nächste Schritte

- **Gruppen erstellen:** Organisieren Sie mehrere Datensätze → [Gruppen-Management](#3-gruppen-organisieren-alleinstellungsmerkmal)
- **Metadaten hinzufügen:** Autor, Projekt, Lizenz → [Metadaten-System](#benutzer-metadaten-system)
- **Session speichern:** Projekt für später sichern → `Strg+S`

---

## 📖 Benutzerhandbuch

Folgen Sie dem typischen Workflow von Datenimport bis Export.

---

### 1. Daten laden

#### Unterstützte Formate

ScatterForge Plot liest ASCII-Dateien mit Whitespace-getrennten Spalten:

**2-Spalten-Format** (q, I):
```
# q / nm^-1    I / a.u.
0.1            1000.5
0.2            856.3
0.3            723.1
```

**3-Spalten-Format** (q, I, I_err):
```
# q / nm^-1    I / a.u.    I_err
0.1            1000.5      15.2
0.2            856.3       12.8
0.3            723.1       10.5
```

**Hinweise:**
- Dateierweiterungen: `.dat`, `.txt`, `.csv`
- Kommentarzeilen beginnen mit `#`
- Dezimaltrennzeichen: Punkt (`.`)
- Fehler in 3. Spalte optional

#### Daten importieren

**Methode 1: Menü**
```
Datei → Daten laden... → Dateien auswählen
```

**Methode 2: Keyboard**
```
Strg+O → Dateien auswählen
```

**Methode 3: Drag & Drop** (geplant für v7.1)

**Nach dem Import:**
- Datasets erscheinen in der Kategorie "Nicht zugeordnet"
- Automatische Stil-Erkennung anhand Dateinamen:
  - `*messung*.dat` → Messung-Stil (Marker + transparente Fehlerfläche)
  - `*fit*.dat` → Fit-Stil (durchgezogene Linie)
  - `*sim*.dat` → Simulation-Stil (gestrichelt)
  - `*theo*.dat` → Theorie-Stil (Strich-Punkt)

---

### 2. Plot-Typ wählen

ScatterForge Plot bietet 7 spezialisierte Plot-Typen für verschiedene Analysen:

| Plot-Typ | X-Achse | Y-Achse | Anwendung |
|----------|---------|---------|-----------|
| **Log-Log** | q [nm⁻¹] | I [a.u.] | Standard-Streukurven (logarithmisch) |
| **Porod** | q [nm⁻¹] | I·q⁴ [a.u.] | Grenzflächenanalyse, Oberflächen-Fraktale |
| **Kratky** | q [nm⁻¹] | I·q² [a.u.] | Kompaktheit, Faltungszustand |
| **Guinier** | q² [nm⁻²] | ln(I) | Trägheitsradius Rg bestimmen |
| **Bragg Spacing** | d [nm] | I [a.u.] | Realraum-Darstellung (d = 2π/q) |
| **2-Theta** | 2θ [°] | I [a.u.] | XRD-Winkeldarstellung |
| **PDDF** | r [nm] | p(r) | Paardistanzverteilungsfunktion |

**Plot-Typ wechseln:**
```
Dropdown "Plot-Typ" → Typ auswählen
oder
Strg+1 bis Strg+7 (Tastaturkürzel)
```

**2-Theta Spezial-Einstellung:**
```
Ansicht → 2-Theta-Einstellungen...
→ Wellenlänge einstellen (Standard: Cu K-alpha = 0.1524 nm)
```

---

### 3. Gruppen organisieren (Alleinstellungsmerkmal)

**Das Gruppen-System ist das Herzstück von ScatterForge Plot!**

#### Was sind Gruppen?

Gruppen organisieren Datasets und ermöglichen:
- **Stack-Faktoren**: Kurven vertikal trennen (nicht-kumulativ!)
- **Batch-Formatierung**: Alle Kurven einer Gruppe gleichzeitig formatieren
- **Farbpaletten**: Gruppenspezifische Farbschemata
- **Übersichtlichkeit**: Strukturierte Organisation vieler Datensätze

#### Stack-Faktoren verstehen

**WICHTIG: Nicht-kumulative Multiplikatoren!**

```
Gruppe A (Stack-Faktor: ×1)      → y_plot = y_original × 1
Gruppe B (Stack-Faktor: ×10)     → y_plot = y_original × 10
Gruppe C (Stack-Faktor: ×100)    → y_plot = y_original × 100
```

**Nicht** wie bei kumulativen Stacks:
```
❌ Gruppe C würde NICHT ×1000 sein (10 × 10 × 10)
✅ Gruppe C ist IMMER ×100 (direkt)
```

**Vorteil:** Präzise Kontrolle über Kurvenseparation in Log-Plots!

#### Gruppe erstellen (Manuell)

```
1. Button "➕ Gruppe" klicken
2. Gruppen-Name eingeben (z.B. "Konzentration 1 mg/ml")
3. Stack-Faktor setzen (z.B. 1, 10, 100, ...)
4. Datasets per Drag & Drop in Gruppe ziehen
```

**Tastaturkürzel:** `Strg+G`

#### Auto-Gruppierung (Empfohlen!)

Perfekt für viele Datensätze:

```
1. Datasets in "Nicht zugeordnet" auswählen (Strg+Klick für Mehrfachauswahl)
2. Button "🔢 Auto-Gruppieren" klicken
3. ✅ Fertig!
```

**Ergebnis:**
- Jedes Dataset bekommt eigene Gruppe
- Automatische Stack-Faktoren: 10⁰, 10¹, 10², 10³, ...
- Gruppen-Name = Dataset-Name

**Tastaturkürzel:** `Strg+A`

#### Gruppen-Bearbeitung

**Gruppe umbenennen:**
```
Doppelklick auf Gruppennamen → Neuen Namen eingeben → Enter
```

**Stack-Faktor ändern:**
```
Rechtsklick auf Gruppe → "Stack-Faktor ändern..." → Wert eingeben
```

**Alle Kurven einer Gruppe formatieren:**
```
Rechtsklick auf Gruppe → "Gruppe bearbeiten..."
→ Farbe, Marker, Linie, Fehlerbalken für ALLE Datasets setzen
```

**Gruppenspezifische Farbpalette:**
```
Rechtsklick auf Gruppe → "Farbpalette wählen..."
→ Palette auswählen (z.B. "viridis", "plasma", "TUBAF")
→ Datasets in dieser Gruppe nutzen nur diese Palette
```

#### Datasets zwischen Gruppen verschieben

**Drag & Drop:**
```
Dataset anklicken → Gedrückt halten → Auf Zielgruppe ziehen → Loslassen
```

**Aus Gruppe entfernen:**
```
Dataset auf "Nicht zugeordnet" ziehen
```

#### Gruppen löschen

```
Rechtsklick auf Gruppe → "Gruppe löschen"
→ Datasets wandern zurück nach "Nicht zugeordnet"
```

**Tastaturkürzel:** `Entf` (Gruppe auswählen, dann Entf drücken)

---

### 4. Kurven gestalten

#### Kurven-Editor (Umfassend)

Der Kurven-Editor gibt Ihnen vollständige Kontrolle über alle visuellen Eigenschaften:

```
Rechtsklick auf Dataset → "🎨 Kurve bearbeiten..."
```

**Tastaturkürzel:** `Strg+K`

**Einstellungen im Dialog:**

**1. Farbe**
- Farbwähler für beliebige RGB-Farben
- Schnellauswahl aus aktueller Palette (bis zu 10 Farben)
- "Farbe zurücksetzen" für automatische Zuweisung

**2. Marker**
- 13 Stile: Kreis (o), Quadrat (s), Dreieck (^,v,<,>), Raute (D), Stern (*), Plus (+), Kreuz (x), Punkt (.), Pixel (,)
- Größe: 0-20 pt (Standard: 4)
- "Kein Marker" für reine Linien

**3. Linie**
- 5 Stile: Durchgezogen (-), Gestrichelt (--), Strich-Punkt (-.), Gepunktet (:), Keine
- Breite: 0-10 pt (Standard: 2)

**4. Fehlerbalken**
- **Darstellung:**
  - **Transparente Fläche** (`fill_between`): Ideal für dichte Datenpunkte
  - **Balken mit Caps** (`errorbar`): Klassische Darstellung
- **Transparenz:** 0-100% (Standard: 30% für Flächen)
- **Cap-Größe:** 0-10 pt (nur bei Balken)
- **Linienbreite:** 0.1-5 pt (nur bei Balken)

#### Schnellfarben

Schneller Zugriff auf Farben der aktuellen Palette:

```
Rechtsklick auf Dataset → "Schnellfarben" → Farbe wählen
```

**Vorteil:** Sofortige Anwendung ohne Dialog!

#### Stil-Vorlagen anwenden

Vordefinierte Stile für typische Datentypen:

```
Rechtsklick auf Dataset → "Stil anwenden" → Stil wählen:
- Messung (Marker + transparente Fehlerfläche)
- Fit (durchgezogene Linie, keine Marker)
- Simulation (gestrichelte Linie)
- Theorie (Strich-Punkt-Linie)
```

#### Individuelle Plotgrenzen

Pro Dataset eigene X/Y-Limits setzen:

```
Rechtsklick auf Dataset → "Plotgrenzen setzen..."
→ X-Min, X-Max, Y-Min, Y-Max eingeben
```

**Anwendung:**
- Unerwünschte Datenbereiche ausblenden
- Auf interessanten Bereich zoomen
- Pro Dataset individuell

---

### 5. Plot formatieren

#### Legenden

**Legende bearbeiten:**
```
Legende → Legende bearbeiten...
```

**Tastaturkürzel:** `Strg+M`

**Funktionen:**
- Einträge umbenennen (unabhängig von Dataset-Namen)
- LaTeX/MathText-Formatierung (`Sample_{1}`, `I·q^{2}`)
- Fett/Kursiv pro Eintrag
- Reihenfolge per Drag & Drop im Tree ändern

**Legenden-Einstellungen:**
```
Legende → Legende-Einstellungen...
```

**Optionen:**
- Position: 9 vordefinierte Positionen
- Spalten: 1-4
- Transparenz: 0-100%
- Rahmen, Schatten

**Wichtig:** Tree-Reihenfolge = Legendenreihenfolge (v7.0)!

#### Achsen

**Achsen-Einstellungen:**
```
Achsen → Achsen-Einstellungen...
```

**Tastaturkürzel:** `Strg+U`

**Funktionen:**
- Achsenbeschriftungen anpassen (LaTeX-Support!)
- Tick-Parameter (Major/Minor)
- Scientific Notation ein/aus
- **Achsenlimits** (feste X/Y-Bereiche)
- Unit-Format-Konvertierung (nm ↔ Å)

**Achsenlimits setzen:**
```
Im Achsen-Dialog:
→ Tab "Limits"
→ X-Min, X-Max, Y-Min, Y-Max
→ Checkbox "Feste Limits verwenden"
```

**Vorteil:** Limits bleiben beim Plot-Update erhalten!

#### Grid

**Grid-Einstellungen:**
```
Grid → Grid-Einstellungen...
```

**Tastaturkürzel:** `Strg+I`

**Optionen:**
- Major/Minor Grid separat steuerbar
- Linienstile und Farben
- Anzeigen/Ausblenden

#### Plot-Titel

**Titel bearbeiten:**
```
Ansicht → Titel bearbeiten...
```

**Tastaturkürzel:** `Strg+T`

**Features:**
- LaTeX/MathText-Support
- Live-Vorschau
- Font-Einstellungen (Größe, Fett, Kursiv)

#### Annotations & Referenzlinien

**Annotation hinzufügen:**
```
Annotations → Annotation hinzufügen...
→ Text, Position, Farbe, Größe
```

**Features:**
- LaTeX/MathText-Unterstützung
- Interaktiv verschiebbar (Drag & Drop)
- Rotation

**Referenzlinie hinzufügen:**
```
Annotations → Referenzlinie hinzufügen...
→ Vertikal/Horizontal, Position, Farbe
```

**Anwendung:**
- Peak-Markierung in XRD-Plots
- Theoretische Werte anzeigen
- Grenzwerte markieren

---

### 6. Exportieren (mit Metadaten)

#### Benutzer-Metadaten-System

**Das zweite Alleinstellungsmerkmal!**

ScatterForge Plot bietet ein umfassendes Metadaten-System für wissenschaftliche Publikationen:

**Benutzer-Profil einrichten:**
```
Datei → Benutzer-Metadaten...
```

**Eingaben:**
- **Autor:** Ihr Name
- **Institution:** Universität/Institut
- **E-Mail:** Kontakt
- **Projekt:** Projektname
- **Beschreibung:** Kurzbeschreibung
- **Copyright:** Copyright-Hinweis
- **Lizenz:** CC-BY, CC0, proprietary, etc.
- **Keywords:** Stichwörter (kommagetrennt)

**Vorteil:** Einmal eingeben, bei jedem Export verwendet!

**Speicherort:** `~/.tubaf_scatter_plots/config.json`

#### Export-Dialog

**Export starten:**
```
Datei → Exportieren...
```

**Tastaturkürzel:** `Strg+E`

**Export-Dialog Features:**

**1. Live-Vorschau**
- Echtzeit-Ansicht während Konfiguration
- Zoom & Pan
- Was Sie sehen = Was Sie bekommen

**2. Format wählen**

| Format | Verwendung | Metadaten |
|--------|------------|-----------|
| PNG | Präsentationen, Web | tEXt chunks |
| TIFF | Publikationen, Druck | TIFF tags  |
| PDF | Dokumente | PDF Info + XMP |
| SVG | Vektorgrafik | XML + XMP |
| EPS | LaTeX-Dokumente | Comments + XMP |

**3. Größe & Auflösung**
- Vordefinierte Formate: 16:10 (25.4×15.875 cm), 4:3
- Custom-Größe
- DPI: 300, 600, 900, 1200

**4. Metadaten überprüfen**
- Automatisch aus Benutzer-Profil geladen
- Im Export-Dialog noch anpassbar
- Keywords hinzufügen

**5. Erweiterte Optionen**
- PNG Transparenz
- Tight Layout (automatische Rand-Optimierung)

#### XMP-Sidecar-Dateien

**Was sind XMP-Dateien?**

XMP (Extensible Metadata Platform) ist ein Adobe-Standard für Metadaten:

```
plot_export.png        ← Ihr Bild
plot_export.png.xmp    ← Metadaten-Datei
```

**Inhalt der .xmp-Datei:**
- Autor, Institution, E-Mail
- Projekt, Beschreibung
- Copyright, Lizenz
- Keywords
- Software-Version
- Erstellungsdatum
- Plot-Typ, verwendete Datasets

**Vorteil:**
- Standardisiertes Format (ISO 16684-1)
- Lesbar mit Metadaten-Browsern
- Unabhängig vom Bildformat
- Volle Rückverfolgbarkeit für Publikationen

**Workflow für Publikationen:**
```
1. Benutzer-Metadaten einmal einrichten
2. Plot erstellen und exportieren
3. .xmp-Datei zusammen mit Bild archivieren
4. Bei Fragen zur Herkunft: Metadaten prüfen
```

---

### 7. Sessions speichern

Sessions speichern den **kompletten** Projektzustand:

**Was wird gespeichert:**
- Alle geladenen Datasets (mit Pfaden)
- Gruppen mit Stack-Faktoren
- Kurven-Formatierungen (Farben, Marker, Fehlerbalken)
- Plot-Einstellungen (Legende, Grid, Achsen)
- Annotations & Referenzlinien
- Aktives Plot-Design
- Individuelle Plotgrenzen
- Farbpaletten (global + gruppenspezifisch)

**Session speichern:**
```
Datei → Session speichern...
```

**Tastaturkürzel:** `Strg+S`

**Session laden:**
```
Datei → Session laden...
```

**Tastaturkürzel:** `Strg+L`

**Format:** JSON (`.scatterforge`)

**Vorteil:** Perfekt für:
- Wiederkehrende Analysen
- Projektdokumentation
- Kollaboration (Session-Datei teilen)
- Backup vor großen Änderungen

---

## 📚 Feature-Referenz

Detaillierte Dokumentation zu ausgewählten Features.

---

### LaTeX/MathText-Unterstützung

ScatterForge Plot unterstützt vollständig LaTeX/MathText-Syntax für wissenschaftliche Notation.

#### Wo verfügbar?

- ✅ Legenden
- ✅ Achsenbeschriftungen
- ✅ Annotations
- ✅ Plot-Titel

#### Syntax-Beispiele

**Indizes:**
```
μ_exp        → μ_{exp}
R_g          → R_{g}
Sample_1     → Sample_{1}
```

**Exponenten:**
```
I·q^2        → I·q^{2}
10^-3        → 10^{-3}
nm^-1        → nm^{-1}
```

**Kombinationen:**
```
I(q) / a.u.              → I(q) / a.u.
R_g = 5.3 nm             → R_{g} = 5.3 nm
Form-Faktor P(q)         → Form-Faktor P(q)
Peak bei q* = 0.5 nm^-1  → Peak bei q^{*} = 0.5 nm^{-1}
```

**Griechische Buchstaben:**
```
\alpha, \beta, \gamma, \delta, \epsilon
\theta, \lambda, \mu, \sigma, \phi
```

#### Live-Vorschau

Alle Editoren mit LaTeX-Unterstützung zeigen eine Live-Vorschau:

```
Legende bearbeiten → Eintrag auswählen → LaTeX eingeben → Vorschau erscheint sofort
```

**Fehlerbehandlung:** Ungültige Syntax wird rot markiert.

#### Verwendung

**In Legenden:**
```
1. Legende → Legende bearbeiten...
2. Eintrag auswählen
3. LaTeX-Syntax eingeben (z.B. "Sample_{1}")
4. Live-Vorschau prüfen
5. OK
```

**In Achsenbeschriftungen:**
```
1. Achsen → Achsen-Einstellungen...
2. Tab "Beschriftungen"
3. X/Y-Label eingeben (z.B. "q / nm^{-1}")
4. Checkbox "LaTeX verwenden" aktivieren
5. OK
```

**In Annotations:**
```
1. Annotations → Annotation hinzufügen...
2. Text eingeben (z.B. "R_g = 5.3 nm")
3. Position wählen
4. OK
```

---

### Mehrsprachigkeit

ScatterForge Plot ist vollständig zweisprachig.

#### Unterstützte Sprachen

- 🇩🇪 **Deutsch** (Standard)
- 🇬🇧 **Englisch**

#### Sprache wechseln

```
Einstellungen → Einstellungen... → Sprache auswählen
```
**Persistenz:** Sprachwahl wird gespeichert und beim nächsten Start geladen.

#### Was ist übersetzt?

- Alle Menüs und Buttons
- Alle Dialoge
- Fehlermeldungen und Bestätigungen
- Tooltips

#### Eigene Sprache hinzufügen

Das i18n-System ist JSON-basiert und einfach erweiterbar:

```
i18n/
├── de.json  (Deutsch)
├── en.json  (Englisch)
└── xx.json  (Ihre Sprache)
```

Erstellen Sie eine neue `.json`-Datei nach dem Schema von `en.json`.

---

### Keyboard Shortcuts

Vollständige Referenz aller Tastaturkürzel.

#### Hauptaktionen

| Shortcut | Aktion |
|----------|--------|
| `Strg+O` | Daten laden |
| `Strg+S` | Session speichern |
| `Strg+Shift+S` | Session speichern als... |
| `Strg+L` | Session laden |
| `Strg+E` | Exportieren |
| `Strg+Q` | Beenden |

#### Gruppen & Daten

| Shortcut | Aktion |
|----------|--------|
| `Strg+G` | Neue Gruppe |
| `Strg+A` | Auto-Gruppieren |
| `Entf` | Ausgewähltes löschen |
| `F2` | Umbenennen |

#### Plot & Ansicht

| Shortcut | Aktion |
|----------|--------|
| `F5` | Plot aktualisieren |
| `Strg+1` | Log-Log |
| `Strg+2` | Porod |
| `Strg+3` | Kratky |
| `Strg+4` | Guinier |
| `Strg+5` | Bragg Spacing |
| `Strg+6` | 2-Theta |
| `Strg+7` | PDDF |

#### Editoren

| Shortcut | Aktion |
|----------|--------|
| `Strg+K` | Kurven-Editor |
| `Strg+T` | Titel bearbeiten |
| `Strg+U` | Achsen-Einstellungen |
| `Strg+I` | Grid-Einstellungen |
| `Strg+M` | Legende bearbeiten |
| `Esc` | Dialog schließen |

---

### Farbpaletten & Designs

#### Globale Farbpalette

```
Dropdown "Farbschema" → Palette auswählen
```

**Verfügbare Paletten:**
- **TUBAF** (Corporate Design)
- **Matplotlib Colormaps:** tab10, tab20, Set1, Set2, Set3, Paired, viridis, plasma, inferno, magma, cividis, twilight, etc.
- **Benutzerdefiniert** (eigene Paletten erstellen)

#### Gruppenspezifische Paletten

```
Rechtsklick auf Gruppe → "Farbpalette wählen..."
```

**Verhalten:**
- Datasets in dieser Gruppe nutzen nur diese Palette
- Überschreibt globale Palette für diese Gruppe
- Fallback auf global, wenn nicht gesetzt

#### Eigene Farbpalette erstellen

```
Design → Design-Manager... → Tab "Farbschemata"
→ "Neues Schema erstellen"
→ Name + Farben definieren
```

#### Plot-Designs

Vordefinierte Design-Sets für verschiedene Anwendungen:

| Design | Beschreibung |
|--------|--------------|
| Standard | Ausgewogene Einstellungen |
| Präsentation | Große Schrift, kräftige Farben |
| Publikation | Kleine Schrift, dezente Farben |
| Poster | Sehr große Schrift |
| Minimalistisch | Reduziert auf Wesentliches |

**Design anwenden:**
```
Design → Design wählen → Design auswählen
```

**Design als Standard speichern:**
```
Design → Design-Manager... → "⭐ Als Programmstandard speichern"
```

**Vorteil:** Beim nächsten Programmstart werden diese Einstellungen automatisch geladen.

---

## ⚙️ Konfiguration

Alle Einstellungen werden in `~/.tubaf_scatter_plots/` gespeichert.

### Dateistruktur

```
~/.tubaf_scatter_plots/
├── config.json              # Hauptkonfiguration
│   ├── Benutzer-Metadaten
│   ├── Standard-Plot-Einstellungen
│   └── Sprachwahl
├── color_schemes.json       # Benutzerdefinierte Farbpaletten
├── style_presets.json       # Benutzerdefinierte Stil-Vorlagen
└── logs/                    # Log-Dateien
    └── scatterplot_20251225.log
```

### Benutzer-Metadaten bearbeiten

**Im Programm:**
```
Datei → Benutzer-Metadaten...
```

**Manuell in `config.json`:**
```json
{
  "user_metadata": {
    "author": "Dr. Max Mustermann",
    "institution": "TU Bergakademie Freiberg",
    "email": "max.mustermann@example.com",
    "project": "Nanopartikel-Analyse",
    "description": "SAXS-Messungen an Gold-Nanopartikeln",
    "copyright": "© 2025 Max Mustermann",
    "license": "CC-BY-4.0",
    "keywords": "SAXS, Gold, Nanopartikel"
  }
}
```

### Standard-Einstellungen zurücksetzen

```bash
# Config löschen (Backup empfohlen!)
rm ~/.tubaf_scatter_plots/config.json

# Beim nächsten Start werden Defaults erstellt
```

---



## Lizenz

**GPL-3.0 License**

Dieses Projekt ist unter der GNU General Public License v3.0 lizenziert.

**Was bedeutet das?**
- ✅ Kostenlos verwenden
- ✅ Quellcode einsehen und ändern
- ✅ Weitergeben (unter gleicher Lizenz)
- ❌ Proprietäre Closed-Source-Versionen erstellen

Siehe [LICENSE](LICENSE) für Details.

### Zitation

Wenn Sie ScatterForge Plot in Ihrer Forschung verwenden, zitieren Sie bitte:

```bibtex
@software{scatterforge_plot,
  author = {Richard Neubert},
  title = {ScatterForge Plot: Professional Scattering Data Visualization Tool},
  year = {2026},
  version = {7.0.2},
  url = {https://github.com/traianuschem/ScatteringPlot},
  note = {Software developed with Claude AI assistance}
}
```

### AI Transparency

The program code for ScatterForge Plot v7.0+ was written by Claude (Anthropic's AI assistant) under the orchestration and direction of Richard Neubert. This follows best practices for AI transparency in software development. All features were designed by the project owner, and all code has been thoroughly reviewed, tested, and approved.

## Kontakt & Support

**Issues:** [GitHub Issues](https://github.com/traianuschem/ScatteringPlot/issues)

**Vor dem Erstellen eines Issues:**
1. Log prüfen
2. Issue mit Log-Auszug erstellen

### Autoren

- **Richard Neubert** - *Project owner, orchestration, feature design, testing*
- **Claude (Anthropic AI)** - *Code implementation and development (v7.0+)*

---

## 📚 Weitere Ressourcen

- **CHANGELOG:** Detaillierte Versionshistorie → [CHANGELOG_v7.0.md](CHANGELOG_v7.0.md)
- **GitHub:** Repository → [traianuschem/ScatteringPlot](https://github.com/traianuschem/ScatteringPlot)
- **Releases:** Stabile Versionen → [GitHub Releases](https://github.com/traianuschem/ScatteringPlot/releases)

---

**Made with ❤️ for the scientific community**

*ScatterForge Plot v7.0.4 - Januar 2026*

---
