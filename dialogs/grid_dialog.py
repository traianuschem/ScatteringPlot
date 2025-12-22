"""
Grid Settings Dialog

This dialog allows users to configure grid appearance and tick settings for plots.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QDoubleSpinBox, QCheckBox,
    QDialogButtonBox, QPushButton, QSpinBox, QTabWidget, QWidget
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from i18n import tr


class GridSettingsDialog(QDialog):
    """Dialog für Grid-Einstellungen"""

    def __init__(self, parent, grid_settings):
        super().__init__(parent)
        self.setWindowTitle(tr("grid.title"))
        self.resize(500, 600)
        self.grid_settings = grid_settings.copy()

        layout = QVBoxLayout(self)

        # Tab-Widget für Grid und Ticks
        tabs = QTabWidget()

        # Tab 1: Grid-Einstellungen
        grid_tab = QWidget()
        grid_tab_layout = QVBoxLayout(grid_tab)
        self.setup_grid_tab(grid_tab_layout)
        tabs.addTab(grid_tab, tr("grid.tabs.grid"))

        # Tab 2: Tick-Einstellungen
        tick_tab = QWidget()
        tick_tab_layout = QVBoxLayout(tick_tab)
        self.setup_tick_tab(tick_tab_layout)
        tabs.addTab(tick_tab, tr("grid.tabs.ticks"))

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def setup_grid_tab(self, layout):

        # Major Grid Gruppe
        major_group = QGroupBox(tr("grid.major.title"))
        major_layout = QGridLayout()

        # Major Grid anzeigen
        self.major_enable = QCheckBox(tr("grid.major.show"))
        self.major_enable.setChecked(self.grid_settings.get('major_enable', True))
        major_layout.addWidget(self.major_enable, 0, 0, 1, 2)

        # Major Grid Achsen
        major_layout.addWidget(QLabel(tr("grid.major.axes")), 1, 0)
        self.major_axis_combo = QComboBox()
        self.major_axis_combo.addItems(['both', 'x', 'y'])
        current_axis = self.grid_settings.get('major_axis', 'both')
        index = self.major_axis_combo.findText(current_axis)
        if index >= 0:
            self.major_axis_combo.setCurrentIndex(index)
        major_layout.addWidget(self.major_axis_combo, 1, 1)

        # Major Grid Linientyp
        major_layout.addWidget(QLabel(tr("grid.major.line_style")), 2, 0)
        self.major_linestyle_combo = QComboBox()
        self.major_linestyle_combo.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        current_style = self.grid_settings.get('major_linestyle', 'solid')
        index = self.major_linestyle_combo.findText(current_style)
        if index >= 0:
            self.major_linestyle_combo.setCurrentIndex(index)
        major_layout.addWidget(self.major_linestyle_combo, 2, 1)

        # Major Grid Liniendicke
        major_layout.addWidget(QLabel(tr("grid.major.line_width")), 3, 0)
        self.major_linewidth_spin = QDoubleSpinBox()
        self.major_linewidth_spin.setRange(0.1, 5.0)
        self.major_linewidth_spin.setSingleStep(0.1)
        self.major_linewidth_spin.setValue(self.grid_settings.get('major_linewidth', 0.8))
        self.major_linewidth_spin.setDecimals(1)
        major_layout.addWidget(self.major_linewidth_spin, 3, 1)

        # Major Grid Alpha (Transparenz)
        major_layout.addWidget(QLabel(tr("grid.major.transparency")), 4, 0)
        self.major_alpha_spin = QDoubleSpinBox()
        self.major_alpha_spin.setRange(0.0, 1.0)
        self.major_alpha_spin.setSingleStep(0.1)
        self.major_alpha_spin.setValue(self.grid_settings.get('major_alpha', 0.3))
        self.major_alpha_spin.setDecimals(2)
        major_layout.addWidget(self.major_alpha_spin, 4, 1)

        # Major Grid Farbe
        major_layout.addWidget(QLabel(tr("grid.major.color")), 5, 0)
        self.major_color_button = QPushButton()
        major_color = self.grid_settings.get('major_color', '#FFFFFF')
        self.major_color_button.setStyleSheet(f"background-color: {major_color}; border: 1px solid #555;")
        self.major_color_button.setText(major_color)
        self.major_color_button.clicked.connect(lambda: self.choose_color('major'))
        major_layout.addWidget(self.major_color_button, 5, 1)

        major_group.setLayout(major_layout)
        layout.addWidget(major_group)

        # Minor Grid Gruppe
        minor_group = QGroupBox(tr("grid.minor.title"))
        minor_layout = QGridLayout()

        # Minor Grid anzeigen
        self.minor_enable = QCheckBox(tr("grid.minor.show"))
        self.minor_enable.setChecked(self.grid_settings.get('minor_enable', False))
        minor_layout.addWidget(self.minor_enable, 0, 0, 1, 2)

        # Minor Grid Achsen
        minor_layout.addWidget(QLabel("Achsen:"), 1, 0)
        self.minor_axis_combo = QComboBox()
        self.minor_axis_combo.addItems(['both', 'x', 'y'])
        current_axis = self.grid_settings.get('minor_axis', 'both')
        index = self.minor_axis_combo.findText(current_axis)
        if index >= 0:
            self.minor_axis_combo.setCurrentIndex(index)
        minor_layout.addWidget(self.minor_axis_combo, 1, 1)

        # Minor Grid Linientyp
        minor_layout.addWidget(QLabel("Linientyp:"), 2, 0)
        self.minor_linestyle_combo = QComboBox()
        self.minor_linestyle_combo.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        current_style = self.grid_settings.get('minor_linestyle', 'dotted')
        index = self.minor_linestyle_combo.findText(current_style)
        if index >= 0:
            self.minor_linestyle_combo.setCurrentIndex(index)
        minor_layout.addWidget(self.minor_linestyle_combo, 2, 1)

        # Minor Grid Liniendicke
        minor_layout.addWidget(QLabel("Liniendicke:"), 3, 0)
        self.minor_linewidth_spin = QDoubleSpinBox()
        self.minor_linewidth_spin.setRange(0.1, 5.0)
        self.minor_linewidth_spin.setSingleStep(0.1)
        self.minor_linewidth_spin.setValue(self.grid_settings.get('minor_linewidth', 0.5))
        self.minor_linewidth_spin.setDecimals(1)
        minor_layout.addWidget(self.minor_linewidth_spin, 3, 1)

        # Minor Grid Alpha (Transparenz)
        minor_layout.addWidget(QLabel("Transparenz:"), 4, 0)
        self.minor_alpha_spin = QDoubleSpinBox()
        self.minor_alpha_spin.setRange(0.0, 1.0)
        self.minor_alpha_spin.setSingleStep(0.1)
        self.minor_alpha_spin.setValue(self.grid_settings.get('minor_alpha', 0.2))
        self.minor_alpha_spin.setDecimals(2)
        minor_layout.addWidget(self.minor_alpha_spin, 4, 1)

        # Minor Grid Farbe
        minor_layout.addWidget(QLabel("Farbe:"), 5, 0)
        self.minor_color_button = QPushButton()
        minor_color = self.grid_settings.get('minor_color', '#FFFFFF')
        self.minor_color_button.setStyleSheet(f"background-color: {minor_color}; border: 1px solid #555;")
        self.minor_color_button.setText(minor_color)
        self.minor_color_button.clicked.connect(lambda: self.choose_color('minor'))
        minor_layout.addWidget(self.minor_color_button, 5, 1)

        minor_group.setLayout(minor_layout)
        layout.addWidget(minor_group)
        layout.addStretch()

    def setup_tick_tab(self, layout):
        """Tick-Einstellungen Tab"""

        # Major Ticks
        major_tick_group = QGroupBox("Major Ticks (Hauptmarkierungen)")
        major_tick_layout = QGridLayout()

        # Tick-Richtung
        major_tick_layout.addWidget(QLabel("Richtung:"), 0, 0)
        self.major_tick_direction = QComboBox()
        self.major_tick_direction.addItems(['in', 'out', 'inout'])
        current_dir = self.grid_settings.get('major_tick_direction', 'in')
        index = self.major_tick_direction.findText(current_dir)
        if index >= 0:
            self.major_tick_direction.setCurrentIndex(index)
        major_tick_layout.addWidget(self.major_tick_direction, 0, 1)

        # Tick-Länge
        major_tick_layout.addWidget(QLabel("Länge:"), 1, 0)
        self.major_tick_length = QDoubleSpinBox()
        self.major_tick_length.setRange(0.0, 20.0)
        self.major_tick_length.setSingleStep(0.5)
        self.major_tick_length.setValue(self.grid_settings.get('major_tick_length', 6.0))
        self.major_tick_length.setSuffix(" pt")
        major_tick_layout.addWidget(self.major_tick_length, 1, 1)

        # Tick-Breite
        major_tick_layout.addWidget(QLabel("Breite:"), 2, 0)
        self.major_tick_width = QDoubleSpinBox()
        self.major_tick_width.setRange(0.1, 5.0)
        self.major_tick_width.setSingleStep(0.1)
        self.major_tick_width.setValue(self.grid_settings.get('major_tick_width', 1.0))
        major_tick_layout.addWidget(self.major_tick_width, 2, 1)

        major_tick_group.setLayout(major_tick_layout)
        layout.addWidget(major_tick_group)

        # Minor Ticks
        minor_tick_group = QGroupBox("Minor Ticks (Hilfsmarkierungen)")
        minor_tick_layout = QGridLayout()

        # Minor Ticks anzeigen
        self.minor_ticks_enable = QCheckBox("Minor Ticks anzeigen")
        self.minor_ticks_enable.setChecked(self.grid_settings.get('minor_ticks_enable', True))
        minor_tick_layout.addWidget(self.minor_ticks_enable, 0, 0, 1, 2)

        # Tick-Richtung
        minor_tick_layout.addWidget(QLabel("Richtung:"), 1, 0)
        self.minor_tick_direction = QComboBox()
        self.minor_tick_direction.addItems(['in', 'out', 'inout'])
        current_dir = self.grid_settings.get('minor_tick_direction', 'in')
        index = self.minor_tick_direction.findText(current_dir)
        if index >= 0:
            self.minor_tick_direction.setCurrentIndex(index)
        minor_tick_layout.addWidget(self.minor_tick_direction, 1, 1)

        # Tick-Länge
        minor_tick_layout.addWidget(QLabel("Länge:"), 2, 0)
        self.minor_tick_length = QDoubleSpinBox()
        self.minor_tick_length.setRange(0.0, 20.0)
        self.minor_tick_length.setSingleStep(0.5)
        self.minor_tick_length.setValue(self.grid_settings.get('minor_tick_length', 3.0))
        self.minor_tick_length.setSuffix(" pt")
        minor_tick_layout.addWidget(self.minor_tick_length, 2, 1)

        # Tick-Breite
        minor_tick_layout.addWidget(QLabel("Breite:"), 3, 0)
        self.minor_tick_width = QDoubleSpinBox()
        self.minor_tick_width.setRange(0.1, 5.0)
        self.minor_tick_width.setSingleStep(0.1)
        self.minor_tick_width.setValue(self.grid_settings.get('minor_tick_width', 0.5))
        minor_tick_layout.addWidget(self.minor_tick_width, 3, 1)

        minor_tick_group.setLayout(minor_tick_layout)
        layout.addWidget(minor_tick_group)

        # Tick-Label-Einstellungen
        tick_label_group = QGroupBox("Tick-Label-Einstellungen")
        tick_label_layout = QGridLayout()

        # Label-Rotation
        tick_label_layout.addWidget(QLabel("X-Achse Rotation:"), 0, 0)
        self.x_tick_rotation = QSpinBox()
        self.x_tick_rotation.setRange(-90, 90)
        self.x_tick_rotation.setSingleStep(15)
        self.x_tick_rotation.setValue(self.grid_settings.get('x_tick_rotation', 0))
        self.x_tick_rotation.setSuffix("°")
        tick_label_layout.addWidget(self.x_tick_rotation, 0, 1)

        tick_label_layout.addWidget(QLabel("Y-Achse Rotation:"), 1, 0)
        self.y_tick_rotation = QSpinBox()
        self.y_tick_rotation.setRange(-90, 90)
        self.y_tick_rotation.setSingleStep(15)
        self.y_tick_rotation.setValue(self.grid_settings.get('y_tick_rotation', 0))
        self.y_tick_rotation.setSuffix("°")
        tick_label_layout.addWidget(self.y_tick_rotation, 1, 1)

        # Label-Schriftgröße
        tick_label_layout.addWidget(QLabel("Schriftgröße:"), 2, 0)
        self.tick_labelsize = QSpinBox()
        self.tick_labelsize.setRange(4, 32)
        self.tick_labelsize.setValue(self.grid_settings.get('tick_labelsize', 10))
        self.tick_labelsize.setSuffix(" pt")
        tick_label_layout.addWidget(self.tick_labelsize, 2, 1)

        tick_label_group.setLayout(tick_label_layout)
        layout.addWidget(tick_label_group)

        layout.addStretch()

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
            # Grid-Einstellungen
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
            'minor_color': self.minor_color_button.text(),
            # Tick-Einstellungen
            'major_tick_direction': self.major_tick_direction.currentText(),
            'major_tick_length': self.major_tick_length.value(),
            'major_tick_width': self.major_tick_width.value(),
            'minor_ticks_enable': self.minor_ticks_enable.isChecked(),
            'minor_tick_direction': self.minor_tick_direction.currentText(),
            'minor_tick_length': self.minor_tick_length.value(),
            'minor_tick_width': self.minor_tick_width.value(),
            'x_tick_rotation': self.x_tick_rotation.value(),
            'y_tick_rotation': self.y_tick_rotation.value(),
            'tick_labelsize': self.tick_labelsize.value()
        }
