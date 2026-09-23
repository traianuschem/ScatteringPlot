"""
Marginale Likelihood der (G)IFT — Bayes'sche IFT nach Hansen (2000).

Bei festen nichtlinearen Parametern θ = (d, λ, Dmax) hängt das Modell linear von den
Spline-Koeffizienten c ab. Mit der Glättungs-Priorverteilung
    p(c | λ) ∝ det(λK)^{1/2} · exp(−½ λ cᵀKc)
und gaußschem Messfehler lässt sich c analytisch herausintegrieren:

    log p(I | θ) = −½ χ²(ĉ) − ½ λ ĉᵀKĉ − ½ log det(B + λK) + ½ log det(λK)
                   − ½ M' log 2π − Σ log σ

mit B = AᵀWA, (B + λK)ĉ = AᵀW·I und M' = M (ohne Untergrund) bzw. M − 1 (Untergrund mit
flacher Priorverteilung, analytisch herausprojiziert wie in der IFT). DREAM muss damit nur
die wenigen nichtlinearen Parameter abtasten.

λ wird wie in der IFT relativ angegeben: λ = λ_rel · tr(B)/tr(K). Abgetastet wird
log₁₀ λ_rel; die Transformation hat die Jacobi-Determinante 1, die Priorverteilung ist
also auch in log λ gleichverteilt (mit parameterabhängigem Bereich).

Dmax als Parameter: Die Knoten skalieren mit Dmax, daher gilt
    ψ_ν(q; Dmax) = Dmax · g_ν(q·Dmax),   g_ν(x) = 4π ∫₀¹ φ̃_ν(u) sin(xu)/(xu) du.
g_ν und g_ν' werden einmal auf einem feinen x-Gitter tabelliert und kubisch (Hermite)
interpoliert; ein Wechsel von Dmax kostet dann O(M·N) statt einer neuen Quadratur
(relativer Fehler ~10⁻⁸).

Alle Auswertungen sind vektorisiert: θ hat die Form (K, d), das Ergebnis (K,).
"""

import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .ift import IFTSettings, regularization_matrix, K_GLATTER
from .splines import SplineBasis
from .transform import cached_design_matrix, FOUR_PI, _points_per_interval
from .structure_factors import get_model

LOG_LAMBDA = 'log_lambda'     # log₁₀ λ_rel
DMAX = 'dmax'                 # nm

_TABLE_DX = 0.05              # Gitterabstand der g_ν-Tabelle in x = q·Dmax
_LOG_2PI = float(np.log(2.0 * np.pi))


# ---------------------------------------------------------------------------
# Skalierte Spline-Transformierte g_ν(x) für variables Dmax
# ---------------------------------------------------------------------------

class ScaledBasisTable:
    """Tabelle von g_ν(x) und g_ν'(x) für x ∈ [0, x_max] mit kubischer Hermite-Interpolation."""

    def __init__(self, n_splines, x_max, dx=_TABLE_DX):
        self.n = int(n_splines)
        self.dx = float(dx)
        n_x = int(np.ceil(max(x_max, 1.0) / self.dx)) + 2
        self.x = self.dx * np.arange(n_x)
        basis = SplineBasis(1.0, self.n)
        u, w = basis.quadrature(_points_per_interval(self.x[-1], basis.h))
        phi = basis.evaluate(u) * w[:, None]                       # (P, N)
        phi_u = phi * u[:, None]
        self.g = np.empty((n_x, self.n))
        self.dg = np.empty((n_x, self.n))
        for s in range(0, n_x, 1024):                               # speicherschonend
            y = np.outer(self.x[s:s + 1024], u)                     # (X, P)
            self.g[s:s + 1024] = FOUR_PI * (np.sinc(y / np.pi) @ phi)
            with np.errstate(invalid='ignore', divide='ignore'):
                dj = np.where(np.abs(y) > 1e-4, (y * np.cos(y) - np.sin(y)) / (y * y), -y / 3.0)
            self.dg[s:s + 1024] = FOUR_PI * (dj @ phi_u)

    @property
    def x_max(self):
        return float(self.x[-1])

    def design(self, q, dmax):
        """ψ_ν(q; Dmax) für ein oder mehrere Dmax: (M, N) bzw. (K, M, N)."""
        q = np.asarray(q, dtype=float)
        d = np.asarray(dmax, dtype=float)
        scalar = d.ndim == 0
        d = np.atleast_1d(d)
        x = d[:, None] * q[None, :]                                  # (K, M)
        if np.any(x > self.x_max) or np.any(x < 0):
            raise ValueError("q·Dmax außerhalb der Tabelle")
        t = x / self.dx
        i = np.minimum(t.astype(int), len(self.x) - 2)
        t = (t - i)[..., None]
        h00 = (1 + 2 * t) * (1 - t) ** 2
        h10 = t * (1 - t) ** 2
        h01 = t * t * (3 - 2 * t)
        h11 = t * t * (t - 1)
        g = (h00 * self.g[i] + h01 * self.g[i + 1]
             + self.dx * (h10 * self.dg[i] + h11 * self.dg[i + 1]))
        A = d[:, None, None] * g
        return A[0] if scalar else A


# ---------------------------------------------------------------------------
# Posterior-Raum und marginale Likelihood
# ---------------------------------------------------------------------------

@dataclass
class ParameterSpace:
    """Abgetastete Parameter mit (gleichverteilter) Priorverteilung im Kasten [lower, upper]
    und optionalem gaußschem Faktor (z. B. φ aus der Einwaage)."""
    names: List[str]
    lower: np.ndarray
    upper: np.ndarray
    gaussian: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self):
        self.lower = np.asarray(self.lower, dtype=float)
        self.upper = np.asarray(self.upper, dtype=float)
        if not np.all(self.upper > self.lower):
            raise ValueError("Priorgrenzen: obere Grenze muss größer als die untere sein")

    @property
    def dim(self):
        return len(self.names)

    def to_unit(self, theta):
        return (np.asarray(theta, dtype=float) - self.lower) / (self.upper - self.lower)

    def from_unit(self, u):
        return self.lower + np.asarray(u, dtype=float) * (self.upper - self.lower)

    def log_prior(self, theta):
        theta = np.atleast_2d(theta)
        inside = np.all((theta >= self.lower) & (theta <= self.upper), axis=1)
        lp = np.where(inside, 0.0, -np.inf)
        for name, (mu, sd) in self.gaussian.items():
            if name in self.names and sd > 0:
                k = self.names.index(name)
                lp = lp - 0.5 * ((theta[:, k] - mu) / sd) ** 2
        return lp

    def prior_std(self):
        """Standardabweichung der Priorverteilung je Parameter (für das Bestimmbarkeits-Flag)."""
        std = (self.upper - self.lower) / np.sqrt(12.0)
        for name, (_mu, sd) in self.gaussian.items():
            if name in self.names and sd > 0:
                k = self.names.index(name)
                std[k] = min(std[k], sd)
        return std

    def to_dict(self):
        return {'names': list(self.names), 'lower': self.lower.tolist(),
                'upper': self.upper.tolist(),
                'gaussian': {k: list(v) for k, v in self.gaussian.items()}}


class MarginalLikelihood:
    """log p(θ | I) = log Prior(θ) + log p(I | θ) für GIFT/IFT, batch-fähig und picklebar.

    Args:
        q, intensity, sigma: Daten im Fitbereich
        ift_settings: Basis (N), K-Typ, Untergrund; Dmax und λ gelten, wenn sie nicht
            abgetastet werden
        model_key: Strukturfaktor-Modell ('none' für die reine IFT)
        values: Werte aller Modellparameter (nicht abgetastete bleiben fest)
        space: abgetastete Parameter (Modellparameter, LOG_LAMBDA, DMAX)
    """

    def __init__(self, q, intensity, sigma, ift_settings: IFTSettings, model_key: str,
                 values: Dict[str, float], space: ParameterSpace, lam_rel: float):
        self.q = np.asarray(q, dtype=float)
        self.I = np.asarray(intensity, dtype=float)
        self.s = np.asarray(sigma, dtype=float)
        self.settings = ift_settings
        self.model_key = model_key
        self.values = {k: float(v) for k, v in values.items()}
        self.space = space
        self.lam_rel = float(lam_rel)
        model = get_model(model_key)
        unknown = [n for n in space.names
                   if n not in (LOG_LAMBDA, DMAX) and n not in model.defaults()]
        if unknown:
            raise ValueError(f"Unbekannte Parameter: {unknown}")
        self.token = uuid.uuid4().hex
        self._cache = None

    def __getstate__(self):
        state = dict(self.__dict__)
        state['_cache'] = None                  # wird im Worker neu aufgebaut
        return state

    # --- Vorbereitung ------------------------------------------------------------

    @property
    def samples_dmax(self):
        return DMAX in self.space.names

    def _prepared(self):
        if self._cache is not None:
            return self._cache
        st = self.settings
        n = st.n_splines
        K = regularization_matrix(n, st.k_type)
        if st.k_type == K_GLATTER:                   # singulär: winziger Ridge wie in der IFT
            K = K + 1e-10 * np.mean(np.diag(K)) * np.eye(n)
        sign, logdet_k = np.linalg.slogdet(K)
        c = {'K': K, 'trace_k': float(np.trace(K)), 'logdet_k': float(logdet_k),
             'yw': self.I / self.s}
        if self.samples_dmax:
            d_hi = self.space.upper[self.space.names.index(DMAX)]
            c['table'] = ScaledBasisTable(n, float(self.q.max()) * d_hi * 1.001)
        else:
            c['A0'] = np.asarray(cached_design_matrix(self.q, st.dmax, n))
        if st.background:
            w = 1.0 / self.s
            c['w'] = w
            c['w_norm2'] = float(w @ w)
            c['yw_p'] = c['yw'] - w * (w @ c['yw']) / c['w_norm2']
            m_eff = len(self.q) - 1
        else:
            c['yw_p'] = c['yw']
            m_eff = len(self.q)
        c['const'] = -0.5 * m_eff * _LOG_2PI - float(np.sum(np.log(self.s)))
        self._cache = c
        return c

    # --- Parameter ---------------------------------------------------------------

    def split(self, theta):
        """θ (K, d) → (Modellwerte als Arrays, λ_rel (K,), Dmax (K,))."""
        theta = np.atleast_2d(np.asarray(theta, dtype=float))
        k = len(theta)
        vals = {n: np.full(k, v) for n, v in self.values.items()}
        lam_rel = np.full(k, self.lam_rel)
        dmax = np.full(k, float(self.settings.dmax))
        for j, name in enumerate(self.space.names):
            if name == LOG_LAMBDA:
                lam_rel = 10.0 ** theta[:, j]
            elif name == DMAX:
                dmax = theta[:, j].copy()
            else:
                vals[name] = theta[:, j].copy()
        return vals, lam_rel, dmax

    def structure_factors(self, vals, k):
        model = get_model(self.model_key)
        if not model.params:
            return np.ones((k, len(self.q)))
        with np.errstate(all='ignore'):
            S = model.evaluate(self.q, vals)
        return np.broadcast_to(np.atleast_2d(S), (k, len(self.q)))

    def design(self, dmax):
        c = self._prepared()
        if 'table' in c:
            return c['table'].design(self.q, dmax)                    # (K, M, N)
        return np.broadcast_to(c['A0'], (len(dmax),) + c['A0'].shape)

    # --- Auswertung --------------------------------------------------------------

    def log_posterior(self, theta):
        """log Prior + log Likelihood für θ (K, d); −∞ außerhalb der Priorgrenzen, bei
        S(q) < 0 oder numerischem Versagen."""
        theta = np.atleast_2d(np.asarray(theta, dtype=float))
        lp = self.space.log_prior(theta)
        ok = np.isfinite(lp)
        out = np.full(len(theta), -np.inf)
        if ok.any():
            out[ok] = lp[ok] + self.solve(theta[ok])['log_likelihood']
        return out

    def solve(self, theta, want_solution=False):
        """Marginale Likelihood (und auf Wunsch ĉ, Cholesky-Faktor, Designmatrix) je Zeile."""
        c = self._prepared()
        theta = np.atleast_2d(np.asarray(theta, dtype=float))
        k = len(theta)
        vals, lam_rel, dmax = self.split(theta)
        S = self.structure_factors(vals, k)
        valid = np.all(np.isfinite(S), axis=1) & np.all(S >= 0, axis=1) & (dmax > 0)
        logl = np.full(k, -np.inf)
        md = np.full(k, np.inf)
        res = {'log_likelihood': logl, 'md': md}
        if want_solution:
            n = self.settings.n_splines
            res.update(c_hat=np.full((k, n), np.nan), L=np.full((k, n, n), np.nan),
                       lam=np.full(k, np.nan), S=np.asarray(S, dtype=float).copy(),
                       dmax=dmax, A=None)
        if not valid.any():
            return res
        idx = np.nonzero(valid)[0]
        A = self.design(dmax[idx])                                     # (K', M, N)
        Aw = A * (S[idx] / self.s[None, :])[..., None]
        if self.settings.background:
            w = c['w']
            Aw = Aw - w[None, :, None] * (np.matmul(w, Aw) / c['w_norm2'])[:, None, :]
        AwT = np.swapaxes(Aw, 1, 2)
        B = np.matmul(AwT, Aw)
        b = np.matmul(AwT, c['yw_p'])
        lam = lam_rel[idx] * np.trace(B, axis1=1, axis2=2) / c['trace_k']
        H = B + lam[:, None, None] * c['K'][None, :, :]
        n = H.shape[-1]
        for j, row in enumerate(idx):
            # zeilenweise (und damit unabhängig von der Stapelgröße bitgleich)
            try:
                L = np.linalg.cholesky(H[j])
            except np.linalg.LinAlgError:
                continue
            if not (lam[j] > 0 and np.isfinite(lam[j])):
                continue
            y = _solve_lower(L, b[j])
            ch = _solve_upper(L.T, y)
            r = Aw[j] @ ch - c['yw_p']
            chi2 = float(r @ r)
            reg = float(lam[j] * (ch @ c['K'] @ ch))
            logdet_h = 2.0 * float(np.sum(np.log(np.diag(L))))
            logdet_lk = n * float(np.log(lam[j])) + c['logdet_k']
            logl[row] = c['const'] - 0.5 * (chi2 + reg) - 0.5 * logdet_h + 0.5 * logdet_lk
            md[row] = chi2 / len(self.q)
            if want_solution:
                res['c_hat'][row] = ch
                res['L'][row] = L
                res['lam'][row] = lam[j]
        if want_solution:
            res['A'] = (idx, A)
        return res


def _solve_lower(L, b):
    from scipy.linalg import solve_triangular
    return solve_triangular(L, b, lower=True, check_finite=False)


def _solve_upper(U, b):
    from scipy.linalg import solve_triangular
    return solve_triangular(U, b, lower=False, check_finite=False)


# ---------------------------------------------------------------------------
# Auswertung im Prozess-Pool
# ---------------------------------------------------------------------------

_WORKER_CACHE: "OrderedDict[str, MarginalLikelihood]" = OrderedDict()


def _cached(ev: MarginalLikelihood) -> MarginalLikelihood:
    """Pro Prozess eine vorbereitete Instanz je Token (Tabelle/Designmatrix nur einmal)."""
    hit = _WORKER_CACHE.get(ev.token)
    if hit is None:
        _WORKER_CACHE[ev.token] = hit = ev
        while len(_WORKER_CACHE) > 4:
            _WORKER_CACHE.popitem(last=False)
    return hit


def _log_posterior_task(task):
    ev, theta = task
    return _cached(ev).log_posterior(theta)


def evaluate_log_posterior(ev: MarginalLikelihood, theta, n_workers: int, chunk: int):
    """log p(θ | I) für viele θ: im Pool (n_workers ≥ 1) oder im Hauptprozess (0).

    Die Aufteilung in Blöcke fester Größe hängt nicht von der Worker-Zahl ab; zusammen mit
    dem einfädigen BLAS im Pool sind die Ergebnisse damit für jede Worker-Zahl bitgleich.
    """
    from . import parallel
    theta = np.atleast_2d(np.asarray(theta, dtype=float))
    blocks = [theta[i:i + chunk] for i in range(0, len(theta), max(1, int(chunk)))]
    if n_workers >= 1:
        results = parallel.get_pool(n_workers).run(_log_posterior_task,
                                                    [(ev, b) for b in blocks])
    else:
        results = [_cached(ev).log_posterior(b) for b in blocks]
    return np.concatenate(results) if results else np.empty(0)
