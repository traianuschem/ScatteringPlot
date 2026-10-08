"""
Plot Layout Dialog (v8.1)

Bearbeitet das Panel-Grid (angelehnt an LabPlots Worksheet-Layout):
- Grid-Größe (Zeilen × Spalten), Höhen- und Breitenverhältnisse
- Vorschau des Grids; Klick auf eine Zelle wählt das Panel
- Panel-Eigenschaften: Name, Typ, aktiv, Position/Span, geteilte X-Achse,
  Legende, Stacking und typ-spezifische Optionen (P(r)-Normierung,
  Significance-Fenster/-Schwellen, dlnI/dlnq-Glättung)

Der Dialog arbeitet auf einer Kopie des Layouts; OK ist nur bei gültigem Layout
(PlotLayout.validate()) möglich.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QTableWidget,
    QTableWidgetItem, QTableWidgetSelectionRange, QAbstractItemView, QHeaderView, QMenu, QMessageBox
)
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt

from core.panel_types import PANEL_TYPE_ORDER
from core.plot_layout import MAIN_ID, LEGEND_MODES
from i18n import tr
from dialogs.dialog_utils import fit_to_screen

# Hintergrundfarben der Panels in der Grid-Vorschau
_PREVIEW_COLORS = ['#3d6a9e', '#5b8c5a', '#9e6b3d', '#7b5ea7', '#3d8f8f', '#a14f5d', '#8a8a3d']


class PlotLayoutDialog(QDialog):
    """Dialog zum Bearbeiten des Panel-Grids"""

    def __init__(self, parent, layout, select_panel_id=None):
        super().__init__(parent)
        self.setWindowTitle(tr("layout_dialog.title"))
        fit_to_screen(self, 900, 560)
        self.layout_model = layout.copy()
        self._current_id = select_panel_id if self.layout_model.get(select_panel_id) else MAIN_ID
        self._loading = False
        self._sel_rect = None   # markierter Zellbereich (r0, c0, r1, c1) der Vorschau

        root = QVBoxLayout(self)
        body = QHBoxLayout()
        root.addLayout(body)

        body.addWidget(self._build_grid_group(), 1)
        body.addWidget(self._build_panel_group(), 1)

        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("color: #ff6b6b;")
        root.addWidget(self.validation_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self._load_grid()
        self._load_panel()
        self._refresh()

    # ── UI-Aufbau ────────────────────────────────────────────────────────────

    def _build_grid_group(self):
        group = QGroupBox(tr("layout_dialog.grid.title"))
        grid = QGridLayout(group)

        grid.addWidget(QLabel(tr("layout_dialog.grid.rows")), 0, 0)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 6)
        self.rows_spin.valueChanged.connect(self._on_grid_changed)
        grid.addWidget(self.rows_spin, 0, 1)

        grid.addWidget(QLabel(tr("layout_dialog.grid.cols")), 0, 2)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 6)
        self.cols_spin.valueChanged.connect(self._on_grid_changed)
        grid.addWidget(self.cols_spin, 0, 3)

        grid.addWidget(QLabel(tr("layout_dialog.grid.row_ratios")), 1, 0)
        self.row_ratios_edit = QLineEdit()
        self.row_ratios_edit.setToolTip(tr("layout_dialog.grid.ratios_tooltip"))
        self.row_ratios_edit.editingFinished.connect(self._on_ratios_changed)
        grid.addWidget(self.row_ratios_edit, 1, 1, 1, 3)

        grid.addWidget(QLabel(tr("layout_dialog.grid.col_ratios")), 2, 0)
        self.col_ratios_edit = QLineEdit()
        self.col_ratios_edit.setToolTip(tr("layout_dialog.grid.ratios_tooltip"))
        self.col_ratios_edit.editingFinished.connect(self._on_ratios_changed)
        grid.addWidget(self.col_ratios_edit, 2, 1, 1, 3)

        self.preview = QTableWidget()
        self.preview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview.cellClicked.connect(self._on_cell_clicked)
        self.preview.itemSelectionChanged.connect(self._on_selection_changed)
        self.preview.setMinimumHeight(220)
        grid.addWidget(self.preview, 3, 0, 1, 4)

        buttons = QHBoxLayout()
        add_btn = QPushButton(tr("layout_dialog.add_panel"))
        add_menu = QMenu(add_btn)
        for panel_type in PANEL_TYPE_ORDER:
            add_menu.addAction(panel_type, lambda pt=panel_type: self._add_panel(pt))
        add_btn.setMenu(add_menu)
        buttons.addWidget(add_btn)
        self.remove_btn = QPushButton(tr("layout_dialog.remove_panel"))
        self.remove_btn.clicked.connect(self._remove_panel)
        buttons.addWidget(self.remove_btn)
        grid.addLayout(buttons, 4, 0, 1, 4)

        merge_buttons = QHBoxLayout()
        self.merge_btn = QPushButton(tr("layout_dialog.merge_cells"))
        self.merge_btn.setToolTip(tr("layout_dialog.merge_cells_tooltip"))
        self.merge_btn.clicked.connect(self._merge_cells)
        merge_buttons.addWidget(self.merge_btn)
        self.split_btn = QPushButton(tr("layout_dialog.split_cells"))
        self.split_btn.setToolTip(tr("layout_dialog.split_cells_tooltip"))
        self.split_btn.clicked.connect(self._split_cells)
        merge_buttons.addWidget(self.split_btn)
        grid.addLayout(merge_buttons, 5, 0, 1, 4)
        return group

    def _build_panel_group(self):
        group = QGroupBox(tr("layout_dialog.panel.title"))
        form = QGridLayout(group)
        row = 0

        form.addWidget(QLabel(tr("layout_dialog.panel.select")), row, 0)
        self.panel_combo = QComboBox()
        self.panel_combo.currentIndexChanged.connect(self._on_panel_selected)
        form.addWidget(self.panel_combo, row, 1, 1, 3)
        row += 1

        form.addWidget(QLabel(tr("layout_dialog.panel.name")), row, 0)
        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self._on_panel_edited)
        form.addWidget(self.name_edit, row, 1, 1, 3)
        row += 1

        form.addWidget(QLabel(tr("layout_dialog.panel.type")), row, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(PANEL_TYPE_ORDER)
        self.type_combo.currentTextChanged.connect(self._on_panel_edited)
        form.addWidget(self.type_combo, row, 1, 1, 3)
        row += 1

        self.enabled_check = QCheckBox(tr("layout_dialog.panel.enabled"))
        self.enabled_check.toggled.connect(self._on_panel_edited)
        form.addWidget(self.enabled_check, row, 0, 1, 4)
        row += 1

        self.pos_spins = {}
        for i, key in enumerate(('row', 'col', 'rowspan', 'colspan')):
            r, c = row + i // 2, (i % 2) * 2
            form.addWidget(QLabel(tr(f"layout_dialog.panel.{key}")), r, c)
            spin = QSpinBox()
            spin.setRange(1, 6)
            spin.valueChanged.connect(self._on_panel_edited)
            form.addWidget(spin, r, c + 1)
            self.pos_spins[key] = spin
        row += 2

        form.addWidget(QLabel(tr("layout_dialog.panel.share_x")), row, 0)
        self.share_combo = QComboBox()
        self.share_combo.setToolTip(tr("layout_dialog.panel.share_x_tooltip"))
        self.share_combo.currentIndexChanged.connect(self._on_panel_edited)
        form.addWidget(self.share_combo, row, 1, 1, 3)
        row += 1

        form.addWidget(QLabel(tr("layout_dialog.panel.legend")), row, 0)
        self.legend_combo = QComboBox()
        for mode in LEGEND_MODES:
            self.legend_combo.addItem(tr(f"layout_dialog.panel.legend_{mode}"), mode)
        self.legend_combo.currentIndexChanged.connect(self._on_panel_edited)
        form.addWidget(self.legend_combo, row, 1, 1, 3)
        row += 1

        self.stack_check = QCheckBox(tr("layout_dialog.panel.apply_stack"))
        self.stack_check.setToolTip(tr("layout_dialog.panel.apply_stack_tooltip"))
        self.stack_check.toggled.connect(self._on_panel_edited)
        form.addWidget(self.stack_check, row, 0, 1, 4)
        row += 1

        # Typ-spezifische Optionen
        self.options_box = QGroupBox(tr("layout_dialog.options.title"))
        opt = QGridLayout(self.options_box)
        self.normalize_check = QCheckBox(tr("layout_dialog.options.normalize_area"))
        self.normalize_check.setToolTip(tr("layout_dialog.options.normalize_area_tooltip"))
        self.normalize_check.toggled.connect(self._on_panel_edited)
        opt.addWidget(self.normalize_check, 0, 0, 1, 2)

        self.window_label = QLabel(tr("options.significance_window"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(3, 51)
        self.window_spin.setSingleStep(2)
        self.window_spin.setToolTip(tr("options.significance_window_tooltip"))
        self.window_spin.valueChanged.connect(self._on_panel_edited)
        opt.addWidget(self.window_label, 1, 0)
        opt.addWidget(self.window_spin, 1, 1)

        self.thresholds_label = QLabel(tr("options.significance_thresholds"))
        self.thresholds_edit = QLineEdit()
        self.thresholds_edit.setToolTip(tr("options.significance_thresholds_tooltip"))
        self.thresholds_edit.editingFinished.connect(self._on_panel_edited)
        opt.addWidget(self.thresholds_label, 2, 0)
        opt.addWidget(self.thresholds_edit, 2, 1)

        self.smooth_label = QLabel(tr("options.dlnidlnq_smooth_window"))
        self.smooth_spin = QSpinBox()
        self.smooth_spin.setRange(3, 51)
        self.smooth_spin.setSingleStep(2)
        self.smooth_spin.setToolTip(tr("options.dlnidlnq_smooth_window_tooltip"))
        self.smooth_spin.valueChanged.connect(self._on_panel_edited)
        opt.addWidget(self.smooth_label, 3, 0)
        opt.addWidget(self.smooth_spin, 3, 1)

        self.no_options_label = QLabel(tr("layout_dialog.options.none"))
        opt.addWidget(self.no_options_label, 4, 0, 1, 2)
        form.addWidget(self.options_box, row, 0, 1, 4)
        row += 1
        form.setRowStretch(row, 1)
        return group

    # ── Laden ────────────────────────────────────────────────────────────────

    def _current(self):
        return self.layout_model.get(self._current_id) or self.layout_model.main

    def _load_grid(self):
        self._loading = True
        lm = self.layout_model
        self.rows_spin.setValue(lm.rows)
        self.cols_spin.setValue(lm.cols)
        self.row_ratios_edit.setText(", ".join(f"{r:g}" for r in lm.row_ratios))
        self.col_ratios_edit.setText(", ".join(f"{c:g}" for c in lm.col_ratios))
        self._loading = False

    def _load_panel(self):
        """Füllt die Panel-Eigenschaften aus dem aktuell gewählten Panel."""
        self._loading = True
        panel = self._current()
        lm = self.layout_model

        self.panel_combo.clear()
        for p in lm.panels:
            self.panel_combo.addItem(p.name + (f" — {tr('panels.main')}" if p.is_main else ""), p.id)
        self.panel_combo.setCurrentIndex(max(0, self.panel_combo.findData(panel.id)))

        self.name_edit.setText(panel.name)
        self.type_combo.setCurrentText(panel.panel_type)
        self.enabled_check.setChecked(panel.enabled or panel.is_main)
        self.enabled_check.setEnabled(not panel.is_main)
        self.remove_btn.setEnabled(not panel.is_main)

        for key in ('row', 'col', 'rowspan', 'colspan'):
            spin = self.pos_spins[key]
            limit = lm.rows if key in ('row', 'rowspan') else lm.cols
            spin.setRange(1, max(limit, 1))
            spin.setValue(getattr(panel, key) + (1 if key in ('row', 'col') else 0))

        self.share_combo.clear()
        self.share_combo.addItem(tr("layout_dialog.panel.share_none"), None)
        for target in lm.compatible_share_targets(panel):
            self.share_combo.addItem(target.name, target.id)
        idx = self.share_combo.findData(panel.share_x_with)
        self.share_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.legend_combo.setCurrentIndex(max(0, self.legend_combo.findData(panel.legend)))
        self.stack_check.setChecked(panel.apply_stack)

        opts = panel.options
        self.normalize_check.setChecked(bool(opts.get('normalize_area', False)))
        self.window_spin.setValue(int(opts.get('window', 9)))
        self.thresholds_edit.setText(", ".join(f"{t:g}" for t in opts.get('thresholds', [3.0, 2.0, 1.0])))
        self.smooth_spin.setValue(int(opts.get('smooth_window', 5)))
        self._update_option_visibility(panel.panel_type)
        self._loading = False

    def _update_option_visibility(self, panel_type):
        is_pr = panel_type == 'P(r)'
        is_sig = panel_type == 'Significance'
        is_dln = panel_type == 'dlnI/dlnq'
        self.normalize_check.setVisible(is_pr)
        for w in (self.window_label, self.window_spin, self.thresholds_label, self.thresholds_edit):
            w.setVisible(is_sig)
        self.smooth_label.setVisible(is_dln)
        self.smooth_spin.setVisible(is_dln)
        self.no_options_label.setVisible(not (is_pr or is_sig or is_dln))

    # ── Änderungen ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_floats(text):
        """Kommagetrennte Zahlen → Liste (None bei ungültiger Eingabe)."""
        values = []
        for token in text.replace(';', ',').split(','):
            token = token.strip()
            if not token:
                continue
            try:
                values.append(float(token))
            except ValueError:
                return None
        return values

    def _parse_ratios(self, text, count):
        values = self._parse_floats(text)
        return values if values is not None and len(values) == count else None

    def _on_grid_changed(self):
        if self._loading:
            return
        self.layout_model.set_grid(self.rows_spin.value(), self.cols_spin.value())
        self._load_grid()
        self._load_panel()
        self._refresh()

    def _on_ratios_changed(self):
        if self._loading:
            return
        lm = self.layout_model
        rows = self._parse_ratios(self.row_ratios_edit.text(), lm.rows)
        cols = self._parse_ratios(self.col_ratios_edit.text(), lm.cols)
        if rows is not None:
            lm.row_ratios = rows
        if cols is not None:
            lm.col_ratios = cols
        self._load_grid()  # ungültige Eingaben auf den letzten gültigen Stand zurücksetzen
        self._refresh()

    def _on_panel_selected(self, index):
        if self._loading or index < 0:
            return
        self._current_id = self.panel_combo.itemData(index)
        self._load_panel()
        self._refresh()

    def _on_selection_changed(self):
        if self._loading:
            return
        ranges = self.preview.selectedRanges()
        if ranges:
            r = ranges[0]
            self._sel_rect = (r.topRow(), r.leftColumn(), r.bottomRow(), r.rightColumn())
        else:
            self._sel_rect = None
        self._update_merge_buttons()

    def _selection_is_multi(self):
        rect = self._sel_rect
        return rect is not None and (rect[2] > rect[0] or rect[3] > rect[1])

    def _update_merge_buttons(self):
        self.merge_btn.setEnabled(self._selection_is_multi())
        panel = self._current()
        self.split_btn.setEnabled(panel.rowspan > 1 or panel.colspan > 1)

    def _merge_cells(self):
        """Verbindet den markierten Zellbereich zu einem Panel.

        Ziel ist das Hauptpanel bzw. das Panel in der linken oberen Zelle, sofern es
        komplett im Bereich liegt; gibt es keins, wird ein neues Panel angelegt.
        Weitere Panels, die komplett im Bereich liegen, werden deaktiviert (ihre
        Einstellungen bleiben erhalten); teilweise überlappende Panels meldet die
        Validierung.
        """
        if not self._selection_is_multi():
            return
        r0, c0, r1, c1 = self._sel_rect
        lm = self.layout_model
        rect_cells = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
        inside = [p for p in lm.panels if (p.enabled or p.is_main) and p.cells() <= rect_cells]

        target = next((p for p in inside if p.is_main), None)
        if target is None:
            target = next((p for p in inside if (r0, c0) in p.cells()), None)
        if target is None and inside:
            target = inside[0]
        if target is None:
            target = lm.add_panel('Log-Log', row=r0, col=c0, rowspan=r1 - r0 + 1,
                                  colspan=c1 - c0 + 1)
        target.row, target.col = r0, c0
        target.rowspan, target.colspan = r1 - r0 + 1, c1 - c0 + 1

        for p in inside:
            if p is target:
                continue
            p.enabled = False
            for other in lm.panels:
                if other.share_x_with == p.id:
                    other.share_x_with = None
        self._current_id = target.id
        self._load_grid()
        self._load_panel()
        self._refresh()

    def _split_cells(self):
        """Setzt das gewählte Panel auf eine einzelne Zelle zurück."""
        panel = self._current()
        panel.rowspan = panel.colspan = 1
        self._load_panel()
        self._refresh()

    def _on_cell_clicked(self, row, col):
        if self._selection_is_multi():
            return  # Bereichsauswahl zum Verbinden, Panel-Auswahl nicht ändern
        for p in self.layout_model.panels:
            if (p.enabled or p.is_main) and (row, col) in p.cells():
                self._current_id = p.id
                break
        else:
            for p in self.layout_model.panels:
                if (row, col) in p.cells():
                    self._current_id = p.id
                    break
        self._load_panel()
        self._refresh()

    def _on_panel_edited(self, *args):
        if self._loading:
            return
        panel = self._current()
        name = self.name_edit.text().strip()
        type_changed = self.type_combo.currentText() != panel.panel_type
        if name and name != panel.name:
            panel.name = name
        panel.set_type(self.type_combo.currentText())
        if not panel.is_main:
            panel.enabled = self.enabled_check.isChecked()
        panel.row = self.pos_spins['row'].value() - 1
        panel.col = self.pos_spins['col'].value() - 1
        panel.rowspan = self.pos_spins['rowspan'].value()
        panel.colspan = self.pos_spins['colspan'].value()
        panel.share_x_with = self.share_combo.currentData()
        panel.legend = self.legend_combo.currentData()
        panel.apply_stack = self.stack_check.isChecked()

        if panel.panel_type == 'P(r)':
            panel.options['normalize_area'] = self.normalize_check.isChecked()
        elif panel.panel_type == 'Significance':
            window = self.window_spin.value()
            panel.options['window'] = window if window % 2 == 1 else window + 1
            thresholds = self._parse_floats(self.thresholds_edit.text())
            if thresholds:
                panel.options['thresholds'] = thresholds
        elif panel.panel_type == 'dlnI/dlnq':
            window = self.smooth_spin.value()
            panel.options['smooth_window'] = window if window % 2 == 1 else window + 1

        if type_changed:
            # Kopplung ggf. ungültig (andere X-Größe) und Namensliste/Optionen neu laden
            if panel.share_x_with:
                target = self.layout_model.get(panel.share_x_with)
                if target is None or target.type_info.x_domain != panel.type_info.x_domain:
                    panel.share_x_with = None
            for other in self.layout_model.panels:
                if other.share_x_with == panel.id and other.type_info.x_domain != panel.type_info.x_domain:
                    other.share_x_with = None
            self._load_panel()
        else:
            # Anzeigenamen in der Auswahlliste aktualisieren
            idx = self.panel_combo.findData(panel.id)
            self._loading = True
            self.panel_combo.setItemText(idx, panel.name + (f" — {tr('panels.main')}" if panel.is_main else ""))
            self._loading = False
        self._refresh()

    def _add_panel(self, panel_type):
        panel = self.layout_model.add_panel(panel_type)
        main = self.layout_model.main
        if (panel.type_info.x_domain == main.type_info.x_domain
                and panel.col == main.col and panel.row == main.row + main.rowspan):
            panel.share_x_with = MAIN_ID
        self._current_id = panel.id
        self._load_grid()
        self._load_panel()
        self._refresh()

    def _remove_panel(self):
        panel = self._current()
        if panel.is_main:
            return
        answer = QMessageBox.question(self, tr("layout_dialog.title"),
                                      tr("layout_dialog.confirm_remove", name=panel.name))
        if answer != QMessageBox.Yes:
            return
        self.layout_model.remove_panel(panel.id)
        self.layout_model.compact()
        self._current_id = MAIN_ID
        self._load_grid()
        self._load_panel()
        self._refresh()

    # ── Vorschau / Validierung ───────────────────────────────────────────────

    def _refresh(self):
        lm = self.layout_model
        self._loading = True   # Selektionsänderungen durch das Neuaufbauen ignorieren
        self.preview.clearSpans()
        self.preview.clear()
        self.preview.setRowCount(lm.rows)
        self.preview.setColumnCount(lm.cols)
        self.preview.setHorizontalHeaderLabels([str(c + 1) for c in range(lm.cols)])
        self.preview.setVerticalHeaderLabels([str(r + 1) for r in range(lm.rows)])
        for r in range(lm.rows):
            for c in range(lm.cols):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                self.preview.setItem(r, c, item)

        for i, panel in enumerate(lm.panels):
            if not (panel.enabled or panel.is_main):
                continue
            if panel.row + panel.rowspan > lm.rows or panel.col + panel.colspan > lm.cols:
                continue
            text = f"{panel.name}\n({panel.panel_type})"
            if panel.share_x_with:
                target = lm.get(panel.share_x_with)
                text += f"\n⇅ {target.name if target else '?'}"
            item = self.preview.item(panel.row, panel.col)
            if item.text():
                item.setText(item.text() + "\n⚠ " + panel.name)
                item.setBackground(QBrush(QColor('#8b2e2e')))
                continue
            item.setText(text)
            color = QColor(_PREVIEW_COLORS[i % len(_PREVIEW_COLORS)])
            if panel.id == self._current_id:
                color = color.lighter(140)
            item.setBackground(QBrush(color))
            if panel.rowspan > 1 or panel.colspan > 1:
                self.preview.setSpan(panel.row, panel.col, panel.rowspan, panel.colspan)

        rect = self._sel_rect
        if rect is not None and rect[2] < lm.rows and rect[3] < lm.cols:
            self.preview.setRangeSelected(
                QTableWidgetSelectionRange(rect[0], rect[1], rect[2], rect[3]), True)
        else:
            self._sel_rect = None
        self._loading = False
        self._update_merge_buttons()

        disabled = [p.name for p in lm.panels if not (p.enabled or p.is_main)]
        errors = lm.validate()
        lines = list(errors)
        if disabled:
            lines.append(tr("layout_dialog.disabled_panels", names=", ".join(disabled)))
        self.validation_label.setStyleSheet("color: #ff6b6b;" if errors else "color: #aaaaaa;")
        self.validation_label.setText("\n".join(lines))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not errors)

    def get_layout(self):
        """Gibt das bearbeitete Layout zurück."""
        return self.layout_model
