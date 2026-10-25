"""MACHINE M2c2: pure gate for documentation-only integration evidence.

Documented vendor APIs do not establish live adapter installation,
authorizations, restart-stable identities or historical restore coverage.
No IO, networking, process invocation, imports of adapters or live actions.
"""
from __future__ import annotations
from collections import Counter

MAX_ENTRIES = 64
ALLOWED_EVIDENCE = frozenset((
    "documented_interface", "runtime_interface_unverified", "repo_source_verified"))
ALLOWED_FAMILIES = frozenset((
    "browser", "terminal", "editor", "generic", "existing_repo", "office", "media", "other"))


class AuditError(ValueError):
    pass


def _string(value, *, maximum=256):
    if (not isinstance(value, str) or not 1 <= len(value) <= maximum
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        raise AuditError("INVALID EVIDENCE FIELD")
    return value


def _strings(values, *, maximum=32):
    if not isinstance(values, list) or not 1 <= len(values) <= maximum:
        raise AuditError("INVALID EVIDENCE COLLECTION")
    items = [_string(v) for v in values]
    if len(set(items)) != len(items):
        raise AuditError("DUPLICATE EVIDENCE ITEM")
    return items


def _source(value):
    if value is None:
        return None
    value = _string(value, maximum=320)
    if not (value.startswith("https://") or
            value.startswith(("services/time/", "integrations/proton/"))):
        raise AuditError("UNTRUSTED SOURCE REFERENCE")
    return value


def validate_audit(value):
    if not isinstance(value, dict) or set(value) != {
            "schema_version", "kind", "audited_utc",
            "status", "runtime_implementation_count", "entries"}:
        raise AuditError("INVALID AUDIT RECORD")
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["kind"] != "machine-app-capability-evidence-audit"
            or value["status"] != "documentation_only"
            or type(value["runtime_implementation_count"]) is not int
            or value["runtime_implementation_count"] != 0):
        raise AuditError("UNVERIFIED RUNTIME CLAIM")
    date = _string(value["audited_utc"], maximum=10)
    if len(date) != 10 or date[4] != "-" or date[7] != "-" or not (
            date[:4]+date[5:7]+date[8:]).isdigit():
        raise AuditError("INVALID AUDIT DATE")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise AuditError("INVALID AUDIT ENTRIES")
    cleaned = []
    subjects = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
                "family", "subject", "applies_to", "evidence",
                "capability", "constraints", "official_source",
                "secondary_source", "runtime_verified",
                "arbitrary_checkpoint_reconstruction_verified",
                "live_enabled"}:
            raise AuditError("UNEXPECTED AUDIT FIELD")
        family = _string(entry["family"])
        subject = _string(entry["subject"])
        evidence = _string(entry["evidence"])
        if family not in ALLOWED_FAMILIES or evidence not in ALLOWED_EVIDENCE:
            raise AuditError("UNRECOGNIZED EVIDENCE CATEGORY")
        if subject in subjects:
            raise AuditError("DUPLICATE EVIDENCE SUBJECT")
        subjects.add(subject)
        # Documentation must never be promoted to verified live behavior.
        if (entry["runtime_verified"] is not False
                or entry["arbitrary_checkpoint_reconstruction_verified"] is not False
                or entry["live_enabled"] is not False):
            raise AuditError("UNVERIFIED LIVE CAPABILITY CLAIM")
        targets = _strings(entry["applies_to"])
        limits = _strings(entry["constraints"])
        capability = _string(entry["capability"])
        source = _source(entry["official_source"])
        secondary = _source(entry["secondary_source"])
        if source is None:
            raise AuditError("SOURCE REQUIRED")
        cleaned.append({
            "family": family, "subject": subject, "applies_to": targets,
            "evidence": evidence, "capability": capability,
            "constraints": limits, "official_source": source,
            "secondary_source": secondary, "runtime_verified": False,
            "arbitrary_checkpoint_reconstruction_verified": False,
            "live_enabled": False,
        })
    return {
        "schema_version": 1, "kind": "machine-app-capability-evidence-audit",
        "audited_utc": date, "status": "documentation_only",
        "runtime_implementation_count": 0, "entries": cleaned,
    }


def summarize_audit(document):
    valid = validate_audit(document)
    categories = Counter(e["family"] for e in valid["entries"])
    evidence = Counter(e["evidence"] for e in valid["entries"])
    return {
        "kind": "machine-adapter-documentation-audit-summary",
        "read_only": True, "executable": False,
        "audited_utc": valid["audited_utc"],
        "entry_count": len(valid["entries"]),
        "family_counts": dict(sorted(categories.items())),
        "evidence_counts": dict(sorted(evidence.items())),
        "live_implementations_verified": 0,
        "recovery_actions_available": [],
        "privacy_consent_granted": False,
        "next_gate": "isolated_adapter_interface_and_permission_review",
    }
