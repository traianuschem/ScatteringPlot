"""
Plot Settings Dialog

This dialog allows users to configure advanced plot settings
such as axis limits.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QCheckBox, QDialogButtonBox
)


class PlotSettingsDialog(QDialog):
    """Dialog für erweiterte Plot-Einstellungen"""

    def __init__(self, parent, axis_limits):
        super().__init__(parent)
        self.setWindowTitle("Erweiterte Plot-Einstellungen")
        self.axis_limits = axis_limits.copy()

        layout = QVBoxLayout(self)

        # Achsenlimits
        limits_group = QGroupBox("Achsenlimits")
        limits_layout = QGridLayout()

        limits_layout.addWidget(QLabel("X min:"), 0, 0)
        self.xmin_edit = QLineEdit()
        if axis_limits['xmin'] is not None:
            self.xmin_edit.setText(str(axis_limits['xmin']))
        limits_layout.addWidget(self.xmin_edit, 0, 1)

        limits_layout.addWidget(QLabel("X max:"), 0, 2)
        self.xmax_edit = QLineEdit()
        if axis_limits['xmax'] is not None:
            self.xmax_edit.setText(str(axis_limits['xmax']))
        limits_layout.addWidget(self.xmax_edit, 0, 3)

        limits_layout.addWidget(QLabel("Y min:"), 1, 0)
        self.ymin_edit = QLineEdit()
        if axis_limits['ymin'] is not None:
            self.ymin_edit.setText(str(axis_limits['ymin']))
        limits_layout.addWidget(self.ymin_edit, 1, 1)

        limits_layout.addWidget(QLabel("Y max:"), 1, 2)
        self.ymax_edit = QLineEdit()
        if axis_limits['ymax'] is not None:
            self.ymax_edit.setText(str(axis_limits['ymax']))
        limits_layout.addWidget(self.ymax_edit, 1, 3)

        self.auto_checkbox = QCheckBox("Automatisch")
        self.auto_checkbox.setChecked(axis_limits.get('auto', True))
        limits_layout.addWidget(self.auto_checkbox, 2, 0, 1, 4)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_limits(self):
        """Gibt Limits zurück"""
        try:
            xmin = float(self.xmin_edit.text()) if self.xmin_edit.text() else None
        except:
            xmin = None

        try:
            xmax = float(self.xmax_edit.text()) if self.xmax_edit.text() else None
        except:
            xmax = None

        try:
            ymin = float(self.ymin_edit.text()) if self.ymin_edit.text() else None
        except:
            ymin = None

        try:
            ymax = float(self.ymax_edit.text()) if self.ymax_edit.text() else None
        except:
            ymax = None

        return {
            'xmin': xmin,
            'xmax': xmax,
            'ymin': ymin,
            'ymax': ymax,
            'auto': self.auto_checkbox.isChecked()
        }
