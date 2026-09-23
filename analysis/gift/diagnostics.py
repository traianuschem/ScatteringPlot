"""
Plausibilitätsprüfungen (Flags) für IFT/GIFT-Ergebnisse.

Jedes Flag hat einen stabilen `code` (für i18n in der GUI und für die Provenance),
eine Stufe ('ok', 'info', 'warning'), den zugehörigen Messwert und eine deutsche
Klartextmeldung.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional

import numpy as np

LEVEL_OK = 'ok'
LEVEL_INFO = 'info'
LEVEL_WARNING = 'warning'


@dataclass
class Flag:
    """Ergebnis einer Prüfung.

    `code` + `variant` bilden den i18n-Schlüssel `gift.flag.<code>.<variant>`; `params`
    enthält die bereits formatierten Platzhalterwerte dafür. `message` ist die deutsche
    Klartextfassung (für Provenance und Logs).
    """
    code: str
    level: str
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    variant: str = 'ok'
    params: Dict[str, str] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Einzelprüfungen (auch einzeln nutzbar, z. B. für die Live-Anzeige im Dialog)
# ---------------------------------------------------------------------------

def dmax_qmin_ratio(dmax, q_min):
    """Verhältnis Dmax·q_min/π (≤ 1: Dmax ist durch den Messbereich abgedeckt)."""
    return float(dmax) * float(q_min) / np.pi


def check_dmax_qmin(dmax, q_min):
    ratio = dmax_qmin_ratio(dmax, q_min)
    limit = np.pi / q_min
    if ratio > 1.0:
        return Flag('dmax_qmin', LEVEL_WARNING,
                    f"Dmax = {dmax:.3g} nm > π/q_min = {limit:.3g} nm "
                    f"(Dmax·q_min/π = {ratio:.2f}): Die größten Abstände sind durch den "
                    f"Messbereich nicht abgedeckt.", ratio, 1.0, 'exceeded',
                    {'dmax': f"{dmax:.3g}", 'limit': f"{limit:.3g}", 'ratio': f"{ratio:.2f}"})
    return Flag('dmax_qmin', LEVEL_OK,
                f"Dmax ≤ π/q_min = {limit:.3g} nm (Dmax·q_min/π = {ratio:.2f})", ratio, 1.0,
                'ok', {'limit': f"{limit:.3g}", 'ratio': f"{ratio:.2f}"})


def shannon_channels(dmax, q_min, q_max):
    """Anzahl der Shannon-Kanäle N_s = Dmax·(q_max − q_min)/π."""
    return float(dmax) * (float(q_max) - float(q_min)) / np.pi


def suggest_n_splines(dmax, q_min, q_max, n_min=20, n_max=200):
    """Empfohlene Spline-Anzahl: etwas mehr als die Zahl der Shannon-Kanäle.

    Die Regularisierung verhindert Überanpassung, eine zu grobe Basis dagegen kann die
    Information der Daten nicht darstellen (MD ≫ 1).
    """
    ns = shannon_channels(dmax, q_min, q_max)
    return int(np.clip(np.ceil(1.2 * ns) + 5, n_min, n_max))


def check_shannon(dmax, q_min, q_max, n_splines):
    ns = shannon_channels(dmax, q_min, q_max)
    suggest = suggest_n_splines(dmax, q_min, q_max)
    if ns < 3.0:
        return Flag('shannon', LEVEL_WARNING,
                    f"Nur {ns:.1f} Shannon-Kanäle im Fitbereich — sehr geringer "
                    f"Informationsgehalt.", ns, 3.0, 'few', {'ns': f"{ns:.1f}"})
    if n_splines < ns:
        return Flag('shannon', LEVEL_WARNING,
                    f"N = {n_splines} Splines < {ns:.1f} Shannon-Kanäle: Die Basis ist "
                    f"gröber als der Informationsgehalt der Daten (empfohlen: N ≥ {suggest}).",
                    ns, float(n_splines), 'coarse',
                    {'ns': f"{ns:.1f}", 'n': str(n_splines), 'suggest': str(suggest)})
    return Flag('shannon', LEVEL_OK, f"{ns:.1f} Shannon-Kanäle im Fitbereich", ns, 3.0,
                'ok', {'ns': f"{ns:.1f}"})


def check_q_range(selection):
    if selection is None:
        return None
    frac = selection.n_excluded / selection.n_total if selection.n_total else 0.0
    if frac > 0.5:
        return Flag('q_range', LEVEL_WARNING,
                    f"{selection.n_excluded} von {selection.n_total} Punkten "
                    f"({frac:.0%}) liegen außerhalb des Fitbereichs.", frac, 0.5, 'excluded',
                    {'excluded': str(selection.n_excluded), 'total': str(selection.n_total),
                     'frac': f"{frac:.0%}"})
    return Flag('q_range', LEVEL_OK,
                f"{selection.n_selected} von {selection.n_total} Punkten im Fitbereich "
                f"({selection.q_min:.4g}–{selection.q_max:.4g} nm⁻¹)", frac, 0.5, 'ok',
                {'selected': str(selection.n_selected), 'total': str(selection.n_total),
                 'q_min': f"{selection.q_min:.4g}", 'q_max': f"{selection.q_max:.4g}"})


def guinier_rg(q, intensity, sigma, qrg_max=1.3, min_points=5, max_iter=20):
    """Iterativer Guinier-Fit ln I = ln I0 − Rg²q²/3 im Bereich q·Rg ≤ qrg_max.

    Returns:
        (Rg, I0, n_points) oder None, wenn kein gültiger Guinier-Bereich existiert.
    """
    q = np.asarray(q, dtype=float)
    I = np.asarray(intensity, dtype=float)
    s = np.asarray(sigma, dtype=float)
    valid = I > 0
    q, I, s = q[valid], I[valid], s[valid]
    if len(q) < min_points:
        return None
    n = min_points
    rg = None
    for _ in range(max_iter):
        x = q[:n] ** 2
        y = np.log(I[:n])
        w = (I[:n] / s[:n]) ** 2
        coef = np.polyfit(x, y, 1, w=np.sqrt(w))
        slope, intercept = coef
        if slope >= 0:
            return None
        rg_new = float(np.sqrt(-3.0 * slope))
        n_new = int(np.count_nonzero(q * rg_new <= qrg_max))
        if n_new < min_points:
            return None
        if rg is not None and n_new == n and abs(rg_new - rg) < 1e-6 * rg:
            break
        rg, n = rg_new, n_new
    return rg, float(np.exp(intercept)), n


def check_fit_quality(md, sigma_estimated):
    """`sigma_estimated`: True, wenn σ nicht gemessen, sondern geschätzt/angenommen ist."""
    if sigma_estimated:
        return Flag('fit_quality', LEVEL_INFO,
                    f"MD = {md:.2f} (σ geschätzt — nur relativ aussagekräftig)", md, None,
                    'estimated', {'md': f"{md:.2f}"})
    if md > 2.0:
        return Flag('fit_quality', LEVEL_WARNING,
                    f"MD = {md:.2f} ≫ 1: Die Anpassung beschreibt die Daten nicht innerhalb "
                    f"der Fehler (Dmax zu klein, Untergrund, Wechselwirkung?).", md, 2.0,
                    'high', {'md': f"{md:.2f}"})
    if md < 0.5:
        return Flag('fit_quality', LEVEL_WARNING,
                    f"MD = {md:.2f} ≪ 1: Die Fehler σ sind vermutlich überschätzt.", md, 0.5,
                    'low', {'md': f"{md:.2f}"})
    return Flag('fit_quality', LEVEL_OK, f"MD = {md:.2f}", md, None, 'ok', {'md': f"{md:.2f}"})


SIGMA_MEASURED = 'measured'
SIGMA_ESTIMATED = 'estimated'
SIGMA_RELATIVE = 'relative'


def check_sigma(sigma_source, sigma_relative=None):
    """Hinweis, wenn σ nicht aus einer Fehlerspalte stammt.

    Aus Kompatibilitätsgründen wird auch ein bool akzeptiert (True = geschätzt).
    """
    if sigma_source is True:
        sigma_source = SIGMA_ESTIMATED
    if sigma_source == SIGMA_ESTIMATED:
        return Flag('sigma_estimated', LEVEL_WARNING,
                    "Keine Fehlerspalte: σ wurde aus den Daten geschätzt.", variant='estimated')
    if sigma_source == SIGMA_RELATIVE:
        pct = f"{100 * sigma_relative:g}"
        return Flag('sigma_estimated', LEVEL_INFO,
                    f"σ als {pct} % von |I| angenommen (z. B. simulierte Daten) — MD und "
                    f"Fehlerbänder sind nur relativ aussagekräftig.", sigma_relative, None,
                    'relative', {'pct': pct})
    return None


def check_inflexion(scan, lam_manual):
    if lam_manual:
        return Flag('lambda', LEVEL_INFO, "λ manuell vorgegeben (Wendepunkt nicht verwendet)",
                    variant='manual')
    if scan is not None and not scan.inflexion_found:
        return Flag('lambda', LEVEL_WARNING,
                    "Kein Wendepunkt in log N_c(λ) gefunden — nach Glatter ein Hinweis auf "
                    "Inkonsistenz zwischen Daten und Annahmen (Dmax, N, Untergrund).",
                    variant='not_found')
    return Flag('lambda', LEVEL_OK, "λ über Wendepunkt-Methode bestimmt")


def _significant(pr, pr_err, rel_floor=0.02):
    scale = np.max(np.abs(pr)) if len(pr) else 0.0
    return np.abs(pr) > np.maximum(2.0 * pr_err, rel_floor * scale)


def check_pr_end(r, pr, pr_err, dmax):
    """p(r) muss vor Dmax weich gegen 0 gehen; ein großer Wert kurz vor Dmax → Dmax zu klein."""
    pmax = np.max(pr)
    if pmax <= 0:
        return None
    tail = r >= 0.9 * dmax
    ratio = float(np.max(np.abs(pr[tail])) / pmax)
    if ratio > 0.1:
        return Flag('pr_end', LEVEL_WARNING,
                    f"p(r) ist kurz vor Dmax noch bei {ratio:.0%} des Maximums — Dmax ist "
                    f"vermutlich zu klein gewählt.", ratio, 0.1, 'high',
                    {'ratio': f"{ratio:.0%}"})
    return Flag('pr_end', LEVEL_OK, "p(r) läuft vor Dmax gegen 0", ratio, 0.1)


def check_pr_tail(r, pr, pr_err, dmax):
    """Lange, nicht-signifikante Nullregion vor Dmax → Dmax deutlich zu groß."""
    sig = _significant(pr, pr_err)
    if not sig.any():
        return None
    r_last = float(r[np.nonzero(sig)[0].max()])
    frac = 1.0 - r_last / dmax
    if frac > 0.2:
        return Flag('pr_tail', LEVEL_INFO,
                    f"p(r) ist ab r ≈ {r_last:.3g} nm nicht mehr signifikant von 0 "
                    f"verschieden ({frac:.0%} des Bereichs) — Dmax ist evtl. zu groß.",
                    r_last, 0.8 * dmax, 'long', {'r': f"{r_last:.3g}", 'frac': f"{frac:.0%}"})
    return Flag('pr_tail', LEVEL_OK, "Kein langer Null-Ausläufer vor Dmax", r_last)


def check_pr_negative(r, pr, pr_err):
    neg = (pr < 0) & _significant(pr, pr_err)
    if neg.any():
        depth = float(-np.min(pr[neg]) / np.max(np.abs(pr)))
        return Flag('pr_negative', LEVEL_WARNING,
                    f"p(r) ist signifikant negativ (bis {depth:.0%} des Maximums) — "
                    f"Untergrund, Inhomogenität oder nicht berücksichtigte Wechselwirkung "
                    f"(→ GIFT)?", depth, None, 'negative', {'depth': f"{depth:.0%}"})
    return Flag('pr_negative', LEVEL_OK, "Keine signifikant negativen p(r)-Werte")


def check_pr_oscillation(r, pr, pr_err):
    """Mehrfache signifikante Vorzeichenwechsel → typisch für i(r) mit Wechselwirkung [W99]."""
    sig = _significant(pr, pr_err)
    signs = np.sign(pr[sig])
    changes = int(np.count_nonzero(np.diff(signs) != 0))
    if changes >= 2:
        return Flag('pr_oscillation', LEVEL_INFO,
                    f"p(r) wechselt {changes}× signifikant das Vorzeichen — typisch für "
                    f"Wechselwirkung zwischen den Teilchen (→ GIFT mit Strukturfaktor).",
                    float(changes), 2.0, 'oscillating', {'n': str(changes)})
    return None


def check_rg_consistency(rg_ift, rg_guinier):
    if rg_guinier is None or not np.isfinite(rg_ift):
        return None
    dev = abs(rg_ift - rg_guinier) / rg_ift
    if dev > 0.1:
        return Flag('rg_consistency', LEVEL_INFO,
                    f"Rg(IFT) = {rg_ift:.3g} nm weicht um {dev:.0%} von Rg(Guinier) = "
                    f"{rg_guinier:.3g} nm ab.", dev, 0.1, 'deviation',
                    {'rg_ift': f"{rg_ift:.3g}", 'rg_guinier': f"{rg_guinier:.3g}",
                     'dev': f"{dev:.0%}"})
    return Flag('rg_consistency', LEVEL_OK,
                f"Rg(IFT) = {rg_ift:.3g} nm, Rg(Guinier) = {rg_guinier:.3g} nm", dev, 0.1,
                'ok', {'rg_ift': f"{rg_ift:.3g}", 'rg_guinier': f"{rg_guinier:.3g}"})


# ---------------------------------------------------------------------------
# Gesamtdiagnose
# ---------------------------------------------------------------------------

def diagnose_ift(solution, selection=None, sigma_estimated=False, guinier=None,
                 sigma_source=None, sigma_relative=None):
    """Alle Flags für eine IFT-Lösung (Reihenfolge = Anzeige-Reihenfolge)."""
    if sigma_source is None:
        sigma_source = SIGMA_ESTIMATED if sigma_estimated else SIGMA_MEASURED
    sigma_estimated = sigma_source != SIGMA_MEASURED
    st = solution.settings
    q_min, q_max = float(np.min(solution.q)), float(np.max(solution.q))
    rg_g = guinier[0] if guinier else None
    flags = [
        check_dmax_qmin(st.dmax, q_min),
        check_shannon(st.dmax, q_min, q_max, st.n_splines),
        check_q_range(selection),
        check_sigma(sigma_source, sigma_relative),
        check_inflexion(solution.scan, solution.lam_manual),
        check_fit_quality(solution.md, sigma_estimated),
        check_pr_end(solution.r, solution.pr, solution.pr_err, st.dmax),
        check_pr_tail(solution.r, solution.pr, solution.pr_err, st.dmax),
        check_pr_negative(solution.r, solution.pr, solution.pr_err),
        check_pr_oscillation(solution.r, solution.pr, solution.pr_err),
        check_rg_consistency(solution.rg, rg_g),
    ]
    return [f for f in flags if f is not None]


def diagnose_gift(result, model):
    """Zusätzliche Flags für eine GIFT-Rechnung [B00, W99]."""
    flags = []
    labels = {p.name: p.label for p in model.params}
    at_bound = []
    for name in result.free:
        rng = result.upper[name] - result.lower[name]
        v = result.params[name]
        if min(v - result.lower[name], result.upper[name] - v) < 0.01 * rng:
            at_bound.append(f"{labels[name]} = {v:.4g}")
    if at_bound:
        names = ', '.join(at_bound)
        flags.append(Flag('gift_bound', LEVEL_WARNING,
                          f"Parameter am Rand der erlaubten Grenzen ({names}) — Grenzen "
                          f"erweitern oder das Modell ist ungeeignet [B00].", None, None,
                          'at_bound', {'names': names}))
    elif result.free:
        flags.append(Flag('gift_bound', LEVEL_OK, "Alle freien Parameter innerhalb der Grenzen"))

    s_min = float(np.min(result.structure_factor))
    if s_min < 0:
        flags.append(Flag('gift_structure_factor', LEVEL_WARNING,
                          f"S(q) wird negativ (min {s_min:.3g}) — unphysikalisch.", s_min, 0.0,
                          'negative', {'min': f"{s_min:.3g}"}))

    if result.md_without_sq is not None and np.isfinite(result.md_without_sq):
        ratio = result.md_without_sq / max(result.md, np.finfo(float).tiny)
        params = {'md_ift': f"{result.md_without_sq:.3g}", 'md_gift': f"{result.md:.3g}"}
        if ratio < 1.2:
            flags.append(Flag('gift_improvement', LEVEL_INFO,
                              f"S(q) verbessert die Anpassung kaum (MD {result.md_without_sq:.3g} "
                              f"→ {result.md:.3g}) — Wechselwirkung evtl. vernachlässigbar.",
                              ratio, 1.2, 'small', params))
        else:
            flags.append(Flag('gift_improvement', LEVEL_OK,
                              f"MD ohne S(q) = {result.md_without_sq:.3g} → mit S(q) = "
                              f"{result.md:.3g}", ratio, 1.2, 'improved', params))

    if not result.lambda_converged:
        flags.append(Flag('gift_lambda', LEVEL_WARNING,
                          "λ hat sich zwischen den GIFT-Zyklen nicht stabilisiert — Ergebnis "
                          "prüfen (λ manuell setzen oder mehr Zyklen).", variant='not_converged'))

    undetermined = [labels[n] for n in result.free
                    if not np.isfinite(result.param_errors.get(n, np.nan))]
    if undetermined:
        names = ', '.join(undetermined)
        flags.append(Flag('gift_errors', LEVEL_INFO,
                          f"Fehler aus der MD-Krümmung nicht bestimmbar für {names} (flache "
                          f"oder nicht konvexe MD-Fläche).", None, None, 'undetermined',
                          {'names': names}))

    if model.apparent_parameters:
        flags.append(Flag('gift_apparent', LEVEL_INFO,
                          "S_ave-Parameter sind scheinbare Modellparameter mit begrenzter "
                          "physikalischer Bedeutung; das Ergebnis ist p(r) bzw. P(q) [W99].",
                          variant='apparent'))
    return flags


def worst_level(flags):
    order = {LEVEL_OK: 0, LEVEL_INFO: 1, LEVEL_WARNING: 2}
    return max((f.level for f in flags), key=lambda lv: order[lv], default=LEVEL_OK)
