"""
Signifikanzanalyse |I(q)/σ(q)| und darauf basierende q-Bereichs-Auswahl.

Wird sowohl vom Significance-Plot-Typ (scatter_plot.py) als auch vom GIFT-Modul
verwendet, damit „nσ“ an beiden Stellen exakt dasselbe bedeutet.
"""

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

# Auswahl-Modi für den q-Fitbereich
QRANGE_FULL = 'full'
QRANGE_SIGMA = 'sigma'
QRANGE_MANUAL = 'manual'
QRANGE_MODES = (QRANGE_FULL, QRANGE_SIGMA, QRANGE_MANUAL)


def significance(y, y_err):
    """Punktweise Signifikanz |y/σ|; nicht-endliche Werte (σ=0, NaN) werden NaN."""
    y = np.asarray(y, dtype=float)
    y_err = np.asarray(y_err, dtype=float)
    with np.errstate(invalid='ignore', divide='ignore'):
        sig = np.abs(y) / np.abs(y_err)
    sig[~np.isfinite(sig)] = np.nan
    return sig


def rolling_median(arr, window):
    """Zentrierter gleitender Median über `window` Punkte (Fenster an den Rändern verkleinert).

    NaN-Werte werden ignoriert; ein Fenster ganz aus NaN liefert NaN.
    """
    arr = np.asarray(arr, dtype=float)
    n = len(arr)
    if n == 0:
        return np.empty(0)
    half = max(int(window), 1) // 2
    # NaN-Padding + nanmedian entspricht exakt dem an den Rändern verkleinerten Fenster
    padded = np.concatenate([np.full(half, np.nan), arr, np.full(half, np.nan)])
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)
    out = np.full(n, np.nan)
    valid = ~np.all(np.isnan(windows), axis=1)
    if valid.any():
        out[valid] = np.nanmedian(windows[valid], axis=1)
    return out


def sigma_cutoff_index(smoothed, n_sigma, min_run):
    """Index des letzten Punkts vor dem ersten dauerhaften Abfall unter `n_sigma`.

    „Dauerhaft“ heißt: mindestens `min_run` aufeinanderfolgende Punkte liegen unter
    der Schwelle (NaN zählt als unter der Schwelle). Einzelne Rauschspitzen nach dem
    Abfall verlängern den Bereich dadurch nicht.

    Returns:
        Index (inklusive) des letzten gültigen Punkts, len-1 wenn die Schwelle nie
        dauerhaft unterschritten wird, oder -1 wenn schon der erste Punkt darunter liegt.
    """
    below = ~(np.nan_to_num(smoothed, nan=-np.inf) >= n_sigma)
    n = len(below)
    min_run = max(int(min_run), 1)
    run = 0
    for i in range(n):
        run = run + 1 if below[i] else 0
        if run >= min_run:
            return i - run  # letzter Punkt vor dem Beginn des Laufs
    # Kein vollständiger Lauf: ein angebrochener Lauf am Ende zählt ebenfalls
    return n - 1 - run if run > 0 else n - 1


def detect_lowq_artifacts(y, y_err=None, max_frac=0.25, min_run=5, min_significance=3.0):
    """Erkennt Artefakte am Anfang einer Kurve (Beamstop-Bereich, Separations-/Abzugs-
    artefakte) und gibt den Index des ersten vertrauenswürdigen Punkts zurück (0 = keine).

    Konservatives Kriterium (v7.13), nur innerhalb der ersten `max_frac` der Punkte:
    1. Führender Block: Die Kurve beginnt mit nicht-positiven Punkten (I ≤ 0 ist bei
       Kleinwinkelstreuung unphysikalisch) oder mit Vorzeichenwechseln. Er endet am letzten
       nicht-positiven Punkt *vor* dem ersten Lauf von `min_run` positiven Punkten. Alles
       davor wird verworfen — auch positive Ausreißer zwischen den Vorzeichenwechseln.
       Ein negativer Punkt später (z. B. im verrauschten Formfaktor-Minimum) zählt nicht.
    2. Nur nach einem solchen Block: anschließende Übergangspunkte mit |I/σ| <
       `min_significance` werden ebenfalls verworfen.
    Ein Anstieg von I(q) zu größerem q direkt danach wird *nicht* entfernt: Er kann ein
    Beamstop-Randschatten sein, aber auch physikalisch (repulsive Wechselwirkung, S(q) < 1);
    dafür gibt es ein Info-Flag.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    limit = min(n, max(min_run + 1, int(np.ceil(max_frac * n))))
    start = 0
    run = 0
    for i in range(limit):
        if y[i] > 0:
            run += 1
            if run >= min_run:
                break
        else:
            run = 0
            start = i + 1
    else:
        return 0                                        # kein sauberer Lauf im Anfangsbereich
    if start > 0 and y_err is not None:            # nur direkt nach einem Artefaktblock
        e = np.asarray(y_err, dtype=float)
        while start < limit and not (e[start] > 0 and y[start] / e[start] >= min_significance):
            start += 1
    if start >= limit:
        return 0                                        # nichts Eindeutiges gefunden
    return start


@dataclass
class QRangeSelection:
    """Ergebnis der q-Bereichs-Auswahl (vollständig reproduzierbar dokumentiert)."""
    mode: str
    q_min: float
    q_max: float
    n_total: int
    n_selected: int
    n_sigma: Optional[float] = None
    window: Optional[int] = None
    min_run: Optional[int] = None
    q_min_manual: bool = False
    q_max_manual: bool = False
    n_artifacts: int = 0             # automatisch verworfene Punkte bei kleinem q
    q_artifacts: Optional[float] = None   # q des letzten verworfenen Punkts

    @property
    def n_excluded(self):
        return self.n_total - self.n_selected

    def mask(self, q):
        q = np.asarray(q, dtype=float)
        return (q >= self.q_min) & (q <= self.q_max)

    def to_dict(self):
        d = asdict(self)
        d['n_excluded'] = self.n_excluded
        return d


def select_q_range(q, y, y_err=None, mode=QRANGE_FULL, n_sigma=2.0, window=9,
                   min_run=None, q_min=None, q_max=None, auto_qmin=False):
    """Bestimmt den q-Fitbereich.

    Modi:
        'full'   — gesamter Datenbereich (q_min/q_max optional als manuelle Grenzen)
        'sigma'  — q_max aus der geglätteten Signifikanz (≥ n_sigma), q_min = erster
                   Punkt oder manuell
        'manual' — q_min/q_max direkt vorgegeben (fehlende Grenze = Datenrand)

    Args:
        min_run: Mindestlänge des Laufs unter der Schwelle (Standard: window // 2)
        auto_qmin: ohne manuelles q_min Artefakte bei kleinem q erkennen und ausschließen
            (detect_lowq_artifacts); gilt nicht im Modus 'manual'

    Raises:
        ValueError: bei 'sigma' ohne Fehlerspalte oder wenn der Bereich leer ist
    """
    q = np.asarray(q, dtype=float)
    if mode not in QRANGE_MODES:
        raise ValueError(f"Unbekannter q-Bereichs-Modus: {mode}")
    if len(q) == 0:
        raise ValueError("Keine Datenpunkte")
    order_ok = np.all(np.diff(q) > 0)
    if not order_ok:
        raise ValueError("q muss streng monoton steigend sein")

    lo = float(q[0]) if q_min is None else float(q_min)
    hi = float(q[-1]) if q_max is None else float(q_max)
    sel_n_sigma = sel_window = sel_min_run = None
    first = 0
    if auto_qmin and q_min is None and mode != QRANGE_MANUAL and y is not None:
        first = detect_lowq_artifacts(y, y_err)
        lo = float(q[first])

    if mode == QRANGE_SIGMA:
        if y_err is None:
            raise ValueError("σ-Voreinstellung benötigt eine Fehlerspalte")
        sel_n_sigma = float(n_sigma)
        sel_window = int(window)
        sel_min_run = int(min_run) if min_run is not None else max(sel_window // 2, 1)
        # Signifikanz erst ab dem ersten vertrauenswürdigen Punkt (Artefakte können |I/σ|
        # künstlich groß machen)
        smoothed = rolling_median(significance(np.asarray(y)[first:],
                                               np.asarray(y_err)[first:]), sel_window)
        idx = sigma_cutoff_index(smoothed, sel_n_sigma, sel_min_run)
        if idx >= 0:
            idx += first
        if idx < 0:
            raise ValueError(
                f"Die geglättete Signifikanz liegt schon am ersten Punkt unter {sel_n_sigma:g}σ")
        if q_max is None:
            hi = float(q[idx])
        else:
            hi = min(float(q_max), float(q[idx]))

    if hi < lo:
        raise ValueError(f"Leerer q-Bereich: q_min={lo:g} > q_max={hi:g}")
    n_selected = int(np.count_nonzero((q >= lo) & (q <= hi)))
    if n_selected == 0:
        raise ValueError("Keine Datenpunkte im gewählten q-Bereich")

    return QRangeSelection(
        mode=mode, q_min=lo, q_max=hi, n_total=len(q), n_selected=n_selected,
        n_sigma=sel_n_sigma, window=sel_window, min_run=sel_min_run,
        q_min_manual=q_min is not None, q_max_manual=q_max is not None,
        n_artifacts=int(first), q_artifacts=float(q[first - 1]) if first else None,
    )
