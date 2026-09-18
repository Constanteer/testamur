from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


AUTHORITY_SCHEMA_VERSION = "testamur.authority.v1"


class AuthoritySubjectKind(StrEnum):
    PRINCIPAL = "PRINCIPAL"
    USER = "USER"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"
    WORKLOAD = "WORKLOAD"
    PROCESS = "PROCESS"
    SESSION = "SESSION"
    AGENT = "AGENT"
    CONNECTOR = "CONNECTOR"
    CREDENTIAL = "CREDENTIAL"
    TOKEN = "TOKEN"
    SECRET = "SECRET"
    SERVICE = "SERVICE"
    RESOURCE = "RESOURCE"
    REPOSITORY = "REPOSITORY"
    DATASET = "DATASET"
    QUEUE = "QUEUE"
    NETWORK_ENDPOINT = "NETWORK_ENDPOINT"
    HOST = "HOST"
    CONTAINER = "CONTAINER"
    BOUNDARY = "BOUNDARY"
    OTHER = "OTHER"


class AuthorityRelationType(StrEnum):
    CAN_READ = "CAN_READ"
    CAN_WRITE = "CAN_WRITE"
    CAN_EXECUTE = "CAN_EXECUTE"
    CAN_CONNECT = "CAN_CONNECT"
    CAN_IMPERSONATE = "CAN_IMPERSONATE"
    CAN_AUTHENTICATE_AS = "CAN_AUTHENTICATE_AS"
    ACCEPTS_CREDENTIAL = "ACCEPTS_CREDENTIAL"
    ISSUES_CREDENTIAL = "ISSUES_CREDENTIAL"
    DELEGATES = "DELEGATES"
    GRANTS = "GRANTS"
    HAS_CAPABILITY = "HAS_CAPABILITY"
    BOUND_TO = "BOUND_TO"
    EXPOSES = "EXPOSES"


class AuthorityEvidenceClass(StrEnum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    DECLARED = "DECLARED"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _required(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    return text


def _optional_string(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    return _required(value, field=field)


def _mapping(value: Mapping[str, Any] | None, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    result = dict(value)
    json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return result


def _normalize_subject_kind(value: str | AuthoritySubjectKind) -> str:
    try:
        return AuthoritySubjectKind(str(value)).value
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AuthoritySubjectKind)
        raise ValueError(
            f"unsupported authority subject kind {value!r}; expected one of: {allowed}"
        ) from exc


def _normalize_relation(value: str | AuthorityRelationType) -> str:
    try:
        return AuthorityRelationType(str(value)).value
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AuthorityRelationType)
        raise ValueError(
            f"unsupported authority relation {value!r}; expected one of: {allowed}"
        ) from exc


def normalize_capability(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("capability must be a mapping")
    item = dict(value)
    namespace = _required(item.get("namespace"), field="capability.namespace")
    action = _required(item.get("action"), field="capability.action")
    resource = _optional_string(item.get("resource"), field="capability.resource")
    constraints = _mapping(item.get("constraints"), field="capability.constraints")
    normalized: dict[str, Any] = {
        "namespace": namespace,
        "action": action,
        "constraints": constraints,
    }
    if resource is not None:
        normalized["resource"] = resource
    metadata = item.get("metadata")
    if metadata is not None:
        normalized["metadata"] = _mapping(metadata, field="capability.metadata")
    return normalized


def normalize_capabilities(
    values: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    result = [normalize_capability(value) for value in values or ()]
    result.sort(
        key=lambda item: (
            str(item.get("namespace") or ""),
            str(item.get("action") or ""),
            str(item.get("resource") or ""),
            json.dumps(
                item.get("constraints") or {},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    )
    return result


def normalize_evidence(
    evidence: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw in evidence or ():
        if not isinstance(raw, Mapping):
            raise ValueError("authority evidence entries must be mappings")
        item = dict(raw)
        item["ref"] = _required(item.get("ref"), field="evidence.ref")
        try:
            evidence_class = AuthorityEvidenceClass(
                str(item.get("evidence_class"))
            ).value
        except ValueError as exc:
            raise ValueError(
                "evidence.evidence_class must be OBSERVED, DERIVED, or DECLARED"
            ) from exc
        item["evidence_class"] = evidence_class
        if evidence_class == AuthorityEvidenceClass.DERIVED.value:
            item["analyzer"] = _required(
                item.get("analyzer"), field="evidence.analyzer"
            )
            item["analyzer_version"] = _required(
                item.get("analyzer_version"), field="evidence.analyzer_version"
            )
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        result.append(item)
    if not result:
        raise ValueError("authority edges require explicit evidence")
    return result


def normalize_boundary_refs(values: Sequence[str] | None) -> list[str]:
    result = sorted({_required(value, field="boundary_refs[]") for value in values or ()})
    return result


class TestamurAuthorityStore:
    """Append-only evidence-bearing authority/capability graph.

    This store deliberately does not reuse material-lineage relation types. Authority
    records answer who/what can exercise which capability and under what constraints.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS testamur_authority_subjects(
          subject_ref TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          label TEXT NOT NULL,
          attributes_json TEXT NOT NULL,
          metadata_json TEXT NOT NULL,
          recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS testamur_authority_subject_kind_idx
          ON testamur_authority_subjects(kind, recorded_at, subject_ref);

        CREATE TABLE IF NOT EXISTS testamur_authority_edges(
          edge_id TEXT PRIMARY KEY,
          relation_type TEXT NOT NULL,
          source_ref TEXT NOT NULL,
          target_ref TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS testamur_authority_source_idx
          ON testamur_authority_edges(source_ref, relation_type, edge_id);
        CREATE INDEX IF NOT EXISTS testamur_authority_target_idx
          ON testamur_authority_edges(target_ref, relation_type, edge_id);
        CREATE INDEX IF NOT EXISTS testamur_authority_relation_idx
          ON testamur_authority_edges(relation_type, edge_id);

        CREATE TRIGGER IF NOT EXISTS testamur_authority_subject_no_update
        BEFORE UPDATE ON testamur_authority_subjects BEGIN
          SELECT RAISE(ABORT, 'Testamur authority subjects are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS testamur_authority_subject_no_delete
        BEFORE DELETE ON testamur_authority_subjects BEGIN
          SELECT RAISE(ABORT, 'Testamur authority subjects are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS testamur_authority_edge_no_update
        BEFORE UPDATE ON testamur_authority_edges BEGIN
          SELECT RAISE(ABORT, 'Testamur authority edges are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS testamur_authority_edge_no_delete
        BEFORE DELETE ON testamur_authority_edges BEGIN
          SELECT RAISE(ABORT, 'Testamur authority edges are immutable');
        END;
        """
        with self.connect() as conn:
            conn.executescript(schema)

    def record_subject(
        self,
        kind: str | AuthoritySubjectKind,
        *,
        label: str,
        subject_ref: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_kind = _normalize_subject_kind(kind)
        normalized_label = _required(label, field="label")
        ref = (
            _required(subject_ref, field="subject_ref")
            if subject_ref is not None
            else f"tst:authority-subject:{uuid.uuid4().hex}"
        )
        attributes_map = _mapping(attributes, field="attributes")
        metadata_map = _mapping(metadata, field="metadata")
        timestamp = recorded_at or _utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO testamur_authority_subjects(
                  subject_ref,kind,label,attributes_json,metadata_json,recorded_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    ref,
                    normalized_kind,
                    normalized_label,
                    json.dumps(
                        attributes_map,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        metadata_map,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    timestamp,
                ),
            )
        return self.get_subject(ref)

    @staticmethod
    def _serialize_subject(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "schema_version": AUTHORITY_SCHEMA_VERSION,
            "subject_ref": str(row["subject_ref"]),
            "kind": str(row["kind"]),
            "label": str(row["label"]),
            "attributes": json.loads(row["attributes_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "recorded_at": str(row["recorded_at"]),
        }

    def get_subject(self, subject_ref: str) -> dict[str, Any]:
        ref = _required(subject_ref, field="subject_ref")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM testamur_authority_subjects WHERE subject_ref=?",
                (ref,),
            ).fetchone()
        if row is None:
            raise KeyError(ref)
        return self._serialize_subject(row)

    def maybe_subject(self, subject_ref: str) -> dict[str, Any] | None:
        ref = _required(subject_ref, field="subject_ref")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM testamur_authority_subjects WHERE subject_ref=?",
                (ref,),
            ).fetchone()
        return None if row is None else self._serialize_subject(row)

    def list_subjects(
        self,
        *,
        kind: str | AuthoritySubjectKind | None = None,
    ) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = ""
        if kind is not None:
            where = " WHERE kind=?"
            params.append(_normalize_subject_kind(kind))
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM testamur_authority_subjects{where} ORDER BY recorded_at,subject_ref",
                params,
            ).fetchall()
        return [self._serialize_subject(row) for row in rows]

    def record_edge(
        self,
        source_ref: str,
        relation_type: str | AuthorityRelationType,
        target_ref: str,
        *,
        capabilities: Iterable[Mapping[str, Any]] | None = None,
        constraints: Mapping[str, Any] | None = None,
        evidence: Iterable[Mapping[str, Any]] | None,
        boundary_refs: Sequence[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
        edge_id: str | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        source = _required(source_ref, field="source_ref")
        target = _required(target_ref, field="target_ref")
        relation = _normalize_relation(relation_type)
        normalized_capabilities = normalize_capabilities(capabilities)
        normalized_constraints = _mapping(constraints, field="constraints")
        normalized_evidence = normalize_evidence(evidence)
        normalized_boundaries = normalize_boundary_refs(boundary_refs)
        normalized_metadata = _mapping(metadata, field="metadata")
        identifier = (
            _required(edge_id, field="edge_id")
            if edge_id is not None
            else f"tst:authority-edge:{uuid.uuid4().hex}"
        )
        timestamp = recorded_at or _utc_now()
        payload = {
            "capabilities": normalized_capabilities,
            "constraints": normalized_constraints,
            "evidence": normalized_evidence,
            "boundary_refs": normalized_boundaries,
            "metadata": normalized_metadata,
        }
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO testamur_authority_edges(
                  edge_id,relation_type,source_ref,target_ref,payload_json,recorded_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    identifier,
                    relation,
                    source,
                    target,
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    timestamp,
                ),
            )
        return self.get_edge(identifier)

    @staticmethod
    def _serialize_edge(row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload_json"])
        return {
            "schema_version": AUTHORITY_SCHEMA_VERSION,
            "edge_id": str(row["edge_id"]),
            "relation_type": str(row["relation_type"]),
            "source_ref": str(row["source_ref"]),
            "target_ref": str(row["target_ref"]),
            "capabilities": list(payload.get("capabilities") or []),
            "constraints": dict(payload.get("constraints") or {}),
            "evidence": list(payload.get("evidence") or []),
            "boundary_refs": list(payload.get("boundary_refs") or []),
            "metadata": dict(payload.get("metadata") or {}),
            "recorded_at": str(row["recorded_at"]),
        }

    def get_edge(self, edge_id: str) -> dict[str, Any]:
        identifier = _required(edge_id, field="edge_id")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM testamur_authority_edges WHERE edge_id=?",
                (identifier,),
            ).fetchone()
        if row is None:
            raise KeyError(identifier)
        return self._serialize_edge(row)

    def list_edges(
        self,
        *,
        source_ref: str | None = None,
        target_ref: str | None = None,
        relation_type: str | AuthorityRelationType | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if source_ref is not None:
            where.append("source_ref=?")
            params.append(_required(source_ref, field="source_ref"))
        if target_ref is not None:
            where.append("target_ref=?")
            params.append(_required(target_ref, field="target_ref"))
        if relation_type is not None:
            where.append("relation_type=?")
            params.append(_normalize_relation(relation_type))
        clause = "" if not where else " WHERE " + " AND ".join(where)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM testamur_authority_edges
                {clause}
                ORDER BY recorded_at,edge_id
                """,
                params,
            ).fetchall()
        return [self._serialize_edge(row) for row in rows]

    def edges_from(self, subject_ref: str) -> list[dict[str, Any]]:
        return self.list_edges(source_ref=subject_ref)

    def edges_to(self, subject_ref: str) -> list[dict[str, Any]]:
        return self.list_edges(target_ref=subject_ref)


__all__ = [
    "AUTHORITY_SCHEMA_VERSION",
    "AuthoritySubjectKind",
    "AuthorityRelationType",
    "AuthorityEvidenceClass",
    "TestamurAuthorityStore",
    "normalize_capability",
    "normalize_capabilities",
    "normalize_evidence",
]
