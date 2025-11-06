"""
Legend Settings Dialog

This dialog allows users to configure legend appearance and position.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QDialogButtonBox
)


class LegendSettingsDialog(QDialog):
    """Dialog für Legenden-Einstellungen"""

    def __init__(self, parent, legend_settings):
        super().__init__(parent)
        self.setWindowTitle("Legenden-Einstellungen")
        self.legend_settings = legend_settings.copy()

        layout = QVBoxLayout(self)

        # Legenden-Gruppe
        legend_group = QGroupBox("Legenden-Einstellungen")
        legend_layout = QGridLayout()

        # Position
        legend_layout.addWidget(QLabel("Position:"), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            'best',
            'upper right',
            'upper left',
            'lower right',
            'lower left',
            'center',
            'center left',
            'center right',
            'lower center',
            'upper center',
            'right',
            'left'
        ])
        current_pos = legend_settings.get('position', 'best')
        index = self.position_combo.findText(current_pos)
        if index >= 0:
            self.position_combo.setCurrentIndex(index)
        legend_layout.addWidget(self.position_combo, 0, 1)

        # Schriftgröße
        legend_layout.addWidget(QLabel("Schriftgröße:"), 1, 0)
        self.fontsize_spin = QSpinBox()
        self.fontsize_spin.setRange(4, 32)
        self.fontsize_spin.setValue(legend_settings.get('fontsize', 10))
        self.fontsize_spin.setSuffix(" pt")
        legend_layout.addWidget(self.fontsize_spin, 1, 1)

        # Anzahl Spalten
        legend_layout.addWidget(QLabel("Spalten:"), 2, 0)
        self.ncol_spin = QSpinBox()
        self.ncol_spin.setRange(1, 10)
        self.ncol_spin.setValue(legend_settings.get('ncol', 1))
        legend_layout.addWidget(self.ncol_spin, 2, 1)

        # Transparenz (Alpha)
        legend_layout.addWidget(QLabel("Transparenz:"), 3, 0)
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.0, 1.0)
        self.alpha_spin.setSingleStep(0.1)
        self.alpha_spin.setValue(legend_settings.get('alpha', 0.9))
        self.alpha_spin.setDecimals(2)
        legend_layout.addWidget(self.alpha_spin, 3, 1)

        # Rahmen
        self.frame_checkbox = QCheckBox("Rahmen anzeigen")
        self.frame_checkbox.setChecked(legend_settings.get('frameon', True))
        legend_layout.addWidget(self.frame_checkbox, 4, 0, 1, 2)

        # Schatten
        self.shadow_checkbox = QCheckBox("Schatten")
        self.shadow_checkbox.setChecked(legend_settings.get('shadow', False))
        legend_layout.addWidget(self.shadow_checkbox, 5, 0, 1, 2)

        # Fancy Box
        self.fancybox_checkbox = QCheckBox("Abgerundete Ecken")
        self.fancybox_checkbox.setChecked(legend_settings.get('fancybox', True))
        legend_layout.addWidget(self.fancybox_checkbox, 6, 0, 1, 2)

        legend_group.setLayout(legend_layout)
        layout.addWidget(legend_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        """Gibt Einstellungen zurück"""
        return {
            'position': self.position_combo.currentText(),
            'fontsize': self.fontsize_spin.value(),
            'ncol': self.ncol_spin.value(),
            'alpha': self.alpha_spin.value(),
            'frameon': self.frame_checkbox.isChecked(),
            'shadow': self.shadow_checkbox.isChecked(),
            'fancybox': self.fancybox_checkbox.isChecked()
        }
