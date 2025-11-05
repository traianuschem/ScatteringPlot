"""
Konfigurationsdatei für das Scattering Plot Tool
Enthält TUBAF-Farbdefinitionen und weitere Einstellungen
"""

# TUBAF Corporate Design Farben
# HINWEIS: Diese Farbpalette ist ein Platzhalter und sollte mit den
# offiziellen TUBAF-Farben aktualisiert werden
# Siehe: https://tu-freiberg.de/zuv/d5/corporate-design/farbdefinition

# Standard TUBAF Farben (Beispiel - bitte anpassen!)
TUBAF_COLORS = [
    '#003A5D',  # TUBAF Dunkelblau (Primärfarbe)
    '#0088CC',  # TUBAF Hellblau
    '#8C8C8C',  # Grau
    '#D4AF37',  # Gold (Bergbau-Tradition)
    '#006666',  # Türkis
    '#CC3333',  # Rot
    '#339933',  # Grün
    '#9966CC',  # Violett
]

# Alternative Farbpaletten (falls benötigt)
ALTERNATIVE_COLORS = {
    'colorblind_safe': [
        '#0173B2',  # Blau
        '#DE8F05',  # Orange
        '#029E73',  # Grün
        '#CC78BC',  # Rosa
        '#CA9161',  # Braun
        '#FBAFE4',  # Pink
        '#949494',  # Grau
        '#ECE133',  # Gelb
    ],
    'vibrant': [
        '#EE7733',  # Orange
        '#0077BB',  # Blau
        '#33BBEE',  # Cyan
        '#EE3377',  # Magenta
        '#CC3311',  # Rot
        '#009988',  # Teal
        '#BBBBBB',  # Grau
    ]
}

# Plot-Einstellungen
DEFAULT_FIGSIZE = (10, 8)
DEFAULT_DPI = 100
DEFAULT_FONT_SIZE = 12
DEFAULT_LINE_WIDTH = 2
DEFAULT_MARKER_SIZE = 4
ERROR_ALPHA = 0.2  # Transparenz für Fehlerbereich

# Datei-Einstellungen
SUPPORTED_EXTENSIONS = ['.txt', '.dat', '.csv', '.asc']
DEFAULT_DELIMITER = None  # Automatische Erkennung

# GUI-Einstellungen
WINDOW_TITLE = "TUBAF Scattering Plot Tool"
WINDOW_SIZE = "1400x900"
