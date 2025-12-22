"""
Legend Editor Dialog

This dialog allows users to edit legend entries with advanced options:
- Show/hide individual entries
- Rename entries
- Change order
- Format entries (bold/italic)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox, QGroupBox, QCheckBox, QLineEdit,
    QLabel, QWidget, QMessageBox, QTextEdit, QToolBar, QComboBox,
    QSpinBox, QDoubleSpinBox, QGridLayout, QTabWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from utils.mathtext_formatter import get_syntax_help_text, preprocess_mathtext


class LegendEditorDialog(QDialog):
    """Dialog zum Bearbeiten von Legendeneinträgen"""

    def __init__(self, parent, groups, unassigned_datasets, legend_settings=None, font_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Legenden-Editor")
        self.resize(800, 700)

        self.groups = groups
        self.unassigned_datasets = unassigned_datasets

        # Legend und Font Settings initialisieren
        if legend_settings is None:
            legend_settings = {}
        if font_settings is None:
            font_settings = {}
        self.legend_settings = legend_settings
        self.font_settings = font_settings

        # Liste aller Items (Gruppen und Datasets) mit ihrer ursprünglichen Referenz
        self.legend_items = []

        # Legendeneinträge sammeln
        for group in self.groups:
            if group.visible and group.datasets:
                self.legend_items.append(('group', group))
                for dataset in group.datasets:
                    if dataset.show_in_legend:
                        self.legend_items.append(('dataset', dataset, group))

        for dataset in self.unassigned_datasets:
            if dataset.show_in_legend:
                self.legend_items.append(('dataset', dataset, None))

        self.setup_ui()
        self.populate_list()

    def setup_ui(self):
        """UI aufbauen"""
        layout = QVBoxLayout(self)

        # Info-Label
        info_label = QLabel(
            "Bearbeiten Sie die Legendeneinträge, Einstellungen und Schriftarten. "
            "Verwenden Sie die Toolbar für schnelle LaTeX-Formatierung."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Tab-Widget für verschiedene Bereiche
        self.tab_widget = QTabWidget()

        # Tab 1: Einträge bearbeiten
        entries_tab = QWidget()
        self.setup_entries_tab(entries_tab)
        self.tab_widget.addTab(entries_tab, "Einträge bearbeiten")

        # Tab 2: Legenden-Einstellungen
        settings_tab = QWidget()
        self.setup_settings_tab(settings_tab)
        self.tab_widget.addTab(settings_tab, "Legenden-Einstellungen")

        # Tab 3: Schriftart
        font_tab = QWidget()
        self.setup_font_tab(font_tab)
        self.tab_widget.addTab(font_tab, "Schriftart")

        layout.addWidget(self.tab_widget)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def setup_entries_tab(self, parent):
        """Tab für Einträge bearbeiten aufbauen"""
        layout = QVBoxLayout(parent)

        # Haupt-Bereich mit horizontaler Teilung
        main_layout = QHBoxLayout()

        # Linke Seite: Liste der Einträge
        list_group = QGroupBox("Legendeneinträge (in Anzeigereihenfolge)")
        list_layout = QVBoxLayout()

        self.entry_list = QListWidget()
        self.entry_list.currentItemChanged.connect(self.on_selection_changed)
        list_layout.addWidget(self.entry_list)

        # Buttons für Reihenfolge
        order_buttons = QHBoxLayout()
        self.move_up_btn = QPushButton("↑ Nach oben")
        self.move_down_btn = QPushButton("↓ Nach unten")
        self.move_up_btn.clicked.connect(self.move_up)
        self.move_down_btn.clicked.connect(self.move_down)
        order_buttons.addWidget(self.move_up_btn)
        order_buttons.addWidget(self.move_down_btn)
        list_layout.addLayout(order_buttons)

        list_group.setLayout(list_layout)
        main_layout.addWidget(list_group, 2)

        # Rechte Seite: Editor-Bereich mit Tiny Editor
        editor_group = QGroupBox("Eintrag bearbeiten")
        editor_layout = QVBoxLayout()

        # Tiny Editor Toolbar
        self.format_toolbar = QToolBar()
        self.format_toolbar.setIconSize(QSize(20, 20))

        # Fett Button
        bold_action = QAction("B", self)
        bold_action.setToolTip("Fett (\\mathbf{...})")
        bold_action.triggered.connect(lambda: self.insert_latex_command("\\mathbf{", "}"))
        bold_action.setFont(self.format_toolbar.font())
        self.format_toolbar.addAction(bold_action)

        # Kursiv Button
        italic_action = QAction("I", self)
        italic_action.setToolTip("Kursiv (\\mathit{...})")
        italic_action.triggered.connect(lambda: self.insert_latex_command("\\mathit{", "}"))
        self.format_toolbar.addAction(italic_action)

        self.format_toolbar.addSeparator()

        # Subscript Button
        sub_action = QAction("x₂", self)
        sub_action.setToolTip("Subscript (_{...})")
        sub_action.triggered.connect(lambda: self.insert_latex_command("_{", "}"))
        self.format_toolbar.addAction(sub_action)

        # Superscript Button
        sup_action = QAction("x²", self)
        sup_action.setToolTip("Superscript (^{...})")
        sup_action.triggered.connect(lambda: self.insert_latex_command("^{", "}"))
        self.format_toolbar.addAction(sup_action)

        self.format_toolbar.addSeparator()

        # Griechische Buchstaben
        greek_letters = [
            ("α", "\\alpha"), ("β", "\\beta"), ("γ", "\\gamma"),
            ("δ", "\\delta"), ("θ", "\\theta"), ("λ", "\\lambda"),
            ("µ", "\\mu"), ("π", "\\pi"), ("σ", "\\sigma")
        ]

        for symbol, latex in greek_letters:
            action = QAction(symbol, self)
            action.setToolTip(f"{latex}")
            action.triggered.connect(lambda checked, l=latex: self.insert_text(l))
            self.format_toolbar.addAction(action)

        self.format_toolbar.addSeparator()

        # Weitere Symbole
        cdot_action = QAction("·", self)
        cdot_action.setToolTip("Multiplikation (\\cdot)")
        cdot_action.triggered.connect(lambda: self.insert_text("\\cdot"))
        self.format_toolbar.addAction(cdot_action)

        times_action = QAction("×", self)
        times_action.setToolTip("Kreuz (\\times)")
        times_action.triggered.connect(lambda: self.insert_text("\\times"))
        self.format_toolbar.addAction(times_action)

        angstrom_action = QAction("Å", self)
        angstrom_action.setToolTip("Angström (\\AA)")
        angstrom_action.triggered.connect(lambda: self.insert_text("\\AA"))
        self.format_toolbar.addAction(angstrom_action)

        editor_layout.addWidget(self.format_toolbar)

        # Name Eingabefeld
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Anzeigename:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(self.name_edit)
        editor_layout.addLayout(name_layout)

        # Syntax-Hilfe Button
        syntax_help_btn = QPushButton("📖 LaTeX/MathText Syntax-Hilfe")
        syntax_help_btn.clicked.connect(self.show_syntax_help)
        editor_layout.addWidget(syntax_help_btn)

        # Preview-Label
        preview_label = QLabel("Vorschau:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        editor_layout.addWidget(preview_label)

        self.preview_text = QLabel("")
        self.preview_text.setWordWrap(True)
        self.preview_text.setStyleSheet(
            "background-color: #2b2b2b; "
            "padding: 8px; "
            "border: 1px solid #555; "
            "border-radius: 4px; "
            "min-height: 30px;"
        )
        editor_layout.addWidget(self.preview_text)

        # Sichtbarkeit
        self.visible_check = QCheckBox("In Legende anzeigen")
        self.visible_check.stateChanged.connect(self.on_visibility_changed)
        editor_layout.addWidget(self.visible_check)

        # Formatierung
        format_label = QLabel("Formatierung:")
        editor_layout.addWidget(format_label)

        self.bold_check = QCheckBox("Fett")
        self.bold_check.stateChanged.connect(self.on_format_changed)
        editor_layout.addWidget(self.bold_check)

        self.italic_check = QCheckBox("Kursiv")
        self.italic_check.stateChanged.connect(self.on_format_changed)
        editor_layout.addWidget(self.italic_check)

        editor_layout.addStretch()
        editor_group.setLayout(editor_layout)
        main_layout.addWidget(editor_group, 1)

        layout.addLayout(main_layout)

        # Initial deaktiviert
        self.enable_editor(False)

    def setup_settings_tab(self, parent):
        """Tab für Legenden-Einstellungen aufbauen"""
        layout = QVBoxLayout(parent)

        settings_group = QGroupBox("Legenden-Einstellungen")
        settings_layout = QGridLayout()

        # Position
        settings_layout.addWidget(QLabel("Position:"), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            'best', 'upper right', 'upper left', 'lower right', 'lower left',
            'center', 'center left', 'center right', 'lower center', 'upper center',
            'right', 'left'
        ])
        current_pos = self.legend_settings.get('position', 'best')
        index = self.position_combo.findText(current_pos)
        if index >= 0:
            self.position_combo.setCurrentIndex(index)
        settings_layout.addWidget(self.position_combo, 0, 1)

        # Anzahl Spalten
        settings_layout.addWidget(QLabel("Spalten:"), 1, 0)
        self.ncol_spin = QSpinBox()
        self.ncol_spin.setRange(1, 10)
        self.ncol_spin.setValue(self.legend_settings.get('ncol', 1))
        settings_layout.addWidget(self.ncol_spin, 1, 1)

        # Transparenz (Alpha)
        settings_layout.addWidget(QLabel("Transparenz:"), 2, 0)
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.0, 1.0)
        self.alpha_spin.setSingleStep(0.1)
        self.alpha_spin.setValue(self.legend_settings.get('alpha', 0.9))
        self.alpha_spin.setDecimals(2)
        settings_layout.addWidget(self.alpha_spin, 2, 1)

        # Rahmen
        self.frame_checkbox = QCheckBox("Rahmen anzeigen")
        self.frame_checkbox.setChecked(self.legend_settings.get('frameon', True))
        settings_layout.addWidget(self.frame_checkbox, 3, 0, 1, 2)

        # Schatten
        self.shadow_checkbox = QCheckBox("Schatten")
        self.shadow_checkbox.setChecked(self.legend_settings.get('shadow', False))
        settings_layout.addWidget(self.shadow_checkbox, 4, 0, 1, 2)

        # Fancy Box
        self.fancybox_checkbox = QCheckBox("Abgerundete Ecken")
        self.fancybox_checkbox.setChecked(self.legend_settings.get('fancybox', True))
        settings_layout.addWidget(self.fancybox_checkbox, 5, 0, 1, 2)

        # Reihenfolge invertieren
        self.reverse_order_checkbox = QCheckBox("Reihenfolge invertieren (gestackte Kurven)")
        self.reverse_order_checkbox.setChecked(self.legend_settings.get('reverse_order', False))
        self.reverse_order_checkbox.setToolTip(
            "Kehrt die Reihenfolge der Legenden-Einträge um.\n"
            "Nützlich bei gestackten Kurven: oberste Kurve → oberster Legenden-Eintrag"
        )
        settings_layout.addWidget(self.reverse_order_checkbox, 6, 0, 1, 2)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

    def setup_font_tab(self, parent):
        """Tab für Schriftart-Einstellungen aufbauen"""
        layout = QVBoxLayout(parent)

        font_group = QGroupBox("Legenden-Schriftart")
        font_layout = QGridLayout()

        # Schriftgröße
        font_layout.addWidget(QLabel("Schriftgröße:"), 0, 0)
        self.legend_size_spin = QSpinBox()
        self.legend_size_spin.setRange(6, 24)
        self.legend_size_spin.setValue(self.font_settings.get('legend_size', 10))
        self.legend_size_spin.setSuffix(" pt")
        font_layout.addWidget(self.legend_size_spin, 0, 1)

        self.legend_bold = QCheckBox("Fett")
        self.legend_bold.setChecked(self.font_settings.get('legend_bold', False))
        font_layout.addWidget(self.legend_bold, 1, 0)

        self.legend_italic = QCheckBox("Kursiv")
        self.legend_italic.setChecked(self.font_settings.get('legend_italic', False))
        font_layout.addWidget(self.legend_italic, 1, 1)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        layout.addStretch()

    def insert_latex_command(self, start, end):
        """Fügt LaTeX-Befehl um ausgewählten Text ein"""
        cursor_pos = self.name_edit.cursorPosition()
        text = self.name_edit.text()
        selected_text = self.name_edit.selectedText()

        if selected_text:
            # Wenn Text ausgewählt ist, umschließe ihn
            new_text = text[:self.name_edit.selectionStart()] + start + selected_text + end + text[self.name_edit.selectionEnd():]
            self.name_edit.setText(new_text)
            self.name_edit.setCursorPosition(self.name_edit.selectionStart() + len(start) + len(selected_text) + len(end))
        else:
            # Sonst füge an Cursor-Position ein
            new_text = text[:cursor_pos] + start + end + text[cursor_pos:]
            self.name_edit.setText(new_text)
            self.name_edit.setCursorPosition(cursor_pos + len(start))

    def insert_text(self, text_to_insert):
        """Fügt Text an Cursor-Position ein"""
        cursor_pos = self.name_edit.cursorPosition()
        text = self.name_edit.text()
        new_text = text[:cursor_pos] + text_to_insert + text[cursor_pos:]
        self.name_edit.setText(new_text)
        self.name_edit.setCursorPosition(cursor_pos + len(text_to_insert))

    def populate_list(self):
        """Liste mit Einträgen füllen"""
        self.entry_list.clear()

        for item_data in self.legend_items:
            item_type = item_data[0]
            obj = item_data[1]

            # Item erstellen
            list_item = QListWidgetItem()

            if item_type == 'group':
                display_name = obj.display_label if hasattr(obj, 'display_label') else obj.name
                prefix = "📁 "  # Gruppen-Symbol
                visible = getattr(obj, 'show_in_legend', True)
            else:  # dataset
                display_name = obj.display_label
                prefix = "   📊 "  # Dataset-Symbol (eingerückt)
                visible = obj.show_in_legend

            # Text mit Formatierung
            text = f"{prefix}{display_name}"
            if not visible:
                text += " (ausgeblendet)"

            list_item.setText(text)
            list_item.setData(Qt.UserRole, item_data)

            self.entry_list.addItem(list_item)

    def on_selection_changed(self, current, previous):
        """Bei Auswahländerung"""
        if current is None:
            self.enable_editor(False)
            return

        self.enable_editor(True)

        # Daten laden
        item_data = current.data(Qt.UserRole)
        item_type = item_data[0]
        obj = item_data[1]

        # Blockiere Signale während des Updates
        self.name_edit.blockSignals(True)
        self.visible_check.blockSignals(True)
        self.bold_check.blockSignals(True)
        self.italic_check.blockSignals(True)

        if item_type == 'group':
            self.name_edit.setText(obj.display_label if hasattr(obj, 'display_label') else obj.name)
            self.visible_check.setChecked(getattr(obj, 'show_in_legend', True))
            self.bold_check.setChecked(getattr(obj, 'legend_bold', False))
            self.italic_check.setChecked(getattr(obj, 'legend_italic', False))
        else:  # dataset
            self.name_edit.setText(obj.display_label)
            self.visible_check.setChecked(obj.show_in_legend)
            self.bold_check.setChecked(getattr(obj, 'legend_bold', False))
            self.italic_check.setChecked(getattr(obj, 'legend_italic', False))

        # Signale wieder aktivieren
        self.name_edit.blockSignals(False)
        self.visible_check.blockSignals(False)
        self.bold_check.blockSignals(False)
        self.italic_check.blockSignals(False)

        # Vorschau aktualisieren
        self.update_preview()

    def enable_editor(self, enabled):
        """Editor aktivieren/deaktivieren"""
        self.name_edit.setEnabled(enabled)
        self.visible_check.setEnabled(enabled)
        self.bold_check.setEnabled(enabled)
        self.italic_check.setEnabled(enabled)

    def on_name_changed(self):
        """Name wurde geändert"""
        current = self.entry_list.currentItem()
        if current is None:
            return

        item_data = current.data(Qt.UserRole)
        item_type = item_data[0]
        obj = item_data[1]

        new_name = self.name_edit.text()

        if item_type == 'group':
            if not hasattr(obj, 'display_label'):
                obj.display_label = obj.name
            obj.display_label = new_name
        else:  # dataset
            obj.display_label = new_name

        self.update_list_item(current)
        self.update_preview()

    def on_visibility_changed(self):
        """Sichtbarkeit wurde geändert"""
        current = self.entry_list.currentItem()
        if current is None:
            return

        item_data = current.data(Qt.UserRole)
        item_type = item_data[0]
        obj = item_data[1]

        is_visible = self.visible_check.isChecked()

        if item_type == 'group':
            if not hasattr(obj, 'show_in_legend'):
                obj.show_in_legend = True
            obj.show_in_legend = is_visible
        else:  # dataset
            obj.show_in_legend = is_visible

        self.update_list_item(current)

    def on_format_changed(self):
        """Formatierung wurde geändert"""
        current = self.entry_list.currentItem()
        if current is None:
            return

        item_data = current.data(Qt.UserRole)
        item_type = item_data[0]
        obj = item_data[1]

        is_bold = self.bold_check.isChecked()
        is_italic = self.italic_check.isChecked()

        # Attribute setzen (falls nicht vorhanden)
        if not hasattr(obj, 'legend_bold'):
            obj.legend_bold = False
        if not hasattr(obj, 'legend_italic'):
            obj.legend_italic = False

        obj.legend_bold = is_bold
        obj.legend_italic = is_italic

        self.update_preview()

    def update_list_item(self, list_item):
        """Aktualisiert die Anzeige eines List-Items"""
        item_data = list_item.data(Qt.UserRole)
        item_type = item_data[0]
        obj = item_data[1]

        if item_type == 'group':
            display_name = obj.display_label if hasattr(obj, 'display_label') else obj.name
            prefix = "📁 "
            visible = getattr(obj, 'show_in_legend', True)
        else:  # dataset
            display_name = obj.display_label
            prefix = "   📊 "
            visible = obj.show_in_legend

        text = f"{prefix}{display_name}"
        if not visible:
            text += " (ausgeblendet)"

        list_item.setText(text)

    def move_up(self):
        """Eintrag nach oben verschieben"""
        current_row = self.entry_list.currentRow()
        if current_row > 0:
            # Daten tauschen
            self.legend_items[current_row], self.legend_items[current_row - 1] = \
                self.legend_items[current_row - 1], self.legend_items[current_row]

            # Liste aktualisieren
            self.populate_list()
            self.entry_list.setCurrentRow(current_row - 1)

    def move_down(self):
        """Eintrag nach unten verschieben"""
        current_row = self.entry_list.currentRow()
        if current_row < self.entry_list.count() - 1:
            # Daten tauschen
            self.legend_items[current_row], self.legend_items[current_row + 1] = \
                self.legend_items[current_row + 1], self.legend_items[current_row]

            # Liste aktualisieren
            self.populate_list()
            self.entry_list.setCurrentRow(current_row + 1)

    def get_legend_order(self):
        """Gibt die neue Reihenfolge der Legendeneinträge zurück"""
        return self.legend_items

    def get_legend_settings(self):
        """Gibt die Legendeneinstellungen zurück"""
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
        """Gibt die Schriftart-Einstellungen zurück"""
        return {
            'legend_size': self.legend_size_spin.value(),
            'legend_bold': self.legend_bold.isChecked(),
            'legend_italic': self.legend_italic.isChecked()
        }

    def update_preview(self):
        """Aktualisiert die Vorschau des formatierten Textes (v7.0)"""
        current = self.entry_list.currentItem()
        if current is None:
            self.preview_text.setText("")
            return

        item_data = current.data(Qt.UserRole)
        obj = item_data[1]

        # Aktuellen Text und Formatierung holen
        text = self.name_edit.text()
        is_bold = self.bold_check.isChecked()
        is_italic = self.italic_check.isChecked()

        if not text:
            self.preview_text.setText("<i>Geben Sie einen Namen ein...</i>")
            return

        # MathText preprocessing
        processed = preprocess_mathtext(text)

        # Erstelle HTML-Preview (approximiert das Ergebnis)
        preview_html = self._create_preview_html(processed, is_bold, is_italic)
        self.preview_text.setText(preview_html)

    def _create_preview_html(self, text, is_bold, is_italic):
        """
        Erstellt eine HTML-Vorschau für den MathText.
        Dies ist eine Approximation - das tatsächliche Rendering erfolgt durch Matplotlib.
        """
        # Einfache Ersetzungen für häufige MathText-Befehle
        replacements = {
            r'$\alpha$': 'α',
            r'$\beta$': 'β',
            r'$\gamma$': 'γ',
            r'$\delta$': 'δ',
            r'$\theta$': 'θ',
            r'$\lambda$': 'λ',
            r'$\mu$': 'µ',
            r'$\pi$': 'π',
            r'$\sigma$': 'σ',
            r'$\pm$': '±',
            r'$\times$': '×',
            r'$\cdot$': '·',
            r'\AA': 'Å',
        }

        preview = text
        for mathtext, symbol in replacements.items():
            preview = preview.replace(mathtext, symbol)

        # Ersetze \mathbf{...} und \mathit{...} mit HTML
        import re
        preview = re.sub(r'\$\\mathbf\{([^}]+)\}\$', r'<b>\1</b>', preview)
        preview = re.sub(r'\$\\mathit\{([^}]+)\}\$', r'<i>\1</i>', preview)

        # Verschachtelte Formatierung
        preview = re.sub(r'\\mathbf\{\\mathit\{([^}]+)\}\}', r'<b><i>\1</i></b>', preview)

        # Hochstellung und Tiefstellung (verbessert für {}-Syntax)
        # ^{...} und ^x
        preview = re.sub(r'\^{([^}]+)}', r'<sup>\1</sup>', preview)
        preview = re.sub(r'\^(\w)', r'<sup>\1</sup>', preview)

        # _{...} und _x
        preview = re.sub(r'_{([^}]+)}', r'<sub>\1</sub>', preview)
        preview = re.sub(r'_(\w)', r'<sub>\1</sub>', preview)

        # Entferne übrig gebliebene $ und \
        preview = preview.replace('$', '')
        preview = preview.replace('\\', '')

        # Globale Formatierung anwenden (nur auf Teile ohne HTML-Tags)
        if is_bold and is_italic:
            preview = f"<b><i>{preview}</i></b>"
        elif is_bold:
            preview = f"<b>{preview}</b>"
        elif is_italic:
            preview = f"<i>{preview}</i>"

        return preview

    def show_syntax_help(self):
        """Zeigt Syntax-Hilfe für LaTeX/MathText an (v7.0)"""
        msg = QMessageBox(self)
        msg.setWindowTitle("LaTeX/MathText Syntax-Hilfe")
        msg.setIcon(QMessageBox.Information)
        msg.setText(get_syntax_help_text())
        msg.setStandardButtons(QMessageBox.Ok)

        # Dialog vergrößern
        msg.setMinimumWidth(500)

        msg.exec()
