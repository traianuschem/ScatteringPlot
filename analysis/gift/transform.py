"""
Fourier-Transformation der Spline-Basis [Glatter 1977, Gl. 4/10]:

    ψ_ν(q) = 4π ∫₀^Dmax φ_ν(r) · sin(qr)/(qr) dr

Andere Kerne (Querschnitt, Dicke, Größenverteilungen; v8.0) siehe `kernels.py`.

Numerisch per stückweiser Gauss-Legendre-Quadratur, vektorisiert über alle q. Die
Anzahl der Stützstellen pro Knotenintervall wird an q_max·h angepasst, damit auch
die schnellen Oszillationen bei großen q aufgelöst werden.
"""

from functools import lru_cache

import numpy as np

from .splines import SplineBasis
from .kernels import get_kernel, PDDF

FOUR_PI = 4.0 * np.pi


def _points_per_interval(q_max, h, freq=1.0):
    # ≥ 12 Punkte; zusätzlich ~2 Punkte pro Radiant Phasenzuwachs im Intervall
    # (freq = 2 für quadrierte Amplituden der Größenverteilungen)
    return int(max(12, np.ceil(2.0 * freq * q_max * h) + 12))


def make_basis(dmax, n_splines, kind=PDDF):
    """Spline-Basis passend zur IFT-Art (Dicken-Verteilung: p(0) frei)."""
    return SplineBasis(dmax, n_splines, left_free=get_kernel(kind).left_free)


def sinc_kernel(q, r):
    """sin(qr)/(qr) als Matrix (len(q) × len(r)), stetig fortgesetzt bei qr = 0."""
    x = np.outer(np.asarray(q, dtype=float), np.asarray(r, dtype=float))
    return np.sinc(x / np.pi)


def design_matrix(q, basis: SplineBasis, kind=PDDF):
    """Designmatrix A (M × N) mit A[i, ν] = ψ_ν(q_i) = ∫ φ_ν(r) K(q_i, r) dr."""
    q = np.asarray(q, dtype=float)
    q_max = float(np.max(np.abs(q))) if len(q) else 0.0
    kern = get_kernel(kind)
    if kern.key == PDDF:
        r, w = basis.quadrature(_points_per_interval(q_max, basis.h))
        phi = basis.evaluate(r)                      # (P × N)
        kernel = sinc_kernel(q, r) * w[None, :]      # (M × P)
        return FOUR_PI * kernel @ phi
    if kern.needs_positive_q and np.any(q <= 0):
        raise ValueError("Diese IFT-Art erfordert q > 0")
    r, w = basis.quadrature(_points_per_interval(q_max, basis.h, 2.0 if kern.size else 1.0))
    phi = basis.evaluate(r)
    return (kern.matrix(q, r) * w[None, :]) @ phi


@lru_cache(maxsize=32)
def _cached_design_matrix(q_bytes, dmax, n_splines, kind):
    q = np.frombuffer(q_bytes, dtype=float)
    A = design_matrix(q, make_basis(dmax, n_splines, kind), kind)
    A.setflags(write=False)
    return A


def cached_design_matrix(q, dmax, n_splines, kind=PDDF):
    """Wie design_matrix(), aber mit Cache pro (q-Gitter, Dmax, N, Art). Nur lesbar."""
    q = np.ascontiguousarray(q, dtype=float)
    return _cached_design_matrix(q.tobytes(), float(dmax), int(n_splines), kind or PDDF)


def moment_vectors(basis: SplineBasis, kind=PDDF, points=8):
    """Vektoren (m₀, m₂) mit F(0) = m₀·c und R_g² = (m₂·c)/(m₀·c) — exakte Quadratur."""
    rq, wq = basis.quadrature(points)
    phi = basis.evaluate(rq)
    w0, w2 = get_kernel(kind).forward_weights(rq)
    return (wq * w0) @ phi, (wq * w2) @ phi
