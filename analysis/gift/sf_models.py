"""
Weitere Strukturfaktoren für GIFT (Phase 5).

- **S_eff nach Vrij** (polydisperse harte Kugeln, Percus-Yevick für Mischungen, Schulz-
  Verteilung der Radien) [V79, W99 §2.2.1]:
      I(q) = Σ_ij √(ρ_iρ_j) F_i F_j S_ij(q),   S_eff = I / Σ_i ρ_i F_i²      [W99 Gl. 4–7]
  mit Amplituden homogener Kugeln F_i = V_i·3j₁(qR_i)/(qR_i). Die partiellen Struktur-
  faktoren folgen aus Baxters Faktorisierung der PY-Gleichung für Mischungen (Baxter 1970;
  Vrijs Lösung ist dieselbe für Streuamplituden):
      1 − ρ̂Ĉ(q) = Q̂ᴴ(q) Q̂(q),
      Q̂_ij(q) = δ_ij − 2π√(ρ_iρ_j) ∫_{λ_ji}^{R_ij} Q_ij(r) e^{iqr} dr,
      Q_ij(r) = ½a_i(r² − R_ij²) + b_i(r − R_ij),
      a_i = (1 − ξ₃ + 3σ_iξ₂)/(1 − ξ₃)²,  b_i = −(3/2)σ_i²ξ₂/(1 − ξ₃)²,
      ξ_n = (π/6)Σ_k ρ_kσ_k^n,  R_ij = (σ_i + σ_j)/2,  λ_ji = (σ_i − σ_j)/2.
  Damit ist I(q) = ‖Q̂^{-H} u‖² mit u_i = √ρ_i F_i. Die Schulz-Verteilung (Anzahl) wird mit
  Gauß-Legendre-Knoten über ihren Träger diskretisiert (Dichte logarithmisch berechnet,
  stabil auch für schmale Verteilungen).
- **S_rod** für dünne, polydisperse Stäbchen (Mean-Field nach van der Schoot) [W99 Gl. 16–17]:
      S_rod = F / (F + 2cF² − (5/4)cG²),
      F(q) = ⟨L²⟩⁻¹ Σ x_i L_i² F̃(qL_i/2),  F̃(x) = Si(2x)/x − (sin x/x)²,
      G̃(x) = (3/4)x⁻²(1 − sin 2x/(2x)) − F̃(x)/2  (G analog gemittelt).
  Nur für dünne Stäbchen (qR < 1) mit großem Achsenverhältnis gültig.
- **Klebrige harte Kugeln** (Baxter, Störungslösung der PY-Gleichung nach Menon et al.
  1991) — Portierung von sasmodels `stickyhardsphere` (BSD-3, siehe
  THIRD_PARTY_NOTICES.md); Parameter wie in SasView: δ = `perturb` (Topfbreite
  Δ/(σ+Δ)), τ = `stickiness` (kleiner = stärkere Anziehung).
- **Fraktales Aggregat** (Teixeira 1988, Gl. 15) wie sasmodels `fractal_sq`:
      S(q) = 1 + Γ(D+1)/(D−1)·sin((D−1)·atan(qξ))·(q r₀)^{−D}·(1 + (qξ)^{−2})^{−(D−1)/2}.

Alle Funktionen: q in nm⁻¹, Längen in nm; Parameter dürfen Arrays der Länge K sein
(Ergebnis (K, M)), ungültige Parametersätze ergeben NaN (→ MD = ∞ in GIFT).
"""

import numpy as np
from scipy.special import sici, gamma

from .structure_factors import s_percus_yevick

N_SCHULZ = 24          # Knoten der Schulz-Verteilung
_GL_X, _GL_W = np.polynomial.legendre.leggauss(N_SCHULZ)


def _batched(*args):
    arrs = [np.atleast_1d(np.asarray(a, dtype=float)) for a in args]
    scalar = all(np.ndim(a) == 0 for a in args)
    return np.broadcast_arrays(*arrs), scalar


# ---------------------------------------------------------------------------
# Schulz-Verteilung
# ---------------------------------------------------------------------------

def schulz_nodes(r_mean, rel_sd, n=N_SCHULZ):
    """Knoten R_k und Anzahlanteile x_k einer Schulz-Verteilung (Mittel r_mean, relative
    Standardabweichung rel_sd = 1/√(z+1))."""
    z = 1.0 / rel_sd ** 2 - 1.0
    lo = max(1e-3 * r_mean, r_mean * (1.0 - 6.0 * rel_sd))
    hi = r_mean * (1.0 + 9.0 * rel_sd)
    R = 0.5 * (hi + lo) + 0.5 * (hi - lo) * _GL_X
    t = R / r_mean
    log_pdf = z * np.log(t) - (z + 1.0) * t
    w = _GL_W * np.exp(log_pdf - np.max(log_pdf))
    return R, w / np.sum(w)


# ---------------------------------------------------------------------------
# Percus-Yevick für Mischungen harter Kugeln (Baxter-Faktorisierung)
# ---------------------------------------------------------------------------

def _baxter_q(q, radii, rho):
    """Q̂(q) (M, m, m) der PY-Mischung harter Kugeln; None bei ξ₃ ≥ 1."""
    q = np.asarray(q, dtype=float)
    h = np.asarray(radii, dtype=float)                           # h_i = σ_i/2
    rho = np.asarray(rho, dtype=float)
    sig = 2.0 * h
    xi = [np.pi / 6.0 * np.sum(rho * sig ** n) for n in range(4)]
    delta = 1.0 - xi[3]
    if not delta > 0:
        return None
    a = (1.0 - xi[3] + 3.0 * sig * xi[2]) / delta ** 2           # (m,)
    b = -1.5 * sig ** 2 * xi[2] / delta ** 2
    R = h[:, None] + h[None, :]                                   # R_ij
    lam = h[:, None] - h[None, :]                                 # λ_ji
    # Q_ij(r) = c2 r² + c1 r + c0 mit c2 = a_i/2, c1 = b_i, c0 = −(a_i R²/2 + b_i R)
    c2 = 0.5 * a[:, None] + 0.0 * R
    c1 = b[:, None] + 0.0 * R
    c0 = -(0.5 * a[:, None] * R ** 2 + b[:, None] * R)
    m = len(h)
    integ = np.empty((len(q), m, m), dtype=complex)
    small = q * np.max(sig) < 0.5
    big = ~small
    if big.any():
        # Stammfunktion e^{ikr}[Q(r)/(ik) + Q'(r)/k² + 2i·c2/k³]; am oberen Rand ist
        # Q_ij(R_ij) = 0. e^{ikR_ij} = e^{ikh_i}e^{ikh_j}, e^{ikλ_ji} = e^{ikh_i}e^{−ikh_j}.
        k = q[big][:, None, None]
        E = np.exp(1j * q[big][:, None] * h[None, :])             # e^{ik h_i}
        eR = E[:, :, None] * E[:, None, :]
        eL = E[:, :, None] * np.conj(E[:, None, :])
        inv_k2 = 1.0 / k ** 2
        third = 2j * c2[None] / k ** 3
        dQ_R = (2.0 * c2 * R + c1)[None]
        dQ_L = (2.0 * c2 * lam + c1)[None]
        Q_L = (c2 * lam ** 2 + c1 * lam + c0)[None]
        integ[big] = (eR * (dQ_R * inv_k2 + third)
                      - eL * (Q_L / (1j * k) + dQ_L * inv_k2 + third))
    if small.any():
        # Taylor-Reihe von e^{ikr} (Auslöschung der geschlossenen Form bei kleinem k)
        k = q[small][:, None, None]
        acc = np.zeros((int(small.sum()), m, m), dtype=complex)
        term = np.ones_like(acc)
        for n in range(18):
            mom = (c0 * (R ** (n + 1) - lam ** (n + 1)) / (n + 1)
                   + c1 * (R ** (n + 2) - lam ** (n + 2)) / (n + 2)
                   + c2 * (R ** (n + 3) - lam ** (n + 3)) / (n + 3))
            acc += term * mom
            term = term * (1j * k) / (n + 1)
        integ[small] = acc
    return np.eye(m)[None] - 2.0 * np.pi * np.sqrt(np.outer(rho, rho))[None] * integ


def py_mixture_intensity(q, radii, rho, amplitudes):
    """I(q) = Σ_ij √(ρ_iρ_j) F_i F_j S_ij(q) einer PY-Mischung harter Kugeln.

    Args:
        q: (M,) nm⁻¹; radii, rho: (m,) Radien (nm) und Anzahldichten (nm⁻³);
        amplitudes: (M, m) Streuamplituden F_i(q)
    Returns:
        (M,) oder NaN bei unphysikalischen Parametern (ξ₃ ≥ 1)
    """
    Q = _baxter_q(q, radii, rho)
    if Q is None:
        return np.full(len(np.atleast_1d(q)), np.nan)
    u = np.sqrt(np.asarray(rho, float))[None, :] * np.asarray(amplitudes, dtype=float)
    try:
        w = np.linalg.solve(np.conj(np.swapaxes(Q, 1, 2)), u[..., None].astype(complex))
    except np.linalg.LinAlgError:
        return np.full(len(u), np.nan)
    return np.sum(np.abs(w[..., 0]) ** 2, axis=1)


def _sphere_amplitude(q, R):
    x = np.outer(q, R)
    with np.errstate(invalid='ignore', divide='ignore'):
        f = np.where(x > 1e-4, 3.0 * (np.sin(x) - x * np.cos(x)) / x ** 3, 1.0 - x ** 2 / 10.0)
    return (4.0 * np.pi / 3.0) * R[None, :] ** 3 * f


def s_eff_vrij_single(q, r_hs, phi, mu):
    """S_eff(q) polydisperser harter Kugeln (Schulz, relative Breite mu) bei Volumenbruch phi."""
    q = np.asarray(q, dtype=float)
    if not (r_hs > 0 and 0 < phi < 0.74 and mu >= 0):
        return np.full(len(q), np.nan)
    if mu < 1e-3:
        return s_percus_yevick(q, r_hs, phi)
    R, x = schulz_nodes(r_hs, mu)
    vol = 4.0 * np.pi / 3.0 * R ** 3
    rho = x * phi / np.sum(x * vol)
    F = _sphere_amplitude(q, R)
    I = py_mixture_intensity(q, R, rho, F)
    return I / np.sum(rho[None, :] * F ** 2, axis=1)


def s_eff_vrij(q, r_hs, phi, mu):
    """Vektorisiert über Parameter-Arrays (K,) → (K, M)."""
    (r, p, m), scalar = _batched(r_hs, phi, mu)
    out = np.stack([s_eff_vrij_single(q, r[k], p[k], m[k]) for k in range(len(r))])
    return out[0] if scalar else out


# ---------------------------------------------------------------------------
# Stäbchen (Mean-Field, van der Schoot) [W99 Gl. 16–17]
# ---------------------------------------------------------------------------

_GH_T, _GH_W = np.polynomial.hermite.hermgauss(21)


def _rod_f_g(x):
    """F̃(x), G̃(x) für x = qL/2 (Reihen für kleine x)."""
    x = np.asarray(x, dtype=float)
    small = x < 1e-2
    xs = np.where(small, 1.0, x)
    si, _ = sici(2.0 * xs)
    sinc = np.sin(xs) / xs
    F = np.where(small, 1.0 - x ** 2 / 9.0, si / xs - sinc ** 2)
    G = np.where(small, -2.0 * x ** 2 / 45.0,
                 0.75 * (1.0 - np.sin(2.0 * xs) / (2.0 * xs)) / xs ** 2 - 0.5 * F)
    return F, G


def s_rod_single(q, c, length, mu_l):
    q = np.asarray(q, dtype=float)
    if not (length > 0 and c >= 0 and mu_l >= 0):
        return np.full(len(q), np.nan)
    L = length * (1.0 + np.sqrt(2.0) * mu_l * _GH_T)
    w = np.where(L > 0, _GH_W, 0.0)
    L = np.where(L > 0, L, 1.0)
    wl = w * L ** 2
    Fi, Gi = _rod_f_g(0.5 * np.outer(q, L))
    F = Fi @ wl / np.sum(wl)
    G = Gi @ wl / np.sum(wl)
    den = F + 2.0 * c * F ** 2 - 1.25 * c * G ** 2
    with np.errstate(divide='ignore', invalid='ignore'):
        S = np.where(den > 0, F / den, np.nan)
    return S


def s_rod(q, c, length, mu_l):
    (cc, L, m), scalar = _batched(c, length, mu_l)
    out = np.stack([s_rod_single(q, cc[k], L[k], m[k]) for k in range(len(cc))])
    return out[0] if scalar else out


# ---------------------------------------------------------------------------
# Klebrige harte Kugeln — Portierung von sasmodels stickyhardsphere.c (BSD-3)
# ---------------------------------------------------------------------------

def s_sticky(q, r_hs, phi, stickiness, perturb):
    """Klebrige harte Kugeln (Menon et al. 1991), wie sasmodels `stickyhardsphere`.

    Parameter wie SasView: r_hs = radius_effective, phi = volfraction, stickiness (τ bzw.
    SasView „stickiness“), perturb (δ, Topfbreite Δ/(σ+Δ)). Unphysikalisch → NaN."""
    q = np.asarray(q, dtype=float)
    (r, ph, tau, dl), scalar = _batched(r_hs, phi, stickiness, perturb)
    r, ph, tau, dl = (v[:, None] for v in (r, ph, tau, dl))
    onemineps = 1.0 - dl
    eta = ph / onemineps ** 3
    aa = 2.0 * r / onemineps
    etam1 = 1.0 - eta
    etam1sq = etam1 * etam1
    qa = eta / 6.0
    qb = tau + eta / etam1
    qc = (1.0 + eta / 2.0) / etam1sq
    radic = qb * qb - 2.0 * qa * qc
    valid = (radic >= 0) & (eta < 1) & (r > 0) & (ph > 0)
    radic = np.sqrt(np.where(valid, radic, 0.0))
    with np.errstate(divide='ignore', invalid='ignore'):
        lam = np.minimum((qb - radic) / qa, (qb + radic) / qa)   # kleinere Wurzel
        mu = lam * eta * etam1
        valid &= mu <= 1.0 + 2.0 * eta
        alpha = (1.0 + 2.0 * eta - mu) / etam1sq
        beta = (mu - 3.0 * eta) / (2.0 * etam1sq)
        kk = q[None, :] * aa
        k2, k3 = kk * kk, kk * kk * kk
        ds, dc = np.sin(kk), np.cos(kk)
        aq = 1.0 + 12.0 * eta * ((ds - kk * dc) * alpha / k3 + beta * (1.0 - dc) / k2
                                 - lam * ds / (12.0 * kk))
        bq = 12.0 * eta * (alpha * (0.5 / kk - ds / k2 + (1.0 - dc) / k3)
                           + beta * (1.0 / kk - ds / k2) - (lam / 12.0) * ((1.0 - dc) / kk))
        S = 1.0 / (aq * aq + bq * bq)
    S = np.where(valid, S, np.nan)
    return S[0] if scalar else S


# ---------------------------------------------------------------------------
# Fraktales Aggregat (Teixeira 1988) — wie sasmodels fractal_sq
# ---------------------------------------------------------------------------

def s_fractal(q, r0, df, xi):
    """S(q) eines fraktalen Aggregats aus Bausteinen mit Radius r0 (Dimension df,
    Korrelationslänge xi). S(0) = 1 + Γ(D+1)(ξ/r₀)^D."""
    q = np.asarray(q, dtype=float)
    (r, d, x), scalar = _batched(r0, df, xi)
    r, d, x = (v[:, None] for v in (r, d, x))
    valid = (r > 0) & (x > 0) & (d > 1.0) & (d <= 3.0)
    dm1 = np.where(valid, d - 1.0, 1.0)
    qq = np.maximum(q[None, :], 1e-12)
    with np.errstate(over='ignore', invalid='ignore'):
        t1 = gamma(d + 1.0) / dm1 * np.sin(dm1 * np.arctan(qq * x))
        t2 = np.exp(-d * np.log(qq * r))
        t3 = np.exp(-0.5 * dm1 * np.log1p(1.0 / (qq * x) ** 2))
        S = 1.0 + t1 * t2 * t3
    S = np.where(valid, S, np.nan)
    return S[0] if scalar else S


def fractal_info(r0, df, xi):
    """Abgeleitete Größen: S(0) − 1 ≈ Bausteine je Aggregat, Rg des Aggregats."""
    return {'n_aggregate': float(gamma(df + 1.0) * (xi / r0) ** df),
            'rg_aggregate_nm': float(xi * np.sqrt(df * (df + 1.0) / 2.0))}
