#!/usr/bin/env python3
"""V2y TEST-ONLY integration rehearsal against actual ArchiveStore schema.

A caller must independently create a private named fixture directory and a
marker file before constructing this adapter. This module has no CLI, owner
key provisioning or production broker integration. It adds an optional
fixture-only signed-admission table to an ArchiveStore initialized inside
that disposable directory, then writes the real snapshots/receipt/meta schema
and the test nonce/evidence in one SQLite BEGIN IMMEDIATE transaction.

A passed synthetic signature is explicitly NOT source owner authorization.
The V2w external file and V2s release ledger remain separate from SQLite.
"""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import stat

from scripts.trash.archive_store_v2 import (
    ArchiveStore, ArchiveError, DB_NAME, MAX_ITEM_BYTES, PILOT_OWNERS,
)
from scripts.trash.archive_v2_capacity import CapacityError
from scripts.trash.archive_v2_provenance import (
    RECEIPT_SCHEMA, ProvenanceError, create_receipt, verify_receipt,
)
from scripts.trash.archive_v2_external_floor_reader import ReadOnlyExternalFloor
from scripts.trash.archive_v2_service_release_history import TestServiceReleaseHistory
from scripts.trash.archive_v2_signed_capture import (
    NONCE, KEY_ID, SHA, RESOURCE, verify_test_proof,
)
from scripts.trash.archive_v2_single_db_fixture import (
    FixtureCommitRefused, _verified_signature,
)

MARKER = "trashpp-v2y-fixture-only.marker"
MARKER_CONTENT = b"post-apollo-trashpp-v2y-TEST-ONLY\n"
MIGRATION_SCHEMA = "post-apollo.trashpp.fixture-admission.v2y"
MAX_MS = 9999999999999
EXPECTED_ADMISSION_COLUMNS = (
    "snapshot_id", "owner_id", "key_id", "nonce", "proof_sha256",
    "signed_receipt_sha256", "external_floor_sha256",
    "signed_claim", "signature_b64",
)


class ArchiveMigrationRefused(Exception):
    """Stable, payload-free refusal, never raw SQLite diagnostics."""


def _require(ok, code):
    if not ok:
        raise ArchiveMigrationRefused(code)


def _fixture_marker(root):
    _require(type(root) is Path and root.is_absolute()
             and root.name.startswith("trashpp-v2y-fixture-")
             and ".." not in root.parts and len(str(root)) < 4096,
             "V2Y_FIXTURE_ROOT_REQUIRED")
    try:
        st = root.lstat()
    except OSError as exc:
        raise ArchiveMigrationRefused("V2Y_FIXTURE_ROOT_MISSING") from exc
    _require(stat.S_ISDIR(st.st_mode)
             and st.st_uid == os.geteuid()
             and st.st_mode & 0o077 == 0,
             "V2Y_FIXTURE_ROOT_UNSAFE")
    file = root / MARKER
    try:
        fd = os.open(file, os.O_RDONLY | os.O_CLOEXEC
                     | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0))
        try:
            info = os.fstat(fd)
            _require(stat.S_ISREG(info.st_mode)
                     and info.st_uid == os.geteuid()
                     and info.st_nlink == 1
                     and info.st_mode & 0o077 == 0
                     and info.st_size == len(MARKER_CONTENT),
                     "V2Y_FIXTURE_MARKER_UNSAFE")
            data = os.read(fd, len(MARKER_CONTENT) + 1)
        finally:
            os.close(fd)
    except ArchiveMigrationRefused:
        raise
    except OSError as exc:
        raise ArchiveMigrationRefused("V2Y_FIXTURE_MARKER_MISSING") from exc
    _require(data == MARKER_CONTENT, "V2Y_FIXTURE_MARKER_INVALID")


def _schema_columns(db):
    return tuple(row[1] for row in db.execute(
        "PRAGMA table_info(fixture_signed_admissions)"))


class TestArchiveStoreAdmissionV2y:
    """A production-shaped disposable schema exercise, never live authority."""

    def __init__(self, archive):
        _require(type(archive) is ArchiveStore,
                 "V2Y_ARCHIVESTORE_REQUIRED")
        _fixture_marker(archive.root)
        _require(archive.path == archive.root / DB_NAME,
                 "V2Y_ARCHIVE_FILENAME_INVALID")
        self.archive = archive
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                meta = db.execute("""SELECT schema_id,revision,payload_bytes
                    FROM archive_meta WHERE id=1""").fetchone()
                _require(meta is not None
                         and meta[0] == "post-apollo.trash-archive.v2a",
                         "V2Y_ARCHIVE_SCHEMA_UNSUPPORTED")
                existing_rows = db.execute(
                    "SELECT count(*) FROM snapshots").fetchone()[0]
                _require(meta[1] >= 0 and meta[2] >= 0
                         and existing_rows >= 0,
                         "V2Y_ARCHIVE_META_INVALID")
                db.execute("""CREATE TABLE IF NOT EXISTS fixture_signed_admissions(
                    snapshot_id TEXT PRIMARY KEY REFERENCES snapshots(id),
                    owner_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    proof_sha256 TEXT NOT NULL,
                    signed_receipt_sha256 TEXT NOT NULL,
                    external_floor_sha256 TEXT NOT NULL,
                    signed_claim BLOB NOT NULL,
                    signature_b64 TEXT NOT NULL,
                    UNIQUE(owner_id,key_id,nonce)
                )""")
                _require(_schema_columns(db) == EXPECTED_ADMISSION_COLUMNS,
                         "V2Y_ADMISSION_SCHEMA_UNSUPPORTED")
                db.execute("""CREATE TABLE IF NOT EXISTS fixture_admission_meta(
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    schema_id TEXT NOT NULL
                )""")
                db.execute("""INSERT OR IGNORE INTO fixture_admission_meta(
                    id,schema_id) VALUES(1,?)""", (MIGRATION_SCHEMA,))
                version = db.execute(
                    "SELECT schema_id FROM fixture_admission_meta WHERE id=1"
                ).fetchone()
                _require(version == (MIGRATION_SCHEMA,),
                         "V2Y_ADMISSION_VERSION_UNSUPPORTED")
                db.commit()
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise ArchiveMigrationRefused("V2Y_SCHEMA_REHEARSAL_FAILED") from exc
            except BaseException:
                db.rollback()
                raise

    def _connect(self, *, readonly=False):
        _fixture_marker(self.archive.root)
        if not readonly:
            return self.archive._connect()
        self.archive._check_root()
        from scripts.trash.archive_store_v2 import _private_file
        _private_file(self.archive.path)
        # A read-only connect must not create any WAL or SHM sidecar.
        for ext in ("-wal", "-shm"):
            _require(not (self.archive.root / (DB_NAME + ext)).exists(),
                     "V2Y_UNEXPECTED_SIDECAR")
        from urllib.parse import quote
        try:
            uri = "file:" + quote(str(self.archive.path),safe="/") + "?mode=ro"
            db = sqlite3.connect(uri,uri=True,timeout=5)
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA foreign_keys=ON")
            return db
        except sqlite3.DatabaseError as exc:
            raise ArchiveMigrationRefused("V2Y_DB_READ_UNAVAILABLE") from exc

    def admit(self, signed_source, capture_policy, signed_receipt,
              receipt_key, payload, display_label, *, floor_reader,
              history, signed_release, release_root, grant_sha256,
              now_ms, on_stage=None):
        """Atomic test copy using real ArchiveStore snapshot/meta/receipt tables."""
        _require(type(payload) is bytes
                 and 0 < len(payload) <= MAX_ITEM_BYTES
                 and type(display_label) is str
                 and len(display_label) <= 120
                 and all(x.isprintable() for x in display_label)
                 and type(now_ms) is int and 1 <= now_ms <= MAX_MS
                 and type(grant_sha256) is str and SHA.fullmatch(grant_sha256)
                 and (on_stage is None or callable(on_stage)),
                 "V2Y_INPUT_INVALID")
        _require(type(signed_receipt) is dict
                 and type(signed_receipt.get("claim")) is dict,
                 "V2Y_SIGNED_RECEIPT_REQUIRED")
        claim = signed_receipt["claim"]
        receipt_sha, raw = _verified_signature(signed_receipt, receipt_key)
        _require(type(capture_policy) is dict
                 and receipt_key["publicKeyBytes"]
                     != capture_policy.get("publicKeyBytes"),
                 "V2Y_DISTINCT_RECEIPT_SIGNER_REQUIRED")
        digest = hashlib.sha256(payload).hexdigest()
        source = verify_test_proof(
            signed_source,capture_policy,owner_id=claim["ownerId"],
            resource_id=claim["resourceId"],
            source_revision=claim["sourceRevision"],
            payload_sha256=digest,now_ms=now_ms)
        _require(source["signatureVerified"] is True
                 and source["captureAllowed"] is False
                 and source["productionAllowed"] is False
                 and claim["policyOrigin"] == "TEST_FIXTURE_ONLY"
                 and claim["ownerId"] in PILOT_OWNERS
                 and claim["captureKeyId"] == source["keyId"]
                 and claim["nonce"] == source["nonce"]
                 and claim["proofSha256"] == source["proofSha256"]
                 and claim["payloadSha256"] == digest
                 and claim["sourceCapturedAtMs"] ==
                     signed_source["claim"]["sourceCapturedAtMs"]
                 and claim["displayLabel"] == display_label
                 and claim["archivedAtMs"] <= now_ms + 30000,
                 "V2Y_SOURCE_RECEIPT_BINDING_INVALID")
        _require(type(floor_reader) is ReadOnlyExternalFloor
                 and floor_reader._fixture is True
                 and type(history) is TestServiceReleaseHistory,
                 "V2Y_TEST_FLOOR_REQUIRED")

        def current_floor():
            try:
                value = floor_reader.require_current(
                    history=history,signed_release=signed_release,
                    release_root=release_root,owner_id=claim["ownerId"],
                    grant_sha256=grant_sha256,now_ms=now_ms)
            except Exception as exc:
                raise ArchiveMigrationRefused("V2Y_FLOOR_REFUSED") from exc
            _require(value["state"] == "TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY"
                     and value["sourceAuthorityVerified"] is False
                     and value["productionAllowed"] is False,
                     "V2Y_TEST_FLOOR_REQUIRED")
            return value["externalFloorSha256"]

        expected_floor = current_floor()
        _require(claim["externalFloorSha256"] == expected_floor,
                 "V2Y_FLOOR_RECEIPT_MISMATCH")
        sid = claim["snapshotId"]
        with closing(self._connect()) as db:
            try:
                page_size = db.execute("PRAGMA page_size").fetchone()[0]
                max_pages = self.archive.disk_quota // page_size
                _require(max_pages >= 1 and
                         db.execute("PRAGMA page_count").fetchone()[0] <= max_pages,
                         "V2Y_ARCHIVE_DISK_QUOTA")
                db.execute("PRAGMA max_page_count="+str(max_pages))
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("""SELECT 1
                    FROM fixture_signed_admissions
                    WHERE owner_id=? AND key_id=? AND nonce=?""",
                    (claim["ownerId"],source["keyId"],source["nonce"])).fetchone()
                _require(existing is None,"V2Y_NONCE_ALREADY_CONSUMED")
                meta = db.execute("""SELECT payload_bytes FROM archive_meta
                    WHERE id=1""").fetchone()
                _require(meta is not None,"V2Y_ARCHIVE_META_INVALID")
                _require(meta[0]+len(payload) <= self.archive.payload_quota,
                         "V2Y_ARCHIVE_PAYLOAD_QUOTA")
                capacity = self.archive._capacity()
                _require(capacity["chargedBytes"] < self.archive.disk_quota,
                         "V2Y_ARCHIVE_DISK_QUOTA")
                _require(capacity["filesystemAvailableBytes"] >=
                         max(16*1024*1024,len(payload)*2),
                         "V2Y_ARCHIVE_FILESYSTEM_SPACE")
                previous = db.execute("""SELECT r.receipt_sha256
                    FROM snapshot_receipts r JOIN snapshots s
                    ON s.id=r.snapshot_id
                    WHERE s.owner_id=? AND s.resource_id=?
                    ORDER BY s.rowid DESC LIMIT 1""",
                    (claim["ownerId"],claim["resourceId"])).fetchone()
                ancestor = previous[0] if previous else ""
                _require(ancestor == claim["previousReceiptSha256"],
                         "V2Y_RECEIPT_PREDECESSOR_INVALID")
                local = create_receipt(
                    sid,claim["ownerId"],claim["resourceId"],
                    claim["sourceRevision"],claim["sourceCapturedAtMs"],
                    claim["archivedAtMs"],display_label,digest,ancestor)
                db.execute("""INSERT INTO snapshots(
                    id,owner_id,resource_id,source_revision,captured_ms,
                    display_label,sha256,payload,provenance_required)
                    VALUES(?,?,?,?,?,?,?,?,1)""",
                    (sid,claim["ownerId"],claim["resourceId"],
                     claim["sourceRevision"],claim["sourceCapturedAtMs"],
                     display_label,digest,payload))
                if on_stage: on_stage("after_copy")
                db.execute("""INSERT INTO snapshot_receipts(
                    snapshot_id,owner_id,resource_id,source_revision,
                    source_captured_ms,archived_ms,display_label,
                    payload_sha256,previous_receipt_sha256,
                    receipt_sha256,receipt_schema)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid,claim["ownerId"],claim["resourceId"],
                     claim["sourceRevision"],claim["sourceCapturedAtMs"],
                     claim["archivedAtMs"],display_label,digest,ancestor,
                     local["receiptSha256"],RECEIPT_SCHEMA))
                if on_stage: on_stage("after_local_receipt")
                db.execute("""INSERT INTO fixture_signed_admissions(
                    snapshot_id,owner_id,key_id,nonce,proof_sha256,
                    signed_receipt_sha256,external_floor_sha256,
                    signed_claim,signature_b64)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (sid,claim["ownerId"],source["keyId"],source["nonce"],
                     source["proofSha256"],receipt_sha,expected_floor,
                     raw,signed_receipt["signatureB64"]))
                if on_stage: on_stage("after_signed_receipt")
                db.execute("""UPDATE archive_meta SET revision=revision+1,
                    payload_bytes=payload_bytes+? WHERE id=1""",(len(payload),))
                if on_stage: on_stage("after_accounting")
                _require(current_floor() == expected_floor,
                         "V2Y_FLOOR_CHANGED")
                _require(self.archive._capacity()["chargedBytes"]
                         <= self.archive.disk_quota,"V2Y_ARCHIVE_DISK_QUOTA")
                db.commit()
                if on_stage: on_stage("after_commit")
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise ArchiveMigrationRefused("V2Y_NONCE_OR_SNAPSHOT_REPLAY") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise ArchiveMigrationRefused("V2Y_ARCHIVE_WRITE_FAILED") from exc
            except BaseException:
                db.rollback()
                raise
        return {
            "state":"TEST_ARCHIVESTORE_SCHEMA_ADMITTED_DENY_ONLY",
            "snapshotId":sid,"ownerId":claim["ownerId"],
            "nonce":source["nonce"],"signedReceiptSha256":receipt_sha,
            "localReceiptSha256":local["receiptSha256"],
            "payloadSha256":digest,"archiveCopyAuthorized":False,
            "captureAllowed":False,"productionAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }

    def inspect(self, owner_id, key_id, nonce, receipt_key):
        """Read-only recovery: no payload or privilege leaks."""
        _require(type(owner_id) is str and owner_id in PILOT_OWNERS
                 and type(key_id) is str and KEY_ID.fullmatch(key_id)
                 and type(nonce) is str and NONCE.fullmatch(nonce),
                 "V2Y_RECOVERY_ID_INVALID")
        with closing(self._connect(readonly=True)) as db:
            witness = db.execute("""SELECT snapshot_id,proof_sha256,
                signed_receipt_sha256,external_floor_sha256,
                signed_claim,signature_b64
                FROM fixture_signed_admissions
                WHERE owner_id=? AND key_id=? AND nonce=?""",
                (owner_id,key_id,nonce)).fetchone()
            if witness is None:
                return {"state":"TEST_NOT_ADMITTED","productionAllowed":False}
            sid,proof,signed_sha,floor_sha,raw,signature = witness
            row = db.execute("""SELECT s.id,s.owner_id,s.resource_id,
                s.source_revision,s.captured_ms,s.display_label,s.sha256,
                s.provenance_required,s.payload,
                r.snapshot_id,r.owner_id,r.resource_id,r.source_revision,
                r.source_captured_ms,r.archived_ms,r.display_label,
                r.payload_sha256,r.previous_receipt_sha256,
                r.receipt_sha256,r.receipt_schema
                FROM snapshots s LEFT JOIN snapshot_receipts r
                ON r.snapshot_id=s.id WHERE s.id=?""",(sid,)).fetchone()
        _require(row is not None and row[7] == 1
                 and type(row[8]) is bytes
                 and hashlib.sha256(row[8]).hexdigest() == row[6],
                 "V2Y_RECOVERY_INTEGRITY_INVALID")
        try:
            verified_local = verify_receipt(row[:8],row[9:])
        except ProvenanceError as exc:
            raise ArchiveMigrationRefused("V2Y_RECOVERY_INTEGRITY_INVALID") from exc
        _require(verified_local["state"] == "RECEIPT_MATCHED",
                 "V2Y_RECOVERY_INTEGRITY_INVALID")
        import json
        try:
            claim = json.loads(raw.decode("ascii"))
        except (ValueError,UnicodeError,TypeError) as exc:
            raise ArchiveMigrationRefused("V2Y_RECOVERY_INTEGRITY_INVALID") from exc
        from scripts.trash.archive_v2_single_db_fixture import (
            canonical_receipt_claim,
        )
        _require(canonical_receipt_claim(claim) == raw
                 and claim["snapshotId"] == sid
                 and claim["ownerId"] == owner_id
                 and claim["resourceId"] == row[2]
                 and claim["sourceRevision"] == row[3]
                 and claim["sourceCapturedAtMs"] == row[4]
                 and claim["displayLabel"] == row[5]
                 and claim["payloadSha256"] == row[6]
                 and claim["proofSha256"] == proof
                 and claim["captureKeyId"] == key_id
                 and claim["nonce"] == nonce
                 and claim["externalFloorSha256"] == floor_sha
                 and claim["previousReceiptSha256"] == row[17]
                 and hashlib.sha256(raw).hexdigest() == signed_sha,
                 "V2Y_RECOVERY_INTEGRITY_INVALID")
        _verified_signature({"claim":claim,"signatureB64":signature},receipt_key)
        return {
            "state":"TEST_ARCHIVESTORE_RECEIPT_RECOVERED_DENY_ONLY",
            "snapshotId":sid,"localReceiptSha256":row[18],
            "signedReceiptSha256":signed_sha,
            "payloadIntegrityVerified":True,
            "sourceAuthorityVerified":False,
            "archiveCopyAuthorized":False,
            "captureAllowed":False,"productionAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }
