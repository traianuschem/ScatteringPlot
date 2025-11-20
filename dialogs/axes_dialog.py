"""
Axes Settings Dialog

This dialog allows users to configure axis labels and titles.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox
)


class AxesSettingsDialog(QDialog):
    """Dialog für Achsen-Einstellungen"""

    def __init__(self, parent, current_xlabel=None, current_ylabel=None, plot_type='Log-Log', axis_limits=None):
        super().__init__(parent)
        self.setWindowTitle("Achsen und Limits")
        self.resize(550, 550)

        self.plot_type = plot_type

        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(
            "Passen Sie die Achsenbeschriftungen an. Leer lassen für automatische Beschriftung "
            "basierend auf dem Plot-Typ."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Achsentitel-Gruppe
        titles_group = QGroupBox("Achsentitel")
        titles_layout = QGridLayout()

        # X-Achsentitel
        titles_layout.addWidget(QLabel("X-Achse Titel:"), 0, 0)
        self.xlabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText(f"Auto: basiert auf '{plot_type}'")
        if current_xlabel:
            self.xlabel_edit.setText(current_xlabel)
        titles_layout.addWidget(self.xlabel_edit, 0, 1)

        # Y-Achsentitel
        titles_layout.addWidget(QLabel("Y-Achse Titel:"), 1, 0)
        self.ylabel_edit = QLineEdit()
        self.ylabel_edit.setPlaceholderText(f"Auto: basiert auf '{plot_type}'")
        if current_ylabel:
            self.ylabel_edit.setText(current_ylabel)
        titles_layout.addWidget(self.ylabel_edit, 1, 1)

        titles_group.setLayout(titles_layout)
        layout.addWidget(titles_group)

        # Achsenlimits-Gruppe
        limits_group = QGroupBox("Achsenlimits")
        limits_layout = QGridLayout()

        # Info-Label
        limits_info = QLabel(
            "Legen Sie feste Achsenlimits fest. Diese bleiben beim Plot-Update erhalten."
        )
        limits_info.setWordWrap(True)
        limits_layout.addWidget(limits_info, 0, 0, 1, 2)

        # Initialisiere axis_limits falls nicht vorhanden
        if axis_limits is None:
            axis_limits = {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None, 'auto': True}

        # X-Limits
        limits_layout.addWidget(QLabel("X-Minimum:"), 1, 0)
        self.xmin_edit = QLineEdit()
        self.xmin_edit.setPlaceholderText("z.B. 0.001")
        if axis_limits.get('xmin') is not None:
            self.xmin_edit.setText(str(axis_limits['xmin']))
        limits_layout.addWidget(self.xmin_edit, 1, 1)

        limits_layout.addWidget(QLabel("X-Maximum:"), 2, 0)
        self.xmax_edit = QLineEdit()
        self.xmax_edit.setPlaceholderText("z.B. 10.0")
        if axis_limits.get('xmax') is not None:
            self.xmax_edit.setText(str(axis_limits['xmax']))
        limits_layout.addWidget(self.xmax_edit, 2, 1)

        # Y-Limits
        limits_layout.addWidget(QLabel("Y-Minimum:"), 3, 0)
        self.ymin_edit = QLineEdit()
        self.ymin_edit.setPlaceholderText("z.B. 0.001")
        if axis_limits.get('ymin') is not None:
            self.ymin_edit.setText(str(axis_limits['ymin']))
        limits_layout.addWidget(self.ymin_edit, 3, 1)

        limits_layout.addWidget(QLabel("Y-Maximum:"), 4, 0)
        self.ymax_edit = QLineEdit()
        self.ymax_edit.setPlaceholderText("z.B. 1000.0")
        if axis_limits.get('ymax') is not None:
            self.ymax_edit.setText(str(axis_limits['ymax']))
        limits_layout.addWidget(self.ymax_edit, 4, 1)

        # Auto-Modus Checkbox
        self.auto_checkbox = QCheckBox("Automatische Skalierung (ignoriert obige Werte)")
        self.auto_checkbox.setChecked(axis_limits.get('auto', True))
        limits_layout.addWidget(self.auto_checkbox, 5, 0, 1, 2)

        # Reset Limits Button
        from PySide6.QtWidgets import QPushButton
        reset_limits_btn = QPushButton("Limits zurücksetzen")
        reset_limits_btn.clicked.connect(self.reset_limits)
        limits_layout.addWidget(reset_limits_btn, 6, 0, 1, 2)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # LaTeX/Math-Text Unterstützung
        math_group = QGroupBox("Formatierung")
        math_layout = QGridLayout()

        math_info = QLabel(
            "Hinweis: Sie können LaTeX-Notation verwenden:\n"
            "- Griechische Buchstaben: \\alpha, \\beta, \\gamma, etc.\n"
            "- Hochgestellt: x^2, e^{-x}\n"
            "- Tiefgestellt: H_2O, x_{max}\n"
            "- Formeln: $\\frac{1}{x}$, $\\sqrt{x}$\n"
            "Beispiel: $q$ [$\\AA^{-1}$] oder I(q) [cm$^{-1}$]"
        )
        math_info.setWordWrap(True)
        math_info.setStyleSheet("QLabel { font-size: 9pt; color: #888; }")
        math_layout.addWidget(math_info, 0, 0)

        math_group.setLayout(math_layout)
        layout.addWidget(math_group)

        # Reset-Button
        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        reset_layout = QHBoxLayout()
        reset_btn = QPushButton("Auf Standard zurücksetzen")
        reset_btn.clicked.connect(self.reset_labels)
        reset_layout.addStretch()
        reset_layout.addWidget(reset_btn)
        layout.addLayout(reset_layout)

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
