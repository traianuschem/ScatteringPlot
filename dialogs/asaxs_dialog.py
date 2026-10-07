"""
ASAXS Analysis Dialog (v8.1)

Nicht-modaler Dialog für abgeleitete Größen aus separierten ASAXS-Termen
(Rechnung: analysis/asaxs.py):
  - I_A / I_N          (Verhältnis anomaler zu nicht-resonanter Streuung)
  - I_cross / I_N
  - Korrelation I_cross / √(I_N·I_A)  (|c| ≤ 1 als Konsistenzcheck)
  - Cauchy-Schwarz √(I_N·I_A) / |I_cross|  (muss überall ≥ 1 sein)

Proben werden automatisch aus den geladenen Datensätzen erkannt (Term-Typ und
Dateiname-Suffix _IN/_IA/_Icross); die Zuordnung ist pro Probe korrigierbar.
„In Datentree übernehmen" legt die Ergebnisse als abgeleitete Datensätze an
(Signal `datasets_ready`), die im Hauptfenster in einem Ratio-Panel erscheinen.
"""

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QComboBox,
    QLineEdit, QCheckBox, QPushButton, QTableWidget, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QSplitter, QWidget
)
from PySide6.QtCore import Qt, Signal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from analysis.asaxs import (
    Curve, compute, pair_asaxs_terms, QUANTITIES, QUANTITY_LABEL, QUANTITY_SUFFIX,
    QUANTITY_CORRELATION, QUANTITY_CAUCHY_SCHWARZ, REQUIRED_TERMS, TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS, TERM_RATIO,
)
from i18n import tr

_TERM_COLUMNS = (TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS)
_TERM_LABELS = {TERM_NORMAL: '$I_N$', TERM_ANOMALOUS: '$I_A$', TERM_CROSS: '$I_{cross}$'}
_TERM_COLORS = {TERM_NORMAL: '#1f77b4', TERM_ANOMALOUS: '#d62728', TERM_CROSS: '#2ca02c'}


class AsaxsDialog(QDialog):
    """Nicht-modaler Dialog für ASAXS-Verhältnisse und -Korrelation."""

    datasets_ready = Signal(object)   # dict: group_name, datasets, quantity

    def __init__(self, datasets_provider, parent=None, preselect=None):
        """
        Args:
            datasets_provider: Callable → Liste aller geladenen 1D-Datensätze
            preselect: optionale Datensätze (z. B. einer Gruppe); die zugehörige Probe
                       wird vorausgewählt
        """
        super().__init__(parent)
        self.setWindowTitle(tr("asaxs.title"))
        self.resize(1180, 760)
        self.setModal(False)
        self._provider = datasets_provider
        self._datasets = []
        self._samples = []          # Liste von Probennamen (Tabellenzeilen)
        self._combos = {}           # (Zeile, Term) → QComboBox
        self._last_results = {}     # Probe → DerivedCurve

        self._build_ui()
        self.refresh_samples(preselect)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        samples_box = QGroupBox(tr("asaxs.samples.title"))
        samples_layout = QVBoxLayout(samples_box)
        self.table = QTableWidget(0, 1 + len(_TERM_COLUMNS))
        self.table.setHorizontalHeaderLabels([tr("asaxs.samples.sample"), 'I_N', 'I_A', 'I_cross'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._update_plot)
        samples_layout.addWidget(self.table)
        redetect_btn = QPushButton(tr("asaxs.samples.redetect"))
        redetect_btn.setToolTip(tr("asaxs.samples.redetect_tooltip"))
        redetect_btn.clicked.connect(lambda: self.refresh_samples())
        samples_layout.addWidget(redetect_btn)
        left_layout.addWidget(samples_box, 1)

        calc_box = QGroupBox(tr("asaxs.calc.title"))
        calc = QGridLayout(calc_box)
        calc.addWidget(QLabel(tr("asaxs.calc.quantity")), 0, 0)
        self.quantity_combo = QComboBox()
        for q in QUANTITIES:
            self.quantity_combo.addItem(tr(f"asaxs.quantity.{q}"), q)
        self.quantity_combo.currentIndexChanged.connect(self._update_plot)
        calc.addWidget(self.quantity_combo, 0, 1, 1, 3)

        calc.addWidget(QLabel(tr("asaxs.calc.q_min")), 1, 0)
        self.qmin_edit = QLineEdit()
        self.qmin_edit.setPlaceholderText(tr("asaxs.calc.q_auto"))
        self.qmin_edit.editingFinished.connect(self._update_plot)
        calc.addWidget(self.qmin_edit, 1, 1)
        calc.addWidget(QLabel(tr("asaxs.calc.q_max")), 1, 2)
        self.qmax_edit = QLineEdit()
        self.qmax_edit.setPlaceholderText(tr("asaxs.calc.q_auto"))
        self.qmax_edit.editingFinished.connect(self._update_plot)
        calc.addWidget(self.qmax_edit, 1, 3)

        self.errors_check = QCheckBox(tr("asaxs.calc.show_errors"))
        self.errors_check.setChecked(True)
        self.errors_check.toggled.connect(self._update_plot)
        calc.addWidget(self.errors_check, 2, 0, 1, 2)
        self.logy_check = QCheckBox(tr("asaxs.calc.log_y"))
        self.logy_check.setToolTip(tr("asaxs.calc.log_y_tooltip"))
        self.logy_check.toggled.connect(self._update_plot)
        calc.addWidget(self.logy_check, 2, 2, 1, 2)
        left_layout.addWidget(calc_box)

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        left_layout.addWidget(self.info_label)

        btns = QGridLayout()
        apply_btn = QPushButton(tr("asaxs.apply_sample"))
        apply_btn.setToolTip(tr("asaxs.apply_tooltip"))
        apply_btn.clicked.connect(lambda: self._apply(all_samples=False))
        btns.addWidget(apply_btn, 0, 0)
        apply_all_btn = QPushButton(tr("asaxs.apply_all"))
        apply_all_btn.setToolTip(tr("asaxs.apply_tooltip"))
        apply_all_btn.clicked.connect(lambda: self._apply(all_samples=True))
        btns.addWidget(apply_all_btn, 0, 1)
        ascii_btn = QPushButton(tr("asaxs.export_ascii"))
        ascii_btn.clicked.connect(self._export_ascii)
        btns.addWidget(ascii_btn, 1, 0)
        png_btn = QPushButton(tr("asaxs.export_png"))
        png_btn.clicked.connect(self._export_png)
        btns.addWidget(png_btn, 1, 1)
        close_btn = QPushButton(tr("common.close"))
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn, 2, 0, 1, 2)
        left_layout.addLayout(btns)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(8, 7), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        right_layout.addWidget(self.canvas)
        right_layout.addWidget(NavigationToolbar2QT(self.canvas, right))
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 780])

    # ── Proben ───────────────────────────────────────────────────────────────

    def refresh_samples(self, preselect=None):
        """Liest die geladenen Datensätze neu ein und ordnet die ASAXS-Terme den Proben zu."""
        self._datasets = [ds for ds in self._provider() if getattr(ds, 'data_loaded', False)
                          and getattr(ds, 'data_term', '') != TERM_RATIO]
        pairs = pair_asaxs_terms(self._datasets)
        self._samples = list(pairs.keys())

        self.table.blockSignals(True)
        self.table.setRowCount(len(self._samples))
        self._combos.clear()
        for row, sample in enumerate(self._samples):
            label = QLabel(sample)
            label.setContentsMargins(4, 0, 4, 0)
            self.table.setCellWidget(row, 0, label)
            for col, term in enumerate(_TERM_COLUMNS, start=1):
                combo = QComboBox()
                combo.addItem("—", None)
                for i, ds in enumerate(self._datasets):
                    combo.addItem(ds.display_label or ds.name, i)
                chosen = pairs[sample].get(term)
                if chosen is not None:
                    combo.setCurrentIndex(combo.findData(self._datasets.index(chosen)))
                combo.currentIndexChanged.connect(self._update_plot)
                self.table.setCellWidget(row, col, combo)
                self._combos[(row, term)] = combo
        self.table.blockSignals(False)

        row = 0
        if preselect:
            for i, sample in enumerate(self._samples):
                if any(ds in preselect for ds in pairs[sample].values()):
                    row = i
                    break
        if self._samples:
            self.table.selectRow(row)
        self._update_plot()

    def _current_row(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return rows[0].row() if rows else (0 if self._samples else None)

    def _terms_for_row(self, row):
        """{Term: DataSet} der Probe in Zeile `row` (nur zugeordnete Terme)."""
        terms = {}
        for term in _TERM_COLUMNS:
            idx = self._combos[(row, term)].currentData()
            if idx is not None:
                terms[term] = self._datasets[idx]
        return terms

    def _q_range(self):
        def val(edit):
            try:
                return float(edit.text()) if edit.text().strip() else None
            except ValueError:
                return None
        return val(self.qmin_edit), val(self.qmax_edit)

    def _quantity(self):
        return self.quantity_combo.currentData()

    def _compute_row(self, row):
        """Berechnet die gewählte Größe für eine Probe (None, wenn Terme fehlen)."""
        terms = self._terms_for_row(row)
        curves = {t: Curve.from_dataset(ds) for t, ds in terms.items()}
        try:
            return compute(self._quantity(), curves, self._q_range())
        except KeyError:
            return None

    # ── Plot ─────────────────────────────────────────────────────────────────

    def _update_plot(self, *args):
        self.figure.clear()
        row = self._current_row()
        if row is None:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, tr("asaxs.no_samples"), ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            self.info_label.setText(tr("asaxs.no_samples"))
            self.canvas.draw_idle()
            return

        quantity = self._quantity()
        terms = self._terms_for_row(row)
        show_err = self.errors_check.isChecked()
        gs = GridSpec(2, 1, figure=self.figure, height_ratios=[3, 2], hspace=0.08)
        ax_terms = self.figure.add_subplot(gs[0])
        ax_ratio = self.figure.add_subplot(gs[1], sharex=ax_terms)

        # Oben: die Terme (symlog, damit auch negative I_cross-Werte sichtbar sind)
        max_abs = []
        for term in _TERM_COLUMNS:
            ds = terms.get(term)
            if ds is None:
                continue
            ax_terms.plot(ds.x, ds.y, 'o', ms=3, color=_TERM_COLORS[term],
                          label=f"{_TERM_LABELS[term]}  ({ds.display_label or ds.name})")
            if show_err and ds.y_err is not None:
                ax_terms.fill_between(ds.x, ds.y - ds.y_err, ds.y + ds.y_err,
                                      color=_TERM_COLORS[term], alpha=0.2)
            finite = np.abs(ds.y[np.isfinite(ds.y) & (ds.y != 0)])
            if finite.size:
                max_abs.append(finite.max())
        linthresh = 10 ** (np.floor(np.log10(max(max_abs))) - 4) if max_abs else 1e-3
        ax_terms.set_yscale('symlog', linthresh=linthresh)
        ax_terms.set_xscale('log')
        ax_terms.set_ylabel('I / cm⁻¹')
        ax_terms.grid(True, which='major', alpha=0.4)
        if terms:
            ax_terms.legend(fontsize=8, loc='best')
        ax_terms.tick_params(axis='x', labelbottom=False)
        ax_terms.set_title(self._samples[row], fontsize=11)

        # Unten: abgeleitete Größe
        result = self._compute_row(row)
        self._last_results = {self._samples[row]: result} if result is not None else {}
        ax_ratio.set_xlabel('q / nm⁻¹')
        ax_ratio.set_ylabel(QUANTITY_LABEL[quantity])
        ax_ratio.grid(True, which='major', alpha=0.4)
        if result is None:
            missing = [t for t in REQUIRED_TERMS[quantity] if t not in terms]
            text = tr("asaxs.missing_terms", terms=", ".join(_TERM_LABELS[t] for t in missing))
            ax_ratio.text(0.5, 0.5, text, ha='center', va='center', transform=ax_ratio.transAxes)
            self.info_label.setText(text)
        else:
            ax_ratio.plot(result.x, result.y, 'o-', ms=3, lw=1, color='#444444')
            if show_err and result.err is not None:
                ax_ratio.fill_between(result.x, result.y - result.err, result.y + result.err,
                                      color='#444444', alpha=0.2)
            if quantity == QUANTITY_CORRELATION:
                for level in (-1.0, 1.0):
                    ax_ratio.axhline(level, color='gray', lw=0.8, ls='--')
            if quantity == QUANTITY_CAUCHY_SCHWARZ:
                # Zulässig ist R ≥ 1; der Bereich darunter verletzt die Ungleichung
                ax_ratio.axhline(1.0, color='#d62728', lw=1.0, ls='--')
                ax_ratio.axhspan(0.0, 1.0, color='#d62728', alpha=0.08, lw=0)
            ax_ratio.axhline(0.0, color='gray', lw=0.6, ls=':')
            if self.logy_check.isChecked() and np.all(result.y[np.isfinite(result.y)] > 0):
                ax_ratio.set_yscale('log')
            self.info_label.setText(self._info_text(result))
        self.canvas.draw_idle()

    def _info_text(self, result):
        lines = [tr("asaxs.info.points", n=len(result.x))]
        if len(result.x):
            lines.append(tr("asaxs.info.range", qmin=f"{result.x.min():.4g}", qmax=f"{result.x.max():.4g}"))
            finite = result.y[np.isfinite(result.y)]
            if finite.size:
                lines.append(tr("asaxs.info.median", value=f"{np.median(finite):.4g}"))
        if result.n_interpolated:
            lines.append(tr("asaxs.info.interpolated", n=result.n_interpolated))
        frac = result.info.get('fraction_above_one')
        if frac:
            lines.append(tr("asaxs.info.above_one", percent=f"{100 * frac:.0f}"))
        if result.quantity == QUANTITY_CAUCHY_SCHWARZ and len(result.x):
            frac_below = result.info.get('fraction_below_one', 0.0)
            lines.append(tr("asaxs.info.below_one", percent=f"{100 * frac_below:.0f}") if frac_below
                         else tr("asaxs.info.cs_ok"))
        return "\n".join(lines)

    # ── Übernehmen / Export ──────────────────────────────────────────────────

    def _results_for(self, all_samples):
        rows = range(len(self._samples)) if all_samples else [self._current_row()]
        out = []
        for row in rows:
            if row is None:
                continue
            result = self._compute_row(row)
            if result is not None and len(result.x):
                out.append((row, self._samples[row], result))
        return out

    def _apply(self, all_samples):
        from core.models import DataSet
        results = self._results_for(all_samples)
        if not results:
            QMessageBox.information(self, tr("asaxs.title"), tr("asaxs.nothing_to_apply"))
            return
        quantity = self._quantity()
        datasets = []
        for row, sample, result in results:
            sources = {term: {'name': ds.name, 'filepath': str(ds.filepath)}
                       for term, ds in self._terms_for_row(row).items()}
            ds = DataSet.from_arrays(
                result.x, result.y, result.err,
                name=f"{sample}_{QUANTITY_SUFFIX[quantity]}",
                data_term=TERM_RATIO,
                derived_from={'analysis': 'asaxs', 'quantity': quantity, 'sample': sample,
                              'q_range': list(self._q_range()), 'sources': sources},
            )
            ds.display_label = f"{sample}: {QUANTITY_LABEL[quantity]}"
            datasets.append(ds)
        self.datasets_ready.emit({
            'group_name': tr("asaxs.group_name", quantity=tr(f"asaxs.quantity.{quantity}")),
            'datasets': datasets,
            'quantity': quantity,
            'ylabel': QUANTITY_LABEL[quantity],
        })
        QMessageBox.information(self, tr("asaxs.title"), tr("asaxs.applied", n=len(datasets)))

    def _export_ascii(self):
        results = self._results_for(all_samples=False)
        if not results:
            QMessageBox.information(self, tr("asaxs.title"), tr("asaxs.nothing_to_apply"))
            return
        _, sample, result = results[0]
        quantity = self._quantity()
        path, _ = QFileDialog.getSaveFileName(
            self, tr("asaxs.export_ascii"), f"{sample}_{QUANTITY_SUFFIX[quantity]}.dat",
            "ASCII (*.dat *.txt);;CSV (*.csv)")
        if not path:
            return
        columns = [result.x, result.y] + ([result.err] if result.err is not None else [])
        header = f"ScatterForge ASAXS: {tr(f'asaxs.quantity.{quantity}')} — {sample}\n" \
                 f"q [nm^-1]\t{QUANTITY_SUFFIX[quantity]}" + ("\tsigma" if result.err is not None else "")
        delimiter = ',' if path.lower().endswith('.csv') else '\t'
        try:
            np.savetxt(path, np.column_stack(columns), delimiter=delimiter, header=header, fmt='%.6e')
        except OSError as e:
            QMessageBox.critical(self, tr("messages.error"), str(e))

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("asaxs.export_png"), "asaxs.png", "PNG (*.png)")
        if path:
            try:
                self.figure.savefig(path, dpi=300, bbox_inches='tight')
            except OSError as e:
                QMessageBox.critical(self, tr("messages.error"), str(e))
