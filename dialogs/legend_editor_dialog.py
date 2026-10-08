"""
Legend Editor Dialog

Bearbeitet die Legendeneinträge (v7.0, überarbeitet v8.1.1):
- Baum aus Gruppen und Datensätzen in Legenden-Reihenfolge; Umsortieren nur
  innerhalb derselben Ebene (Gruppen untereinander, Datensätze innerhalb ihrer Gruppe)
- Checkbox = Eintrag in der Legende anzeigen (unabhängig von der Kurven-Sichtbarkeit)
- Anzeigename mit LaTeX/MathText und chemischen Formeln (\\ce{...}), Fett/Kursiv
- Vorschau wird mit Matplotlib gerendert (identisch zum Plot)

Alle Änderungen werden erst mit OK übernommen (apply_entry_changes / get_order);
Abbrechen lässt Datensätze und Gruppen unverändert.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QDialogButtonBox, QGroupBox, QCheckBox, QLineEdit,
    QLabel, QWidget, QMessageBox, QToolBar, QComboBox,
    QSpinBox, QDoubleSpinBox, QGridLayout, QTabWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QColor, QPixmap, QIcon, QBrush
from utils.mathtext_formatter import get_syntax_help_text, format_legend_text, is_in_math
from i18n import tr
from dialogs.dialog_utils import fit_to_screen, scroll_wrap, render_text_pixmap

# Markierung des Pseudo-Knotens für nicht zugeordnete Datensätze
_UNASSIGNED = 'unassigned'


class LegendEditorDialog(QDialog):
    """Dialog zum Bearbeiten von Legendeneinträgen"""

    LEGEND_POSITIONS = [
        'best', 'upper right', 'upper left', 'lower right', 'lower left',
        'center', 'center left', 'center right', 'lower center', 'upper center',
        'right', 'left'
    ]

    def __init__(self, parent, groups, unassigned_datasets, legend_settings=None, font_settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr("legend_editor.title"))
        fit_to_screen(self, 860, 680)

        self.groups = list(groups)
        self.unassigned_datasets = list(unassigned_datasets)
        self.legend_settings = legend_settings or {}
        self.font_settings = font_settings or {}

        # Arbeitskopie der Eintrags-Eigenschaften: id(obj) → dict
        self._entries = {}
        for group in self.groups:
            self._entries[id(group)] = {
                'obj': group,
                'label': getattr(group, 'display_label', None) or group.name,
                'visible': getattr(group, 'show_in_legend', True),
                'bold': getattr(group, 'legend_bold', False),
                'italic': getattr(group, 'legend_italic', False),
            }
            for dataset in group.datasets:
                self._add_dataset_entry(dataset)
        for dataset in self.unassigned_datasets:
            self._add_dataset_entry(dataset)

        self._loading = False
        self.setup_ui()
        self.populate_tree()

    def _add_dataset_entry(self, dataset):
        self._entries[id(dataset)] = {
            'obj': dataset,
            'label': dataset.display_label,
            'visible': getattr(dataset, 'legend_visible', True),
            'bold': getattr(dataset, 'legend_bold', False),
            'italic': getattr(dataset, 'legend_italic', False),
        }

    # ── UI-Aufbau ────────────────────────────────────────────────────────────

    def setup_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(tr("legend_editor.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.tab_widget = QTabWidget()

        entries_tab = QWidget()
        self.setup_entries_tab(entries_tab)
        self.tab_widget.addTab(entries_tab, tr("legend_editor.tabs.entries"))

        settings_tab = QWidget()
        self.setup_settings_tab(settings_tab)
        self.tab_widget.addTab(scroll_wrap(settings_tab), tr("legend_editor.tabs.settings"))

        layout.addWidget(self.tab_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def setup_entries_tab(self, parent):
        layout = QHBoxLayout(parent)

        # Links: Baum der Einträge
        list_group = QGroupBox(tr("legend_editor.entries.title"))
        list_layout = QVBoxLayout(list_group)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(22, 12))
        self.tree.currentItemChanged.connect(self.on_selection_changed)
        self.tree.itemChanged.connect(self.on_item_changed)
        list_layout.addWidget(self.tree)

        hint = QLabel(tr("legend_editor.entries.checkbox_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-style: italic;")
        list_layout.addWidget(hint)

        order_buttons = QHBoxLayout()
        self.move_up_btn = QPushButton(tr("legend_editor.entries.move_up"))
        self.move_down_btn = QPushButton(tr("legend_editor.entries.move_down"))
        self.move_up_btn.clicked.connect(lambda: self.move_current(-1))
        self.move_down_btn.clicked.connect(lambda: self.move_current(1))
        order_buttons.addWidget(self.move_up_btn)
        order_buttons.addWidget(self.move_down_btn)
        list_layout.addLayout(order_buttons)
        layout.addWidget(list_group, 1)

        # Rechts: Eintrag bearbeiten
        editor_group = QGroupBox(tr("legend_editor.entries.edit_entry"))
        editor_layout = QVBoxLayout(editor_group)

        self.format_toolbar = QToolBar()
        self._build_toolbar()
        editor_layout.addWidget(self.format_toolbar)

        editor_layout.addWidget(QLabel(tr("legend_editor.entries.display_name")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(tr("legend_editor.entries.placeholder"))
        self.name_edit.textChanged.connect(self.on_name_changed)
        editor_layout.addWidget(self.name_edit)

        format_row = QHBoxLayout()
        self.bold_check = QCheckBox(tr("title_editor.font.bold"))
        self.bold_check.toggled.connect(self.on_format_changed)
        format_row.addWidget(self.bold_check)
        self.italic_check = QCheckBox(tr("title_editor.font.italic"))
        self.italic_check.toggled.connect(self.on_format_changed)
        format_row.addWidget(self.italic_check)
        format_row.addStretch()
        syntax_help_btn = QPushButton(tr("legend_editor.entries.latex_help"))
        syntax_help_btn.clicked.connect(self.show_syntax_help)
        format_row.addWidget(syntax_help_btn)
        editor_layout.addLayout(format_row)

        preview_label = QLabel(tr("legend_editor.entries.preview"))
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        editor_layout.addWidget(preview_label)

        self.preview_image = QLabel()
        self.preview_image.setMinimumHeight(48)
        self.preview_image.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.preview_image.setStyleSheet(
            "background-color: white; border: 1px solid #555; border-radius: 4px; padding: 6px;")
        editor_layout.addWidget(self.preview_image)

        self.preview_error = QLabel()
        self.preview_error.setWordWrap(True)
        self.preview_error.setStyleSheet("color: #ff6b6b;")
        editor_layout.addWidget(self.preview_error)

        editor_layout.addStretch()
        layout.addWidget(editor_group, 1)

        self.enable_editor(False)

    def _build_toolbar(self):
        """Toolbar: fügt je nach Cursor-Position (in/außerhalb $…$) passende Syntax ein."""
        def add(text, tooltip, callback):
            action = QAction(text, self)
            action.setToolTip(tooltip)
            action.triggered.connect(callback)
            self.format_toolbar.addAction(action)

        add("B", tr("legend_editor.entries.bold"), lambda: self.wrap_selection('**', '**', r'\mathbf{', '}'))
        add("I", tr("legend_editor.entries.italic"), lambda: self.wrap_selection('*', '*', r'\mathit{', '}'))
        self.format_toolbar.addSeparator()
        add("x₂", tr("legend_editor.entries.subscript"), lambda: self.wrap_selection('$_{', '}$', '_{', '}'))
        add("x²", tr("legend_editor.entries.superscript"), lambda: self.wrap_selection('$^{', '}$', '^{', '}'))
        add("\\ce", tr("legend_editor.entries.chem"), lambda: self.wrap_selection(r'\ce{', '}', r'\ce{', '}'))
        self.format_toolbar.addSeparator()
        for symbol, latex in [("α", r"\alpha"), ("β", r"\beta"), ("γ", r"\gamma"),
                              ("δ", r"\delta"), ("θ", r"\theta"), ("λ", r"\lambda"),
                              ("µ", r"\mu"), ("π", r"\pi"), ("σ", r"\sigma")]:
            add(symbol, latex, lambda checked=False, l=latex: self.insert_symbol(l))
        self.format_toolbar.addSeparator()
        for symbol, latex in [("·", r"\cdot"), ("×", r"\times"), ("±", r"\pm"),
                              ("→", r"\rightarrow"), ("Å", r"\AA")]:
            add(symbol, latex, lambda checked=False, l=latex: self.insert_symbol(l))

    def setup_settings_tab(self, parent):
        layout = QVBoxLayout(parent)

        settings_group = QGroupBox(tr("legend.settings_title"))
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel(tr("legend.position")), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(self.LEGEND_POSITIONS)
        index = self.position_combo.findText(self.legend_settings.get('position', 'best'))
        self.position_combo.setCurrentIndex(max(index, 0))
        settings_layout.addWidget(self.position_combo, 0, 1)

        settings_layout.addWidget(QLabel(tr("legend.columns")), 1, 0)
        self.ncol_spin = QSpinBox()
        self.ncol_spin.setRange(1, 10)
        self.ncol_spin.setValue(self.legend_settings.get('ncol', 1))
        settings_layout.addWidget(self.ncol_spin, 1, 1)

        settings_layout.addWidget(QLabel(tr("legend.transparency")), 2, 0)
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.0, 1.0)
        self.alpha_spin.setSingleStep(0.1)
        self.alpha_spin.setDecimals(2)
        self.alpha_spin.setValue(self.legend_settings.get('alpha', 0.9))
        settings_layout.addWidget(self.alpha_spin, 2, 1)

        self.frame_checkbox = QCheckBox(tr("legend.show_frame"))
        self.frame_checkbox.setChecked(self.legend_settings.get('frameon', True))
        settings_layout.addWidget(self.frame_checkbox, 3, 0, 1, 2)

        self.shadow_checkbox = QCheckBox(tr("legend.shadow"))
        self.shadow_checkbox.setChecked(self.legend_settings.get('shadow', False))
        settings_layout.addWidget(self.shadow_checkbox, 4, 0, 1, 2)

        self.fancybox_checkbox = QCheckBox(tr("legend.rounded_corners"))
        self.fancybox_checkbox.setChecked(self.legend_settings.get('fancybox', True))
        settings_layout.addWidget(self.fancybox_checkbox, 5, 0, 1, 2)

        self.reverse_order_checkbox = QCheckBox(tr("legend.reverse_order"))
        self.reverse_order_checkbox.setChecked(self.legend_settings.get('reverse_order', False))
        self.reverse_order_checkbox.setToolTip(tr("legend.reverse_order_tooltip"))
        settings_layout.addWidget(self.reverse_order_checkbox, 6, 0, 1, 2)
        layout.addWidget(settings_group)

        # Schrift (gilt für alle Einträge; Fett/Kursiv zusätzlich zur Formatierung je Eintrag)
        font_group = QGroupBox(tr("legend_editor.font.title"))
        font_layout = QGridLayout(font_group)
        font_layout.addWidget(QLabel(tr("legend_editor.font.size")), 0, 0)
        self.legend_size_spin = QSpinBox()
        self.legend_size_spin.setRange(6, 24)
        self.legend_size_spin.setValue(self.font_settings.get('legend_size', 10))
        self.legend_size_spin.setSuffix(" pt")
        self.legend_size_spin.valueChanged.connect(self.update_preview)
        font_layout.addWidget(self.legend_size_spin, 0, 1)

        self.legend_bold = QCheckBox(tr("legend_editor.font.all_bold"))
        self.legend_bold.setChecked(self.font_settings.get('legend_bold', False))
        self.legend_bold.toggled.connect(self.update_preview)
        font_layout.addWidget(self.legend_bold, 1, 0)

        self.legend_italic = QCheckBox(tr("legend_editor.font.all_italic"))
        self.legend_italic.setChecked(self.font_settings.get('legend_italic', False))
        self.legend_italic.toggled.connect(self.update_preview)
        font_layout.addWidget(self.legend_italic, 1, 1)
        layout.addWidget(font_group)
        layout.addStretch()

    # ── Baum ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _swatch(dataset):
        pixmap = QPixmap(22, 12)
        pixmap.fill(QColor(dataset.color) if dataset.color else QColor('#888888'))
        return QIcon(pixmap)

    def _make_item(self, parent, obj, kind, curve_hidden):
        entry = self._entries[id(obj)]
        item = QTreeWidgetItem(parent)
        item.setData(0, Qt.UserRole, (kind, obj))
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked if entry['visible'] else Qt.Unchecked)
        if kind == 'dataset':
            item.setIcon(0, self._swatch(obj))
        if curve_hidden:
            item.setForeground(0, QBrush(QColor('#888888')))
            item.setToolTip(0, tr("legend_editor.entries.curve_hidden_tooltip"))
        item.setData(0, Qt.UserRole + 1, curve_hidden)
        self._update_item_text(item)
        return item

    def _update_item_text(self, item):
        kind, obj = item.data(0, Qt.UserRole)
        if kind == _UNASSIGNED:
            return
        text = self._entries[id(obj)]['label'] or (obj.name if kind == 'group' else '')
        if item.data(0, Qt.UserRole + 1):
            text += f"  ({tr('legend_editor.entries.curve_hidden')})"
        item.setText(0, text)

    def populate_tree(self):
        """Baut den Baum in Legenden-Reihenfolge (Gruppen, dann nicht zugeordnete) auf."""
        self._loading = True
        self.tree.clear()
        for group in self.groups:
            group_hidden = not group.visible
            group_item = self._make_item(self.tree, group, 'group', group_hidden)
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            for dataset in group.datasets:
                self._make_item(group_item, dataset, 'dataset',
                                group_hidden or not dataset.show_in_legend)
            group_item.setExpanded(True)
        if self.unassigned_datasets:
            node = QTreeWidgetItem(self.tree, [tr("tree.unassigned")])
            node.setData(0, Qt.UserRole, (_UNASSIGNED, None))
            node.setFlags(Qt.ItemIsEnabled)
            for dataset in self.unassigned_datasets:
                self._make_item(node, dataset, 'dataset', not dataset.show_in_legend)
            node.setExpanded(True)
        self._loading = False

    def _current_entry(self):
        item = self.tree.currentItem()
        if item is None:
            return None, None
        kind, obj = item.data(0, Qt.UserRole)
        if kind == _UNASSIGNED:
            return item, None
        return item, self._entries[id(obj)]

    def on_selection_changed(self, current, previous):
        item, entry = self._current_entry()
        self.enable_editor(entry is not None)
        self._update_move_buttons()
        self._loading = True
        if entry is None:
            self.name_edit.clear()
            self.bold_check.setChecked(False)
            self.italic_check.setChecked(False)
        else:
            self.name_edit.setText(entry['label'])
            self.bold_check.setChecked(entry['bold'])
            self.italic_check.setChecked(entry['italic'])
        self._loading = False
        self.update_preview()

    def on_item_changed(self, item, column):
        if self._loading:
            return
        kind, obj = item.data(0, Qt.UserRole)
        if kind != _UNASSIGNED:
            self._entries[id(obj)]['visible'] = item.checkState(0) == Qt.Checked

    def enable_editor(self, enabled):
        for widget in (self.name_edit, self.bold_check, self.italic_check, self.format_toolbar):
            widget.setEnabled(enabled)

    def on_name_changed(self, text):
        if self._loading:
            return
        item, entry = self._current_entry()
        if entry is None:
            return
        entry['label'] = text
        self._loading = True
        self._update_item_text(item)
        self._loading = False
        self.update_preview()

    def on_format_changed(self):
        if self._loading:
            return
        item, entry = self._current_entry()
        if entry is None:
            return
        entry['bold'] = self.bold_check.isChecked()
        entry['italic'] = self.italic_check.isChecked()
        self.update_preview()

    # ── Reihenfolge ──────────────────────────────────────────────────────────

    def _sibling_range(self, item):
        """(Container, Index, Anzahl verschiebbarer Geschwister) eines Eintrags."""
        parent = item.parent()
        if parent is not None:
            return parent, parent.indexOfChild(item), parent.childCount()
        # Oberste Ebene: nur Gruppen sind verschiebbar (der Knoten 'Ohne Gruppe' bleibt am Ende)
        return None, self.tree.indexOfTopLevelItem(item), len(self.groups)

    def _update_move_buttons(self):
        item = self.tree.currentItem()
        movable = item is not None and item.data(0, Qt.UserRole)[0] != _UNASSIGNED
        if movable:
            _, index, count = self._sibling_range(item)
            self.move_up_btn.setEnabled(index > 0)
            self.move_down_btn.setEnabled(index < count - 1)
        else:
            self.move_up_btn.setEnabled(False)
            self.move_down_btn.setEnabled(False)

    def move_current(self, step):
        item = self.tree.currentItem()
        if item is None or item.data(0, Qt.UserRole)[0] == _UNASSIGNED:
            return
        parent, index, count = self._sibling_range(item)
        target = index + step
        if not 0 <= target < count:
            return
        self._loading = True
        if parent is None:
            expanded = item.isExpanded()
            self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(target, item)
            item.setExpanded(expanded)
            self.groups.insert(target, self.groups.pop(index))
        else:
            parent.takeChild(index)
            parent.insertChild(target, item)
        self._loading = False
        self.tree.setCurrentItem(item)
        self._update_move_buttons()

    # ── Eingabehilfen ────────────────────────────────────────────────────────

    def wrap_selection(self, text_start, text_end, math_start, math_end):
        """Umschließt die Auswahl (oder fügt am Cursor ein) – mit Text-Syntax außerhalb
        und Formel-Syntax innerhalb von $…$."""
        edit = self.name_edit
        text = edit.text()
        if edit.hasSelectedText():
            start = edit.selectionStart()
            end = start + len(edit.selectedText())
        else:
            start = end = edit.cursorPosition()
        in_math = is_in_math(text, start)
        before, after = (math_start, math_end) if in_math else (text_start, text_end)
        new_text = text[:start] + before + text[start:end] + after + text[end:]
        edit.setText(new_text)
        edit.setCursorPosition(start + len(before) + (end - start) + (len(after) if end > start else 0))
        edit.setFocus()

    def insert_symbol(self, latex):
        """Fügt ein Symbol ein: als $\\alpha$ im Text, als \\alpha innerhalb einer Formel."""
        edit = self.name_edit
        text = edit.text()
        pos = edit.cursorPosition()
        if is_in_math(text, pos):
            # Leerzeichen, falls direkt ein Buchstabe folgt (\alpha b statt \alphab)
            snippet = latex + (' ' if pos < len(text) and text[pos].isalpha() else '')
        else:
            snippet = f'${latex}$'
        edit.setText(text[:pos] + snippet + text[pos:])
        edit.setCursorPosition(pos + len(snippet))
        edit.setFocus()

    # ── Vorschau ─────────────────────────────────────────────────────────────

    def update_preview(self):
        item, entry = self._current_entry()
        if entry is None or not entry['label']:
            self.preview_image.clear()
            self.preview_error.clear()
            return
        label = format_legend_text(entry['label'],
                                   entry['bold'] or self.legend_bold.isChecked(),
                                   entry['italic'] or self.legend_italic.isChecked())
        pixmap, error = render_text_pixmap(
            label, fontsize=self.legend_size_spin.value(),
            fontfamily=self.font_settings.get('font_family', 'sans-serif'))
        if error:
            self.preview_image.clear()
            self.preview_error.setText(tr("legend_editor.entries.preview_error", error=error))
        else:
            self.preview_image.setPixmap(pixmap)
            self.preview_error.clear()

    def show_syntax_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("legend_editor.entries.latex_help"))
        msg.setIcon(QMessageBox.Information)
        msg.setText(get_syntax_help_text())
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setMinimumWidth(500)
        msg.exec()

    # ── Ergebnis ─────────────────────────────────────────────────────────────

    def apply_entry_changes(self):
        """Schreibt Name, Legenden-Sichtbarkeit und Formatierung in die Objekte."""
        for entry in self._entries.values():
            obj = entry['obj']
            obj.display_label = entry['label']
            if hasattr(obj, 'datasets'):  # Gruppe: Checkbox = Gruppenüberschrift
                obj.show_in_legend = entry['visible']
            else:
                obj.legend_visible = entry['visible']
            obj.legend_bold = entry['bold']
            obj.legend_italic = entry['italic']

    def get_order(self):
        """Reihenfolge als (Gruppen, {id(Gruppe): Datensätze}, nicht zugeordnete)."""
        group_order, dataset_orders, unassigned = [], {}, []
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            kind, obj = top.data(0, Qt.UserRole)
            children = [top.child(j).data(0, Qt.UserRole)[1] for j in range(top.childCount())]
            if kind == 'group':
                group_order.append(obj)
                dataset_orders[id(obj)] = children
            else:
                unassigned = children
        return group_order, dataset_orders, unassigned

    def get_legend_settings(self):
        return {
            'position': self.position_combo.currentText(),
            'ncol': self.ncol_spin.value(),
            'alpha': self.alpha_spin.value(),
            'frameon': self.frame_checkbox.isChecked(),
            'shadow': self.shadow_checkbox.isChecked(),
            'fancybox': self.fancybox_checkbox.isChecked(),
            'reverse_order': self.reverse_order_checkbox.isChecked()
        }

    def get_font_settings(self):
        return {
            'legend_size': self.legend_size_spin.value(),
            'legend_bold': self.legend_bold.isChecked(),
            'legend_italic': self.legend_italic.isChecked()
        }
