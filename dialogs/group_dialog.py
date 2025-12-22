"""
Group Creation Dialog

This dialog allows users to create new data groups with
a name and stack factor.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QDoubleSpinBox
)
from i18n import tr


class CreateGroupDialog(QDialog):
    """Dialog zum Erstellen einer neuen Gruppe"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.new_group.title"))
        self.resize(400, 150)

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(tr("dialogs.new_group.group_name")))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Stack-Faktor
        factor_layout = QHBoxLayout()
        factor_layout.addWidget(QLabel(tr("dialogs.new_group.stack_factor")))
        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(0.0001, 1e15)  # Praktisch unbegrenzt
        self.factor_spin.setValue(1.0)
        self.factor_spin.setDecimals(4)
        self.factor_spin.setSingleStep(0.1)
        factor_layout.addWidget(self.factor_spin)
        layout.addLayout(factor_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        """Gibt Name und Stack-Faktor zurück"""
        return self.name_edit.text(), self.factor_spin.value()
