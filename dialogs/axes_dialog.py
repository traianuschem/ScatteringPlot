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

    def __init__(self, parent, current_xlabel=None, current_ylabel=None, plot_type='Log-Log'):
        super().__init__(parent)
        self.setWindowTitle("Achsenbeschriftungen")
        self.resize(500, 300)

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

    def get_labels(self):
        """Gibt die Achsenbeschriftungen zurück"""
        xlabel = self.xlabel_edit.text().strip() if self.xlabel_edit.text().strip() else None
        ylabel = self.ylabel_edit.text().strip() if self.ylabel_edit.text().strip() else None
        return xlabel, ylabel
