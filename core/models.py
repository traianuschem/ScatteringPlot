"""
Data models for TUBAF Scattering Plot Tool

This module contains the core data models:
- DataSet: Represents a single dataset with style information
- DataGroup: Represents a group of datasets with stack factor
- Dataset2D: Represents a 2D SAXS dataset (NeXus/HDF5)
"""

from pathlib import Path
import logging
import numpy as np
from utils.data_loader import load_scattering_data
from utils.user_config import get_user_config


class DataSet:
    """Datensatz mit Stil-Informationen"""
    def __init__(self, filepath, name=None, apply_auto_style=True, skip_load=False,
                 filter_nonpositive=True):
        self.filepath = Path(filepath)
        self.name = name or self.filepath.stem
        self.display_label = self.name
        self.data = None
        self.x = None
        self.y = None
        self.y_err = None
        self.data_loaded = False  # Flag für erfolgreiches Laden
        # Wenn False, werden x≤0/y≤0-Werte beim Laden NICHT gefiltert.
        # Notwendig für azimutale Profile (φ < 0) und andere lineare Daten.
        self.filter_nonpositive = filter_nonpositive

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

        if not skip_load:
            self.load_data()

        # Auto-Stil anwenden
        if apply_auto_style:
            self.apply_auto_style()

    def load_data(self, raise_on_error=True):
        """Lädt Daten

        Args:
            raise_on_error: Wenn False, werden Fehler nur geloggt statt Exception zu werfen
        """
        logger = logging.getLogger(__name__)
        try:
            self.data = load_scattering_data(
                self.filepath,
                filter_nonpositive=getattr(self, 'filter_nonpositive', True)
            )
            self.x = self.data[:, 0]
            self.y = self.data[:, 1]
            if self.data.shape[1] > 2:
                self.y_err = self.data[:, 2]
            self.data_loaded = True
        except Exception as e:
            error_msg = f"Fehler beim Laden von {self.filepath}: {e}"
            if raise_on_error:
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)
                self.data_loaded = False

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
            'y_max': self.y_max,
            'filter_nonpositive': self.filter_nonpositive
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialisierung mit Fehlertoleranz für fehlende Dateien"""
        # Dataset ohne Daten laden erstellen (skip_load=True)
        ds = cls(data['filepath'], data.get('name'), apply_auto_style=False, skip_load=True,
                 filter_nonpositive=data.get('filter_nonpositive', True))
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

        # Versuche Daten zu laden, aber ignoriere Fehler (z.B. fehlende Dateien)
        ds.load_data(raise_on_error=False)

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


class Dataset2D:
    """2D SAXS dataset loaded from a NeXus/HDF5 file (.h5 or .h5z)."""

    def __init__(self, filepath, name=None):
        self.filepath = Path(filepath)
        self.name = name or self.filepath.stem
        self.display_label = self.name
        self.qx: np.ndarray | None = None  # nm⁻¹, valid pixels only
        self.qy: np.ndarray | None = None  # nm⁻¹
        self.I: np.ndarray | None = None
        self.metadata: dict = {}
        self.data_loaded = False

    # ── Loading ──────────────────────────────────────────────────────────────

    def load_data(self, raise_on_error=True):
        from utils.nexus_loader import read_nexus_2d
        logger = logging.getLogger(__name__)
        try:
            result = read_nexus_2d(self.filepath)
            self.qx = result['qx']
            self.qy = result['qy']
            self.I = result['I']
            self.metadata = result['metadata']
            self.data_loaded = True
            logger.debug(f"Dataset2D loaded: {self.name} ({len(self.I)} valid pixels)")
        except Exception as e:
            msg = f"Fehler beim Laden von {self.filepath}: {e}"
            if raise_on_error:
                raise ValueError(msg)
            else:
                logger.warning(msg)
                self.data_loaded = False

    # ── Analysis methods ─────────────────────────────────────────────────────

    def generate_cartesian_map(self, bins: int = 600):
        """
        Bin (qx, qy, I) onto a regular cartesian grid.
        Returns (qx_edges, qy_edges, H) where H[i,j] is the mean intensity,
        NaN for empty bins.
        """
        H, qx_e, qy_e = np.histogram2d(
            self.qx, self.qy, bins=bins, weights=self.I
        )
        counts, _, _ = np.histogram2d(self.qx, self.qy, bins=[qx_e, qy_e])
        with np.errstate(invalid='ignore'):
            H = np.where(counts > 0, H / counts, np.nan)
        return qx_e, qy_e, H.T  # transpose so (row=qy, col=qx) for imshow

    def generate_polar_map(self, q_bins: int = 300, phi_bins: int = 360, log_q: bool = True):
        """
        Bin I(|q|, φ) onto a polar grid.
        Returns (q_edges, phi_edges, H) with H[i,j] mean intensity,
        phi in degrees [-180, 180], |q| in nm⁻¹ (log-spaced if log_q).
        """
        q = np.sqrt(self.qx**2 + self.qy**2)
        phi = np.degrees(np.arctan2(self.qy, self.qx))  # [-180, 180]

        q_pos = q > 0
        if not np.any(q_pos):
            raise ValueError("No valid q > 0 pixels for polar map")

        q_min = np.nanmin(q[q_pos])
        q_max = np.nanmax(q[q_pos])

        if log_q and q_min > 0:
            q_edges = np.logspace(np.log10(q_min), np.log10(q_max), q_bins + 1)
        else:
            q_edges = np.linspace(q_min, q_max, q_bins + 1)

        phi_edges = np.linspace(-180, 180, phi_bins + 1)

        H, _, _ = np.histogram2d(q, phi, bins=[q_edges, phi_edges], weights=self.I)
        counts, _, _ = np.histogram2d(q, phi, bins=[q_edges, phi_edges])
        with np.errstate(invalid='ignore'):
            H = np.where(counts > 0, H / counts, np.nan)

        return q_edges, phi_edges, H  # H[i_q, i_phi]

    def azimuthal_profile(self, q_lo: float, q_hi: float, phi_bins: int = 360):
        """
        Integrate I over the q-ring [q_lo, q_hi] as a function of φ.
        Returns (phi_centers [deg], I_mean).
        """
        q = np.sqrt(self.qx**2 + self.qy**2)
        mask = (q >= q_lo) & (q <= q_hi)
        if not np.any(mask):
            raise ValueError(f"No pixels in q-ring [{q_lo:.3f}, {q_hi:.3f}] nm⁻¹")

        phi = np.degrees(np.arctan2(self.qy[mask], self.qx[mask]))
        I_ring = self.I[mask]

        phi_edges = np.linspace(-180, 180, phi_bins + 1)
        H, _ = np.histogram(phi, bins=phi_edges, weights=I_ring)
        counts, _ = np.histogram(phi, bins=phi_edges)
        with np.errstate(invalid='ignore'):
            I_mean = np.where(counts > 0, H / counts, np.nan)

        phi_centers = 0.5 * (phi_edges[:-1] + phi_edges[1:])
        return phi_centers, I_mean

    def sector_integral(self, phi_lo: float, phi_hi: float, q_bins: int = 300, log_q: bool = True):
        """
        Integrate I over the azimuthal sector [phi_lo, phi_hi] as a function of |q|.
        phi in degrees.  Returns (q_centers [nm⁻¹], I_mean, I_std).
        """
        q = np.sqrt(self.qx**2 + self.qy**2)
        phi = np.degrees(np.arctan2(self.qy, self.qx))

        # Handle sector that wraps around ±180°
        if phi_lo <= phi_hi:
            mask = (phi >= phi_lo) & (phi <= phi_hi) & (q > 0)
        else:
            mask = ((phi >= phi_lo) | (phi <= phi_hi)) & (q > 0)

        if not np.any(mask):
            raise ValueError(f"No pixels in sector [{phi_lo:.1f}°, {phi_hi:.1f}°]")

        q_sec = q[mask]
        I_sec = self.I[mask]

        q_min = np.nanmin(q_sec)
        q_max = np.nanmax(q_sec)

        if log_q and q_min > 0:
            q_edges = np.logspace(np.log10(q_min), np.log10(q_max), q_bins + 1)
        else:
            q_edges = np.linspace(q_min, q_max, q_bins + 1)

        H, _ = np.histogram(q_sec, bins=q_edges, weights=I_sec)
        counts, _ = np.histogram(q_sec, bins=q_edges)
        H2, _ = np.histogram(q_sec, bins=q_edges, weights=I_sec**2)

        with np.errstate(invalid='ignore'):
            I_mean = np.where(counts > 0, H / counts, np.nan)
            variance = np.where(counts > 1, H2 / counts - I_mean**2, np.nan)
            I_std = np.sqrt(np.maximum(variance, 0))

        q_centers = 0.5 * (q_edges[:-1] + q_edges[1:])
        valid = counts > 0
        return q_centers[valid], I_mean[valid], I_std[valid]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            'type': 'Dataset2D',
            'filepath': str(self.filepath),
            'name': self.name,
            'display_label': self.display_label,
            'metadata': {k: v for k, v in self.metadata.items() if isinstance(v, (str, int, float, type(None)))},
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Dataset2D':
        ds = cls(data['filepath'], data.get('name'))
        ds.display_label = data.get('display_label', ds.name)
        ds.metadata = data.get('metadata', {})
        ds.load_data(raise_on_error=False)
        return ds
