# Changelog — Version 7.1

## Version 7.1.1 — ScatterForge Plot (RELEASE)

**Release Date:** 29. April 2026  
**Status:** Stable Release — Quality Updates for 2D Analysis

### ✨ Neue Features & Verbesserungen (7.1.1)

#### 1. Farbskala-Schieberegler für q-Map und Polar Map (Commit: 166f6d5)

- Zwei horizontale Perzentil-Schieberegler (0–100 %) je 2D-Ansicht für `vmin` und `vmax`
- Norm-Update direkt via `im.set_norm()` + `colorbar.update_normal()` — kein teures Neuberechnen des Histogramms
- Aktuelle Intensitätswerte werden live unter den Slidern angezeigt
- „⟳ Auto (1 %–99 %)"-Button setzt beide Slider in einen wissenschaftlich sinnvollen Bereich zurück
- Separate, unabhängige Slider für q-Map und Polar Map
- Dateien: `dialogs/plot2d_dialog.py`

#### 2. Export über bestehenden ExportSettingsDialog (Commit: 166f6d5)

- PNG-Export des 2D-Dialogs routet jetzt durch den gemeinsamen `ExportSettingsDialog`
- Metadaten (Autor, Institution, Lizenz, Keywords), DPI, Größe und Format-Optionen konsistent mit 1D-Export
- Polar-Map-Seite: Checkbox **„Overlay beim Export einblenden"** — Selektor-Linien, Band und Labels können beim Export wahlweise aus- oder eingeblendet werden
- Fallback auf einfachen Dateidialog wenn `ExportSettingsDialog` nicht verfügbar
- Dateien: `dialogs/plot2d_dialog.py`

#### 3. sin(φ)-Korrektur für das Azimutalprofil (Commit: 166f6d5)

Checkable QGroupBox mit vollständiger Pole-Behandlung:

**Operationen:**
- **I / sin(φ)** — Lorentz-Korrektur für gleichmäßige Raumwinkel-Dichte (Orientierungsverteilungsfunktion)
- **I · sin(φ)** — Jacobi-Gewichtung für Integration über Kugeloberfläche (Hermans-Orientierungsfaktor)

**Polbehandlung (nur für Division):**
- **Maskierung (NaN)** — Werte innerhalb der konfigurierbaren Pol-Schwelle (Standard 5°) werden auf NaN gesetzt
- **Epsilon-Clamp** — Nenner wird auf sin(0,5°) nach unten geclampt; kein Divergenz-Crash
- **Voigt-Extrapolation** — Pseudo-Voigt-Fit (Kombination Gauss + Lorentz) an den Flanken [thresh, 3·thresh]° beider Pole; Extrapolation in den maskierten Bereich; deaktiviert wenn scipy fehlt

Die angewendete Korrektur erscheint im Y-Achsen-Label und im ASCII-Export-Header.

- `scipy>=1.7.0` zu `requirements.txt` hinzugefügt
- Dateien: `dialogs/plot2d_dialog.py`, `requirements.txt`, `i18n/translations/en.json`, `i18n/translations/de.json`

#### 4. Farbbalken im Dark-Theme korrekt weiß (Commit: ea75916)

- Neue Hilfsfunktion `_style_cbar()` setzt Tick-Labels, Achsen-Label und Spines der Colorbar-Axes auf das dunkle Farbschema
- Aufruf nach Ersterzeugung und nach jedem Slider-Update (`update_normal`)
- Dateien: `dialogs/plot2d_dialog.py`

### 🔑 Neue i18n-Keys (7.1.1)

```
2d.polar_export_overlay   2d.cmap_range_group   2d.cmap_auto_reset
2d.sin_corr_group         2d.sin_corr_divide    2d.sin_corr_multiply
2d.sin_corr_pole_handling 2d.sin_corr_pole_mask 2d.sin_corr_pole_clamp
2d.sin_corr_pole_voigt    2d.sin_corr_pole_threshold
```

---

## Version 7.1.0 — ScatterForge Plot (RELEASE)

**Release Date:** 29. April 2026  
**Status:** Stable Release — Großer Feature-Release: 2D SAXS Viewer

### 🎉 Hauptfeature: Vollständiger 2D-Detektor-Analyzer

ScatterForge Plot kann jetzt prozessierte 2D-Detektordaten im NeXus/HDF5-Format laden und analysieren. Die komplette Auswertekette — von der rohen Detektoraufnahme bis zum übertragbaren 1D-Profil — ist in einem nicht-modalen Dialog integriert.

#### Neue Dateien

| Datei | Beschreibung |
|-------|--------------|
| `utils/nexus_loader.py` | HDF5/h5z IO-Layer: liest NeXus-Dateien, konvertiert m⁻¹ → nm⁻¹, maskiert Pixel |
| `dialogs/plot2d_dialog.py` | Vollständiger nicht-modaler 2D-Analyse-Dialog mit 4 Ansichten |

#### Geänderte Dateien

| Datei | Änderungen |
|-------|------------|
| `core/models.py` | `Dataset2D`-Klasse mit allen Analysemethoden |
| `scatter_plot.py` | „🔬 Load 2D (HDF5)"-Button, Tree-Sektion, Dialog-Aufruf, Session-Persistenz |
| `i18n/translations/en.json` | Kompletter `"2d"`-Block + `"tree.section_2d"` |
| `i18n/translations/de.json` | Dt. Übersetzungen für alle 2D-Keys |
| `requirements.txt` | `h5py>=3.0` hinzugefügt |

#### Features im Detail (Commit: 47b84f9)

**Dateiformat-Unterstützung:**
- `.h5` (direkt via h5py)
- `.h5z` (ZIP-komprimiertes HDF5, automatische Extraktion)
- Auto-Erkennung m⁻¹ → nm⁻¹ (wenn Median |q| > 10⁴)
- Pixel-Maske aus `/entry/instrument/detector/pixel_mask`

**4 Analyseansichten:**

| Ansicht | Achsen | Methode |
|---------|--------|---------|
| q-Map (Kartesisch) | qx / qy | `generate_cartesian_map()` |
| Polarkarte | φ / \|q\| (log) | `generate_polar_map()` |
| Azimutalprofil | φ | `azimuthal_profile()` |
| Sektor-Integral | \|q\| | `sector_integral()` |

**Interaktiver q-Ring-Selektor (Commit: e79e359):**
- Zwei ziehbare horizontale Linien (Cyan = q_lo, Orange = q_hi) + schattiertes Band in der Polarkarte
- Pixel-genaues Hit-Testing im Log-Maßstab via `ax.transData.transform`
- Live-Update von Linie, Band, Annotation-Labels und Status-Labels im Parameterpanel
- Cursor wechselt auf `SizeVerCursor` beim Hover über eine Linie
- „→ Azimutales Profil"-Button übernimmt die Drag-Werte direkt
- Bidirektionale Synchronisation: Drag → Spinbox, Spinbox → Linie

**1D-Projektionstransfer:**
- Azimutalprofil und Sektor-Integral können per „Add to 1D Plot" direkt in den 1D-Datensatz-Baum übernommen werden
- Signal `projection_ready(DataSet)` → `add_projection_to_tree()` im Hauptfenster

**Export:**
- PNG/SVG/PDF/EPS/TIFF aus dem 2D-Dialog
- ASCII `.dat` für Azimutalprofil (2 Spalten) und Sektor-Integral (3 Spalten, mit σ)

**Session-Persistenz:**
- `Dataset2D.to_dict()` / `from_dict()`: speichert Dateipfad und Metadaten, lädt Daten beim nächsten Start nach

### 🔑 Neue i18n-Keys (7.1.0)

Kompletter `"2d"`-Block mit 20+ Keys sowie `"tree.section_2d"`.

### 📦 Neue Abhängigkeit

```
h5py>=3.0
```

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, Fachanalyse (SAXS), Testing und Qualitätssicherung

**AI Transparency Notice:**  
Der Programmcode für ScatterForge Plot v7.1 wurde von Claude (Anthropic AI) unter der Leitung und Orchestrierung von Richard Neubert geschrieben. Die fachliche Analyse der SAXS-Datenformate und die physikalische Spezifikation aller Auswertealgorithmen (Polarkarte, Azimutalprofil, sin(φ)-Korrektur) stammen vom Projektinhaber.

---

*Letzte Aktualisierung: 2026-04-29*
