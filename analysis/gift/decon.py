"""
DECON: radiales Kontrastprofil als Faltungswurzel der Abstandsverteilung
[Glatter 1981; Glatter & Hainisch 1984; Mittelbach & Glatter 1998].

Für zentrosymmetrische Teilchen gilt p(r) = r^(dim−1)·γ(r) mit der Autokorrelation
γ(r) = Δρ * Δρ (dim = 3 Kugel, 2 Zylinderquerschnitt, 1 Lamelle) [G81 Gl. 2]. Gesucht ist
Δρ auf [0, R], R = Dmax/2 (Normierung wie die IFT-Kerne in kernels.py).

**Überlappungsintegrale** [GH84, Anhang]: Für Stufen i (e_{i−1} < x < e_i) ist

    V_ik(r) = r^(dim−1) [μ(e_i, e_k) − μ(e_i, e_{k−1}) − μ(e_{i−1}, e_k) + μ(e_{i−1}, e_{k−1})]

mit μ(R₁, R₂; r) dem Maß (Volumen, Fläche, Länge) des Schnitts zweier Kugeln, Kreise
bzw. Strecken mit Radien R₁, R₂ im Mittelpunktsabstand r [GH84 Gl. A3–A5]. Damit ist
p(r) = cᵀV(r)c exakt und für beliebige Stufenbreiten gültig.

**Basis:**
- `splines` (Standard, [MG98 §2.2]): kubische B-Splines mit dem Knotenabstand der IFT
  [G81: Stufenbreite = Knotenabstand], intern in feine Stufen zerlegt (4 je Intervall);
  V_spline = Sᵀ V_Stufen S.
- `steps` [G81, GH84]: äquidistante Stufen.

**Anpassung** [G81 Gl. 7–19]: gewichtete kleinste Quadrate gegen p(r) ± σ, iterativ
linearisiert (Levenberg-Marquardt), Stabilisierung B + λK mit K aus ersten Differenzen,
λ nach der Wendepunkt-Methode [G81 §III.2]. Start: konstantes Profil mit ∫p̃ = ∫p
[G81 Gl. 5]. Zusätzlich (Erweiterung) weitere Startprofile, um gleich gute, aber
verschiedene Lösungen zu erkennen.

**Polydispersität** [MG98 §2.3]: Für eine Anzahlverteilung D(P, x) mit x = R/R_m (Modus
bei x = 1) wird die Überlappungsmatrix gemittelt,

    V^P(r) = ∫ D(P, x) x^(2dim−1) V(r/x) dx                         [MG98 Gl. 9],

und Δρ ist dann das Profil der Referenzpopulation. Die Breite wird über das Minimum der
mittleren Abweichung bestimmt (Scan von P, [MG98 Fig. 2d]). Verteilung: verschobene
Schulz-Verteilung D ∝ x^t e^(−t·x), t = 1/σ² − 1 [MG98 Gl. 10], oder Gauß.
P = σ·√(2 ln 2) (HWHM, [MG98 Gl. 11]).

**Stufenmodell** [GH84 §II]: wenige Stufen (2–4) mit variablen Breiten; Grenzen und
Höhen werden optimiert (Gitter + Simplex).

**Kontrolle im Streuraum** [MG98]: I(q) = Σ D x^(2dim) A²(qx) (mit den IFT-Vorfaktoren)
gegen die entschmierte Kurve der IFT bzw. den Formfaktor der GIFT.

[G81] Glatter, J. Appl. Cryst. 14 (1981) 101. [GH84] Glatter & Hainisch, J. Appl. Cryst.
17 (1984) 435. [MG98] Mittelbach & Glatter, J. Appl. Cryst. 31 (1998) 600.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import least_squares, minimize
from scipy.special import j1

from .kernels import PDDF, CROSS_SECTION, THICKNESS
from .ift import settings_kind

GEOMETRIES = {PDDF: 'sphere', CROSS_SECTION: 'cylinder', THICKNESS: 'lamella'}
DIM = {'sphere': 3, 'cylinder': 2, 'lamella': 1}
BASIS_SPLINES = 'splines'
BASIS_STEPS = 'steps'
POLY_NONE, POLY_FIXED, POLY_SCAN = 'none', 'fixed', 'scan'
DIST_SCHULZ, DIST_GAUSS = 'schulz', 'gauss'
FINE_STEPS = 4                                   # Stufen je Knotenintervall [MG98]
ALT_CHI2_FACTOR, ALT_CHI2_ABS = 1.5, 0.5         # „gleich gut“: χ² ≤ 1.5·χ²_best + 0.5
ALT_DIFF = 0.2                                   # „verschieden“: max|Δρ| ≥ 0.2·max|ρ|
HWHM = np.sqrt(2.0 * np.log(2.0))


class DeconCancelled(Exception):
    """Abbruch über den Fortschritts-Callback (Rückgabe False)."""


@dataclass
class DeconSettings:
    basis: str = BASIS_SPLINES
    n_intervals: Optional[int] = None    # None: Knotenabstand der IFT [G81]
    lam: object = 'auto'                 # 'auto' (Wendepunkt) oder fester λ_rel
    lam_grid: tuple = (1e-8, 1e3, 34)
    # Wendepunkt: Plateau von N_c vor dem steilen MD-Anstieg [G81 §III.2]. χ² gegen p(r)
    # (korrelierte Fehler) steigt schon vor dem Plateau merklich, daher Toleranz 100 %
    md_tolerance: float = 1.0
    plateau_slope: float = 0.3
    polydispersity: str = POLY_NONE      # 'none', 'fixed', 'scan'
    distribution: str = DIST_SCHULZ
    sigma: float = 0.0                   # relative Standardabweichung (für 'fixed')
    p_scan: tuple = (0.0, 0.40, 21)      # P (HWHM-Maß) von … bis …, Anzahl [MG98: 0–40 %]
    scan_lam_points: int = 18            # gröberes λ-Gitter je P im Scan
    n_random: int = 4                    # zusätzliche Zufallsstarts (Mehrdeutigkeit)
    seed: int = 20260924
    n_r: int = 121
    sigma_floor: float = 0.05            # σ_k ≥ floor · max σ_p (Ränder: σ_p → 0)

    def to_dict(self):
        return asdict(self)


@dataclass
class DeconResult:
    kind: str
    geometry: str
    radius: float
    settings: DeconSettings
    x: np.ndarray                        # Radius bzw. Abstand von der Mittelebene
    rho: np.ndarray
    rho_err: np.ndarray
    coefficients: np.ndarray
    edges: Optional[np.ndarray]          # Stufengrenzen (Basis 'steps')
    r: np.ndarray                        # p(r)-Gitter der Anpassung
    p_target: np.ndarray
    p_sigma: np.ndarray
    p_fit: np.ndarray
    chi2_red: float                      # χ²/M gegen p(r)
    md_pr: float                         # MD = √(χ²/M) [G81 Gl. 20, MG98 Gl. 4]
    lam_rel: float
    inflexion_found: bool
    sigma_poly: float                    # relative Standardabweichung der Größenverteilung
    q: np.ndarray
    i_model: np.ndarray                  # I(q) aus dem Profil (inkl. S(q), Untergrund)
    i_reference: np.ndarray              # entschmierte IFT-Kurve (bzw. GIFT-Fit)
    md_q: float                          # √(mean(((I_model − I_ref)/σ)²)) [MG98]
    md_data: float                       # χ²/M gegen die Messdaten
    md_ift: float                        # χ²/M der IFT
    alternatives: List[Dict] = field(default_factory=list)
    starts: List[Dict] = field(default_factory=list)
    lam_scan: Optional[Dict] = None
    poly_scan: Optional[Dict] = None     # {'P', 'sigma', 'md_pr', 'md_q', 'index'}
    step_model: Optional[Dict] = None
    flags: list = field(default_factory=list)

    @property
    def p_percent(self):
        return 100.0 * HWHM * self.sigma_poly

    def results_summary(self):
        out = {'geometry': self.geometry, 'basis': self.settings.basis,
               'radius_nm': self.radius, 'chi2_red': self.chi2_red, 'md_pr': self.md_pr,
               'md_q': self.md_q, 'md_data': self.md_data, 'md_ift': self.md_ift,
               'lambda_rel': self.lam_rel, 'inflexion_found': self.inflexion_found,
               'polydispersity': self.settings.polydispersity,
               'distribution': self.settings.distribution,
               'sigma_poly': self.sigma_poly, 'P_percent': self.p_percent,
               'n_alternatives': len(self.alternatives),
               'alternatives_chi2': [a['chi2_red'] for a in self.alternatives],
               'rho_center': float(self.rho[0]), 'rho_min': float(np.min(self.rho)),
               'rho_max': float(np.max(self.rho))}
        if self.step_model:
            sm = self.step_model
            out['step_model'] = {'edges_nm': [float(e) for e in sm['edges']],
                                 'heights': [float(h) for h in sm['heights']],
                                 'chi2_red': sm['chi2_red'], 'md_q': sm['md_q']}
        return out


# ---------------------------------------------------------------------------
# Überlappungsintegrale [GH84, Anhang]
# ---------------------------------------------------------------------------

def overlap_measure(dim, R1, R2, r):
    """μ(R₁, R₂; r): Maß des Schnitts zweier Kugeln (dim 3), Kreise (2) bzw. Strecken (1)
    mit Radien R₁, R₂ und Mittelpunktsabstand r ≥ 0 [GH84 Gl. A1, A3–A5]."""
    R1, R2, r = np.broadcast_arrays(np.asarray(R1, float), np.asarray(R2, float),
                                    np.asarray(r, float))
    out = np.zeros(r.shape)
    Rm = np.minimum(R1, R2)
    full = r <= np.abs(R1 - R2)
    lens = ~full & (r < R1 + R2)
    if dim == 3:
        out[full] = 4.0 / 3.0 * np.pi * Rm[full] ** 3
        a, b, d = R1[lens], R2[lens], r[lens]
        out[lens] = np.pi * (a + b - d) ** 2 * (d * d + 2 * d * (a + b) - 3 * (a - b) ** 2) / (12 * d)
    elif dim == 2:
        out[full] = np.pi * Rm[full] ** 2
        a, b, d = R1[lens], R2[lens], r[lens]
        c1 = np.clip((d * d + a * a - b * b) / (2 * d * a), -1.0, 1.0)
        c2 = np.clip((d * d + b * b - a * a) / (2 * d * b), -1.0, 1.0)
        k = np.maximum((-d + a + b) * (d + a - b) * (d - a + b) * (d + a + b), 0.0)
        out[lens] = a * a * np.arccos(c1) + b * b * np.arccos(c2) - 0.5 * np.sqrt(k)
    else:
        out[full] = 2.0 * Rm[full]
        out[lens] = R1[lens] + R2[lens] - r[lens]
    return out


def step_forms(edges, r, geometry):
    """V(r) (len(r), N, N) für Stufen mit Grenzen edges = [0, e₁, …, e_N]; p = cᵀVc."""
    dim = DIM[geometry]
    e = np.asarray(edges, dtype=float)
    r = np.asarray(r, dtype=float)
    U = overlap_measure(dim, e[None, :, None], e[None, None, :], r[:, None, None])
    V = U[:, 1:, 1:] - U[:, 1:, :-1] - U[:, :-1, 1:] + U[:, :-1, :-1]
    if dim > 1:
        V = V * r[:, None, None] ** (dim - 1)
    return V


def step_amplitudes(edges, q, geometry):
    """Amplituden a_k(q) der Stufen (Normierung wie die IFT-Kerne): A = Σ c_k a_k."""
    e = np.asarray(edges, dtype=float)
    q = np.asarray(q, dtype=float)
    x = np.outer(q, e)
    safe = np.where(x > 1e-6, x, 1.0)
    if geometry == 'sphere':
        f = np.where(x > 1e-6, 3 * (np.sin(safe) - safe * np.cos(safe)) / safe ** 3, 1.0)
        full = 4.0 / 3.0 * np.pi * e[None, :] ** 3 * f
    elif geometry == 'cylinder':
        f = np.where(x > 1e-6, 2 * j1(safe) / safe, 1.0)
        full = np.pi * e[None, :] ** 2 * f
    else:
        full = 2.0 * np.sinc(x / np.pi) * e[None, :]
    return full[:, 1:] - full[:, :-1]


def q_prefactor(q, geometry):
    q = np.asarray(q, dtype=float)
    if geometry == 'sphere':
        return np.ones_like(q)
    if geometry == 'cylinder':
        return np.pi / q
    return 2.0 * np.pi / q ** 2


# ---------------------------------------------------------------------------
# Profilbasis
# ---------------------------------------------------------------------------

class ProfileBasis:
    """Profil auf [0, R]: kubische B-Splines (beide Ränder frei) oder Stufen. Intern immer
    als Stufen (Grenzen `edges`) mit Transformationsmatrix S: Stufenhöhen = S·c."""

    def __init__(self, radius=None, n_intervals=None, kind=BASIS_SPLINES, edges=None):
        self.kind = kind
        self.knots = None
        if edges is not None:                        # Stufen mit variabler Breite [GH84]
            self.kind = BASIS_STEPS
            self.edges = np.asarray(edges, dtype=float)
            self.n = len(self.edges) - 1
            self.S = np.eye(self.n)
            self.R = float(self.edges[-1])
            return
        self.R = float(radius)
        n_int = max(int(n_intervals), 2)
        if kind == BASIS_STEPS:
            self.edges = np.linspace(0.0, self.R, n_int + 1)
            self.n = n_int
            self.S = np.eye(n_int)
        else:
            inner = np.linspace(0.0, self.R, n_int + 1)
            self.knots = np.concatenate([np.zeros(3), inner, np.full(3, self.R)])
            self.n = n_int + 3
            self.edges = np.linspace(0.0, self.R, FINE_STEPS * n_int + 1)
            mid = 0.5 * (self.edges[:-1] + self.edges[1:])
            self.S = BSpline.design_matrix(mid, self.knots, 3).toarray()

    def evaluate(self, x):
        """Profilbasis an x (len(x), n); außerhalb [0, R] null."""
        x = np.asarray(x, dtype=float).ravel()
        inside = (x >= 0) & (x <= self.R)
        if self.knots is not None:
            out = BSpline.design_matrix(np.clip(x, 0.0, self.R), self.knots, 3).toarray()
            out[~inside] = 0.0
            return out
        idx = np.clip(np.searchsorted(self.edges, x, side='right') - 1, 0, self.n - 1)
        out = np.zeros((len(x), self.n))
        out[np.nonzero(inside)[0], idx[inside]] = 1.0
        return out

    def volume_vector(self, geometry):
        """∫Δρ dV (Vorzeichen-Normierung) als Vektor in c."""
        e = self.edges
        shell = {3: 4.0 / 3.0 * np.pi * np.diff(e ** 3), 2: np.pi * np.diff(e ** 2),
                 1: 2.0 * np.diff(e)}[DIM[geometry]]
        return shell @ self.S


# ---------------------------------------------------------------------------
# Größenverteilung [MG98 §2.3]
# ---------------------------------------------------------------------------

def size_nodes(sigma, distribution=DIST_SCHULZ, n=41):
    """Knoten x = R/R_m und Gewichte der Anzahlverteilung (Modus bei x = 1)."""
    if sigma <= 1e-4:
        return np.array([1.0]), np.array([1.0])
    if distribution == DIST_GAUSS:
        x = np.linspace(max(1.0 - 4.0 * sigma, 1e-3), 1.0 + 4.0 * sigma, n)
        logd = -0.5 * ((x - 1.0) / sigma) ** 2
    else:
        t = 1.0 / sigma ** 2 - 1.0
        if t <= 0:
            raise ValueError("Schulz-Verteilung: σ < 1 erforderlich")
        # Schulz mit Modus 1: x^t e^(−t x); Mittelwert (t+1)/t, rel. Std 1/√(t+1)
        mean, sd = (t + 1.0) / t, np.sqrt(t + 1.0) / t
        x = np.linspace(max(mean - 5.0 * sd, 1e-3), mean + 7.0 * sd, n)
        logd = t * np.log(x) - t * x
    w = np.exp(logd - logd.max())
    w[0] *= 0.5
    w[-1] *= 0.5
    return x, w / w.sum()


def poly_forms(basis: ProfileBasis, r, geometry, sigma, distribution=DIST_SCHULZ):
    """V^P(r) = Σ_j w_j x_j^(2dim−1) V(r/x_j) in der Profilbasis (len(r), n, n)."""
    dim = DIM[geometry]
    xs, ws = size_nodes(sigma, distribution)
    r = np.asarray(r, dtype=float)
    nf = len(basis.edges) - 1
    Vf = np.zeros((len(r), nf, nf))
    for x, w in zip(xs, ws):                     # Mittelung in der feinen Stufenbasis
        Vf += (w * x ** (2 * dim - 1)) * step_forms(basis.edges, r / x, geometry)
    out = np.einsum('ai,kab,bj->kij', basis.S, Vf, basis.S, optimize=True)
    return 0.5 * (out + np.swapaxes(out, 1, 2))


def poly_intensity(basis: ProfileBasis, q, geometry, c, sigma, distribution=DIST_SCHULZ):
    """I(q) = pref(q) · Σ_j w_j x_j^(2dim) A²(q x_j) [MG98 Gl. 7]."""
    dim = DIM[geometry]
    xs, ws = size_nodes(sigma, distribution)
    q = np.asarray(q, dtype=float)
    I = np.zeros(len(q))
    for x, w in zip(xs, ws):
        A = step_amplitudes(basis.edges, q * x, geometry) @ (basis.S @ c)
        I += w * x ** (2 * dim) * A * A
    return q_prefactor(q, geometry) * I


# ---------------------------------------------------------------------------
# Anpassung
# ---------------------------------------------------------------------------

def _pr(M, c):
    return np.einsum('i,kij,j->k', c, M, c)


def _solve(M, p, s, D, lam, c0):
    sq = np.sqrt(lam)

    def res(c):
        return np.concatenate([(_pr(M, c) - p) / s, sq * (D @ c)])

    def jac(c):
        return np.vstack([2.0 * np.einsum('kij,j->ki', M, c) / s[:, None], sq * D])

    return least_squares(res, c0, jac=jac, method='lm', xtol=1e-12, ftol=1e-12,
                         max_nfev=3000).x


def _scaled(M, r, p, c):
    """Skaliert c so, dass ∫p̃ dr = ∫p dr [G81 Gl. 5]."""
    k = np.sqrt(max(np.trapezoid(p, r), 1e-300) / max(abs(np.trapezoid(_pr(M, c), r)), 1e-300))
    return c * k


def _starts(basis, M, r, p, n_random, seed):
    """Konstantes Startprofil [G81] und (Erweiterung) weitere Startprofile."""
    xs = 0.5 * (basis.edges[:-1] + basis.edges[1:])

    def fit(y):
        return np.linalg.lstsq(basis.S, y, rcond=None)[0]

    out = [('constant', _scaled(M, r, p, fit(np.ones_like(xs))))]
    if n_random <= 0:
        return out
    extra = [('core_neg_shell_pos', fit(np.where(xs < 0.6 * basis.R, -0.5, 1.0))),
             ('core_pos_shell_neg', fit(np.where(xs < 0.6 * basis.R, 1.0, -0.5))),
             ('decreasing', fit(1.0 - 0.8 * xs / basis.R))]
    rng = np.random.default_rng(seed)
    extra += [(f'random_{i}', rng.standard_normal(basis.n)) for i in range(n_random)]
    return out + [(n_, _scaled(M, r, p, c)) for n_, c in extra]


def _select_lambda_decon(lam_rel, chi2, nc, md_tolerance, plateau_slope):
    """Wendepunkt-Methode für DECON [G81 §III.2]: größtes λ auf einem inneren Plateau von
    log N_c (lokales Minimum von |d log N_c / d log λ| < plateau_slope), dessen χ² höchstens
    max(1, (1 + tol)·χ²_min) beträgt — also vor dem steilen Anstieg der Abweichung.

    Anders als in der IFT zählt der linke Scanrand nicht: Dort ist N_c flach, weil die
    Lösung praktisch ungeglättet ist. Ohne inneres Plateau (fein aufgelöste Basis) wird das
    größte λ gewählt, das p(r) noch innerhalb dieser Grenze beschreibt (found = False)."""
    x = np.log10(lam_rel)
    y = np.log10(np.maximum(nc, np.finfo(float).tiny))
    slope = np.abs(np.gradient(y, x))
    limit = max(1.0, (1.0 + md_tolerance) * float(np.min(chi2)))
    ok = chi2 <= limit
    inner = np.arange(1, len(x) - 1)
    is_min = (slope[inner] <= slope[inner - 1]) & (slope[inner] <= slope[inner + 1])
    cand = inner[is_min & ok[inner] & (slope[inner] < plateau_slope)]
    if len(cand):
        return int(cand.max()), True
    return int(np.nonzero(ok)[0].max()), False


def _chi2(M, c, p, s):
    return float(np.sum(((_pr(M, c) - p) / s) ** 2)) / len(p)


def _fit(M, p, s, D, lam_scale, settings, starts):
    """λ (Wendepunkt [G81 §III.2] oder fest) und Lösungen aller Startprofile."""
    lam_scan = None
    found = True
    if settings.lam == 'auto':
        lo, hi, num = settings.lam_grid
        grid = np.geomspace(hi, lo, int(num))                   # warm start von groß nach klein
        c = starts[0][1]
        chi, nc, cs = [], [], []
        for lr in grid:
            c = _solve(M, p, s, D, lr * lam_scale, c)
            chi.append(_chi2(M, c, p, s))
            nc.append(float(np.sum((D @ c) ** 2) / max(float(np.sum(c * c)), 1e-300)))
            cs.append(c)
        g = grid[::-1]
        chi = np.array(chi[::-1])
        nc = np.array(nc[::-1])
        cs = cs[::-1]
        idx, found = _select_lambda_decon(g, chi, nc, settings.md_tolerance,
                                          settings.plateau_slope)
        lam_rel = float(g[idx])
        lam_scan = {'lam_rel': g, 'chi2_red': chi, 'nc': nc, 'index': int(idx),
                    'inflexion_found': bool(found)}
        starts = [('constant', cs[idx])] + list(starts[1:])
    else:
        lam_rel = float(settings.lam)
    sols = []
    for name, c0 in starts:
        c = _solve(M, p, s, D, lam_rel * lam_scale, c0)
        sols.append((name, c, _chi2(M, c, p, s)))
    return lam_rel, bool(found), lam_scan, sols


def _target(solution, r):
    from .transform import make_basis
    kind = settings_kind(solution.settings)
    n = solution.settings.n_splines
    Phi = make_basis(solution.settings.dmax, n, kind).evaluate(r)
    cov = solution.covariance[:n, :n]
    p = Phi @ solution.coefficients
    sp = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', Phi, cov, Phi), 0.0))
    return p, sp


def default_intervals(solution):
    """Stufenbreite = Knotenabstand der IFT [G81 §III.1]: R/(Dmax/(N−1)) Intervalle."""
    return int(np.clip(round(0.5 * (solution.settings.n_splines - 1)), 3, 60))


def _prepare(solution, settings, R, sigma):
    """Anpassungsgitter, Zielwerte und σ; bei Polydispersität reicht p̃ bis 2R·x_max,
    jenseits von Dmax ist p = 0."""
    dmax = float(solution.settings.dmax)
    xs, _w = size_nodes(sigma, settings.distribution)
    r_hi = max(dmax, 2.0 * R * float(xs.max()))
    r = np.linspace(0.0, r_hi, int(round(settings.n_r * r_hi / dmax)))
    p, sp = _target(solution, np.minimum(r, dmax))
    p = np.where(r <= dmax, p, 0.0)
    s = np.maximum(sp, settings.sigma_floor * float(np.max(sp)) + 1e-300)
    return r, p, s


def _evaluate(solution, basis, geometry, c, sigma, distribution):
    """I(q) des Profils (mit S(q) und Untergrund der Lösung) gegen die entschmierte
    IFT-Kurve [MG98] und gegen die Messdaten."""
    q = solution.q
    S = solution.extras.get('structure_factor')
    I = poly_intensity(basis, q, geometry, c, sigma, distribution)
    if S is not None:
        I = I * S
    if solution.background is not None:
        I = I + solution.background
    ref = solution.i_fit
    md_q = float(np.sqrt(np.mean(((I - ref) / solution.sigma) ** 2)))
    md_data = float(np.mean(((solution.intensity - I) / solution.sigma) ** 2))
    return I, ref, md_q, md_data


def _run_single(solution, settings, geometry, R, n_int, sigma, full=True):
    if not full:
        lo, hi, _num = settings.lam_grid
        settings = DeconSettings(**{**asdict(settings),
                                    'lam_grid': (lo, hi, settings.scan_lam_points)})
    basis = ProfileBasis(R, n_int, settings.basis)
    r, p, s = _prepare(solution, settings, R, sigma)
    M = poly_forms(basis, r, geometry, sigma, settings.distribution)
    D = np.diff(np.eye(basis.n), axis=0)
    starts = _starts(basis, M, r, p, settings.n_random if full else 0, settings.seed)
    J = 2.0 * np.einsum('kij,j->ki', M, starts[0][1]) / s[:, None]
    lam_scale = float(np.sum(J * J)) / float(np.trace(D.T @ D))
    lam_rel, found, lam_scan, sols = _fit(M, p, s, D, lam_scale, settings, starts)
    return dict(basis=basis, r=r, p=p, s=s, M=M, D=D, lam_scale=lam_scale, lam_rel=lam_rel,
                found=found, lam_scan=lam_scan, sols=sols)


def run_decon(solution, settings: Optional[DeconSettings] = None, progress=None) -> DeconResult:
    """Radiales Kontrastprofil aus einer IFT/GIFT-Lösung (p(r), p_c(r) oder p_t(r))."""
    settings = settings or DeconSettings()
    kind = settings_kind(solution.settings)
    if kind not in GEOMETRIES:
        raise ValueError("DECON ist nur für p(r), p_c(r) und p_t(r) definiert")
    geometry = GEOMETRIES[kind]
    R = 0.5 * float(solution.settings.dmax)
    n_int = settings.n_intervals or default_intervals(solution)

    poly_scan = None
    if settings.polydispersity == POLY_SCAN:
        lo, hi, num = settings.p_scan
        P = np.linspace(lo, hi, int(num))
        sig = P / HWHM
        md_pr, md_q = [], []
        for j, sg in enumerate(sig):
            if progress is not None and progress(j, len(sig)) is False:
                raise DeconCancelled()
            one = _run_single(solution, settings, geometry, R, n_int, sg, full=False)
            _n, c, x2 = min(one['sols'], key=lambda t: t[2])
            md_pr.append(float(np.sqrt(x2)))
            md_q.append(_evaluate(solution, one['basis'], geometry, c, sg,
                                  settings.distribution)[2])
        idx = int(np.argmin(md_pr))
        sigma = float(sig[idx])
        poly_scan = {'P': P, 'sigma': sig, 'md_pr': np.array(md_pr), 'md_q': np.array(md_q),
                     'index': idx}
    elif settings.polydispersity == POLY_FIXED:
        sigma = float(settings.sigma)
    else:
        sigma = 0.0

    run = _run_single(solution, settings, geometry, R, n_int, sigma, full=True)
    basis, M, D = run['basis'], run['M'], run['D']
    vw = basis.volume_vector(geometry)
    sols = [(n_, -c_ if vw @ c_ < 0 else c_, x2_) for n_, c_, x2_ in run['sols']]
    sols.sort(key=lambda t: t[2])
    _name, c, x2 = sols[0]

    # Fehler: linearisiert, Cov = H⁻¹ JᵀJ H⁻¹ mit H = JᵀJ + λK [G81 Gl. 17, stabilisiert]
    s = run['s']
    J = 2.0 * np.einsum('kij,j->ki', M, c) / s[:, None]
    H = J.T @ J + run['lam_rel'] * run['lam_scale'] * D.T @ D
    try:
        Hi = np.linalg.inv(H)
        cov_c = Hi @ (J.T @ J) @ Hi
    except np.linalg.LinAlgError:
        cov_c = np.full((basis.n, basis.n), np.nan)
    xg = np.linspace(0.0, R, 401)
    Px = basis.evaluate(xg)
    rho = Px @ c
    rho_err = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', Px, cov_c, Px), 0.0))

    alternatives = []
    norm = float(np.max(np.abs(rho))) or 1.0
    for n_, c_, x2_ in sols[1:]:
        if x2_ > ALT_CHI2_FACTOR * x2 + ALT_CHI2_ABS:
            continue
        rho_ = Px @ c_
        if np.max(np.abs(rho_ - rho)) < ALT_DIFF * norm:
            continue
        if any(np.max(np.abs(rho_ - a['rho'])) < ALT_DIFF * norm for a in alternatives):
            continue
        alternatives.append({'start': n_, 'chi2_red': x2_, 'rho': rho_, 'coefficients': c_})

    I, ref, md_q, md_data = _evaluate(solution, basis, geometry, c, sigma,
                                      settings.distribution)
    res = DeconResult(
        kind=kind, geometry=geometry, radius=R, settings=settings, x=xg, rho=rho,
        rho_err=rho_err, coefficients=c,
        edges=basis.edges if settings.basis == BASIS_STEPS else None,
        r=run['r'], p_target=run['p'], p_sigma=s, p_fit=_pr(M, c), chi2_red=x2,
        md_pr=float(np.sqrt(x2)), lam_rel=run['lam_rel'], inflexion_found=run['found'],
        sigma_poly=sigma, q=solution.q, i_model=I, i_reference=ref, md_q=md_q,
        md_data=md_data, md_ift=float(solution.md), alternatives=alternatives,
        starts=[{'start': n_, 'chi2_red': x2_} for n_, _c, x2_ in sols],
        lam_scan=run['lam_scan'], poly_scan=poly_scan)
    from .diagnostics import diagnose_decon
    res.flags = diagnose_decon(res)
    return res


# ---------------------------------------------------------------------------
# Stufenmodell mit variablen Breiten [GH84]
# ---------------------------------------------------------------------------

def optimize_step_model(solution, n_steps=2, sigma=0.0, distribution=DIST_SCHULZ,
                        settings: Optional[DeconSettings] = None, n_grid=12):
    """Optimale Stufengrenzen e₁ < … < e_n und Höhen ohne Glättung [GH84 §II–III].

    n = 2: Gitter über (e₁, e₂) wie [GH84 Fig. 5], die drei besten Punkte als Start des
    Simplex; n > 2: gleichmäßige Startteilungen. Returns dict(edges, heights, chi2_red,
    md_pr, md_q, md_data, x, rho, i_model, sigma_poly)."""
    settings = settings or DeconSettings()
    kind = settings_kind(solution.settings)
    if kind not in GEOMETRIES:
        raise ValueError("Stufenmodell nur für p(r), p_c(r) und p_t(r)")
    geometry = GEOMETRIES[kind]
    R0 = 0.5 * float(solution.settings.dmax)
    r, p, s = _prepare(solution, settings, R0 * 1.05, sigma)
    D0 = np.zeros((0, n_steps))

    def heights(edges):
        b = ProfileBasis(edges=np.concatenate([[0.0], edges]))
        M = poly_forms(b, r, geometry, sigma, distribution)
        best = None
        for _n, c0 in _starts(b, M, r, p, 2, settings.seed):
            c = _solve(M, p, s, D0, 0.0, c0)
            x2 = _chi2(M, c, p, s)
            if best is None or x2 < best[1]:
                best = (c, x2)
        return best

    def objective(z):
        e = np.cumsum(np.exp(z))
        if e[-1] > 1.05 * R0 or e[0] < 0.01 * R0:
            return 1e30
        return heights(e)[1]

    def z_of(e):
        return np.log(np.diff(np.concatenate([[0.0], e])))

    if n_steps == 2:
        g = np.linspace(0.1, 1.0, n_grid) * R0
        cand = [np.array([a, b]) for a in g for b in g if b > a + 0.02 * R0]
        vals = [objective(z_of(e)) for e in cand]
        seeds = [cand[i] for i in np.argsort(vals)[:3]]
    else:
        seeds = [np.linspace(0, top * R0, n_steps + 1)[1:] for top in (0.8, 0.9, 1.0)]
    best = None
    for e0 in seeds:
        out = minimize(objective, z_of(e0), method='Nelder-Mead',
                       options={'xatol': 1e-5, 'fatol': 1e-7, 'maxiter': 400 * n_steps})
        if best is None or out.fun < best.fun:
            best = out
    e = np.cumsum(np.exp(best.x))
    c, x2 = heights(e)
    b = ProfileBasis(edges=np.concatenate([[0.0], e]))
    if b.volume_vector(geometry) @ c < 0:
        c = -c
    I, _ref, md_q, md_data = _evaluate(solution, b, geometry, c, sigma, distribution)
    xg = np.linspace(0.0, float(e[-1]) * 1.02, 401)
    return {'edges': e, 'heights': c, 'chi2_red': x2, 'md_pr': float(np.sqrt(x2)),
            'md_q': md_q, 'md_data': md_data, 'x': xg, 'rho': b.evaluate(xg) @ c,
            'i_model': I, 'sigma_poly': sigma}
