#!/usr/bin/env python3
"""V2j read-only, database-wide unsigned provenance-chain audit.

This audits only metadata and receipt links. It does NOT read payload bytes,
authenticate owner identities, sign receipts, alter SQLite or grant Restore /
Burn authority. Never report a partial scan as successful.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

# Python -I omits this script's directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.trash.archive_v2_index import (
    DB_NAME, STORE_SCHEMA, ReadIndexError, _dir, _private_regular,
)
from scripts.trash.archive_v2_location import ArchiveRootError, archive_directory
from scripts.trash.archive_v2_provenance import ProvenanceError, verify_receipt

MAX_RECORDS = 100000


class ChainAuditError(Exception):
    """Stable refusal code, never payload or private user source contents."""


def _require(ok, code):
    if not ok:
        raise ChainAuditError(code)


def _empty(state):
    return {"ok": True, "kind": "archive-v2-chain-audit",
            "readOnly": True, "state": state,
            "snapshotCount": 0, "receiptCount": 0, "legacyCount": 0,
            "sourceCount": 0, "payloadVerified": False,
            "authentication": "UNSIGNED_LOCAL",
            "completeness": "DATABASE_LOCAL_ONLY"}


def audit(directory):
    """Read a single consistent SQLite snapshot, fail closed on any bad link."""
    try:
        root = archive_directory(directory, create=False)
    except ArchiveRootError as exc:
        raise ChainAuditError(str(exc)) from exc
    if root is None:
        return _empty("NOT_INSTALLED")
    try:
        root = _dir(str(root))
        database = root / DB_NAME
        if not _private_regular(database):
            return _empty("NOT_INSTALLED")
        for suffix in ("-wal", "-shm"):
            try:
                (root / (DB_NAME + suffix)).lstat()
            except FileNotFoundError:
                continue
            raise ChainAuditError("ARCHIVE_UNEXPECTED_SIDECAR")
        _private_regular(root / (DB_NAME + "-journal"),
                         require_private_mode=False)
    except ReadIndexError as exc:
        raise ChainAuditError(str(exc)) from exc

    uri = "file:" + quote(str(database), safe="/") + "?mode=ro&cache=private"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA busy_timeout=1000")
            db.execute("BEGIN")
            meta = db.execute(
                "SELECT schema_id FROM archive_meta WHERE id=1"
            ).fetchone()
            _require(meta == (STORE_SCHEMA,), "ARCHIVE_SCHEMA_UNSUPPORTED")
            columns = {r[1] for r in db.execute("PRAGMA table_info(snapshots)")}
            flag = "provenance_required" in columns
            receipts = db.execute("""SELECT 1 FROM sqlite_master
                WHERE type='table' AND name='snapshot_receipts'""").fetchone() is not None
            _require(flag == receipts, "ARCHIVE_PROVENANCE_SCHEMA_INVALID")

            count = db.execute("SELECT count(*) FROM snapshots").fetchone()[0]
            _require(type(count) is int and count <= MAX_RECORDS,
                     "ARCHIVE_AUDIT_LIMIT")
            if receipts:
                orphan = db.execute("""SELECT count(*)
                    FROM snapshot_receipts r LEFT JOIN snapshots s
                        ON s.id=r.snapshot_id
                    WHERE s.id IS NULL""").fetchone()[0]
                _require(orphan == 0, "ARCHIVE_ORPHAN_RECEIPT")

            cols = (
                ",s.provenance_required,r.snapshot_id,r.owner_id,r.resource_id,"
                "r.source_revision,r.source_captured_ms,r.archived_ms,"
                "r.display_label,r.payload_sha256,r.previous_receipt_sha256,"
                "r.receipt_sha256,r.receipt_schema"
                if flag else ",0," + ",".join(["NULL"] * 11)
            )
            join = (" FROM snapshots s LEFT JOIN snapshot_receipts r"
                    " ON r.snapshot_id=s.id" if receipts
                    else " FROM snapshots s")
            query = (
                "SELECT s.rowid,s.id,s.owner_id,s.resource_id,s.source_revision,"
                "s.captured_ms,s.display_label,s.sha256"
                + cols + join + " ORDER BY s.rowid ASC"
            )

            sources = {}     # (owner,resource) -> last validated receipt digest
            source_keys = set()
            sealed = set()   # source groups with at least one V2i receipt
            seen_hashes = set()
            scanned = receipt_count = legacy_count = 0
            for row in db.execute(query):
                # row[0] is SQLite insertion order; row[1:9] is snapshot
                # metadata, row[9:] the exact 11-field receipt tuple.
                scanned += 1
                _require(scanned <= MAX_RECORDS, "ARCHIVE_AUDIT_LIMIT")
                try:
                    evidence = verify_receipt(row[1:9], row[9:])
                except ProvenanceError as exc:
                    raise ChainAuditError(str(exc)) from exc
                key = (row[2], row[3])
                source_keys.add(key)
                if evidence["state"] == "LEGACY_UNATTESTED":
                    # Legitimate migrated V2a rows occur before V2i receipt
                    # insertion. An unsigned row *after* signed local history
                    # is a break in this database's recorded sequence.
                    _require(key not in sealed, "ARCHIVE_CHAIN_GAP")
                    legacy_count += 1
                else:
                    sealed.add(key)
                    receipt_count += 1
                    actual = evidence["receiptSha256"]
                    _require(actual not in seen_hashes, "ARCHIVE_CHAIN_DUPLICATE")
                    seen_hashes.add(actual)
                    expected_previous = sources.get(key, "")
                    _require(evidence["previousReceiptHash"] == expected_previous,
                             "ARCHIVE_CHAIN_LINK_INVALID")
                    sources[key] = actual

            _require(scanned == count, "ARCHIVE_AUDIT_INCOMPLETE")
            if receipts:
                total_receipts = db.execute(
                    "SELECT count(*) FROM snapshot_receipts").fetchone()[0]
                _require(receipt_count == total_receipts,
                         "ARCHIVE_AUDIT_INCOMPLETE")
            return {"ok": True, "kind": "archive-v2-chain-audit",
                    "readOnly": True,
                    "state": ("CHAIN_CONSISTENT" if receipt_count
                              else "LEGACY_ONLY"),
                    "snapshotCount": scanned,
                    "receiptCount": receipt_count,
                    "legacyCount": legacy_count,
                    "sourceCount": len(source_keys),
                    "payloadVerified": False,
                    "authentication": "UNSIGNED_LOCAL",
                    "completeness": "DATABASE_LOCAL_ONLY"}
    except sqlite3.Error as exc:
        raise ChainAuditError("ARCHIVE_AUDIT_UNAVAILABLE") from exc


def main(argv):
    try:
        if len(argv) != 3 or argv[1] != "audit":
            raise ChainAuditError("READ_ONLY_AUDIT_ONLY")
        report = audit(argv[2])
    except ChainAuditError as exc:
        report = {"ok": False, "error": str(exc)}
    except Exception:
        report = {"ok": False, "error": "ARCHIVE_AUDIT_FAILED"}
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
