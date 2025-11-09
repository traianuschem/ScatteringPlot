"""
User Configuration Management für TUBAF Scattering Plot Tool

Verwaltet persistente Einstellungen:
- Farbschemata (eigene + matplotlib)
- Stil-Vorlagen
- Auto-Erkennungs-Regeln
- Letzte Pfade, Einstellungen, etc.
"""

import json
from pathlib import Path
import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm


# User Config Verzeichnis
CONFIG_DIR = Path.home() / ".tubaf_scatter_plots"
CONFIG_FILE = CONFIG_DIR / "config.json"
SCHEMES_FILE = CONFIG_DIR / "color_schemes.json"
STYLES_FILE = CONFIG_DIR / "style_presets.json"


def ensure_config_dir():
    """Stellt sicher, dass das Config-Verzeichnis existiert"""
    CONFIG_DIR.mkdir(exist_ok=True)


def get_matplotlib_colormaps():
    """
    Gibt eine Liste aller verfügbaren matplotlib Colormaps zurück

    Returns:
        dict: {name: [list of hex colors]}
    """
    colormaps = {}

    # Qualitative Colormaps (gut für diskrete Datensätze)
    qualitative = [
        'tab10', 'tab20', 'tab20b', 'tab20c',
        'Set1', 'Set2', 'Set3', 'Paired', 'Accent', 'Pastel1', 'Pastel2', 'Dark2'
    ]

    # Sequential Colormaps
    sequential = [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis',
        'Blues', 'Greens', 'Reds', 'Oranges', 'Purples',
        'YlOrRd', 'YlOrBr', 'YlGnBu', 'RdPu', 'BuPu', 'GnBu'
    ]

    # Diverging Colormaps
    diverging = [
        'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic'
    ]

    all_cmaps = qualitative + sequential + diverging

    for cmap_name in all_cmaps:
        try:
            cmap = cm.get_cmap(cmap_name)
            # 10 Farben aus der Colormap sampeln
            n_colors = 10
            colors = []
            for i in range(n_colors):
                rgba = cmap(i / n_colors)
                # RGBA zu Hex
                hex_color = '#{:02x}{:02x}{:02x}'.format(
                    int(rgba[0] * 255),
                    int(rgba[1] * 255),
                    int(rgba[2] * 255)
                )
                colors.append(hex_color)
            colormaps[cmap_name] = colors
        except:
            pass

    return colormaps


# Standard Stil-Vorlagen
DEFAULT_STYLE_PRESETS = {
    'Messung': {
        'line_style': '',
        'marker_style': 'o',
        'line_width': 1.5,
        'marker_size': 4,
        'description': 'Für Messdaten mit Fehlerbalken'
    },
    'Fit': {
        'line_style': '-',
        'marker_style': '',
        'line_width': 2,
        'marker_size': 0,
        'description': 'Für Fit-Kurven (durchgezogene Linie)'
    },
    'Simulation': {
        'line_style': '--',
        'marker_style': '',
        'line_width': 1.5,
        'marker_size': 0,
        'description': 'Für Simulationen (gestrichelte Linie)'
    },
    'Theorie': {
        'line_style': '-.',
        'marker_style': '',
        'line_width': 1.5,
        'marker_size': 0,
        'description': 'Für theoretische Kurven (Strich-Punkt)'
    }
}


# Standard Auto-Erkennungs-Regeln
DEFAULT_AUTO_DETECTION_RULES = {
    'fit': 'Fit',
    'fitted': 'Fit',
    'anpassung': 'Fit',
    'messung': 'Messung',
    'measurement': 'Messung',
    'measure': 'Messung',
    'data': 'Messung',
    'daten': 'Messung',
    'sim': 'Simulation',
    'simulation': 'Simulation',
    'theo': 'Theorie',
    'theory': 'Theorie',
    'theorie': 'Theorie'
}


class UserConfig:
    """Verwaltet alle User-Einstellungen"""

    def __init__(self):
        ensure_config_dir()
        self.config = self.load_config()
        self.color_schemes = self.load_color_schemes()
        self.style_presets = self.load_style_presets()
        self.plot_designs = self.config.get('plot_designs', {})  # Plot-Designs laden (v5.2+)
        self.auto_detection_rules = self.config.get('auto_detection_rules', DEFAULT_AUTO_DETECTION_RULES.copy())
        self.auto_detection_enabled = self.config.get('auto_detection_enabled', True)

        # Default Plot-Settings (v5.4) - werden beim Programmstart geladen
        self.default_plot_settings = self.config.get('default_plot_settings', {})

    def load_config(self):
        """Lädt die Hauptkonfiguration"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        # Standard-Config
        return {
            'last_directory': str(Path.home()),
            'last_export_directory': str(Path.home()),
            'export_dpi': 300,
            'window_geometry': '1600x1000',
            'auto_detection_enabled': True,
            'auto_detection_rules': DEFAULT_AUTO_DETECTION_RULES.copy(),
            'dark_mode': False
        }

    def save_config(self):
        """Speichert die Hauptkonfiguration"""
        self.config['auto_detection_rules'] = self.auto_detection_rules
        self.config['auto_detection_enabled'] = self.auto_detection_enabled
        self.config['plot_designs'] = self.plot_designs  # Plot-Designs speichern (v5.2+)
        self.config['default_plot_settings'] = self.default_plot_settings  # Default-Settings speichern (v5.4+)

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Config: {e}")

    def save_default_plot_settings(self, legend_settings, grid_settings, font_settings, current_design='Standard'):
        """Speichert aktuelle Plot-Einstellungen als Standard (v5.4)"""
        from utils.logger import get_logger
        logger = get_logger()

        self.default_plot_settings = {
            'legend_settings': legend_settings.copy(),
            'grid_settings': grid_settings.copy(),
            'font_settings': font_settings.copy(),
            'current_plot_design': current_design
        }
        logger.debug(f"UserConfig: Speichere default_plot_settings (Design: {current_design})")
        self.save_config()
        logger.debug("UserConfig: default_plot_settings in config.json gespeichert")

    def get_default_plot_settings(self):
        """Gibt Default-Plot-Settings zurück, oder None falls nicht gesetzt (v5.4)"""
        return self.default_plot_settings if self.default_plot_settings else None

    def load_color_schemes(self):
        """Lädt gespeicherte Farbschemata"""
        schemes = {}

        # TUBAF Standard
        try:
            from tu_freiberg_colors import PRIMARY, SECONDARY, TERTIARY
            schemes['TUBAF'] = [
                PRIMARY['uniblau']['hex'],
                SECONDARY['geo']['hex'],
                SECONDARY['material']['hex'],
                SECONDARY['energie']['hex'],
                SECONDARY['umwelt']['hex'],
                TERTIARY['orange_2']['hex'],
                TERTIARY['gruen_3']['hex'],
                TERTIARY['tuerkis_2']['hex'],
                TERTIARY['rot_6']['hex'],
                TERTIARY['blau_2']['hex'],
            ]
        except:
            schemes['TUBAF'] = ['#0069b4', '#8b7530', '#007b99', '#b71e3f', '#15882e',
                                '#e18409', '#95c11f', '#1e959a', '#cd1222', '#a1d9ef']

        # Matplotlib Colormaps
        schemes.update(get_matplotlib_colormaps())

        # User-definierte Schemata laden
        if SCHEMES_FILE.exists():
            try:
                with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
                    user_schemes = json.load(f)
                    schemes.update(user_schemes)
            except:
                pass

        return schemes

    def save_color_scheme(self, name, colors):
        """Speichert ein neues Farbschema"""
        # Nur user-definierte Schemata speichern (nicht TUBAF oder matplotlib)
        user_schemes = {}
        if SCHEMES_FILE.exists():
            try:
                with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
                    user_schemes = json.load(f)
            except:
                pass

        user_schemes[name] = colors

        try:
            with open(SCHEMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(user_schemes, f, indent=2)

            self.color_schemes[name] = colors
            return True
        except Exception as e:
            print(f"Fehler beim Speichern des Farbschemas: {e}")
            return False

    def delete_color_scheme(self, name):
        """Löscht ein user-definiertes Farbschema"""
        if name in ['TUBAF'] or name in get_matplotlib_colormaps():
            return False  # Standard-Schemata können nicht gelöscht werden

        if SCHEMES_FILE.exists():
            try:
                with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
                    user_schemes = json.load(f)

                if name in user_schemes:
                    del user_schemes[name]

                    with open(SCHEMES_FILE, 'w', encoding='utf-8') as f:
                        json.dump(user_schemes, f, indent=2)

                    if name in self.color_schemes:
                        del self.color_schemes[name]

                    return True
            except:
                pass

        return False

    def load_style_presets(self):
        """Lädt Stil-Vorlagen"""
        if STYLES_FILE.exists():
            try:
                with open(STYLES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        return DEFAULT_STYLE_PRESETS.copy()

    def save_style_presets(self):
        """Speichert Stil-Vorlagen"""
        try:
            with open(STYLES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.style_presets, f, indent=2)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern der Stil-Vorlagen: {e}")
            return False

    def add_style_preset(self, name, style_dict):
        """Fügt eine neue Stil-Vorlage hinzu"""
        self.style_presets[name] = style_dict
        return self.save_style_presets()

    def delete_style_preset(self, name):
        """Löscht eine Stil-Vorlage"""
        if name in self.style_presets:
            del self.style_presets[name]
            return self.save_style_presets()
        return False

    def get_style_by_filename(self, filename):
        """
        Erkennt den Stil anhand des Dateinamens

        Args:
            filename: Dateiname oder Pfad

        Returns:
            dict or None: Stil-Dictionary oder None
        """
        if not self.auto_detection_enabled:
            return None

        filename_lower = Path(filename).stem.lower()

        # Durchsuche Erkennungs-Regeln (erstes Match gewinnt)
        for keyword, style_name in self.auto_detection_rules.items():
            if keyword.lower() in filename_lower:
                if style_name in self.style_presets:
                    return self.style_presets[style_name].copy()

        return None

    def set_last_directory(self, directory):
        """Speichert das zuletzt verwendete Verzeichnis"""
        self.config['last_directory'] = str(directory)
        self.save_config()

    def get_last_directory(self):
        """Gibt das zuletzt verwendete Verzeichnis zurück"""
        return self.config.get('last_directory', str(Path.home()))

    def set_export_dpi(self, dpi):
        """Speichert die Standard-Export-DPI"""
        self.config['export_dpi'] = dpi
        self.save_config()

    def get_export_dpi(self):
        """Gibt die Standard-Export-DPI zurück"""
        return self.config.get('export_dpi', 300)

    def set_dark_mode(self, enabled):
        """Speichert die Dark Mode Einstellung"""
        self.config['dark_mode'] = enabled
        self.save_config()

    def get_dark_mode(self):
        """Gibt die Dark Mode Einstellung zurück"""
        return self.config.get('dark_mode', False)


# Globale Config-Instanz
_user_config = None

def get_user_config():
    """Gibt die globale UserConfig-Instanz zurück"""
    global _user_config
    if _user_config is None:
        _user_config = UserConfig()
    return _user_config
