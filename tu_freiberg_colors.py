"""
TU Bergakademie Freiberg - Corporate Design Farbpalette
=======================================================
Farbdefinitionen für Python-Programme basierend auf dem offiziellen
Corporate Design der TU Bergakademie Freiberg.

Verwendung:
    from tu_freiberg_colors import PRIMARY, SECONDARY, TERTIARY
    
    # Primärfarbe verwenden
    plt.plot(x, y, color=PRIMARY['uniblau']['hex'])
    
    # RGB-Werte für andere Anwendungen
    r, g, b = SECONDARY['geo']['rgb']
"""

# ============================================================================
# PRIMÄRFARBEN
# ============================================================================

PRIMARY = {
    'uniblau': {
        'hex': '#0069b4',
        'rgb': (0, 105, 180),
        'cmyk': (100, 50, 0, 0),
        'description': 'Hausfarbe der TU Bergakademie Freiberg'
    },
    'dunkelblau': {
        'hex': '#00497f',
        'rgb': (0, 73, 127),
        'cmyk': (100, 50, 0, 40),
        'description': 'Zweite Primärfarbe für spannungsvolles Design'
    },
    'schwarz': {
        'hex': '#000000',
        'rgb': (0, 0, 0),
        'cmyk': (0, 0, 0, 100),
        'description': 'Schwarz für Textgestaltung'
    },
    'weiss': {
        'hex': '#ffffff',
        'rgb': (255, 255, 255),
        'cmyk': (0, 0, 0, 0),
        'description': 'Weiß für Textgestaltung'
    }
}


# ============================================================================
# SEKUNDÄRFARBEN / PROFILFARBEN
# ============================================================================

SECONDARY = {
    'geo': {
        'hex': '#8b7530',
        'rgb': (139, 117, 48),
        'cmyk': (20, 30, 80, 45),
        'description': 'Profillinie Geo'
    },
    'geo_invertiert': {
        'hex': '#d5b26b',
        'rgb': (213, 178, 107),
        'cmyk': (20, 30, 65, 0),
        'description': 'Geo invertiert für Barrierefreiheit'
    },
    'material': {
        'hex': '#007b99',
        'rgb': (0, 123, 153),
        'cmyk': (100, 0, 20, 30),
        'description': 'Profillinie Materialien & Werkstoffe'
    },
    'material_invertiert': {
        'hex': '#bee2e9',
        'rgb': (190, 226, 233),
        'cmyk': (30, 0, 10, 0),
        'description': 'Material invertiert für Barrierefreiheit'
    },
    'energie': {
        'hex': '#b71e3f',
        'rgb': (183, 30, 63),
        'cmyk': (30, 100, 70, 0),
        'description': 'Profillinie Energie'
    },
    'energie_invertiert': {
        'hex': '#e5aa94',
        'rgb': (229, 170, 148),
        'cmyk': (10, 40, 40, 0),
        'description': 'Energie invertiert für Barrierefreiheit'
    },
    'umwelt': {
        'hex': '#15882e',
        'rgb': (21, 136, 46),
        'cmyk': (80, 0, 100, 25),
        'description': 'Profillinie Umwelt'
    },
    'umwelt_invertiert': {
        'hex': '#b5d8af',
        'rgb': (181, 216, 175),
        'cmyk': (35, 0, 40, 0),
        'description': 'Umwelt invertiert für Barrierefreiheit'
    }
}


# ============================================================================
# TERTIÄRFARBEN / AKZENTFARBEN
# ============================================================================

TERTIARY = {
    # Blautöne
    'blau_1': {'hex': '#68a8c2', 'rgb': (104, 168, 194), 'cmyk': (52, 0, 4, 25)},
    'blau_2': {'hex': '#a1d9ef', 'rgb': (162, 217, 239), 'cmyk': (40, 0, 5, 0)},
    'blau_3': {'hex': '#16bae7', 'rgb': (22, 186, 231), 'cmyk': (70, 0, 5, 0)},
    
    # Brauntöne
    'braun_1': {'hex': '#473624', 'rgb': (71, 54, 36), 'cmyk': (45, 55, 70, 70)},
    'braun_2': {'hex': '#6a5944', 'rgb': (106, 89, 68), 'cmyk': (40, 45, 60, 50)},
    'braun_3': {'hex': '#a58c55', 'rgb': (165, 140, 85), 'cmyk': (20, 30, 65, 30)},
    
    # Gelbtöne
    'gelb_1': {'hex': '#ffd962', 'rgb': (255, 217, 98), 'cmyk': (0, 15, 70, 0)},
    'gelb_2': {'hex': '#ffdd9e', 'rgb': (255, 221, 158), 'cmyk': (0, 15, 45, 0)},
    'gelb_3': {'hex': '#fff3d8', 'rgb': (255, 243, 216), 'cmyk': (0, 5, 20, 0)},
    
    # Grautöne
    'grau_1': {'hex': '#a59e89', 'rgb': (165, 158, 137), 'cmyk': (30, 25, 40, 20)},
    'grau_2': {'hex': '#beb293', 'rgb': (190, 178, 147), 'cmyk': (20, 20, 40, 15)},
    'grau_3': {'hex': '#eadac5', 'rgb': (234, 218, 197), 'cmyk': (10, 15, 25, 0)},
    
    # Grüntöne
    'gruen_1': {'hex': '#147069', 'rgb': (20, 112, 105), 'cmyk': (80, 20, 50, 35)},
    'gruen_2': {'hex': '#449d89', 'rgb': (68, 157, 137), 'cmyk': (70, 10, 50, 10)},
    'gruen_3': {'hex': '#95c11f', 'rgb': (149, 193, 31), 'cmyk': (50, 0, 100, 0)},
    'gruen_4': {'hex': '#8fc297', 'rgb': (143, 194, 151), 'cmyk': (50, 5, 50, 0)},
    
    # Orangetöne
    'orange_1': {'hex': '#e6733c', 'rgb': (230, 115, 60), 'cmyk': (5, 65, 80, 0)},
    'orange_2': {'hex': '#e18409', 'rgb': (225, 132, 9), 'cmyk': (10, 55, 100, 0)},
    'orange_3': {'hex': '#f39433', 'rgb': (243, 148, 51), 'cmyk': (0, 50, 85, 0)},
    
    # Rottöne
    'rot_1': {'hex': '#521813', 'rgb': (82, 24, 19), 'cmyk': (30, 90, 75, 70)},
    'rot_2': {'hex': '#6d0f0e', 'rgb': (109, 15, 14), 'cmyk': (15, 100, 85, 60)},
    'rot_3': {'hex': '#8b2822', 'rgb': (139, 40, 34), 'cmyk': (20, 90, 85, 40)},
    'rot_4': {'hex': '#a96e54', 'rgb': (169, 110, 84), 'cmyk': (20, 55, 60, 25)},
    'rot_5': {'hex': '#a83e1c', 'rgb': (168, 62, 28), 'cmyk': (10, 80, 90, 30)},
    'rot_6': {'hex': '#cd1222', 'rgb': (205, 18, 34), 'cmyk': (10, 100, 90, 5)},
    
    # Türkistöne
    'tuerkis_1': {'hex': '#528287', 'rgb': (82, 130, 135), 'cmyk': (65, 25, 35, 25)},
    'tuerkis_2': {'hex': '#1e959a', 'rgb': (30, 149, 154), 'cmyk': (75, 10, 35, 15)},
    'tuerkis_3': {'hex': '#66c1bf', 'rgb': (102, 193, 191), 'cmyk': (60, 0, 30, 0)},
    'tuerkis_4': {'hex': '#88cdd3', 'rgb': (136, 205, 211), 'cmyk': (50, 0, 20, 0)}
}


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def get_rgb_normalized(color_dict):
    """
    Gibt RGB-Werte normalisiert (0-1) zurück für Matplotlib.
    
    Args:
        color_dict: Dictionary mit 'rgb' key
        
    Returns:
        tuple: (r, g, b) mit Werten zwischen 0 und 1
    """
    r, g, b = color_dict['rgb']
    return (r/255, g/255, b/255)


def get_all_hex_colors():
    """
    Gibt alle Hex-Farbwerte als flache Liste zurück.
    
    Returns:
        list: Liste aller Hex-Farbcodes
    """
    colors = []
    for category in [PRIMARY, SECONDARY, TERTIARY]:
        colors.extend([color['hex'] for color in category.values()])
    return colors


def get_profile_colors():
    """
    Gibt die vier Profilfarben zurück (Geo, Material, Energie, Umwelt).
    
    Returns:
        dict: Dictionary mit Profilfarben
    """
    return {
        'geo': SECONDARY['geo']['hex'],
        'material': SECONDARY['material']['hex'],
        'energie': SECONDARY['energie']['hex'],
        'umwelt': SECONDARY['umwelt']['hex']
    }


def print_color_palette():
    """Druckt eine Übersicht aller Farben."""
    print("=" * 70)
    print("TU Bergakademie Freiberg - Farbpalette")
    print("=" * 70)
    
    print("\nPRIMÄRFARBEN:")
    print("-" * 70)
    for name, color in PRIMARY.items():
        print(f"{name:20} | HEX: {color['hex']:7} | RGB: {str(color['rgb']):15}")
    
    print("\nSEKUNDÄRFARBEN / PROFILFARBEN:")
    print("-" * 70)
    for name, color in SECONDARY.items():
        print(f"{name:20} | HEX: {color['hex']:7} | RGB: {str(color['rgb']):15}")
    
    print("\nTERTIÄRFARBEN / AKZENTFARBEN:")
    print("-" * 70)
    for name, color in TERTIARY.items():
        print(f"{name:20} | HEX: {color['hex']:7} | RGB: {str(color['rgb']):15}")


# ============================================================================
# BEISPIELVERWENDUNG
# ============================================================================

if __name__ == "__main__":
    print_color_palette()
    
    print("\n" + "=" * 70)
    print("BEISPIELE:")
    print("=" * 70)
    
    # Beispiel 1: Primärfarbe
    print(f"\nUniblau (Hausfarbe): {PRIMARY['uniblau']['hex']}")
    print(f"RGB: {PRIMARY['uniblau']['rgb']}")
    print(f"Normalisiert für Matplotlib: {get_rgb_normalized(PRIMARY['uniblau'])}")
    
    # Beispiel 2: Profilfarben
    print("\nProfilfarben:")
    for name, hex_color in get_profile_colors().items():
        print(f"  {name}: {hex_color}")
    
    # Beispiel 3: Akzentfarben
    print(f"\nAkzentfarbe Orange 2: {TERTIARY['orange_2']['hex']}")
