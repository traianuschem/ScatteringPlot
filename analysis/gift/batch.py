"""
Serienauswertung (Batch) mehrerer Datensätze mit denselben Einstellungen (Phase 4,
bewusst rudimentär; Metadaten-Auslese folgt später).

Jeder Datensatz wird wie im Dialog ausgewertet (q-Bereich inkl. automatischem q_min,
IFT bzw. GIFT) und mit eigenem Provenance-Sidecar in seinen GIFT/-Ordner exportiert.
Optional wird Dmax (und N) je Datensatz vorgeschlagen (explorer.suggest_dmax) — sinnvoll,
wenn sich die Teilchengröße in der Serie ändert (z. B. Aggregation). Eine Übersichtstabelle
(CSV) verknüpft die Ergebnisse über die record_id.
"""

import csv
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

from .diagnostics import suggest_n_splines, LEVEL_WARNING
from .explorer import suggest_dmax
from .ift import IFTSettings
from .gift import GIFTSettings, BSSACancelled
from .pipeline import (run_ift_analysis, export_ift_results, QRangeSettings, IFTAnalysis,
                       relative_sigma)
from ..significance import select_q_range

DMAX_FIXED = 'fixed'
DMAX_SUGGEST = 'suggest'


class BatchCancelled(Exception):
    """Abbruch der Serie."""


@dataclass
class BatchItem:
    name: str
    source_file: Path
    q: np.ndarray
    intensity: np.ndarray
    sigma: Optional[np.ndarray]
    source_metadata: Dict = field(default_factory=dict)


@dataclass
class BatchEntry:
    item: BatchItem
    analysis: Optional[IFTAnalysis] = None
    paths: Dict[str, Path] = field(default_factory=dict)
    error: Optional[str] = None
    dmax_suggested: Optional[bool] = None
    runtime_s: float = 0.0


def _dmax_for(item, settings, q_range, sigma_relative, fallback):
    """Dmax/N-Vorschlag für einen Datensatz im Fitbereich (None → fallback)."""
    q, I = np.asarray(item.q, float), np.asarray(item.intensity, float)
    s = item.sigma
    if s is None:
        from .ift import estimate_sigma
        s = relative_sigma(I, sigma_relative) if sigma_relative else estimate_sigma(q, I)
    sel = select_q_range(q, I, item.sigma, **q_range.to_kwargs())
    m = sel.mask(q)
    dmax, _scan = suggest_dmax(q[m], I[m], np.asarray(s)[m], settings)
    if dmax is None:
        return fallback, settings.n_splines, False
    return dmax, suggest_n_splines(dmax, sel.q_min, sel.q_max), True


def run_batch(items: List[BatchItem], settings: IFTSettings, q_range: QRangeSettings,
              gift_settings: Optional[GIFTSettings] = None, sigma_relative=None,
              dmax_mode=DMAX_FIXED, export=True, write_w3c=True,
              progress: Optional[Callable] = None) -> List[BatchEntry]:
    """Wertet alle Datensätze aus.

    Args:
        progress: progress(index, n, name) → False bricht ab (BatchCancelled)
    """
    entries = []
    for k, item in enumerate(items):
        if progress is not None and progress(k, len(items), item.name) is False:
            raise BatchCancelled()
        entry = BatchEntry(item)
        t0 = time.perf_counter()
        try:
            st = settings
            if dmax_mode == DMAX_SUGGEST:
                dmax, n_spl, ok = _dmax_for(item, settings, q_range, sigma_relative,
                                            settings.dmax)
                st = replace(settings, dmax=float(f"{dmax:.4g}"), n_splines=int(n_spl))
                entry.dmax_suggested = ok
            meta = dict(item.source_metadata)
            meta.update(batch_dmax_mode=dmax_mode,
                        batch_dmax_suggested=entry.dmax_suggested)
            entry.analysis = run_ift_analysis(
                item.q, item.intensity, item.sigma, st, q_range=q_range,
                source_file=item.source_file, source_metadata=meta,
                sigma_relative=sigma_relative, gift_settings=gift_settings)
            if export:
                entry.paths = export_ift_results(entry.analysis, source_file=item.source_file,
                                                 write_w3c=write_w3c)
        except BSSACancelled:
            raise BatchCancelled()
        except (ValueError, np.linalg.LinAlgError, OSError) as e:
            entry.error = str(e)
        entry.runtime_s = time.perf_counter() - t0
        entries.append(entry)
    return entries


SUMMARY_COLUMNS = ['name', 'file', 'record_id', 'status', 'q_min_nm-1', 'q_max_nm-1',
                   'n_artifacts', 'dmax_nm', 'dmax_suggested', 'n_splines', 'lambda_rel',
                   'lambda_method', 'md', 'rg_nm', 'rg_err_nm', 'i0', 'i0_err', 'oscillation',
                   'positive_fraction', 'positive_1sigma', 'n_peaks', 'n_good', 'log_evidence',
                   'rg_guinier_nm', 'warnings']


def summary_rows(entries: List[BatchEntry]) -> List[Dict]:
    rows = []
    for e in entries:
        row = {'name': e.item.name, 'file': Path(e.item.source_file).name}
        a = e.analysis
        if a is None:
            row.update(status=f"Fehler: {e.error}")
            rows.append(row)
            continue
        s = a.solution
        m = a.metrics
        row.update(
            record_id=a.record.record_id, status=a.worst_level,
            **{'q_min_nm-1': a.selection.q_min, 'q_max_nm-1': a.selection.q_max},
            n_artifacts=getattr(a.selection, 'n_artifacts', 0), dmax_nm=s.settings.dmax,
            dmax_suggested=e.dmax_suggested, n_splines=s.settings.n_splines,
            lambda_rel=s.lam_rel,
            lambda_method='manual' if s.lam_manual else s.scan.method, md=s.md,
            rg_nm=s.rg, rg_err_nm=s.rg_err, i0=s.i0, i0_err=s.i0_err,
            oscillation=m.get('oscillation'), positive_fraction=m.get('positive_fraction'),
            positive_1sigma=m.get('positive_1sigma'), n_peaks=m.get('n_peaks'),
            n_good=m.get('n_good'), log_evidence=m.get('log_evidence'),
            rg_guinier_nm=a.guinier[0] if a.guinier else None,
            warnings=' '.join(f.code for f in a.all_flags if f.level == LEVEL_WARNING))
        if a.gift is not None:
            for name, v in a.gift.params.items():
                row[f"sq_{name}"] = v
                row[f"sq_{name}_err"] = a.gift.param_errors.get(name)
        rows.append(row)
    return rows


def write_summary(entries: List[BatchEntry], path) -> Path:
    """Übersicht als CSV (Semikolon-getrennt, UTF-8 mit BOM → Excel-kompatibel)."""
    rows = summary_rows(entries)
    cols = list(SUMMARY_COLUMNS)
    for r in rows:
        cols += [k for k in r if k not in cols]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';', extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: ('' if v is None else (f"{v:.6g}" if isinstance(v, float) else v))
                        for k, v in r.items()})
    return path
