"""
Statistische Absicherung der (G)IFT-Parameter (Plan §2.3):

    LHS-Screening → DREAM(ZS) über (S(q)-Parameter, log λ, Dmax) → Posterior-Prädiktion

Die Likelihood ist die marginale Likelihood mit analytisch herausintegrierten
Spline-Koeffizienten (likelihood.py). Für die Posterior-Prädiktion werden ausgedünnte
Proben θ gezogen und je Probe c ~ N(ĉ, (B + λK)⁻¹); daraus entstehen Bänder für p(r),
I_fit(q), S(q) und P(q) sowie die Verteilungen von Rg und I(0).

GUI-frei; der Dialog startet `run_uncertainty()` auf Knopfdruck.
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .dream import DreamSettings, DreamResult, sample as dream_sample, DreamCancelled  # noqa: F401
from .likelihood import (MarginalLikelihood, ParameterSpace, evaluate_log_posterior,
                         LOG_LAMBDA, DMAX)
from .screening import ScreeningResult, screen, default_screen_size
from .diagnostics import diagnose_uncertainty
from .splines import SplineBasis
from .structure_factors import get_model
from .transform import FOUR_PI
from . import parallel

QUANTILES = (2.5, 16.0, 50.0, 84.0, 97.5)


@dataclass
class UncertaintySettings:
    """Einstellungen der DREAM-Analyse (vollständig im Provenance-Record)."""
    sample_params: Optional[List[str]] = None     # None → freie GIFT-Parameter
    sample_lambda: bool = True
    sample_dmax: bool = True
    lower: Dict[str, float] = field(default_factory=dict)   # auch 'log_lambda', 'dmax'
    upper: Dict[str, float] = field(default_factory=dict)
    gaussian: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # Name → (μ, σ)
    dmax_limit_upper: bool = False     # π/q_min als Obergrenze der Dmax-Priorverteilung
    lambda_decades: float = 4.0        # Standardbereich log λ: Optimum ± n Dekaden
    dmax_range: Tuple[float, float] = (0.75, 1.5)   # Standardbereich Dmax relativ
    scale_sigma: bool = False          # σ ← σ·√MD (MD am Optimum)
    n_screen: Optional[int] = None     # None → 100·d (200 … 1000)
    n_predict: int = 400               # ausgedünnte Proben für die Bänder
    dream: DreamSettings = field(default_factory=DreamSettings)
    n_workers: Optional[int] = None    # None → parallel.default_workers(); 0 → Hauptprozess
    chunk: int = 2                     # feste Blockgröße je Pool-Aufgabe (bitgleich)

    def to_dict(self):
        d = asdict(self)
        d['gaussian'] = {k: list(v) for k, v in self.gaussian.items()}
        d['dmax_range'] = list(self.dmax_range)
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        dream = DreamSettings(**d.pop('dream', {}))
        d['gaussian'] = {k: tuple(v) for k, v in d.get('gaussian', {}).items()}
        d['dmax_range'] = tuple(d.get('dmax_range', (0.75, 1.5)))
        known = set(cls.__dataclass_fields__)
        return cls(dream=dream, **{k: v for k, v in d.items() if k in known})


@dataclass
class UncertaintyResult:
    settings: UncertaintySettings
    space: ParameterSpace
    labels: Dict[str, str]
    units: Dict[str, str]
    reference: Dict[str, float]          # BSSA-/IFT-Optimum (bzw. Wendepunkt-λ, gewähltes Dmax)
    log_posterior_reference: float
    summary: Dict[str, Dict[str, float]]
    correlation: np.ndarray
    modes: Dict[str, int]                # Anzahl getrennter Modi je Parameter (1D-KDE)
    dream: DreamResult
    screening: ScreeningResult
    bands: Dict[str, np.ndarray]
    rg: Dict[str, float]
    i0: Dict[str, float]
    rg_samples: np.ndarray
    i0_samples: np.ndarray
    sigma_scale: float
    q_min: float
    model_key: str
    fixed_values: Dict[str, float]
    n_workers: int
    runtime_s: float
    flags: list = field(default_factory=list)

    @property
    def names(self):
        return list(self.space.names)

    def results_summary(self):
        """Kompakte Zusammenfassung für den Provenance-Record."""
        d = self.dream
        return {
            'converged': bool(d.converged), 'r_hat': dict(zip(self.names, map(float, d.r_hat))),
            'n_evals': int(d.n_evals), 'n_generations': int(d.n_generations),
            'burn_in_generations': int(d.burn_in), 'acceptance_rate': d.acceptance_rate,
            'n_posterior_samples': int((d.n_generations + 1 - d.burn_in) * d.chains.shape[1]),
            'outlier_chains_reset': int(d.outliers_reset), 'archive_size': int(d.archive_size),
            'p_cr': d.p_cr.tolist(),
            'posterior': self.summary, 'reference': self.reference,
            'log_posterior_reference': self.log_posterior_reference,
            'correlation': self.correlation.tolist(), 'modes': self.modes,
            'rg_nm': self.rg, 'i0': self.i0, 'sigma_scale': self.sigma_scale,
            'runtime_s': self.runtime_s,
        }


def _labels(model_key):
    model = get_model(model_key)
    labels = {p.name: p.label for p in model.params}
    units = {p.name: p.unit for p in model.params}
    labels.update({LOG_LAMBDA: 'log₁₀ λ_rel', DMAX: 'Dmax'})
    units.update({LOG_LAMBDA: '', DMAX: 'nm'})
    return labels, units


def build_space(analysis, settings: UncertaintySettings):
    """Abgetastete Parameter, Priorgrenzen und Referenzpunkt aus einer (G)IFT-Analyse."""
    sol = analysis.solution
    g = analysis.gift
    model_key = g.model_key if g is not None else 'none'
    model = get_model(model_key)
    values = dict(g.params) if g is not None else {}
    free = list(g.free) if g is not None else []
    wanted = free if settings.sample_params is None else \
        [n for n in settings.sample_params if n in values]
    names, lo, hi, ref = [], [], [], {}
    for n in wanted:
        spec = next(p for p in model.params if p.name == n)
        l_ = settings.lower.get(n, g.lower.get(n, spec.lower))
        h_ = settings.upper.get(n, g.upper.get(n, spec.upper))
        names.append(n)
        lo.append(max(float(l_), spec.lower))
        hi.append(min(float(h_), spec.upper))
        ref[n] = float(values[n])
    if settings.sample_lambda:
        center = float(np.log10(sol.lam_rel))
        st = sol.settings
        scan_lo = min(np.log10(st.lam_rel_min), np.log10(sol.scan.lam_rel[0]))
        l_ = settings.lower.get(LOG_LAMBDA, max(center - settings.lambda_decades, scan_lo))
        h_ = settings.upper.get(LOG_LAMBDA, min(center + settings.lambda_decades,
                                                np.log10(st.lam_rel_max)))
        names.append(LOG_LAMBDA)
        lo.append(float(l_))
        hi.append(float(h_))
        ref[LOG_LAMBDA] = center
    if settings.sample_dmax:
        d0 = float(sol.settings.dmax)
        l_ = settings.lower.get(DMAX, settings.dmax_range[0] * d0)
        h_ = settings.upper.get(DMAX, settings.dmax_range[1] * d0)
        if settings.dmax_limit_upper:
            h_ = min(h_, np.pi / float(sol.q[0]))
        names.append(DMAX)
        lo.append(float(l_))
        hi.append(float(h_))
        ref[DMAX] = d0
    if not names:
        raise ValueError("Keine Parameter zum Abtasten ausgewählt")
    for n, l_, h_ in zip(names, lo, hi):
        if not h_ > l_:
            raise ValueError(f"Ungültige Priorgrenzen für {n}: {l_} … {h_}")
    gaussian = {k: (float(v[0]), float(v[1])) for k, v in settings.gaussian.items()
                if k in names and float(v[1]) > 0}
    space = ParameterSpace(names, np.array(lo), np.array(hi), gaussian)
    return space, model_key, values, ref


def run_uncertainty(analysis, settings: UncertaintySettings,
                    progress: Optional[Callable] = None) -> UncertaintyResult:
    """DREAM-Analyse einer fertigen (G)IFT-Analyse.

    Args:
        progress: progress(phase, n_evals, generation, max R̂, Akzeptanzrate) → False bricht
            ab (DreamCancelled). phase ∈ {'screening', 'dream', 'predict'}.
    """
    t0 = time.perf_counter()
    sol = analysis.solution
    space, model_key, values, ref = build_space(analysis, settings)
    sigma_scale = float(np.sqrt(sol.md)) if settings.scale_sigma else 1.0
    ev = MarginalLikelihood(sol.q, sol.intensity, sol.sigma * sigma_scale, sol.settings,
                            model_key, values, space, sol.lam_rel)
    workers = parallel.default_workers() if settings.n_workers is None \
        else max(0, int(settings.n_workers))
    ds = settings.dream
    d = space.dim

    def check(phase, *args):
        if progress is not None and progress(phase, *args) is False:
            raise DreamCancelled()

    # 1) Screening
    check('screening', 0, 0, float('inf'), 0.0)
    n_screen = settings.n_screen or default_screen_size(d)
    scr = screen(ev, n_screen, ds.seed, workers, chunk=max(16, settings.chunk))
    check('screening', n_screen, 0, float('inf'), 0.0)

    # 2) DREAM(ZS): Archiv aus der LHS-Stichprobe (Priorverteilung), Ketten ab den besten
    #    Screening-Punkten und dem BSSA-/IFT-Optimum
    theta_ref = np.array([[ref[n] for n in space.names]])
    lp_ref = float(evaluate_log_posterior(ev, theta_ref, workers, 1)[0])
    m0 = min(len(scr.samples), max(10 * d, 2 * ds.n_chains, 2 * ds.delta_max + 1))
    z_init = scr.samples[:m0]
    cand = np.vstack([theta_ref, scr.samples])
    cand_lp = np.concatenate([[lp_ref], scr.log_p])
    order = np.argsort(np.where(np.isfinite(cand_lp), -cand_lp, np.inf), kind='stable')
    order = order[:ds.n_chains]
    if len(order) < ds.n_chains or not np.all(np.isfinite(cand_lp[order])):
        raise ValueError("Zu wenige gültige Startpunkte im Screening — Priorgrenzen prüfen")
    x_init, lp_init = cand[order], cand_lp[order]

    def log_density(theta):
        return evaluate_log_posterior(ev, theta, workers, settings.chunk)

    def on_gen(n, gen, rhat, acc):
        check('dream', n_screen + 1 + n, gen, rhat, acc)
        return True

    dres = dream_sample(log_density, space.lower, space.upper, ds, z_init, x_init, lp_init,
                        progress=on_gen)

    # 3) Posterior-Auswertung
    check('predict', n_screen + 1 + dres.n_evals, dres.n_generations,
          float(np.max(dres.r_hat)), dres.acceptance_rate)
    x, lp = dres.posterior()
    summary = _summarize(space, x, lp, ref)
    corr = np.corrcoef(x.T) if d > 1 else np.ones((1, 1))
    corr = np.atleast_2d(np.nan_to_num(corr, nan=0.0))
    modes = {n: count_modes(x[:, k], space.lower[k], space.upper[k])
             for k, n in enumerate(space.names)}
    bands, rg_s, i0_s = _predict(ev, x, settings.n_predict, [int(ds.seed), 2])
    labels, units = _labels(model_key)

    result = UncertaintyResult(
        settings=settings, space=space, labels={n: labels[n] for n in space.names},
        units={n: units[n] for n in space.names}, reference=ref,
        log_posterior_reference=lp_ref, summary=summary, correlation=corr, modes=modes,
        dream=dres, screening=scr, bands=bands, rg=_quantile_summary(rg_s),
        i0=_quantile_summary(i0_s), rg_samples=rg_s, i0_samples=i0_s,
        sigma_scale=sigma_scale, q_min=float(sol.q[0]), model_key=model_key,
        fixed_values={k: v for k, v in values.items() if k not in space.names},
        n_workers=workers, runtime_s=time.perf_counter() - t0)
    result.flags = diagnose_uncertainty(result)
    return result


# ---------------------------------------------------------------------------
# Auswertung
# ---------------------------------------------------------------------------

def _quantile_summary(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {k: float('nan') for k in ('median', 'q2.5', 'q16', 'q84', 'q97.5', 'mean', 'std')}
    q = np.percentile(v, QUANTILES)
    return {'median': float(q[2]), 'q2.5': float(q[0]), 'q16': float(q[1]),
            'q84': float(q[3]), 'q97.5': float(q[4]), 'mean': float(v.mean()),
            'std': float(v.std(ddof=1)) if v.size > 1 else 0.0}


def _summarize(space, x, lp, ref):
    i_map = int(np.argmax(lp))
    out = {}
    for k, n in enumerate(space.names):
        s = _quantile_summary(x[:, k])
        s['map'] = float(x[i_map, k])
        s['reference'] = float(ref[n])
        s['prior_std'] = float(space.prior_std()[k])
        span = space.upper[k] - space.lower[k]
        s['mass_at_lower'] = float(np.mean(x[:, k] <= space.lower[k] + 0.02 * span))
        s['mass_at_upper'] = float(np.mean(x[:, k] >= space.upper[k] - 0.02 * span))
        out[n] = s
    return out


def count_modes(v, lower, upper, n_grid=256, rel_height=0.2, dip=0.5):
    """Zahl getrennter Modi einer 1D-Stichprobe (Gauß-KDE, Silverman-Bandbreite).

    Ein Maximum zählt, wenn es ≥ rel_height·Hauptmaximum ist und das Minimum zu seinem
    Nachbarn unter dip·(kleineres der beiden Maxima) fällt."""
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < 20 or np.std(v) == 0:
        return 1
    if v.size > 4000:
        v = v[np.linspace(0, v.size - 1, 4000).astype(int)]
    grid = np.linspace(lower, upper, n_grid)
    bw = 1.06 * np.std(v) * v.size ** (-0.2)
    dens = np.zeros(n_grid)
    for s in range(0, v.size, 1000):
        dens += np.exp(-0.5 * ((grid[:, None] - v[None, s:s + 1000]) / bw) ** 2).sum(axis=1)
    peaks = [i for i in range(1, n_grid - 1) if dens[i] >= dens[i - 1] and dens[i] > dens[i + 1]]
    if dens[0] > dens[1]:
        peaks.insert(0, 0)
    if dens[-1] > dens[-2]:
        peaks.append(n_grid - 1)
    peaks = [i for i in peaks if dens[i] >= rel_height * dens.max()]
    if not peaks:
        return 1
    modes = [peaks[0]]
    for p in peaks[1:]:
        lo_ = dens[modes[-1]:p + 1].min()
        if lo_ < dip * min(dens[modes[-1]], dens[p]):
            modes.append(p)
        elif dens[p] > dens[modes[-1]]:
            modes[-1] = p
    return len(modes)


def _predict(ev: MarginalLikelihood, x, n_predict, seed_entropy):
    """Posterior-Prädiktion: Bänder (Quantile) für p(r), I_fit, S(q), P(q); Rg, I(0)."""
    rng = np.random.default_rng(seed_entropy)
    n = min(int(n_predict), len(x))
    idx = np.sort(rng.choice(len(x), n, replace=False))
    theta = x[idx]
    res = ev.solve(theta, want_solution=True)
    rows, A = res['A']
    st = ev.settings
    N = st.n_splines
    unit = SplineBasis(1.0, N)
    d_all = res['dmax']
    r = np.linspace(0.0, float(np.max(d_all[rows])), int(st.n_r))
    rq, wq = unit.quadrature(8)
    phi_q = unit.evaluate(rq)
    m0_unit = FOUR_PI * (wq @ phi_q)                    # I(0) = D·m0_unit·c
    m2_unit = FOUR_PI * ((wq * rq ** 2) @ phi_q)        # ∫r²p = D³·m2_unit·c
    pr, ifit, pq, sq, rg, i0 = [], [], [], [], [], []
    c_prep = ev._prepared()
    for j, row in enumerate(rows):
        L = res['L'][row]
        if not np.all(np.isfinite(L)):
            continue
        c = res['c_hat'][row] + _solve_upper(L.T, rng.standard_normal(N))
        D = d_all[row]
        S = res['S'][row]
        Pq = A[j] @ c
        I_fit = S * Pq
        if st.background:
            w = c_prep['w']
            bg_mean = float(w @ (c_prep['yw'] - (A[j] * (S / ev.s)[:, None]) @ c)) / c_prep['w_norm2']
            I_fit = I_fit + bg_mean + rng.standard_normal() / np.sqrt(c_prep['w_norm2'])
        p = unit.evaluate(r / D) @ c
        pr.append(p)
        ifit.append(I_fit)
        pq.append(Pq)
        sq.append(S)
        i0_ = D * float(m0_unit @ c)
        m2 = D ** 3 * float(m2_unit @ c)
        i0.append(i0_)
        rg.append(np.sqrt(m2 / (2.0 * i0_)) if i0_ > 0 and m2 > 0 else np.nan)
    q = ev.q
    bands = {'r': r, 'q': q, 'quantiles': np.array(QUANTILES),
             'pr': np.percentile(np.array(pr), QUANTILES, axis=0),
             'i_fit': np.percentile(np.array(ifit), QUANTILES, axis=0),
             'pq': np.percentile(np.array(pq), QUANTILES, axis=0),
             'sq': np.percentile(np.array(sq), QUANTILES, axis=0),
             'n_draws': len(pr)}
    return bands, np.array(rg), np.array(i0)


def _solve_upper(U, b):
    from scipy.linalg import solve_triangular
    return solve_triangular(U, b, lower=False, check_finite=False)
