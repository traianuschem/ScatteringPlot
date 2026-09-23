"""
Boltzmann-Simplex-Simulated-Annealing (BSSA) nach Bergmann, Fritz & Glatter (2000).

Nelder-Mead-Simplex mit „temperaturabhängigen“ Fluktuationen (entspricht `amebsa`
aus Numerical Recipes, Press et al. 1992):

- Zu jedem Vertex-Wert wird eine positive, logarithmisch verteilte Zufallsgröße
  −T·ln(u) addiert, vom Wert jedes Versuchspunkts eine solche subtrahiert [B00 Gl. 5].
  Echte Abwärtsschritte werden immer, Aufwärtsschritte manchmal akzeptiert.
- Abkühlschema: T ← (1 − ε)·T nach j Zügen, ε = 0.2, j = 20 … 40 je nach Dimension [B00].
- Start-T aus der Streuung der Funktionswerte der Anfangsvertices [B00].
- Bei T = 0 geht das Verfahren in den reinen Simplex über (abschließende Politur).

Gearbeitet wird in normierten Koordinaten x ∈ [0, 1]ⁿ; Punkte außerhalb erhalten
f = ∞ („unphysikalische Parameter“ [B00]).
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

TINY = 1e-12


class BSSACancelled(Exception):
    """Wird ausgelöst, wenn der Fortschritts-Callback False zurückgibt."""


@dataclass
class BSSASettings:
    seed: int = 12345
    cooling: float = 0.2                 # ε  [B00]
    moves_per_temperature: Optional[int] = None   # j; None → 20 + 5·(n−1), max. 40
    t_stop_rel: float = 1e-4             # Abbruch, wenn T < t_stop_rel·T0
    max_evals: int = 4000
    initial_step: float = 0.15           # Kantenlänge des Startsimplex (normiert)
    # Start-T aus der Streuung von f über Startsimplex UND eine kleine Zufallsprobe des
    # erlaubten Bereichs (probe_per_dim·n Punkte). Die Simplex-Streuung allein ist bei
    # stark multimodalen Flächen zu klein, um lokale Minima wieder zu verlassen.
    probe_per_dim: int = 10
    polish_evals: int = 400
    ftol: float = 1e-7

    def moves(self, ndim):
        if self.moves_per_temperature:
            return int(self.moves_per_temperature)
        return int(min(40, 20 + 5 * (ndim - 1)))

    def to_dict(self):
        return dict(self.__dict__)


@dataclass
class BSSAResult:
    x: np.ndarray
    f: float
    n_evals: int
    t0: float
    history: List[dict] = field(default_factory=list)
    converged: bool = False


def _inside(x):
    return np.all(x >= 0.0) and np.all(x <= 1.0)


def minimize(func: Callable, x0, settings: BSSASettings = None,
             callback: Optional[Callable] = None) -> BSSAResult:
    """Minimiert func(x) über x ∈ [0, 1]ⁿ mit BSSA.

    Args:
        func: Zielfunktion (z. B. MD), darf ∞ zurückgeben
        x0: Startpunkt (normiert)
        callback: callback(n_evals, T, f_best, x_best) → False bricht ab (BSSACancelled)
    """
    st = settings or BSSASettings()
    rng = np.random.default_rng(st.seed)
    x0 = np.clip(np.asarray(x0, dtype=float), 0.0, 1.0)
    ndim = len(x0)
    n_evals = [0]
    best = {'x': x0.copy(), 'f': np.inf}

    def f(x):
        n_evals[0] += 1
        val = float(func(x)) if _inside(x) else np.inf
        if not np.isfinite(val):
            val = np.inf
        if val < best['f']:
            best['f'], best['x'] = val, x.copy()
        return val

    # Startsimplex: x0 und x0 ± step·e_i (Schritt nach innen gespiegelt)
    p = np.tile(x0, (ndim + 1, 1))
    for i in range(ndim):
        step = st.initial_step if x0[i] + st.initial_step <= 1.0 else -st.initial_step
        p[i + 1, i] += step
    y = np.array([f(v) for v in p])
    if not np.any(np.isfinite(y)):
        raise ValueError("Die Zielfunktion ist an allen Startpunkten unendlich "
                         "(Startwerte außerhalb der physikalischen Grenzen?)")
    probe = [f(v) for v in rng.random((st.probe_per_dim * ndim, ndim))]
    finite = np.array([v for v in list(y) + probe if np.isfinite(v)])
    spread = float(np.std(finite)) if len(finite) > 1 else 0.0
    t0 = spread if spread > 0 else 0.01 * max(abs(finite.min()), TINY)
    history = []

    def amebsa(temperature, budget):
        """Ein Temperaturschritt (NR amebsa); gibt True zurück, wenn der Simplex konvergiert ist."""
        nonlocal p, y
        psum = p.sum(axis=0)
        tt = -temperature

        def amotsa(ihi, yhi, fac):
            nonlocal psum
            fac1 = (1.0 - fac) / ndim
            fac2 = fac1 - fac
            ptry = psum * fac1 - p[ihi] * fac2
            ytry = f(ptry)
            yflu = ytry - tt * np.log(rng.random() + TINY)       # Fluktuation abziehen
            if yflu < yhi:
                y[ihi] = ytry
                psum = psum + ptry - p[ihi]
                p[ihi] = ptry
            return yflu

        iters = budget
        while True:
            fluct = y + tt * np.log(rng.random(ndim + 1) + TINY)  # positive Fluktuation
            order = np.argsort(fluct)
            ilo, ihi, inhi = order[0], order[-1], order[-2]
            ylo, yhi, ynhi = fluct[ilo], fluct[ihi], fluct[inhi]
            if np.isfinite(yhi) and np.isfinite(ylo):
                rtol = 2.0 * abs(yhi - ylo) / (abs(yhi) + abs(ylo) + TINY)
            else:
                rtol = np.inf
            if rtol < st.ftol:
                return True
            if iters <= 0 or n_evals[0] >= st.max_evals:
                return False
            iters -= 2
            ytry = amotsa(ihi, yhi, -1.0)                          # Reflexion
            if ytry <= ylo:
                amotsa(ihi, ytry, 2.0)                             # Expansion
            elif ytry >= ynhi:
                ysave = ytry
                ytry = amotsa(ihi, ysave, 0.5)                     # Kontraktion
                if ytry >= ysave:
                    for i in range(ndim + 1):                      # Mehrfach-Kontraktion
                        if i != ilo:
                            p[i] = 0.5 * (p[i] + p[ilo])
                            y[i] = f(p[i])
                    iters -= ndim
                    psum = p.sum(axis=0)
            else:
                iters += 1

    temperature = t0
    moves = st.moves(ndim)
    while temperature > st.t_stop_rel * t0 and n_evals[0] < st.max_evals:
        amebsa(temperature, moves)
        history.append({'evals': n_evals[0], 'T': temperature, 'f_best': best['f'],
                        'x_best': best['x'].tolist()})
        if callback is not None and callback(n_evals[0], temperature, best['f'],
                                             best['x']) is False:
            raise BSSACancelled()
        temperature *= (1.0 - st.cooling)

    # Politur bei T = 0 (reiner Simplex), ausgehend vom besten je gefundenen Punkt
    p = np.tile(best['x'], (ndim + 1, 1))
    for i in range(ndim):
        step = 0.02 if best['x'][i] + 0.02 <= 1.0 else -0.02
        p[i + 1, i] += step
    y = np.array([f(v) for v in p])
    converged = amebsa(0.0, st.polish_evals)
    history.append({'evals': n_evals[0], 'T': 0.0, 'f_best': best['f'],
                    'x_best': best['x'].tolist()})
    if callback is not None:
        callback(n_evals[0], 0.0, best['f'], best['x'])
    return BSSAResult(x=best['x'], f=best['f'], n_evals=n_evals[0], t0=t0,
                      history=history, converged=bool(converged))
