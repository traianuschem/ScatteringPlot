"""
Data models for TUBAF Scattering Plot Tool

This module contains the core data models:
- DataSet: Represents a single dataset with style information
- DataGroup: Represents a group of datasets with stack factor
"""

from pathlib import Path
from utils.data_loader import load_scattering_data
from utils.user_config import get_user_config


class DataSet:
    """Datensatz mit Stil-Informationen"""
    def __init__(self, filepath, name=None, apply_auto_style=True):
        self.filepath = Path(filepath)
        self.name = name or self.filepath.stem
        self.display_label = self.name
        self.data = None
        self.x = None
        self.y = None
        self.y_err = None

        # Stil
        self.line_style = None
        self.marker_style = None
        self.color = None
        self.line_width = 2
        self.marker_size = 4
        self.show_in_legend = True
        self.legend_bold = False
        self.legend_italic = False

        # Fehlerbalken (v6.0)
        self.show_errorbars = True
        self.errorbar_style = 'fill'  # 'bars' oder 'fill' (transparente Fläche)
        self.errorbar_capsize = 3
        self.errorbar_alpha = 0.3  # Für fill_between
        self.errorbar_linewidth = 1.0

        # Individuelle Plotgrenzen (v5.7)
        self.x_min = None
        self.x_max = None
        self.y_min = None
        self.y_max = None

        self.load_data()

        # Auto-Stil anwenden
        if apply_auto_style:
            self.apply_auto_style()

    def load_data(self):
        """Lädt Daten"""
        try:
            self.data = load_scattering_data(self.filepath)
            self.x = self.data[:, 0]
            self.y = self.data[:, 1]
            if self.data.shape[1] > 2:
                self.y_err = self.data[:, 2]
        except Exception as e:
            raise ValueError(f"Fehler beim Laden von {self.filepath}: {e}")

    def apply_auto_style(self):
        """Wendet automatisch erkannten Stil an"""
        config = get_user_config()
        style = config.get_style_by_filename(self.filepath)
        if style:
            self.line_style = style.get('line_style')
            self.marker_style = style.get('marker_style')
            self.line_width = style.get('line_width', 2)
            self.marker_size = style.get('marker_size', 4)
            # Fehlerbalken-Einstellungen (v6.0)
            if 'errorbar_style' in style:
                self.errorbar_style = style.get('errorbar_style', 'fill')
            if 'errorbar_alpha' in style:
                self.errorbar_alpha = style.get('errorbar_alpha', 0.3)

    def apply_style_preset(self, preset_name):
        """Wendet Stil-Vorlage an"""
        config = get_user_config()
        if preset_name in config.style_presets:
            style = config.style_presets[preset_name]
            self.line_style = style.get('line_style')
            self.marker_style = style.get('marker_style')
            self.line_width = style.get('line_width', 2)
            self.marker_size = style.get('marker_size', 4)
            # Fehlerbalken-Einstellungen (v6.0)
            if 'errorbar_style' in style:
                self.errorbar_style = style.get('errorbar_style', 'fill')
            if 'errorbar_alpha' in style:
                self.errorbar_alpha = style.get('errorbar_alpha', 0.3)

    def get_plot_style(self):
        """Gibt Plot-Stil zurück"""
        line = self.line_style if self.line_style else ''
        marker = self.marker_style if self.marker_style else ''
        if not line and not marker:
            # Auto: Fit=Linie, sonst Marker
            if 'fit' in self.name.lower():
                return '-'
            return 'o'
        return line + marker

    def to_dict(self):
        """Serialisierung"""
        return {
            'filepath': str(self.filepath),
            'name': self.name,
            'display_label': self.display_label,
            'line_style': self.line_style,
            'marker_style': self.marker_style,
            'color': self.color,
            'line_width': self.line_width,
            'marker_size': self.marker_size,
            'show_in_legend': self.show_in_legend,
            'legend_bold': self.legend_bold,
            'legend_italic': self.legend_italic,
            'show_errorbars': self.show_errorbars,
            'errorbar_style': self.errorbar_style,
            'errorbar_capsize': self.errorbar_capsize,
            'errorbar_alpha': self.errorbar_alpha,
            'errorbar_linewidth': self.errorbar_linewidth,
            'x_min': self.x_min,
            'x_max': self.x_max,
            'y_min': self.y_min,
            'y_max': self.y_max
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialisierung"""
        ds = cls(data['filepath'], data.get('name'), apply_auto_style=False)
        ds.display_label = data.get('display_label', ds.name)
        ds.line_style = data.get('line_style')
        ds.marker_style = data.get('marker_style')
        ds.color = data.get('color')
        ds.line_width = data.get('line_width', 2)
        ds.marker_size = data.get('marker_size', 4)
        ds.show_in_legend = data.get('show_in_legend', True)
        ds.legend_bold = data.get('legend_bold', False)
        ds.legend_italic = data.get('legend_italic', False)
        ds.show_errorbars = data.get('show_errorbars', True)
        ds.errorbar_style = data.get('errorbar_style', 'fill')
        ds.errorbar_capsize = data.get('errorbar_capsize', 3)
        ds.errorbar_alpha = data.get('errorbar_alpha', 0.3)
        ds.errorbar_linewidth = data.get('errorbar_linewidth', 1.0)
        ds.x_min = data.get('x_min')
        ds.x_max = data.get('x_max')
        ds.y_min = data.get('y_min')
        ds.y_max = data.get('y_max')
        return ds


class DataGroup:
    """Datengruppe"""
    def __init__(self, name, stack_factor=1.0, color_scheme=None):
        self.name = name
        self.datasets = []
        self.stack_factor = stack_factor
        self.visible = True
        self.collapsed = False
        self.color_scheme = color_scheme  # Optional: Gruppenspezifische Farbpalette
        self.show_in_legend = True
        self.legend_bold = False
        self.legend_italic = False
        self.display_label = name

    def add_dataset(self, dataset):
        """Datensatz hinzufügen"""
        self.datasets.append(dataset)

    def remove_dataset(self, dataset):
        """Datensatz entfernen"""
        if dataset in self.datasets:
            self.datasets.remove(dataset)

    def to_dict(self):
        """Serialisierung"""
        return {
            'name': self.name,
            'stack_factor': self.stack_factor,
            'visible': self.visible,
            'collapsed': self.collapsed,
            'color_scheme': self.color_scheme,
            'show_in_legend': self.show_in_legend,
            'legend_bold': self.legend_bold,
            'legend_italic': self.legend_italic,
            'display_label': self.display_label,
            'datasets': [ds.to_dict() for ds in self.datasets]
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialisierung"""
        group = cls(data['name'], data.get('stack_factor', 1.0), data.get('color_scheme'))
        group.visible = data.get('visible', True)
        group.collapsed = data.get('collapsed', False)
        group.show_in_legend = data.get('show_in_legend', True)
        group.legend_bold = data.get('legend_bold', False)
        group.legend_italic = data.get('legend_italic', False)
        group.display_label = data.get('display_label', group.name)
        group.datasets = [DataSet.from_dict(ds_data) for ds_data in data.get('datasets', [])]
        return group
