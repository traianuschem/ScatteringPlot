"""
Reference Lines Dialog

This dialog allows users to add vertical or horizontal reference lines to plots.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QDoubleSpinBox, QLineEdit,
    QDialogButtonBox, QPushButton
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog
from i18n import tr


class ReferenceLinesDialog(QDialog):
    """Dialog für Referenzlinien"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("reference_lines.title"))

        layout = QVBoxLayout(self)

        # Typ-Gruppe
        type_group = QGroupBox(tr("reference_lines.type.title"))
        type_layout = QGridLayout()

        type_layout.addWidget(QLabel(tr("reference_lines.type.orientation")), 0, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems([tr("reference_lines.type.vertical"), tr("reference_lines.type.horizontal")])
        type_layout.addWidget(self.type_combo, 0, 1)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Position-Gruppe
        pos_group = QGroupBox(tr("reference_lines.position.title"))
        pos_layout = QGridLayout()

        pos_layout.addWidget(QLabel(tr("reference_lines.position.value")), 0, 0)
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1e6, 1e6)
        self.value_spin.setDecimals(3)
        self.value_spin.setValue(0.5)
        pos_layout.addWidget(self.value_spin, 0, 1)

        pos_layout.addWidget(QLabel(tr("reference_lines.position.label")), 1, 0)
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText(tr("reference_lines.position.label_placeholder"))
        pos_layout.addWidget(self.label_edit, 1, 1)

        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)

        # Stil-Gruppe
        style_group = QGroupBox(tr("reference_lines.style.title"))
        style_layout = QGridLayout()

        style_layout.addWidget(QLabel(tr("reference_lines.style.line_type")), 0, 0)
        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        self.linestyle_combo.setCurrentText('dashed')
        style_layout.addWidget(self.linestyle_combo, 0, 1)

        style_layout.addWidget(QLabel(tr("reference_lines.style.line_width")), 1, 0)
        self.linewidth_spin = QDoubleSpinBox()
        self.linewidth_spin.setRange(0.5, 5.0)
        self.linewidth_spin.setSingleStep(0.5)
        self.linewidth_spin.setValue(1.5)
        style_layout.addWidget(self.linewidth_spin, 1, 1)

        style_layout.addWidget(QLabel(tr("reference_lines.style.color")), 2, 0)
        self.color_button = QPushButton()
        self.color = '#FF0000'
        self.color_button.setStyleSheet(f"background-color: {self.color}; border: 1px solid #555;")
        self.color_button.setText(self.color)
        self.color_button.clicked.connect(self.choose_color)
        style_layout.addWidget(self.color_button, 2, 1)

        style_layout.addWidget(QLabel(tr("reference_lines.style.alpha")), 3, 0)
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.0, 1.0)
        self.alpha_spin.setSingleStep(0.1)
        self.alpha_spin.setValue(0.8)
        self.alpha_spin.setDecimals(2)
        style_layout.addWidget(self.alpha_spin, 3, 1)

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_color(self):
        """Öffnet Farbwahl-Dialog"""
        color = QColorDialog.getColor(QColor(self.color), self, tr("reference_lines.line_color_dialog"))
        if color.isValid():
            self.color = color.name()
            self.color_button.setStyleSheet(f"background-color: {self.color}; border: 1px solid #555;")
            self.color_button.setText(self.color)

    def get_reference_line(self):
        """Gibt Referenzlinie-Dict zurück"""
        return {
            'type': 'vertical' if self.type_combo.currentIndex() == 0 else 'horizontal',
            'value': self.value_spin.value(),
            'label': self.label_edit.text(),
            'linestyle': self.linestyle_combo.currentText(),
            'linewidth': self.linewidth_spin.value(),
            'color': self.color,
            'alpha': self.alpha_spin.value()
        }
