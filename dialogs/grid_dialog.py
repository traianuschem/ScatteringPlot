"""
Grid Settings Dialog

This dialog allows users to configure grid appearance for plots.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QDoubleSpinBox, QCheckBox,
    QDialogButtonBox, QPushButton
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


class GridSettingsDialog(QDialog):
    """Dialog für Grid-Einstellungen"""

    def __init__(self, parent, grid_settings):
        super().__init__(parent)
        self.setWindowTitle("Grid-Einstellungen")
        self.grid_settings = grid_settings.copy()

        layout = QVBoxLayout(self)

        # Major Grid Gruppe
        major_group = QGroupBox("Major Grid (Hauptlinien)")
        major_layout = QGridLayout()

        # Major Grid anzeigen
        self.major_enable = QCheckBox("Major Grid anzeigen")
        self.major_enable.setChecked(grid_settings.get('major_enable', True))
        major_layout.addWidget(self.major_enable, 0, 0, 1, 2)

        # Major Grid Achsen
        major_layout.addWidget(QLabel("Achsen:"), 1, 0)
        self.major_axis_combo = QComboBox()
        self.major_axis_combo.addItems(['both', 'x', 'y'])
        current_axis = grid_settings.get('major_axis', 'both')
        index = self.major_axis_combo.findText(current_axis)
        if index >= 0:
            self.major_axis_combo.setCurrentIndex(index)
        major_layout.addWidget(self.major_axis_combo, 1, 1)

        # Major Grid Linientyp
        major_layout.addWidget(QLabel("Linientyp:"), 2, 0)
        self.major_linestyle_combo = QComboBox()
        self.major_linestyle_combo.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        current_style = grid_settings.get('major_linestyle', 'solid')
        index = self.major_linestyle_combo.findText(current_style)
        if index >= 0:
            self.major_linestyle_combo.setCurrentIndex(index)
        major_layout.addWidget(self.major_linestyle_combo, 2, 1)

        # Major Grid Liniendicke
        major_layout.addWidget(QLabel("Liniendicke:"), 3, 0)
        self.major_linewidth_spin = QDoubleSpinBox()
        self.major_linewidth_spin.setRange(0.1, 5.0)
        self.major_linewidth_spin.setSingleStep(0.1)
        self.major_linewidth_spin.setValue(grid_settings.get('major_linewidth', 0.8))
        self.major_linewidth_spin.setDecimals(1)
        major_layout.addWidget(self.major_linewidth_spin, 3, 1)

        # Major Grid Alpha (Transparenz)
        major_layout.addWidget(QLabel("Transparenz:"), 4, 0)
        self.major_alpha_spin = QDoubleSpinBox()
        self.major_alpha_spin.setRange(0.0, 1.0)
        self.major_alpha_spin.setSingleStep(0.1)
        self.major_alpha_spin.setValue(grid_settings.get('major_alpha', 0.3))
        self.major_alpha_spin.setDecimals(2)
        major_layout.addWidget(self.major_alpha_spin, 4, 1)

        # Major Grid Farbe
        major_layout.addWidget(QLabel("Farbe:"), 5, 0)
        self.major_color_button = QPushButton()
        major_color = grid_settings.get('major_color', '#FFFFFF')
        self.major_color_button.setStyleSheet(f"background-color: {major_color}; border: 1px solid #555;")
        self.major_color_button.setText(major_color)
        self.major_color_button.clicked.connect(lambda: self.choose_color('major'))
        major_layout.addWidget(self.major_color_button, 5, 1)

        major_group.setLayout(major_layout)
        layout.addWidget(major_group)

        # Minor Grid Gruppe
        minor_group = QGroupBox("Minor Grid (Hilfslinien)")
        minor_layout = QGridLayout()

        # Minor Grid anzeigen
        self.minor_enable = QCheckBox("Minor Grid anzeigen")
        self.minor_enable.setChecked(grid_settings.get('minor_enable', False))
        minor_layout.addWidget(self.minor_enable, 0, 0, 1, 2)

        # Minor Grid Achsen
        minor_layout.addWidget(QLabel("Achsen:"), 1, 0)
        self.minor_axis_combo = QComboBox()
        self.minor_axis_combo.addItems(['both', 'x', 'y'])
        current_axis = grid_settings.get('minor_axis', 'both')
        index = self.minor_axis_combo.findText(current_axis)
        if index >= 0:
            self.minor_axis_combo.setCurrentIndex(index)
        minor_layout.addWidget(self.minor_axis_combo, 1, 1)

        # Minor Grid Linientyp
        minor_layout.addWidget(QLabel("Linientyp:"), 2, 0)
        self.minor_linestyle_combo = QComboBox()
        self.minor_linestyle_combo.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        current_style = grid_settings.get('minor_linestyle', 'dotted')
        index = self.minor_linestyle_combo.findText(current_style)
        if index >= 0:
            self.minor_linestyle_combo.setCurrentIndex(index)
        minor_layout.addWidget(self.minor_linestyle_combo, 2, 1)

        # Minor Grid Liniendicke
        minor_layout.addWidget(QLabel("Liniendicke:"), 3, 0)
        self.minor_linewidth_spin = QDoubleSpinBox()
        self.minor_linewidth_spin.setRange(0.1, 5.0)
        self.minor_linewidth_spin.setSingleStep(0.1)
        self.minor_linewidth_spin.setValue(grid_settings.get('minor_linewidth', 0.5))
        self.minor_linewidth_spin.setDecimals(1)
        minor_layout.addWidget(self.minor_linewidth_spin, 3, 1)

        # Minor Grid Alpha (Transparenz)
        minor_layout.addWidget(QLabel("Transparenz:"), 4, 0)
        self.minor_alpha_spin = QDoubleSpinBox()
        self.minor_alpha_spin.setRange(0.0, 1.0)
        self.minor_alpha_spin.setSingleStep(0.1)
        self.minor_alpha_spin.setValue(grid_settings.get('minor_alpha', 0.2))
        self.minor_alpha_spin.setDecimals(2)
        minor_layout.addWidget(self.minor_alpha_spin, 4, 1)

        # Minor Grid Farbe
        minor_layout.addWidget(QLabel("Farbe:"), 5, 0)
        self.minor_color_button = QPushButton()
        minor_color = grid_settings.get('minor_color', '#FFFFFF')
        self.minor_color_button.setStyleSheet(f"background-color: {minor_color}; border: 1px solid #555;")
        self.minor_color_button.setText(minor_color)
        self.minor_color_button.clicked.connect(lambda: self.choose_color('minor'))
        minor_layout.addWidget(self.minor_color_button, 5, 1)

        minor_group.setLayout(minor_layout)
        layout.addWidget(minor_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_color(self, grid_type):
        """Öffnet Farbwahl-Dialog"""
        from PySide6.QtWidgets import QColorDialog

        if grid_type == 'major':
            current_color = self.major_color_button.text()
            button = self.major_color_button
        else:
            current_color = self.minor_color_button.text()
            button = self.minor_color_button

        color = QColorDialog.getColor(QColor(current_color), self, f"{grid_type.capitalize()} Grid Farbe")

        if color.isValid():
            color_hex = color.name()
            button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #555;")
            button.setText(color_hex)

    def get_settings(self):
        """Gibt Einstellungen zurück"""
        return {
            'major_enable': self.major_enable.isChecked(),
            'major_axis': self.major_axis_combo.currentText(),
            'major_linestyle': self.major_linestyle_combo.currentText(),
            'major_linewidth': self.major_linewidth_spin.value(),
            'major_alpha': self.major_alpha_spin.value(),
            'major_color': self.major_color_button.text(),
            'minor_enable': self.minor_enable.isChecked(),
            'minor_axis': self.minor_axis_combo.currentText(),
            'minor_linestyle': self.minor_linestyle_combo.currentText(),
            'minor_linewidth': self.minor_linewidth_spin.value(),
            'minor_alpha': self.minor_alpha_spin.value(),
            'minor_color': self.minor_color_button.text()
        }
