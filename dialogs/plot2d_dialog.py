"""
2D SAXS Analysis Dialog

Displays a Dataset2D as:
  - Cartesian q-map  (2D histogram in qx/qy)          [page 0]
  - Polar map        (2D histogram in |q|/φ)           [page 1]
      interactive q-ring selector (draggable lines)
  - Azimuthal profile  I(φ) integrated over q-ring     [page 2]
      optional sin(φ) correction with pole handling
  - Sector integral    I(|q|) at azimuthal sector      [page 3]

Color scale for q-Map and Polar Map is adjustable via percentile
sliders without recomputing the histogram.

Export PNG routes through the existing ExportSettingsDialog for
consistent metadata handling across the application.
"""

import numpy as np
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QGridLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QFileDialog, QMessageBox, QSizePolicy, QWidget,
    QStackedWidget, QFrame, QSlider, QRadioButton,
    QButtonGroup,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.colors import SymLogNorm, Normalize

from i18n import tr

# ── optional scipy for Voigt fitting ─────────────────────────────────────────
try:
    from scipy.optimize import curve_fit as _scipy_curve_fit
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False

# ── constants ─────────────────────────────────────────────────────────────────
VIEW_QMAP      = 0
VIEW_POLAR     = 1
VIEW_AZIMUTHAL = 2
VIEW_SECTOR    = 3

_COLORMAPS = ['viridis', 'inferno', 'plasma', 'magma', 'cividis',
              'RdBu_r', 'coolwarm', 'turbo', 'hot', 'jet']

_CLR_LO      = '#4fc3f7'   # cyan   — q_lo line
_CLR_HI      = '#ff9800'   # orange — q_hi line
_DRAG_TOL_PX = 8            # pixel tolerance for line picking

_DEFAULT_EXPORT = {
    'format': 'PNG', 'dpi': 300,
    'width': 10.0, 'height': 7.0,
    'keep_aspect': True, 'transparent': False,
    'tight_layout': True, 'bg_color': '#2b2b2b',
}


# ── helper: pseudo-Voigt peak centred at x=0 ─────────────────────────────────
def _pseudo_voigt(x, A, sigma, gamma, eta, base):
    """Mixture of Gaussian and Lorentzian, peak at x=0, baseline *base*."""
    G = np.exp(-np.log(2.0) * (x / sigma) ** 2)
    L = 1.0 / (1.0 + (x / gamma) ** 2)
    return A * (eta * L + (1.0 - eta) * G) + base


# ── dialog ────────────────────────────────────────────────────────────────────
class Plot2DDialog(QDialog):
    """Non-modal dialog for 2D SAXS analysis."""

    projection_ready = Signal(object)   # emits DataSet to main window

    # ── construction ──────────────────────────────────────────────────────────

    def __init__(self, dataset_2d, parent=None):
        super().__init__(parent)
        self.dataset = dataset_2d
        self.setWindowTitle(f"{tr('2d.dialog_title')} — {dataset_2d.display_label}")
        self.resize(1120, 800)
        self.setModal(False)

        self._last_result      = None
        self._export_settings  = _DEFAULT_EXPORT.copy()

        # ── q-ring selector state ────────────────────────────────────────────
        self._polar_ax         = None
        self._q_selector_lo    = None
        self._q_selector_hi    = None
        self._q_band           = None
        self._q_lo_label       = None
        self._q_hi_label       = None
        self._dragging         = None
        self._drag_cid_press   = None
        self._drag_cid_motion  = None
        self._drag_cid_release = None
        self._drag_cid_hover   = None

        # ── color-scale artist cache (per view) ──────────────────────────────
        self._qmap_im          = None
        self._qmap_cbar        = None
        self._qmap_data_finite = None   # sorted finite+ values for percentile lookup
        self._polar_im         = None
        self._polar_cbar       = None
        self._polar_data_finite= None

        self._build_ui()
        self._update_param_panel()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._update_plot)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # ── toolbar ──────────────────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(8)

        tb.addWidget(QLabel(tr('2d.view_label') + ':'))
        self.view_combo = QComboBox()
        self.view_combo.addItems([
            tr('2d.view_qmap'), tr('2d.view_polar'),
            tr('2d.view_azimuthal'), tr('2d.view_sector'),
        ])
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        tb.addWidget(self.view_combo)

        tb.addSpacing(16)
        tb.addWidget(QLabel(tr('2d.colormap_label') + ':'))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(_COLORMAPS)
        self.cmap_combo.setCurrentText('viridis')
        tb.addWidget(self.cmap_combo)

        tb.addSpacing(16)
        tb.addWidget(QLabel(tr('2d.bins_label') + ':'))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(50, 2000)
        self.bins_spin.setValue(600)
        self.bins_spin.setSingleStep(50)
        tb.addWidget(self.bins_spin)

        tb.addSpacing(16)
        self.log_check = QCheckBox(tr('2d.log_scale'))
        self.log_check.setChecked(True)
        tb.addWidget(self.log_check)

        update_btn = QPushButton(tr('2d.update_plot'))
        update_btn.clicked.connect(self._update_plot)
        tb.addWidget(update_btn)
        tb.addStretch()
        layout.addLayout(tb)

        # ── canvas + parameter panel ─────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        canvas_w = QWidget()
        cl = QVBoxLayout(canvas_w)
        cl.setContentsMargins(0, 0, 0, 0)
        self.figure     = Figure(facecolor='#2b2b2b')
        self.canvas     = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav_toolbar = NavigationToolbar2QT(self.canvas, canvas_w)
        cl.addWidget(self.nav_toolbar)
        cl.addWidget(self.canvas)
        splitter.addWidget(canvas_w)

        self.param_stack = QStackedWidget()
        self.param_stack.setFixedWidth(260)
        self.param_stack.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.param_stack.addWidget(self._make_qmap_page())       # 0
        self.param_stack.addWidget(self._make_polar_page())      # 1
        self.param_stack.addWidget(self._make_azimuthal_page())  # 2
        self.param_stack.addWidget(self._make_sector_page())     # 3
        splitter.addWidget(self.param_stack)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        # ── bottom button row ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.export_png_btn = QPushButton(tr('2d.export_png'))
        self.export_png_btn.clicked.connect(self._export_png)
        btn_row.addWidget(self.export_png_btn)

        self.export_ascii_btn = QPushButton(tr('2d.export_ascii'))
        self.export_ascii_btn.clicked.connect(self._export_ascii)
        btn_row.addWidget(self.export_ascii_btn)

        btn_row.addStretch()

        self.add_to_1d_btn = QPushButton(tr('2d.add_to_1d'))
        self.add_to_1d_btn.setEnabled(False)
        self.add_to_1d_btn.clicked.connect(self._add_to_1d)
        btn_row.addWidget(self.add_to_1d_btn)

        layout.addLayout(btn_row)

    # ── parameter pages ───────────────────────────────────────────────────────

    def _make_cmap_group(self, prefix: str) -> QGroupBox:
        """
        Shared factory: creates a 'Farbskala' group with two percentile sliders.
        Widget references are stored as  self._{prefix}_vmin_slider  etc.
        prefix: 'qmap' | 'polar'
        """
        group = QGroupBox(tr('2d.cmap_range_group'))
        vbox  = QVBoxLayout(group)
        vbox.setSpacing(3)
        grid  = QGridLayout()
        grid.setSpacing(2)
        grid.setColumnStretch(1, 1)

        # -- min row --
        grid.addWidget(QLabel('Min:'), 0, 0)
        lo_slider = QSlider(Qt.Horizontal)
        lo_slider.setRange(0, 1000)
        lo_slider.setValue(10)          # 1 %
        grid.addWidget(lo_slider, 0, 1)
        lo_pct_lbl = QLabel('1.0 %')
        lo_pct_lbl.setFixedWidth(42)
        lo_pct_lbl.setStyleSheet('color:#aaa;font-size:10px;')
        grid.addWidget(lo_pct_lbl, 0, 2)
        lo_val_lbl = QLabel('–')
        lo_val_lbl.setStyleSheet('color:#ccc;font-size:10px;')
        grid.addWidget(lo_val_lbl, 1, 1, 1, 2)

        # -- max row --
        grid.addWidget(QLabel('Max:'), 2, 0)
        hi_slider = QSlider(Qt.Horizontal)
        hi_slider.setRange(0, 1000)
        hi_slider.setValue(990)         # 99 %
        grid.addWidget(hi_slider, 2, 1)
        hi_pct_lbl = QLabel('99.0 %')
        hi_pct_lbl.setFixedWidth(42)
        hi_pct_lbl.setStyleSheet('color:#aaa;font-size:10px;')
        grid.addWidget(hi_pct_lbl, 2, 2)
        hi_val_lbl = QLabel('–')
        hi_val_lbl.setStyleSheet('color:#ccc;font-size:10px;')
        grid.addWidget(hi_val_lbl, 3, 1, 1, 2)

        vbox.addLayout(grid)

        auto_btn = QPushButton(tr('2d.cmap_auto_reset'))
        auto_btn.setFixedHeight(22)
        vbox.addWidget(auto_btn)

        # store refs
        setattr(self, f'_{prefix}_vmin_slider',  lo_slider)
        setattr(self, f'_{prefix}_vmax_slider',  hi_slider)
        setattr(self, f'_{prefix}_vmin_pct_lbl', lo_pct_lbl)
        setattr(self, f'_{prefix}_vmax_pct_lbl', hi_pct_lbl)
        setattr(self, f'_{prefix}_vmin_val_lbl', lo_val_lbl)
        setattr(self, f'_{prefix}_vmax_val_lbl', hi_val_lbl)

        lo_slider.valueChanged.connect(lambda _: self._on_cmap_slider(prefix))
        hi_slider.valueChanged.connect(lambda _: self._on_cmap_slider(prefix))
        auto_btn.clicked.connect(lambda: self._cmap_auto_reset(prefix))

        return group

    def _make_qmap_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(self._make_cmap_group('qmap'))
        lay.addStretch()
        return w

    def _make_polar_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        # q-ring selector group
        q_grp = QGroupBox(tr('2d.polar_qring_group'))
        q_lay = QVBoxLayout(q_grp)
        q_lay.setSpacing(6)

        hint = QLabel(tr('2d.polar_qring_hint'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#aaa;font-size:10px;')
        q_lay.addWidget(hint)

        lo_row = QHBoxLayout()
        lo_dot = QLabel('─')
        lo_dot.setStyleSheet(f'color:{_CLR_LO};font-weight:bold;')
        lo_row.addWidget(lo_dot)
        lo_row.addWidget(QLabel('qₘᴵⁿ:'))
        self._polar_lo_label = QLabel('–')
        self._polar_lo_label.setStyleSheet(f'color:{_CLR_LO};font-weight:bold;')
        lo_row.addWidget(self._polar_lo_label)
        lo_row.addStretch()
        q_lay.addLayout(lo_row)

        hi_row = QHBoxLayout()
        hi_dot = QLabel('─')
        hi_dot.setStyleSheet(f'color:{_CLR_HI};font-weight:bold;')
        hi_row.addWidget(hi_dot)
        hi_row.addWidget(QLabel('qₘᵃˣ:'))
        self._polar_hi_label = QLabel('–')
        self._polar_hi_label.setStyleSheet(f'color:{_CLR_HI};font-weight:bold;')
        hi_row.addWidget(self._polar_hi_label)
        hi_row.addStretch()
        q_lay.addLayout(hi_row)

        lay.addWidget(q_grp)

        self._polar_export_overlay_check = QCheckBox(tr('2d.polar_export_overlay'))
        self._polar_export_overlay_check.setChecked(True)
        lay.addWidget(self._polar_export_overlay_check)

        go_btn = QPushButton(tr('2d.go_to_azimuthal'))
        go_btn.clicked.connect(self._go_to_azimuthal)
        lay.addWidget(go_btn)

        lay.addWidget(self._make_cmap_group('polar'))
        lay.addStretch()
        return w

    def _make_azimuthal_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        # q-ring parameter group
        rng_grp = QGroupBox(tr('2d.view_azimuthal'))
        grid = QGridLayout(rng_grp)

        grid.addWidget(QLabel(tr('2d.q_lo')), 0, 0)
        self.q_lo_spin = QDoubleSpinBox()
        self.q_lo_spin.setRange(0, 1000); self.q_lo_spin.setDecimals(4)
        self.q_lo_spin.setValue(0.05);    self.q_lo_spin.setSingleStep(0.01)
        self.q_lo_spin.valueChanged.connect(self._sync_selector_from_spinboxes)
        grid.addWidget(self.q_lo_spin, 0, 1)

        grid.addWidget(QLabel(tr('2d.q_hi')), 1, 0)
        self.q_hi_spin = QDoubleSpinBox()
        self.q_hi_spin.setRange(0, 1000); self.q_hi_spin.setDecimals(4)
        self.q_hi_spin.setValue(0.5);     self.q_hi_spin.setSingleStep(0.01)
        self.q_hi_spin.valueChanged.connect(self._sync_selector_from_spinboxes)
        grid.addWidget(self.q_hi_spin, 1, 1)

        grid.addWidget(QLabel(tr('2d.phi_bins')), 2, 0)
        self.phi_bins_spin = QSpinBox()
        self.phi_bins_spin.setRange(10, 720); self.phi_bins_spin.setValue(360)
        grid.addWidget(self.phi_bins_spin, 2, 1)

        lay.addWidget(rng_grp)
        lay.addWidget(self._make_sin_corr_group())
        lay.addStretch()
        return w

    def _make_sin_corr_group(self) -> QGroupBox:
        """sin(φ) correction UI — checkable group box."""
        group = QGroupBox(tr('2d.sin_corr_group'))
        group.setCheckable(True)
        group.setChecked(False)
        self._sin_corr_group = group

        vbox = QVBoxLayout(group)
        vbox.setSpacing(4)

        # operation radios
        op_row = QHBoxLayout()
        self._sin_div_radio = QRadioButton(tr('2d.sin_corr_divide'))
        self._sin_mul_radio = QRadioButton(tr('2d.sin_corr_multiply'))
        self._sin_div_radio.setChecked(True)
        op_bg = QButtonGroup(group)
        op_bg.addButton(self._sin_div_radio)
        op_bg.addButton(self._sin_mul_radio)
        op_row.addWidget(self._sin_div_radio)
        op_row.addWidget(self._sin_mul_radio)
        op_row.addStretch()
        vbox.addLayout(op_row)

        # pole handling sub-group
        pole_grp = QGroupBox(tr('2d.sin_corr_pole_handling'))
        self._pole_handling_group_box = pole_grp
        pole_vbox = QVBoxLayout(pole_grp)
        pole_vbox.setSpacing(3)

        self._pole_mask_radio  = QRadioButton(tr('2d.sin_corr_pole_mask'))
        self._pole_clamp_radio = QRadioButton(tr('2d.sin_corr_pole_clamp'))
        self._pole_voigt_radio = QRadioButton(tr('2d.sin_corr_pole_voigt'))
        self._pole_mask_radio.setChecked(True)

        if not _SCIPY_AVAILABLE:
            self._pole_voigt_radio.setEnabled(False)
            self._pole_voigt_radio.setToolTip('scipy nicht verfügbar / scipy not available')

        pole_bg = QButtonGroup(pole_grp)
        for rb in (self._pole_mask_radio, self._pole_clamp_radio, self._pole_voigt_radio):
            pole_bg.addButton(rb)
            pole_vbox.addWidget(rb)

        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel(tr('2d.sin_corr_pole_threshold')))
        self._pole_thresh_spin = QDoubleSpinBox()
        self._pole_thresh_spin.setRange(0.5, 30.0)
        self._pole_thresh_spin.setDecimals(1)
        self._pole_thresh_spin.setValue(5.0)
        self._pole_thresh_spin.setSuffix(' °')
        thr_row.addWidget(self._pole_thresh_spin)
        thr_row.addStretch()
        pole_vbox.addLayout(thr_row)

        vbox.addWidget(pole_grp)

        # disable pole sub-group when multiplication is selected
        self._sin_mul_radio.toggled.connect(
            lambda checked: pole_grp.setEnabled(not checked)
        )
        return group

    def _make_sector_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        grp  = QGroupBox(tr('2d.view_sector'))
        grid = QGridLayout(grp)

        grid.addWidget(QLabel(tr('2d.phi_lo')), 0, 0)
        self.phi_lo_spin = QDoubleSpinBox()
        self.phi_lo_spin.setRange(-180, 180); self.phi_lo_spin.setDecimals(1)
        self.phi_lo_spin.setValue(-30);       self.phi_lo_spin.setSingleStep(5)
        grid.addWidget(self.phi_lo_spin, 0, 1)

        grid.addWidget(QLabel(tr('2d.phi_hi')), 1, 0)
        self.phi_hi_spin = QDoubleSpinBox()
        self.phi_hi_spin.setRange(-180, 180); self.phi_hi_spin.setDecimals(1)
        self.phi_hi_spin.setValue(30);        self.phi_hi_spin.setSingleStep(5)
        grid.addWidget(self.phi_hi_spin, 1, 1)

        self.logq_check = QCheckBox(tr('2d.log_q_axis'))
        self.logq_check.setChecked(True)
        grid.addWidget(self.logq_check, 2, 0, 1, 2)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ── view switching ────────────────────────────────────────────────────────

    def _on_view_changed(self, index: int):
        if index != VIEW_POLAR:
            self._disconnect_q_selector()
        self._update_param_panel()
        self._update_plot()

    def _update_param_panel(self):
        idx = self.view_combo.currentIndex()
        self.param_stack.setCurrentIndex(idx)
        self.add_to_1d_btn.setEnabled(idx in (VIEW_AZIMUTHAL, VIEW_SECTOR))

    def _go_to_azimuthal(self):
        self.view_combo.setCurrentIndex(VIEW_AZIMUTHAL)

    # ── plotting ──────────────────────────────────────────────────────────────

    def _update_plot(self):
        if not self.dataset.data_loaded:
            return
        self._disconnect_q_selector()
        self.figure.clear()
        idx = self.view_combo.currentIndex()
        try:
            if   idx == VIEW_QMAP:      self._plot_qmap()
            elif idx == VIEW_POLAR:     self._plot_polar()
            elif idx == VIEW_AZIMUTHAL: self._plot_azimuthal()
            elif idx == VIEW_SECTOR:    self._plot_sector()
        except Exception as e:
            ax = self.figure.add_subplot(111)
            ax.set_facecolor('#2b2b2b')
            ax.text(0.5, 0.5, str(e), transform=ax.transAxes,
                    ha='center', va='center', color='red', wrap=True)
        self.canvas.draw()

    # ---------- q-map ---------------------------------------------------------

    def _plot_qmap(self):
        bins = self.bins_spin.value()
        qx_e, qy_e, H = self.dataset.generate_cartesian_map(bins=bins)
        self._last_result = ('qmap', qx_e, qy_e, H)

        self._qmap_data_finite = self._finite_positive(H)

        ax   = self.figure.add_subplot(111, facecolor='#1e1e1e')
        cmap = self._cmap_obj()
        norm = self._norm_from_slider('qmap', H)
        im   = ax.pcolormesh(qx_e, qy_e, H, cmap=cmap, norm=norm, shading='flat')
        cbar = self.figure.colorbar(im, ax=ax, label='I (a.u.)', pad=0.02)
        _style_cbar(cbar)
        self._qmap_im   = im
        self._qmap_cbar = cbar

        ax.set_xlabel(r'$q_x$ (nm$^{-1}$)', color='white')
        ax.set_ylabel(r'$q_y$ (nm$^{-1}$)', color='white')
        ax.set_title(tr('2d.view_qmap'), color='white')
        ax.set_aspect('equal')
        _style_ax(ax)
        self._refresh_cmap_labels('qmap')

    # ---------- polar map -----------------------------------------------------

    def _plot_polar(self):
        bins = self.bins_spin.value()
        q_e, phi_e, H = self.dataset.generate_polar_map(q_bins=bins, phi_bins=360)
        self._last_result = ('polar', q_e, phi_e, H)

        self._polar_data_finite = self._finite_positive(H)

        ax   = self.figure.add_subplot(111, facecolor='#1e1e1e')
        cmap = self._cmap_obj()
        norm = self._norm_from_slider('polar', H)
        im   = ax.pcolormesh(phi_e, q_e, H, cmap=cmap, norm=norm, shading='flat')
        cbar = self.figure.colorbar(im, ax=ax, label='I (a.u.)', pad=0.02)
        _style_cbar(cbar)
        self._polar_im   = im
        self._polar_cbar = cbar

        ax.set_xlabel(r'$\varphi$ (°)', color='white')
        ax.set_ylabel(r'$|q|$ (nm$^{-1}$)', color='white')
        ax.set_title(tr('2d.view_polar'), color='white')
        ax.set_yscale('log')
        _style_ax(ax)
        self._refresh_cmap_labels('polar')

        self._setup_q_selector(ax)

    # ---------- azimuthal profile ---------------------------------------------

    def _plot_azimuthal(self):
        q_lo     = self.q_lo_spin.value()
        q_hi     = self.q_hi_spin.value()
        phi_bins = self.phi_bins_spin.value()
        if q_lo >= q_hi:
            raise ValueError(f"q_lo ({q_lo:.4f}) must be < q_hi ({q_hi:.4f})")

        phi, I = self.dataset.azimuthal_profile(q_lo, q_hi, phi_bins)
        I      = self._apply_sin_correction(phi, I)
        self._last_result = ('azimuthal', phi, I, q_lo, q_hi)

        ax = self.figure.add_subplot(111, facecolor='#1e1e1e')
        ax.plot(phi, I, color=_CLR_LO, linewidth=1.2)
        ax.set_xlabel(r'$\varphi$ (°)', color='white')
        ax.set_ylabel(f'I{self._sin_y_label()} (a.u.)', color='white')
        ax.set_title(
            f"{tr('2d.view_azimuthal')}: "
            f"{q_lo:.3f} ≤ |q| ≤ {q_hi:.3f} nm⁻¹",
            color='white',
        )
        ax.set_xlim(-180, 180)
        _style_ax(ax)

    # ---------- sector integral -----------------------------------------------

    def _plot_sector(self):
        phi_lo = self.phi_lo_spin.value()
        phi_hi = self.phi_hi_spin.value()
        log_q  = self.logq_check.isChecked()
        bins   = self.bins_spin.value()
        q, I, I_err = self.dataset.sector_integral(phi_lo, phi_hi,
                                                    q_bins=bins, log_q=log_q)
        self._last_result = ('sector', q, I, I_err, phi_lo, phi_hi)

        ax = self.figure.add_subplot(111, facecolor='#1e1e1e')
        ax.errorbar(q, I, yerr=I_err, fmt='-', color=_CLR_LO,
                    ecolor=_CLR_LO, alpha=0.5, linewidth=1.2, capsize=0)
        ax.set_xlabel(r'$|q|$ (nm$^{-1}$)', color='white')
        ax.set_ylabel('I (a.u.)', color='white')
        ax.set_title(
            f"{tr('2d.view_sector')}: {phi_lo:.1f}° ≤ φ ≤ {phi_hi:.1f}°",
            color='white',
        )
        if log_q:
            ax.set_xscale('log')
        if self.log_check.isChecked() and np.any(I[np.isfinite(I)] > 0):
            ax.set_yscale('log')
        _style_ax(ax)

    # ── color-scale controls ──────────────────────────────────────────────────

    def _cmap_obj(self):
        cmap = plt.get_cmap(self.cmap_combo.currentText())
        cmap.set_bad(color='#2b2b2b')
        return cmap

    def _finite_positive(self, H: np.ndarray) -> np.ndarray:
        """Return sorted array of finite values; positive-only for log mode."""
        flat = H[np.isfinite(H)]
        if self.log_check.isChecked():
            flat = flat[flat > 0]
        return flat

    def _norm_from_slider(self, prefix: str, H: np.ndarray) -> Normalize:
        """Build norm from the current percentile slider positions."""
        data = self._finite_positive(H)
        setattr(self, f'_{prefix}_data_finite', data)

        if len(data) == 0:
            return Normalize()

        lo_pct = getattr(self, f'_{prefix}_vmin_slider').value() / 10.0
        hi_pct = getattr(self, f'_{prefix}_vmax_slider').value() / 10.0
        vmin   = float(np.percentile(data, lo_pct))
        vmax   = float(np.percentile(data, hi_pct))

        if vmin >= vmax:
            vmin, vmax = float(data.min()), float(data.max())

        if self.log_check.isChecked():
            linthresh = max(1e-12, vmin)
            return SymLogNorm(linthresh=linthresh, vmin=vmin, vmax=vmax)
        return Normalize(vmin=vmin, vmax=vmax)

    def _on_cmap_slider(self, prefix: str):
        """Slider moved — update labels and re-norm the artist without replot."""
        lo_s = getattr(self, f'_{prefix}_vmin_slider')
        hi_s = getattr(self, f'_{prefix}_vmax_slider')
        lo_p = lo_s.value() / 10.0
        hi_p = hi_s.value() / 10.0

        getattr(self, f'_{prefix}_vmin_pct_lbl').setText(f'{lo_p:.1f} %')
        getattr(self, f'_{prefix}_vmax_pct_lbl').setText(f'{hi_p:.1f} %')

        data = getattr(self, f'_{prefix}_data_finite', None)
        im   = getattr(self, f'_{prefix}_im',   None)
        cbar = getattr(self, f'_{prefix}_cbar', None)
        if im is None or data is None or len(data) == 0:
            return

        vmin = float(np.percentile(data, lo_p))
        vmax = float(np.percentile(data, hi_p))
        if vmin >= vmax:
            return

        getattr(self, f'_{prefix}_vmin_val_lbl').setText(f'{vmin:.3g}')
        getattr(self, f'_{prefix}_vmax_val_lbl').setText(f'{vmax:.3g}')

        if self.log_check.isChecked():
            new_norm = SymLogNorm(linthresh=max(1e-12, vmin), vmin=vmin, vmax=vmax)
        else:
            new_norm = Normalize(vmin=vmin, vmax=vmax)

        im.set_norm(new_norm)
        if cbar is not None:
            cbar.update_normal(im)
            _style_cbar(cbar)
        self.canvas.draw_idle()

    def _cmap_auto_reset(self, prefix: str):
        """Reset sliders to 1 % / 99 %."""
        getattr(self, f'_{prefix}_vmin_slider').setValue(10)
        getattr(self, f'_{prefix}_vmax_slider').setValue(990)
        # valueChanged fires automatically, so _on_cmap_slider is called

    def _refresh_cmap_labels(self, prefix: str):
        """Populate value labels right after a fresh plot."""
        data = getattr(self, f'_{prefix}_data_finite', None)
        if data is None or len(data) == 0:
            return
        lo_p = getattr(self, f'_{prefix}_vmin_slider').value() / 10.0
        hi_p = getattr(self, f'_{prefix}_vmax_slider').value() / 10.0
        vmin = float(np.percentile(data, lo_p))
        vmax = float(np.percentile(data, hi_p))
        getattr(self, f'_{prefix}_vmin_val_lbl').setText(f'{vmin:.3g}')
        getattr(self, f'_{prefix}_vmax_val_lbl').setText(f'{vmax:.3g}')
        getattr(self, f'_{prefix}_vmin_pct_lbl').setText(f'{lo_p:.1f} %')
        getattr(self, f'_{prefix}_vmax_pct_lbl').setText(f'{hi_p:.1f} %')

    # ── sin(φ) correction ─────────────────────────────────────────────────────

    def _sin_y_label(self) -> str:
        """Y-axis label suffix reflecting the applied correction."""
        if not self._sin_corr_group.isChecked():
            return ''
        return '/sin(φ)' if self._sin_div_radio.isChecked() else '·sin(φ)'

    def _apply_sin_correction(self, phi: np.ndarray, I: np.ndarray) -> np.ndarray:
        """Apply the user-selected sin(φ) correction to a raw I(φ) array."""
        if not self._sin_corr_group.isChecked():
            return I

        phi_rad = np.deg2rad(phi)
        sin_phi = np.sin(phi_rad)
        I       = I.copy().astype(float)

        if self._sin_mul_radio.isChecked():
            # Multiplication — safe everywhere, |sin| for symmetric treatment
            return I * np.abs(sin_phi)

        # ---- Division branch ----
        thresh_deg = self._pole_thresh_spin.value()
        thresh_sin = np.sin(np.deg2rad(thresh_deg))

        if self._pole_mask_radio.isChecked():
            safe = np.abs(sin_phi)
            with np.errstate(invalid='ignore', divide='ignore'):
                I = np.where(safe < thresh_sin, np.nan, I / safe)

        elif self._pole_clamp_radio.isChecked():
            # Clamp denominator: never smaller than sin(0.5°)
            eps  = np.sin(np.deg2rad(0.5))
            safe = np.maximum(np.abs(sin_phi), eps)
            I    = I / safe

        elif self._pole_voigt_radio.isChecked() and _SCIPY_AVAILABLE:
            # 1) mask poles → I_div
            safe = np.abs(sin_phi)
            with np.errstate(invalid='ignore', divide='ignore'):
                I_div = np.where(safe < thresh_sin, np.nan, I / safe)
            # 2) Voigt extrapolation at each pole
            I = self._voigt_extrapolate_poles(phi, I_div, thresh_deg)

        else:
            # fallback: mask
            safe = np.abs(sin_phi)
            with np.errstate(invalid='ignore', divide='ignore'):
                I = np.where(safe < thresh_sin, np.nan, I / safe)

        return I

    def _voigt_extrapolate_poles(
        self,
        phi: np.ndarray,
        I_div: np.ndarray,
        thresh_deg: float,
    ) -> np.ndarray:
        """
        For each pole (0° and ±180°):
          • fit a pseudo-Voigt to the flanks  [thresh, 3*thresh]
          • fill the masked region [0, thresh) with the extrapolated curve
        If the fit fails, the masked region remains NaN.
        """
        I_out      = I_div.copy()
        fit_window = thresh_deg * 3.0

        for pole in (0.0, 180.0):
            # distance from this pole, accounting for periodicity at ±180
            if pole == 0.0:
                dist = np.abs(phi)
            else:
                dist = np.minimum(np.abs(phi - 180.0), np.abs(phi + 180.0))

            masked_region = dist < thresh_deg
            fit_region    = (dist >= thresh_deg) & (dist <= fit_window)

            if np.sum(fit_region) < 5:
                continue

            x_fit = dist[fit_region]
            y_fit = I_div[fit_region]
            valid = np.isfinite(y_fit)
            if np.sum(valid) < 5:
                continue

            try:
                y_v = y_fit[valid]
                x_v = x_fit[valid]
                A0     = max(float(np.nanmax(y_v)) - float(np.nanmin(y_v)), 1e-30)
                base0  = float(np.nanmin(y_v))
                sig0   = thresh_deg * 1.5
                p0     = [A0, sig0, sig0, 0.5, base0]
                bounds = ([0, 0.01, 0.01, 0.0, -np.inf],
                          [np.inf, 180.0, 180.0, 1.0, np.inf])
                popt, _ = _scipy_curve_fit(
                    _pseudo_voigt, x_v, y_v,
                    p0=p0, bounds=bounds, maxfev=2000,
                )
                I_out[masked_region] = _pseudo_voigt(dist[masked_region], *popt)
            except Exception:
                pass    # leave as NaN if fit fails or data is insufficient

        return I_out

    # ── q-ring selector ───────────────────────────────────────────────────────

    def _setup_q_selector(self, ax):
        """Draw draggable q-lo / q-hi lines on the polar-map axes."""
        self._disconnect_q_selector()
        self._polar_ax = ax

        q_lo = self.q_lo_spin.value()
        q_hi = self.q_hi_spin.value()

        y_min, y_max = ax.get_ylim()
        q_lo = float(np.clip(q_lo, y_min, y_max))
        q_hi = float(np.clip(q_hi, y_min, y_max))
        if q_lo >= q_hi:
            q_lo = y_min
            q_hi = y_max * 0.5

        self._q_selector_lo = ax.axhline(
            q_lo, color=_CLR_LO, lw=1.8, ls='--', alpha=0.95, zorder=5)
        self._q_selector_hi = ax.axhline(
            q_hi, color=_CLR_HI, lw=1.8, ls='--', alpha=0.95, zorder=5)
        self._q_band = ax.axhspan(q_lo, q_hi, alpha=0.12, color='white', zorder=4)

        trans = ax.get_yaxis_transform()
        self._q_lo_label = ax.text(
            1.02, q_lo, f'{q_lo:.4f}', color=_CLR_LO,
            transform=trans, va='center', fontsize=8, clip_on=False, zorder=6)
        self._q_hi_label = ax.text(
            1.02, q_hi, f'{q_hi:.4f}', color=_CLR_HI,
            transform=trans, va='center', fontsize=8, clip_on=False, zorder=6)

        self._update_polar_status(q_lo, q_hi)

        self._drag_cid_press   = self.canvas.mpl_connect(
            'button_press_event',   self._on_q_press)
        self._drag_cid_motion  = self.canvas.mpl_connect(
            'motion_notify_event',  self._on_q_motion)
        self._drag_cid_release = self.canvas.mpl_connect(
            'button_release_event', self._on_q_release)
        self._drag_cid_hover   = self.canvas.mpl_connect(
            'motion_notify_event',  self._on_q_hover)

    def _disconnect_q_selector(self):
        for attr in ('_drag_cid_press', '_drag_cid_motion',
                     '_drag_cid_release', '_drag_cid_hover'):
            cid = getattr(self, attr, None)
            if cid is not None:
                try:
                    self.canvas.mpl_disconnect(cid)
                except Exception:
                    pass
                setattr(self, attr, None)
        self._dragging        = None
        self._polar_ax        = None
        self._q_selector_lo   = None
        self._q_selector_hi   = None
        self._q_band          = None
        self._q_lo_label      = None
        self._q_hi_label      = None

    def _line_y_pix(self, line) -> float:
        q_val = line.get_ydata()[0]
        return self._polar_ax.transData.transform([0, q_val])[1]

    def _on_q_press(self, event):
        if event.button != 1 or event.inaxes != self._polar_ax:
            return
        if self._q_selector_lo is None:
            return
        y_pix   = event.y
        dist_lo = abs(self._line_y_pix(self._q_selector_lo) - y_pix)
        dist_hi = abs(self._line_y_pix(self._q_selector_hi) - y_pix)
        if min(dist_lo, dist_hi) <= _DRAG_TOL_PX:
            self._dragging = 'lo' if dist_lo <= dist_hi else 'hi'

    def _on_q_release(self, event):
        if self._dragging is None:
            return
        self._dragging = None
        self.canvas.setCursor(QCursor(Qt.ArrowCursor))
        if self._q_selector_lo is not None:
            q_lo = self._q_selector_lo.get_ydata()[0]
            q_hi = self._q_selector_hi.get_ydata()[0]
            self.q_lo_spin.blockSignals(True)
            self.q_hi_spin.blockSignals(True)
            self.q_lo_spin.setValue(q_lo)
            self.q_hi_spin.setValue(q_hi)
            self.q_lo_spin.blockSignals(False)
            self.q_hi_spin.blockSignals(False)

    def _on_q_motion(self, event):
        if self._dragging is None or event.inaxes != self._polar_ax:
            return
        if event.ydata is None or event.ydata <= 0:
            return

        ax    = self._polar_ax
        q_lo  = self._q_selector_lo.get_ydata()[0]
        q_hi  = self._q_selector_hi.get_ydata()[0]
        y_min, y_max = ax.get_ylim()
        new_q = float(np.clip(event.ydata, y_min * 1.001, y_max * 0.999))

        if self._dragging == 'lo':
            new_q = min(new_q, q_hi * 0.99)
            q_lo  = new_q
            self._q_selector_lo.set_ydata([q_lo, q_lo])
            if self._q_lo_label:
                self._q_lo_label.set_position((1.02, q_lo))
                self._q_lo_label.set_text(f'{q_lo:.4f}')
        else:
            new_q = max(new_q, q_lo * 1.01)
            q_hi  = new_q
            self._q_selector_hi.set_ydata([q_hi, q_hi])
            if self._q_hi_label:
                self._q_hi_label.set_position((1.02, q_hi))
                self._q_hi_label.set_text(f'{q_hi:.4f}')

        if self._q_band is not None:
            try:
                self._q_band.remove()
            except Exception:
                pass
        self._q_band = ax.axhspan(q_lo, q_hi, alpha=0.12, color='white', zorder=4)
        self._update_polar_status(q_lo, q_hi)
        self.canvas.draw_idle()

    def _on_q_hover(self, event):
        if self._dragging is not None:
            return
        if self._q_selector_lo is None or event.inaxes != self._polar_ax:
            self.canvas.setCursor(QCursor(Qt.ArrowCursor))
            return
        y_pix = event.y
        near  = (
            abs(self._line_y_pix(self._q_selector_lo) - y_pix) <= _DRAG_TOL_PX
            or abs(self._line_y_pix(self._q_selector_hi) - y_pix) <= _DRAG_TOL_PX
        )
        self.canvas.setCursor(
            QCursor(Qt.SizeVerCursor if near else Qt.ArrowCursor))

    def _sync_selector_from_spinboxes(self):
        if self._q_selector_lo is None:
            return
        q_lo = self.q_lo_spin.value()
        q_hi = self.q_hi_spin.value()
        if q_lo >= q_hi:
            return
        ax = self._polar_ax
        self._q_selector_lo.set_ydata([q_lo, q_lo])
        self._q_selector_hi.set_ydata([q_hi, q_hi])
        if self._q_band is not None:
            try:
                self._q_band.remove()
            except Exception:
                pass
        self._q_band = ax.axhspan(q_lo, q_hi, alpha=0.12, color='white', zorder=4)
        if self._q_lo_label:
            self._q_lo_label.set_position((1.02, q_lo))
            self._q_lo_label.set_text(f'{q_lo:.4f}')
        if self._q_hi_label:
            self._q_hi_label.set_position((1.02, q_hi))
            self._q_hi_label.set_text(f'{q_hi:.4f}')
        self._update_polar_status(q_lo, q_hi)
        self.canvas.draw_idle()

    def _update_polar_status(self, q_lo: float, q_hi: float):
        if hasattr(self, '_polar_lo_label'):
            self._polar_lo_label.setText(f'{q_lo:.4f} nm⁻¹')
        if hasattr(self, '_polar_hi_label'):
            self._polar_hi_label.setText(f'{q_hi:.4f} nm⁻¹')

    def _set_selector_visible(self, visible: bool):
        for artist in (self._q_selector_lo, self._q_selector_hi,
                       self._q_band, self._q_lo_label, self._q_hi_label):
            if artist is not None:
                artist.set_visible(visible)

    # ── export ────────────────────────────────────────────────────────────────

    def _export_png(self):
        """Open the shared ExportSettingsDialog, then save the figure."""
        is_polar    = (self.view_combo.currentIndex() == VIEW_POLAR)
        hide_overlay = (
            is_polar
            and self._q_selector_lo is not None
            and not self._polar_export_overlay_check.isChecked()
        )

        if hide_overlay:
            self._set_selector_visible(False)
            self.canvas.draw()

        try:
            from dialogs.export_dialog import ExportSettingsDialog
            dlg = ExportSettingsDialog(
                self.parent(),
                self._export_settings,
                main_figure=self.figure,
            )
            if dlg.exec():
                self._export_settings = dlg.get_settings()
                self._do_export(self._export_settings)
        except ImportError:
            # fallback: simple file dialog
            self._export_simple()
        finally:
            if hide_overlay:
                self._set_selector_visible(True)
                self.canvas.draw_idle()

    def _do_export(self, settings: dict):
        """Perform the actual figure save after ExportSettingsDialog.accept()."""
        fmt        = settings.get('format', 'PNG').lower()
        ext_filters = {
            'png':  'PNG (*.png)',
            'svg':  'SVG (*.svg)',
            'pdf':  'PDF (*.pdf)',
            'tiff': 'TIFF (*.tiff *.tif)',
            'eps':  'EPS (*.eps)',
        }
        path, _ = QFileDialog.getSaveFileName(
            self, tr('2d.export_png'), '',
            ext_filters.get(fmt, 'All Files (*.*)')
        )
        if not path:
            return
        if not path.lower().endswith(f'.{fmt}'):
            path = f'{path}.{fmt}'

        orig_size = self.figure.get_size_inches()
        self.figure.set_size_inches(settings['width'], settings['height'])
        try:
            kw = {
                'dpi': settings.get('dpi', 300),
                'bbox_inches': 'tight' if settings.get('tight_layout', True) else None,
            }
            if fmt == 'png':
                if settings.get('transparent', False):
                    kw['transparent'] = True
                else:
                    kw['facecolor'] = settings.get('bg_color', '#2b2b2b')
                if 'png_compression' in settings:
                    kw['pil_kwargs'] = {'compress_level': settings['png_compression']}
            elif fmt == 'svg':
                import matplotlib as _mpl
                _mpl.rcParams['svg.fonttype'] = (
                    'path' if settings.get('svg_text_as_path') else 'none')
            elif fmt == 'pdf':
                meta = {}
                if settings.get('meta_title'):  meta['Title']  = settings['meta_title']
                if settings.get('meta_author'): meta['Author'] = settings['meta_author']
                if meta:
                    kw['metadata'] = meta

            self.figure.savefig(path, **kw)
            QMessageBox.information(
                self, tr('messages.success'),
                tr('messages.export_success_file', filename=path))
        except Exception as e:
            QMessageBox.critical(
                self, tr('messages.error'),
                tr('messages.export_error_msg', error=str(e)))
        finally:
            self.figure.set_size_inches(orig_size)

    def _export_simple(self):
        """Fallback export without ExportSettingsDialog."""
        path, _ = QFileDialog.getSaveFileName(
            self, tr('2d.export_png'), '', 'PNG (*.png);;SVG (*.svg)')
        if not path:
            return
        try:
            self.figure.savefig(path, dpi=150, bbox_inches='tight',
                                facecolor=self.figure.get_facecolor())
            QMessageBox.information(
                self, tr('messages.success'),
                tr('messages.export_success_file', filename=path))
        except Exception as e:
            QMessageBox.critical(
                self, tr('messages.error'),
                tr('messages.export_error_msg', error=str(e)))

    def _export_ascii(self):
        if self._last_result is None:
            return
        kind = self._last_result[0]
        if kind not in ('azimuthal', 'sector'):
            QMessageBox.information(
                self, tr('messages.info'), tr('2d.export_ascii_1d_only'))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, tr('2d.export_ascii'), '', 'DAT (*.dat);;TXT (*.txt)')
        if not path:
            return
        try:
            if kind == 'azimuthal':
                _, phi, I, q_lo, q_hi = self._last_result
                corr = self._sin_y_label()
                header = (
                    f"# Azimuthal profile: {self.dataset.name}\n"
                    f"# q-ring: {q_lo:.4f} to {q_hi:.4f} nm^-1\n"
                    f"# sin-correction: {corr if corr else 'none'}\n"
                    f"# phi [deg]\tI{corr} [a.u.]\n"
                )
                data = np.column_stack([phi, I])
                fmt  = ['%.4f', '%.6e']
            else:
                _, q, I, I_err, phi_lo, phi_hi = self._last_result
                header = (
                    f"# Sector integral: {self.dataset.name}\n"
                    f"# sector: {phi_lo:.1f} to {phi_hi:.1f} deg\n"
                    f"# q [nm^-1]\tI [a.u.]\tsigma\n"
                )
                data = np.column_stack([q, I, I_err])
                fmt  = ['%.6e', '%.6e', '%.6e']

            with open(path, 'w', encoding='utf-8') as f:
                f.write(header)
                np.savetxt(f, data, fmt=fmt, delimiter='\t')

            QMessageBox.information(
                self, tr('messages.success'),
                tr('messages.export_success_file', filename=path))
        except Exception as e:
            QMessageBox.critical(
                self, tr('messages.error'),
                tr('messages.export_error_msg', error=str(e)))

    # ── Add to 1D Plot ────────────────────────────────────────────────────────

    def _add_to_1d(self):
        if self._last_result is None:
            self._update_plot()
        if self._last_result is None:
            return
        kind = self._last_result[0]
        try:
            from core.models import DataSet
            import tempfile, os

            if kind == 'azimuthal':
                _, phi, I, q_lo, q_hi = self._last_result
                corr = self._sin_y_label()
                name = (
                    f"{self.dataset.name}_azim_{q_lo:.3f}-{q_hi:.3f}"
                    + (corr.replace('/', '_div_').replace('·', '_mul_') if corr else '')
                )
                header   = f"# phi [deg]\tI{corr} [a.u.]\n"
                data_arr = np.column_stack([phi, I])
                fmt      = ['%.4f', '%.6e']
            elif kind == 'sector':
                _, q, I, I_err, phi_lo, phi_hi = self._last_result
                name     = f"{self.dataset.name}_sector_{phi_lo:.0f}-{phi_hi:.0f}deg"
                header   = f"# q [nm^-1]\tI [a.u.]\tsigma\n"
                data_arr = np.column_stack([q, I, I_err])
                fmt      = ['%.6e', '%.6e', '%.6e']
            else:
                return

            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix='.dat', prefix='scatterforge_proj_')
            os.close(tmp_fd)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(header)
                np.savetxt(f, data_arr, fmt=fmt, delimiter='\t')

            ds = DataSet(tmp_path, name=name, apply_auto_style=False)
            ds.display_label = name
            self.projection_ready.emit(ds)
            QMessageBox.information(
                self, tr('messages.success'),
                tr('2d.added_to_1d', name=name))
        except Exception as e:
            QMessageBox.critical(self, tr('messages.error'), str(e))


# ── module-level helper ───────────────────────────────────────────────────────

def _style_ax(ax):
    """Dark-theme axis styling."""
    ax.tick_params(colors='white', which='both')
    for spine in ax.spines.values():
        spine.set_edgecolor('#555555')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    ax.figure.set_facecolor('#2b2b2b')


def _style_cbar(cbar):
    """Apply white text/tick styling to a matplotlib Colorbar."""
    cbar.ax.yaxis.set_tick_params(colors='white', which='both')
    cbar.ax.tick_params(colors='white', which='both')
    for spine in cbar.ax.spines.values():
        spine.set_edgecolor('#555555')
    cbar.set_label(cbar.ax.get_ylabel(), color='white')
    # label is stored on the long axis
    cbar.ax.yaxis.label.set_color('white')
