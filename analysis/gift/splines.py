"""
Kubische B-Spline-Basis für p(r) auf [0, Dmax] [Glatter 1977, Gl. 9].

Verwendet wird eine geklemmte (clamped) kubische B-Spline-Basis mit äquidistanten
inneren Knoten (Abstand h = Dmax / (N − 1)). Der erste und der letzte Basisspline
(die als einzige bei r = 0 bzw. r = Dmax von null verschieden sind) werden
weggelassen. Damit gilt p(0) = p(Dmax) = 0, die Steigung an den Rändern bleibt aber
frei — wichtig für Teilchen mit p(r) ∝ r (Ketten) oder steilem Anstieg (Stäbchen).

Mit `left_free=True` (Dicken-Verteilung p_t, v8.0) bleibt der erste Basisspline erhalten:
p(0) ist dann frei, nur p(Dmax) = 0.

Skalierungseigenschaft (für die Dmax-Variation in DREAM): Die Knoten skalieren linear
mit Dmax, also φ_ν(r) = φ̃_ν(r / Dmax) mit der Basis φ̃_ν auf [0, 1].
"""

import numpy as np
from scipy.interpolate import BSpline

DEGREE = 3


class SplineBasis:
    """N kubische B-Splines auf [0, Dmax] mit p(0) = p(Dmax) = 0 (bzw. nur p(Dmax) = 0)."""

    def __init__(self, dmax, n_splines, left_free=False):
        if dmax <= 0:
            raise ValueError("Dmax muss positiv sein")
        if n_splines < 3:
            raise ValueError("Mindestens 3 Splines erforderlich")
        self.dmax = float(dmax)
        self.n = int(n_splines)
        self.left_free = bool(left_free)
        # vollständige Basis: n_intervals + 3 Splines; weggelassen werden 2 (bzw. 1)
        self.n_intervals = self.n - 2 if self.left_free else self.n - 1
        self._keep = slice(0, -1) if self.left_free else slice(1, -1)
        self.h = self.dmax / self.n_intervals
        inner = self.h * np.arange(self.n_intervals + 1)
        inner[-1] = self.dmax
        self.knots = np.concatenate([np.zeros(DEGREE), inner, np.full(DEGREE, self.dmax)])

    def evaluate(self, r):
        """Basiswerte als Matrix (len(r) × N); außerhalb [0, Dmax] null."""
        r = np.asarray(r, dtype=float)
        out = np.zeros((len(r), self.n))
        inside = (r >= 0.0) & (r <= self.dmax)
        if inside.any():
            full = BSpline.design_matrix(r[inside], self.knots, DEGREE).toarray()
            out[inside] = full[:, self._keep]
        return out

    def evaluate_derivative(self, r):
        """Ableitungen dφ_ν/dr als Matrix (len(r) × N); außerhalb [0, Dmax] null."""
        r = np.asarray(r, dtype=float)
        out = np.zeros((len(r), self.n))
        inside = (r >= 0.0) & (r <= self.dmax)
        if inside.any():
            n_full = len(self.knots) - DEGREE - 1
            deriv = BSpline(self.knots, np.eye(n_full), DEGREE).derivative()
            out[inside] = deriv(r[inside])[:, self._keep]
        return out

    def quadrature(self, points_per_interval=16):
        """Gauss-Legendre-Knoten und -Gewichte auf [0, Dmax], stückweise pro Knotenintervall.

        Auf jedem Intervall ist die Basis ein kubisches Polynom; die Quadratur ist damit
        für Momente bis Grad 2·n−4 exakt.
        """
        x, w = np.polynomial.legendre.leggauss(int(points_per_interval))
        edges = self.h * np.arange(self.n_intervals + 1)
        mid = 0.5 * (edges[:-1] + edges[1:])
        half = 0.5 * self.h
        r = (mid[:, None] + half * x[None, :]).ravel()
        weights = np.tile(half * w, self.n_intervals)
        return r, weights
