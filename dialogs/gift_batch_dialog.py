"""
Serienauswertung (v7.13, bewusst rudimentär): wendet die Einstellungen des IFT/GIFT-Dialogs
auf mehrere geladene Datensätze an (analysis.gift.batch), exportiert je Datensatz mit
eigenem Sidecar und schreibt eine Übersichtstabelle (CSV). Optional wird Dmax je Datensatz
vorgeschlagen (Explorer) und die Ergebnisse werden als Gruppen übernommen.
"""

import time
from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QComboBox, QCheckBox,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter, QWidget, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QThread

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from i18n import tr
from analysis.gift.batch import (BatchItem, run_batch, write_summary, BatchCancelled,
                                 DMAX_FIXED, DMAX_SUGGEST)
from analysis.gift.pipeline import RESULT_SUBDIR


class _BatchWorker(QThread):
    progress = Signal(int, int, str)
    done = Signal(object)
    failed = Signal(str)

    CANCELLED = '__cancelled__'

    def __init__(self, kwargs, parent=None):
        super().__init__(parent)
        self.kwargs = kwargs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _cb(self, k, n, name):
        self.progress.emit(k, n, name)
        return not self._cancel

    def run(self):
        try:
            entries = run_batch(**self.kwargs, progress=self._cb)
        except BatchCancelled:
            self.failed.emit(self.CANCELLED)
            return
        except (ValueError, OSError) as e:
            self.failed.emit(str(e))
            return
        self.done.emit(entries)


class GiftBatchDialog(QDialog):
    """Serienauswertung mit den aktuellen Einstellungen des GIFT-Dialogs."""

    def __init__(self, gift_dialog, datasets):
        super().__init__(gift_dialog)
        self.gift = gift_dialog
        self.datasets = [ds for ds in datasets if getattr(ds, 'filepath', None)]
        self.setWindowTitle(tr('gift.batch_title'))
        self.resize(1100, 720)
        self.setModal(False)
        self._worker = None
        self.entries = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        hint = QLabel(tr('gift.batch_hint'))
        hint.setWordWrap(True)
        root.addWidget(hint)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.ds_list = QListWidget()
        for ds in self.datasets:
            item = QListWidgetItem(ds.display_label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if ds is self.gift.dataset else Qt.Unchecked)
            item.setToolTip(str(ds.filepath))
            self.ds_list.addItem(item)
        lv.addWidget(self.ds_list, 1)
        row = QHBoxLayout()
        for text, state in ((tr('gift.batch_all'), Qt.Checked), (tr('gift.batch_none'), Qt.Unchecked)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, st=state: self._check_all(st))
            row.addWidget(b)
        lv.addLayout(row)
        self.dmax_combo = QComboBox()
        self.dmax_combo.addItem(tr('gift.batch_dmax_suggest'), DMAX_SUGGEST)
        self.dmax_combo.addItem(tr('gift.batch_dmax_fixed'), DMAX_FIXED)
        self.dmax_combo.setToolTip(tr('gift.batch_dmax_tooltip'))
        lv.addWidget(self.dmax_combo)
        self.groups_check = QCheckBox(tr('gift.batch_groups'))
        lv.addWidget(self.groups_check)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [tr('gift.dataset'), 'Dmax / nm', 'Rg / nm', 'I(0)', 'MD', tr('gift.metric.oscillation'),
             tr('gift.metric.n_peaks'), tr('gift.batch_status')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        rv.addWidget(self.table, 1)
        self.fig = Figure(figsize=(6, 4), layout='tight')
        self.canvas = FigureCanvasQTAgg(self.fig)
        rv.addWidget(NavigationToolbar2QT(self.canvas, right))
        rv.addWidget(self.canvas, 2)
        split.addWidget(right)
        split.setSizes([300, 800])

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.status)
        btns = QHBoxLayout()
        self.start_btn = QPushButton(tr('gift.batch_start'))
        self.start_btn.clicked.connect(self._start)
        btns.addWidget(self.start_btn)
        self.cancel_btn = QPushButton(tr('gift.cancel'))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(lambda: self._worker and self._worker.cancel())
        btns.addWidget(self.cancel_btn)
        btns.addStretch()
        close = QPushButton(tr('common.close'))
        close.clicked.connect(self.close)
        btns.addWidget(close)
        root.addLayout(btns)

    def _check_all(self, state):
        for i in range(self.ds_list.count()):
            self.ds_list.item(i).setCheckState(state)

    def _selected(self):
        return [ds for i, ds in enumerate(self.datasets)
                if self.ds_list.item(i).checkState() == Qt.Checked]

    def _items(self, datasets):
        from dialogs.gift_dialog import dataset_arrays
        g = self.gift
        factor = g._q_factor()
        keep = g.keep_nonpositive_check.isChecked()
        items = []
        for ds in datasets:
            q, I, err = dataset_arrays(ds)
            mask = np.ones(len(q), bool) if keep else I > 0
            err = err[mask] if err is not None and np.all(err[mask] > 0) else None
            meta = {'dataset_name': ds.name, 'col_x': ds.col_x, 'col_y': ds.col_y,
                    'col_err': ds.col_err, 'nonpositive_intensities': 'kept' if keep else 'removed',
                    'q_unit_file': 'nm^-1' if factor == 1.0 else 'A^-1',
                    'q_conversion_factor': factor, 'batch': True}
            items.append(BatchItem(ds.display_label, Path(ds.filepath), factor * q[mask],
                                   I[mask], err, meta))
        return items

    def _start(self):
        datasets = self._selected()
        if not datasets or self._worker is not None:
            return
        g = self.gift
        try:
            items = self._items(datasets)
        except (ValueError, OSError) as e:
            QMessageBox.critical(self, tr('messages.error'), str(e))
            return
        self._datasets_run = datasets
        kwargs = dict(items=items, settings=g._settings(), q_range=g._qrange_settings(),
                      gift_settings=g._gift_settings() if g._model_key() != 'none' else None,
                      sigma_relative=g._sigma_relative(), dmax_mode=self.dmax_combo.currentData(),
                      export=True, write_w3c=g.w3c_check.isChecked())
        self._worker = _BatchWorker(kwargs, self)
        self._worker.progress.connect(
            lambda k, n, name: self.status.setText(tr('gift.batch_running', k=k + 1, n=n, name=name)))
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._t0 = time.perf_counter()
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self._worker.start()

    def _on_finished(self):
        self._worker = None
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _on_failed(self, message):
        self.status.setText(tr('gift.batch_cancelled') if message == _BatchWorker.CANCELLED
                            else f"<span style='color:#c62828'>{tr('gift.error')}: {message}</span>")

    def _on_done(self, entries):
        self.entries = entries
        first = Path(entries[0].item.source_file)
        out = first.parent / RESULT_SUBDIR / f"GIFT_Serie_{time.strftime('%Y%m%d-%H%M%S')}.csv"
        try:
            path = write_summary(entries, out)
            summary = tr('gift.batch_done', n=len(entries), t=f"{time.perf_counter() - self._t0:.1f}",
                         path=str(path))
        except OSError as e:
            summary = f"{tr('gift.error')}: {e}"
        self.status.setText(summary)
        self._fill_table()
        self._plot()
        if self.groups_check.isChecked():
            for e, ds in zip(entries, self._datasets_run):
                if e.analysis is not None and e.paths:
                    self.gift.results_applied.emit({
                        'paths': e.paths, 'record_id': e.analysis.record.record_id,
                        'dataset': ds, 'worst_level': e.analysis.worst_level})

    def _fill_table(self):
        self.table.setRowCount(len(self.entries))
        for i, e in enumerate(self.entries):
            a = e.analysis
            if a is None:
                cells = [e.item.name, '', '', '', '', '', '', f"{tr('gift.error')}: {e.error}"]
            else:
                s, m = a.solution, a.metrics
                dmax = f"{s.settings.dmax:.4g}" + (' *' if e.dmax_suggested else '')
                cells = [e.item.name, dmax, f"{s.rg:.4g} ± {s.rg_err:.2g}", f"{s.i0:.4g}",
                         f"{s.md:.3g}", f"{m.get('oscillation', np.nan):.2f}",
                         f"{m.get('n_peaks', np.nan):.0f}", a.worst_level]
            for j, text in enumerate(cells):
                self.table.setItem(i, j, QTableWidgetItem(text))

    def _plot(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        for e in self.entries:
            a = e.analysis
            if a is None:
                continue
            s = a.solution
            norm = s.i0 if s.i0 > 0 else np.max(np.abs(s.pr))
            ax.plot(s.r, s.pr / norm, lw=1.5, label=e.item.name)
        ax.axhline(0, color='k', lw=0.6)
        ax.set_xlabel('r / nm')
        ax.set_ylabel('p(r) / I(0)')
        ax.set_title(tr('gift.batch_plot_title'), fontsize=9)
        ax.legend(fontsize=7)
        self.canvas.draw_idle()

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait(10000)
        super().closeEvent(event)
