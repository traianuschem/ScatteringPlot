"""
User Metadata Editor Dialog für ScatterForge Plot

Dialog zur Bearbeitung von Benutzer-Metadaten für wissenschaftliche Exports.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QLabel, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
from utils.user_metadata import UserMetadataManager
from i18n import tr


class UserMetadataDialog(QDialog):
    """
    Dialog zur Bearbeitung von Benutzer-Metadaten.

    Ermöglicht die Eingabe und Verwaltung von:
    - Persönlichen Daten (Name, E-Mail, ORCID)
    - Affiliation (Institution, Abteilung, ROR-ID)
    - Export-Defaults (Lizenz, Optionen)
    """

    def __init__(self, metadata_manager: UserMetadataManager, parent=None):
        """
        Initialisiert den Dialog.

        Args:
            metadata_manager: UserMetadataManager-Instanz
            parent: Parent-Widget
        """
        super().__init__(parent)
        self.metadata_manager = metadata_manager
        self.setWindowTitle(tr("user_metadata.title"))
        self.setMinimumWidth(600)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Erstellt die Benutzeroberfläche."""
        layout = QVBoxLayout()

        # Info-Text oben
        info_label = QLabel(tr("user_metadata.info"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(info_label)

        # Persönliche Daten
        personal_group = QGroupBox(tr("user_metadata.personal.title"))
        personal_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("user_metadata.personal.name_placeholder"))

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText(tr("user_metadata.personal.email_placeholder"))

        self.orcid_input = QLineEdit()
        self.orcid_input.setPlaceholderText(tr("user_metadata.personal.orcid_placeholder"))
        self.orcid_input.textChanged.connect(self.validate_orcid_input)

        # ORCID Info-Label
        self.orcid_info = QLabel()
        self.orcid_info.setWordWrap(True)
        self.orcid_info.setStyleSheet("color: #666; font-size: 10px;")
        self.orcid_info.setText(tr("user_metadata.personal.orcid_info"))

        personal_layout.addRow(tr("user_metadata.personal.name"), self.name_input)
        personal_layout.addRow(tr("user_metadata.personal.email"), self.email_input)
        personal_layout.addRow(tr("user_metadata.personal.orcid"), self.orcid_input)
        personal_layout.addRow("", self.orcid_info)

        personal_group.setLayout(personal_layout)
        layout.addWidget(personal_group)

        # Affiliation
        affiliation_group = QGroupBox(tr("user_metadata.affiliation.title"))
        affiliation_layout = QFormLayout()

        self.institution_input = QLineEdit()
        self.institution_input.setPlaceholderText(tr("user_metadata.affiliation.institution_placeholder"))

        self.department_input = QLineEdit()
        self.department_input.setPlaceholderText(tr("user_metadata.affiliation.department_placeholder"))

        self.ror_input = QLineEdit()
        self.ror_input.setPlaceholderText(tr("user_metadata.affiliation.ror_placeholder"))

        # ROR Info-Label
        ror_info = QLabel(tr("user_metadata.affiliation.ror_info"))
        ror_info.setWordWrap(True)
        ror_info.setStyleSheet("color: #666; font-size: 10px;")

        affiliation_layout.addRow(tr("user_metadata.affiliation.institution"), self.institution_input)
        affiliation_layout.addRow(tr("user_metadata.affiliation.department"), self.department_input)
        affiliation_layout.addRow(tr("user_metadata.affiliation.ror"), self.ror_input)
        affiliation_layout.addRow("", ror_info)

        affiliation_group.setLayout(affiliation_layout)
        layout.addWidget(affiliation_group)

        # Export-Defaults
        defaults_group = QGroupBox(tr("user_metadata.export_defaults.title"))
        defaults_layout = QVBoxLayout()

        # Lizenz
        license_layout = QHBoxLayout()
        license_layout.addWidget(QLabel(tr("user_metadata.export_defaults.license")))

        self.license_combo = QComboBox()
        self.license_combo.addItems([
            "CC-BY-4.0",
            "CC-BY-SA-4.0",
            "CC-BY-NC-4.0",
            "CC-BY-NC-SA-4.0",
            "CC0-1.0",
            "All Rights Reserved"
        ])
        self.license_combo.currentTextChanged.connect(self.update_license_info)

        license_layout.addWidget(self.license_combo)
        license_layout.addStretch()
        defaults_layout.addLayout(license_layout)

        # Lizenz-Info
        self.license_info = QLabel()
        self.license_info.setWordWrap(True)
        self.license_info.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        defaults_layout.addWidget(self.license_info)

        # Checkboxen
        self.timestamp_check = QCheckBox(tr("user_metadata.export_defaults.timestamp"))
        self.timestamp_check.setToolTip(tr("user_metadata.export_defaults.timestamp_tooltip"))

        self.provenance_check = QCheckBox(tr("user_metadata.export_defaults.provenance"))
        self.provenance_check.setToolTip(tr("user_metadata.export_defaults.provenance_tooltip"))

        self.uuid_check = QCheckBox(tr("user_metadata.export_defaults.uuid"))
        self.uuid_check.setToolTip(tr("user_metadata.export_defaults.uuid_tooltip"))

        defaults_layout.addWidget(self.timestamp_check)
        defaults_layout.addWidget(self.provenance_check)
        defaults_layout.addWidget(self.uuid_check)

        defaults_group.setLayout(defaults_layout)
        layout.addWidget(defaults_group)

        # Speicherort
        path_group = QGroupBox(tr("user_metadata.path.title"))
        path_layout = QHBoxLayout()

        self.path_label = QLabel()
        self.path_label.setStyleSheet("font-family: monospace; color: #333;")

        change_path_btn = QPushButton(tr("user_metadata.path.change"))
        change_path_btn.setToolTip(tr("user_metadata.path.change_tooltip"))
        change_path_btn.clicked.connect(self.change_save_location)

        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(change_path_btn)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # Hinweis zu Pflichtfeldern
        required_label = QLabel(tr("user_metadata.required"))
        required_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        layout.addWidget(required_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Save
        )
        button_box.button(QDialogButtonBox.Save).setText(tr("user_metadata.buttons.save"))
        button_box.button(QDialogButtonBox.Cancel).setText(tr("user_metadata.buttons.cancel"))
        button_box.accepted.connect(self.save_and_close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_data(self):
        """Lädt Daten aus dem MetadataManager in die UI."""
        meta = self.metadata_manager.metadata

        # Persönliche Daten
        self.name_input.setText(meta['user'].get('name', ''))
        self.email_input.setText(meta['user'].get('email', ''))
        self.orcid_input.setText(meta['user'].get('orcid', ''))

        # Affiliation
        self.institution_input.setText(meta['affiliation'].get('institution', ''))
        self.department_input.setText(meta['affiliation'].get('department', ''))
        self.ror_input.setText(meta['affiliation'].get('ror', ''))

        # Export-Defaults
        self.license_combo.setCurrentText(meta['export_defaults'].get('license', 'CC-BY-4.0'))
        self.timestamp_check.setChecked(meta['export_defaults'].get('auto_timestamp', True))
        self.provenance_check.setChecked(meta['export_defaults'].get('include_provenance', True))
        self.uuid_check.setChecked(meta['export_defaults'].get('generate_uuid', False))

        # Pfad
        self.update_path_label()
        self.update_license_info()

    def update_path_label(self):
        """Aktualisiert das Pfad-Label."""
        if self.metadata_manager.current_file:
            path_text = str(self.metadata_manager.current_file)
            # Kürzen, falls zu lang
            if len(path_text) > 60:
                path_text = "..." + path_text[-57:]
        else:
            path_text = tr("user_metadata.path.not_saved")

        self.path_label.setText(path_text)

    def update_license_info(self):
        """Aktualisiert die Lizenz-Beschreibung."""
        license_texts = {
            'CC-BY-4.0': tr('user_metadata.licenses.cc_by'),
            'CC-BY-SA-4.0': tr('user_metadata.licenses.cc_by_sa'),
            'CC-BY-NC-4.0': tr('user_metadata.licenses.cc_by_nc'),
            'CC-BY-NC-SA-4.0': tr('user_metadata.licenses.cc_by_nc_sa'),
            'CC0-1.0': tr('user_metadata.licenses.cc0'),
            'All Rights Reserved': tr('user_metadata.licenses.all_rights')
        }

        license_name = self.license_combo.currentText()
        self.license_info.setText(license_texts.get(license_name, ''))

    def validate_orcid_input(self):
        """Validiert ORCID-Eingabe und zeigt Feedback."""
        orcid = self.orcid_input.text().strip()

        if not orcid:
            self.orcid_info.setStyleSheet("color: #666; font-size: 10px;")
            self.orcid_info.setText(tr("user_metadata.personal.orcid_info"))
            return

        is_valid = self.metadata_manager.validate_orcid(orcid)

        if is_valid:
            self.orcid_info.setStyleSheet("color: green; font-size: 10px;")
            self.orcid_info.setText(tr("user_metadata.personal.orcid_valid"))
        else:
            self.orcid_info.setStyleSheet("color: red; font-size: 10px;")
            self.orcid_info.setText(tr("user_metadata.personal.orcid_invalid"))

    def save_and_close(self):
        """Speichert Daten und schließt den Dialog."""
        # Validierung: Name und Institution sind Pflicht
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                tr("user_metadata.dialogs.missing_name_title"),
                tr("user_metadata.dialogs.missing_name_message")
            )
            self.name_input.setFocus()
            return

        if not self.institution_input.text().strip():
            QMessageBox.warning(
                self,
                tr("user_metadata.dialogs.missing_institution_title"),
                tr("user_metadata.dialogs.missing_institution_message")
            )
            self.institution_input.setFocus()
            return

        # ORCID validieren (falls angegeben)
        orcid = self.orcid_input.text().strip()
        if orcid and not self.metadata_manager.validate_orcid(orcid):
            result = QMessageBox.question(
                self,
                tr("user_metadata.dialogs.invalid_orcid_title"),
                tr("user_metadata.dialogs.invalid_orcid_message"),
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.No:
                self.orcid_input.setFocus()
                return

        # Daten in Manager übertragen
        meta = self.metadata_manager.metadata

        meta['user']['name'] = self.name_input.text().strip()
        meta['user']['email'] = self.email_input.text().strip()
        meta['user']['orcid'] = self.orcid_input.text().strip()

        meta['affiliation']['institution'] = self.institution_input.text().strip()
        meta['affiliation']['department'] = self.department_input.text().strip()
        meta['affiliation']['ror'] = self.ror_input.text().strip()

        meta['export_defaults']['license'] = self.license_combo.currentText()
        meta['export_defaults']['auto_timestamp'] = self.timestamp_check.isChecked()
        meta['export_defaults']['include_provenance'] = self.provenance_check.isChecked()
        meta['export_defaults']['generate_uuid'] = self.uuid_check.isChecked()

        # Speichern
        try:
            self.metadata_manager.save()
            QMessageBox.information(
                self,
                tr("user_metadata.dialogs.saved_title"),
                tr("user_metadata.dialogs.saved_message", path=str(self.metadata_manager.current_file))
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("user_metadata.dialogs.error_title"),
                tr("user_metadata.dialogs.error_message", error=str(e))
            )

    def change_save_location(self):
        """Ändert den Speicherort der Config."""
        from PySide6.QtWidgets import QFileDialog

        # Default-Pfad
        if self.metadata_manager.current_file:
            default_path = str(self.metadata_manager.current_file)
        else:
            default_path = str(Path.home() / ".scatterforge" / "user_metadata.json")

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            tr("user_metadata.dialogs.change_location_title"),
            default_path,
            tr("user_metadata.dialogs.json_filter")
        )

        if filepath:
            self.metadata_manager.current_file = Path(filepath)
            self.update_path_label()
