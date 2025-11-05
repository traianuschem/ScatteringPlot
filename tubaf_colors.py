"""
TUBAF Corporate Design Farbpalette
TU Bergakademie Freiberg

Offizielle Farbdefinitionen nach:
https://tu-freiberg.de/zuv/d5/corporate-design/farbdefinition
"""

# Primärfarben TUBAF
TUBAF_BLUE_DARK = '#003A5D'      # TUBAF Dunkelblau (Hauptfarbe)
TUBAF_BLUE_LIGHT = '#0088CC'     # TUBAF Hellblau
TUBAF_GRAY = '#8C8C8C'           # TUBAF Grau

# Sekundärfarben TUBAF (Bitte anpassen an offizielle Vorgaben!)
TUBAF_GOLD = '#D4AF37'           # Gold (Bergbau-Tradition)
TUBAF_TURQUOISE = '#006666'      # Türkis
TUBAF_RED = '#CC3333'            # Rot
TUBAF_GREEN = '#339933'          # Grün
TUBAF_PURPLE = '#9966CC'         # Violett
TUBAF_ORANGE = '#FF8800'         # Orange
TUBAF_BROWN = '#8B4513'          # Braun

# Standard-Farbpalette für Plots (in Reihenfolge der Verwendung)
TUBAF_COLORS = [
    TUBAF_BLUE_DARK,
    TUBAF_BLUE_LIGHT,
    TUBAF_GOLD,
    TUBAF_RED,
    TUBAF_GREEN,
    TUBAF_TURQUOISE,
    TUBAF_ORANGE,
    TUBAF_PURPLE,
    TUBAF_GRAY,
    TUBAF_BROWN,
]

# Alternative Palette (z.B. für viele Datensätze)
TUBAF_COLORS_EXTENDED = TUBAF_COLORS * 2  # Verdoppelt für mehr Datensätze

# Farbpalette mit Namen (für GUI-Auswahl)
TUBAF_COLOR_NAMES = {
    'Dunkelblau': TUBAF_BLUE_DARK,
    'Hellblau': TUBAF_BLUE_LIGHT,
    'Grau': TUBAF_GRAY,
    'Gold': TUBAF_GOLD,
    'Türkis': TUBAF_TURQUOISE,
    'Rot': TUBAF_RED,
    'Grün': TUBAF_GREEN,
    'Violett': TUBAF_PURPLE,
    'Orange': TUBAF_ORANGE,
    'Braun': TUBAF_BROWN,
}

# Alternative Farbpaletten für spezielle Anwendungen
ALTERNATIVE_PALETTES = {
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
    ],
    'sequential_blue': [
        '#F0F8FF',  # Sehr hell
        '#C6DBEF',
        '#9ECAE1',
        '#6BAED6',
        '#4292C6',
        '#2171B5',
        '#08519C',
        '#08306B',  # Sehr dunkel
    ]
}


def get_color_by_name(name):
    """
    Gibt die Farbe anhand des Namens zurück

    Args:
        name (str): Name der Farbe

    Returns:
        str: Hex-Code der Farbe oder None
    """
    return TUBAF_COLOR_NAMES.get(name, None)


def get_palette(name='default'):
    """
    Gibt eine Farbpalette anhand des Namens zurück

    Args:
        name (str): Name der Palette ('default', 'colorblind_safe', 'vibrant')

    Returns:
        list: Liste von Hex-Farbcodes
    """
    if name == 'default':
        return TUBAF_COLORS
    elif name == 'extended':
        return TUBAF_COLORS_EXTENDED
    else:
        return ALTERNATIVE_PALETTES.get(name, TUBAF_COLORS)
