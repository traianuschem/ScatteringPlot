"""Synthetische Testkurven nach Glatter (1977): Kugel, Debye-Kette, dünner Stab."""

import numpy as np
from scipy.special import sici


def sphere_intensity(q, radius, i0=1.0):
    x = np.asarray(q, dtype=float) * radius
    with np.errstate(invalid='ignore', divide='ignore'):
        f = 3.0 * (np.sin(x) - x * np.cos(x)) / x ** 3
    f = np.where(x < 1e-6, 1.0, f)
    return i0 * f ** 2


def sphere_pr(r, radius):
    """p(r) einer homogenen Kugel (unnormiert)."""
    r = np.asarray(r, dtype=float)
    x = r / radius
    p = r ** 2 * (1.0 - 0.75 * x + x ** 3 / 16.0)
    return np.where(r <= 2.0 * radius, p, 0.0)


def debye_intensity(q, rg, i0=1.0):
    x = (np.asarray(q, dtype=float) * rg) ** 2
    with np.errstate(invalid='ignore', divide='ignore'):
        f = 2.0 * (np.exp(-x) - 1.0 + x) / x ** 2
    return i0 * np.where(x < 1e-8, 1.0, f)


def rod_intensity(q, length, i0=1.0):
    """Unendlich dünner Stab der Länge L (Rg = L/√12)."""
    x = np.asarray(q, dtype=float) * length
    si, _ = sici(x)
    with np.errstate(invalid='ignore', divide='ignore'):
        f = 2.0 * si / x - (np.sin(x / 2.0) / (x / 2.0)) ** 2
    return i0 * np.where(x < 1e-8, 1.0, f)


def noisy(intensity, rel_error, seed):
    """Gaußsches Rauschen mit relativem Fehler; gibt (I_noisy, σ) zurück."""
    rng = np.random.default_rng(seed)
    sigma = rel_error * intensity
    return intensity + rng.normal(0.0, sigma), sigma
