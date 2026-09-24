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

Mehrfachstart: Im ersten Zyklus laufen `n_starts` unabhängige BSSA-Suchen (Lauf 0 ab den
Startwerten, weitere ab zufälligen Punkten im Suchbereich, Seeds seed + 1000·k). Die
beste wird übernommen. Wie oft das beste Minimum erreicht wurde, ist ein Maß für die
Zuverlässigkeit (Flag `gift_multistart`). Bei geladenen Systemen (RMSA) hat die MD-Fläche
ausgeprägte Nebenminima [F00].
"""

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional

import numpy as np

from .ift import IFTSettings, IFTSolution, IFTProblem, run_ift, LAMBDA_AUTO
from .structure_factors import get_model, DEFAULT_GIFT_MODEL
from .bssa import BSSASettings, minimize, BSSACancelled   # noqa: F401 (re-export)
from . import parallel


@dataclass
class GIFTSettings:
    """Einstellungen für GIFT (vollständig in der Provenance dokumentiert)."""
    model: str = DEFAULT_GIFT_MODEL
    start: Dict[str, float] = field(default_factory=dict)
    lower: Dict[str, float] = field(default_factory=dict)
    upper: Dict[str, float] = field(default_factory=dict)
    fixed: Optional[List[str]] = None      # None → Standard des Modells (fixed_default)
    bssa: BSSASettings = field(default_factory=BSSASettings)
    lambda_cycles: int = 3
    lambda_tolerance_log10: float = 0.25
    n_starts: Optional[int] = None         # None → Standard des Modells (HS: 4, RMSA: 8)
    # Prozesse für die BSSA-Starts: None → parallel.default_workers(), ≥ 1 → Prozess-Pool.
    # Im Pool rechnet BLAS einfädig; das Ergebnis ist daher von der Worker-Zahl
    # unabhängig bitgleich (Seeds hängen an den Starts). 0 → im Hauptprozess (Diagnose;
    # mehrfädiges BLAS, nicht bitgleich zu den Pool-Ergebnissen).
    n_workers: Optional[int] = None

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
    model_info: Dict[str, float] = field(default_factory=dict)   # z. B. Debye-Länge (RMSA)
    starts: List[dict] = field(default_factory=list)   # Ergebnisse der Mehrfachstarts
    n_workers: int = 1                                  # verwendete Prozesse


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


class _Search:
    """Picklebare Beschreibung der BSSA-Suche (Daten, Modell, Grenzen, festes λ)."""

    def __init__(self, q, I, s, ift_settings, smearing, model_key, values, free, lo, hi,
                 lam_fixed):
        self.q, self.I, self.s = q, I, s
        self.ift_settings, self.smearing = ift_settings, smearing
        self.model_key, self.values, self.free = model_key, dict(values), list(free)
        self.lo, self.hi, self.lam_fixed = dict(lo), dict(hi), float(lam_fixed)
        self._problem = None

    def __getstate__(self):
        state = dict(self.__dict__)
        state['_problem'] = None          # wird im Worker neu aufgebaut
        return state

    def to_vals(self, x):
        vals = dict(self.values)
        for n, xi in zip(self.free, x):
            vals[n] = self.lo[n] + xi * (self.hi[n] - self.lo[n])
        return vals

    def objective(self, x):
        if self._problem is None:
            self._problem = IFTProblem(self.q, self.I, self.s, self.ift_settings, self.smearing)
        sq = get_model(self.model_key).evaluate(self.q, self.to_vals(x))
        if np.any(sq < 0):
            return np.inf                    # unphysikalisch [B00]
        return self._problem.md(sq, self.lam_fixed)


def _run_start(search, x_start, bssa_settings, start, cycle, progress=None):
    """Ein BSSA-Lauf. progress(start, n, T, f, x) → False bricht ab."""
    def cb(n, T, fbest, xbest):
        if progress is None:
            return True
        return progress(start, n, T, fbest, xbest)

    res = minimize(search.objective, x_start, bssa_settings, cb)
    return {'start': start, 'cycle': cycle, 'x': res.x, 'f': float(res.f),
            'n_evals': res.n_evals, 'history': res.history}


def _start_task(task):
    """Worker-Aufgabe (Prozess-Pool): ein BSSA-Lauf mit Fortschritt/Abbruch über den Pool."""
    search, x_start, bssa_settings, start, cycle = task

    def progress(k, n, T, f, x):
        parallel.report_progress((k, n, T, f, np.asarray(x).tolist()))
        return not parallel.cancel_requested()

    try:
        return _run_start(search, x_start, bssa_settings, start, cycle, progress)
    except BSSACancelled:
        return {'start': start, 'cancelled': True}


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
    fixed = model.default_fixed() if settings.fixed is None else list(settings.fixed)
    free = [p.name for p in model.params if p.name not in fixed]
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
    starts: List[dict] = []
    rng_starts = np.random.default_rng(int(settings.bssa.seed) + 7919)

    n_starts = model.default_starts if settings.n_starts is None else settings.n_starts
    n_workers_used = 1
    for cycle in range(max(1, settings.lambda_cycles) if free else 0):
        search = _Search(q, I, s, ift_settings, smearing, model.key, values, free, lo, hi,
                         lam_rel)
        n_runs = max(1, int(n_starts)) if cycle == 0 else 1
        tasks = []
        for k in range(n_runs):
            if cycle == 0:
                seed = int(settings.bssa.seed) + 1000 * k
                x_start = to_x(values) if k == 0 else rng_starts.random(len(free))
            else:
                seed = int(settings.bssa.seed) + cycle
                x_start = to_x(values)
            tasks.append((search, x_start, replace(settings.bssa, seed=seed), k, cycle))

        workers = parallel.default_workers() if settings.n_workers is None \
            else max(0, int(settings.n_workers))
        n_workers_used = max(n_workers_used, min(workers, n_runs))
        base = n_evals
        if workers >= 1:
            # Parallel: Fortschritt aggregiert (Summe der Auswertungen, bestes MD)
            evals_per_start, best_seen = {}, [np.inf, None]

            def on_item(item, cycle=cycle, base=base):
                k, n, T, f, x = item
                evals_per_start[k] = n
                if f < best_seen[0]:
                    best_seen[:] = [f, x]
                if progress is None:
                    return True
                x_best = best_seen[1] if best_seen[1] is not None else x
                return progress(base + sum(evals_per_start.values()), T, best_seen[0],
                                search.to_vals(np.asarray(x_best)), cycle)

            try:
                results = parallel.get_pool(workers).run(_start_task, tasks, on_item)
            except parallel.TasksCancelled:
                raise BSSACancelled()
        else:
            results = []
            for task in tasks:
                done = n_evals + sum(r['n_evals'] for r in results)

                def on_step(k, n, T, f, x, cycle=cycle, done=done):
                    if progress is None:
                        return True
                    return progress(done + n, T, f, search.to_vals(x), cycle)

                results.append(_run_start(*task, progress=on_step))
        if any(r.get('cancelled') for r in results):
            raise BSSACancelled()

        # Auswertung in Startreihenfolge (identisch für seriell und parallel)
        best = None
        for r, task in zip(results, tasks):
            k = r['start']
            hist = [{'cycle': cycle, 'start': k, 'evals': n_evals + h['evals'], 'T': h['T'],
                     'md': h['f_best'], 'params': search.to_vals(np.array(h['x_best']))}
                    for h in r['history']]
            n_evals += r['n_evals']
            if cycle == 0:
                starts.append({'start': k, 'seed': task[2].seed,
                               'x_start': np.asarray(task[1]).tolist(),
                               'params': search.to_vals(r['x']), 'md': r['f'],
                               'n_evals': r['n_evals']})
            if best is None or r['f'] < best[0]['f']:
                best = (r, hist)
        history.extend(best[1])
        values = search.to_vals(best[0]['x'])
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
        model_info=model.derived(values), starts=starts, n_workers=n_workers_used,
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
