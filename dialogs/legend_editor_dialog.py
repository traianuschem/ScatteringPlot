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
    QLabel, QWidget, QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt
from utils.mathtext_formatter import get_syntax_help_text, preprocess_mathtext


class LegendEditorDialog(QDialog):
    """Dialog zum Bearbeiten von Legendeneinträgen"""

    def __init__(self, parent, groups, unassigned_datasets):
        super().__init__(parent)
        self.setWindowTitle("Legenden-Editor")
        self.resize(600, 500)

        self.groups = groups
        self.unassigned_datasets = unassigned_datasets

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
            "Bearbeiten Sie die Legendeneinträge. Gruppen können als Zwischenüberschriften "
            "formatiert werden (z.B. fett). Ändern Sie die Reihenfolge mit den Buttons."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Haupt-Bereich
        main_layout = QHBoxLayout()

        # Liste der Einträge
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

        # Editor-Bereich
        editor_group = QGroupBox("Eintrag bearbeiten")
        editor_layout = QVBoxLayout()

        # Name
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

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initial deaktiviert
        self.enable_editor(False)

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
