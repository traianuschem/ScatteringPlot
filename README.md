# TUBAF Scattering Plot Tool - Version 4.2 (Qt)

Professionelles Tool für Streudaten-Analyse mit moderner Qt6-GUI.

## 🆕 Was ist neu in Version 4.0?

**Komplette GUI-Umstellung auf Qt6:**
- ✅ Moderne, native Qt6-Oberfläche
- ✅ Professioneller Dark Mode Support (Fusion Style)
- ✅ Bessere Performance und Stabilität
- ✅ Natives Look & Feel auf allen Plattformen
- ✅ Verbesserte High-DPI Support
- ✅ Modernere Dialoge und Widgets

**Features bleiben erhalten:**
- Verschiedene Plot-Typen (Log-Log, Porod, Kratky, Guinier, PDDF)
- Stil-Vorlagen und Auto-Erkennung
- Farbschema-Manager (TUBAF + 30+ matplotlib Colormaps)
- Drag & Drop für Datensätze
- Session-Verwaltung (speichern/laden)
- Export als PNG/SVG

## 📦 Installation

### Voraussetzungen
- Python 3.8 oder höher
- pip

### Dependencies installieren

```bash
pip install -r requirements.txt
```

Dies installiert:
- PySide6 (Qt6 für Python)
- numpy
- matplotlib

## 🚀 Start

```bash
python3 scatter_plot.py
```

## 🎨 Dark Mode

Dark Mode kann über **Design → 🌙 Dark Mode umschalten** aktiviert/deaktiviert werden.

**Hinweis:** Die Plots bleiben im Light Mode für bessere Lesbarkeit und Publikations-Qualität.

## 📂 Migration von Version 3.0

Sessions, die in Version 3.0 (Tkinter) gespeichert wurden, sind kompatibel mit Version 4.0 (Qt).

**Backup:** Die alte Tkinter-Version wurde als `scatter_plot_v3_tkinter_backup.py` gesichert.

## 🔧 Konfiguration

Alle Einstellungen werden gespeichert in:
```
~/.tubaf_scatter_plots/
├── config.json
├── color_schemes.json
└── style_presets.json
```

## 📝 Verwendung

1. **Daten laden:** Datei → Daten laden... oder 📁-Button
2. **Gruppen erstellen:** ➕ Gruppe Button
3. **Datensätze zuordnen:** Drag & Drop aus "Nicht zugeordnet"
4. **Plot anpassen:** Optionen-Panel links
5. **Export:** Datei → PNG/SVG Export

## 🛠️ Entwicklung

**Tkinter vs Qt:**
- Version 1-3: Tkinter (in Python enthalten)
- Version 4+: Qt6/PySide6 (moderne GUI Framework)

**Vorteile von Qt:**
- Native Dark Mode Support
- Professionelleres Aussehen
- Bessere Widgets (QTreeWidget, QSplitter, etc.)
- Standard in wissenschaftlicher Software
- Aktive Entwicklung

## 📄 Lizenz

TU Bergakademie Freiberg

---

**Version:** 4.0  
**Datum:** November 2025  
**Framework:** Qt6 (PySide6)
