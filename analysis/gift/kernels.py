"""
Transformationskerne der IFT (v8.0): p(r), Querschnitt, Dicke und Größenverteilungen.

Alle Kerne haben die Form

    K(q, r) = c · q⁻ᵇ · rᵃ · k(q·r),         I(q) = ∫₀^Dmax f(r) K(q, r) dr,

mit einer Spline-Darstellung von f (p(r), p_c(r), p_t(r) bzw. D_V(R)). Damit skaliert die
Transformierte eines Splines φ̃(r/D) mit Dmax wie ψ(q; D) = D^{a+1} · c · q⁻ᵇ · g(q·D),
g(x) = ∫₀¹ φ̃(u) uᵃ k(x·u) du — Grundlage der Dmax-Variation in DREAM.

| Art             | f(r)        | Kern                                   | Quelle                 |
|-----------------|-------------|----------------------------------------|------------------------|
| `pddf`          | p(r)        | 4π · sin(qr)/(qr)                      | [G77 Gl. 4]            |
| `cross_section` | p_c(r)      | (π/q) · 2π J₀(qr)          (L = 1)     | [G80b], Porod-Näherung |
| `thickness`     | p_t(r)      | (2π/q²) · 2 cos(qr)        (A = 1)     | [G80b]                 |
| `size_sphere`   | D_V(R)      | V(R) · [3(sin x − x cos x)/x³]²        | [G80a]                 |
| `size_cylinder` | D_V(R)      | (π/q) · πR² · [2J₁(x)/x]²  (lange Zyl.)| [G80a/b]               |
| `size_lamella`  | D_V(T)      | (2π/q²) · T · [sin(x/2)/(x/2)]²        | [G80a/b]               |

(x = qR bzw. qT.) Für jede Art gibt es den Vorwärtswert und den Trägheitsradius:

    F(0) = ∫ w₀(r) f(r) dr,   w₀ = c₀ rᵃ;       R_g² = g₂ · ∫ w₀ r² f dr / F(0)

- `pddf`: I(0) und R_g [G77 Gl. 19/20]
- `cross_section`: I_c(0) = 2π∫p_c und R_c (homogener Zylinder: R = √2·R_c)
- `thickness`: I_t(0) = 2∫p_t und R_t (homogene Lamelle: T = √12·R_t)
- Größenverteilungen: dieselben Größen des Ensembles (vergleichbar mit Guinier bzw. mit
  der Querschnitts-/Dicken-IFT), z. B. Kugeln: R_g² = (3/5)·∫D_V V R² / ∫D_V V.

Quellen: [G77] Glatter (1977) J. Appl. Cryst. 10, 415; [G80a] Glatter (1980) J. Appl.
Cryst. 13, 7; [G80b] Glatter (1980) J. Appl. Cryst. 13, 577.
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.special import j0, j1, jv, spherical_jn

PDDF = 'pddf'
CROSS_SECTION = 'cross_section'
THICKNESS = 'thickness'
SIZE_SPHERE = 'size_sphere'
SIZE_CYLINDER = 'size_cylinder'
SIZE_LAMELLA = 'size_lamella'
SIZE_SPHERE_N = 'size_sphere_n'
SIZE_CYLINDER_N = 'size_cylinder_n'
SIZE_LAMELLA_N = 'size_lamella_n'

_SMALL = 1e-4


def _sinc(x):
    return np.sinc(x / np.pi)


def _dsinc(x):
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(np.abs(x) > _SMALL, (x * np.cos(x) - np.sin(x)) / (x * x), -x / 3.0)


def _sphere_amp(x):
    """3 j₁(x)/x (= 1 bei x = 0)."""
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(np.abs(x) > _SMALL, 3.0 * spherical_jn(1, x) / np.where(x == 0, 1, x),
                        1.0 - x * x / 10.0)


def _dsphere_amp(x):
    """d/dx [3 j₁(x)/x] = −3 j₂(x)/x."""
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(np.abs(x) > _SMALL, -3.0 * spherical_jn(2, x) / np.where(x == 0, 1, x),
                        -x / 5.0)


def _disk_amp(x):
    """2 J₁(x)/x (= 1 bei x = 0)."""
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(np.abs(x) > _SMALL, 2.0 * j1(x) / np.where(x == 0, 1, x),
                        1.0 - x * x / 8.0)


def _ddisk_amp(x):
    """d/dx [2 J₁(x)/x] = −2 J₂(x)/x."""
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(np.abs(x) > _SMALL, -2.0 * jv(2, x) / np.where(x == 0, 1, x), -x / 4.0)


@dataclass(frozen=True)
class Kernel:
    key: str
    c: float                        # Vorfaktor
    b: int                          # Potenz q⁻ᵇ
    a: int                          # Potenz rᵃ
    k: Callable                     # Formfunktion k(x)
    dk: Callable                    # Ableitung k'(x)
    c0: float                       # Vorwärtswert: w₀(r) = c₀·rᵃ
    g2: float                       # R_g² = g₂ · ∫w₀ r² f / ∫w₀ f
    left_free: bool = False         # f(0) ≠ 0 zulässig (Dicken-Verteilung)
    size: bool = False              # Größenverteilung (r = Teilchenradius bzw. -dicke)
    span: int = 1                   # größter Abstand im Teilchen = span · Dmax (Radius → 2)
    number: bool = False            # Primärgröße Anzahlverteilung D_N [G80a Gl. 1a]

    def particle_volume(self, r):
        """Teilchenvolumen v(R) (bzw. je Länge/Fläche) der Größenverteilungs-Kerne."""
        r = np.asarray(r, dtype=float)
        if self.number:
            return np.sqrt(self.c0) * r ** (self.a // 2)
        return self.c0 * r ** self.a

    @property
    def guinier_dim(self):
        """Dimension des Guinier-Gesetzes: 3 (Kugel/p(r)), 2 (Querschnitt), 1 (Dicke)."""
        return 3 - self.b

    def matrix(self, q, r):
        """K(q, r) als Matrix (len(q) × len(r))."""
        q = np.asarray(q, dtype=float)
        r = np.asarray(r, dtype=float)
        x = np.outer(q, r)
        out = self.c * self.k(x)
        if self.a:
            out = out * r[None, :] ** self.a
        if self.b:
            out = out / q[:, None] ** self.b
        return out

    def q_factor(self, q):
        q = np.asarray(q, dtype=float)
        return self.c / q ** self.b if self.b else np.full(q.shape, self.c)

    def forward_weights(self, r):
        """(w₀(r), w₂(r)) mit F(0) = ∫w₀ f und R_g² = ∫w₂ f / F(0)."""
        r = np.asarray(r, dtype=float)
        w0 = self.c0 * r ** self.a if self.a else np.full(r.shape, self.c0)
        return w0, self.g2 * w0 * r * r

    @property
    def needs_positive_q(self):
        return self.b > 0


def _sq(f):
    return lambda x: f(x) ** 2


def _dsq(f, df):
    return lambda x: 2.0 * f(x) * df(x)


KERNELS = {
    PDDF: Kernel(PDDF, 4.0 * np.pi, 0, 0, _sinc, _dsinc, 4.0 * np.pi, 0.5),
    CROSS_SECTION: Kernel(CROSS_SECTION, 2.0 * np.pi ** 2, 1, 0, j0, lambda x: -j1(x),
                          2.0 * np.pi, 0.5),
    THICKNESS: Kernel(THICKNESS, 4.0 * np.pi, 2, 0, np.cos, lambda x: -np.sin(x), 2.0, 0.5,
                      left_free=True),
    SIZE_SPHERE: Kernel(SIZE_SPHERE, 4.0 * np.pi / 3.0, 0, 3, _sq(_sphere_amp),
                        _dsq(_sphere_amp, _dsphere_amp), 4.0 * np.pi / 3.0, 0.6, size=True,
                        span=2),
    SIZE_CYLINDER: Kernel(SIZE_CYLINDER, np.pi ** 2, 1, 2, _sq(_disk_amp),
                          _dsq(_disk_amp, _ddisk_amp), np.pi, 0.5, size=True, span=2),
    SIZE_LAMELLA: Kernel(SIZE_LAMELLA, 2.0 * np.pi, 2, 1,
                         lambda x: _sinc(0.5 * x) ** 2,
                         lambda x: _sinc(0.5 * x) * _dsinc(0.5 * x),
                         1.0, 1.0 / 12.0, size=True),
    # Anzahlverteilungen D_N [G80a Gl. 1a]: Kern v(R)²·Φ(qR), Vorwärtswert ∫D_N v²
    SIZE_SPHERE_N: Kernel(SIZE_SPHERE_N, (4.0 * np.pi / 3.0) ** 2, 0, 6, _sq(_sphere_amp),
                          _dsq(_sphere_amp, _dsphere_amp), (4.0 * np.pi / 3.0) ** 2, 0.6,
                          size=True, span=2, number=True),
    SIZE_CYLINDER_N: Kernel(SIZE_CYLINDER_N, np.pi ** 3, 1, 4, _sq(_disk_amp),
                            _dsq(_disk_amp, _ddisk_amp), np.pi ** 2, 0.5, size=True, span=2,
                            number=True),
    SIZE_LAMELLA_N: Kernel(SIZE_LAMELLA_N, 2.0 * np.pi, 2, 2,
                           lambda x: _sinc(0.5 * x) ** 2,
                           lambda x: _sinc(0.5 * x) * _dsinc(0.5 * x),
                           1.0, 1.0 / 12.0, size=True, number=True),
}

KINDS = tuple(KERNELS)


def dmax_limit(q_min, kind=PDDF):
    """Größtes durch q_min abgedecktes Dmax: π/q_min (Radius-Verteilungen: π/(2 q_min))."""
    return np.pi / (get_kernel(kind).span * float(q_min))


def get_kernel(kind) -> Kernel:
    try:
        return KERNELS[kind or PDDF]
    except KeyError:
        raise ValueError(f"Unbekannte IFT-Art: {kind}") from None


# Beschriftungen für Export und Provenance (die GUI übersetzt über i18n)
LABELS = {
    PDDF: dict(f='p(r)', x='r', rg='Rg', i0='I(0)', tag='',
               title="p(r) aus IFT (Glatter 1977)",
               equiv=('R_Kugel', np.sqrt(5.0 / 3.0))),
    CROSS_SECTION: dict(f='p_c(r)', x='r', rg='Rc', i0='I_c(0)', tag='xs',
                        title="Querschnitts-Abstandsverteilung p_c(r) (Glatter 1980b)",
                        equiv=('R_Zylinder', np.sqrt(2.0))),
    THICKNESS: dict(f='p_t(r)', x='r', rg='Rt', i0='I_t(0)', tag='thk',
                    title="Dicken-Abstandsverteilung p_t(r) (Glatter 1980b)",
                    equiv=('T_Lamelle', np.sqrt(12.0))),
    SIZE_SPHERE: dict(f='D_V(R)', x='R', rg='Rg', i0='I(0)', tag='sizeS',
                      title="Volumenverteilung D_V(R), homogene Kugeln (Glatter 1980a)",
                      equiv=None),
    SIZE_CYLINDER: dict(f='D_V(R)', x='R', rg='Rc', i0='I_c(0)', tag='sizeC',
                        title="Volumenverteilung D_V(R), lange Zylinder (Glatter 1980a)",
                        equiv=None),
    SIZE_LAMELLA: dict(f='D_V(T)', x='T', rg='Rt', i0='I_t(0)', tag='sizeL',
                       title="Volumenverteilung D_V(T), Lamellen (Glatter 1980a)",
                       equiv=None),
    SIZE_SPHERE_N: dict(f='D_N(R)', x='R', rg='Rg', i0='I(0)', tag='sizeSn',
                        title="Anzahlverteilung D_N(R), homogene Kugeln (Glatter 1980a)",
                        equiv=None),
    SIZE_CYLINDER_N: dict(f='D_N(R)', x='R', rg='Rc', i0='I_c(0)', tag='sizeCn',
                          title="Anzahlverteilung D_N(R), lange Zylinder (Glatter 1980a)",
                          equiv=None),
    SIZE_LAMELLA_N: dict(f='D_N(T)', x='T', rg='Rt', i0='I_t(0)', tag='sizeLn',
                         title="Anzahlverteilung D_N(T), Lamellen (Glatter 1980a)",
                         equiv=None),
}
