"""
Panel-Typen für das flexible Panel-Layout (v8.1)

Jeder Panel-Typ beschreibt, wie Datensätze in einem Plot-Panel dargestellt werden:
Achsenbeschriftung, Skalen, Daten-Transformation, welche Datensätze er akzeptiert
und welcher Renderer verwendet wird. Die Registry ersetzt die früheren
`if plot_type == ...`-Verzweigungen in `ScatterPlotApp.update_plot()`.

Ehemalige Plot-Typen mit festem Subplot (PDDF, Significance, ASAXS ± Subplot) sind
jetzt eigenständige Panel-Typen ('P(r)', 'Significance', 'I linear'), die sich frei
im Grid platzieren lassen.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import logging

import numpy as np
from scipy.signal import savgol_filter

# numpy 2.0 hat trapz() in trapezoid() umbenannt
np_trapezoid = getattr(np, 'trapezoid', getattr(np, 'trapz', None))

logger = logging.getLogger(__name__)


# ── Transformationen ─────────────────────────────────────────────────────────
# Signatur: (x, y, err, ctx) -> (x, y, err)
# err darf None sein; ctx enthält 'wavelength' und 'options' (Panel-Optionen).

def _identity(x, y, err, ctx):
    return x, y, err


def _porod(x, y, err, ctx):
    f = x ** 4
    return x, y * f, (err * f if err is not None else None)


def _kratky(x, y, err, ctx):
    f = x ** 2
    return x, y * f, (err * f if err is not None else None)


def _guinier(x, y, err, ctx):
    with np.errstate(invalid='ignore', divide='ignore'):
        ln_y = np.log(y)
        # Fehlerfortpflanzung: σ(ln I) = σ(I) / I
        ln_err = np.abs(err / y) if err is not None else None
    return x ** 2, ln_y, ln_err


def _dlnidlnq(x, y, err, ctx):
    """Logarithmische Ableitung d(ln I)/d(ln q) zur Identifikation versteckter
    Features (Schultern). Fehlerfortpflanzung durch Glättung + Ableitung ist nicht
    trivial, daher ohne Fehlerbalken."""
    pos_mask = (x > 0) & (y > 0)
    x_pos = x[pos_mask]
    y_pos = y[pos_mask]
    if len(x_pos) < 2:
        return np.array([]), np.array([]), None

    log_x = np.log(x_pos)
    log_y = np.log(y_pos)

    window = int(ctx.get('options', {}).get('smooth_window', 5))
    if window % 2 == 0:
        window -= 1
    # Größtes gültiges (ungerades) Fenster, das nicht mehr Punkte verlangt als vorhanden
    max_window = len(log_y) if len(log_y) % 2 == 1 else len(log_y) - 1
    window = min(window, max_window)

    if window >= 3:
        log_y = savgol_filter(log_y, window_length=window, polyorder=2)
    else:
        logger.warning("dlnI/dlnq: Zu wenige Datenpunkte für Glättung, "
                       "verwende ungeglättete Ableitung")

    return x_pos, np.gradient(log_y, log_x), None


def _bragg(x, y, err, ctx):
    # d = 2π/q (q in nm⁻¹, d in nm)
    with np.errstate(divide='ignore'):
        return 2 * np.pi / x, y, err


def _two_theta(x, y, err, ctx):
    # 2θ = 2·arcsin(λq / 4π); nur gültige Werte (Argument ≤ 1)
    wavelength = ctx.get('wavelength', 0.1524)
    arg = wavelength * x / (4 * np.pi)
    valid = arg <= 1
    two_theta = 2 * np.arcsin(arg[valid]) * 180 / np.pi
    return two_theta, y[valid], (err[valid] if err is not None else None)


def _pofr(x, y, err, ctx):
    """P(r) mit optionaler Flächen-Normierung (∫P(r)dr = 1)."""
    if ctx.get('options', {}).get('normalize_area', False) and len(x) > 1:
        area = np_trapezoid(y, x)
        if area > 0:
            return x, y / area, (err / area if err is not None else None)
    return x, y, err


# ── Akzeptanz-Prädikate ──────────────────────────────────────────────────────

def _is_ratio(ds):
    return getattr(ds, 'data_term', '') == 'ratio'


def _accepts_q_space(ds):
    # I(q)-Panels: keine P(r)-Kurven und keine abgeleiteten Verhältnisse
    return not ds.is_pofr() and not _is_ratio(ds)


def _accepts_pofr(ds):
    return ds.is_pofr()


def _accepts_with_errors(ds):
    return _accepts_q_space(ds) and ds.y_err is not None


# ── Registry ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PanelType:
    """Beschreibt die Darstellung eines Panels."""
    key: str
    xlabel: str
    ylabel: str
    xscale: str
    yscale: str
    x_domain: str                      # nur Panels gleicher Domäne dürfen die X-Achse teilen
    transform: Callable = _identity    # (x, y, err, ctx) -> (x, y, err)
    accepts: Callable = _accepts_q_space
    renderer: str = 'curve'            # 'curve' | 'significance'
    default_options: dict = field(default_factory=dict)
    xlim: Optional[tuple] = None
    zero_line: bool = False            # gestrichelte Nulllinie (lineare Panels mit ±-Werten)
    show_errors: bool = True
    # Label-Variante, wenn eine Option aktiv ist, z. B. P(r) → "P(r) (norm.)"
    option_ylabels: dict = field(default_factory=dict)

    def default_ylabel(self, options=None):
        options = options or {}
        for opt, label in self.option_ylabels.items():
            if options.get(opt):
                return label
        return self.ylabel


_Q = 'q / nm⁻¹'

PANEL_TYPES = {
    'Log-Log': PanelType('Log-Log', _Q, 'I / a.u.', 'log', 'log', 'q'),
    'Porod': PanelType('Porod', _Q, 'I·q⁴ / a.u.·nm⁻⁴', 'log', 'log', 'q', _porod),
    'Kratky': PanelType('Kratky', _Q, 'I·q² / a.u.·nm⁻²', 'linear', 'linear', 'q', _kratky),
    # Fraction-Slash (U+2044) statt "/", damit format_axis_label() dies nicht
    # fälschlich als "Größe / Einheit" interpretiert.
    'dlnI/dlnq': PanelType('dlnI/dlnq', _Q, 'd ln(I) ⁄ d ln(q)', 'log', 'linear', 'q',
                           _dlnidlnq, default_options={'smooth_window': 5},
                           show_errors=False),
    'Guinier': PanelType('Guinier', 'q² / nm⁻²', 'ln(I)', 'linear', 'linear', 'q2', _guinier),
    'Bragg Spacing': PanelType('Bragg Spacing', 'd / nm', 'I / a.u.', 'log', 'log', 'd', _bragg),
    '2-Theta': PanelType('2-Theta', '2θ / °', 'I / a.u.', 'linear', 'log', '2theta', _two_theta),
    'Azimuthal Profile': PanelType('Azimuthal Profile', 'φ / °', 'I / a.u.', 'linear', 'linear',
                                   'phi', xlim=(-180.0, 180.0)),
    'ASAXS': PanelType('ASAXS', _Q, 'I / cm⁻¹', 'log', 'symlog', 'q'),
    'I linear': PanelType('I linear', _Q, 'I / cm⁻¹', 'log', 'linear', 'q', zero_line=True),
    # Abgeleitete Verhältnisse/Korrelationen (z. B. ASAXS I_A/I_N aus dem ASAXS-Dialog)
    'Ratio': PanelType('Ratio', _Q, 'ratio', 'log', 'linear', 'q', accepts=_is_ratio,
                       zero_line=True),
    'P(r)': PanelType('P(r)', 'r / nm', 'P(r)', 'linear', 'linear', 'r', _pofr,
                      accepts=_accepts_pofr, default_options={'normalize_area': False},
                      zero_line=True, option_ylabels={'normalize_area': 'P(r) (norm.)'}),
    # Fraction-Slash: Verhältnis, keine Einheit
    'Significance': PanelType('Significance', _Q, '|I(q)| ⁄ σ(q)', 'log', 'linear', 'q',
                              accepts=_accepts_with_errors, renderer='significance',
                              default_options={'window': 9, 'thresholds': [3.0, 2.0, 1.0]}),
}

# Reihenfolge für Auswahllisten (Haupt-Combo und Layout-Dialog)
PANEL_TYPE_ORDER = list(PANEL_TYPES.keys())


def get_panel_type(key):
    """Liefert den PanelType zu `key` (Fallback: Log-Log)."""
    return PANEL_TYPES.get(key, PANEL_TYPES['Log-Log'])


def default_options_for(key):
    """Kopie der Standard-Optionen eines Panel-Typs."""
    opts = get_panel_type(key).default_options
    return {k: (list(v) if isinstance(v, list) else v) for k, v in opts.items()}
