"""
Plot Limits Dialog

This dialog allows users to set individual plot limits for a dataset.
Only data points within these limits will be displayed.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox, QPushButton
)
from PySide6.QtCore import Qt
from i18n import tr


class PlotLimitsDialog(QDialog):
    """Dialog zum Festlegen individueller Plotgrenzen für einen Datensatz"""

    def __init__(self, parent, dataset):
        super().__init__(parent)
        self.dataset = dataset
        self.setWindowTitle(tr("plot_limits.title", dataset=dataset.name))
        self.resize(450, 300)

        layout = QVBoxLayout(self)

        # Info-Label
        info_label = QLabel(tr("plot_limits.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Grenzen-Gruppe
        limits_group = QGroupBox(tr("plot_limits.limits.title"))
        limits_layout = QGridLayout()

        # X-Grenzen
        limits_layout.addWidget(QLabel(tr("plot_limits.limits.x_min")), 0, 0)
        self.x_min_edit = QLineEdit()
        self.x_min_edit.setPlaceholderText("z.B. 0.001")
        if dataset.x_min is not None:
            self.x_min_edit.setText(str(dataset.x_min))
        limits_layout.addWidget(self.x_min_edit, 0, 1)

        limits_layout.addWidget(QLabel(tr("plot_limits.limits.x_max")), 1, 0)
        self.x_max_edit = QLineEdit()
        self.x_max_edit.setPlaceholderText("z.B. 10.0")
        if dataset.x_max is not None:
            self.x_max_edit.setText(str(dataset.x_max))
        limits_layout.addWidget(self.x_max_edit, 1, 1)

        # Y-Grenzen
        limits_layout.addWidget(QLabel(tr("plot_limits.limits.y_min")), 2, 0)
        self.y_min_edit = QLineEdit()
        self.y_min_edit.setPlaceholderText("z.B. 0.0")
        if dataset.y_min is not None:
            self.y_min_edit.setText(str(dataset.y_min))
        limits_layout.addWidget(self.y_min_edit, 2, 1)

        limits_layout.addWidget(QLabel(tr("plot_limits.limits.y_max")), 3, 0)
        self.y_max_edit = QLineEdit()
        self.y_max_edit.setPlaceholderText("z.B. 100.0")
        if dataset.y_max is not None:
            self.y_max_edit.setText(str(dataset.y_max))
        limits_layout.addWidget(self.y_max_edit, 3, 1)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Info über Datenbereich
        data_info_group = QGroupBox(tr("plot_limits.data_range.title"))
        data_info_layout = QGridLayout()

        data_info_layout.addWidget(QLabel(tr("plot_limits.data_range.x_range")), 0, 0)
        x_range = f"{dataset.x.min():.6g} bis {dataset.x.max():.6g}"
        data_info_layout.addWidget(QLabel(x_range), 0, 1)

        data_info_layout.addWidget(QLabel(tr("plot_limits.data_range.y_range")), 1, 0)
        y_range = f"{dataset.y.min():.6g} bis {dataset.y.max():.6g}"
        data_info_layout.addWidget(QLabel(y_range), 1, 1)

        data_info_group.setLayout(data_info_layout)
        layout.addWidget(data_info_group)

        # Reset-Button
        reset_btn = QPushButton(tr("plot_limits.reset_all"))
        reset_btn.clicked.connect(self.reset_limits)
        layout.addWidget(reset_btn)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def reset_limits(self):
        """Setzt alle Grenzen zurück"""
        self.x_min_edit.clear()
        self.x_max_edit.clear()
        self.y_min_edit.clear()
        self.y_max_edit.clear()

    def get_limits(self):
        """Gibt die gesetzten Grenzen zurück"""
        try:
            x_min = float(self.x_min_edit.text()) if self.x_min_edit.text() else None
        except ValueError:
            x_min = None

        try:
            x_max = float(self.x_max_edit.text()) if self.x_max_edit.text() else None
        except ValueError:
            x_max = None

        try:
            y_min = float(self.y_min_edit.text()) if self.y_min_edit.text() else None
        except ValueError:
            y_min = None

        try:
            y_max = float(self.y_max_edit.text()) if self.y_max_edit.text() else None
        except ValueError:
            y_max = None

        return x_min, x_max, y_min, y_max
