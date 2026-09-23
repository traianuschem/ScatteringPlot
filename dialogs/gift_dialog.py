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
Live-Vorschau. GIFT/DREAM (spätere Phasen) laufen im Hintergrund-Thread.
"""

import time
import warnings
from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox, QFormLayout, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QFileDialog, QScrollArea, QSizePolicy, QFrame, QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QColor, QBrush

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from i18n import tr
from utils.data_loader import select_columns
from analysis.significance import (significance, rolling_median, QRANGE_FULL,
                                   QRANGE_SIGMA, QRANGE_MANUAL)
from analysis.gift.ift import (IFTSettings, LAMBDA_AUTO, K_DIRICHLET, K_GLATTER,
                               K_CURVATURE, estimate_sigma)
from analysis.gift.diagnostics import (guinier_rg, dmax_qmin_ratio, shannon_channels,
                                       suggest_n_splines, LEVEL_OK, LEVEL_INFO, LEVEL_WARNING,
                                       SIGMA_RELATIVE)
from analysis.gift.pipeline import (run_ift_analysis, export_ift_results, result_paths,
                                    relative_sigma, QRangeSettings, RESULT_SUBDIR)
from analysis.gift.provenance import ProvenanceRecord, compute_sha256
from analysis.gift.structure_factors import MODELS, get_model
from analysis.gift.gift import GIFTSettings
from analysis.gift.bssa import BSSASettings, BSSACancelled

_MODEL_ORDER = ('none', 'hs_py_avg', 'hs_py', 'rmsa')

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
    text = tr(key, **flag.params) if flag.params else tr(key)
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


class GiftDialog(QDialog):
    """Nicht-modaler Dialog für IFT und GIFT."""

    results_applied = Signal(object)   # dict: paths, record_id, dataset, flags

    def __init__(self, dataset, parent=None, significance_window=9):
        super().__init__(parent)
        self.dataset = dataset
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
        ds = self.dataset
        if getattr(ds, 'raw_data', None) is None:
            ds.load_data()
        data = select_columns(ds.raw_data, ds.col_x, ds.col_y, ds.col_err,
                              filter_nonpositive=False)
        q = data[:, 0]
        I = data[:, 1]
        err = data[:, 2] if data.shape[1] > 2 else None
        keep = np.isfinite(q) & np.isfinite(I) & (q > 0)
        if err is not None:
            keep &= np.isfinite(err)
        order = np.argsort(q[keep])
        q, I = q[keep][order], I[keep][order]
        err = err[keep][order] if err is not None else None
        # Doppelte q-Werte entfernen (q muss streng monoton sein)
        q, idx = np.unique(q, return_index=True)
        self.q_all, self.I_all = q, I[idx]
        self.err_all = err[idx] if err is not None else None
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
        self.qrange_info = QLabel()
        self.qrange_info.setWordWrap(True)
        f.addRow(self.qrange_info)
        lv.addWidget(g_q)

        # IFT
        g_ift = QGroupBox(tr('gift.group_ift'))
        f = QFormLayout(g_ift)
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
        f.addRow('Dmax:', dmax_row)
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
        self.lam_auto_check = QCheckBox(tr('gift.lambda_auto'))
        self.lam_auto_check.setChecked(True)
        f.addRow(self.lam_auto_check)
        self.lam_spin = QDoubleSpinBox()
        self.lam_spin.setRange(-14.0, 4.0)
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
        v.addLayout(row)
        self.apparent_label = QLabel(tr('gift.apparent_hint'))
        self.apparent_label.setWordWrap(True)
        self.apparent_label.setStyleSheet('font-style: italic;')
        v.addWidget(self.apparent_label)
        self.gift_status = QLabel()
        self.gift_status.setWordWrap(True)
        v.addWidget(self.gift_status)
        lv.addWidget(g_sq)

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
        self.fig_iq, self.canvas_iq = self._add_plot_tab(tr('gift.tab_iq'))
        self.fig_pr, self.canvas_pr = self._add_plot_tab(tr('gift.tab_pr'))
        self.fig_sq, self.canvas_sq = self._add_plot_tab(tr('gift.tab_sq'))
        self.fig_lam, self.canvas_lam = self._add_plot_tab(tr('gift.tab_lambda'))
        self.fig_sig, self.canvas_sig = self._add_plot_tab(tr('gift.tab_significance'))
        self.fig_bssa, self.canvas_bssa = self._add_plot_tab(tr('gift.tab_bssa'))
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
        self.lam_auto_check.toggled.connect(self._on_lam_auto_toggled)
        for w in (self.window_spin, self.qmin_spin, self.qmax_spin, self.dmax_spin,
                  self.nspl_spin, self.lam_spin):
            w.valueChanged.connect(self._schedule)
        self.k_combo.currentIndexChanged.connect(self._schedule)
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

    def _add_plot_tab(self, title):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        fig = Figure(figsize=(7, 5), tight_layout=True)
        canvas = FigureCanvasQTAgg(fig)
        v.addWidget(NavigationToolbar2QT(canvas, w))
        v.addWidget(canvas)
        self.tabs.addTab(w, title)
        return fig, canvas

    # ------------------------------------------------------------------
    # Startwerte
    # ------------------------------------------------------------------

    def _init_defaults(self):
        self._updating = True
        q, I, err = self._current_arrays()
        self.qmin_spin.setValue(q[0])
        self.qmax_spin.setValue(q[-1])
        sig = err if err is not None else estimate_sigma(q, I)
        guinier = guinier_rg(q, I, sig)
        limit = np.pi / q[0]
        dmax = limit if guinier is None else min(limit, 3.5 * guinier[0])
        self.dmax_spin.setValue(float(f"{dmax:.3g}"))
        # Standard: 2σ-Voreinstellung, falls Fehler vorhanden
        self.qmode_combo.setCurrentIndex(2 if self.has_errors else 0)
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
            self.qmin_spin.setValue(q[0])
            self.qmax_spin.setValue(q[-1])
            self._updating = False
        self.qmin_spin.setEnabled(mode != QRANGE_FULL)
        self._update_dmax_info()
        self._schedule()

    def _on_lam_auto_toggled(self, checked):
        self.lam_spin.setEnabled(not checked)
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

    def _set_suggested_n(self):
        q, _, _ = self._current_arrays()
        q_min = self._effective_qmin()
        q_max = q[-1] if self.qmode_combo.currentData()[0] != QRANGE_MANUAL \
            else min(q[-1], self.qmax_spin.value())
        if self.analysis is not None and self.qmode_combo.currentData()[0] == QRANGE_SIGMA:
            q_max = self.analysis.selection.q_max
        self.nspl_spin.setValue(suggest_n_splines(self.dmax_spin.value(), q_min, q_max))

    def _set_dmax_to_limit(self):
        self.dmax_spin.setValue(float(f"{np.pi / self._effective_qmin():.4g}"))

    def _effective_qmin(self):
        q, _, _ = self._current_arrays()
        mode, _n = self.qmode_combo.currentData()
        if mode == QRANGE_FULL:
            return float(q[0])
        return max(float(q[0]), self.qmin_spin.value())

    def _update_dmax_info(self, *_):
        q_min = self._effective_qmin()
        ratio = dmax_qmin_ratio(self.dmax_spin.value(), q_min)
        color = _LEVEL_STYLE[LEVEL_WARNING][1] if ratio > 1 else _LEVEL_STYLE[LEVEL_OK][1]
        self.dmax_info.setText(
            f"<span style='color:{color}'>π/q_min = {np.pi / q_min:.4g} nm · "
            f"Dmax·q_min/π = {ratio:.2f}</span>")

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
        lam = LAMBDA_AUTO if self.lam_auto_check.isChecked() else 10 ** self.lam_spin.value()
        return IFTSettings(dmax=self.dmax_spin.value(), n_splines=self.nspl_spin.value(),
                           lam=lam, k_type=self.k_combo.currentData(),
                           background=self.bg_check.isChecked())

    def _qrange_settings(self):
        mode, n = self.qmode_combo.currentData()
        q, _, _ = self._current_arrays()
        if mode == QRANGE_FULL:
            return QRangeSettings(mode=QRANGE_FULL)
        q_min = self.qmin_spin.value()
        q_min = None if q_min <= q[0] * (1 + 1e-9) else q_min
        if mode == QRANGE_SIGMA:
            return QRangeSettings(mode=QRANGE_SIGMA, n_sigma=n, window=self.window_spin.value(),
                                  q_min=q_min)
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
        if self.lam_auto_check.isChecked():
            self.lam_spin.setValue(np.log10(self.analysis.solution.lam_rel))
        self._updating = False
        self.qrange_info.setText(tr('gift.qrange_info', n=sel.n_selected, total=sel.n_total,
                                    q_min=f"{sel.q_min:.4g}", q_max=f"{sel.q_max:.4g}"))
        self._update_dmax_info()
        self._show_results()
        self._plot_all()
        self._show_provenance()

    def _show_results(self):
        a = self.analysis
        s = a.solution
        rows = [
            f"<b>Rg</b> = {s.rg:.4g} ± {s.rg_err:.2g} nm",
            f"<b>I(0)</b> = {s.i0:.4g} ± {s.i0_err:.2g}",
        ]
        if a.guinier:
            rows.append(f"Rg<sub>Guinier</sub> = {a.guinier[0]:.4g} nm ({a.guinier[2]} Pkt.)")
        rows.append(f"<b>MD</b> = {s.md:.3g}")
        rows.append(f"λ<sub>rel</sub> = {s.lam_rel:.3g}"
                    f" ({tr('gift.lambda_manual') if s.lam_manual else tr('gift.lambda_inflexion')})")
        if s.background is not None:
            rows.append(f"{tr('gift.background_value')} = {s.background:.4g} ± {s.background_err:.2g}")
        ns = shannon_channels(s.settings.dmax, s.q[0], s.q[-1])
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
        self.result_label.setText("<br>".join(rows))

        self.flag_list.clear()
        order = {LEVEL_WARNING: 0, LEVEL_INFO: 1, LEVEL_OK: 2}
        for flag in sorted(a.flags, key=lambda f: order[f.level]):
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
        """Startwerte: R_HS aus dem Rg der IFT (äquivalente Kugel, R = √(5/3)·Rg); φ, μ Standard.

        Nach [BP97] konvergiert die Suche mit eher überschätzten Startwerten besser.
        """
        model = get_model(self._model_key())
        rg = None
        if self.analysis is not None and np.isfinite(self.analysis.solution.rg):
            rg = self.analysis.solution.rg
        for p in model.params:
            if p.name == 'r_hs':
                start = np.sqrt(5.0 / 3.0) * rg if rg else self.dmax_spin.value() / 2.0
                self._set_param(p, float(f"{start:.3g}"))
            else:
                self._set_param(p, p.default)
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
                            fixed=fixed, bssa=BSSASettings(seed=self.seed_spin.value()))

    def _set_busy(self, busy):
        self.compute_btn.setEnabled(not busy)
        self.apply_btn.setEnabled(not busy and self.analysis is not None)
        self.cancel_btn.setEnabled(busy)
        self.model_combo.setEnabled(not busy)

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
        if pending is not None:
            self._pending_reproduction = None
            self._report_reproduction(pending)

    def _on_gift_failed(self, message):
        self._pending_reproduction = None
        if message == _GiftWorker.CANCELLED:
            self.gift_status.setText(tr('gift.gift_cancelled'))
        else:
            self.gift_status.setText(f"<span style='color:#c62828'>{tr('gift.error')}: {message}</span>")

    def _on_worker_finished(self):
        self._worker = None
        self._set_busy(False)

    def _cancel_gift(self):
        if self._worker is not None:
            self._worker.cancel()

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait(10000)
        super().closeEvent(event)

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
        gs = self.fig_iq.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05)
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
        ax.plot(s.r, s.pr, '-', color=_CLR_FIT, lw=1.8, label='p(r)')
        ax.fill_between(s.r, s.pr - s.pr_err, s.pr + s.pr_err, color=_CLR_FIT, alpha=0.25, lw=0,
                        label='± σ')
        ax.axhline(0, color='k', lw=0.8)
        ax.axvline(s.settings.dmax, color='k', ls='--', lw=0.8, label='Dmax')
        limit = np.pi / a.selection.q_min
        if limit <= 1.3 * s.settings.dmax:
            ax.axvline(limit, color='#c62828', ls=':', lw=1.0, label='π/q_min')
        ax.set_xlabel('r / nm')
        ax.set_ylabel('p(r)')
        ax.set_xlim(0, max(s.settings.dmax, 0) * 1.05)
        ax.legend(fontsize=8)
        self.canvas_pr.draw_idle()

    def _plot_lambda(self):
        sc = self.analysis.solution.scan
        s = self.analysis.solution
        self.fig_lam.clear()
        ax = self.fig_lam.add_subplot(111)
        x = np.log10(sc.lam_rel)
        ax.plot(x, np.log10(sc.nc), '-', color=_CLR_DATA, label='log N_c')
        ax.set_xlabel('log₁₀ λ_rel')
        ax.set_ylabel('log₁₀ N_c', color=_CLR_DATA)
        ax2 = ax.twinx()
        ax2.plot(x, sc.md, '-', color=_CLR_FIT, label='MD')
        ax2.set_yscale('log')
        ax2.set_ylabel(tr('gift.md_axis'), color=_CLR_FIT)
        ax.axvline(np.log10(s.lam_rel), color='k', ls='--', lw=1.0)
        ax.set_title(tr('gift.lambda_title'), fontsize=10)
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
        self.dmax_spin.setValue(float(p['dmax']))
        self.nspl_spin.setValue(int(p['n_splines']))
        idx = self.k_combo.findData(p.get('k_type', K_DIRICHLET))
        if idx >= 0:
            self.k_combo.setCurrentIndex(idx)
        self.bg_check.setChecked(bool(p.get('background', False)))
        manual = p.get('lam') != LAMBDA_AUTO
        self.lam_auto_check.setChecked(not manual)
        if manual:
            self.lam_spin.setValue(np.log10(float(p['lam'])))
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
        else:
            self.model_combo.setCurrentIndex(self.model_combo.findData('none'))
        if not self.has_errors:
            rel = pre['parameters'].get('sigma_relative')
            self.sigma_mode_combo.setCurrentIndex(
                self.sigma_mode_combo.findData(SIGMA_RELATIVE if rel else 'estimated'))
            if rel:
                self.sigma_rel_spin.setValue(100.0 * float(rel))
        self._updating = False
        self._on_qmode_changed()
        self.compute()

        # Eingangsdatei unverändert?
        current = compute_sha256(self.dataset.filepath)
        stored = [e.get('sha256') for e in rec.to_dict()['input']['entities']]
        if stored and current not in stored:
            QMessageBox.warning(self, tr('gift.load_sidecar'), tr('gift.sidecar_hash_mismatch'))
        else:
            old = next((a['results_summary'] for a in acts if a['type'] == 'ift'), {})
            rg_old = old.get('rg_nm')
            if rg_old is None:
                return
            if self._worker is not None:
                # GIFT läuft asynchron: Vergleich nach Abschluss (_on_gift_done)
                self._pending_reproduction = rg_old
            elif self.analysis is not None:
                self._report_reproduction(rg_old)

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
            self.compute()
        elif self.analysis is None or self.analysis.gift is None or self._dirty:
            QMessageBox.information(self, tr('gift.apply'), tr('gift.need_compute'))
            return
        if self.analysis is None:
            return
        paths = result_paths(self.dataset.filepath, self._out_dir())
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
            # Veraltete S(q)/P(q)-Dateien einer früheren GIFT-Rechnung entfernen
            # (sie gehörten nicht zu diesem Sidecar; das Überschreiben wurde bestätigt)
            for key in ('sq', 'pq', 'prov_w3c'):
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
