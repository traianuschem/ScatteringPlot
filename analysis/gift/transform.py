"""
Fourier-Transformation der Spline-Basis [Glatter 1977, Gl. 4/10]:

    ψ_ν(q) = 4π ∫₀^Dmax φ_ν(r) · sin(qr)/(qr) dr

Numerisch per stückweiser Gauss-Legendre-Quadratur, vektorisiert über alle q. Die
Anzahl der Stützstellen pro Knotenintervall wird an q_max·h angepasst, damit auch
die schnellen Oszillationen bei großen q aufgelöst werden.
"""

from functools import lru_cache

import numpy as np

from .splines import SplineBasis

FOUR_PI = 4.0 * np.pi


def _points_per_interval(q_max, h):
    # ≥ 12 Punkte; zusätzlich ~2 Punkte pro Radiant Phasenzuwachs im Intervall
    return int(max(12, np.ceil(2.0 * q_max * h) + 12))


def sinc_kernel(q, r):
    """sin(qr)/(qr) als Matrix (len(q) × len(r)), stetig fortgesetzt bei qr = 0."""
    x = np.outer(np.asarray(q, dtype=float), np.asarray(r, dtype=float))
    return np.sinc(x / np.pi)


def design_matrix(q, basis: SplineBasis):
    """Designmatrix A (M × N) mit A[i, ν] = ψ_ν(q_i)."""
    q = np.asarray(q, dtype=float)
    q_max = float(np.max(np.abs(q))) if len(q) else 0.0
    r, w = basis.quadrature(_points_per_interval(q_max, basis.h))
    phi = basis.evaluate(r)                      # (P × N)
    kernel = sinc_kernel(q, r) * w[None, :]      # (M × P)
    return FOUR_PI * kernel @ phi


@lru_cache(maxsize=32)
def _cached_design_matrix(q_bytes, dmax, n_splines):
    q = np.frombuffer(q_bytes, dtype=float)
    A = design_matrix(q, SplineBasis(dmax, n_splines))
    A.setflags(write=False)
    return A


def cached_design_matrix(q, dmax, n_splines):
    """Wie design_matrix(), aber mit Cache pro (q-Gitter, Dmax, N). Nur lesbar."""
    q = np.ascontiguousarray(q, dtype=float)
    return _cached_design_matrix(q.tobytes(), float(dmax), int(n_splines))
