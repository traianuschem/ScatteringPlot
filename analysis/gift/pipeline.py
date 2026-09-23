"""
Gesamtablauf einer IFT-Analyse mit lückenloser Provenance:

    q-Bereich wählen → σ prüfen/schätzen → IFT/GIFT → Diagnose → [DREAM] → Export (+ Sidecar)

GUI-frei; der Dialog ruft `run_ift_analysis()` und `export_ift_results()` auf.
"""

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import __version__ as MODULE_VERSION
from .ift import IFTSettings, IFTSolution, run_ift, estimate_sigma
from .diagnostics import (diagnose_ift, guinier_rg, worst_level, Flag, SIGMA_MEASURED,
                          SIGMA_ESTIMATED, SIGMA_RELATIVE)
from .diagnostics import diagnose_gift
from .gift import GIFTSettings, GIFTResult, run_gift
from .structure_factors import get_model
from .provenance import ProvenanceRecord, default_agent, compute_sha256
from .uncertainty import UncertaintySettings, UncertaintyResult, run_uncertainty, QUANTILES
from .explorer import solution_metrics
from ..significance import select_q_range, QRANGE_FULL

RESULT_SUBDIR = 'GIFT'
REPO_DIR = Path(__file__).resolve().parents[2]


@dataclass
class QRangeSettings:
    """Einstellungen für den q-Fitbereich (siehe analysis.significance.select_q_range)."""
    mode: str = QRANGE_FULL
    n_sigma: float = 2.0
    window: int = 9
    min_run: Optional[int] = None
    q_min: Optional[float] = None
    q_max: Optional[float] = None
    # Artefakte am Kurvenanfang automatisch ausschließen (v7.13); nur ohne manuelles q_min
    auto_qmin: bool = True

    def to_kwargs(self):
        return dict(mode=self.mode, n_sigma=self.n_sigma, window=self.window,
                    min_run=self.min_run, q_min=self.q_min, q_max=self.q_max,
                    auto_qmin=self.auto_qmin)


@dataclass
class IFTAnalysis:
    """Ergebnis inkl. Diagnose und Provenance."""
    solution: IFTSolution
    selection: Any
    flags: List[Flag]
    guinier: Optional[tuple]
    sigma_estimated: bool
    record: ProvenanceRecord
    sigma_source: str = SIGMA_MEASURED
    sigma_relative: Optional[float] = None
    source_file: Optional[Path] = None
    gift: Optional[GIFTResult] = None
    uncertainty: Optional[UncertaintyResult] = None       # DREAM (auf Knopfdruck)
    metrics: Dict[str, float] = field(default_factory=dict)   # Kennzahlen (explorer.py)
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_flags(self) -> List[Flag]:
        return self.flags + (self.uncertainty.flags if self.uncertainty is not None else [])

    @property
    def worst_level(self):
        return worst_level(self.all_flags)


def _software_version():
    try:
        from core.version import __app_name__, __version__
        return __app_name__, __version__
    except ImportError:
        return "ScatterForge Plot", "unknown"


def relative_sigma(intensity, fraction):
    """σ = fraction·|I| mit Untergrenze (für I ≈ 0), z. B. für simulierte Daten."""
    I = np.abs(np.asarray(intensity, dtype=float))
    floor = 1e-6 * max(float(np.median(I)), np.finfo(float).tiny)
    return fraction * np.maximum(I, floor)


def run_ift_analysis(q, intensity, sigma=None, settings: IFTSettings = None,
                     q_range: QRangeSettings = None, source_file=None,
                     source_metadata: Optional[Dict[str, Any]] = None,
                     sigma_relative: Optional[float] = None,
                     gift_settings: Optional[GIFTSettings] = None,
                     progress=None) -> IFTAnalysis:
    """Komplette IFT-Analyse eines Datensatzes.

    Args:
        q, intensity, sigma: vollständige Messdaten (σ=None → wird geschätzt)
        settings: IFT-Einstellungen (Dmax ist Pflicht)
        q_range: Auswahl des Fitbereichs (Standard: voller Bereich)
        source_file: Pfad der Datendatei (für Hash und Provenance)
        source_metadata: z. B. Spaltenzuordnung, Datensatzname
        sigma_relative: nur ohne σ — nimmt σ = sigma_relative·|I| an, statt σ aus dem
            Rauschen zu schätzen (sinnvoll für rauschfreie Simulationen)
        gift_settings: GIFT statt IFT (Strukturfaktor-Modell ≠ 'none')
        progress: Fortschritts-Callback der BSSA-Suche (siehe gift.run_gift)
    """
    if settings is None:
        raise ValueError("IFTSettings mit Dmax erforderlich")
    q_range = q_range or QRangeSettings()
    q = np.asarray(q, dtype=float)
    I = np.asarray(intensity, dtype=float)
    order = np.argsort(q)
    q, I = q[order], I[order]
    sigma_arr = None if sigma is None else np.asarray(sigma, dtype=float)[order]

    app_name, app_version = _software_version()
    record = ProvenanceRecord(default_agent(app_name, app_version, MODULE_VERSION, REPO_DIR))

    # 1) Datenquelle
    meta = dict(source_metadata or {})
    sigma_valid = sigma_arr is not None and np.all(np.isfinite(sigma_arr)) \
        and np.all(sigma_arr > 0)
    if sigma_valid:
        sigma_source = SIGMA_MEASURED
    elif sigma_relative is not None:
        sigma_source = SIGMA_RELATIVE
    else:
        sigma_source = SIGMA_ESTIMATED
    meta.update({'n_points': int(len(q)), 'q_unit': 'nm^-1', 'r_unit': 'nm',
                 'sigma_source': sigma_source})
    if source_file is not None:
        source_file = Path(source_file)
        record.set_input_folder(source_file.parent)
        record.add_input_entity(source_file, metadata=meta)
    record.add_activity("Daten laden", "data_loading", parameters=meta)

    # 2) Vorverarbeitung: σ und q-Bereich
    sigma_estimated = sigma_source != SIGMA_MEASURED
    if sigma_source == SIGMA_RELATIVE:
        sigma_arr = relative_sigma(I, sigma_relative)
    elif sigma_source == SIGMA_ESTIMATED:
        sigma_arr = estimate_sigma(q, I)
    selection = select_q_range(q, I, None if sigma_estimated else sigma_arr,
                               **q_range.to_kwargs())
    mask = selection.mask(q)
    record.add_activity("q-Bereich und Fehler", "preprocessing",
                        parameters={'q_range': q_range.__dict__,
                                    'sigma_source': sigma_source,
                                    'sigma_estimated': sigma_estimated,
                                    'sigma_estimator': ('savgol_mad' if sigma_source ==
                                                        SIGMA_ESTIMATED else None),
                                    'sigma_relative': (sigma_relative if sigma_source ==
                                                       SIGMA_RELATIVE else None)},
                        results_summary=selection.to_dict())

    # 3) GIFT (optional): Strukturfaktor-Parameter per BSSA
    gift = None
    model_key = 'none'
    if gift_settings is not None and gift_settings.model != 'none':
        model = get_model(gift_settings.model)
        model_key = model.key
        gift = run_gift(q[mask], I[mask], sigma_arr[mask], settings, gift_settings,
                        progress=progress)
        record.add_activity(
            "GIFT: Strukturfaktor per BSSA (Bergmann et al. 2000)", "gift_bssa",
            parameters={**gift_settings.to_dict(), 'model_reference': model.reference,
                        'lower_effective': gift.lower, 'upper_effective': gift.upper,
                        'free': gift.free},
            results_summary={'params': gift.params, 'param_errors': gift.param_errors,
                             'param_error_method': 'MD curvature (approximate)',
                             'md': gift.md, 'md_without_structure_factor': gift.md_without_sq,
                             'n_evals': gift.n_evals, 'lambda_history': gift.lambda_history,
                             'lambda_converged': gift.lambda_converged,
                             'bssa_steps': len(gift.history),
                             'model_info': gift.model_info,
                             'multistart': gift.starts, 'n_workers': gift.n_workers})
        solution = gift.solution
    else:
        solution = run_ift(q[mask], I[mask], sigma_arr[mask], settings)

    # 4) IFT-Ergebnis und Diagnose
    guinier = guinier_rg(q[mask], I[mask], sigma_arr[mask])
    metrics = solution_metrics(solution)
    flags = diagnose_ift(solution, selection, guinier=guinier, sigma_source=sigma_source,
                         sigma_relative=sigma_relative, metrics=metrics)
    if gift is not None:
        flags += diagnose_gift(gift, get_model(model_key))
    record.add_activity(
        "Indirekte Fourier-Transformation (Glatter 1977)"
        + (f" mit S(q) = {model_key}" if gift is not None else ""), "ift",
        parameters={**settings.to_dict(), 'basis': 'clamped cubic B-splines',
                    'lambda_selection': 'inflexion point (log N_c vs. log λ)',
                    'smearing': 'pinhole', 'structure_factor_model': model_key},
        results_summary={
            'lambda_rel': solution.lam_rel, 'lambda_abs': solution.lam,
            'lambda_manual': solution.lam_manual,
            'lambda_method': solution.scan.method,
            'lambda_rel_scan_min': float(solution.scan.lam_rel[0]),
            'inflexion_found': bool(solution.scan.inflexion_found),
            'lambda_rel_inflexion': float(solution.scan.lam_rel[solution.scan.index_inflexion]),
            'lambda_rel_evidence': float(solution.scan.lam_rel[solution.scan.index_evidence]),
            'metrics': metrics,
            'md': solution.md, 'chi2': solution.chi2,
            'rg_nm': solution.rg, 'rg_err_nm': solution.rg_err,
            'i0': solution.i0, 'i0_err': solution.i0_err,
            'background': solution.background, 'background_err': solution.background_err,
            'rg_guinier_nm': guinier[0] if guinier else None,
            'guinier_points': guinier[2] if guinier else None,
        })
    record.set_flags(flags)
    if gift is None:
        record.set_reproducibility(deterministic=True, random_seed=None,
                                   note="IFT ist deterministisch (keine Zufallszahlen).")
    else:
        record.set_reproducibility(
            deterministic=True, random_seed=int(gift_settings.bssa.seed),
            seed_per_cycle="seed + Zyklusnummer", seed_per_start="seed + 1000·Start",
            start_points="Start 0: Startwerte; weitere: default_rng(seed + 7919)",
            n_starts=len(gift.starts), n_workers=gift.n_workers,
            workers_note="Ergebnis unabhängig von der Worker-Zahl (Seeds je Start)",
            rng="numpy.random.default_rng (PCG64)",
            note="BSSA ist bei gleichem Seed, gleichen Daten und gleichen Einstellungen "
                 "bitgleich reproduzierbar.")

    extras = {'source_metadata': meta, 'q_all': q, 'I_all': I, 'sigma_all': sigma_arr}
    return IFTAnalysis(extras=extras,
                       solution=solution, selection=selection, flags=flags, guinier=guinier,
                       sigma_estimated=sigma_estimated, record=record,
                       sigma_source=sigma_source,
                       sigma_relative=sigma_relative if sigma_source == SIGMA_RELATIVE else None,
                       source_file=source_file, gift=gift, metrics=metrics)


def run_uncertainty_analysis(analysis: IFTAnalysis, settings: UncertaintySettings,
                             progress=None) -> UncertaintyResult:
    """DREAM-Analyse (Plan §2.3) einer fertigen IFT/GIFT-Analyse; das Ergebnis hängt danach
    an `analysis.uncertainty` und wird mit exportiert."""
    result = run_uncertainty(analysis, settings, progress=progress)
    analysis.uncertainty = result
    return result


def _add_uncertainty_provenance(rec: ProvenanceRecord, u: UncertaintyResult):
    ds = u.settings.dream
    rec.add_activity(
        "Latin-Hypercube-Screening der Posterior-Landschaft", "screening",
        parameters={'n': int(len(u.screening.log_p)), 'seed_entropy': u.screening.seed_entropy,
                    'prior': u.space.to_dict()},
        results_summary=u.screening.summary(u.names))
    rec.add_activity(
        "DREAM(ZS): Posterior der Parameter (ter Braak & Vrugt 2008; marginale Likelihood "
        "nach Hansen 2000)", "dream",
        parameters={**u.settings.to_dict(), 'prior': u.space.to_dict(),
                    'likelihood': 'marginal (spline coefficients integrated out analytically)',
                    'model': u.model_key, 'fixed_values': u.fixed_values,
                    'n_workers_used': u.n_workers},
        results_summary=u.results_summary())
    rec.set_reproducibility(
        dream_seed=int(ds.seed), dream_rng="numpy.random.default_rng(seed) (PCG64)",
        screening_seed_entropy=u.screening.seed_entropy,
        prediction_seed_entropy=[int(ds.seed), 2],
        dream_chunk=int(u.settings.chunk), dream_n_workers=int(u.n_workers),
        dream_note="Ketten bitgleich für jede Worker-Zahl ≥ 1 (feste Blockgröße, einfädiges "
                   "BLAS im Pool); 0 Worker = Hauptprozess (Diagnose, nicht bitgleich).")


def _save_uncertainty(u: UncertaintyResult, paths, analysis, rec):
    d = u.dream
    b = u.bands
    np.savez_compressed(
        paths['dream'], names=np.array(u.names), labels=np.array([u.labels[n] for n in u.names]),
        lower=u.space.lower, upper=u.space.upper, chains=d.chains, log_p=d.log_p,
        accepted=d.accepted, burn_in=d.burn_in, r_hat=d.r_hat,
        r_hat_history=np.array([[g, *r] for g, r in d.r_hat_history]),
        screening_samples=u.screening.samples, screening_log_p=u.screening.log_p,
        quantiles=np.array(QUANTILES), r=b['r'], q=b['q'], pr_band=b['pr'],
        i_fit_band=b['i_fit'], pq_band=b['pq'], sq_band=b['sq'],
        rg_samples=u.rg_samples, i0_samples=u.i0_samples,
        record_id=np.array(rec.record_id))
    rec.add_output('dream_chains', paths['dream'].name, paths['dream'],
                   extra_fields={'format': 'numpy npz'})
    pr = b['pr']
    np.savetxt(paths['pr_band'], np.column_stack([b['r'], pr[2], pr[0], pr[1], pr[3], pr[4]]),
               fmt='%.8e', delimiter='\t', comments='', encoding='utf-8',
               header=_header(analysis, f"p(r)-Posterior-Band (DREAM, {b['n_draws']} Ziehungen)",
                              ['r / nm', 'median', 'q2.5', 'q16', 'q84', 'q97.5']))
    rec.add_output('pr_band', paths['pr_band'].name, paths['pr_band'],
                   extra_fields={'columns': ['r_nm', 'median', 'q2.5', 'q16', 'q84', 'q97.5']})


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _header(analysis: IFTAnalysis, title: str, columns: List[str]) -> str:
    s = analysis.solution
    st = s.settings
    lines = [
        f"# {title}",
        f"# record_id: {analysis.record.record_id}",
        f"# erzeugt von: {analysis.record.agent.get('software')} "
        f"{analysis.record.agent.get('version')} / analysis.gift {MODULE_VERSION}",
        f"# Quelle: {analysis.source_file.name if analysis.source_file else '-'}",
        f"# Dmax = {st.dmax:g} nm, N = {st.n_splines}, K = {st.k_type}, "
        f"lambda_rel = {s.lam_rel:.4g} ({_lambda_label(s)})",
        f"# q-Bereich: {analysis.selection.q_min:.6g} - {analysis.selection.q_max:.6g} nm^-1 "
        f"({analysis.selection.mode})",
        f"# Rg = {s.rg:.6g} +- {s.rg_err:.3g} nm, I(0) = {s.i0:.6g} +- {s.i0_err:.3g}, "
        f"MD = {s.md:.4g}",
        *([f"# Kennzahlen: Oszillation = {analysis.metrics['oscillation']:.3g}, "
           f"Positive Fraction = {analysis.metrics['positive_fraction']:.3g}, "
           f"1sigma-Positive = {analysis.metrics['positive_1sigma']:.3g}, "
           f"Maxima = {analysis.metrics['n_peaks']:.0f}, N_g = {analysis.metrics['n_good']:.3g}, "
           f"log-Evidenz = {analysis.metrics['log_evidence']:.6g}"]
          if analysis.metrics else []),
        *([_gift_header_line(analysis)] if analysis.gift is not None else []),
        *([_dream_header_line(analysis)] if analysis.uncertainty is not None else []),
        f"# Flags: " + ", ".join(f"{f.code}={f.level}" for f in analysis.all_flags),
        "# " + "\t".join(columns),
    ]
    return "\n".join(lines)


def _lambda_label(s) -> str:
    if s.lam_manual:
        return 'manuell'
    return 'Evidenz-Maximum' if s.scan.method == 'evidence' else 'Wendepunkt'


def _gift_header_line(analysis: IFTAnalysis) -> str:
    g = analysis.gift
    params = ", ".join(f"{k} = {v:.6g} +- {g.param_errors.get(k, float('nan')):.3g}"
                       for k, v in g.params.items())
    return f"# GIFT: S(q) = {g.model_key}; {params}; MD ohne S(q) = {g.md_without_sq:.4g}"


def _dream_header_line(analysis: IFTAnalysis) -> str:
    u = analysis.uncertainty
    parts = [f"{n} = {u.summary[n]['median']:.6g} [{u.summary[n]['q2.5']:.4g}, "
             f"{u.summary[n]['q97.5']:.4g}]" for n in u.names]
    return ("# DREAM (Median [95 %]): " + "; ".join(parts)
            + f"; Rg = {u.rg['median']:.6g} [{u.rg['q2.5']:.4g}, {u.rg['q97.5']:.4g}] nm; "
            f"R-hat max = {float(np.max(u.dream.r_hat)):.3f}")


def result_paths(source_file, out_dir=None) -> Dict[str, Path]:
    """Standard-Dateinamen im Unterordner GIFT/ neben der Datendatei."""
    source_file = Path(source_file)
    out_dir = Path(out_dir) if out_dir else source_file.parent / RESULT_SUBDIR
    stem = source_file.stem
    return {
        'pr': out_dir / f"{stem}_GIFT_pr.dat",
        'fit': out_dir / f"{stem}_GIFT_fit-PDDF.dat",
        'data': out_dir / f"{stem}_GIFT_data.dat",
        'sq': out_dir / f"{stem}_GIFT_Sq.dat",
        'pq': out_dir / f"{stem}_GIFT_Pq.dat",
        'dream': out_dir / f"{stem}_GIFT_dream.npz",
        'pr_band': out_dir / f"{stem}_GIFT_pr_band.dat",
        'prov': out_dir / f"{stem}_GIFT_prov.json",
        'prov_w3c': out_dir / f"{stem}_GIFT.prov-w3c.json",
    }


def export_ift_results(analysis: IFTAnalysis, out_dir=None, source_file=None,
                       write_w3c=True) -> Dict[str, Path]:
    """Schreibt p(r), Fit und den Provenance-Sidecar.

    Returns:
        Dict der geschriebenen Pfade ('pr', 'fit', 'prov', ggf. 'prov_w3c').
    """
    source = source_file or analysis.source_file
    if source is None:
        raise ValueError("Ohne Quelldatei muss ein Zielpfad (source_file) angegeben werden")
    paths = result_paths(source, out_dir)
    paths['pr'].parent.mkdir(parents=True, exist_ok=True)
    s = analysis.solution
    # Der Export arbeitet auf einer Kopie des Records: Die Analyse bleibt unverändert und
    # kann erneut (z. B. in einen anderen Ordner) exportiert werden.
    rec = copy.deepcopy(analysis.record)
    analysis.extras['exported_record'] = rec

    if analysis.uncertainty is not None:
        _add_uncertainty_provenance(rec, analysis.uncertainty)
        rec.set_flags(analysis.all_flags)
    rec.add_activity("Export", "export",
                     parameters={'out_dir': paths['pr'].parent, 'write_w3c': write_w3c})

    np.savetxt(paths['pr'], np.column_stack([s.r, s.pr, s.pr_err]), fmt='%.8e',
               delimiter='\t', comments='', encoding='utf-8',
               header=_header(analysis, "p(r) aus IFT (Glatter 1977)",
                              ['r / nm', 'p(r)', 'sigma_p(r)']))
    rec.add_output('pr', paths['pr'].name, paths['pr'],
                   extra_fields={'columns': ['r_nm', 'p_r', 'sigma_p_r']})

    np.savetxt(paths['fit'], np.column_stack([s.q, s.i_fit, s.i_fit_err]), fmt='%.8e',
               delimiter='\t', comments='', encoding='utf-8',
               header=_header(analysis, "IFT-Fit I(q) im Fitbereich",
                              ['q / nm^-1', 'I_fit', 'sigma_I_fit']))
    rec.add_output('fit', paths['fit'].name, paths['fit'],
                   extra_fields={'columns': ['q_nm-1', 'I_fit', 'sigma_I_fit']})

    written = {'pr': paths['pr'], 'fit': paths['fit']}
    meta = analysis.extras.get('source_metadata', {})
    if float(meta.get('q_conversion_factor', 1.0)) != 1.0:
        # q wurde umgerechnet (z. B. Å⁻¹ → nm⁻¹): verwendete Eingangsdaten mitschreiben,
        # damit Daten und Fit in derselben Einheit geplottet werden können
        x = analysis.extras
        np.savetxt(paths['data'], np.column_stack([x['q_all'], x['I_all'], x['sigma_all']]),
                   fmt='%.8e', delimiter='\t', comments='', encoding='utf-8',
                   header=_header(analysis, f"Eingangsdaten nach q-Umrechnung "
                                            f"(Faktor {meta['q_conversion_factor']:g} → nm^-1)",
                                  ['q / nm^-1', 'I', 'sigma (verwendet)']))
        rec.add_output('input_converted', paths['data'].name, paths['data'],
                       extra_fields={'columns': ['q_nm-1', 'I', 'sigma_used']})
        written['data'] = paths['data']
    if analysis.gift is not None:
        g = analysis.gift
        np.savetxt(paths['sq'], np.column_stack([s.q, g.structure_factor]), fmt='%.8e',
                   delimiter='\t', comments='', encoding='utf-8',
                   header=_header(analysis, f"Strukturfaktor S(q) ({g.model_key})",
                                  ['q / nm^-1', 'S(q)']))
        rec.add_output('structure_factor', paths['sq'].name, paths['sq'],
                       extra_fields={'columns': ['q_nm-1', 'S_q']})
        pq = s.extras['form_factor']
        pq_err = s.extras['form_factor_err']
        np.savetxt(paths['pq'], np.column_stack([s.q, pq, pq_err]), fmt='%.8e',
                   delimiter='\t', comments='', encoding='utf-8',
                   header=_header(analysis, "Formfaktor P(q) = I_fit/S(q) (ohne Untergrund)",
                                  ['q / nm^-1', 'P(q)', 'sigma_P(q)']))
        rec.add_output('form_factor', paths['pq'].name, paths['pq'],
                       extra_fields={'columns': ['q_nm-1', 'P_q', 'sigma_P_q']})
        written.update({'sq': paths['sq'], 'pq': paths['pq']})
    if analysis.uncertainty is not None:
        _save_uncertainty(analysis.uncertainty, paths, analysis, rec)
        written.update({'dream': paths['dream'], 'pr_band': paths['pr_band']})
    if write_w3c:
        rec.export_prov_json_to_file(paths['prov_w3c'])
        rec.add_output('provenance_prov_json', paths['prov_w3c'].name, paths['prov_w3c'])
        written['prov_w3c'] = paths['prov_w3c']
    rec.export_to_file(paths['prov'])
    written['prov'] = paths['prov']
    return written
