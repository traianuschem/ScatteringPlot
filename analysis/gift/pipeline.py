"""
Gesamtablauf einer IFT-Analyse mit lückenloser Provenance:

    q-Bereich wählen → σ prüfen/schätzen → IFT → Diagnose → Export (+ Sidecar)

GUI-frei; der Dialog ruft `run_ift_analysis()` und `export_ift_results()` auf.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import __version__ as MODULE_VERSION
from .ift import IFTSettings, IFTSolution, run_ift, estimate_sigma
from .diagnostics import (diagnose_ift, guinier_rg, worst_level, Flag, SIGMA_MEASURED,
                          SIGMA_ESTIMATED, SIGMA_RELATIVE)
from .provenance import ProvenanceRecord, default_agent, compute_sha256
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

    def to_kwargs(self):
        return dict(mode=self.mode, n_sigma=self.n_sigma, window=self.window,
                    min_run=self.min_run, q_min=self.q_min, q_max=self.q_max)


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
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def worst_level(self):
        return worst_level(self.flags)


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
                     sigma_relative: Optional[float] = None) -> IFTAnalysis:
    """Komplette IFT-Analyse eines Datensatzes.

    Args:
        q, intensity, sigma: vollständige Messdaten (σ=None → wird geschätzt)
        settings: IFT-Einstellungen (Dmax ist Pflicht)
        q_range: Auswahl des Fitbereichs (Standard: voller Bereich)
        source_file: Pfad der Datendatei (für Hash und Provenance)
        source_metadata: z. B. Spaltenzuordnung, Datensatzname
        sigma_relative: nur ohne σ — nimmt σ = sigma_relative·|I| an, statt σ aus dem
            Rauschen zu schätzen (sinnvoll für rauschfreie Simulationen)
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

    # 3) IFT
    solution = run_ift(q[mask], I[mask], sigma_arr[mask], settings)
    guinier = guinier_rg(q[mask], I[mask], sigma_arr[mask])
    flags = diagnose_ift(solution, selection, guinier=guinier, sigma_source=sigma_source,
                         sigma_relative=sigma_relative)
    record.add_activity(
        "Indirekte Fourier-Transformation (Glatter 1977)", "ift",
        parameters={**settings.to_dict(), 'basis': 'clamped cubic B-splines',
                    'lambda_selection': 'inflexion point (log N_c vs. log λ)',
                    'smearing': 'pinhole'},
        results_summary={
            'lambda_rel': solution.lam_rel, 'lambda_abs': solution.lam,
            'lambda_manual': solution.lam_manual,
            'inflexion_found': bool(solution.scan.inflexion_found),
            'md': solution.md, 'chi2': solution.chi2,
            'rg_nm': solution.rg, 'rg_err_nm': solution.rg_err,
            'i0': solution.i0, 'i0_err': solution.i0_err,
            'background': solution.background, 'background_err': solution.background_err,
            'rg_guinier_nm': guinier[0] if guinier else None,
            'guinier_points': guinier[2] if guinier else None,
        })
    record.set_flags(flags)
    record.set_reproducibility(deterministic=True, random_seed=None,
                               note="IFT ist deterministisch (keine Zufallszahlen).")

    return IFTAnalysis(solution=solution, selection=selection, flags=flags, guinier=guinier,
                       sigma_estimated=sigma_estimated, record=record,
                       sigma_source=sigma_source,
                       sigma_relative=sigma_relative if sigma_source == SIGMA_RELATIVE else None,
                       source_file=source_file)


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
        f"lambda_rel = {s.lam_rel:.4g} ({'manuell' if s.lam_manual else 'Wendepunkt'})",
        f"# q-Bereich: {analysis.selection.q_min:.6g} - {analysis.selection.q_max:.6g} nm^-1 "
        f"({analysis.selection.mode})",
        f"# Rg = {s.rg:.6g} +- {s.rg_err:.3g} nm, I(0) = {s.i0:.6g} +- {s.i0_err:.3g}, "
        f"MD = {s.md:.4g}",
        f"# Flags: " + ", ".join(f"{f.code}={f.level}" for f in analysis.flags),
        "# " + "\t".join(columns),
    ]
    return "\n".join(lines)


def result_paths(source_file, out_dir=None) -> Dict[str, Path]:
    """Standard-Dateinamen im Unterordner GIFT/ neben der Datendatei."""
    source_file = Path(source_file)
    out_dir = Path(out_dir) if out_dir else source_file.parent / RESULT_SUBDIR
    stem = source_file.stem
    return {
        'pr': out_dir / f"{stem}_GIFT_pr.dat",
        'fit': out_dir / f"{stem}_GIFT_fit-PDDF.dat",
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
    rec = analysis.record

    rec.add_activity("Export", "export",
                     parameters={'out_dir': paths['pr'].parent, 'write_w3c': write_w3c})

    np.savetxt(paths['pr'], np.column_stack([s.r, s.pr, s.pr_err]), fmt='%.8e',
               delimiter='\t', comments='',
               header=_header(analysis, "p(r) aus IFT (Glatter 1977)",
                              ['r / nm', 'p(r)', 'sigma_p(r)']))
    rec.add_output('pr', paths['pr'].name, paths['pr'],
                   extra_fields={'columns': ['r_nm', 'p_r', 'sigma_p_r']})

    np.savetxt(paths['fit'], np.column_stack([s.q, s.i_fit, s.i_fit_err]), fmt='%.8e',
               delimiter='\t', comments='',
               header=_header(analysis, "IFT-Fit I(q) im Fitbereich",
                              ['q / nm^-1', 'I_fit', 'sigma_I_fit']))
    rec.add_output('fit', paths['fit'].name, paths['fit'],
                   extra_fields={'columns': ['q_nm-1', 'I_fit', 'sigma_I_fit']})

    written = {'pr': paths['pr'], 'fit': paths['fit']}
    if write_w3c:
        rec.export_prov_json_to_file(paths['prov_w3c'])
        rec.add_output('provenance_prov_json', paths['prov_w3c'].name, paths['prov_w3c'])
        written['prov_w3c'] = paths['prov_w3c']
    rec.export_to_file(paths['prov'])
    written['prov'] = paths['prov']
    return written
