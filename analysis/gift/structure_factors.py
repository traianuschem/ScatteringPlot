"""
Strukturfaktor-Modelle für GIFT (Registry).

Phase 3a:
- 'none'       S(q) = 1 (reine IFT)
- 'hs_py'      Harte Kugeln, Percus-Yevick, monodispers        [BP97 §2.4]
- 'hs_py_avg'  gemittelter HS-PY-Strukturfaktor S_ave(q) mit Gaußverteilung der
               Radien, μ = σ_R/R_HS, bei festem Gesamt-φ          [BP97 Gl. 34, W99 Gl. 8]

Alle Modelle sind vektorisiert: Parameter dürfen Arrays der Form (K,) sein, das
Ergebnis hat dann die Form (K, M) — Grundlage für die spätere Batch-Auswertung
(DREAM, Screening). Skalare Parameter liefern (M,).

PY-Lösung: S = 1 / (1 − n·ĉ(q)) mit der direkten Korrelationsfunktion
    c(r) = −(α + β·u + γ·u³),  u = r/σ_HS ≤ 1,
    α = (1+2φ)²/(1−φ)⁴,  β = −6φ(1+φ/2)²/(1−φ)⁴,  γ = φα/2.
Mit x = q·σ_HS = 2qR_HS gilt −n·ĉ = 24φ·J(x), J(x) = ∫₀¹ (α+βu+γu³) u² j₀(xu) du.
Für x > 1 wird die geschlossene Form (Kinning & Thomas 1984) verwendet, für x ≤ 1
Gauss-Legendre-Quadratur (numerisch stabil, die geschlossene Form löscht dort aus).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

_X_SWITCH = 1.0
_GL_X, _GL_W = np.polynomial.legendre.leggauss(24)
_GL_U = 0.5 * (_GL_X + 1.0)
_GL_WU = 0.5 * _GL_W
_GH_T, _GH_W = np.polynomial.hermite.hermgauss(21)


def _py_coefficients(phi):
    phi = np.asarray(phi, dtype=float)
    d4 = (1.0 - phi) ** 4
    alpha = (1.0 + 2.0 * phi) ** 2 / d4
    beta = -6.0 * phi * (1.0 + 0.5 * phi) ** 2 / d4
    gamma = 0.5 * phi * alpha
    return alpha, beta, gamma


def _j_closed(x, alpha, beta, gamma):
    """J(x) = G(x)/x in geschlossener Form (nur für x ≳ 1 numerisch stabil)."""
    s, c = np.sin(x), np.cos(x)
    x2 = x * x
    g = (alpha * (s - x * c) / x2
         + beta * (2.0 * x * s + (2.0 - x2) * c - 2.0) / (x2 * x)
         + gamma * (-x2 * x2 * c + 4.0 * ((3.0 * x2 - 6.0) * c + (x2 * x - 6.0 * x) * s + 6.0))
         / (x2 * x2 * x))
    return g / x


def _j_quadrature(x, alpha, beta, gamma):
    """J(x) per Gauss-Legendre (glatt für x ≤ 1)."""
    u = _GL_U
    poly = alpha[..., None] + beta[..., None] * u + gamma[..., None] * u ** 3   # (..., P)
    kern = np.sinc(x[..., None] * u / np.pi)                                     # (..., P)
    return np.sum(poly * u ** 2 * kern * _GL_WU, axis=-1)


def s_percus_yevick(q, r_hs, phi):
    """Monodisperser HS-PY-Strukturfaktor. Broadcasting über r_hs/phi (→ (K, M))."""
    q = np.asarray(q, dtype=float)
    r_hs = np.asarray(r_hs, dtype=float)
    phi = np.asarray(phi, dtype=float)
    batched = r_hs.ndim > 0 or phi.ndim > 0
    r_b = np.atleast_1d(r_hs)[:, None] if batched else r_hs
    phi_b = np.atleast_1d(phi)[:, None] if batched else phi
    x = 2.0 * q * r_b
    alpha, beta, gamma = _py_coefficients(phi_b)
    x, alpha, beta, gamma, phi_b = np.broadcast_arrays(x, alpha, beta, gamma, phi_b)
    J = np.empty_like(x)
    small = x <= _X_SWITCH
    if small.any():
        J[small] = _j_quadrature(x[small], alpha[small], beta[small], gamma[small])
    if (~small).any():
        J[~small] = _j_closed(x[~small], alpha[~small], beta[~small], gamma[~small])
    return 1.0 / (1.0 + 24.0 * phi_b * J)


def s_percus_yevick_avg(q, r_hs, phi, mu):
    """Gemittelter HS-PY-Strukturfaktor S_ave = Σ x_α S_PY(q; R_α, φ) [BP97 Gl. 34].

    Die Radien sind gaußverteilt mit Mittelwert R_HS und Breite μ·R_HS (μ = σ/R_HS);
    diskretisiert mit 21 Gauss-Hermite-Knoten. Knoten mit R ≤ 0 werden verworfen und
    die Gewichte neu normiert. Das Volumenbruch-φ ist für alle Spezies gleich.
    """
    q = np.asarray(q, dtype=float)
    r_hs = np.atleast_1d(np.asarray(r_hs, dtype=float))
    phi = np.atleast_1d(np.asarray(phi, dtype=float))
    mu = np.atleast_1d(np.asarray(mu, dtype=float))
    scalar = all(np.ndim(v) == 0 for v in (r_hs, phi, mu)) or \
        (r_hs.size == phi.size == mu.size == 1)
    r_hs, phi, mu = np.broadcast_arrays(r_hs, phi, mu)
    radii = r_hs[:, None] * (1.0 + np.sqrt(2.0) * mu[:, None] * _GH_T[None, :])   # (K, H)
    w = np.where(radii > 0, _GH_W[None, :], 0.0)
    w = w / np.sum(w, axis=1, keepdims=True)
    K, H = radii.shape
    s = s_percus_yevick(q, np.where(radii > 0, radii, 1.0).ravel(),
                        np.repeat(phi, H)).reshape(K, H, len(q))
    out = np.einsum('kh,khm->km', w, s)
    return out[0] if scalar else out


def s_none(q):
    return np.ones_like(np.asarray(q, dtype=float))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class ParamSpec:
    name: str            # interner Name (Funktionsargument)
    label: str           # Anzeigename
    unit: str
    default: float
    lower: float         # physikalische Grenzen (MD = ∞ außerhalb) [B00]
    upper: float
    decimals: int = 3
    # Größenparameter: Standard-Suchbereich [Start/f, Start·f] statt der (sehr weiten)
    # physikalischen Grenzen, sofern keine eigenen Grenzen vorgegeben sind
    relative_search: float = 0.0


@dataclass
class StructureFactorModel:
    key: str
    label_key: str                         # i18n-Schlüssel
    func: Callable
    params: List[ParamSpec] = field(default_factory=list)
    reference: str = ''
    apparent_parameters: bool = False      # [W99]: Parameter nur „scheinbar“

    def evaluate(self, q, values: Dict[str, float]):
        return self.func(q, **{p.name: values[p.name] for p in self.params})

    def defaults(self):
        return {p.name: p.default for p in self.params}

    def in_bounds(self, values: Dict[str, float]):
        return all(p.lower <= values[p.name] <= p.upper for p in self.params)

    def to_dict(self):
        return {'key': self.key, 'reference': self.reference,
                'params': [p.__dict__ for p in self.params]}


MODELS: Dict[str, StructureFactorModel] = {
    'none': StructureFactorModel(
        'none', 'gift.model_none', lambda q: s_none(q), [], 'S(q) = 1 (IFT)'),
    'hs_py': StructureFactorModel(
        'hs_py', 'gift.model_hs_py',
        lambda q, phi, r_hs: s_percus_yevick(q, r_hs, phi),
        [ParamSpec('phi', 'φ', '', 0.10, 1e-4, 0.55, 4),
         ParamSpec('r_hs', 'R_HS', 'nm', 10.0, 0.1, 1e4, 3, relative_search=4.0)],
        'Percus-Yevick hard spheres (Brunner-Popela & Glatter 1997, §2.4)'),
    'hs_py_avg': StructureFactorModel(
        'hs_py_avg', 'gift.model_hs_py_avg',
        lambda q, phi, r_hs, mu: s_percus_yevick_avg(q, r_hs, phi, mu),
        [ParamSpec('phi', 'φ', '', 0.10, 1e-4, 0.55, 4),
         ParamSpec('r_hs', 'R_HS', 'nm', 10.0, 0.1, 1e4, 3, relative_search=4.0),
         ParamSpec('mu', 'μ', '', 0.20, 0.0, 0.9, 3)],
        'averaged PY structure factor S_ave (Brunner-Popela & Glatter 1997, Eq. 34; '
        'Weyerich et al. 1999, Eq. 8)', apparent_parameters=True),
}
DEFAULT_GIFT_MODEL = 'hs_py_avg'


def get_model(key: str) -> StructureFactorModel:
    if key not in MODELS:
        raise ValueError(f"Unbekanntes Strukturfaktor-Modell: {key}")
    return MODELS[key]
