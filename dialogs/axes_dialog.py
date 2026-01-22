"""
Axes Settings Dialog

This dialog allows users to configure axis labels and titles.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox, QPushButton, QMessageBox, QHBoxLayout,
    QSpinBox, QFontComboBox
)
from utils.mathtext_formatter import get_syntax_help_text, preprocess_mathtext
from i18n import tr


class AxesSettingsDialog(QDialog):
    """Dialog für Achsen-Einstellungen"""

    def __init__(self, parent, current_xlabel=None, current_ylabel=None, plot_type='Log-Log', axis_limits=None, font_settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr("axes.title"))
        self.resize(650, 750)

        # Font settings initialisieren
        if font_settings is None:
            font_settings = {}
        self.font_settings = font_settings

        self.plot_type = plot_type

        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(tr("axes.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Achsentitel-Gruppe
        titles_group = QGroupBox(tr("axes.axis_titles.title"))
        titles_layout = QGridLayout()

        # X-Achsentitel
        titles_layout.addWidget(QLabel(tr("axes.axis_titles.x_title")), 0, 0)
        self.xlabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText(tr("axes.axis_titles.auto_based_on", plot_type=plot_type))
        if current_xlabel:
            self.xlabel_edit.setText(current_xlabel)
        titles_layout.addWidget(self.xlabel_edit, 0, 1)

        # Y-Achsentitel
        titles_layout.addWidget(QLabel(tr("axes.axis_titles.y_title")), 1, 0)
        self.ylabel_edit = QLineEdit()
        self.ylabel_edit.setPlaceholderText(tr("axes.axis_titles.auto_based_on", plot_type=plot_type))
        if current_ylabel:
            self.ylabel_edit.setText(current_ylabel)
        titles_layout.addWidget(self.ylabel_edit, 1, 1)

        # Syntax-Hilfe Button (v7.0)
        syntax_help_btn = QPushButton(tr("axes.axis_titles.latex_help"))
        syntax_help_btn.clicked.connect(self.show_syntax_help)
        titles_layout.addWidget(syntax_help_btn, 2, 0, 1, 2)

        # Vorschau (v7.0)
        titles_layout.addWidget(QLabel(tr("axes.axis_titles.preview")), 3, 0)
        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "background-color: #2b2b2b; "
            "padding: 8px; "
            "border: 1px solid #555; "
            "border-radius: 4px; "
            "min-height: 40px;"
        )
        titles_layout.addWidget(self.preview_label, 3, 1)

        # Connect signals AFTER all UI elements are created
        self.xlabel_edit.textChanged.connect(self.update_preview)
        self.ylabel_edit.textChanged.connect(self.update_preview)

        titles_group.setLayout(titles_layout)
        layout.addWidget(titles_group)

        # Achsenlimits-Gruppe
        limits_group = QGroupBox(tr("axes.limits.title"))
        limits_layout = QGridLayout()

        # Info-Label
        limits_info = QLabel(tr("axes.limits.info"))
        limits_info.setWordWrap(True)
        limits_layout.addWidget(limits_info, 0, 0, 1, 2)

        # Initialisiere axis_limits falls nicht vorhanden
        if axis_limits is None:
            axis_limits = {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None, 'auto': True}

        # X-Limits
        limits_layout.addWidget(QLabel(tr("axes.limits.x_min")), 1, 0)
        self.xmin_edit = QLineEdit()
        self.xmin_edit.setPlaceholderText(tr("axes.limits.placeholder", value="0.001"))
        if axis_limits.get('xmin') is not None:
            self.xmin_edit.setText(str(axis_limits['xmin']))
        limits_layout.addWidget(self.xmin_edit, 1, 1)

        limits_layout.addWidget(QLabel(tr("axes.limits.x_max")), 2, 0)
        self.xmax_edit = QLineEdit()
        self.xmax_edit.setPlaceholderText(tr("axes.limits.placeholder", value="10.0"))
        if axis_limits.get('xmax') is not None:
            self.xmax_edit.setText(str(axis_limits['xmax']))
        limits_layout.addWidget(self.xmax_edit, 2, 1)

        # Y-Limits
        limits_layout.addWidget(QLabel(tr("axes.limits.y_min")), 3, 0)
        self.ymin_edit = QLineEdit()
        self.ymin_edit.setPlaceholderText(tr("axes.limits.placeholder", value="0.001"))
        if axis_limits.get('ymin') is not None:
            self.ymin_edit.setText(str(axis_limits['ymin']))
        limits_layout.addWidget(self.ymin_edit, 3, 1)

        limits_layout.addWidget(QLabel(tr("axes.limits.y_max")), 4, 0)
        self.ymax_edit = QLineEdit()
        self.ymax_edit.setPlaceholderText(tr("axes.limits.placeholder", value="1000.0"))
        if axis_limits.get('ymax') is not None:
            self.ymax_edit.setText(str(axis_limits['ymax']))
        limits_layout.addWidget(self.ymax_edit, 4, 1)

        # Auto-Modus Checkbox
        self.auto_checkbox = QCheckBox(tr("axes.limits.auto_scaling"))
        self.auto_checkbox.setChecked(axis_limits.get('auto', True))
        limits_layout.addWidget(self.auto_checkbox, 5, 0, 1, 2)

        # Reset Limits Button
        reset_limits_btn = QPushButton(tr("axes.limits.reset"))
        reset_limits_btn.clicked.connect(self.reset_limits)
        limits_layout.addWidget(reset_limits_btn, 6, 0, 1, 2)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Schriftart-Einstellungen für Achsenbeschriftungen
        labels_font_group = QGroupBox(tr("axes.font_labels.title"))
        labels_font_layout = QGridLayout()

        # Font Family
        labels_font_layout.addWidget(QLabel(tr("axes.font_labels.family")), 0, 0)
        self.labels_font_combo = QFontComboBox()
        current_labels_font = self.font_settings.get('labels_font_family', 'Arial')
        index = self.labels_font_combo.findText(current_labels_font)
        if index >= 0:
            self.labels_font_combo.setCurrentIndex(index)
        labels_font_layout.addWidget(self.labels_font_combo, 0, 1)

        # Font Size
        labels_font_layout.addWidget(QLabel(tr("axes.font_labels.size")), 1, 0)
        self.labels_size_spin = QSpinBox()
        self.labels_size_spin.setRange(6, 32)
        self.labels_size_spin.setValue(self.font_settings.get('labels_size', 12))
        self.labels_size_spin.setSuffix(" pt")
        labels_font_layout.addWidget(self.labels_size_spin, 1, 1)

        # Bold & Italic
        self.labels_bold = QCheckBox(tr("axes.font_labels.bold"))
        self.labels_bold.setChecked(self.font_settings.get('labels_bold', False))
        labels_font_layout.addWidget(self.labels_bold, 2, 0)

        self.labels_italic = QCheckBox(tr("axes.font_labels.italic"))
        self.labels_italic.setChecked(self.font_settings.get('labels_italic', False))
        labels_font_layout.addWidget(self.labels_italic, 2, 1)

        labels_font_group.setLayout(labels_font_layout)
        layout.addWidget(labels_font_group)

        # Schriftart-Einstellungen für Ticks
        ticks_font_group = QGroupBox(tr("axes.font_ticks.title"))
        ticks_font_layout = QGridLayout()

        # Font Family
        ticks_font_layout.addWidget(QLabel(tr("axes.font_labels.family")), 0, 0)
        self.ticks_font_combo = QFontComboBox()
        current_ticks_font = self.font_settings.get('ticks_font_family', 'Arial')
        index = self.ticks_font_combo.findText(current_ticks_font)
        if index >= 0:
            self.ticks_font_combo.setCurrentIndex(index)
        ticks_font_layout.addWidget(self.ticks_font_combo, 0, 1)

        # Font Size
        ticks_font_layout.addWidget(QLabel(tr("axes.font_labels.size")), 1, 0)
        self.ticks_size_spin = QSpinBox()
        self.ticks_size_spin.setRange(6, 24)
        self.ticks_size_spin.setValue(self.font_settings.get('ticks_size', 10))
        self.ticks_size_spin.setSuffix(" pt")
        ticks_font_layout.addWidget(self.ticks_size_spin, 1, 1)

        # Bold & Italic
        self.ticks_bold = QCheckBox(tr("axes.font_labels.bold"))
        self.ticks_bold.setChecked(self.font_settings.get('ticks_bold', False))
        ticks_font_layout.addWidget(self.ticks_bold, 2, 0)

        self.ticks_italic = QCheckBox(tr("axes.font_labels.italic"))
        self.ticks_italic.setChecked(self.font_settings.get('ticks_italic', False))
        ticks_font_layout.addWidget(self.ticks_italic, 2, 1)

        ticks_font_group.setLayout(ticks_font_layout)
        layout.addWidget(ticks_font_group)

        # Reset-Button
        reset_layout = QHBoxLayout()
        reset_btn = QPushButton(tr("axes.reset_default"))
        reset_btn.clicked.connect(self.reset_labels)
        reset_layout.addStretch()
        reset_layout.addWidget(reset_btn)
        layout.addLayout(reset_layout)

        # Initial preview update
        self.update_preview()

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def reset_labels(self):
        """Setzt Labels auf Standard zurück"""
        self.xlabel_edit.clear()
        self.ylabel_edit.clear()

    def reset_limits(self):
        """Setzt Achsenlimits zurück"""
        self.xmin_edit.clear()
        self.xmax_edit.clear()
        self.ymin_edit.clear()
        self.ymax_edit.clear()
        self.auto_checkbox.setChecked(True)

    def get_labels(self):
        """Gibt die Achsenbeschriftungen zurück"""
        xlabel = self.xlabel_edit.text().strip() if self.xlabel_edit.text().strip() else None
        ylabel = self.ylabel_edit.text().strip() if self.ylabel_edit.text().strip() else None
        return xlabel, ylabel

    def get_axis_limits(self):
        """Gibt die Achsenlimits zurück"""
        try:
            xmin = float(self.xmin_edit.text()) if self.xmin_edit.text() else None
        except ValueError:
            xmin = None

        try:
            xmax = float(self.xmax_edit.text()) if self.xmax_edit.text() else None
        except ValueError:
            xmax = None

        try:
            ymin = float(self.ymin_edit.text()) if self.ymin_edit.text() else None
        except ValueError:
            ymin = None

        try:
            ymax = float(self.ymax_edit.text()) if self.ymax_edit.text() else None
        except ValueError:
            ymax = None

        return {
            'xmin': xmin,
            'xmax': xmax,
            'ymin': ymin,
            'ymax': ymax,
            'auto': self.auto_checkbox.isChecked()
        }

    def get_font_settings(self):
        """Gibt die Schriftart-Einstellungen zurück"""
        return {
            'labels_font_family': self.labels_font_combo.currentText(),
            'labels_size': self.labels_size_spin.value(),
            'labels_bold': self.labels_bold.isChecked(),
            'labels_italic': self.labels_italic.isChecked(),
            'ticks_font_family': self.ticks_font_combo.currentText(),
            'ticks_size': self.ticks_size_spin.value(),
            'ticks_bold': self.ticks_bold.isChecked(),
            'ticks_italic': self.ticks_italic.isChecked()
        }

    def update_preview(self):
        """Aktualisiert die Vorschau der formatierten Achsenbeschriftungen (v7.0)"""
        xlabel = self.xlabel_edit.text()
        ylabel = self.ylabel_edit.text()

        if not xlabel and not ylabel:
            self.preview_label.setText(f"<i>{tr('axes.axis_titles.preview_placeholder')}</i>")
            return

        # MathText preprocessing
        preview_parts = []
        if xlabel:
            processed_x = preprocess_mathtext(xlabel)
            preview_x_html = self._create_preview_html(processed_x)
            preview_parts.append(f"<b>X:</b> {preview_x_html}")

        if ylabel:
            processed_y = preprocess_mathtext(ylabel)
            preview_y_html = self._create_preview_html(processed_y)
            preview_parts.append(f"<b>Y:</b> {preview_y_html}")

        self.preview_label.setText(" | ".join(preview_parts))

    def _create_preview_html(self, text):
        """
        Erstellt eine HTML-Vorschau für den MathText.
        Dies ist eine Approximation - das tatsächliche Rendering erfolgt durch Matplotlib.
        """
        # Einfache Ersetzungen für häufige MathText-Befehle
        replacements = {
            r'$\alpha$': 'α', r'$\beta$': 'β', r'$\gamma$': 'γ',
            r'$\delta$': 'δ', r'$\theta$': 'θ', r'$\lambda$': 'λ',
            r'$\mu$': 'µ', r'$\pi$': 'π', r'$\sigma$': 'σ',
            r'$\pm$': '±', r'$\times$': '×', r'$\cdot$': '·',
            r'$\AA$': 'Å', r'\AA': 'Å',
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

        return preview

    def show_syntax_help(self):
        """Zeigt Syntax-Hilfe für LaTeX/MathText an (v7.0)"""
        msg = QMessageBox(self)
        msg.setWindowTitle("LaTeX/MathText Syntax-Hilfe")
        msg.setIcon(QMessageBox.Information)
        msg.setText(get_syntax_help_text())
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setMinimumWidth(500)
        msg.exec()
