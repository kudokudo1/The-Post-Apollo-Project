#!/usr/bin/env python3
"""MACHINE // read-only preflight for a FUTURE protected archive migration.

This creates a reproducible, metadata-only inventory of already-encrypted
archive records in the current Unix account's fixed data home. It supports
one later recheck by expected inventory digest, but NEVER copies, opens a
protected target, changes ownership, creates files, or authorizes migration.

The inventory checksum detects accidental source changes, not malicious
same-UID tampering and not AES-GCM plaintext authenticity. No C3e/C5
authentication, protected service identity or live browser access exists.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveOfflineArchiveManager as manager
import MachineBraveOfflineArchive as offline
import MachineBraveSealedVault as vault

PLAN_KIND = "machine-protected-archive-migration-inventory-v1"
REJECTION = {"status": "refused", "restore_allowed": False,
             "migration_authorized": False, "safe_actions": []}
FIELDS = frozenset(("record_id", "created_at_utc", "sealed_bytes", "sha256"))


class PreflightRefusal(ValueError):
    pass


def refuse():
    raise PreflightRefusal("MACHINE MIGRATION PREFLIGHT REFUSED")


def _inventory(base=None):
    """Two read-only passes through existing strict vault reader.

    The caller-facing CLI does not take a base path; CI may inject a
    disposable source base. All reads use the existing owner's vault
    validation and no directory is created.
    """
    with manager._repository(destination=base):
        # Calling vault_root(create=False) is a read-only absence check.
        present = vault.vault_root(create=False) is not None
        first = manager._inventory()
        second = manager._inventory()
    if first != second or not isinstance(first, list) or len(first) > vault.MAX_RECORDS:
        refuse()

    records = []
    seen = set()
    for record in first:
        if type(record) is not dict or frozenset(record) != FIELDS:
            refuse()
        record_id = vault._id(record["record_id"])
        digest = record["sha256"]
        sealed_bytes = record["sealed_bytes"]
        stamp = record["created_at_utc"]
        if (record_id in seen or type(digest) is not str or
                vault.DIGEST_RE.fullmatch(digest) is None or
                type(sealed_bytes) is not int or
                not 1 <= sealed_bytes <= vault.MAX_RECORD or
                type(stamp) is not str or not stamp):
            refuse()
        seen.add(record_id)
        records.append({
            "record_id": record_id, "created_at_utc": stamp,
            "sealed_bytes": sealed_bytes, "sha256": digest
        })
    records.sort(key=lambda entry: entry["record_id"])
    total = sum(entry["sealed_bytes"] for entry in records)
    return {
        "kind": PLAN_KIND,
        "source_state": "present" if present else "absent",
        "record_count": len(records),
        "total_sealed_bytes": total,
        "records": records,
    }


def _fingerprint(inventory):
    raw = json.dumps(inventory, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def plan(*, source_base=None):
    inventory = _inventory(source_base)
    return {
        "status": "offline_migration_inventory_preflight",
        "inventory": inventory,
        "inventory_sha256": _fingerprint(inventory),
        "read_only": True,
        "source_ciphertext_authentication_verified": False,
        "distinct_service_uid_installed": False,
        "protected_destination_inspected": False,
        "independent_backup_verified": False,
        "client_authenticated": False,
        "operator_consent_verified": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def recheck(expected_inventory_sha256, *, source_base=None):
    if (type(expected_inventory_sha256) is not str or
            vault.DIGEST_RE.fullmatch(expected_inventory_sha256) is None):
        refuse()
    current = plan(source_base=source_base)
    if current["inventory_sha256"] != expected_inventory_sha256:
        refuse()
    # An exact match is merely a read-only checkpoint, not a migration
    # approval or proof that same-UID files cannot later change.
    return {
        "status": "offline_migration_inventory_unchanged",
        "inventory_sha256": current["inventory_sha256"],
        "record_count": current["inventory"]["record_count"],
        "source_state": current["inventory"]["source_state"],
        "read_only": True,
        "distinct_service_uid_installed": False,
        "protected_destination_inspected": False,
        "independent_backup_verified": False,
        "client_authenticated": False,
        "operator_consent_verified": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ["plan"]:
            result = plan()
        elif len(args) == 2 and args[0] == "recheck":
            result = recheck(args[1])
        else:
            refuse()
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (PreflightRefusal, manager.ManagerError, offline.ArchiveError,
            vault.VaultError, ValueError, TypeError, KeyError,
            OverflowError, OSError):
        print(json.dumps(REJECTION, sort_keys=True, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    sys.exit(main())
