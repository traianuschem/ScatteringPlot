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
from utils.data_loader import load_raw_data, default_column_mapping, select_columns
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

        # Spaltenauswahl: Rohdaten + x/y/error-Spaltenzuordnung
        self.raw_data = None
        self.col_x = None
        self.col_y = None
        self.col_err = None
        self._columns_configured = False
        # Wenn False, werden x≤0/y≤0-Werte beim Laden NICHT gefiltert.
        # Notwendig für azimutale Profile (φ < 0) und andere lineare Daten.
        # _base_filter_nonpositive ist der vom Aufrufer gewünschte Ausgangswert;
        # set_pddf_role() UND-verknüpft ihn mit der Cross-Term-/P(r)-Ausnahme, sodass
        # ein explizites filter_nonpositive=False (z.B. Azimutalprofile) nie durch die
        # Rollen-Erkennung überschrieben wird.
        self._base_filter_nonpositive = filter_nonpositive
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

        # ASAXS (v7.3)
        self.data_term = ''        # '', 'normal', 'cross', 'anomalous'
        self.snr_visualization = False  # SNR-basierte Qualitätsmarker
        # SNR-Visualisierungseinstellungen
        self.snr_threshold = 1.0          # SNR-Schwellenwert (Standard: 1)
        self.snr_good_marker = 'o'        # Marker für gute Punkte
        self.snr_poor_marker = '^'        # Marker für schlechte Punkte
        self.snr_poor_alpha = 0.3         # Transparenz der schlechten Punkte
        self.snr_show_errorbars = True    # Fehlerbalken im SNR-Modus anzeigen
        self._auto_detect_asaxs_term()
        self._auto_detect_pddf_type()
        # Manuelle Rollen-Übersteuerung ('', 'data', 'fit', 'pofr') — siehe set_pddf_role().
        # Wendet u.a. die Cross-Term-/P(r)-Nicht-Positiv-Filterausnahme an.
        self.set_pddf_role('')

        if not skip_load:
            self.load_data()

        # Auto-Stil anwenden
        if apply_auto_style:
            self.apply_auto_style()

    def _auto_detect_asaxs_term(self):
        """Erkennt ASAXS-Term-Typ automatisch aus dem Dateinamen."""
        stem = self.filepath.stem.lower()
        if stem.endswith('_icross') or '_icross_' in stem:
            self.data_term = 'cross'
        elif stem.endswith('_in') or '_in_' in stem:
            self.data_term = 'normal'
        elif stem.endswith('_ia') or '_ia_' in stem:
            self.data_term = 'anomalous'

    def _auto_detect_pddf_type(self):
        """Erkennt P(r)-Daten automatisch aus dem Dateinamen."""
        stem = self.filepath.stem.lower()
        pr_patterns = ['_pr', '_p_r', '_pddf', '_pofr', 'pair_dist', 'p(r)']
        self.is_pr_data = any(p in stem for p in pr_patterns)

    def is_pofr(self):
        """P(r)-Klassifikation für die PDDF-Subplot-Zuordnung.

        Die manuelle Rollen-Übersteuerung (`pddf_role`, gesetzt via `set_pddf_role()`)
        hat Vorrang vor der automatischen Dateinamen-Erkennung (`is_pr_data`), damit
        falsch erkannte Dateien korrigiert werden können.
        """
        if self.pddf_role == 'pofr':
            return True
        if self.pddf_role in ('data', 'fit'):
            return False
        return self.is_pr_data

    def is_fit_curve(self):
        """Bestimmt, ob der Datensatz als Linie (statt Marker) gerendert werden soll.

        Manuelle Rolle hat Vorrang vor der Dateinamen-Heuristik ('fit' im Namen).
        """
        if self.pddf_role == 'fit':
            return True
        if self.pddf_role in ('data', 'pofr'):
            return False
        return 'fit' in self.name.lower()

    def set_pddf_role(self, role):
        """Setzt die manuelle PDDF-Rollen-Zuordnung ('', 'data', 'fit', 'pofr') neu.

        '' bedeutet Auto-Erkennung aus dem Dateinamen (Standard). Wendet die davon
        abhängige Nicht-Positiv-Filterung sofort auf bereits geladene Rohdaten an:
        P(r)-Daten (r=0-Startpunkt, ggf. negative Werte im Tail) und der ASAXS-
        Cross-Term (kann negative Intensitäten haben) dürfen nicht x/y>0-gefiltert
        werden.
        """
        self.pddf_role = role
        new_filter = self._base_filter_nonpositive and not (self.is_pofr() or self.data_term == 'cross')
        if new_filter != self.filter_nonpositive:
            self.filter_nonpositive = new_filter
            if self.raw_data is not None:
                self._apply_column_selection()

    def load_data(self, raise_on_error=True):
        """Lädt Daten

        Args:
            raise_on_error: Wenn False, werden Fehler nur geloggt statt Exception zu werfen
        """
        logger = logging.getLogger(__name__)
        try:
            self.raw_data = load_raw_data(self.filepath)
            if not self._columns_configured:
                self.col_x, self.col_y, self.col_err = default_column_mapping(self.raw_data.shape[1])
            self._apply_column_selection()
            self.data_loaded = True
        except Exception as e:
            error_msg = f"Fehler beim Laden von {self.filepath}: {e}"
            if raise_on_error:
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)
                self.data_loaded = False

    def _apply_column_selection(self):
        """Wendet die aktuelle Spaltenzuordnung auf self.raw_data an."""
        self.data = select_columns(
            self.raw_data, self.col_x, self.col_y, self.col_err,
            filter_nonpositive=getattr(self, 'filter_nonpositive', True)
        )
        self.x = self.data[:, 0]
        self.y = self.data[:, 1]
        self.y_err = self.data[:, 2] if self.data.shape[1] > 2 else None

    def set_column_mapping(self, col_x, col_y, col_err):
        """Setzt die x/y/error-Spaltenzuordnung neu und wendet sie auf die
        bereits geladenen Rohdaten an (kein erneutes Einlesen der Datei).

        Raises:
            ValueError: Wenn nach Auswahl/Filterung keine Datenpunkte übrig bleiben
        """
        old_x, old_y, old_err = self.col_x, self.col_y, self.col_err
        self.col_x, self.col_y, self.col_err = col_x, col_y, col_err
        try:
            self._apply_column_selection()
            self._columns_configured = True
        except ValueError:
            self.col_x, self.col_y, self.col_err = old_x, old_y, old_err
            self._apply_column_selection()
            raise

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
            # Fehlerbalken-Einstellungen (v6.0, erweitert v7.3.1)
            if 'show_errorbars' in style:
                self.show_errorbars = style['show_errorbars']
            if 'errorbar_style' in style:
                self.errorbar_style = style['errorbar_style']
            if 'errorbar_alpha' in style:
                self.errorbar_alpha = style['errorbar_alpha']
            if 'errorbar_capsize' in style:
                self.errorbar_capsize = style['errorbar_capsize']
            if 'errorbar_linewidth' in style:
                self.errorbar_linewidth = style['errorbar_linewidth']
            # SNR-Einstellungen (v7.3.1)
            if 'snr_visualization' in style:
                self.snr_visualization = style['snr_visualization']
            if 'snr_threshold' in style:
                self.snr_threshold = style['snr_threshold']
            if 'snr_good_marker' in style:
                self.snr_good_marker = style['snr_good_marker']
            if 'snr_poor_marker' in style:
                self.snr_poor_marker = style['snr_poor_marker']
            if 'snr_poor_alpha' in style:
                self.snr_poor_alpha = style['snr_poor_alpha']
            if 'snr_show_errorbars' in style:
                self.snr_show_errorbars = style['snr_show_errorbars']

    def get_plot_style(self):
        """Gibt Plot-Stil zurück"""
        line = self.line_style if self.line_style else ''
        marker = self.marker_style if self.marker_style else ''
        if not line and not marker:
            # Auto: Fit=Linie, sonst Marker
            if self.is_fit_curve():
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
            'filter_nonpositive': self._base_filter_nonpositive,
            'data_term': self.data_term,
            'pddf_role': self.pddf_role,
            'snr_visualization': self.snr_visualization,
            'snr_threshold': self.snr_threshold,
            'snr_good_marker': self.snr_good_marker,
            'snr_poor_marker': self.snr_poor_marker,
            'snr_poor_alpha': self.snr_poor_alpha,
            'snr_show_errorbars': self.snr_show_errorbars,
            'col_x': self.col_x,
            'col_y': self.col_y,
            'col_err': self.col_err,
            'columns_configured': self._columns_configured,
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
        if 'data_term' in data:
            ds.data_term = data['data_term']
        ds.set_pddf_role(data.get('pddf_role', ''))
        ds.snr_visualization = data.get('snr_visualization', False)
        ds.snr_threshold = data.get('snr_threshold', 1.0)
        ds.snr_good_marker = data.get('snr_good_marker', 'o')
        ds.snr_poor_marker = data.get('snr_poor_marker', '^')
        ds.snr_poor_alpha = data.get('snr_poor_alpha', 0.3)
        ds.snr_show_errorbars = data.get('snr_show_errorbars', True)
        ds._columns_configured = data.get('columns_configured', False)
        ds.col_x = data.get('col_x')
        ds.col_y = data.get('col_y')
        ds.col_err = data.get('col_err')

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
        # Subplot-Zuweisung (v7.3.1): 'both' | 'main' | 'sub'
        # Steuert, in welchem Axes-Bereich diese Gruppe gerendert wird,
        # wenn ein Subplot aktiv ist (ASAXS ± Subplot, PDDF).
        self.subplot_target = 'both'

    def add_dataset(self, dataset):
        """Datensatz hinzufügen"""
        self.datasets.append(dataset)

    def remove_dataset(self, dataset):
        """Datensatz entfernen"""
        if dataset in self.datasets:
            self.datasets.remove(dataset)

    def auto_suggest_pddf_subplot(self):
        """Setzt subplot_target anhand der Dateinamen — nur wenn noch Default 'both'."""
        if self.subplot_target != 'both' or not self.datasets:
            return
        pr_count = sum(1 for ds in self.datasets if ds.is_pofr())
        if pr_count == len(self.datasets):
            self.subplot_target = 'sub'
        elif pr_count == 0:
            self.subplot_target = 'main'
        # Gemischt → bleibt 'both'

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
            'subplot_target': self.subplot_target,
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
        group.subplot_target = data.get('subplot_target', 'both')
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
