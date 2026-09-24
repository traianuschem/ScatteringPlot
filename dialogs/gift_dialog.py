"""
IFT/GIFT-Dialog (v7.8)

Nicht-modaler Dialog zur Berechnung der Paarabstandsverteilung p(r) eines
1D-Datensatzes mit der indirekten Fourier-Transformation nach Glatter (1977).

Links: Einstellungen (q-Fitbereich inkl. σ-Voreinstellungen aus der
Signifikanzanalyse, Dmax mit Live-Anzeige von π/q_min, Splines, λ, K, Untergrund).
Rechts: Tabs mit I(q)+Fit/Residuen, p(r), λ-Wahl (Glatter Fig. 2), Signifikanz und
Provenance. Unten: Ergebnisse und Flag-Liste.

„Übernehmen“ schreibt p(r), Fit und den Provenance-Sidecar in den Unterordner
GIFT/ neben der Datendatei und meldet die Dateien an das Hauptfenster
(Signal `results_applied`), das daraus eine PDDF-Gruppe anlegt.

Die IFT ist schnell (Millisekunden) und läuft synchron mit entprellter
Live-Vorschau. GIFT (BSSA) und die DREAM-Unsicherheitsanalyse (v7.12, auf Knopfdruck)
laufen im Hintergrund-Thread.
"""

import os
import time
import warnings
from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox, QFormLayout, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QFileDialog, QScrollArea, QSizePolicy, QFrame, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication,
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QColor, QBrush

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from i18n import tr
from utils.data_loader import select_columns
from analysis.significance import (significance, rolling_median, QRANGE_FULL,
                                   QRANGE_SIGMA, QRANGE_MANUAL, detect_lowq_artifacts,
                                   select_q_range)
from analysis.gift.ift import (IFTSettings, LAMBDA_AUTO, K_DIRICHLET, K_GLATTER,
                               K_CURVATURE, estimate_sigma, LAMBDA_INFLEXION,
                               LAMBDA_EVIDENCE)
from analysis.gift.explorer import (suggest_dmax, scan_1d, scan_map, METRICS, OSC_GOOD,
                                    md_acceptable, _physical)
from analysis.gift.diagnostics import (guinier_rg, dmax_qmin_ratio, shannon_channels,
                                       suggest_n_splines, LEVEL_OK, LEVEL_INFO, LEVEL_WARNING,
                                       SIGMA_RELATIVE)
from analysis.gift.pipeline import (run_ift_analysis, export_ift_results, result_paths,
                                    relative_sigma, QRangeSettings, RESULT_SUBDIR)
from analysis.gift.provenance import ProvenanceRecord, compute_sha256
from analysis.gift.structure_factors import MODELS, get_model
from analysis.gift.gift import GIFTSettings
from analysis.gift.bssa import BSSASettings, BSSACancelled
from analysis.gift.parallel import default_workers
from analysis.gift.uncertainty import (UncertaintySettings, run_uncertainty, DreamCancelled,
                                       LOG_LAMBDA, DMAX)
from analysis.gift.dream import DreamSettings
from analysis.gift.kernels import KINDS, PDDF, LABELS, get_kernel, dmax_limit
from analysis.gift.decon import (DeconSettings, DeconCancelled, GEOMETRIES as DECON_GEOMETRIES,
                                 BASIS_SPLINES, BASIS_STEPS, POLY_NONE, POLY_SCAN, POLY_FIXED,
                                 DIST_SCHULZ, DIST_GAUSS, HWHM as DECON_HWHM)
from analysis.gift.pipeline import run_decon_analysis, run_step_model_analysis

_MODEL_ORDER = ('none', 'hs_py_avg', 'hs_vrij', 'hs_py', 'sticky', 'rmsa', 'fractal', 'rod')
LAMBDA_MANUAL = 'manual'


def dataset_arrays(ds):
    """q, I, σ (oder None) eines Datensatzes aus den Rohdaten — OHNE den log-Plot-Filter
    (I ≤ 0 nach Untergrundabzug ist für die IFT legitim); sortiert, q > 0, eindeutig."""
    if getattr(ds, 'raw_data', None) is None:
        ds.load_data()
    data = select_columns(ds.raw_data, ds.col_x, ds.col_y, ds.col_err,
                          filter_nonpositive=False)
    q = data[:, 0]
    I = data[:, 1]
    err = data[:, 2] if data.shape[1] > 2 else None
    keep = np.isfinite(q) & np.isfinite(I) & (q > 0)
    if err is not None:
        # σ ≤ 0 ist kein gültiger Messfehler (z.B. degenerierte Punkte bei der
        # ASAXS-Separation) — einzelne solche Punkte ausschließen statt die
        # gesamte Fehlerspalte zu verwerfen (siehe has_errors in GiftDialog).
        keep &= np.isfinite(err) & (err > 0)
    order = np.argsort(q[keep])
    q, I = q[keep][order], I[keep][order]
    err = err[keep][order] if err is not None else None
    # Doppelte q-Werte entfernen (q muss streng monoton sein)
    q, idx = np.unique(q, return_index=True)
    return q, I[idx], (err[idx] if err is not None else None)

_LEVEL_STYLE = {
    LEVEL_OK: ('✔', '#2e7d32'),
    LEVEL_INFO: ('ℹ', '#1565c0'),
    LEVEL_WARNING: ('⚠', '#c62828'),
}
_CLR_DATA = '#1f77b4'
_CLR_FIT = '#d62728'
_CLR_EXCL = '#b0b0b0'


def flag_text(flag):
    """Übersetzter Flag-Text (Fallback: deutsche Klartextmeldung aus dem Kern)."""
    key = f"gift.flag.{flag.code}.{flag.variant}"
    params = dict(flag.params)
    if 'cause_codes' in params:
        # Ursachenliste (pr_smoothness) je Ursache übersetzen
        codes = [c for c in params['cause_codes'].split(',') if c]
        params['causes'] = '; '.join(tr(f"gift.cause.{c}") for c in codes) or \
            tr('gift.cause.none')
    text = tr(key, **params) if params else tr(key)
    return flag.message if text == key else text


class _GiftWorker(QThread):
    """Führt eine GIFT-Analyse (BSSA) im Hintergrund aus."""

    progress = Signal(int, float, float, int)      # Auswertungen, T, MD, Zyklus
    done = Signal(object)                          # IFTAnalysis
    failed = Signal(str)

    CANCELLED = '__cancelled__'

    def __init__(self, kwargs, parent=None):
        super().__init__(parent)
        self.kwargs = kwargs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _callback(self, n, temperature, md, params, cycle):
        self.progress.emit(int(n), float(temperature), float(md), int(cycle))
        return not self._cancel

    def run(self):
        try:
            analysis = run_ift_analysis(**self.kwargs, progress=self._callback)
        except BSSACancelled:
            self.failed.emit(self.CANCELLED)
            return
        except (ValueError, np.linalg.LinAlgError) as e:
            self.failed.emit(str(e))
            return
        self.done.emit(analysis)


class _DreamWorker(QThread):
    """Führt die DREAM-Unsicherheitsanalyse im Hintergrund aus."""

    progress = Signal(str, int, int, float, float)  # Phase, Auswertungen, Generation, R̂, Akz.
    done = Signal(object, object)                  # (IFTAnalysis, UncertaintyResult)
    failed = Signal(str)

    CANCELLED = '__cancelled__'

    def __init__(self, analysis, settings, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.settings = settings
        self._cancel = False
        self._last = 0.0

    def cancel(self):
        self._cancel = True

    def _callback(self, phase, n, gen, rhat, acc):
        now = time.perf_counter()
        if phase != 'dream' or now - self._last > 0.2:      # GUI nicht überfluten
            self._last = now
            self.progress.emit(phase, int(n), int(gen), float(rhat), float(acc))
        return not self._cancel

    def run(self):
        try:
            result = run_uncertainty(self.analysis, self.settings, progress=self._callback)
        except DreamCancelled:
            self.failed.emit(self.CANCELLED)
            return
        except (ValueError, np.linalg.LinAlgError) as e:
            self.failed.emit(str(e))
            return
        self.done.emit(self.analysis, result)


class _DeconWorker(QThread):
    """DECON bzw. Stufenmodell im Hintergrund (der P-Scan dauert bis zu einigen Minuten)."""

    progress = Signal(int, int)
    done = Signal(object, str, object)          # (IFTAnalysis, Aufgabe, Ergebnis)
    failed = Signal(str)

    CANCELLED = '__cancelled__'

    def __init__(self, analysis, task, kwargs, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.task = task
        self.kwargs = kwargs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _callback(self, j, n):
        self.progress.emit(int(j), int(n))
        return not self._cancel

    def run(self):
        try:
            if self.task == 'steps':
                result = run_step_model_analysis(self.analysis, **self.kwargs)
            else:
                result = run_decon_analysis(self.analysis, progress=self._callback,
                                            **self.kwargs)
        except DeconCancelled:
            self.failed.emit(self.CANCELLED)
            return
        except (ValueError, np.linalg.LinAlgError) as e:
            self.failed.emit(str(e))
            return
        self.done.emit(self.analysis, self.task, result)


class GiftDialog(QDialog):
    """Nicht-modaler Dialog für IFT und GIFT."""

    results_applied = Signal(object)   # dict: paths, record_id, dataset, flags

    def __init__(self, dataset, parent=None, significance_window=9, datasets=None):
        super().__init__(parent)
        self.dataset = dataset
        # Callable → Liste aller geladenen Datensätze (für die Serienauswertung)
        self._datasets_provider = datasets
        self.setWindowTitle(f"{tr('gift.title')} — {dataset.display_label}")
        self.resize(1250, 860)
        self.setModal(False)

        self.analysis = None
        self.out_dir = None
        self._updating = False
        self._dirty = True
        self._worker = None
        self._t_start = 0.0
        self.param_widgets = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.compute)

        self._load_arrays()
        self._build_ui(significance_window)
        self._init_defaults()
        self.compute()

    # ------------------------------------------------------------------
    # Daten
    # ------------------------------------------------------------------

    def _load_arrays(self):
        """Holt q, I, σ aus den Rohdaten des Datensatzes — OHNE den log-Plot-Filter
        (I ≤ 0 nach Untergrundabzug ist für die IFT legitim)."""
        self.q_all, self.I_all, self.err_all = dataset_arrays(self.dataset)
        self.has_errors = self.err_all is not None and np.all(self.err_all > 0)
        self.n_nonpositive = int(np.count_nonzero(self.I_all <= 0))

    def _q_factor(self):
        """Umrechnungsfaktor der Datei-q-Einheit nach nm⁻¹ (Å⁻¹ → nm⁻¹: 10)."""
        combo = getattr(self, 'qunit_combo', None)
        return float(combo.currentData()) if combo is not None else 1.0

    def _current_arrays(self):
        if self.keep_nonpositive_check.isChecked():
            mask = np.ones(len(self.q_all), dtype=bool)
        else:
            mask = self.I_all > 0
        err = self.err_all[mask] if self.has_errors else None
        return self._q_factor() * self.q_all[mask], self.I_all[mask], err

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, significance_window):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # --- linke Seite: Einstellungen (scrollbar) ---------------------------------
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)

        # Daten
        g_data = QGroupBox(tr('gift.group_data'))
        f = QFormLayout(g_data)
        f.addRow(tr('gift.dataset') + ':', QLabel(self.dataset.display_label))
        file_label = QLabel(Path(self.dataset.filepath).name)
        file_label.setToolTip(str(self.dataset.filepath))
        f.addRow(tr('gift.file') + ':', file_label)
        f.addRow(tr('gift.points') + ':', QLabel(str(len(self.q_all))))
        self.qunit_combo = QComboBox()
        self.qunit_combo.addItem('nm⁻¹', 1.0)
        self.qunit_combo.addItem(tr('gift.qunit_angstrom'), 10.0)
        self.qunit_combo.setToolTip(tr('gift.qunit_tooltip'))
        f.addRow(tr('gift.qunit') + ':', self.qunit_combo)
        f.addRow(tr('gift.sigma_source') + ':', QLabel(
            tr('gift.sigma_measured') if self.has_errors else tr('gift.sigma_estimated')))
        # Ohne Fehlerspalte: σ aus dem Rauschen schätzen oder relativ annehmen (Simulationen)
        sigma_row = QHBoxLayout()
        self.sigma_mode_combo = QComboBox()
        self.sigma_mode_combo.addItem(tr('gift.sigma_mode_estimate'), 'estimated')
        self.sigma_mode_combo.addItem(tr('gift.sigma_mode_relative'), SIGMA_RELATIVE)
        self.sigma_mode_combo.setToolTip(tr('gift.sigma_mode_tooltip'))
        sigma_row.addWidget(self.sigma_mode_combo, 1)
        self.sigma_rel_spin = QDoubleSpinBox()
        self.sigma_rel_spin.setRange(0.01, 50.0)
        self.sigma_rel_spin.setDecimals(2)
        self.sigma_rel_spin.setValue(1.0)
        self.sigma_rel_spin.setSuffix(' %')
        sigma_row.addWidget(self.sigma_rel_spin)
        f.addRow(tr('gift.sigma_mode') + ':', sigma_row)
        for w in (self.sigma_mode_combo, self.sigma_rel_spin):
            w.setEnabled(not self.has_errors)
        self.sigma_rel_spin.setEnabled(False)
        self.keep_nonpositive_check = QCheckBox(
            tr('gift.keep_nonpositive', n=self.n_nonpositive))
        self.keep_nonpositive_check.setChecked(True)
        self.keep_nonpositive_check.setToolTip(tr('gift.keep_nonpositive_tooltip'))
        self.keep_nonpositive_check.setEnabled(self.n_nonpositive > 0)
        f.addRow(self.keep_nonpositive_check)
        lv.addWidget(g_data)

        # q-Fitbereich
        g_q = QGroupBox(tr('gift.group_qrange'))
        f = QFormLayout(g_q)
        self.qmode_combo = QComboBox()
        self.qmode_combo.addItem(tr('gift.qrange_full'), (QRANGE_FULL, None))
        for n in (3, 2, 1):
            self.qmode_combo.addItem(tr('gift.qrange_sigma', n=n), (QRANGE_SIGMA, float(n)))
        self.qmode_combo.addItem(tr('gift.qrange_manual'), (QRANGE_MANUAL, None))
        if not self.has_errors:
            model = self.qmode_combo.model()
            for i in (1, 2, 3):
                model.item(i).setEnabled(False)
            self.qmode_combo.setToolTip(tr('gift.qrange_sigma_disabled'))
        f.addRow(tr('gift.qrange_mode') + ':', self.qmode_combo)
        self.window_spin = QSpinBox()
        self.window_spin.setRange(3, 51)
        self.window_spin.setSingleStep(2)
        self.window_spin.setValue(max(3, int(significance_window) | 1))
        self.window_spin.setToolTip(tr('gift.window_tooltip'))
        f.addRow(tr('gift.window') + ':', self.window_spin)
        self.qmin_spin = self._q_spin()
        self.qmax_spin = self._q_spin()
        f.addRow('q_min / nm⁻¹:', self.qmin_spin)
        f.addRow('q_max / nm⁻¹:', self.qmax_spin)
        self.auto_qmin_check = QCheckBox(tr('gift.auto_qmin'))
        self.auto_qmin_check.setChecked(True)
        self.auto_qmin_check.setToolTip(tr('gift.auto_qmin_tooltip'))
        f.addRow(self.auto_qmin_check)
        self.qrange_info = QLabel()
        self.qrange_info.setWordWrap(True)
        f.addRow(self.qrange_info)
        lv.addWidget(g_q)

        # IFT
        g_ift = QGroupBox(tr('gift.group_ift'))
        f = QFormLayout(g_ift)
        self.kind_combo = QComboBox()
        for k in KINDS:
            self.kind_combo.addItem(tr(f'gift.kind.{k}'), k)
        self.kind_combo.setToolTip(tr('gift.kind_tooltip'))
        f.addRow(tr('gift.kind_label') + ':', self.kind_combo)
        self._kind_prev = PDDF
        dmax_row = QHBoxLayout()
        self.dmax_spin = QDoubleSpinBox()
        self.dmax_spin.setRange(0.1, 1e5)
        self.dmax_spin.setDecimals(2)
        self.dmax_spin.setSuffix(' nm')
        self.dmax_spin.setSingleStep(1.0)
        dmax_row.addWidget(self.dmax_spin, 1)
        self.dmax_limit_btn = QPushButton('π/q_min')
        self.dmax_limit_btn.setToolTip(tr('gift.dmax_limit_tooltip'))
        self.dmax_limit_btn.clicked.connect(self._set_dmax_to_limit)
        dmax_row.addWidget(self.dmax_limit_btn)
        self.dmax_suggest_btn = QPushButton(tr('gift.dmax_suggest'))
        self.dmax_suggest_btn.setToolTip(tr('gift.dmax_suggest_tooltip'))
        self.dmax_suggest_btn.clicked.connect(self._set_dmax_suggested)
        dmax_row.addWidget(self.dmax_suggest_btn)
        self.dmax_label = QLabel('Dmax:')
        f.addRow(self.dmax_label, dmax_row)
        self.dmax_info = QLabel()
        self.dmax_info.setWordWrap(True)
        f.addRow(self.dmax_info)
        nspl_row = QHBoxLayout()
        self.nspl_spin = QSpinBox()
        self.nspl_spin.setRange(5, 200)
        self.nspl_spin.setValue(20)
        self.nspl_spin.setToolTip(tr('gift.nsplines_tooltip'))
        nspl_row.addWidget(self.nspl_spin, 1)
        self.nspl_suggest_btn = QPushButton(tr('gift.nsplines_suggest'))
        self.nspl_suggest_btn.setToolTip(tr('gift.nsplines_suggest_tooltip'))
        self.nspl_suggest_btn.clicked.connect(self._set_suggested_n)
        nspl_row.addWidget(self.nspl_suggest_btn)
        f.addRow(tr('gift.nsplines') + ':', nspl_row)
        self.lam_method_combo = QComboBox()
        self.lam_method_combo.addItem(tr('gift.lambda_method_inflexion'), LAMBDA_INFLEXION)
        self.lam_method_combo.addItem(tr('gift.lambda_method_evidence'), LAMBDA_EVIDENCE)
        self.lam_method_combo.addItem(tr('gift.lambda_method_manual'), LAMBDA_MANUAL)
        self.lam_method_combo.setToolTip(tr('gift.lambda_method_tooltip'))
        f.addRow(tr('gift.lambda_method') + ':', self.lam_method_combo)
        self.lam_spin = QDoubleSpinBox()
        self.lam_spin.setRange(-30.0, 4.0)
        self.lam_spin.setDecimals(2)
        self.lam_spin.setSingleStep(0.25)
        self.lam_spin.setPrefix('log₁₀ λ_rel = ')
        self.lam_spin.setEnabled(False)
        f.addRow(self.lam_spin)
        self.k_combo = QComboBox()
        self.k_combo.addItem(tr('gift.k_dirichlet'), K_DIRICHLET)
        self.k_combo.addItem(tr('gift.k_glatter'), K_GLATTER)
        self.k_combo.addItem(tr('gift.k_curvature'), K_CURVATURE)
        self.k_combo.setToolTip(tr('gift.k_tooltip'))
        f.addRow(tr('gift.k_type') + ':', self.k_combo)
        self.bg_check = QCheckBox(tr('gift.background'))
        self.bg_check.setToolTip(tr('gift.background_tooltip'))
        f.addRow(self.bg_check)
        lv.addWidget(g_ift)

        # GIFT: Strukturfaktor
        g_sq = QGroupBox(tr('gift.group_sq'))
        v = QVBoxLayout(g_sq)
        form = QFormLayout()
        self.model_combo = QComboBox()
        for key in _MODEL_ORDER:
            self.model_combo.addItem(tr(MODELS[key].label_key), key)
        self.model_combo.setToolTip(tr('gift.model_tooltip'))
        form.addRow(tr('gift.model') + ':', self.model_combo)
        v.addLayout(form)
        self.param_grid_w = QWidget()
        self.param_grid = QGridLayout(self.param_grid_w)
        self.param_grid.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.param_grid_w)
        row = QHBoxLayout()
        self.from_ift_btn = QPushButton(tr('gift.from_ift'))
        self.from_ift_btn.setToolTip(tr('gift.from_ift_tooltip'))
        self.from_ift_btn.clicked.connect(self._starts_from_ift)
        row.addWidget(self.from_ift_btn)
        row.addStretch()
        row.addWidget(QLabel(tr('gift.seed') + ':'))
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2 ** 31 - 1)
        self.seed_spin.setValue(12345)
        self.seed_spin.setToolTip(tr('gift.seed_tooltip'))
        row.addWidget(self.seed_spin)
        row.addWidget(QLabel(tr('gift.workers') + ':'))
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, max(1, os.cpu_count() or 1))
        self.workers_spin.setValue(default_workers())
        self.workers_spin.setToolTip(tr('gift.workers_tooltip'))
        row.addWidget(self.workers_spin)
        v.addLayout(row)
        self.apparent_label = QLabel(tr('gift.apparent_hint'))
        self.apparent_label.setWordWrap(True)
        self.apparent_label.setStyleSheet('font-style: italic;')
        v.addWidget(self.apparent_label)
        self.gift_status = QLabel()
        self.gift_status.setWordWrap(True)
        v.addWidget(self.gift_status)
        lv.addWidget(g_sq)

        # Unsicherheit (DREAM)
        g_dream = QGroupBox(tr('gift.group_dream'))
        v = QVBoxLayout(g_dream)
        hint = QLabel(tr('gift.dream_hint'))
        hint.setWordWrap(True)
        hint.setStyleSheet('font-style: italic;')
        v.addWidget(hint)
        self.prior_grid_w = QWidget()
        self.prior_grid = QGridLayout(self.prior_grid_w)
        self.prior_grid.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.prior_grid_w)
        row = QHBoxLayout()
        self.prior_default_btn = QPushButton(tr('gift.dream_prior_defaults'))
        self.prior_default_btn.setToolTip(tr('gift.dream_prior_defaults_tooltip'))
        self.prior_default_btn.clicked.connect(lambda: self._set_prior_defaults(force=True))
        row.addWidget(self.prior_default_btn)
        row.addStretch()
        v.addLayout(row)
        self.dream_dmax_limit_check = QCheckBox(tr('gift.dream_dmax_limit'))
        self.dream_dmax_limit_check.setToolTip(tr('gift.dream_dmax_limit_tooltip'))
        self.dream_dmax_limit_check.toggled.connect(lambda _: self._set_prior_defaults(
            force=True, only=(DMAX,)))
        v.addWidget(self.dream_dmax_limit_check)
        self.dream_scale_sigma_check = QCheckBox(tr('gift.dream_scale_sigma'))
        self.dream_scale_sigma_check.setToolTip(tr('gift.dream_scale_sigma_tooltip'))
        v.addWidget(self.dream_scale_sigma_check)
        grid = QGridLayout()
        self.dream_chains_spin = QSpinBox()
        self.dream_chains_spin.setRange(3, 64)
        self.dream_chains_spin.setValue(DreamSettings.n_chains)
        self.dream_chains_spin.setToolTip(tr('gift.dream_chains_tooltip'))
        self.dream_budget_spin = QSpinBox()
        self.dream_budget_spin.setRange(2000, 2_000_000)
        self.dream_budget_spin.setSingleStep(10000)
        self.dream_budget_spin.setValue(DreamSettings.max_evals)
        self.dream_budget_spin.setToolTip(tr('gift.dream_budget_tooltip'))
        self.dream_rhat_spin = QDoubleSpinBox()
        self.dream_rhat_spin.setRange(1.01, 1.5)
        self.dream_rhat_spin.setDecimals(2)
        self.dream_rhat_spin.setSingleStep(0.01)
        self.dream_rhat_spin.setValue(DreamSettings.r_hat_target)
        self.dream_rhat_spin.setToolTip(tr('gift.dream_rhat_tooltip'))
        self.dream_seed_spin = QSpinBox()
        self.dream_seed_spin.setRange(0, 2 ** 31 - 1)
        self.dream_seed_spin.setValue(DreamSettings.seed)
        for i, (label, w) in enumerate(((tr('gift.dream_chains'), self.dream_chains_spin),
                                        (tr('gift.dream_budget'), self.dream_budget_spin),
                                        ('R̂ <', self.dream_rhat_spin),
                                        (tr('gift.seed'), self.dream_seed_spin))):
            grid.addWidget(QLabel(label + ':'), i // 2, 2 * (i % 2))
            grid.addWidget(w, i // 2, 2 * (i % 2) + 1)
        v.addLayout(grid)
        self.dream_btn = QPushButton(tr('gift.dream_run'))
        self.dream_btn.setToolTip(tr('gift.dream_run_tooltip'))
        self.dream_btn.clicked.connect(self._start_dream)
        v.addWidget(self.dream_btn)
        self.dream_status = QLabel()
        self.dream_status.setWordWrap(True)
        v.addWidget(self.dream_status)
        lv.addWidget(g_dream)
        self.prior_widgets = {}
        self._prior_edited = False

        # Ausgabe
        g_out = QGroupBox(tr('gift.group_output'))
        f = QVBoxLayout(g_out)
        self.out_label = QLabel()
        self.out_label.setWordWrap(True)
        f.addWidget(self.out_label)
        out_btn = QPushButton(tr('gift.change_out_dir'))
        out_btn.clicked.connect(self._choose_out_dir)
        f.addWidget(out_btn)
        self.w3c_check = QCheckBox(tr('gift.write_w3c'))
        self.w3c_check.setChecked(True)
        f.addWidget(self.w3c_check)
        lv.addWidget(g_out)

        self.live_check = QCheckBox(tr('gift.live_preview'))
        self.live_check.setChecked(True)
        lv.addWidget(self.live_check)
        lv.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(left)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumWidth(440)
        splitter.addWidget(scroll)

        # --- rechte Seite: Tabs + Ergebnisse -------------------------------------
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        # I(q) mit Residuen: GridSpec mit festen Rändern (tight_layout ist damit inkompatibel)
        self.fig_iq, self.canvas_iq = self._add_plot_tab(tr('gift.tab_iq'), layout=False)
        self.fig_pr, self.canvas_pr = self._add_plot_tab(tr('gift.tab_pr'))
        self.fig_sq, self.canvas_sq = self._add_plot_tab(tr('gift.tab_sq'))
        self.fig_lam, self.canvas_lam = self._add_plot_tab(tr('gift.tab_lambda'))
        self.fig_sig, self.canvas_sig = self._add_plot_tab(tr('gift.tab_significance'))
        self.fig_bssa, self.canvas_bssa = self._add_plot_tab(tr('gift.tab_bssa'))
        self._build_explorer_tab()
        self._build_decon_tab()
        # Unsicherheit (DREAM): Übersicht, Corner-Plot, Ketten, Posterior-Bänder
        self.unc_tabs = QTabWidget()
        ov = QWidget()
        ovl = QVBoxLayout(ov)
        self.unc_info = QLabel()
        self.unc_info.setWordWrap(True)
        self.unc_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        ovl.addWidget(self.unc_info)
        self.dream_adopt_btn = QPushButton(tr('gift.dream_adopt'))
        self.dream_adopt_btn.setToolTip(tr('gift.dream_adopt_tooltip'))
        self.dream_adopt_btn.clicked.connect(self._adopt_from_dream)
        self.dream_adopt_btn.setEnabled(False)
        ovl.addWidget(self.dream_adopt_btn, 0, Qt.AlignLeft)
        self.unc_table = QTableWidget(0, 7)
        self.unc_table.setHorizontalHeaderLabels(
            [tr('gift.dream_col_param'), tr('gift.dream_col_reference'), tr('gift.dream_col_median'),
             '68 %', '95 %', 'R̂', 'MAP'])
        self.unc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.unc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ovl.addWidget(self.unc_table, 1)
        self.unc_tabs.addTab(ov, tr('gift.dream_tab_overview'))
        self.fig_corner, self.canvas_corner = self._add_plot_tab(tr('gift.dream_tab_corner'),
                                                                 self.unc_tabs, layout=False)
        self.fig_trace, self.canvas_trace = self._add_plot_tab(tr('gift.dream_tab_traces'),
                                                               self.unc_tabs)
        self.fig_band, self.canvas_band = self._add_plot_tab(tr('gift.dream_tab_bands'),
                                                             self.unc_tabs)
        self.tabs.addTab(self.unc_tabs, tr('gift.tab_uncertainty'))
        prov_w = QWidget()
        pv = QVBoxLayout(prov_w)
        self.record_label = QLabel()
        self.record_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pv.addWidget(self.record_label)
        self.prov_tree = QTreeWidget()
        self.prov_tree.setHeaderLabels([tr('gift.prov_key'), tr('gift.prov_value')])
        self.prov_tree.setColumnWidth(0, 280)
        pv.addWidget(self.prov_tree)
        self.tabs.addTab(prov_w, tr('gift.tab_provenance'))
        rv.addWidget(self.tabs, 3)

        res_row = QHBoxLayout()
        self.result_label = QLabel()
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.result_label.setMinimumWidth(260)
        res_row.addWidget(self.result_label)
        self.flag_list = QListWidget()
        self.flag_list.setWordWrap(True)
        self.flag_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        res_row.addWidget(self.flag_list, 1)
        res_w = QWidget()
        res_w.setLayout(res_row)
        res_w.setMaximumHeight(210)
        rv.addWidget(res_w, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([460, 790])

        # --- Buttons ---------------------------------------------------------------
        btn_row = QHBoxLayout()
        self.compute_btn = QPushButton(tr('gift.compute'))
        self.compute_btn.clicked.connect(self.compute)
        btn_row.addWidget(self.compute_btn)
        self.cancel_btn = QPushButton(tr('gift.cancel'))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_gift)
        btn_row.addWidget(self.cancel_btn)
        load_btn = QPushButton(tr('gift.load_sidecar'))
        load_btn.setToolTip(tr('gift.load_sidecar_tooltip'))
        load_btn.clicked.connect(self._load_settings_from_sidecar)
        btn_row.addWidget(load_btn)
        self.batch_btn = QPushButton(tr('gift.batch'))
        self.batch_btn.setToolTip(tr('gift.batch_tooltip'))
        self.batch_btn.clicked.connect(self._open_batch)
        self.batch_btn.setEnabled(self._datasets_provider is not None)
        btn_row.addWidget(self.batch_btn)
        btn_row.addStretch()
        self.apply_btn = QPushButton(tr('gift.apply'))
        self.apply_btn.setToolTip(tr('gift.apply_tooltip'))
        self.apply_btn.clicked.connect(self.apply)
        btn_row.addWidget(self.apply_btn)
        close_btn = QPushButton(tr('common.close'))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        # --- Signale ---------------------------------------------------------------
        self.qmode_combo.currentIndexChanged.connect(self._on_qmode_changed)
        self.lam_method_combo.currentIndexChanged.connect(self._on_lam_method_changed)
        self.auto_qmin_check.toggled.connect(self._on_auto_qmin_toggled)
        for w in (self.window_spin, self.qmin_spin, self.qmax_spin, self.dmax_spin,
                  self.nspl_spin, self.lam_spin):
            w.valueChanged.connect(self._schedule)
        self.k_combo.currentIndexChanged.connect(self._schedule)
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        self.bg_check.toggled.connect(self._schedule)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.qunit_combo.currentIndexChanged.connect(self._on_qunit_changed)
        self.seed_spin.valueChanged.connect(self._schedule)
        self.sigma_mode_combo.currentIndexChanged.connect(self._on_sigma_mode_changed)
        self.sigma_rel_spin.valueChanged.connect(self._schedule)
        self.keep_nonpositive_check.toggled.connect(self._on_data_filter_changed)
        self.dmax_spin.valueChanged.connect(self._update_dmax_info)
        self.qmin_spin.valueChanged.connect(self._update_dmax_info)

    def _q_spin(self):
        s = QDoubleSpinBox()
        s.setDecimals(5)
        s.setRange(0.0, 1e4)
        s.setSingleStep(0.001)
        return s

    def _add_plot_tab(self, title, tabs=None, layout=True):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        fig = Figure(figsize=(7, 5), layout='tight' if layout else 'none')
        canvas = FigureCanvasQTAgg(fig)
        v.addWidget(NavigationToolbar2QT(canvas, w))
        v.addWidget(canvas)
        (tabs or self.tabs).addTab(w, title)
        return fig, canvas

    # ------------------------------------------------------------------
    # Startwerte
    # ------------------------------------------------------------------

    def _init_defaults(self):
        self._updating = True
        q, I, err = self._current_arrays()
        self.qmin_spin.setValue(self._auto_qmin())
        self.qmax_spin.setValue(q[-1])
        # Standard: 2σ-Voreinstellung, falls Fehler vorhanden
        self.qmode_combo.setCurrentIndex(2 if self.has_errors else 0)
        qf, If, sf, sel = self._fit_arrays()
        guinier = guinier_rg(qf, If, sf)
        limit = np.pi / sel.q_min
        if guinier is not None:
            dmax = min(limit, 3.5 * guinier[0])
        else:
            # Kein Guinier-Bereich: Teilchen vermutlich > π/q_min. Dmax aus dem Explorer
            # statt stillschweigend π/q_min (erzwingt sonst ein oszillierendes p(r)).
            st = IFTSettings(dmax=limit, n_splines=suggest_n_splines(limit, sel.q_min, sel.q_max))
            try:
                dmax = suggest_dmax(qf, If, sf, st)[0] or limit
            except (ValueError, np.linalg.LinAlgError):
                dmax = limit
        self.dmax_spin.setValue(float(f"{dmax:.3g}"))
        self._updating = False
        self._on_qmode_changed()
        # Spline-Anzahl aus den Shannon-Kanälen des (vorläufigen) Fitbereichs
        self._set_suggested_n()
        self._on_model_changed()
        self._update_out_label()

    # ------------------------------------------------------------------
    # Reaktionen
    # ------------------------------------------------------------------

    def _schedule(self, *_):
        if self._updating:
            return
        self._dirty = True
        if self._model_key() != 'none':
            # GIFT dauert Sekunden: nur auf Knopfdruck rechnen
            if self._worker is None:
                self.gift_status.setText(tr('gift.gift_stale'))
            return
        if self.live_check.isChecked():
            self._timer.start()

    def _on_qmode_changed(self, *_):
        mode, _n = self.qmode_combo.currentData()
        self.qmax_spin.setEnabled(mode != QRANGE_SIGMA)
        self.window_spin.setEnabled(mode == QRANGE_SIGMA)
        if mode == QRANGE_FULL:
            q, _, _ = self._current_arrays()
            self._updating = True
            self.qmin_spin.setValue(self._auto_qmin())
            self.qmax_spin.setValue(q[-1])
            self._updating = False
        self.qmin_spin.setEnabled(mode != QRANGE_FULL)
        self.auto_qmin_check.setEnabled(mode != QRANGE_MANUAL)
        self._update_dmax_info()
        self._schedule()

    def _lam_method(self):
        return self.lam_method_combo.currentData()

    def _set_lam_method(self, method):
        idx = self.lam_method_combo.findData(method)
        if idx >= 0:
            self.lam_method_combo.setCurrentIndex(idx)

    def _on_lam_method_changed(self, *_):
        self.lam_spin.setEnabled(self._lam_method() == LAMBDA_MANUAL)
        self._schedule()

    def _set_manual(self, dmax=None, lam_rel=None, n_splines=None):
        """Übernimmt Werte (Explorer-Klick, DREAM) in die Einstellungen."""
        self._updating = True
        try:
            if dmax is not None:
                self.dmax_spin.setValue(float(f"{dmax:.4g}"))
            if n_splines is not None:
                self.nspl_spin.setValue(int(n_splines))
            if lam_rel is not None:
                self._set_lam_method(LAMBDA_MANUAL)
                self.lam_spin.setEnabled(True)
                self.lam_spin.setValue(float(np.log10(lam_rel)))
        finally:
            self._updating = False
        self._update_dmax_info()
        self._schedule()

    # --- automatisches q_min ---------------------------------------------------------

    def _auto_first(self):
        """Index des ersten vertrauenswürdigen Punkts (Artefakterkennung) bzw. 0."""
        if not self.auto_qmin_check.isChecked():
            return 0
        _q, I, err = self._current_arrays()
        return detect_lowq_artifacts(I, err)

    def _auto_qmin(self):
        q, _, _ = self._current_arrays()
        return float(q[self._auto_first()])

    def _on_auto_qmin_toggled(self, *_):
        mode, _n = self.qmode_combo.currentData()
        if mode != QRANGE_MANUAL:
            self._updating = True
            self.qmin_spin.setValue(self._auto_qmin())
            self._updating = False
        self._update_dmax_info()
        self._schedule()

    def _on_qunit_changed(self, *_):
        """Neue q-Einheit: Startwerte (q-Bereich, Dmax, N) neu bestimmen."""
        self._init_defaults()
        self._schedule()

    def _on_data_filter_changed(self, *_):
        self._on_qmode_changed()

    def _on_sigma_mode_changed(self, *_):
        self.sigma_rel_spin.setEnabled(
            not self.has_errors and self.sigma_mode_combo.currentData() == SIGMA_RELATIVE)
        self._schedule()

    def _sigma_relative(self):
        """Relativer Fehler (Anteil), falls ohne Fehlerspalte „relativ“ gewählt ist."""
        if self.has_errors or self.sigma_mode_combo.currentData() != SIGMA_RELATIVE:
            return None
        return self.sigma_rel_spin.value() / 100.0

    def _kind(self):
        return self.kind_combo.currentData() or PDDF

    def _on_kind_changed(self, *_):
        """IFT-Art gewechselt (v7.15): Beschriftungen anpassen; beim Wechsel zwischen Abstand
        (Dmax) und Radius (R_max) den Wert umrechnen, damit die Teilchengröße gleich bleibt."""
        kind = self._kind()
        span_old = get_kernel(self._kind_prev).span
        span_new = get_kernel(kind).span
        self._kind_prev = kind
        self.dmax_label.setText(tr(f'gift.dmax_label.{kind}') + ':')
        self.dmax_limit_btn.setText('π/(2q_min)' if span_new == 2 else 'π/q_min')
        if not self._updating and span_old != span_new:
            self.dmax_spin.setValue(self.dmax_spin.value() * span_old / span_new)
        self._update_dmax_info()
        self._schedule()

    def _set_suggested_n(self):
        sel = self._fit_arrays()[3]          # voraussichtlicher Fitbereich (inkl. nσ-q_max)
        self.nspl_spin.setValue(suggest_n_splines(self.dmax_spin.value(), sel.q_min, sel.q_max,
                                                  kind=self._kind()))

    def _set_dmax_to_limit(self):
        self.dmax_spin.setValue(float(f"{dmax_limit(self._effective_qmin(), self._kind()):.4g}"))

    def _effective_qmin(self):
        q, _, _ = self._current_arrays()
        mode, _n = self.qmode_combo.currentData()
        if mode == QRANGE_FULL:
            return self._auto_qmin()
        return max(float(q[0]), self.qmin_spin.value())

    def _fit_arrays(self):
        """Daten im voraussichtlichen Fitbereich (vor der Rechnung, für Startwerte)."""
        q, I, err = self._current_arrays()
        sig = err if err is not None else self._sigma_for_display(q, I)
        try:
            sel = select_q_range(q, I, err, **self._qrange_settings().to_kwargs())
        except ValueError:
            sel = select_q_range(q, I, None, auto_qmin=self.auto_qmin_check.isChecked())
        m = sel.mask(q)
        return q[m], I[m], sig[m], sel

    def _set_dmax_suggested(self):
        """Dmax (und N) aus dem Explorer: kleinstes Dmax mit glattem, vor Dmax auslaufendem
        p(r) und voller Anpassung (explorer.suggest_dmax)."""
        q, I, s, sel = self._fit_arrays()
        kind = self._kind()
        limit = dmax_limit(sel.q_min, kind)
        n = suggest_n_splines(limit, sel.q_min, sel.q_max, kind=kind)
        st = self._settings()
        st.dmax, st.n_splines = limit, n
        dmax, _scan = suggest_dmax(q, I, s, st)
        if dmax is None:
            QMessageBox.information(self, tr('gift.dmax_suggest'), tr('gift.dmax_suggest_none'))
            return
        self._set_manual(dmax=dmax, n_splines=suggest_n_splines(dmax, sel.q_min, sel.q_max,
                                                                kind=kind))

    def _update_dmax_info(self, *_):
        q_min = self._effective_qmin()
        kind = self._kind()
        ratio = dmax_qmin_ratio(self.dmax_spin.value(), q_min, kind)
        color = _LEVEL_STYLE[LEVEL_WARNING][1] if ratio > 1 else _LEVEL_STYLE[LEVEL_OK][1]
        lim_txt = 'π/(2q_min)' if get_kernel(kind).span == 2 else 'π/q_min'
        self.dmax_info.setText(
            f"<span style='color:{color}'>{lim_txt} = {dmax_limit(q_min, kind):.4g} nm · "
            f"{tr(f'gift.dmax_label.{kind}')}/({lim_txt}) = {ratio:.2f}</span>")

    def _choose_out_dir(self):
        start = str(self._out_dir())
        d = QFileDialog.getExistingDirectory(self, tr('gift.change_out_dir'), start)
        if d:
            self.out_dir = Path(d)
            self._update_out_label()

    def _out_dir(self):
        return self.out_dir or Path(self.dataset.filepath).parent / RESULT_SUBDIR

    def _update_out_label(self):
        self.out_label.setText(tr('gift.out_dir', path=str(self._out_dir())))

    # ------------------------------------------------------------------
    # Rechnung
    # ------------------------------------------------------------------

    def _settings(self):
        method = self._lam_method()
        manual = method == LAMBDA_MANUAL
        lam = 10 ** self.lam_spin.value() if manual else LAMBDA_AUTO
        return IFTSettings(dmax=self.dmax_spin.value(), n_splines=self.nspl_spin.value(),
                           lam=lam, k_type=self.k_combo.currentData(),
                           background=self.bg_check.isChecked(),
                           lam_method=LAMBDA_INFLEXION if manual else method,
                           kind=self._kind())

    def _qrange_settings(self):
        mode, n = self.qmode_combo.currentData()
        q, _, _ = self._current_arrays()
        auto = self.auto_qmin_check.isChecked()
        if mode == QRANGE_FULL:
            return QRangeSettings(mode=QRANGE_FULL, auto_qmin=auto)
        q_min = self.qmin_spin.value()
        # q_min = Anfangswert bzw. automatisch erkannter Wert → nicht manuell
        base = self._auto_qmin() if (auto and mode != QRANGE_MANUAL) else float(q[0])
        q_min = None if q_min <= base * (1 + 1e-9) else q_min
        if mode == QRANGE_SIGMA:
            return QRangeSettings(mode=QRANGE_SIGMA, n_sigma=n, window=self.window_spin.value(),
                                  q_min=q_min, auto_qmin=auto)
        q_max = self.qmax_spin.value()
        q_max = None if q_max >= q[-1] * (1 - 1e-9) else q_max
        return QRangeSettings(mode=QRANGE_MANUAL, q_min=q_min, q_max=q_max)

    def _source_metadata(self):
        ds = self.dataset
        return {
            'dataset_name': ds.name,
            'col_x': ds.col_x, 'col_y': ds.col_y, 'col_err': ds.col_err,
            'nonpositive_intensities': 'kept' if self.keep_nonpositive_check.isChecked()
            else 'removed',
            'n_nonpositive': self.n_nonpositive,
            'q_unit_file': 'nm^-1' if self._q_factor() == 1.0 else 'A^-1',
            'q_conversion_factor': self._q_factor(),
        }

    def _analysis_kwargs(self):
        q, I, err = self._current_arrays()
        return dict(q=q, intensity=I, sigma=err, settings=self._settings(),
                    q_range=self._qrange_settings(), source_file=self.dataset.filepath,
                    source_metadata=self._source_metadata(),
                    sigma_relative=self._sigma_relative())

    def _show_error(self, message):
        self.analysis = None
        self.result_label.setText(f"<b style='color:#c62828'>{tr('gift.error')}</b><br>{message}")
        self.flag_list.clear()
        self.apply_btn.setEnabled(False)

    def compute(self):
        """IFT (synchron, Millisekunden) oder GIFT (Hintergrund-Thread) starten."""
        self._timer.stop()
        if self._worker is not None:
            # Während GIFT/DREAM läuft, bleibt die Analyse unverändert (Ergebnis gehört dazu)
            self._dirty = True
            return
        if self._model_key() != 'none':
            self._start_gift()
            return
        try:
            self.analysis = run_ift_analysis(**self._analysis_kwargs())
        except (ValueError, np.linalg.LinAlgError) as e:
            self._show_error(e)
            return
        self._dirty = False
        self._show_analysis()

    def _show_analysis(self):
        self.apply_btn.setEnabled(True)
        sel = self.analysis.selection
        # q-Spinboxen an die tatsächliche Auswahl anpassen (σ-Modus berechnet q_max)
        self._updating = True
        if self.qmode_combo.currentData()[0] == QRANGE_SIGMA:
            self.qmax_spin.setValue(sel.q_max)
        if self.qmode_combo.currentData()[0] != QRANGE_MANUAL and not sel.q_min_manual:
            self.qmin_spin.setValue(sel.q_min)
        if self._lam_method() != LAMBDA_MANUAL:
            self.lam_spin.setValue(np.log10(self.analysis.solution.lam_rel))
        self._updating = False
        self.qrange_info.setText(tr('gift.qrange_info', n=sel.n_selected, total=sel.n_total,
                                    q_min=f"{sel.q_min:.4g}", q_max=f"{sel.q_max:.4g}"))
        self._update_dmax_info()
        self._set_explorer_ranges()
        self._set_prior_defaults()
        if self.analysis.uncertainty is None:
            self.dream_status.setText('')
        self._show_results()
        self._plot_all()
        self._show_provenance()

    def _show_results(self):
        a = self.analysis
        s = a.solution
        kind = s.settings.kind
        lab = LABELS[kind]
        rows = [
            f"<b>{lab['rg']}</b> = {s.rg:.4g} ± {s.rg_err:.2g} nm",
            f"<b>{lab['i0']}</b> = {s.i0:.4g} ± {s.i0_err:.2g}",
        ]
        if lab['equiv'] and np.isfinite(s.rg):
            name, fac = lab['equiv']
            rows.append(f"{tr(f'gift.equiv.{kind}')} = {fac * s.rg:.4g} ± {fac * s.rg_err:.2g} nm")
        z = a.extras.get('size_statistics')
        if z:
            x = lab['x']
            rows.append(f"{tr('gift.size_mode')} = {z['mode']:.4g} nm · ⟨{x}⟩<sub>V</sub> = "
                        f"{z['mean_V']:.4g} ± {z['mean_V_err']:.2g} nm · σ<sub>V</sub> = "
                        f"{z['std_V']:.3g} nm")
            note = (f" ({tr('gift.size_number_range', r=format(z['r_min'], '.3g'))})"
                    if z['number_restricted'] else '')
            rows.append(f"⟨{x}⟩<sub>N</sub> = {z['mean_N']:.4g} ± {z['mean_N_err']:.2g} nm · "
                        f"σ<sub>N</sub> = {z['std_N']:.3g} nm{note}")
        if a.guinier:
            rows.append(f"{lab['rg']}<sub>Guinier</sub> = {a.guinier[0]:.4g} nm "
                        f"({a.guinier[2]} Pkt.)")
        rows.append(f"<b>MD</b> = {s.md:.3g}")
        method = 'manual' if s.lam_manual else s.scan.method
        rows.append(f"λ<sub>rel</sub> = {s.lam_rel:.3g} ({tr('gift.lambda_label_' + method)})")
        m = a.metrics
        if m:
            rows.append(f"{tr('gift.metric.oscillation')} = {m['oscillation']:.2f} · "
                        f"{tr('gift.metric.n_peaks')} = {m['n_peaks']:.0f} · "
                        f"{tr('gift.metric.positive_fraction')} = {m['positive_fraction']:.2f} "
                        f"({m['positive_1sigma']:.2f})")
            rows.append(f"N<sub>g</sub> = {m['n_good']:.1f} · log p(I) = {m['log_evidence']:.5g}")
        if s.background is not None:
            rows.append(f"{tr('gift.background_value')} = {s.background:.4g} ± {s.background_err:.2g}")
        ns = shannon_channels(s.settings.dmax, s.q[0], s.q[-1], kind)
        rows.append(f"N<sub>s</sub> = {ns:.1f}")
        if a.gift is not None:
            g = a.gift
            model = get_model(g.model_key)
            rows.append(f"<b>S(q)</b>: {tr(model.label_key)}")
            for p in model.params:
                err = g.param_errors.get(p.name, float('nan'))
                fixed = '' if p.name in g.free else f" ({tr('gift.param_fixed')})"
                unit = f" {p.unit}" if p.unit else ''
                rows.append(f"&nbsp;&nbsp;{p.label} = {g.params[p.name]:.4g} ± {err:.2g}{unit}{fixed}")
            rows.append(f"MD<sub>ohne S(q)</sub> = {g.md_without_sq:.3g}")
            info = g.model_info or {}
            if 'debye_length_nm' in info:
                rows.append(f"λ<sub>D</sub> = {info['debye_length_nm']:.3g} nm, κσ = {info['k']:.3g}, "
                            f"βU(σ) = {info['contact_potential_kT']:.3g} kT")
                if info.get('rescale_s', 1.0) < 0.999:
                    rows.append(f"σ'/σ = {1.0 / info['rescale_s']:.3g} ({tr('gift.rmsa_rescaled')})")
        if a.uncertainty is not None:
            u = a.uncertainty
            rows.append(f"<b>DREAM</b> ({tr('gift.dream_median_95')})")
            for n in u.names:
                sm = u.summary[n]
                unit = f" {u.units[n]}" if u.units[n] else ''
                rows.append(f"&nbsp;&nbsp;{u.labels[n]} = {sm['median']:.4g} "
                            f"[{sm['q2.5']:.4g}, {sm['q97.5']:.4g}]{unit}")
            rows.append(f"&nbsp;&nbsp;{lab['rg']} = {u.rg['median']:.4g} [{u.rg['q2.5']:.4g}, "
                        f"{u.rg['q97.5']:.4g}] nm")
        self.result_label.setText("<br>".join(rows))

        self.flag_list.clear()
        order = {LEVEL_WARNING: 0, LEVEL_INFO: 1, LEVEL_OK: 2}
        for flag in sorted(a.all_flags, key=lambda f: order[f.level]):
            symbol, color = _LEVEL_STYLE[flag.level]
            item = QListWidgetItem(f"{symbol}  {flag_text(flag)}")
            item.setForeground(QBrush(QColor(color)))
            item.setToolTip(flag.message)
            self.flag_list.addItem(item)

    # ------------------------------------------------------------------
    # GIFT
    # ------------------------------------------------------------------

    def _model_key(self):
        return self.model_combo.currentData() if hasattr(self, 'model_combo') else 'none'

    def _on_model_changed(self, *_):
        key = self._model_key()
        model = get_model(key)
        self._rebuild_param_grid()
        self._rebuild_prior_grid()
        self.param_grid_w.setVisible(bool(model.params))
        self.from_ift_btn.setVisible(bool(model.params))
        self.seed_spin.setEnabled(bool(model.params))
        self.apparent_label.setVisible(model.apparent_parameters)
        self.live_check.setEnabled(key == 'none')
        self.compute_btn.setText(tr('gift.compute') if key == 'none' else tr('gift.run_gift'))
        if model.params and self.analysis is not None and self.analysis.gift is None:
            self._starts_from_ift()
        self.gift_status.setText('' if key == 'none' else tr('gift.gift_stale'))
        self._dirty = True
        if key == 'none' and not self._updating:
            self._schedule()

    def _rebuild_param_grid(self):
        while self.param_grid.count():
            item = self.param_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.param_widgets = {}
        model = get_model(self._model_key())
        if not model.params:
            return
        for col, text in enumerate(('', tr('gift.param_start'), tr('gift.param_lower'),
                                    tr('gift.param_upper'), tr('gift.param_fixed'))):
            self.param_grid.addWidget(QLabel(f"<i>{text}</i>"), 0, col)
        for row, p in enumerate(model.params, start=1):
            unit = f" / {p.unit}" if p.unit else ''
            self.param_grid.addWidget(QLabel(p.label + unit), row, 0)
            widgets = {}
            for col, key in enumerate(('start', 'lower', 'upper'), start=1):
                spin = QDoubleSpinBox()
                spin.setDecimals(p.decimals)
                spin.setRange(p.lower, p.upper)
                spin.setSingleStep(10 ** -max(p.decimals - 1, 0))
                self.param_grid.addWidget(spin, row, col)
                widgets[key] = spin
            fixed = QCheckBox()
            self.param_grid.addWidget(fixed, row, 4)
            widgets['fixed'] = fixed
            self.param_widgets[p.name] = widgets
            fixed.setChecked(p.fixed_default)
            self._set_param(p, p.default)
            for w in (widgets['start'], widgets['lower'], widgets['upper']):
                w.valueChanged.connect(self._schedule)
            fixed.toggled.connect(self._schedule)
            fixed.toggled.connect(lambda _: self._set_prior_defaults())

    def _set_param(self, spec, start):
        """Setzt Startwert und Standard-Suchgrenzen eines Parameters."""
        w = self.param_widgets[spec.name]
        lo, hi = spec.lower, spec.upper
        if spec.relative_search and start > 0:
            lo = max(spec.lower, start / spec.relative_search)
            hi = min(spec.upper, start * spec.relative_search)
        was = self._updating
        self._updating = True
        w['lower'].setValue(lo)
        w['upper'].setValue(hi)
        w['start'].setValue(start)
        self._updating = was

    def _starts_from_ift(self):
        """Startwerte aus der IFT je nach `ParamSpec.start_rule`: Radien aus Rg (äquivalente
        Kugel, R = √(5/3)·Rg), ξ = 10·R, Stäbchenlänge = Dmax; sonst Standardwerte.

        Nach [BP97] konvergiert die Suche mit eher überschätzten Startwerten besser.
        """
        model = get_model(self._model_key())
        rg = None
        if self.analysis is not None and np.isfinite(self.analysis.solution.rg):
            rg = self.analysis.solution.rg
        r_eq = np.sqrt(5.0 / 3.0) * rg if rg else self.dmax_spin.value() / 2.0
        rules = {'rg_sphere': r_eq, 'rg_sphere_x10': 10.0 * r_eq,
                 'dmax': self.dmax_spin.value()}
        for p in model.params:
            start = rules.get(p.start_rule, p.default)
            start = min(max(start, p.lower), p.upper)
            self._set_param(p, float(f"{start:.3g}"))
        self._schedule()

    def _gift_settings(self):
        model = get_model(self._model_key())
        start, lower, upper, fixed = {}, {}, {}, []
        for p in model.params:
            w = self.param_widgets[p.name]
            start[p.name] = w['start'].value()
            lower[p.name] = w['lower'].value()
            upper[p.name] = w['upper'].value()
            if w['fixed'].isChecked():
                fixed.append(p.name)
        return GIFTSettings(model=model.key, start=start, lower=lower, upper=upper,
                            fixed=fixed, bssa=BSSASettings(seed=self.seed_spin.value()),
                            n_workers=self.workers_spin.value())

    def _set_busy(self, busy):
        self.compute_btn.setEnabled(not busy)
        self.apply_btn.setEnabled(not busy and self.analysis is not None)
        self.cancel_btn.setEnabled(busy)
        self.model_combo.setEnabled(not busy)
        self.dream_btn.setEnabled(not busy)
        self.prior_default_btn.setEnabled(not busy)
        decon_ok = self.analysis is not None and             self.analysis.solution.settings.kind in DECON_GEOMETRIES
        self.decon_run_btn.setEnabled(not busy and decon_ok)
        self.decon_steps_btn.setEnabled(not busy and decon_ok and self.analysis.decon is not None)

    def _start_gift(self):
        if self._worker is not None:
            return
        gs = self._gift_settings()
        for name in gs.start:
            if not gs.lower[name] <= gs.start[name] <= gs.upper[name]:
                QMessageBox.warning(self, tr('gift.run_gift'), tr('gift.start_outside', name=name))
                return
        self._worker = _GiftWorker(dict(self._analysis_kwargs(), gift_settings=gs), self)
        self._worker.progress.connect(self._on_gift_progress)
        self._worker.done.connect(self._on_gift_done)
        self._worker.failed.connect(self._on_gift_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._t_start = time.perf_counter()
        self._set_busy(True)
        self.gift_status.setText(tr('gift.gift_starting'))
        self._worker.start()

    def _on_gift_progress(self, n, temperature, md, cycle):
        self.gift_status.setText(tr('gift.gift_running', n=n, T=f"{temperature:.3g}",
                                    md=f"{md:.4g}", cycle=cycle + 1))

    def _on_gift_done(self, analysis):
        self.analysis = analysis
        self._dirty = False
        dt = time.perf_counter() - self._t_start
        self.gift_status.setText(tr('gift.gift_done', n=analysis.gift.n_evals,
                                    t=f"{dt:.1f}", cycles=len(analysis.gift.lambda_history) - 1))
        self._show_analysis()
        pending = getattr(self, '_pending_reproduction', None)
        self._pending_reproduction = None
        if pending is not None:
            self._report_reproduction(pending)
        # _start_dream braucht einen freien Worker-Slot: nach Ende des GIFT-Threads starten
        if getattr(self, '_pending_dream', None) is not None:
            QTimer.singleShot(0, self._start_pending_dream_when_idle)

    def _on_gift_failed(self, message):
        self._pending_reproduction = None
        self._pending_dream = None
        if message == _GiftWorker.CANCELLED:
            self.gift_status.setText(tr('gift.gift_cancelled'))
        else:
            self.gift_status.setText(f"<span style='color:#c62828'>{tr('gift.error')}: {message}</span>")

    def _on_worker_finished(self):
        self._worker = None
        self._set_busy(False)
        if self._dirty and self._model_key() == 'none' and self.live_check.isChecked():
            self._timer.start()          # während der Rechnung geänderte Einstellungen

    def _cancel_gift(self):
        if self._worker is not None:
            self._worker.cancel()

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait(10000)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Unsicherheit (DREAM)
    # ------------------------------------------------------------------

    def _prior_rows(self):
        model = get_model(self._model_key())
        rows = [(p.name, p.label, p.unit, p.lower, p.upper, p.decimals) for p in model.params]
        rows.append((LOG_LAMBDA, 'log₁₀ λ_rel', '', -30.0, 4.0, 2))
        rows.append((DMAX, 'Dmax', 'nm', 0.1, 1e5, 2))
        return rows

    def _rebuild_prior_grid(self):
        while self.prior_grid.count():
            item = self.prior_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.prior_widgets = {}
        for col, text in enumerate(('', tr('gift.dream_col_sample'), tr('gift.param_lower'),
                                    tr('gift.param_upper'), 'μ', 'σ')):
            self.prior_grid.addWidget(QLabel(f"<i>{text}</i>"), 0, col)
        for row, (name, label, unit, lo, hi, dec) in enumerate(self._prior_rows(), start=1):
            self.prior_grid.addWidget(QLabel(label + (f" / {unit}" if unit else '')), row, 0)
            w = {'use': QCheckBox()}
            self.prior_grid.addWidget(w['use'], row, 1)
            for col, key in enumerate(('lower', 'upper', 'mu', 'sd'), start=2):
                spin = QDoubleSpinBox()
                spin.setDecimals(dec)
                spin.setRange(0.0 if key == 'sd' else lo, (hi - lo) if key == 'sd' else hi)
                spin.setSingleStep(10 ** -max(dec - 1, 0))
                if key == 'sd':
                    spin.setSpecialValueText('–')
                if key in ('mu', 'sd'):
                    spin.setToolTip(tr('gift.dream_gauss_tooltip'))
                self.prior_grid.addWidget(spin, row, col)
                w[key] = spin
            self.prior_widgets[name] = w
        self._prior_edited = False
        self._set_prior_defaults(force=True)
        for w in self.prior_widgets.values():
            w['use'].toggled.connect(self._on_prior_edited)
            for key in ('lower', 'upper', 'mu', 'sd'):
                w[key].valueChanged.connect(self._on_prior_edited)

    def _on_prior_edited(self, *_):
        if not getattr(self, '_prior_updating', False):
            self._prior_edited = True

    def _prior_defaults(self):
        """Standard-Priorgrenzen und Referenzwerte (wie uncertainty.build_space)."""
        a = self.analysis
        out = {}
        g = a.gift if a is not None else None
        for name, _l, _u, _lo, _hi, _d in self._prior_rows():
            if name == LOG_LAMBDA:
                c = np.log10(a.solution.lam_rel) if a is not None else self.lam_spin.value()
                lo = np.log10(a.solution.scan.lam_rel[0]) if a is not None else -14.0
                out[name] = (max(c - 4.0, min(lo, -14.0)), min(c + 4.0, 4.0), c, True)
            elif name == DMAX:
                d0 = a.solution.settings.dmax if a is not None else self.dmax_spin.value()
                lo, hi = 0.75 * d0, 1.5 * d0
                if self.dream_dmax_limit_check.isChecked():
                    q_min = a.selection.q_min if a is not None else self._effective_qmin()
                    hi = min(hi, dmax_limit(q_min, self._kind()))
                    lo = min(lo, 0.5 * hi)
                out[name] = (lo, hi, d0, True)
            else:
                pw = self.param_widgets.get(name)
                free = pw is not None and not pw['fixed'].isChecked()
                if g is not None and g.model_key == self._model_key():
                    out[name] = (g.lower[name], g.upper[name], g.params[name], free)
                elif pw is not None:
                    out[name] = (pw['lower'].value(), pw['upper'].value(), pw['start'].value(),
                                 free)
        return out

    def _set_prior_defaults(self, force=False, only=None):
        if not self.prior_widgets or (self._prior_edited and not force):
            return
        self._prior_updating = True
        try:
            for name, (lo, hi, ref, use) in self._prior_defaults().items():
                if only and name not in only:
                    continue
                w = self.prior_widgets[name]
                w['lower'].setValue(lo)
                w['upper'].setValue(hi)
                if force or w['sd'].value() == 0:
                    w['mu'].setValue(ref)
                    w['sd'].setValue(0.0)
                if only is None:
                    w['use'].setChecked(use)
        finally:
            self._prior_updating = False
        if force and only is None:
            self._prior_edited = False

    def _uncertainty_settings(self):
        use = [n for n, w in self.prior_widgets.items() if w['use'].isChecked()]
        return UncertaintySettings(
            sample_params=[n for n in use if n not in (LOG_LAMBDA, DMAX)],
            sample_lambda=LOG_LAMBDA in use, sample_dmax=DMAX in use,
            lower={n: self.prior_widgets[n]['lower'].value() for n in use},
            upper={n: self.prior_widgets[n]['upper'].value() for n in use},
            gaussian={n: (self.prior_widgets[n]['mu'].value(), self.prior_widgets[n]['sd'].value())
                      for n in use if self.prior_widgets[n]['sd'].value() > 0},
            dmax_limit_upper=self.dream_dmax_limit_check.isChecked(),
            scale_sigma=self.dream_scale_sigma_check.isChecked(),
            dream=DreamSettings(n_chains=self.dream_chains_spin.value(),
                                max_evals=self.dream_budget_spin.value(),
                                seed=self.dream_seed_spin.value(),
                                r_hat_target=self.dream_rhat_spin.value()),
            n_workers=self.workers_spin.value())

    def _apply_uncertainty_settings(self, params):
        """Stellt DREAM-Einstellungen aus einem Sidecar wieder her (Aktivität 'dream')."""
        us = UncertaintySettings.from_dict(params)
        prior = params.get('prior', {})
        names = prior.get('names', [])
        self._prior_updating = True
        try:
            self.dream_dmax_limit_check.setChecked(us.dmax_limit_upper)
            self.dream_scale_sigma_check.setChecked(us.scale_sigma)
            self.dream_chains_spin.setValue(us.dream.n_chains)
            self.dream_budget_spin.setValue(us.dream.max_evals)
            self.dream_rhat_spin.setValue(us.dream.r_hat_target)
            self.dream_seed_spin.setValue(us.dream.seed)
            for n, w in self.prior_widgets.items():
                w['use'].setChecked(n in names)
                if n in names:
                    k = names.index(n)
                    w['lower'].setValue(float(prior['lower'][k]))
                    w['upper'].setValue(float(prior['upper'][k]))
                mu, sd = us.gaussian.get(n, (w['mu'].value(), 0.0))
                w['mu'].setValue(float(mu))
                w['sd'].setValue(float(sd))
        finally:
            self._prior_updating = False
        self._prior_edited = True

    def _start_dream(self, _checked=False, compare=None):
        if self._worker is not None:
            return
        if self._model_key() == 'none':
            if self._dirty or self.analysis is None:
                self.compute()
        elif self.analysis is None or self.analysis.gift is None or self._dirty:
            QMessageBox.information(self, tr('gift.dream_run'), tr('gift.need_compute'))
            return
        if self.analysis is None:
            return
        settings = self._uncertainty_settings()
        if not (settings.sample_params or settings.sample_lambda or settings.sample_dmax):
            QMessageBox.information(self, tr('gift.dream_run'), tr('gift.dream_nothing'))
            return
        self._dream_compare = compare
        self._worker = _DreamWorker(self.analysis, settings, self)
        self._worker.progress.connect(self._on_dream_progress)
        self._worker.done.connect(self._on_dream_done)
        self._worker.failed.connect(self._on_dream_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._t_start = time.perf_counter()
        self._set_busy(True)
        self.dream_status.setText(tr('gift.dream_starting'))
        self._worker.start()

    def _on_dream_progress(self, phase, n, gen, rhat, acc):
        if phase == 'screening':
            self.dream_status.setText(tr('gift.dream_screening', n=n))
        elif phase == 'predict':
            self.dream_status.setText(tr('gift.dream_predict'))
        else:
            self.dream_status.setText(tr('gift.dream_running', n=n, gen=gen,
                                         rhat='–' if not np.isfinite(rhat) else f"{rhat:.3f}",
                                         acc=f"{100 * acc:.0f}"))

    def _on_dream_done(self, analysis, result):
        if analysis is not self.analysis:
            self.dream_status.setText(tr('gift.dream_stale'))
            return
        analysis.uncertainty = result
        d = result.dream
        key = 'gift.dream_done' if d.converged else 'gift.dream_done_not_converged'
        self.dream_status.setText(tr(key, n=d.n_evals, t=f"{time.perf_counter() - self._t_start:.1f}",
                                     rhat=f"{float(np.max(d.r_hat)):.3f}"))
        self._show_results()
        self._plot_uncertainty()
        self.tabs.setCurrentWidget(self.unc_tabs)
        compare = getattr(self, '_dream_compare', None)
        self._dream_compare = None
        if compare:
            self._report_dream_reproduction(compare, result)

    def _on_dream_failed(self, message):
        self._dream_compare = None
        if message == _DreamWorker.CANCELLED:
            self.dream_status.setText(tr('gift.dream_cancelled'))
        else:
            self.dream_status.setText(
                f"<span style='color:#c62828'>{tr('gift.error')}: {message}</span>")

    def _adopt_from_dream(self):
        """λ und/oder Dmax auf den Posterior-Median der DREAM-Analyse setzen (λ manuell)."""
        u = self.analysis.uncertainty if self.analysis is not None else None
        if u is None:
            return
        lam = 10 ** u.summary[LOG_LAMBDA]['median'] if LOG_LAMBDA in u.names else None
        dmax = u.summary[DMAX]['median'] if DMAX in u.names else None
        self._set_manual(dmax=dmax, lam_rel=lam)
        self.dream_status.setText(tr('gift.dream_adopted'))

    def _open_batch(self):
        from dialogs.gift_batch_dialog import GiftBatchDialog
        dlg = GiftBatchDialog(self, self._datasets_provider() if self._datasets_provider else [])
        dlg.show()

    # ------------------------------------------------------------------
    # Explorer (Dmax × λ-Karte, 1D-Scans)
    # ------------------------------------------------------------------

    def _build_explorer_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        self.exp_mode_combo = QComboBox()
        for key in ('map', 'dmax', 'lam', 'n_splines'):
            self.exp_mode_combo.addItem(tr(f'gift.explorer_mode_{key}'), key)
        self.exp_metric_combo = QComboBox()
        for key in METRICS:
            self.exp_metric_combo.addItem(tr(f'gift.metric.{key}'), key)
        self.exp_run_btn = QPushButton(tr('gift.explorer_run'))
        self.exp_run_btn.clicked.connect(self._run_explorer)

        def dspin(lo, hi, dec, val, suffix=''):
            sp = QDoubleSpinBox()
            sp.setRange(lo, hi)
            sp.setDecimals(dec)
            sp.setValue(val)
            if suffix:
                sp.setSuffix(suffix)
            return sp

        def ispin(lo, hi, val):
            sp = QSpinBox()
            sp.setRange(lo, hi)
            sp.setValue(val)
            return sp

        self.exp_dmin_spin = dspin(0.1, 1e5, 1, 10.0, ' nm')
        self.exp_dmax_spin = dspin(0.1, 1e5, 1, 100.0, ' nm')
        self.exp_nd_spin = ispin(3, 200, 33)
        self.exp_lmin_spin = dspin(-30.0, 4.0, 1, -12.0)
        self.exp_lmax_spin = dspin(-30.0, 4.0, 1, 2.0)
        self.exp_nl_spin = ispin(3, 200, 43)
        self.exp_nmin_spin = ispin(5, 200, 10)
        self.exp_nmax_spin = ispin(5, 200, 60)
        self.exp_osc_spin = dspin(1.0, 10.0, 2, OSC_GOOD)
        self.exp_osc_spin.setToolTip(tr('gift.explorer_osc_tooltip'))
        row = 0
        grid.addWidget(QLabel(tr('gift.explorer_mode') + ':'), row, 0)
        grid.addWidget(self.exp_mode_combo, row, 1, 1, 2)
        grid.addWidget(QLabel(tr('gift.explorer_metric') + ':'), row, 3)
        grid.addWidget(self.exp_metric_combo, row, 4, 1, 2)
        grid.addWidget(self.exp_run_btn, row, 6)
        row += 1
        grid.addWidget(QLabel('Dmax:'), row, 0)
        grid.addWidget(self.exp_dmin_spin, row, 1)
        grid.addWidget(self.exp_dmax_spin, row, 2)
        grid.addWidget(QLabel(tr('gift.explorer_points') + ':'), row, 3)
        grid.addWidget(self.exp_nd_spin, row, 4)
        grid.addWidget(QLabel(tr('gift.explorer_osc') + ' ≤'), row, 5)
        grid.addWidget(self.exp_osc_spin, row, 6)
        row += 1
        grid.addWidget(QLabel('log₁₀ λ_rel:'), row, 0)
        grid.addWidget(self.exp_lmin_spin, row, 1)
        grid.addWidget(self.exp_lmax_spin, row, 2)
        grid.addWidget(QLabel(tr('gift.explorer_points') + ':'), row, 3)
        grid.addWidget(self.exp_nl_spin, row, 4)
        grid.addWidget(QLabel('N:'), row, 5)
        nbox = QHBoxLayout()
        nbox.addWidget(self.exp_nmin_spin)
        nbox.addWidget(self.exp_nmax_spin)
        grid.addLayout(nbox, row, 6)
        v.addLayout(grid)
        self.exp_status = QLabel(tr('gift.explorer_hint'))
        self.exp_status.setWordWrap(True)
        v.addWidget(self.exp_status)
        self.fig_exp = Figure(figsize=(7, 5), layout='constrained')
        self.canvas_exp = FigureCanvasQTAgg(self.fig_exp)
        v.addWidget(NavigationToolbar2QT(self.canvas_exp, w))
        v.addWidget(self.canvas_exp, 1)
        self.canvas_exp.mpl_connect('button_press_event', self._on_explorer_click)
        self.exp_metric_combo.currentIndexChanged.connect(lambda _: self._plot_explorer())
        self.exp_osc_spin.valueChanged.connect(lambda _: self._plot_explorer())
        self.tabs.addTab(w, tr('gift.tab_explorer'))
        self._exp_result = None
        self._exp_ranges_set = False
        self._exp_ax = None

    # ------------------------------------------------------------------
    # DECON (v7.15)
    # ------------------------------------------------------------------

    def _build_decon_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        grid = QGridLayout()
        self.decon_basis_combo = QComboBox()
        self.decon_basis_combo.addItem(tr('gift.decon_basis_splines'), BASIS_SPLINES)
        self.decon_basis_combo.addItem(tr('gift.decon_basis_steps'), BASIS_STEPS)
        self.decon_basis_combo.setToolTip(tr('gift.decon_basis_tooltip'))
        self.decon_n_spin = QSpinBox()
        self.decon_n_spin.setRange(0, 60)
        self.decon_n_spin.setSpecialValueText(tr('gift.decon_auto'))
        self.decon_n_spin.setValue(0)
        self.decon_n_spin.setToolTip(tr('gift.decon_n_tooltip'))
        self.decon_lam_combo = QComboBox()
        self.decon_lam_combo.addItem(tr('gift.lambda_method_inflexion'), 'auto')
        self.decon_lam_combo.addItem(tr('gift.lambda_method_manual'), 'manual')
        self.decon_lam_combo.setToolTip(tr('gift.decon_lam_tooltip'))
        self.decon_lam_spin = QDoubleSpinBox()
        self.decon_lam_spin.setRange(-10.0, 4.0)
        self.decon_lam_spin.setDecimals(2)
        self.decon_lam_spin.setValue(-3.0)
        self.decon_lam_spin.setPrefix('log₁₀ λ = ')
        self.decon_lam_spin.setEnabled(False)
        self.decon_lam_combo.currentIndexChanged.connect(
            lambda _: self.decon_lam_spin.setEnabled(self.decon_lam_combo.currentData() == 'manual'))
        self.decon_poly_combo = QComboBox()
        self.decon_poly_combo.addItem(tr('gift.decon_poly_none'), POLY_NONE)
        self.decon_poly_combo.addItem(tr('gift.decon_poly_scan'), POLY_SCAN)
        self.decon_poly_combo.addItem(tr('gift.decon_poly_fixed'), POLY_FIXED)
        self.decon_poly_combo.setToolTip(tr('gift.decon_poly_tooltip'))
        self.decon_dist_combo = QComboBox()
        self.decon_dist_combo.addItem(tr('gift.decon_dist_schulz'), DIST_SCHULZ)
        self.decon_dist_combo.addItem(tr('gift.decon_dist_gauss'), DIST_GAUSS)
        self.decon_p_spin = QDoubleSpinBox()
        self.decon_p_spin.setRange(0.0, 60.0)
        self.decon_p_spin.setDecimals(1)
        self.decon_p_spin.setSuffix(' %')
        self.decon_p_spin.setPrefix('P = ')
        self.decon_p_spin.setToolTip(tr('gift.decon_p_tooltip'))
        self.decon_p_spin.setEnabled(False)
        self.decon_poly_combo.currentIndexChanged.connect(
            lambda _: self.decon_p_spin.setEnabled(self.decon_poly_combo.currentData() == POLY_FIXED))
        self.decon_run_btn = QPushButton(tr('gift.decon_run'))
        self.decon_run_btn.setToolTip(tr('gift.decon_run_tooltip'))
        self.decon_run_btn.clicked.connect(self._run_decon)
        self.decon_steps_spin = QSpinBox()
        self.decon_steps_spin.setRange(2, 4)
        self.decon_steps_spin.setValue(2)
        self.decon_steps_btn = QPushButton(tr('gift.decon_steps_run'))
        self.decon_steps_btn.setToolTip(tr('gift.decon_steps_tooltip'))
        self.decon_steps_btn.clicked.connect(self._run_step_model)
        grid.addWidget(QLabel(tr('gift.decon_basis') + ':'), 0, 0)
        grid.addWidget(self.decon_basis_combo, 0, 1)
        grid.addWidget(QLabel(tr('gift.decon_n') + ':'), 0, 2)
        grid.addWidget(self.decon_n_spin, 0, 3)
        grid.addWidget(self.decon_lam_combo, 0, 4)
        grid.addWidget(self.decon_lam_spin, 0, 5)
        grid.addWidget(QLabel(tr('gift.decon_poly') + ':'), 1, 0)
        grid.addWidget(self.decon_poly_combo, 1, 1)
        grid.addWidget(self.decon_dist_combo, 1, 2, 1, 2)
        grid.addWidget(self.decon_p_spin, 1, 4)
        grid.addWidget(self.decon_run_btn, 1, 5)
        grid.addWidget(QLabel(tr('gift.decon_steps') + ':'), 2, 0)
        grid.addWidget(self.decon_steps_spin, 2, 1)
        grid.addWidget(self.decon_steps_btn, 2, 2, 1, 2)
        v.addLayout(grid)
        self.decon_status = QLabel(tr('gift.decon_hint'))
        self.decon_status.setWordWrap(True)
        self.decon_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.decon_status)
        self.fig_decon = Figure(figsize=(7, 6), layout='constrained')
        self.canvas_decon = FigureCanvasQTAgg(self.fig_decon)
        v.addWidget(NavigationToolbar2QT(self.canvas_decon, w))
        v.addWidget(self.canvas_decon, 1)
        self.tabs.addTab(w, tr('gift.tab_decon'))

    def _decon_settings(self):
        manual = self.decon_lam_combo.currentData() == 'manual'
        return DeconSettings(
            basis=self.decon_basis_combo.currentData(),
            n_intervals=self.decon_n_spin.value() or None,
            lam=10 ** self.decon_lam_spin.value() if manual else 'auto',
            polydispersity=self.decon_poly_combo.currentData(),
            distribution=self.decon_dist_combo.currentData(),
            sigma=self.decon_p_spin.value() / 100.0 / DECON_HWHM)

    def _start_decon_worker(self, task, **kw):
        a = self.analysis
        if a is None or self._worker is not None:
            return
        if a.solution.settings.kind not in DECON_GEOMETRIES:
            QMessageBox.information(self, tr('gift.tab_decon'), tr('gift.decon_not_available'))
            return
        self._worker = _DeconWorker(a, task, kw, self)
        self._worker.progress.connect(self._on_decon_progress)
        self._worker.done.connect(self._on_decon_done)
        self._worker.failed.connect(self._on_decon_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._t_start = time.perf_counter()
        self._set_busy(True)
        self.decon_run_btn.setEnabled(False)
        self.decon_steps_btn.setEnabled(False)
        self.decon_status.setText(tr('gift.decon_running'))
        self._worker.start()

    def _run_decon(self):
        self._start_decon_worker('profile', settings=self._decon_settings())

    def _run_step_model(self):
        if self.analysis is None or self.analysis.decon is None:
            QMessageBox.information(self, tr('gift.tab_decon'), tr('gift.decon_need_profile'))
            return
        self._start_decon_worker('steps', n_steps=self.decon_steps_spin.value())

    def _on_decon_progress(self, j, n):
        self.decon_status.setText(tr('gift.decon_scan_running', j=j + 1, n=n))

    def _on_decon_done(self, analysis, task, result):
        if analysis is not self.analysis:
            return
        if task == 'profile' and self.decon_lam_combo.currentData() != 'manual':
            self._updating = True
            self.decon_lam_spin.setValue(np.log10(result.lam_rel))
            self._updating = False
        self._show_results()
        self._plot_decon()
        self._show_provenance()

    def _on_decon_failed(self, message):
        text = tr('gift.decon_cancelled') if message == _DeconWorker.CANCELLED else \
            f"<span style='color:#c62828'>{tr('gift.error')}: {message}</span>"
        self.decon_status.setText(text)

    def _plot_decon(self):
        fig = self.fig_decon
        fig.clear()
        a = self.analysis
        d = a.decon if a is not None else None
        available = a is not None and a.solution.settings.kind in DECON_GEOMETRIES
        idle = self._worker is None
        self.decon_run_btn.setEnabled(available and idle)
        self.decon_steps_btn.setEnabled(available and idle and d is not None)
        if d is None:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, tr('gift.decon_hint') if available else
                    tr('gift.decon_not_available'), ha='center', va='center', wrap=True,
                    transform=ax.transAxes)
            ax.set_axis_off()
            self.canvas_decon.draw_idle()
            if available:
                self.decon_status.setText(tr('gift.decon_hint'))
            return
        s = a.solution
        lab = LABELS[s.settings.kind]
        ax = fig.add_subplot(2, 2, (1, 2))
        drawstyle = 'steps-post' if d.settings.basis == BASIS_STEPS else 'default'
        ax.plot(d.x, d.rho, '-', color=_CLR_FIT, lw=1.8, label=tr('gift.decon_profile'))
        ax.fill_between(d.x, d.rho - d.rho_err, d.rho + d.rho_err, color=_CLR_FIT, alpha=0.25,
                        lw=0, label='± σ')
        for i, alt in enumerate(d.alternatives):
            ax.plot(d.x, alt['rho'], '--', lw=1.1,
                    label=f"{tr('gift.decon_alternative')} {i + 1} (χ² = {alt['chi2_red']:.3g})")
        sm = d.step_model
        if sm is not None:
            ax.plot(sm['x'], sm['rho'], '-', color='#6a1b9a', lw=1.4, drawstyle=drawstyle,
                    label=tr('gift.decon_step_label', n=len(sm['edges']),
                             edges=', '.join(f"{e:.3g}" for e in sm['edges'])))
        ax.axhline(0, color='k', lw=0.8)
        xlab = {'sphere': 'r', 'cylinder': 'r', 'lamella': 'x'}[d.geometry]
        ax.set_xlabel(f"{xlab} / nm")
        ax.set_ylabel('Δρ (rel.)')
        ax.legend(fontsize=7)
        ax2 = fig.add_subplot(2, 2, 3)
        ax2.plot(d.r, d.p_target, 'o', ms=2.5, color=_CLR_DATA, label=f"{lab['f']} (IFT)")
        ax2.plot(d.r, d.p_fit, '-', color=_CLR_FIT, lw=1.3, label='DECON')
        ax2.axhline(0, color='k', lw=0.6)
        ax2.set_xlabel('r / nm')
        ax2.set_ylabel(lab['f'])
        ax2.legend(fontsize=7)
        ax3 = fig.add_subplot(2, 2, 4)
        if d.poly_scan is not None:
            ps = d.poly_scan
            ax3.plot(100 * ps['P'], ps['md_pr'], 'o-', ms=3, color=_CLR_FIT, label='MD(p)')
            ax3.axvline(d.p_percent, color='#ff9800', lw=1.2)
            ax3.set_xlabel(tr('gift.decon_p_axis'))
            ax3.set_ylabel('MD')
            ax3.set_yscale('log')
            ax3.legend(fontsize=7)
        else:
            ax3.plot(s.q, s.i_fit, '-', color='k', lw=0.9, label='IFT')
            ax3.plot(d.q, np.maximum(d.i_model, 1e-300), '-', color=_CLR_FIT, lw=1.3,
                     label='DECON')
            if sm is not None:
                ax3.plot(d.q, np.maximum(sm['i_model'], 1e-300), '-', color='#6a1b9a', lw=1.0,
                         label=tr('gift.decon_steps'))
            ax3.set_xscale('log')
            ax3.set_yscale('log')
            ax3.set_xlabel('q / nm⁻¹')
            ax3.set_ylabel('I(q)')
            ax3.legend(fontsize=7, loc='lower left')
        poly = (tr('gift.decon_status_poly', p=f"{d.p_percent:.0f}", sigma=f"{d.sigma_poly:.3f}")
                if d.settings.polydispersity != POLY_NONE else tr('gift.decon_status_mono'))
        text = tr('gift.decon_status', geometry=tr(f'gift.decon_geom.{d.geometry}'),
                  R=f"{d.radius:.4g}", md=f"{d.md_pr:.3g}", md_q=f"{d.md_q:.3g}",
                  lam=f"{d.lam_rel:.2g}", n=len(d.alternatives), poly=poly)
        if sm is not None:
            text += " " + tr('gift.decon_status_steps',
                             edges=', '.join(f"{e:.4g}" for e in sm['edges']),
                             heights=', '.join(f"{h:.3g}" for h in sm['heights']),
                             md=f"{sm['md_pr']:.3g}")
        self.decon_status.setText(text)
        self.canvas_decon.draw_idle()

    def _set_explorer_ranges(self, force=False):
        if self.analysis is None or (self._exp_ranges_set and not force):
            return
        s = self.analysis.solution
        d0 = s.settings.dmax
        limit = dmax_limit(self.analysis.selection.q_min, s.settings.kind)
        self.exp_dmin_spin.setValue(float(f"{0.5 * min(d0, limit):.3g}"))
        self.exp_dmax_spin.setValue(float(f"{2.5 * max(d0, limit):.3g}"))
        self.exp_nmin_spin.setValue(max(5, s.settings.n_splines // 3))
        lo = np.floor(min(np.log10(s.lam_rel), np.log10(s.scan.lam_rel[s.scan.index_evidence]))) - 4
        self.exp_lmin_spin.setValue(float(min(-12.0, max(lo, -30.0))))
        self.exp_lmax_spin.setValue(2.0)
        self.exp_nmax_spin.setValue(min(200, 3 * s.settings.n_splines))
        self._exp_ranges_set = True

    def _run_explorer(self):
        a = self.analysis
        if a is None:
            return
        s = a.solution
        sf = a.gift.structure_factor if a.gift is not None else None
        mode = self.exp_mode_combo.currentData()
        st = s.settings
        QApplication.setOverrideCursor(Qt.WaitCursor)
        t0 = time.perf_counter()
        try:
            if mode == 'map':
                res = scan_map(s.q, s.intensity, s.sigma, st,
                               np.linspace(self.exp_dmin_spin.value(), self.exp_dmax_spin.value(),
                                           self.exp_nd_spin.value()),
                               np.logspace(self.exp_lmin_spin.value(), self.exp_lmax_spin.value(),
                                           self.exp_nl_spin.value()),
                               structure_factor=sf)
            elif mode == 'dmax':
                res = scan_1d(s.q, s.intensity, s.sigma, st, 'dmax',
                              np.linspace(self.exp_dmin_spin.value(), self.exp_dmax_spin.value(),
                                          self.exp_nd_spin.value()), structure_factor=sf)
            elif mode == 'lam':
                res = scan_1d(s.q, s.intensity, s.sigma, st, 'lam',
                              np.logspace(self.exp_lmin_spin.value(), self.exp_lmax_spin.value(),
                                          self.exp_nl_spin.value()), structure_factor=sf)
            else:
                lo, hi = sorted((self.exp_nmin_spin.value(), self.exp_nmax_spin.value()))
                res = scan_1d(s.q, s.intensity, s.sigma, st, 'n_splines',
                              np.unique(np.linspace(lo, hi, min(hi - lo + 1, 30)).round()),
                              structure_factor=sf)
        except (ValueError, np.linalg.LinAlgError) as e:
            self.exp_status.setText(f"<span style='color:#c62828'>{tr('gift.error')}: {e}</span>")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._exp_result = (mode, res, a)
        self.exp_status.setText(tr('gift.explorer_done', t=f"{time.perf_counter() - t0:.2f}")
                                + ' ' + tr('gift.explorer_hint'))
        self._plot_explorer()

    def _plot_explorer(self):
        fig = self.fig_exp
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            fig.clear()
        self._exp_ax = None
        if self._exp_result is None:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, tr('gift.explorer_empty'), ha='center', va='center',
                    transform=ax.transAxes, wrap=True)
            ax.set_axis_off()
            self.canvas_exp.draw_idle()
            return
        mode, res, a = self._exp_result
        stale = self._explorer_stale(a)
        if self.analysis is not None:
            a_cur = self.analysis
        else:
            a_cur = a
        key = self.exp_metric_combo.currentData()
        label = tr(f'gift.metric.{key}')
        osc_max = self.exp_osc_spin.value()
        s = a_cur.solution
        log_keys = ('oscillation', 'md', 'chi2_dof')
        ax = fig.add_subplot(111)
        self._exp_ax = ax
        if mode == 'map':
            Z = np.asarray(res.metrics[key], dtype=float)
            if key in log_keys:
                Z = np.log10(np.where(Z > 0, Z, np.nan))
                label = 'log₁₀ ' + label
            elif key == 'log_evidence':
                Z = np.maximum(Z - np.nanmax(Z), -100.0)
                label = tr('gift.lambda_evidence_axis')
            L = np.log10(res.lam_rel)
            extent = [res.dmax[0], res.dmax[-1], L[0], L[-1]]
            cmap = 'magma_r' if key == 'oscillation' else 'viridis'
            im = ax.imshow(Z, origin='lower', aspect='auto', extent=extent, cmap=cmap,
                           interpolation='nearest')
            fig.colorbar(im, ax=ax, label=label)
            good = res.good_region(osc_max=osc_max)
            if good.any() and not good.all():
                ax.contour(res.dmax, L, good.astype(float), levels=[0.5], colors='lime',
                           linewidths=1.5)
            li = np.log10(res.lam_inflexion)
            ax.plot(res.dmax, li, '-', color='w', lw=1.4, label=tr('gift.lambda_method_inflexion'))
            nf = ~res.inflexion_found
            if nf.any():
                ax.plot(res.dmax[nf], li[nf], 'x', color='#c62828', ms=6,
                        label=tr('gift.explorer_no_inflexion'))
            ax.plot(res.dmax, np.log10(res.lam_evidence), ':', color='cyan', lw=1.4,
                    label=tr('gift.lambda_method_evidence'))
            ax.axvline(dmax_limit(res.q_min, s.settings.kind), color='#00bcd4', ls='--',
                       lw=1.0, label='π/q_min')
            ax.plot(s.settings.dmax, np.log10(s.lam_rel), '*', color='#ff9800', ms=14,
                    mec='k', label=tr('gift.explorer_current'))
            ax.set_xlim(extent[0], extent[1])
            ax.set_ylim(extent[2], extent[3])
            ax.set_xlabel('Dmax / nm')
            ax.set_ylabel('log₁₀ λ_rel')
            ax.legend(fontsize=7, loc='lower right', framealpha=0.7)
            ax.set_title(tr('gift.explorer_map_title'), fontsize=9)
        else:
            m = res.metrics
            x = np.log10(res.values) if mode == 'lam' else res.values
            y = np.asarray(m[key], dtype=float)
            if key == 'log_evidence':
                y = y - np.nanmax(y)
                label = tr('gift.lambda_evidence_axis')
            ax.plot(x, y, 'o-', color=_CLR_DATA, ms=4, lw=1.2)
            smooth = _physical(m) & (m['oscillation'] <= osc_max)
            good = smooth & md_acceptable(m['md'], len(s.q), reference=smooth)
            ax.plot(x[good], y[good], 'o', color='lime', mec='#2e7d32', ms=7,
                    label=tr('gift.explorer_good'))
            if key in log_keys:
                ax.set_yscale('log')
            if mode == 'dmax':
                ax.axvline(dmax_limit(a.selection.q_min, s.settings.kind), color='#00bcd4',
                           ls='--', lw=1.0, label='π/q_min')
                ax.axvline(s.settings.dmax, color='#ff9800', lw=1.5,
                           label=tr('gift.explorer_current'))
                ax.set_xlabel('Dmax / nm')
            elif mode == 'lam':
                ax.axvline(np.log10(res.lam_inflexion[0]), color='k', ls='--', lw=1.0,
                           label=tr('gift.lambda_method_inflexion'))
                ax.axvline(np.log10(res.lam_evidence[0]), color='#2e7d32', ls=':', lw=1.4,
                           label=tr('gift.lambda_method_evidence'))
                ax.axvline(np.log10(s.lam_rel), color='#ff9800', lw=1.5,
                           label=tr('gift.explorer_current'))
                ax.set_xlabel('log₁₀ λ_rel')
            else:
                ax.axvline(s.settings.n_splines, color='#ff9800', lw=1.5,
                           label=tr('gift.explorer_current'))
                ax.set_xlabel(tr('gift.nsplines'))
            ax.set_ylabel(label)
            ax.legend(fontsize=7)
            ax.set_title(tr(f'gift.explorer_mode_{mode}'), fontsize=9)
        if stale:
            ax.set_title(ax.get_title() + '  —  ' + tr('gift.explorer_stale'), fontsize=9,
                         color='#c62828')
        self.canvas_exp.draw_idle()

    def _explorer_stale(self, a):
        """Hängt die Karte von geänderten Einstellungen ab (q-Bereich, N, K, Untergrund,
        S(q))? Dmax und λ selbst sind die Achsen und machen sie nicht ungültig."""
        b = self.analysis
        if b is None or b is a:
            return False
        sa, sb = a.solution, b.solution
        if len(sa.q) != len(sb.q) or not np.array_equal(sa.q, sb.q):
            return True
        if (sa.settings.n_splines, sa.settings.k_type, sa.settings.background) !=                 (sb.settings.n_splines, sb.settings.k_type, sb.settings.background):
            return True
        fa = a.gift.structure_factor if a.gift is not None else None
        fb = b.gift.structure_factor if b.gift is not None else None
        return not ((fa is None and fb is None) or
                    (fa is not None and fb is not None and np.array_equal(fa, fb)))

    def _on_explorer_click(self, event):
        if self._exp_ax is None or event.inaxes is not self._exp_ax or event.xdata is None:
            return
        if self.canvas_exp.toolbar is not None and self.canvas_exp.toolbar.mode:
            return                           # Zoom/Pan aktiv
        mode = self._exp_result[0]
        if mode == 'map':
            self._set_manual(dmax=event.xdata, lam_rel=10 ** event.ydata)
        elif mode == 'dmax':
            self._set_manual(dmax=event.xdata)
        elif mode == 'lam':
            self._set_manual(lam_rel=10 ** event.xdata)
        else:
            self._set_manual(n_splines=int(round(event.xdata)))
        self.exp_status.setText(tr('gift.explorer_adopted'))

    def _report_dream_reproduction(self, old, result):
        lines = []
        for n in result.names:
            o = old.get(n, {}).get('median')
            new = result.summary[n]['median']
            if o is not None:
                lines.append(f"{result.labels[n]}: {o:.5g} → {new:.5g}")
        QMessageBox.information(self, tr('gift.load_sidecar'),
                                tr('gift.dream_reproduced', lines="\n".join(lines) or '–'))

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------

    def _plot_all(self):
        self._plot_iq()
        self._plot_pr()
        self._plot_sq()
        self._plot_lambda()
        self._plot_significance()
        self._plot_bssa()
        self._plot_uncertainty()
        self._plot_explorer()
        self._plot_decon()

    def _no_gift_text(self, fig, canvas):
        fig.clear()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, tr('gift.only_gift'), ha='center', va='center',
                transform=ax.transAxes)
        ax.set_axis_off()
        canvas.draw_idle()

    def _plot_sq(self):
        g = self.analysis.gift
        if g is None:
            self._no_gift_text(self.fig_sq, self.canvas_sq)
            return
        s = g.solution
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.fig_sq.clear()
        ax1 = self.fig_sq.add_subplot(211)
        ax1.plot(s.q, g.structure_factor, '-', color='#2e7d32', lw=1.6)
        ax1.axhline(1.0, color='k', lw=0.6, ls=':')
        ax1.set_xscale('log')
        ax1.set_ylabel('S(q)')
        ax1.set_title(tr(get_model(g.model_key).label_key), fontsize=9)
        ax2 = self.fig_sq.add_subplot(212, sharex=ax1)
        pos = s.intensity > 0
        ax2.plot(s.q[pos], s.intensity[pos], 'o', ms=2.5, color=_CLR_DATA, alpha=0.6,
                 label=tr('gift.legend_data'))
        ax2.plot(s.q, s.i_fit, '-', color=_CLR_FIT, lw=1.4, label='I = S·P')
        pq = g.form_factor
        ax2.plot(s.q[pq > 0], pq[pq > 0], '--', color='#6a1b9a', lw=1.4, label='P(q)')
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.set_xlabel('q / nm⁻¹')
        ax2.set_ylabel('I(q), P(q)')
        ax2.legend(fontsize=8, loc='lower left')
        self.canvas_sq.draw_idle()

    def _plot_bssa(self):
        g = self.analysis.gift
        if g is None or not g.history:
            self._no_gift_text(self.fig_bssa, self.canvas_bssa)
            return
        model = get_model(g.model_key)
        h = g.history
        ev = np.array([x['evals'] for x in h])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.fig_bssa.clear()
        ax1 = self.fig_bssa.add_subplot(211)
        ax1.semilogy(ev, [x['md'] for x in h], '-', color=_CLR_FIT, label='MD')
        ax1.set_ylabel(tr('gift.md_axis'), color=_CLR_FIT)
        temps = np.array([x['T'] for x in h])
        ax1b = ax1.twinx()
        ax1b.semilogy(ev[temps > 0], temps[temps > 0], '--', color='#555555', label='T')
        ax1b.set_ylabel('T', color='#555555')
        ax1.set_title(tr('gift.bssa_title', evals=g.n_evals), fontsize=9)
        ax2 = self.fig_bssa.add_subplot(212, sharex=ax1)
        for p in model.params:
            if p.name not in g.free:
                continue
            lo, hi = g.lower[p.name], g.upper[p.name]
            vals = np.array([x['params'][p.name] for x in h])
            ax2.plot(ev, (vals - lo) / (hi - lo), '-', lw=1.2, label=p.label)
        ax2.set_ylim(-0.05, 1.05)
        ax2.set_xlabel(tr('gift.bssa_evals'))
        ax2.set_ylabel(tr('gift.bssa_normalized'))
        ax2.legend(fontsize=8)
        self.canvas_bssa.draw_idle()

    def _plot_uncertainty(self):
        u = self.analysis.uncertainty if self.analysis is not None else None
        figs = ((self.fig_corner, self.canvas_corner), (self.fig_trace, self.canvas_trace),
                (self.fig_band, self.canvas_band))
        if u is None:
            self.dream_adopt_btn.setEnabled(False)
            self.unc_info.setText(tr('gift.dream_not_run'))
            self.unc_table.setRowCount(0)
            for fig, canvas in figs:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    fig.clear()
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, tr('gift.dream_not_run'), ha='center', va='center',
                        transform=ax.transAxes, wrap=True)
                ax.set_axis_off()
                canvas.draw_idle()
            return
        self._show_uncertainty_table(u)
        self._plot_corner(u)
        self._plot_traces(u)
        self._plot_bands(u)

    def _axis_label(self, u, n):
        return u.labels[n] + (f" / {u.units[n]}" if u.units[n] else '')

    def _show_uncertainty_table(self, u):
        self.dream_adopt_btn.setEnabled(bool({LOG_LAMBDA, DMAX} & set(u.names)))
        d = u.dream
        self.unc_info.setText(tr(
            'gift.dream_info', evals=d.n_evals, gens=d.n_generations, chains=d.chains.shape[1],
            burn=d.burn_in, samples=(d.n_generations + 1 - d.burn_in) * d.chains.shape[1],
            acc=f"{100 * d.acceptance_rate:.0f}", rhat=f"{float(np.max(d.r_hat)):.3f}",
            t=f"{u.runtime_s:.1f}", rg=f"{u.rg['median']:.4g} [{u.rg['q2.5']:.4g}, "
                                      f"{u.rg['q97.5']:.4g}]",
            i0=f"{u.i0['median']:.4g} [{u.i0['q2.5']:.4g}, {u.i0['q97.5']:.4g}]",
            workers=u.n_workers))
        self.unc_table.setRowCount(len(u.names))
        for i, n in enumerate(u.names):
            sm = u.summary[n]
            rh = float(d.r_hat[i])
            cells = [self._axis_label(u, n), f"{sm['reference']:.5g}", f"{sm['median']:.5g}",
                     f"{sm['q16']:.4g} … {sm['q84']:.4g}", f"{sm['q2.5']:.4g} … {sm['q97.5']:.4g}",
                     f"{rh:.3f}", f"{sm['map']:.5g}"]
            for j, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if j == 5 and not rh < d.settings.r_hat_target:
                    item.setForeground(QBrush(QColor(_LEVEL_STYLE[LEVEL_WARNING][1])))
                if j == 1 and not sm['q2.5'] <= sm['reference'] <= sm['q97.5']:
                    item.setForeground(QBrush(QColor(_LEVEL_STYLE[LEVEL_INFO][1])))
                self.unc_table.setItem(i, j, item)

    def _plot_corner(self, u):
        fig = self.fig_corner
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            fig.clear()
        x, _ = u.dream.posterior()
        if len(x) > 6000:
            x = x[np.linspace(0, len(x) - 1, 6000).astype(int)]
        names = u.names
        d = len(names)
        axes = fig.subplots(d, d, squeeze=False)
        fig.subplots_adjust(left=0.1, right=0.98, bottom=0.1, top=0.97, wspace=0.08, hspace=0.08)
        for i in range(d):
            for j in range(d):
                ax = axes[i][j]
                if j > i:
                    ax.set_visible(False)
                    continue
                if i == j:
                    ax.hist(x[:, i], bins=40, color=_CLR_DATA, alpha=0.75)
                    sm = u.summary[names[i]]
                    for q_ in (sm['q2.5'], sm['q97.5']):
                        ax.axvline(q_, color='k', ls=':', lw=0.8)
                    ax.axvline(sm['median'], color='k', lw=1.0)
                    ax.axvline(sm['reference'], color=_CLR_FIT, ls='--', lw=1.0)
                    ax.set_yticks([])
                else:
                    ax.hist2d(x[:, j], x[:, i], bins=40, cmap='Blues')
                    ax.plot(u.summary[names[j]]['reference'], u.summary[names[i]]['reference'],
                            'x', color=_CLR_FIT, ms=7, mew=1.5)
                    if j > 0:
                        ax.tick_params(labelleft=False)
                if i < d - 1:
                    ax.tick_params(labelbottom=False)
                else:
                    ax.set_xlabel(self._axis_label(u, names[j]), fontsize=8)
                if j == 0 and i > 0:
                    ax.set_ylabel(self._axis_label(u, names[i]), fontsize=8)
                ax.tick_params(labelsize=7)
                for label in ax.get_xticklabels():
                    label.set_rotation(45)
        fig.text(0.98, 0.97, tr('gift.dream_corner_legend'), ha='right', va='top', fontsize=8)
        self.canvas_corner.draw_idle()

    def _plot_traces(self, u):
        fig = self.fig_trace
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            fig.clear()
        d = u.dream
        g = np.arange(d.chains.shape[0])
        n = len(u.names)
        axes = fig.subplots(n + 1, 1, sharex=True, squeeze=False)[:, 0]
        lp = np.where(np.isfinite(d.log_p), d.log_p, np.nan)
        axes[0].plot(g, lp, lw=0.5)
        post = lp[d.burn_in:]
        if np.isfinite(post).any():
            lo_ = np.nanpercentile(post, 0.5)
            hi_ = np.nanmax(post)
            axes[0].set_ylim(lo_ - 0.5 * (hi_ - lo_ + 1), hi_ + 0.1 * (hi_ - lo_ + 1))
        axes[0].set_ylabel('log p', fontsize=8)
        for k, name in enumerate(u.names):
            ax = axes[k + 1]
            ax.plot(g, d.chains[:, :, k], lw=0.5)
            ax.axhline(u.reference[name], color=_CLR_FIT, ls='--', lw=0.8)
            ax.set_ylabel(u.labels[name], fontsize=8)
        for ax in axes:
            ax.axvspan(0, d.burn_in, color=_CLR_EXCL, alpha=0.3, lw=0)
            ax.tick_params(labelsize=7)
        axes[-1].set_xlabel(tr('gift.dream_generation'))
        axes[0].set_title(tr('gift.dream_trace_title'), fontsize=9)
        self.canvas_trace.draw_idle()

    def _plot_bands(self, u):
        fig = self.fig_band
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            fig.clear()
        b = u.bands
        s = self.analysis.solution
        gift = self.analysis.gift is not None
        n_rows = 3 if gift else 2
        ax = fig.add_subplot(n_rows, 1, 1)
        pr = b['pr']
        ax.fill_between(b['r'], pr[0], pr[4], color=_CLR_FIT, alpha=0.18, lw=0, label='95 %')
        ax.fill_between(b['r'], pr[1], pr[3], color=_CLR_FIT, alpha=0.35, lw=0, label='68 %')
        ax.plot(b['r'], pr[2], '-', color=_CLR_FIT, lw=1.5, label=tr('gift.dream_median'))
        ax.plot(s.r, s.pr, '--', color='k', lw=1.0, label=tr('gift.dream_point_estimate'))
        ax.axhline(0, color='k', lw=0.6)
        lab = LABELS[s.settings.kind]
        ax.set_xlabel(f"{lab['x']} / nm")
        ax.set_ylabel(lab['f'])
        ax.legend(fontsize=7)
        ax2 = fig.add_subplot(n_rows, 1, 2)
        pos = s.intensity > 0
        ax2.plot(s.q[pos], s.intensity[pos], 'o', ms=2.5, color=_CLR_DATA, alpha=0.6,
                 label=tr('gift.legend_data'))
        fi = b['i_fit']
        ax2.fill_between(b['q'], np.maximum(fi[0], 1e-300), fi[4], color=_CLR_FIT, alpha=0.3,
                         lw=0, label='95 %')
        ax2.plot(b['q'], fi[2], '-', color=_CLR_FIT, lw=1.2, label=tr('gift.dream_median'))
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.set_xlabel('q / nm⁻¹')
        ax2.set_ylabel('I(q)')
        ax2.legend(fontsize=7, loc='lower left')
        if gift:
            ax3 = fig.add_subplot(n_rows, 1, 3, sharex=ax2)
            sq = b['sq']
            ax3.fill_between(b['q'], sq[0], sq[4], color='#2e7d32', alpha=0.2, lw=0)
            ax3.fill_between(b['q'], sq[1], sq[3], color='#2e7d32', alpha=0.35, lw=0)
            ax3.plot(b['q'], sq[2], '-', color='#2e7d32', lw=1.2)
            ax3.plot(s.q, self.analysis.gift.structure_factor, '--', color='k', lw=0.8)
            ax3.axhline(1.0, color='k', lw=0.5, ls=':')
            ax3.set_xscale('log')
            ax3.set_xlabel('q / nm⁻¹')
            ax3.set_ylabel('S(q)')
        self.canvas_band.draw_idle()

    def _shade_excluded(self, ax, sel):
        q, _, _ = self._current_arrays()
        if sel.q_min > q[0]:
            ax.axvspan(q[0] * 0.95, sel.q_min, color=_CLR_EXCL, alpha=0.25, lw=0)
        if sel.q_max < q[-1]:
            ax.axvspan(sel.q_max, q[-1] * 1.05, color=_CLR_EXCL, alpha=0.25, lw=0)

    def _plot_iq(self):
        a = self.analysis
        s = a.solution
        q, I, _ = self._current_arrays()
        sig = self._sigma_for_display(q, I)
        with warnings.catch_warnings():
            # Beim Leeren geteilter log-Achsen meldet matplotlib harmlose xlim-Warnungen
            warnings.simplefilter('ignore', UserWarning)
            self.fig_iq.clear()
        gs = self.fig_iq.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05, left=0.11,
                                      right=0.97, top=0.97, bottom=0.1)
        ax = self.fig_iq.add_subplot(gs[0])
        axr = self.fig_iq.add_subplot(gs[1], sharex=ax)
        inside = a.selection.mask(q)
        pos = I > 0
        ax.errorbar(q[inside & pos], I[inside & pos], yerr=sig[inside & pos], fmt='o', ms=3,
                    color=_CLR_DATA, ecolor=_CLR_DATA, alpha=0.7, elinewidth=0.6,
                    label=tr('gift.legend_data'))
        ax.plot(q[~inside & pos], I[~inside & pos], 'o', ms=3, color=_CLR_EXCL,
                label=tr('gift.legend_excluded'))
        ax.plot(s.q, s.i_fit, '-', color=_CLR_FIT, lw=1.6, label=tr('gift.legend_fit'))
        ax.fill_between(s.q, s.i_fit - s.i_fit_err, s.i_fit + s.i_fit_err, color=_CLR_FIT,
                        alpha=0.2, lw=0)
        self._shade_excluded(ax, a.selection)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_ylabel('I(q)')
        ax.legend(fontsize=8, loc='lower left')
        ax.tick_params(labelbottom=False)
        resid = (s.intensity - s.i_fit) / s.sigma
        axr.plot(s.q, resid, '.', ms=3, color=_CLR_DATA)
        axr.axhline(0, color='k', lw=0.8)
        for lvl in (-2, 2):
            axr.axhline(lvl, color='k', lw=0.6, ls='--')
        axr.set_xscale('log')
        axr.set_xlabel('q / nm⁻¹')
        axr.set_ylabel('ΔI/σ')
        self.canvas_iq.draw_idle()

    def _plot_pr(self):
        a = self.analysis
        s = a.solution
        self.fig_pr.clear()
        ax = self.fig_pr.add_subplot(111)
        kind = s.settings.kind
        lab = LABELS[kind]
        ax.plot(s.r, s.pr, '-', color=_CLR_FIT, lw=1.8, label=lab['f'])
        ax.fill_between(s.r, s.pr - s.pr_err, s.pr + s.pr_err, color=_CLR_FIT, alpha=0.25, lw=0,
                        label='± σ')
        z = a.extras.get('size_statistics')
        if z is not None:
            # abgeleitete Verteilungen, auf das Maximum der Primärgröße skaliert
            top = float(np.max(s.pr)) if np.max(s.pr) > 0 else 1.0
            for (name, arr), style, color in zip(z['derived'].items(), ('--', ':'),
                                                 ('#6a1b9a', '#2e7d32')):
                ax.plot(z['R'], top * arr, style, color=color, lw=1.4, label=f"{name} (norm.)")
        ax.axhline(0, color='k', lw=0.8)
        ax.axvline(s.settings.dmax, color='k', ls='--', lw=0.8,
                   label=tr(f'gift.dmax_label.{kind}'))
        limit = dmax_limit(a.selection.q_min, kind)
        if limit <= 1.3 * s.settings.dmax:
            ax.axvline(limit, color='#c62828', ls=':', lw=1.0,
                       label='π/(2q_min)' if get_kernel(kind).span == 2 else 'π/q_min')
        ax.set_xlabel(f"{lab['x']} / nm")
        ax.set_ylabel(lab['f'])
        ax.set_xlim(0, max(s.settings.dmax, 0) * 1.05)
        ax.legend(fontsize=8)
        self.canvas_pr.draw_idle()

    def _plot_lambda(self):
        sc = self.analysis.solution.scan
        s = self.analysis.solution
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.fig_lam.clear()
        ax = self.fig_lam.add_subplot(211)
        x = np.log10(sc.lam_rel)
        ax.plot(x, np.log10(sc.nc), '-', color=_CLR_DATA, label='log N_c')
        ax.set_ylabel('log₁₀ N_c', color=_CLR_DATA)
        ax2 = ax.twinx()
        ax2.plot(x, sc.md, '-', color=_CLR_FIT, label='MD')
        ax2.set_yscale('log')
        ax2.set_ylabel(tr('gift.md_axis'), color=_CLR_FIT)
        ax.set_title(tr('gift.lambda_title'), fontsize=10)
        ax3 = self.fig_lam.add_subplot(212, sharex=ax)
        if sc.log_evidence is not None:
            ev = sc.log_evidence - np.max(sc.log_evidence)
            ax3.plot(x, np.maximum(ev, -200), '-', color='#2e7d32')
            ax3.set_ylim(max(-200, np.min(ev)) - 5, 5)
            ax3.set_ylabel(tr('gift.lambda_evidence_axis'), color='#2e7d32')
            ax4 = ax3.twinx()
            ax4.plot(x, sc.n_good, '-', color='#6a1b9a')
            ax4.set_ylabel('N_g', color='#6a1b9a')
        ax3.set_xlabel('log₁₀ λ_rel')
        for a_ in (ax, ax3):
            if sc.index_inflexion is not None:
                a_.axvline(x[sc.index_inflexion], color='k', ls='--', lw=0.9,
                           label=tr('gift.lambda_method_inflexion'))
            if sc.index_evidence is not None:
                a_.axvline(x[sc.index_evidence], color='#2e7d32', ls=':', lw=1.2,
                           label=tr('gift.lambda_method_evidence'))
            a_.axvline(np.log10(s.lam_rel), color=_CLR_FIT, lw=1.2, alpha=0.6,
                       label=tr('gift.lambda_chosen'))
        ax3.legend(fontsize=7, loc='lower left')
        self.canvas_lam.draw_idle()

    def _plot_significance(self):
        self.fig_sig.clear()
        ax = self.fig_sig.add_subplot(111)
        q, I, err = self._current_arrays()
        if err is None:
            ax.text(0.5, 0.5, tr('gift.no_errors'), ha='center', va='center',
                    transform=ax.transAxes)
            self.canvas_sig.draw_idle()
            return
        sig = significance(I, err)
        ax.plot(q, sig, '-', color=_CLR_DATA, lw=0.6, alpha=0.4)
        ax.plot(q, rolling_median(sig, self.window_spin.value()), '-', color=_CLR_DATA, lw=2)
        mode, n = self.qmode_combo.currentData()
        for lvl in (3, 2, 1):
            ax.axhline(lvl, color='k', ls='--' if lvl == n else ':', lw=1.0 if lvl == n else 0.6)
        self._shade_excluded(ax, self.analysis.selection)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('q / nm⁻¹')
        ax.set_ylabel('|I(q)| / σ(q)')
        self.canvas_sig.draw_idle()

    def _sigma_for_display(self, q, I):
        if self.has_errors:
            return self._current_arrays()[2]
        rel = self._sigma_relative()
        return relative_sigma(I, rel) if rel is not None else estimate_sigma(q, I)

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    def _show_provenance(self, record=None):
        rec = record or self.analysis.record
        self.record_label.setText(f"<b>record_id</b>: {rec.record_id}")
        self.prov_tree.clear()
        self._fill_tree(self.prov_tree.invisibleRootItem(), rec.to_dict())
        self.prov_tree.expandToDepth(1)

    def _fill_tree(self, parent, value):
        if isinstance(value, dict):
            for k, v in value.items():
                item = QTreeWidgetItem(parent, [str(k), '' if isinstance(v, (dict, list))
                                                else str(v)])
                self._fill_tree(item, v)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                label = v.get('label') or v.get('code') or v.get('id') if isinstance(v, dict) else None
                item = QTreeWidgetItem(parent, [f"[{i}] {label or ''}".strip(),
                                                '' if isinstance(v, (dict, list)) else str(v)])
                self._fill_tree(item, v)

    def _load_settings_from_sidecar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr('gift.load_sidecar'), str(self._out_dir()), "Provenance (*_prov.json *.json)")
        if not path:
            return
        try:
            rec = ProvenanceRecord.load(path)
            acts = rec.to_dict()['processing']['activities']
            ift = next(a for a in acts if a['type'] == 'ift')
            pre = next(a for a in acts if a['type'] == 'preprocessing')
        except (OSError, ValueError, KeyError, StopIteration) as e:
            QMessageBox.warning(self, tr('messages.error'), tr('gift.sidecar_invalid', error=e))
            return
        p = ift['parameters']
        qr = pre['parameters'].get('q_range', {})
        load = next((a for a in acts if a['type'] == 'data_loading'), {'parameters': {}})
        factor = float(load['parameters'].get('q_conversion_factor', 1.0))
        idx_unit = self.qunit_combo.findData(factor)
        if idx_unit >= 0 and idx_unit != self.qunit_combo.currentIndex():
            self.qunit_combo.setCurrentIndex(idx_unit)
        self._updating = True
        idx_kind = self.kind_combo.findData(p.get('kind', PDDF))
        self.kind_combo.setCurrentIndex(max(idx_kind, 0))
        self.dmax_spin.setValue(float(p['dmax']))
        self.nspl_spin.setValue(int(p['n_splines']))
        idx = self.k_combo.findData(p.get('k_type', K_DIRICHLET))
        if idx >= 0:
            self.k_combo.setCurrentIndex(idx)
        self.bg_check.setChecked(bool(p.get('background', False)))
        manual = p.get('lam') != LAMBDA_AUTO
        self._set_lam_method(LAMBDA_MANUAL if manual
                             else p.get('lam_method', LAMBDA_INFLEXION))
        self.lam_spin.setEnabled(manual)
        if manual:
            self.lam_spin.setValue(np.log10(float(p['lam'])))
        # Ältere Sidecars (< v7.13) kannten kein automatisches q_min
        self.auto_qmin_check.setChecked(bool(qr.get('auto_qmin', False)))
        mode, n = qr.get('mode', QRANGE_FULL), qr.get('n_sigma')
        for i in range(self.qmode_combo.count()):
            m, nn = self.qmode_combo.itemData(i)
            if m == mode and (m != QRANGE_SIGMA or nn == n):
                self.qmode_combo.setCurrentIndex(i)
                break
        if qr.get('window'):
            self.window_spin.setValue(int(qr['window']))
        if qr.get('q_min') is not None:
            self.qmin_spin.setValue(float(qr['q_min']))
        if qr.get('q_max') is not None:
            self.qmax_spin.setValue(float(qr['q_max']))
        gift_act = next((a for a in acts if a['type'] == 'gift_bssa'), None)
        if gift_act is not None:
            gp = gift_act['parameters']
            self.model_combo.setCurrentIndex(self.model_combo.findData(gp.get('model', 'none')))
            self._rebuild_param_grid()
            start = gp.get('start', {})
            lo = gp.get('lower_effective', gp.get('lower', {}))
            hi = gp.get('upper_effective', gp.get('upper', {}))
            for name, w in self.param_widgets.items():
                if name in lo:
                    w['lower'].setValue(float(lo[name]))
                if name in hi:
                    w['upper'].setValue(float(hi[name]))
                if name in start:
                    w['start'].setValue(float(start[name]))
                fixed_list = gp.get('fixed')
                if fixed_list is None:
                    fixed_list = get_model(gp.get('model', 'none')).default_fixed()
                w['fixed'].setChecked(name in fixed_list)
            self.seed_spin.setValue(int(gp.get('bssa', {}).get('seed', 12345)))
            # Worker-Zahl beeinflusst das Ergebnis nicht; 0 (Hauptprozess) wird übernommen,
            # damit auch Diagnose-Läufe exakt wiederholt werden können
            if gp.get('n_workers') == 0:
                self.workers_spin.setValue(0)
        else:
            self.model_combo.setCurrentIndex(self.model_combo.findData('none'))
        if not self.has_errors:
            rel = pre['parameters'].get('sigma_relative')
            self.sigma_mode_combo.setCurrentIndex(
                self.sigma_mode_combo.findData(SIGMA_RELATIVE if rel else 'estimated'))
            if rel:
                self.sigma_rel_spin.setValue(100.0 * float(rel))
        # DREAM-Einstellungen (falls der Sidecar eine Unsicherheitsanalyse enthält): nach der
        # (G)IFT automatisch wiederholen und die Posterior-Mediane vergleichen
        dream_act = next((a for a in acts if a['type'] == 'dream'), None)
        self._pending_dream = None
        if dream_act is not None:
            self._apply_uncertainty_settings(dream_act['parameters'])
            self._pending_dream = dream_act.get('results_summary', {}).get('posterior', {})
        self._updating = False
        self._on_qmode_changed()

        # Eingangsdatei unverändert?
        current = compute_sha256(self.dataset.filepath)
        stored = [e.get('sha256') for e in rec.to_dict()['input']['entities']]
        mismatch = bool(stored) and current not in stored
        if mismatch:
            self._pending_dream = None
        self.compute()
        if mismatch:
            QMessageBox.warning(self, tr('gift.load_sidecar'), tr('gift.sidecar_hash_mismatch'))
            return
        old = next((a['results_summary'] for a in acts if a['type'] == 'ift'), {})
        rg_old = old.get('rg_nm')
        if self._worker is not None:
            # GIFT läuft asynchron: Vergleich (und ggf. DREAM) nach Abschluss (_on_gift_done)
            self._pending_reproduction = rg_old
        elif self.analysis is not None:
            if rg_old is not None:
                self._report_reproduction(rg_old)
            self._start_pending_dream()

    def _start_pending_dream_when_idle(self):
        if self._worker is not None:
            QTimer.singleShot(50, self._start_pending_dream_when_idle)
            return
        self._start_pending_dream()

    def _start_pending_dream(self):
        pending = getattr(self, '_pending_dream', None)
        self._pending_dream = None
        if pending is not None and self.analysis is not None:
            self._start_dream(compare=pending)

    def _report_reproduction(self, rg_old):
        QMessageBox.information(
            self, tr('gift.load_sidecar'),
            tr('gift.sidecar_reproduced', rg_old=f"{rg_old:.5g}",
               rg_new=f"{self.analysis.solution.rg:.5g}"))

    # ------------------------------------------------------------------
    # Übernehmen
    # ------------------------------------------------------------------

    def apply(self):
        """Exportieren und ans Hauptfenster melden (IFT wird vorher frisch gerechnet)."""
        if self._model_key() == 'none':
            if self._dirty or self.analysis is None:
                self.compute()
        elif self.analysis is None or self.analysis.gift is None or self._dirty:
            QMessageBox.information(self, tr('gift.apply'), tr('gift.need_compute'))
            return
        if self.analysis is None:
            return
        paths = result_paths(self.dataset.filepath, self._out_dir(),
                             self.analysis.solution.settings.kind)
        existing = [p for k, p in paths.items() if p.exists()]
        if existing:
            reply = QMessageBox.question(
                self, tr('gift.apply'),
                tr('gift.overwrite', files="\n".join(p.name for p in existing)))
            if reply != QMessageBox.Yes:
                return
        try:
            written = export_ift_results(self.analysis, out_dir=self._out_dir(),
                                         source_file=self.dataset.filepath,
                                         write_w3c=self.w3c_check.isChecked())
            # Veraltete S(q)/P(q)/DREAM-Dateien einer früheren Rechnung entfernen
            # (sie gehörten nicht zu diesem Sidecar; das Überschreiben wurde bestätigt)
            for key in ('sq', 'pq', 'prov_w3c', 'dream', 'pr_band', 'decon'):
                if key not in written and paths[key].exists():
                    paths[key].unlink()
        except OSError as e:
            QMessageBox.critical(self, tr('messages.error'), str(e))
            return
        self._show_provenance(self.analysis.extras.get('exported_record'))
        self.results_applied.emit({
            'paths': written,
            'record_id': self.analysis.record.record_id,
            'dataset': self.dataset,
            'worst_level': self.analysis.worst_level,
        })
        QMessageBox.information(
            self, tr('messages.success'),
            tr('gift.applied', dir=str(written['pr'].parent),
               files="\n".join(p.name for p in written.values())))
