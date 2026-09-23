"""
Generalisierte indirekte Fourier-Transformation (GIFT).

    I(q) = S(q; d) · Σ c_ν ψ_ν(q)                                  [BP97 Gl. 5]

Die linearen Koeffizienten c (Formfaktor, modellfrei) werden für jeden
Strukturfaktor-Parametersatz d per stabilisierter Least-Squares-Rechnung bestimmt;
die nichtlinearen Parameter d minimieren die mittlere Abweichung MD(d) [B00 Gl. 4]
per Boltzmann-Simplex-Simulated-Annealing [B00].

λ-Behandlung: Während der BSSA-Suche ist λ fest (glatte MD-Fläche). Danach wird λ am
Optimum per Wendepunkt-Methode neu bestimmt; weicht es um mehr als einen Faktor 10^0.25
ab, folgt ein weiterer Zyklus ab dem gefundenen Optimum (max. `lambda_cycles`).
"""

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

import numpy as np

from .ift import IFTSettings, IFTSolution, IFTProblem, run_ift, LAMBDA_AUTO
from .structure_factors import get_model, DEFAULT_GIFT_MODEL
from .bssa import BSSASettings, minimize, BSSACancelled   # noqa: F401 (re-export)


@dataclass
class GIFTSettings:
    """Einstellungen für GIFT (vollständig in der Provenance dokumentiert)."""
    model: str = DEFAULT_GIFT_MODEL
    start: Dict[str, float] = field(default_factory=dict)
    lower: Dict[str, float] = field(default_factory=dict)
    upper: Dict[str, float] = field(default_factory=dict)
    fixed: List[str] = field(default_factory=list)
    bssa: BSSASettings = field(default_factory=BSSASettings)
    lambda_cycles: int = 3
    lambda_tolerance_log10: float = 0.25

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if k != 'bssa'}
        d['bssa'] = self.bssa.to_dict()
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        bssa = BSSASettings(**d.pop('bssa', {}))
        return cls(bssa=bssa, **d)


@dataclass
class GIFTResult:
    """Ergebnis der GIFT-Rechnung."""
    settings: GIFTSettings
    model_key: str
    params: Dict[str, float]
    param_errors: Dict[str, float]
    free: List[str]
    lower: Dict[str, float]
    upper: Dict[str, float]
    solution: IFTSolution                 # IFT mit S(q) am Optimum (inkl. p(r), Fit)
    structure_factor: np.ndarray
    form_factor: np.ndarray
    md: float
    md_without_sq: Optional[float]        # MD der IFT mit S = 1 (gleiches λ-Verfahren)
    n_evals: int
    lambda_history: List[float]
    lambda_converged: bool
    history: List[dict] = field(default_factory=list)   # BSSA-Verlauf (alle Zyklen)


def _bounds(model, settings, start):
    """Effektive Suchgrenzen: Benutzervorgabe > relativer Suchbereich > physikalisch."""
    lo, hi = {}, {}
    for p in model.params:
        default_lo, default_hi = p.lower, p.upper
        if p.relative_search and start.get(p.name, 0) > 0:
            default_lo = start[p.name] / p.relative_search
            default_hi = start[p.name] * p.relative_search
        lo[p.name] = float(settings.lower.get(p.name, default_lo))
        hi[p.name] = float(settings.upper.get(p.name, default_hi))
    for p in model.params:
        # Benutzergrenzen dürfen die physikalischen Grenzen nicht überschreiten
        lo[p.name] = max(lo[p.name], p.lower)
        hi[p.name] = min(hi[p.name], p.upper)
        if not lo[p.name] < hi[p.name]:
            raise ValueError(f"Ungültige Grenzen für {p.label}: {lo[p.name]} … {hi[p.name]}")
    return lo, hi


def run_gift(q, intensity, sigma, ift_settings: IFTSettings, settings: GIFTSettings,
             progress: Optional[Callable] = None, smearing=None) -> GIFTResult:
    """GIFT-Rechnung.

    Args:
        progress: progress(n_evals, T, md_best, params_best, cycle) → False bricht ab
    """
    model = get_model(settings.model)
    q = np.asarray(q, dtype=float)
    I = np.asarray(intensity, dtype=float)
    s = np.asarray(sigma, dtype=float)
    values = model.defaults()
    values.update({k: float(v) for k, v in settings.start.items() if k in values})
    lo, hi = _bounds(model, settings, values)
    free = [p.name for p in model.params if p.name not in settings.fixed]
    for name in values:
        if not lo[name] <= values[name] <= hi[name]:
            raise ValueError(f"Startwert {name} = {values[name]} liegt außerhalb "
                             f"[{lo[name]}, {hi[name]}]")

    def to_x(vals):
        return np.array([(vals[n] - lo[n]) / (hi[n] - lo[n]) for n in free])

    def to_vals(x):
        vals = dict(values)
        for n, xi in zip(free, x):
            vals[n] = lo[n] + xi * (hi[n] - lo[n])
        return vals

    problem = IFTProblem(q, I, s, ift_settings, smearing)
    auto_lambda = ift_settings.lam == LAMBDA_AUTO

    def s_of(vals):
        return model.evaluate(q, vals)

    # λ für die Suche: am Startpunkt per Wendepunkt (oder manuell vorgegeben)
    if auto_lambda:
        lam_rel = run_ift(q, I, s, ift_settings, smearing, s_of(values)).lam_rel
    else:
        lam_rel = float(ift_settings.lam)
    lambda_history = [lam_rel]
    history: List[dict] = []
    n_evals = 0
    lambda_converged = not auto_lambda
    cycle = 0

    for cycle in range(max(1, settings.lambda_cycles) if free else 0):
        lam_fixed = lam_rel

        def objective(x, lam_fixed=lam_fixed):
            vals = to_vals(x)
            sq = s_of(vals)
            if np.any(sq < 0):
                return np.inf                    # unphysikalisch [B00]
            return problem.md(sq, lam_fixed)

        def cb(n, T, fbest, xbest, cycle=cycle):
            if progress is None:
                return True
            return progress(n_evals + n, T, fbest, to_vals(xbest), cycle)

        bssa_settings = replace(settings.bssa, seed=int(settings.bssa.seed) + cycle)
        res = minimize(objective, to_x(values), bssa_settings, cb)
        for h in res.history:
            history.append({'cycle': cycle, 'evals': n_evals + h['evals'], 'T': h['T'],
                            'md': h['f_best'], 'params': to_vals(np.array(h['x_best']))})
        n_evals += res.n_evals
        values = to_vals(res.x)
        if not auto_lambda:
            break
        lam_new = run_ift(q, I, s, ift_settings, smearing, s_of(values)).lam_rel
        lambda_history.append(lam_new)
        if abs(np.log10(lam_new / lam_rel)) <= settings.lambda_tolerance_log10:
            lam_rel = lam_new
            lambda_converged = True
            break
        lam_rel = lam_new

    # Endgültige Lösung mit dem regulären λ-Verfahren (Wendepunkt oder manuell)
    sq = s_of(values)
    solution = run_ift(q, I, s, ift_settings, smearing, sq)
    md_plain = run_ift(q, I, s, ift_settings, smearing).md

    # Parameterfehler aus der Krümmung von χ² = M·MD am Optimum (bei festem λ):
    # Cov(d) ≈ 2·H_χ²⁻¹. Nur eine Näherung — die statistisch saubere Analyse ist DREAM.
    errors = {n: float('nan') for n in model.defaults()}
    if free:
        errors.update(_curvature_errors(
            lambda x: problem.md(s_of(to_vals(x)), solution.lam_rel), to_x(values),
            len(q), [hi[n] - lo[n] for n in free], free))
    for n in model.defaults():
        if n not in free:
            errors[n] = 0.0

    return GIFTResult(
        settings=settings, model_key=model.key, params=values, param_errors=errors,
        free=free, lower=lo, upper=hi, solution=solution, structure_factor=sq,
        form_factor=solution.extras.get('form_factor'), md=solution.md,
        md_without_sq=md_plain, n_evals=n_evals,
        lambda_history=lambda_history, lambda_converged=lambda_converged, history=history,
    )


def _curvature_errors(f, x0, n_points, scales, names, h=1e-3):
    """Numerische Hesse-Matrix von MD (normierte Koordinaten) → σ der Parameter."""
    n = len(x0)
    f0 = f(x0)
    H = np.zeros((n, n))
    steps = np.full(n, h)
    for i in range(n):
        if x0[i] - steps[i] < 0 or x0[i] + steps[i] > 1:
            steps[i] = max(min(x0[i], 1 - x0[i]), 1e-6)
    for i in range(n):
        ei = np.zeros(n)
        ei[i] = steps[i]
        H[i, i] = (f(x0 + ei) - 2 * f0 + f(x0 - ei)) / steps[i] ** 2
        for j in range(i + 1, n):
            ej = np.zeros(n)
            ej[j] = steps[j]
            H[i, j] = H[j, i] = (f(x0 + ei + ej) - f(x0 + ei - ej) - f(x0 - ei + ej)
                                 + f(x0 - ei - ej)) / (4 * steps[i] * steps[j])
    H_chi2 = n_points * H
    out = {}
    try:
        if not np.all(np.isfinite(H_chi2)):
            raise np.linalg.LinAlgError
        cov = 2.0 * np.linalg.inv(H_chi2)
        var = np.diag(cov)
        for k, name in enumerate(names):
            out[name] = float(np.sqrt(var[k]) * scales[k]) if var[k] > 0 else float('nan')
    except np.linalg.LinAlgError:
        out = {name: float('nan') for name in names}
    return out
