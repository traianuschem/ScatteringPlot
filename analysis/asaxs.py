"""
ASAXS-Auswertung der separierten Terme (v8.1)

Bei der anomalen Kleinwinkelstreuung wird die Streuintensität energieabhängig in drei
Terme zerlegt: den nicht-resonanten Term I_N, den Cross-Term I_cross und den rein
resonanten (anomalen) Term I_A. Dieses Modul berechnet daraus abgeleitete Größen:

- Verhältnisse, z. B. I_A/I_N oder I_cross/I_N (Anteil bzw. Kontrastverhältnis der
  resonanten Streuer), auf dem q-Gitter des Nenners
- den Korrelationskoeffizienten c = I_cross / √(I_N·I_A). Nach der Cauchy-Schwarz-Ungleichung
  gilt |c| ≤ 1; c ≈ ±1 bedeutet, dass resonante und nicht-resonante Streuung dieselbe
  Struktur „sehen“ (z. B. Zweiphasensystem), |c| > 1 weist auf Probleme der Separation hin.
- den Cauchy-Schwarz-Test R = √(I_N·I_A) / |I_cross| = 1/|c|: R ≥ 1 muss überall gelten,
  R < 1 verletzt die Ungleichung (Messfehler, Separationsartefakt).
  Konvention (Stuhrmann): I = I_N + 2f'·I_cross + (f'²+f''²)·I_A, die 2 steht also vor f'
  und nicht in I_cross; sonst wäre die Schranke 2·√(I_N·I_A).

Die Terme liegen i. d. R. auf demselben q-Gitter; falls nicht, wird der Zähler
linear in log(q) auf das Gitter des Nenners interpoliert (nur im Überlappungsbereich).
Fehler werden nach Gauß fortgepflanzt (unkorrelierte Terme angenommen).
"""

import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

TERM_NORMAL = 'normal'        # I_N
TERM_CROSS = 'cross'          # I_cross
TERM_ANOMALOUS = 'anomalous'  # I_A
TERM_RATIO = 'ratio'          # abgeleitete Größe (Verhältnis/Korrelation)
TERMS = (TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS)

QUANTITY_IA_IN = 'ia_in'
QUANTITY_ICROSS_IN = 'icross_in'
QUANTITY_CORRELATION = 'correlation'
QUANTITY_CAUCHY_SCHWARZ = 'cauchy_schwarz'
QUANTITIES = (QUANTITY_IA_IN, QUANTITY_ICROSS_IN, QUANTITY_CORRELATION, QUANTITY_CAUCHY_SCHWARZ)

# Benötigte Terme je Größe
REQUIRED_TERMS = {
    QUANTITY_IA_IN: (TERM_ANOMALOUS, TERM_NORMAL),
    QUANTITY_ICROSS_IN: (TERM_CROSS, TERM_NORMAL),
    QUANTITY_CORRELATION: (TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS),
    QUANTITY_CAUCHY_SCHWARZ: (TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS),
}

# Namenssuffixe für die abgeleiteten Kurven (Dateiname/Label)
QUANTITY_SUFFIX = {
    QUANTITY_IA_IN: 'IA_IN',
    QUANTITY_ICROSS_IN: 'Icross_IN',
    QUANTITY_CORRELATION: 'corr',
    QUANTITY_CAUCHY_SCHWARZ: 'CS',
}

# Achsentitel (MathText)
QUANTITY_LABEL = {
    QUANTITY_IA_IN: r'$I_A \,/\, I_N$',
    QUANTITY_ICROSS_IN: r'$I_{cross} \,/\, I_N$',
    QUANTITY_CORRELATION: r'$I_{cross} \,/\, \sqrt{I_N I_A}$',
    QUANTITY_CAUCHY_SCHWARZ: r'$\sqrt{I_N I_A} \,/\, |I_{cross}|$',
}

_SUFFIX_RE = re.compile(r'_(icross|ia|in)(?=_|$)', re.IGNORECASE)


@dataclass
class Curve:
    """Einfache Kurve (q, I, σ); σ darf None sein."""
    x: np.ndarray
    y: np.ndarray
    err: Optional[np.ndarray] = None

    def __post_init__(self):
        self.x = np.asarray(self.x, dtype=float)
        self.y = np.asarray(self.y, dtype=float)
        if self.err is not None:
            self.err = np.abs(np.asarray(self.err, dtype=float))

    @classmethod
    def from_dataset(cls, dataset):
        return cls(dataset.x, dataset.y, dataset.y_err)


@dataclass
class DerivedCurve:
    """Ergebnis einer ASAXS-Auswertung."""
    quantity: str
    x: np.ndarray
    y: np.ndarray
    err: Optional[np.ndarray]
    n_interpolated: int = 0            # Anzahl interpolierter Zähler-Punkte
    info: dict = field(default_factory=dict)


def base_name(name):
    """Probenname ohne ASAXS-Termsuffix (_IN, _IA, _Icross), z. B. 'probe_IA' → 'probe'."""
    stripped = _SUFFIX_RE.sub('', name, count=1)
    return stripped.strip('_ ') or name


def pair_asaxs_terms(datasets):
    """Ordnet ASAXS-Datensätze nach Probenname den Termen zu.

    Args:
        datasets: Objekte mit `.name` und `.data_term` ('normal' | 'cross' | 'anomalous').

    Returns:
        dict Basisname → {Term: Datensatz}, in Reihenfolge des ersten Auftretens.
        Pro Probe und Term wird der erste passende Datensatz verwendet.
    """
    samples = {}
    for ds in datasets:
        term = getattr(ds, 'data_term', '')
        if term not in TERMS:
            continue
        entry = samples.setdefault(base_name(ds.name), {})
        entry.setdefault(term, ds)
    return samples


def interpolate_to(src, x_target):
    """Interpoliert eine Kurve linear in log(q) auf `x_target`.

    Returns:
        (y, err, mask): Werte auf x_target; mask markiert Punkte im Überlappungsbereich
        (außerhalb NaN). err ist None, wenn die Quelle keine Fehler hat.
    """
    x_target = np.asarray(x_target, dtype=float)
    order = np.argsort(src.x)
    xs, ys = src.x[order], src.y[order]
    valid = (xs > 0) & np.isfinite(ys)
    xs, ys = xs[valid], ys[valid]
    es = src.err[order][valid] if src.err is not None else None

    mask = (x_target >= xs[0]) & (x_target <= xs[-1]) & (x_target > 0) if len(xs) else \
        np.zeros(len(x_target), dtype=bool)
    y = np.full(len(x_target), np.nan)
    err = np.full(len(x_target), np.nan) if es is not None else None
    if len(xs) >= 2 and mask.any():
        lx, lt = np.log(xs), np.log(x_target[mask])
        y[mask] = np.interp(lt, lx, ys)
        if es is not None:
            err[mask] = np.interp(lt, lx, es)
    elif len(xs) == 1 and mask.any():
        y[mask] = ys[0]
        if es is not None:
            err[mask] = es[0]
    return y, err, mask


def _on_grid(num, den):
    """Zähler auf das Gitter des Nenners bringen (direkt, wenn identisch)."""
    if num.x.shape == den.x.shape and np.allclose(num.x, den.x, rtol=1e-9, atol=0):
        return num.y.copy(), (num.err.copy() if num.err is not None else None), 0
    y, err, mask = interpolate_to(num, den.x)
    return y, err, int(mask.sum())


def _rel_sq(err, val):
    if err is None:
        return 0.0
    with np.errstate(invalid='ignore', divide='ignore'):
        return (err / val) ** 2


def ratio(num, den, quantity=QUANTITY_IA_IN, q_range=None):
    """Verhältnis num/den auf dem q-Gitter des Nenners.

    σ_R = |R| · √((σ_num/num)² + (σ_den/den)²). Punkte mit den ≤ 0, außerhalb des
    Überlappungsbereichs oder außerhalb `q_range` (qmin, qmax; None = offen) entfallen.
    """
    y_num, e_num, n_interp = _on_grid(num, den)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = y_num / den.y
    keep = np.isfinite(r) & (den.y > 0) & np.isfinite(y_num)
    err = None
    if e_num is not None or den.err is not None:
        with np.errstate(invalid='ignore'):
            err = np.abs(r) * np.sqrt(_rel_sq(e_num, y_num) + _rel_sq(den.err, den.y))
        # y_num = 0 → relativer Fehler undefiniert; absoluten Fehler direkt verwenden
        if e_num is not None:
            zero = keep & (y_num == 0)
            err[zero] = e_num[zero] / den.y[zero]
        keep &= np.isfinite(err)
    keep &= _q_mask(den.x, q_range)
    return DerivedCurve(quantity, den.x[keep], r[keep], err[keep] if err is not None else None,
                        n_interpolated=n_interp)


def correlation(normal, anomalous, cross, q_range=None):
    """Korrelationskoeffizient c = I_cross / √(I_N·I_A) auf dem Gitter von I_N.

    σ_c = |c| · √((σ_X/I_X)² + (σ_N/2I_N)² + (σ_A/2I_A)²); nur Punkte mit I_N, I_A > 0.
    """
    y_a, e_a, n_a = _on_grid(anomalous, normal)
    y_x, e_x, n_x = _on_grid(cross, normal)
    with np.errstate(invalid='ignore', divide='ignore'):
        denom = np.sqrt(normal.y * y_a)
        c = y_x / denom
    keep = np.isfinite(c) & (normal.y > 0) & (y_a > 0)
    err = None
    if any(e is not None for e in (normal.err, e_a, e_x)):
        with np.errstate(invalid='ignore', divide='ignore'):
            rel = _rel_sq(normal.err, 2 * normal.y) + _rel_sq(e_a, 2 * y_a)
            err = np.abs(c) * np.sqrt(_rel_sq(e_x, y_x) + rel)
            if e_x is not None:
                zero = keep & (y_x == 0)
                err[zero] = e_x[zero] / denom[zero]
        keep &= np.isfinite(err)
    keep &= _q_mask(normal.x, q_range)
    out = DerivedCurve(QUANTITY_CORRELATION, normal.x[keep], c[keep],
                       err[keep] if err is not None else None, n_interpolated=max(n_a, n_x))
    finite = np.abs(out.y[np.isfinite(out.y)])
    out.info['fraction_above_one'] = float(np.mean(finite > 1.0)) if finite.size else 0.0
    return out


def cauchy_schwarz(normal, anomalous, cross, q_range=None):
    """Cauchy-Schwarz-Test R = √(I_N·I_A) / |I_cross| auf dem Gitter von I_N.

    Aus |I_cross| ≤ √(I_N·I_A) folgt R ≥ 1. σ_R = R · √((σ_N/2I_N)² + (σ_A/2I_A)² + (σ_X/I_X)²);
    nur Punkte mit I_N, I_A > 0 und I_cross ≠ 0 (dort ist R unendlich).
    `info['fraction_below_one']` gibt den Anteil der Punkte mit R < 1 an (Verletzung).
    """
    y_a, e_a, n_a = _on_grid(anomalous, normal)
    y_x, e_x, n_x = _on_grid(cross, normal)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = np.sqrt(normal.y * y_a) / np.abs(y_x)
    keep = np.isfinite(r) & (normal.y > 0) & (y_a > 0) & (y_x != 0)
    err = None
    if any(e is not None for e in (normal.err, e_a, e_x)):
        with np.errstate(invalid='ignore', divide='ignore'):
            rel = _rel_sq(normal.err, 2 * normal.y) + _rel_sq(e_a, 2 * y_a) + _rel_sq(e_x, y_x)
            err = r * np.sqrt(rel)
        keep &= np.isfinite(err)
    keep &= _q_mask(normal.x, q_range)
    out = DerivedCurve(QUANTITY_CAUCHY_SCHWARZ, normal.x[keep], r[keep],
                       err[keep] if err is not None else None, n_interpolated=max(n_a, n_x))
    out.info['fraction_below_one'] = float(np.mean(out.y < 1.0)) if out.y.size else 0.0
    return out


def _q_mask(x, q_range):
    mask = np.ones(len(x), dtype=bool)
    if q_range:
        qmin, qmax = q_range
        if qmin is not None:
            mask &= x >= qmin
        if qmax is not None:
            mask &= x <= qmax
    return mask


def compute(quantity, terms, q_range=None):
    """Berechnet eine Größe aus einem Term-Dict {Term: Curve}.

    Raises:
        KeyError: wenn ein benötigter Term fehlt.
    """
    missing = [t for t in REQUIRED_TERMS[quantity] if t not in terms]
    if missing:
        raise KeyError(f"Fehlende ASAXS-Terme für {quantity}: {', '.join(missing)}")
    if quantity == QUANTITY_IA_IN:
        return ratio(terms[TERM_ANOMALOUS], terms[TERM_NORMAL], quantity, q_range)
    if quantity == QUANTITY_ICROSS_IN:
        return ratio(terms[TERM_CROSS], terms[TERM_NORMAL], quantity, q_range)
    func = cauchy_schwarz if quantity == QUANTITY_CAUCHY_SCHWARZ else correlation
    return func(terms[TERM_NORMAL], terms[TERM_ANOMALOUS], terms[TERM_CROSS], q_range)
