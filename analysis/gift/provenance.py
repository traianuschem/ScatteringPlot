"""
Provenance-Record (JSON-Sidecar) für GIFT/IFT-Analysen.

Portiert und verallgemeinert aus JADE-DLS (`ade_dls/gui/core/provenance.py`, gleicher
Autor, GPL-3.0). Die Feldstruktur ist identisch, damit dieselben Werkzeuge beide
Sidecars lesen können; Software-Name und Schema-URI sind Parameter.

Schema: agent → input entities (SHA-256) → processing activities (DAG über `used`)
→ output catalog (SHA-256, wasGeneratedBy, wasDerivedFrom). Zusätzlich gegenüber
JADE: `flags` (Plausibilitätsprüfungen) und `reproducibility` (Seeds, Worker).
Jede Ergebnisdatei trägt die UUID4-`record_id` in ihrem Header.

Grundsatz: Provenance darf nie einen erfolgreichen Export verhindern — Fehler beim
Hashen führen zu leeren Hash-Feldern, nicht zu Ausnahmen.
"""

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

GIFT_SCHEMA_URI = "https://scatterforge.org/schema/gift-provenance/v1.0"
GIFT_NAMESPACE = "https://scatterforge.org/ns/gift-provenance#"


def _now():
    return datetime.now(timezone.utc).isoformat()


def compute_sha256(filepath) -> str:
    """SHA-256 einer Datei als Hex-String, oder '' bei I/O-Fehlern."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError):
        return ""


def json_safe(value):
    """Wandelt numpy-Typen/Arrays und Pfade rekursiv in JSON-serialisierbare Werte."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, 'tolist'):          # numpy-Array oder -Skalar
        return json_safe(value.tolist())
    if isinstance(value, float) and (value != value or value in (float('inf'), float('-inf'))):
        return None                        # NaN/Inf sind kein gültiges JSON
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _git_commit(repo_dir) -> Optional[str]:
    try:
        out = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(repo_dir),
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            commit = out.stdout.strip()
            dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=str(repo_dir),
                                   capture_output=True, text=True, timeout=5)
            if dirty.returncode == 0 and dirty.stdout.strip():
                commit += '-dirty'
            return commit
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def default_agent(software: str, version: str, module_version: str,
                  repo_dir=None) -> Dict[str, Any]:
    """Agent-Beschreibung inkl. der für die Numerik relevanten Bibliotheksversionen."""
    import numpy
    import scipy
    agent = {
        "software": software,
        "version": version,
        "module": "analysis.gift",
        "module_version": module_version,
        "platform": platform.platform(),
        "python_version": (f"{sys.version_info.major}.{sys.version_info.minor}"
                           f".{sys.version_info.micro}"),
        "numpy_version": numpy.__version__,
        "scipy_version": scipy.__version__,
    }
    if repo_dir is not None:
        agent["git_commit"] = _git_commit(repo_dir)
    return agent


class ProvenanceRecord:
    """Provenance-Record einer GIFT/IFT-Analyse (PROV-DM-artig)."""

    def __init__(self, agent: Dict[str, Any], schema_uri: str = GIFT_SCHEMA_URI,
                 namespace: str = GIFT_NAMESPACE, prefix: str = "gift"):
        self.record_id: str = str(uuid.uuid4())
        self.created: str = _now()
        self.schema_uri = schema_uri
        self.namespace = namespace
        self.prefix = prefix
        self.agent: Dict[str, Any] = dict(agent)
        self._input_folder: Optional[str] = None
        self._input_entities: List[Dict[str, Any]] = []
        self._excluded_files: List[str] = []
        self._activities: List[Dict[str, Any]] = []
        self._outputs: List[Dict[str, Any]] = []
        self.flags: List[Dict[str, Any]] = []
        self.reproducibility: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Eingänge
    # ------------------------------------------------------------------

    def set_input_folder(self, folder) -> None:
        self._input_folder = str(folder)

    def add_input_entity(self, filepath, metadata: Optional[Dict[str, Any]] = None,
                         role: str = "raw_data") -> str:
        """Registriert eine Eingangsdatei mit SHA-256-Fingerabdruck. Gibt die Entity-ID zurück."""
        p = Path(filepath)
        sha = compute_sha256(filepath)
        entity: Dict[str, Any] = {
            "id": f"sha256:{sha}" if sha else f"file:{p.name}",
            "filename": p.name,
            "path": str(p.resolve()) if p.exists() else str(filepath),
            "sha256": sha,
            "role": role,
        }
        if metadata:
            entity["metadata"] = json_safe(metadata)
        self._input_entities.append(entity)
        return entity["id"]

    def mark_file_excluded(self, filename: str) -> None:
        if filename not in self._excluded_files:
            self._excluded_files.append(filename)

    # ------------------------------------------------------------------
    # Aktivitäten
    # ------------------------------------------------------------------

    def add_activity(self, label: str, activity_type: str,
                     parameters: Optional[Dict[str, Any]] = None,
                     results_summary: Optional[Dict[str, Any]] = None,
                     used: Optional[List[str]] = None) -> str:
        """Hängt eine Aktivität an. Ohne `used` wird sie an die vorherige gekettet."""
        n = len(self._activities)
        act_id = f"act-{n + 1:03d}"
        if used is None:
            used = [f"act-{n:03d}"] if n > 0 else []
        activity: Dict[str, Any] = {
            "id": act_id,
            "label": label,
            "type": activity_type,
            "timestamp": _now(),
            "parameters": json_safe(parameters or {}),
            "used": list(used),
        }
        if results_summary is not None:
            activity["results_summary"] = json_safe(results_summary)
        self._activities.append(activity)
        return act_id

    def annotate_last_activity(self, results_summary: Dict[str, Any]) -> None:
        if self._activities:
            self._activities[-1]["results_summary"] = json_safe(results_summary)

    def activity(self, act_id: str) -> Optional[Dict[str, Any]]:
        return next((a for a in self._activities if a["id"] == act_id), None)

    # ------------------------------------------------------------------
    # Flags und Reproduzierbarkeit
    # ------------------------------------------------------------------

    def set_flags(self, flags) -> None:
        self.flags = [json_safe(f.to_dict() if hasattr(f, 'to_dict') else f) for f in flags]

    def set_reproducibility(self, **info) -> None:
        self.reproducibility.update(json_safe(info))

    # ------------------------------------------------------------------
    # Output-Katalog
    # ------------------------------------------------------------------

    def add_output(self, output_type: str, label: str, filepath=None,
                   extra_fields: Optional[Dict[str, Any]] = None) -> str:
        """Registriert ein Artefakt (mit SHA-256, falls eine Datei angegeben ist)."""
        n = len(self._outputs)
        out_id = f"out-{n + 1:03d}"
        entry: Dict[str, Any] = {
            "id": out_id,
            "type": output_type,
            "label": label,
            "record_id": self.record_id,
            "wasGeneratedBy": self._activities[-1]["id"] if self._activities else None,
            "wasDerivedFrom": [e["id"] for e in self._input_entities],
            "timestamp": _now(),
        }
        if filepath:
            p = Path(filepath)
            entry["path"] = str(p.resolve())
            sha = compute_sha256(filepath)
            if sha:
                entry["sha256"] = sha
        if extra_fields:
            entry.update(json_safe(extra_fields))
        self._outputs.append(entry)
        return out_id

    def verify_outputs(self) -> List[Dict[str, Any]]:
        """Prüft die SHA-256 aller Katalogdateien gegen die Dateien auf der Platte.

        Returns:
            Liste mit {id, label, path, status}, status ∈ {'ok', 'modified', 'missing',
            'no_hash'}.
        """
        report = []
        for out in self._outputs:
            path = out.get("path")
            expected = out.get("sha256")
            if not path:
                continue
            if not expected:
                status = "no_hash"
            elif not Path(path).exists():
                status = "missing"
            else:
                status = "ok" if compute_sha256(path) == expected else "modified"
            report.append({"id": out["id"], "label": out.get("label"), "path": path,
                           "status": status})
        return report

    def verify_inputs(self) -> List[Dict[str, Any]]:
        """Prüft, ob die Eingangsdateien unverändert sind (für „Aus Sidecar wiederholen“)."""
        report = []
        for ent in self._input_entities:
            path = ent.get("path")
            expected = ent.get("sha256")
            if not path or not Path(path).exists():
                status = "missing"
            elif not expected:
                status = "no_hash"
            else:
                status = "ok" if compute_sha256(path) == expected else "modified"
            report.append({"id": ent["id"], "filename": ent.get("filename"), "path": path,
                           "status": status})
        return report

    # ------------------------------------------------------------------
    # Serialisierung
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "$schema": self.schema_uri,
            "record_id": self.record_id,
            "created": self.created,
            "agent": self.agent,
            "input": {
                "data_folder": self._input_folder,
                "entities": self._input_entities,
                "excluded_files": self._excluded_files,
            },
            "processing": {
                "activities": self._activities,
            },
            "flags": self.flags,
            "reproducibility": self.reproducibility,
            "output": {
                "catalog": self._outputs,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceRecord":
        rec = cls(agent=data.get("agent", {}), schema_uri=data.get("$schema", GIFT_SCHEMA_URI))
        rec.record_id = data.get("record_id", rec.record_id)
        rec.created = data.get("created", rec.created)
        inp = data.get("input", {})
        rec._input_folder = inp.get("data_folder")
        rec._input_entities = list(inp.get("entities", []))
        rec._excluded_files = list(inp.get("excluded_files", []))
        rec._activities = list(data.get("processing", {}).get("activities", []))
        rec.flags = list(data.get("flags", []))
        rec.reproducibility = dict(data.get("reproducibility", {}))
        rec._outputs = list(data.get("output", {}).get("catalog", []))
        return rec

    @classmethod
    def load(cls, filepath) -> "ProvenanceRecord":
        return cls.from_dict(json.loads(Path(filepath).read_text(encoding="utf-8")))

    def export_to_file(self, filepath) -> None:
        """Schreibt den Sidecar. Der Sidecar selbst wird nicht in seinen eigenen Katalog
        aufgenommen (sein Hash würde sich dadurch ändern)."""
        Path(filepath).write_text(self.to_json(), encoding="utf-8")

    def to_prov_json(self, indent: int = 2) -> str:
        """Serialisierung als W3C PROV-JSON (https://www.w3.org/TR/prov-json/)."""
        pfx = self.prefix

        def ns(local: str) -> str:
            return f"{pfx}:{local}"

        def xsd_datetime(iso: str) -> dict:
            return {"$": iso, "type": "xsd:dateTime"}

        doc: Dict[str, Any] = {
            "prefix": {
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "prov": "http://www.w3.org/ns/prov#",
                pfx: self.namespace,
            }
        }

        agent_id = ns("agent-software")
        doc["agent"] = {agent_id: {"prov:type": {"$": "prov:SoftwareAgent", "type": "xsd:QName"}}}
        for k, v in self.agent.items():
            doc["agent"][agent_id][ns(k)] = "" if v is None else v

        doc["entity"] = {}
        for ent in self._input_entities:
            eid = ns(ent["id"].replace(":", "_"))
            doc["entity"][eid] = {
                "prov:type": {"$": ns("RawDataFile"), "type": "xsd:QName"},
                ns("filename"): ent.get("filename", ""),
                ns("path"): ent.get("path", ""),
                ns("sha256"): ent.get("sha256", ""),
                ns("role"): ent.get("role", "raw_data"),
            }
            if "metadata" in ent:
                doc["entity"][eid][ns("metadata")] = json.dumps(ent["metadata"], ensure_ascii=False)

        for out in self._outputs:
            oid = ns(out["id"])
            doc["entity"][oid] = {
                "prov:type": {"$": ns("ExportedArtifact"), "type": "xsd:QName"},
                ns("outputType"): out.get("type", ""),
                ns("label"): out.get("label", ""),
                ns("recordId"): out.get("record_id", self.record_id),
            }
            for key in ("sha256", "path"):
                if key in out:
                    doc["entity"][oid][ns(key)] = out[key]

        doc["activity"] = {}
        for act in self._activities:
            aid = ns(act["id"])
            doc["activity"][aid] = {
                "prov:startedAtTime": xsd_datetime(act.get("timestamp", _now())),
                "prov:type": {"$": ns(act.get("type", "analysis")), "type": "xsd:QName"},
                ns("label"): act.get("label", ""),
                ns("parameters"): json.dumps(act.get("parameters", {}), ensure_ascii=False),
            }
            if "results_summary" in act:
                doc["activity"][aid][ns("resultsSummary")] = json.dumps(
                    act["results_summary"], ensure_ascii=False)

        doc["wasInformedBy"] = {}
        for act in self._activities:
            for prev_id in act.get("used", []):
                if prev_id:
                    bn = f"_:wib_{act['id']}_{prev_id}".replace("-", "_")
                    doc["wasInformedBy"][bn] = {"prov:informed": ns(act["id"]),
                                                "prov:informant": ns(prev_id)}

        doc["wasAssociatedWith"] = {}
        for i, act in enumerate(self._activities):
            doc["wasAssociatedWith"][f"_:waw_{i + 1:03d}"] = {
                "prov:activity": ns(act["id"]), "prov:agent": agent_id}

        doc["used"] = {}
        first = self._activities[0]["id"] if self._activities else None
        if first:
            for ent in self._input_entities:
                bn = f"_:u_{first}_{ent['id']}".replace(":", "_").replace("-", "_")
                doc["used"][bn] = {"prov:activity": ns(first),
                                   "prov:entity": ns(ent["id"].replace(":", "_"))}

        doc["wasGeneratedBy"] = {}
        doc["wasDerivedFrom"] = {}
        for out in self._outputs:
            gen_act = out.get("wasGeneratedBy")
            if gen_act:
                bn = f"_:wgb_{out['id']}".replace("-", "_")
                doc["wasGeneratedBy"][bn] = {"prov:entity": ns(out["id"]),
                                             "prov:activity": ns(gen_act),
                                             "prov:time": xsd_datetime(out.get("timestamp", _now()))}
            for src_id in out.get("wasDerivedFrom", []):
                bn = f"_:wdf_{out['id']}_{src_id}".replace(":", "_").replace("-", "_")
                doc["wasDerivedFrom"][bn] = {"prov:generatedEntity": ns(out["id"]),
                                             "prov:usedEntity": ns(src_id.replace(":", "_"))}

        doc[ns("sessionMetadata")] = {
            ns("recordId"): self.record_id,
            ns("created"): self.created,
            ns("dataFolder"): self._input_folder or "",
            ns("flags"): json.dumps(self.flags, ensure_ascii=False),
            ns("reproducibility"): json.dumps(self.reproducibility, ensure_ascii=False),
        }
        return json.dumps(doc, indent=indent, ensure_ascii=False)

    def export_prov_json_to_file(self, filepath) -> None:
        Path(filepath).write_text(self.to_prov_json(), encoding="utf-8")
