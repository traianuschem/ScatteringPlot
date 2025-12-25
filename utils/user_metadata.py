"""
User Metadata Management für ScatterForge Plot

Verwaltet Benutzer-Metadaten für wissenschaftliche Publikationen:
- Persönliche Daten (Name, ORCID, E-Mail)
- Affiliation (Institution, Abteilung, ROR-ID)
- Export-Defaults (Lizenz, Zeitstempel, UUID)
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class UserMetadataManager:
    """
    Verwaltet Benutzer-Metadaten für wissenschaftliche Exports.

    Die Metadaten werden standardmäßig in ~/.scatterforge/user_metadata.json
    gespeichert, können aber auch von beliebigen Speicherorten geladen werden
    (z.B. Cloud-Verzeichnisse für Team-Nutzung).
    """

    def __init__(self):
        """Initialisiert den Metadata-Manager und lädt die Default-Config."""
        self.current_file: Optional[Path] = None
        self.metadata: Dict[str, Any] = self.load_default()

    def create_empty_metadata(self) -> Dict[str, Any]:
        """
        Erstellt eine leere Metadaten-Struktur mit Defaults.

        Returns:
            dict: Leere Metadaten-Struktur mit Standardwerten
        """
        return {
            "version": "1.0",
            "user": {
                "name": "",
                "email": "",
                "orcid": ""
            },
            "affiliation": {
                "institution": "",
                "department": "",
                "ror": ""
            },
            "export_defaults": {
                "license": "CC-BY-4.0",
                "auto_timestamp": True,
                "include_provenance": True,
                "generate_uuid": False
            },
            "last_modified": datetime.now(timezone.utc).isoformat()
        }

    def load_default(self) -> Dict[str, Any]:
        """
        Lädt Default-Config aus ~/.scatterforge/user_metadata.json.

        Returns:
            dict: Metadaten-Dictionary
        """
        default_path = Path.home() / ".scatterforge" / "user_metadata.json"

        if default_path.exists():
            try:
                return self.load_from_file(default_path)
            except Exception:
                # Fallback zu leerer Config bei Fehlern
                pass

        return self.create_empty_metadata()

    def load_from_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Lädt Metadaten von einem spezifischen Pfad.

        Args:
            filepath: Pfad zur JSON-Config-Datei

        Returns:
            dict: Metadaten-Dictionary

        Raises:
            FileNotFoundError: Wenn Datei nicht existiert
            json.JSONDecodeError: Wenn JSON ungültig ist
        """
        filepath = Path(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
            self.current_file = filepath

        # Validierung und Migration
        self._validate_and_migrate()

        return self.metadata

    def _validate_and_migrate(self):
        """
        Validiert die geladenen Metadaten und migriert alte Versionen.
        Fügt fehlende Felder mit Defaults hinzu.
        """
        # Sicherstellen, dass alle Keys existieren
        empty = self.create_empty_metadata()

        if "version" not in self.metadata:
            self.metadata["version"] = "1.0"

        if "user" not in self.metadata:
            self.metadata["user"] = empty["user"]
        else:
            for key in empty["user"]:
                if key not in self.metadata["user"]:
                    self.metadata["user"][key] = empty["user"][key]

        if "affiliation" not in self.metadata:
            self.metadata["affiliation"] = empty["affiliation"]
        else:
            for key in empty["affiliation"]:
                if key not in self.metadata["affiliation"]:
                    self.metadata["affiliation"][key] = empty["affiliation"][key]

        if "export_defaults" not in self.metadata:
            self.metadata["export_defaults"] = empty["export_defaults"]
        else:
            for key in empty["export_defaults"]:
                if key not in self.metadata["export_defaults"]:
                    self.metadata["export_defaults"][key] = empty["export_defaults"][key]

    def save(self, filepath: Optional[Path] = None):
        """
        Speichert Metadaten in Datei.

        Args:
            filepath: Optionaler Zielpfad. Falls None, wird current_file verwendet,
                     oder ~/.scatterforge/user_metadata.json als Fallback.

        Raises:
            IOError: Wenn Speichern fehlschlägt
        """
        if filepath is None:
            if self.current_file is not None:
                filepath = self.current_file
            else:
                filepath = Path.home() / ".scatterforge" / "user_metadata.json"

        filepath = Path(filepath)

        # Verzeichnis erstellen, falls nicht vorhanden
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Timestamp aktualisieren
        self.metadata["last_modified"] = datetime.now(timezone.utc).isoformat()

        # Speichern
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

        self.current_file = filepath

    def get_export_metadata(self, plot_title: str = "",
                           subject: str = "",
                           keywords: str = "") -> Dict[str, str]:
        """
        Generiert vollständige Metadaten für den Export.

        Kombiniert User-Metadaten mit plot-spezifischen Informationen
        und automatisch generierten Daten (Timestamp, Provenienz).

        Args:
            plot_title: Titel des Plots
            subject: Beschreibung/Subject
            keywords: Komma-separierte Keywords

        Returns:
            dict: Vollständige Metadaten für Export
        """
        from core.version import get_metadata_provenance

        meta = {
            'Title': plot_title,
            'Author': self.metadata['user']['name'],
            'Subject': subject,
            'Keywords': keywords,
        }

        # ORCID (falls vorhanden)
        if self.metadata['user'].get('orcid'):
            orcid = self.metadata['user']['orcid'].strip()
            # Format: https://orcid.org/0000-0002-1234-5678
            if orcid and not orcid.startswith('http'):
                meta['Creator_ORCID'] = f"https://orcid.org/{orcid}"
            else:
                meta['Creator_ORCID'] = orcid

        # Affiliation
        affiliation_parts = []
        if self.metadata['affiliation'].get('institution'):
            affiliation_parts.append(self.metadata['affiliation']['institution'])
        if self.metadata['affiliation'].get('department'):
            affiliation_parts.append(self.metadata['affiliation']['department'])

        if affiliation_parts:
            meta['Affiliation'] = ", ".join(affiliation_parts)

        # ROR-ID (falls vorhanden)
        if self.metadata['affiliation'].get('ror'):
            meta['Affiliation_ROR'] = self.metadata['affiliation']['ror']

        # E-Mail (falls vorhanden)
        if self.metadata['user'].get('email'):
            meta['Author_Email'] = self.metadata['user']['email']

        # Timestamp (wenn aktiviert)
        if self.metadata['export_defaults']['auto_timestamp']:
            now = datetime.now(timezone.utc)
            meta['CreationDate'] = now.isoformat()
            meta['CreationDate_Unix'] = int(now.timestamp())

        # Software-Provenienz (wenn aktiviert)
        if self.metadata['export_defaults']['include_provenance']:
            prov = get_metadata_provenance()
            meta['Creator_Tool'] = f"{prov['software']} v{prov['version']}"
            meta['Creator_Tool_Version'] = prov['version']
            meta['Python_Version'] = prov['python_version']
            meta['Matplotlib_Version'] = prov['matplotlib_version']

        # Lizenz
        license_name = self.metadata['export_defaults']['license']
        meta['License'] = license_name

        # Lizenz-URL (für bekannte CC-Lizenzen)
        license_urls = {
            'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
            'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
            'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
            'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
        }
        if license_name in license_urls:
            meta['License_URL'] = license_urls[license_name]

        # UUID (wenn aktiviert)
        if self.metadata['export_defaults']['generate_uuid']:
            import uuid
            meta['Image_UUID'] = str(uuid.uuid4())

        return meta

    def validate_orcid(self, orcid: str) -> bool:
        """
        Validiert ORCID-Format (16 Ziffern in 4er-Blöcken mit optionalem X am Ende).

        Args:
            orcid: ORCID-String (z.B. "0000-0002-1234-5678")

        Returns:
            bool: True wenn gültig
        """
        if not orcid:
            return True  # Leer ist okay (optional)

        # Entferne https://orcid.org/ falls vorhanden
        orcid = orcid.replace('https://orcid.org/', '').replace('http://orcid.org/', '')

        # Format: 0000-0002-1234-5678 oder 0000-0002-1234-567X
        parts = orcid.split('-')

        if len(parts) != 4:
            return False

        if len(parts[0]) != 4 or len(parts[1]) != 4 or len(parts[2]) != 4 or len(parts[3]) != 4:
            return False

        # Ersten 3 Blöcke müssen Ziffern sein
        for i in range(3):
            if not parts[i].isdigit():
                return False

        # Letzter Block: Ziffern oder Ziffern+X
        if not (parts[3].isdigit() or (parts[3][:-1].isdigit() and parts[3][-1] in ['X', 'x'])):
            return False

        return True


# Globale Instanz
_user_metadata_manager = None


def get_user_metadata_manager() -> UserMetadataManager:
    """
    Gibt die globale UserMetadataManager-Instanz zurück.

    Returns:
        UserMetadataManager: Globale Instanz
    """
    global _user_metadata_manager
    if _user_metadata_manager is None:
        _user_metadata_manager = UserMetadataManager()
    return _user_metadata_manager
