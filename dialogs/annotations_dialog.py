"""
Annotations Dialog

This dialog allows users to add text annotations to plots.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QDialogButtonBox, QPushButton, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog
from utils.mathtext_formatter import get_syntax_help_text, preprocess_mathtext
from i18n import tr


class AnnotationsDialog(QDialog):
    """Dialog für Annotations/Textfelder"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("annotations.title"))

        layout = QVBoxLayout(self)

        # Text-Gruppe
        text_group = QGroupBox(tr("annotations.text.title"))
        text_layout = QGridLayout()

        text_layout.addWidget(QLabel(tr("annotations.text.label")), 0, 0)
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText(tr("annotations.text.placeholder"))
        self.text_edit.textChanged.connect(self.update_preview)
        text_layout.addWidget(self.text_edit, 0, 1)

        # Syntax-Hilfe Button (v7.0)
        syntax_help_btn = QPushButton(tr("annotations.text.latex_help"))
        syntax_help_btn.clicked.connect(self.show_syntax_help)
        text_layout.addWidget(syntax_help_btn, 1, 0, 1, 2)

        # Vorschau (v7.0)
        text_layout.addWidget(QLabel(tr("annotations.text.preview")), 2, 0)
        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "background-color: #2b2b2b; "
            "padding: 8px; "
            "border: 1px solid #555; "
            "border-radius: 4px; "
            "min-height: 30px;"
        )
        text_layout.addWidget(self.preview_label, 2, 1)

        text_group.setLayout(text_layout)
        layout.addWidget(text_group)

        # Position-Gruppe
        pos_group = QGroupBox(tr("annotations.position.title"))
        pos_layout = QGridLayout()

        pos_layout.addWidget(QLabel(tr("annotations.position.x")), 0, 0)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-1e6, 1e6)
        self.x_spin.setDecimals(3)
        self.x_spin.setValue(0.1)
        pos_layout.addWidget(self.x_spin, 0, 1)

        pos_layout.addWidget(QLabel(tr("annotations.position.y")), 1, 0)
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-1e6, 1e6)
        self.y_spin.setDecimals(3)
        self.y_spin.setValue(1.0)
        pos_layout.addWidget(self.y_spin, 1, 1)

        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)

        # Stil-Gruppe
        style_group = QGroupBox(tr("annotations.style.title"))
        style_layout = QGridLayout()

        style_layout.addWidget(QLabel(tr("annotations.style.font_size")), 0, 0)
        self.fontsize_spin = QSpinBox()
        self.fontsize_spin.setRange(6, 32)
        self.fontsize_spin.setValue(12)
        self.fontsize_spin.setSuffix(" pt")
        style_layout.addWidget(self.fontsize_spin, 0, 1)

        style_layout.addWidget(QLabel(tr("annotations.style.color")), 1, 0)
        self.color_button = QPushButton()
        self.color = '#FFFFFF'
        self.color_button.setStyleSheet(f"background-color: {self.color}; border: 1px solid #555;")
        self.color_button.setText(self.color)
        self.color_button.clicked.connect(self.choose_color)
        style_layout.addWidget(self.color_button, 1, 1)

        style_layout.addWidget(QLabel(tr("annotations.style.rotation")), 2, 0)
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(0, 360)
        self.rotation_spin.setValue(0)
        self.rotation_spin.setSuffix("°")
        style_layout.addWidget(self.rotation_spin, 2, 1)

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_color(self):
        """Öffnet Farbwahl-Dialog"""
        color = QColorDialog.getColor(QColor(self.color), self, tr("annotations.text_color_dialog"))
        if color.isValid():
            self.color = color.name()
            self.color_button.setStyleSheet(f"background-color: {self.color}; border: 1px solid #555;")
            self.color_button.setText(self.color)

    def get_annotation(self):
        """Gibt Annotation-Dict zurück"""
        return {
            'text': self.text_edit.text(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'fontsize': self.fontsize_spin.value(),
            'color': self.color,
            'rotation': self.rotation_spin.value()
        }

    def update_preview(self):
        """Aktualisiert die Vorschau des formatierten Textes (v7.0)"""
        text = self.text_edit.text()

        if not text:
            self.preview_label.setText(f"<i>{tr('annotations.text.preview_placeholder')}</i>")
            return

        # MathText preprocessing
        processed = preprocess_mathtext(text)

        # Erstelle HTML-Preview (approximiert das Ergebnis)
        preview_html = self._create_preview_html(processed)
        self.preview_label.setText(preview_html)

    def _create_preview_html(self, text):
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
