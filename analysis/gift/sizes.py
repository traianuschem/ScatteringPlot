"""
Auswertung einer Größenverteilung aus der IFT [Glatter 1980a] (v8.0).

Die IFT liefert die Volumenverteilung D_V(R) (Kerne `size_*` in kernels.py). Daraus:

    D_I(R) = D_V(R) · v(R)          Intensitätsverteilung (v = Teilchenvolumen: 4π/3 R³,
                                    πR² je Länge bzw. T je Fläche)
    D_N(R) ∝ D_V(R) / v(R)          Anzahlverteilung

Die Anzahlverteilung ist bei kleinen R instabil (Division durch R³ bzw. R²): Größen unter
R_min ≈ π/q_max erzeugen im Messbereich praktisch keine q-Abhängigkeit und sind nicht
bestimmbar, und schon kleines Rauschen in D_V wird dort um v(R_max)/v(R) verstärkt. D_N und
ihre Momente werden daher nur für R ≥ R_min = π/q_max und nur dort ausgewertet, wo D_V
signifikant ist (D_V ≥ 2σ).

Momente (volumen- bzw. anzahlgewichtet) mit linearer Fehlerfortpflanzung aus der
Kovarianz der Spline-Koeffizienten.
"""

from typing import Dict

import numpy as np

from .kernels import get_kernel
from .transform import make_basis


def _ratio_stats(num_vec, den_vec, num2_vec, c, cov):
    """Mittelwert m = n₁/n₀ und Standardabweichung s = √(n₂/n₀ − m²) mit Fehlern."""
    n0, n1, n2 = den_vec @ c, num_vec @ c, num2_vec @ c
    if not (n0 > 0):
        return (np.nan,) * 4
    mean = n1 / n0
    var = n2 / n0 - mean ** 2
    g_mean = (num_vec - mean * den_vec) / n0
    mean_err = float(np.sqrt(max(g_mean @ cov @ g_mean, 0.0)))
    if var <= 0:
        return float(mean), mean_err, np.nan, np.nan
    std = np.sqrt(var)
    g_var = (num2_vec - (var + mean ** 2) * den_vec) / n0 - 2.0 * mean * g_mean
    g_std = g_var / (2.0 * std)
    std_err = float(np.sqrt(max(g_std @ cov @ g_std, 0.0)))
    return float(mean), mean_err, float(std), std_err


def size_statistics(solution, n_grid=None) -> Dict:
    """Verteilungen und Momente einer IFT mit Größenverteilungs-Kern.

    Primärgröße ist D_V (Kerne `size_*`) oder D_N (Kerne `size_*_n`, [G80a Gl. 1a]). Die
    jeweils anderen Verteilungen werden abgeleitet und auf max = 1 normiert; eine aus D_V
    abgeleitete D_N wird nur im auswertbaren Bereich angegeben (sonst NaN).

    Returns:
        dict mit 'R', 'primary' ('D_V'/'D_N'), 'f', 'f_err' (Primärgröße), 'derived'
        ({Name: normierte Verteilung}), 'r_min', 'mode', 'volume', 'mean_V', 'std_V',
        'mean_N', 'std_N' (+ '_err'), 'number_restricted', 'negative_fraction'
    """
    st = solution.settings
    kern = get_kernel(st.kind)
    if not kern.size:
        raise ValueError("Keine Größenverteilung (IFT-Art ohne Größen-Kern)")
    n = st.n_splines
    basis = make_basis(st.dmax, n, st.kind)
    c = solution.coefficients
    cov = solution.covariance[:n, :n]
    R = solution.r if n_grid is None else np.linspace(0.0, st.dmax, int(n_grid))
    Phi = basis.evaluate(R)
    f = Phi @ c
    f_err = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', Phi, cov, Phi), 0.0))
    v = kern.particle_volume(R)
    r_min = np.pi / float(np.max(solution.q))

    # Momente per Quadratur über die Basis
    rq, wq = basis.quadrature(8)
    phi_q = basis.evaluate(rq)
    W = wq[:, None] * phi_q                                   # ∫ f g(R) dR = (g·W)ᵀ c
    vq = kern.particle_volume(rq)
    fq = phi_q @ c
    fq_err = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', phi_q, cov, phi_q), 0.0))
    if kern.number:
        Wv = W * vq[:, None]                                  # D_V = D_N·v
        Wn = W
        keep = np.ones(len(rq), dtype=bool)
        vol = Wv.T @ np.ones_like(rq)
    else:
        Wv = W
        # D_N = D_V/v: nur für R ≥ π/q_max und signifikantes D_V (Rauschverstärkung)
        keep = (rq >= r_min) & (fq >= 2.0 * fq_err)
        Wn = W / np.where(keep, vq, np.inf)[:, None]
        vol = W.T @ np.ones_like(rq)
    mean_v = _ratio_stats(Wv.T @ rq, Wv.T @ np.ones_like(rq), Wv.T @ rq ** 2, c, cov)
    mean_n = _ratio_stats(Wn.T @ rq, Wn.T @ np.ones_like(rq), Wn.T @ rq ** 2, c, cov)

    def norm(y):
        m = np.nanmax(np.abs(y)) if np.any(np.isfinite(y)) else np.nan
        return y / m if np.isfinite(m) and m > 0 else y

    with np.errstate(divide='ignore', invalid='ignore'):
        if kern.number:
            derived = {'D_V': norm(f * v), 'D_I': norm(f * v * v)}
        else:
            dn = np.where((R >= r_min) & (f >= 2.0 * f_err), f / v, np.nan)
            derived = {'D_I': norm(f * v), 'D_N': norm(dn)}
    total_abs = float(np.sum(wq * np.abs(fq)))
    neg = float(np.sum(wq * np.maximum(-fq, 0.0)) / total_abs) if total_abs > 0 else np.nan
    return {
        'R': R, 'primary': 'D_N' if kern.number else 'D_V', 'f': f, 'f_err': f_err,
        'derived': derived, 'r_min': r_min, 'mode': float(R[int(np.argmax(f))]),
        'volume': float(vol @ c), 'volume_err': float(np.sqrt(max(vol @ cov @ vol, 0.0))),
        'mean_V': mean_v[0], 'mean_V_err': mean_v[1], 'std_V': mean_v[2],
        'std_V_err': mean_v[3],
        'mean_N': mean_n[0], 'mean_N_err': mean_n[1], 'std_N': mean_n[2],
        'std_N_err': mean_n[3], 'number_restricted': not kern.number,
        'negative_fraction': neg,
    }
