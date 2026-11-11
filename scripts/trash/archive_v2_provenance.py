#!/usr/bin/env python3
"""V2i immutable snapshot receipt codec and unkeyed provenance checks.

These SHA-256 digests detect accidental/unsanctioned metadata changes but are
NOT digital signatures, proof of source authorization, or protection from an
attacker able to rewrite the same SQLite database.
"""
import hashlib
import hmac
import json
import re

RECEIPT_SCHEMA = "post-apollo.trash-archive.receipt.v2i"
IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
HEX_ID = re.compile(r"^[0-9a-f]{32}$")
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_OWNERS = frozenset(("demo-scrape", "weather-events"))
MAX_MS = 9999999999999


class ProvenanceError(Exception):
    """Safe stable error code, no private paths or payload content."""


def _require(ok):
    if not ok:
        raise ProvenanceError("SNAPSHOT_PROVENANCE_INVALID")


FIELDS = ("snapshotId", "ownerId", "resourceId", "sourceRevision",
          "sourceCapturedAtMs", "archivedAtMs", "displayLabel",
          "payloadSha256", "previousReceiptHash")


def _fields(snapshot_id, owner, resource_id, revision, source_ms,
            archived_ms, label, digest, previous):
    _require(type(snapshot_id) is str and HEX_ID.fullmatch(snapshot_id)
             and type(owner) is str and owner in ALLOWED_OWNERS
             and type(resource_id) is str and IDENTIFIER.fullmatch(resource_id)
             and type(revision) is str and IDENTIFIER.fullmatch(revision)
             and type(source_ms) is int and 1 <= source_ms <= MAX_MS
             and type(archived_ms) is int and 1 <= archived_ms <= MAX_MS
             and type(label) is str and len(label) <= 120
             and all(c.isprintable() for c in label)
             and type(digest) is str and HEX_SHA.fullmatch(digest)
             and type(previous) is str and
             (previous == "" or HEX_SHA.fullmatch(previous)))
    return dict(zip(FIELDS, (snapshot_id, owner, resource_id, revision,
                             source_ms, archived_ms, label, digest, previous)))


def create_receipt(snapshot_id, owner, resource_id, revision, source_ms,
                   archived_ms, label, digest, previous=""):
    values = _fields(snapshot_id, owner, resource_id, revision, source_ms,
                     archived_ms, label, digest, previous)
    envelope = {"schema": RECEIPT_SCHEMA, **values}
    canonical = json.dumps(envelope, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False)
    envelope["receiptSha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return envelope


def verify_receipt(snapshot_fields, receipt_fields, *, required=False):
    """Check metadata binding using a single consistent SQLite read snapshot.

    snapshot_fields: (id,owner,resource,revision,captured_ms,label,digest,flag).
    receipt_fields: 11-tuple (snapshot_id,owner,resource,revision,
      source_ms,archive_ms,label,digest,previous,hash,schema) or all NULL.
    """
    _require(type(required) is bool
             and isinstance(snapshot_fields, (tuple, list))
             and len(snapshot_fields) == 8
             and snapshot_fields[7] in (0, 1)
             and isinstance(receipt_fields, (tuple, list))
             and len(receipt_fields) == 11)
    if snapshot_fields[7] == 0:
        _require(not required and all(x is None for x in receipt_fields))
        return {"state": "LEGACY_UNATTESTED"}
    _require(all(x is not None for x in receipt_fields))
    (sid, owner, rid, rev, source_ms, stored_ms,
     label, digest, previous, stored_hash, schema) = receipt_fields
    _require(schema == RECEIPT_SCHEMA
             and type(stored_hash) is str and HEX_SHA.fullmatch(stored_hash)
             and (sid, owner, rid, rev, source_ms, label, digest)
             == tuple(snapshot_fields[:7]))
    actual = create_receipt(sid, owner, rid, rev, source_ms, stored_ms,
                            label, digest, previous)
    _require(hmac.compare_digest(actual["receiptSha256"], stored_hash))
    return {"state": "RECEIPT_MATCHED",
            "receiptSha256": stored_hash,
            "previousReceiptHash": previous,
            "sourceCapturedAtMs": source_ms,
            "archivedAtMs": stored_ms,
            "payloadSha256": digest,
            "authentication": "UNSIGNED_LOCAL"}
