"""
Kennzahlen einer p(r)-Lösung und Explorer (Scans über Dmax, λ, N sowie Dmax × λ-Karten).

Kennzahlen (SasView-kompatibel definiert, damit Zahlen direkt vergleichbar sind; die
Interpretation unterscheidet sich teilweise, siehe docs/GIFT/KENNZAHLEN.md):

- Oszillation  (Dmax/π)·√(∫p′² dr / ∫p² dr) auf 100 Stützstellen r = 0 … Dmax − Dmax/100
               (SasView `Invertor.oscillations`; Kugel ≈ 1.1)
- Positive Fraction      Σ max(p, 0) / Σ |p|
- 1σ-Positive Fraction   Σ p·[p > σ_p] / Σ |p|  (σ_p aus der vollen Kovarianz; SasView
                         verwendet nur deren Diagonale)
- Maxima       Zahl der lokalen Maxima (SasView `npeaks`)
- MD, χ²/dof   χ²/M bzw. χ²/(M − N_g)
- N_g          effektive Zahl der von den Daten bestimmten Parameter Σ β/(β+λ)
- log-Evidenz  log p(I | λ, Dmax) [Hansen 2000]
- Randanteil   max |p(r)| für r ≥ 0.9·Dmax relativ zum Maximum (≤ 0.1: p(r) läuft vor Dmax
               gegen 0; entspricht dem Flag pr_end)
- Rg, I(0), Untergrund

Der Explorer nutzt die verallgemeinerte Eigenzerlegung (ift.IFTDecomposition): Für jedes
Dmax wird einmal zerlegt, alle λ kosten danach nur O(N²). Bei GIFT wird mit festem S(q)
(Optimum) gerechnet.
"""

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

import numpy as np

from .ift import (IFTSettings, IFTDecomposition, _select_lambda, LAMBDA_AUTO,
                  LAMBDA_EVIDENCE, lambda_grid)
from .splines import SplineBasis
from .transform import FOUR_PI

N_SLICE = 100
OSC_GOOD = 1.6              # Standardschwelle „glattes p(r)“ (Kugel: 1.1)
MD_FACTOR_GOOD = 1.25       # MD ≤ Faktor × kleinstes MD im Scan …
MD_SIGMA_GOOD = 3.0         # … oder ≤ kleinstes MD + 3·√(2/M) (statistische Streuung von MD)


def md_acceptable(md, n_points, md_factor=MD_FACTOR_GOOD, n_sigma=MD_SIGMA_GOOD,
                  reference=None):
    """MD „so gut wie das beste“: MD ≤ MD_ref + max((f−1)·MD_ref, n·√(2/M)).

    MD_ref ist das kleinste MD unter `reference` (Maske, z. B. nur glatte Lösungen) bzw.
    im ganzen Scan. Die rein relative Toleranz ist zu streng, wenn MD mit wachsendem Dmax
    durch Überanpassung weiter sinkt; √(2/M) ist die Standardabweichung von χ²/M bei
    korrektem Modell. Referenz „nur glatte Lösungen“: Ein kleineres MD, das nur ein stark
    oszillierendes oder überwiegend negatives p(r) erreicht (z. B. bei einem Korrelations-
    peak in den Daten), soll den glatten Bereich nicht ausschließen."""
    md = np.asarray(md, dtype=float)
    ref = md if reference is None or not np.any(reference) else md[reference]
    md_min = np.nanmin(ref)
    tol = max((md_factor - 1.0) * md_min, n_sigma * np.sqrt(2.0 / n_points))
    return md <= md_min + tol

METRICS = ('oscillation', 'md', 'chi2_dof', 'log_evidence', 'positive_fraction',
           'positive_1sigma', 'n_peaks', 'end_fraction', 'rg', 'i0', 'n_good', 'background')
END_GOOD = 0.1              # p(r) im letzten Zehntel vor Dmax ≤ 10 % des Maximums (Flag pr_end)


def sasview_r(dmax, nslice=N_SLICE):
    dx = dmax / nslice
    return np.linspace(0.0, dmax - dx, nslice)


def _moment_vectors(basis):
    rq, wq = basis.quadrature(8)
    phi = basis.evaluate(rq)
    return FOUR_PI * (wq @ phi), FOUR_PI * ((wq * rq ** 2) @ phi)


def pr_metrics(basis: SplineBasis, C, pr_var_fn):
    """Kennzahlen für Koeffizienten C (Λ, N).

    Args:
        pr_var_fn: Phi (R, N) → Varianz von p(r) (Λ, R)
    """
    C = np.atleast_2d(C)
    r = sasview_r(basis.dmax)
    Phi = basis.evaluate(r)
    P = C @ Phi.T                                              # (Λ, R)
    dP = C @ basis.evaluate_derivative(r).T
    sum_p2 = np.sum(P * P, axis=1)
    abs_p = np.sum(np.abs(P), axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        osc = np.where(sum_p2 > 0, np.sqrt(np.sum(dP * dP, axis=1) / sum_p2)
                       * basis.dmax / np.pi, np.nan)
        pos = np.where(abs_p > 0, np.sum(np.maximum(P, 0.0), axis=1) / abs_p, np.nan)
        err = np.sqrt(np.maximum(pr_var_fn(Phi), 0.0))
        pos1 = np.where(abs_p > 0, np.sum(np.where(P > err, P, 0.0), axis=1) / abs_p, np.nan)
    rising = P[:, :-1] < P[:, 1:]
    peaks = (np.sum((rising[:, :-1] != rising[:, 1:]) & rising[:, :-1], axis=1)
             + 1 - rising[:, 0].astype(int) + rising[:, -1].astype(int))
    pmax = np.max(P, axis=1)
    tail = r >= 0.9 * basis.dmax
    with np.errstate(divide='ignore', invalid='ignore'):
        end = np.where(pmax > 0, np.max(np.abs(P[:, tail]), axis=1) / pmax, np.nan)
    m0, m2 = _moment_vectors(basis)
    i0 = C @ m0
    m2c = C @ m2
    with np.errstate(divide='ignore', invalid='ignore'):
        rg = np.where((i0 > 0) & (m2c > 0), np.sqrt(m2c / (2.0 * i0)), np.nan)
    return {'oscillation': osc, 'positive_fraction': pos, 'positive_1sigma': pos1,
            'n_peaks': peaks.astype(float), 'rg': rg, 'i0': i0, 'end_fraction': end}


def _grid_metrics(dec: IFTDecomposition, lam_rel):
    """Alle Kennzahlen für eine Zerlegung und ein λ_rel-Gitter (Λ,)."""
    g = dec.scan(lam_rel)
    weights = dec.beta[None, :] / (dec.beta[None, :] + g['lam'][:, None]) ** 2   # (Λ, N)

    def var_fn(Phi):
        P1 = Phi @ dec.back.T                                  # (R, N)
        return weights @ (P1 * P1).T                           # (Λ, R)

    out = pr_metrics(dec.basis, g['C'], var_fn)
    m = len(dec.q)
    out.update(md=g['md'], log_evidence=g['log_evidence'], n_good=g['n_good'],
               chi2_dof=g['chi2'] / np.maximum(m - g['n_good'], 1.0))
    if dec.settings.background:
        out['background'] = (dec.w @ dec.yw - (dec.w @ dec.Aw) @ g['C'].T) / dec.w_norm2
    else:
        out['background'] = np.full(len(g['lam']), np.nan)
    return out


def solution_metrics(sol) -> Dict[str, float]:
    """Kennzahlen einer fertigen IFT/GIFT-Lösung (volle Kovarianz)."""
    st = sol.settings
    n = st.n_splines
    basis = SplineBasis(st.dmax, n)
    cov = sol.covariance[:n, :n]
    out = pr_metrics(basis, sol.coefficients[None, :],
                     lambda Phi: np.einsum('ij,jk,ik->i', Phi, cov, Phi)[None, :])
    out = {k: float(v[0]) for k, v in out.items()}
    n_good = sol.extras.get('n_good', float('nan'))
    out.update(md=float(sol.md), log_evidence=sol.extras.get('log_evidence', float('nan')),
               n_good=n_good, chi2_dof=float(sol.chi2 / max(len(sol.q) - n_good, 1.0)),
               background=float('nan') if sol.background is None else float(sol.background))
    return out


def _lambda_choice(dec: IFTDecomposition, settings: IFTSettings):
    """λ_rel wie in run_ift (manuell, Wendepunkt oder Evidenz) + Wendepunkt gefunden?"""
    grid, g = lambda_grid(dec, settings)
    idx_i, _slope, found = _select_lambda(grid, g['md'], g['nc'], settings.md_tolerance,
                                          settings.plateau_slope)
    idx_e = int(np.argmax(g['log_evidence']))
    if settings.lam != LAMBDA_AUTO:
        chosen = float(settings.lam)
    elif settings.lam_method == LAMBDA_EVIDENCE:
        chosen = float(grid[idx_e])
    else:
        chosen = float(grid[idx_i])
    return chosen, float(grid[idx_i]), bool(found), float(grid[idx_e])


@dataclass
class ExplorerScan:
    """1D-Scan: Kennzahlen als Funktion eines Parameters (Dmax, λ oder N)."""
    param: str
    values: np.ndarray
    lam_rel: np.ndarray                  # verwendetes λ je Punkt
    metrics: Dict[str, np.ndarray]
    inflexion_found: np.ndarray
    lam_inflexion: np.ndarray
    lam_evidence: np.ndarray


@dataclass
class ExplorerMap:
    """2D-Karte Dmax × λ (Metriken als (nλ, nDmax))."""
    dmax: np.ndarray
    lam_rel: np.ndarray
    metrics: Dict[str, np.ndarray]
    lam_inflexion: np.ndarray
    inflexion_found: np.ndarray
    lam_evidence: np.ndarray
    q_min: float
    n_points: int = 0

    def good_region(self, osc_max=OSC_GOOD, md_factor=MD_FACTOR_GOOD, pos_min=None):
        """Glattes p(r) (Oszillation ≤ osc_max) bei voller Anpassung (md_acceptable)."""
        smooth = _physical(self.metrics) & (self.metrics['oscillation'] <= osc_max)
        good = smooth & md_acceptable(self.metrics['md'], self.n_points, md_factor,
                                      reference=smooth)
        if pos_min is not None:
            good &= self.metrics['positive_fraction'] >= pos_min
        return good


def _physical(m, end_max=END_GOOD):
    """I(0) = (Σ Δρ·V)² > 0, Rg endlich (gilt auch bei Kontrastwechsel) und p(r) läuft vor
    Dmax gegen 0 (sonst ist Dmax zu klein)."""
    return (m['i0'] > 0) & np.isfinite(m['rg']) & (m['end_fraction'] <= end_max)


def _check(progress, k, n):
    if progress is not None and progress(k, n) is False:
        raise ExplorerCancelled()


class ExplorerCancelled(Exception):
    """Abbruch eines Explorer-Scans."""


def scan_1d(q, I, s, settings: IFTSettings, param: str, values, smearing=None,
            structure_factor=None, progress: Optional[Callable] = None) -> ExplorerScan:
    """Kennzahlen über einen Parameter.

    param: 'dmax' oder 'n_splines' (λ je Punkt nach dem Verfahren der Einstellungen) bzw.
    'lam' (Werte = λ_rel bei festem Dmax/N).
    """
    values = np.asarray(values, dtype=float)
    if param == 'lam':
        dec = IFTDecomposition(q, I, s, settings, smearing, structure_factor)
        m = _grid_metrics(dec, values)
        _c, li, found, le = _lambda_choice(dec, settings)
        n = len(values)
        return ExplorerScan(param, values, values.copy(), m, np.full(n, found),
                            np.full(n, li), np.full(n, le))
    if param not in ('dmax', 'n_splines'):
        raise ValueError(f"Unbekannter Scan-Parameter: {param}")
    rows, lam, found, li, le = [], [], [], [], []
    for k, v in enumerate(values):
        _check(progress, k, len(values))
        st = replace(settings, dmax=float(v)) if param == 'dmax' else \
            replace(settings, n_splines=int(round(v)))
        dec = IFTDecomposition(q, I, s, st, smearing, structure_factor)
        chosen, lam_i, f, lam_e = _lambda_choice(dec, st)
        rows.append(_grid_metrics(dec, [chosen]))
        lam.append(chosen)
        found.append(f)
        li.append(lam_i)
        le.append(lam_e)
    metrics = {key: np.array([r[key][0] for r in rows]) for key in rows[0]}
    return ExplorerScan(param, values, np.array(lam), metrics, np.array(found),
                        np.array(li), np.array(le))


def scan_map(q, I, s, settings: IFTSettings, dmax_values, lam_values, smearing=None,
             structure_factor=None, progress: Optional[Callable] = None) -> ExplorerMap:
    """2D-Karte über Dmax × λ_rel."""
    dmax_values = np.asarray(dmax_values, dtype=float)
    lam_values = np.asarray(lam_values, dtype=float)
    cols, li, found, le = [], [], [], []
    for k, d in enumerate(dmax_values):
        _check(progress, k, len(dmax_values))
        st = replace(settings, dmax=float(d))
        dec = IFTDecomposition(q, I, s, st, smearing, structure_factor)
        cols.append(_grid_metrics(dec, lam_values))
        _c, lam_i, f, lam_e = _lambda_choice(dec, st)
        li.append(lam_i)
        found.append(f)
        le.append(lam_e)
    metrics = {key: np.stack([c[key] for c in cols], axis=1) for key in cols[0]}
    return ExplorerMap(dmax=dmax_values, lam_rel=lam_values, metrics=metrics,
                       lam_inflexion=np.array(li), inflexion_found=np.array(found),
                       lam_evidence=np.array(le), q_min=float(np.min(q)), n_points=len(q))


def suggest_dmax(q, I, s, settings: IFTSettings, factors=None, osc_max=OSC_GOOD,
                 md_factor=MD_FACTOR_GOOD, smearing=None, structure_factor=None):
    """Kleinstes Dmax mit glattem p(r) und voll angepassten Daten.

    Scan über Dmax = f·π/q_min (Standard f = 0.05 … 3, logarithmisch, damit auch Teilchen
    weit unter π/q_min gefunden werden) mit dem λ-Verfahren der Einstellungen;
    „gut“ heißt I(0) > 0, p(r) vor Dmax ≈ 0 (Randanteil ≤ 0.1), Oszillation ≤ osc_max, MD akzeptabel (md_acceptable) und (beim
    Wendepunkt-Verfahren) Wendepunkt gefunden. Gedacht für Daten ohne Guinier-Bereich, bei
    denen Dmax nicht aus Rg abgeschätzt werden kann.

    Returns:
        (Dmax oder None, ExplorerScan)
    """
    if factors is None:
        factors = np.geomspace(0.05, 3.0, 45)
    limit = np.pi / float(np.min(q))
    scan = scan_1d(q, I, s, settings, 'dmax', np.asarray(factors) * limit, smearing,
                   structure_factor)
    m = scan.metrics
    smooth = _physical(m) & (m['oscillation'] <= osc_max)
    if settings.lam == LAMBDA_AUTO and settings.lam_method != LAMBDA_EVIDENCE:
        smooth &= scan.inflexion_found
    good = smooth & md_acceptable(m['md'], len(q), md_factor, reference=smooth)
    idx = np.nonzero(good)[0]
    return (float(scan.values[idx[0]]) if len(idx) else None), scan
