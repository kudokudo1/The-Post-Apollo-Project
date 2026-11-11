#!/usr/bin/env python3
"""V2x one-database quota/nonce/signed-receipt commit PROTOTYPE.

Writes ONLY a dedicated trashpp-v2x-test-archive.sqlite3 inside an explicitly
named, private fixture directory. It does not write ArchiveStore's database,
install a signer, connect a real owner, authorize Capture, Restore or Burn.

All authorization inputs are synthetic. The external floor is reverified
before and just before committing one SQLite transaction containing quota
accounting, consumed nonce, copy and both signed/local metadata receipts.
A cross-filesystem floor change after the last check is still possible.
"""
import base64
import binascii
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

from scripts.trash.archive_v2_external_floor_reader import ReadOnlyExternalFloor
from scripts.trash.archive_v2_provenance import create_receipt
from scripts.trash.archive_v2_service_release_history import TestServiceReleaseHistory
from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, Ed25519PublicKey, InvalidSignature,
    KEY_ID, NONCE, RESOURCE, SHA, verify_test_proof,
)

DB_NAME = "trashpp-v2x-test-archive.sqlite3"
SCHEMA = "post-apollo.trashpp.fixture-signed-archive-receipt.v2x"
FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "receiptKeyId",
    "snapshotId", "ownerId", "resourceId", "sourceRevision",
    "sourceCapturedAtMs", "archivedAtMs", "displayLabel", "payloadSha256",
    "captureKeyId", "nonce", "proofSha256", "externalFloorSha256",
    "previousReceiptSha256",
))
ENVELOPE = frozenset(("claim", "signatureB64"))
RECEIPT_KEY = frozenset(("rootKeyId", "publicKeyBytes", "origin"))
HEX_ID = re.compile(r"^[0-9a-f]{32}$")
MAX_COPY = 8 * 1024 * 1024
MAX_MS = 9999999999999
MIN_DISK = 64 * 1024
DEFAULT_DISK = 64 * 1024 * 1024


class FixtureCommitRefused(Exception):
    """Safe denial codes; no private file names, signatures or data."""


def _require(value, code):
    if not value:
        raise FixtureCommitRefused(code)


def _ms(value):
    return type(value) is int and 1 <= value <= MAX_MS


def canonical_receipt_claim(claim):
    _require(type(claim) is dict and set(claim) == FIELDS,
             "FIXTURE_RECEIPT_SCHEMA_INVALID")
    _require(claim["schema"] == SCHEMA
             and claim["audience"] == AUDIENCE
             and claim["purpose"] == PURPOSE
             and claim["policyOrigin"] == "TEST_FIXTURE_ONLY",
             "FIXTURE_RECEIPT_SCOPE_INVALID")
    _require(type(claim["receiptKeyId"]) is str
             and KEY_ID.fullmatch(claim["receiptKeyId"])
             and type(claim["captureKeyId"]) is str
             and KEY_ID.fullmatch(claim["captureKeyId"])
             and type(claim["ownerId"]) is str
             and claim["ownerId"] in ALLOWED_OWNERS
             and type(claim["resourceId"]) is str
             and RESOURCE.fullmatch(claim["resourceId"])
             and type(claim["snapshotId"]) is str
             and HEX_ID.fullmatch(claim["snapshotId"])
             and type(claim["sourceRevision"]) is str
             and SHA.fullmatch(claim["sourceRevision"])
             and type(claim["payloadSha256"]) is str
             and SHA.fullmatch(claim["payloadSha256"])
             and type(claim["displayLabel"]) is str
             and len(claim["displayLabel"]) <= 120
             and all(c.isprintable() for c in claim["displayLabel"])
             and type(claim["nonce"]) is str
             and NONCE.fullmatch(claim["nonce"])
             and type(claim["proofSha256"]) is str
             and SHA.fullmatch(claim["proofSha256"])
             and type(claim["externalFloorSha256"]) is str
             and SHA.fullmatch(claim["externalFloorSha256"])
             and type(claim["previousReceiptSha256"]) is str
             and (claim["previousReceiptSha256"] == ""
                  or SHA.fullmatch(claim["previousReceiptSha256"])),
             "FIXTURE_RECEIPT_FIELDS_INVALID")
    _require(_ms(claim["sourceCapturedAtMs"])
             and _ms(claim["archivedAtMs"])
             and claim["sourceCapturedAtMs"] <= claim["archivedAtMs"],
             "FIXTURE_RECEIPT_TIME_INVALID")
    raw = json.dumps(claim, sort_keys=True, ensure_ascii=True,
                     separators=(",",":"), allow_nan=False).encode("ascii")
    _require(len(raw) <= 4096, "FIXTURE_RECEIPT_TOO_LARGE")
    return raw


def _verified_signature(signed, key):
    _require(type(key) is dict and set(key) == RECEIPT_KEY
             and key["origin"] == "EXTERNALLY_PINNED_TEST_ROOT"
             and type(key["rootKeyId"]) is str
             and KEY_ID.fullmatch(key["rootKeyId"])
             and type(key["publicKeyBytes"]) is bytes
             and len(key["publicKeyBytes"]) == 32,
             "FIXTURE_RECEIPT_KEY_NOT_PROVISIONED")
    _require(type(signed) is dict and set(signed) == ENVELOPE,
             "FIXTURE_RECEIPT_ENVELOPE_INVALID")
    raw = canonical_receipt_claim(signed["claim"])
    _require(signed["claim"]["receiptKeyId"] == key["rootKeyId"],
             "FIXTURE_RECEIPT_KEY_MISMATCH")
    wire = signed["signatureB64"]
    _require(type(wire) is str and len(wire) == 88,
             "FIXTURE_RECEIPT_SIGNATURE_INVALID")
    try:
        decoded = base64.b64decode(wire, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FixtureCommitRefused("FIXTURE_RECEIPT_SIGNATURE_INVALID") from exc
    _require(len(decoded) == 64 and
             base64.b64encode(decoded).decode("ascii") == wire,
             "FIXTURE_RECEIPT_SIGNATURE_INVALID")
    _require(Ed25519PublicKey is not None,
             "FIXTURE_RECEIPT_CRYPTO_UNAVAILABLE")
    try:
        Ed25519PublicKey.from_public_bytes(
            key["publicKeyBytes"]).verify(decoded, raw)
    except (InvalidSignature, ValueError) as exc:
        raise FixtureCommitRefused("FIXTURE_RECEIPT_SIGNATURE_REFUSED") from exc
    return hashlib.sha256(raw).hexdigest(), raw


class TestAtomicArchiveCommit:
    """Only test-prefixed private roots and a dedicated synthetic filename."""

    def __init__(self, root, *, payload_quota=16*1024*1024,
                 disk_quota=DEFAULT_DISK):
        _require(type(root) in (str, Path) and
                 Path(root).is_absolute()
                 and ".." not in Path(root).parts
                 and Path(root).name.startswith("trashpp-v2x-fixture-")
                 and type(payload_quota) is int
                 and 1 <= payload_quota <= 2**40
                 and type(disk_quota) is int
                 and MIN_DISK <= disk_quota <= 2**40,
                 "FIXTURE_ARCHIVE_CONFIG_INVALID")
        self.root = Path(root)
        self.path = self.root / DB_NAME
        self.payload_quota = payload_quota
        self.disk_quota = disk_quota
        self._guard_root()
        _require(not (self.root / "trashpp-archive-v2.sqlite3").exists(),
                 "FIXTURE_REAL_ARCHIVE_PRESENT")
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT
                             | os.O_EXCL | getattr(os,"O_NOFOLLOW",0), 0o600)
                os.close(fd)
            except FileExistsError:
                self._guard_file()
            except OSError as exc:
                raise FixtureCommitRefused("FIXTURE_ARCHIVE_CREATE_FAILED") from exc
        self._guard_file()
        with closing(self._connect()) as db:
            try:
                with db:
                    db.execute("""CREATE TABLE IF NOT EXISTS test_meta(
                        id INTEGER PRIMARY KEY CHECK(id=1),
                        revision INTEGER NOT NULL CHECK(revision>=0),
                        payload_bytes INTEGER NOT NULL CHECK(payload_bytes>=0)
                    )""")
                    db.execute("""INSERT OR IGNORE INTO test_meta
                        (id,revision,payload_bytes) VALUES(1,0,0)""")
                    db.execute("""CREATE TABLE IF NOT EXISTS test_nonces(
                        owner_id TEXT NOT NULL,key_id TEXT NOT NULL,
                        nonce TEXT NOT NULL,proof_sha256 TEXT NOT NULL,
                        snapshot_id TEXT NOT NULL UNIQUE,
                        PRIMARY KEY(owner_id,key_id,nonce)
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS test_snapshots(
                        id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,
                        resource_id TEXT NOT NULL,source_revision TEXT NOT NULL,
                        captured_ms INTEGER NOT NULL,archived_ms INTEGER NOT NULL,
                        display_label TEXT NOT NULL,payload_sha256 TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        UNIQUE(owner_id,resource_id,source_revision)
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS test_receipts(
                        snapshot_id TEXT PRIMARY KEY
                            REFERENCES test_snapshots(id),
                        local_receipt_sha256 TEXT NOT NULL,
                        previous_receipt_sha256 TEXT NOT NULL,
                        signed_claim BLOB NOT NULL,
                        signature_b64 TEXT NOT NULL,
                        signed_receipt_sha256 TEXT NOT NULL,
                        external_floor_sha256 TEXT NOT NULL
                    )""")
            except sqlite3.DatabaseError as exc:
                raise FixtureCommitRefused("FIXTURE_SCHEMA_FAILED") from exc

    def _guard_root(self):
        try:
            st = self.root.lstat()
        except OSError as exc:
            raise FixtureCommitRefused("FIXTURE_ROOT_UNAVAILABLE") from exc
        _require(stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid()
                 and st.st_mode & 0o077 == 0,
                 "FIXTURE_ROOT_UNSAFE")

    def _guard_file(self):
        self._guard_root()
        try:
            st = self.path.lstat()
        except OSError as exc:
            raise FixtureCommitRefused("FIXTURE_DB_UNAVAILABLE") from exc
        _require(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid()
                 and st.st_nlink == 1 and st.st_mode & 0o077 == 0,
                 "FIXTURE_DB_UNSAFE")
        for ext in ("-wal","-shm"):
            try:
                (self.root / (DB_NAME + ext)).lstat()
            except FileNotFoundError:
                continue
            raise FixtureCommitRefused("FIXTURE_UNEXPECTED_SIDECAR")

    def _connect(self, *, read_only=False):
        self._guard_file()
        try:
            if read_only:
                uri = "file:" + quote(str(self.path),safe="/") + "?mode=ro"
                db = sqlite3.connect(uri,uri=True,timeout=5)
                db.execute("PRAGMA query_only=ON")
            else:
                db = sqlite3.connect(str(self.path),timeout=5)
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=5000")
            return db
        except sqlite3.DatabaseError as exc:
            raise FixtureCommitRefused("FIXTURE_DB_UNAVAILABLE") from exc

    def _charged(self):
        logical = allocated = 0
        for name in (DB_NAME, DB_NAME+"-journal"):
            path = self.root / name
            try:
                st = path.lstat()
            except FileNotFoundError:
                continue
            _require(stat.S_ISREG(st.st_mode) and
                     st.st_uid == os.geteuid() and st.st_nlink == 1,
                     "FIXTURE_DISK_UNSAFE")
            logical += st.st_size
            allocated += st.st_blocks * 512
        return max(logical,allocated)

    @staticmethod
    def _floor_current(reader, history, signed_release,
                       release_root, owner, grant, now_ms, expected=None):
        _require(type(reader) is ReadOnlyExternalFloor
                 and reader._fixture is True
                 and type(history) is TestServiceReleaseHistory,
                 "FIXTURE_FLOOR_NOT_AUTHORITY")
        try:
            verified = reader.require_current(
                history=history, signed_release=signed_release,
                release_root=release_root, owner_id=owner,
                grant_sha256=grant, now_ms=now_ms)
        except Exception as exc:
            raise FixtureCommitRefused("FIXTURE_FLOOR_REFUSED") from exc
        _require(verified.get("state") ==
                 "TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY"
                 and verified.get("signatureVerified") is True
                 and verified.get("sourceAuthorityVerified") is False
                 and verified.get("captureAllowed") is False
                 and verified.get("productionAllowed") is False
                 and type(verified.get("externalFloorSha256")) is str
                 and SHA.fullmatch(verified["externalFloorSha256"]),
                 "FIXTURE_FLOOR_NOT_AUTHORITY")
        if expected is not None:
            _require(verified["externalFloorSha256"] == expected,
                     "FIXTURE_FLOOR_CHANGED")
        return verified["externalFloorSha256"]

    def admit(self, signed_capture, capture_policy, signed_receipt, receipt_key,
              payload, display_label, *, floor_reader, release_history,
              signed_release, release_root, grant_sha256, now_ms,
              on_stage=None):
        """One transaction: nonce, synthetic copy, local+signed receipt, quotas."""
        _require(type(payload) is bytes and 0 < len(payload) <= MAX_COPY,
                 "FIXTURE_PAYLOAD_INVALID")
        _require(type(display_label) is str
                 and len(display_label) <= 120
                 and all(c.isprintable() for c in display_label)
                 and (on_stage is None or callable(on_stage)),
                 "FIXTURE_LABEL_OR_HOOK_INVALID")
        digest = hashlib.sha256(payload).hexdigest()
        _require(type(signed_receipt) is dict
                 and type(signed_receipt.get("claim")) is dict,
                 "FIXTURE_RECEIPT_ENVELOPE_INVALID")
        claim = signed_receipt["claim"]
        _require(_ms(now_ms)
                 and type(grant_sha256) is str and SHA.fullmatch(grant_sha256),
                 "FIXTURE_CLOCK_OR_GRANT_INVALID")
        signed_hash, signed_raw = _verified_signature(
            signed_receipt, receipt_key)
        _require(claim["archivedAtMs"] <= now_ms + 30000
                 and claim["displayLabel"] == display_label,
                 "FIXTURE_RECEIPT_LABEL_OR_TIME_MISMATCH")
        _require(receipt_key["publicKeyBytes"] !=
                 capture_policy.get("publicKeyBytes"),
                 "FIXTURE_RECEIPT_KEY_NOT_DISTINCT")
        source = verify_test_proof(
            signed_capture, capture_policy,
            owner_id=claim["ownerId"], resource_id=claim["resourceId"],
            source_revision=claim["sourceRevision"], payload_sha256=digest,
            now_ms=now_ms)
        _require(source["captureAllowed"] is False
                 and source["signatureVerified"] is True
                 and source["productionAllowed"] is False
                 and claim["captureKeyId"] == source["keyId"]
                 and claim["nonce"] == source["nonce"]
                 and claim["proofSha256"] == source["proofSha256"]
                 and claim["payloadSha256"] == digest
                 and signed_capture["claim"]["sourceCapturedAtMs"]
                     == claim["sourceCapturedAtMs"],
                 "FIXTURE_PROOF_RECEIPT_MISMATCH")
        floor_digest = self._floor_current(
            floor_reader,release_history,signed_release,release_root,
            claim["ownerId"],grant_sha256,now_ms)
        _require(floor_digest == claim["externalFloorSha256"],
                 "FIXTURE_FLOOR_RECEIPT_MISMATCH")
        sid = claim["snapshotId"]
        with closing(self._connect()) as db:
            try:
                pagesize = db.execute("PRAGMA page_size").fetchone()[0]
                page_cap = self.disk_quota // pagesize
                _require(page_cap >= 1 and
                         db.execute("PRAGMA page_count").fetchone()[0]
                             <= page_cap,
                         "FIXTURE_DISK_QUOTA")
                selected = db.execute(
                    "PRAGMA max_page_count="+str(page_cap)).fetchone()[0]
                _require(selected <= page_cap, "FIXTURE_DISK_QUOTA")
                db.execute("BEGIN IMMEDIATE")
                revision,used = db.execute(
                    "SELECT revision,payload_bytes FROM test_meta WHERE id=1"
                ).fetchone()
                _require(used+len(payload) <= self.payload_quota,
                         "FIXTURE_PAYLOAD_QUOTA")
                previous = db.execute("""SELECT r.local_receipt_sha256
                    FROM test_receipts r JOIN test_snapshots s
                      ON s.id=r.snapshot_id
                    WHERE s.owner_id=? AND s.resource_id=?
                    ORDER BY s.rowid DESC LIMIT 1""",
                    (claim["ownerId"],claim["resourceId"])).fetchone()
                parent = previous[0] if previous else ""
                _require(parent == claim["previousReceiptSha256"],
                         "FIXTURE_RECEIPT_PREDECESSOR_MISMATCH")
                db.execute("""INSERT INTO test_nonces
                    (owner_id,key_id,nonce,proof_sha256,snapshot_id)
                    VALUES(?,?,?,?,?)""",
                    (claim["ownerId"],source["keyId"],source["nonce"],
                     source["proofSha256"],sid))
                if on_stage is not None:
                    on_stage("after_nonce")
                local = create_receipt(
                    sid,claim["ownerId"],claim["resourceId"],
                    claim["sourceRevision"],claim["sourceCapturedAtMs"],
                    claim["archivedAtMs"],display_label,digest,parent)
                db.execute("""INSERT INTO test_snapshots
                    (id,owner_id,resource_id,source_revision,captured_ms,
                     archived_ms,display_label,payload_sha256,payload)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (sid,claim["ownerId"],claim["resourceId"],
                     claim["sourceRevision"],claim["sourceCapturedAtMs"],
                     claim["archivedAtMs"],display_label,digest,payload))
                if on_stage is not None:
                    on_stage("after_copy")
                db.execute("""INSERT INTO test_receipts
                    (snapshot_id,local_receipt_sha256,previous_receipt_sha256,
                     signed_claim,signature_b64,signed_receipt_sha256,
                     external_floor_sha256)
                    VALUES(?,?,?,?,?,?,?)""",
                    (sid,local["receiptSha256"],parent,signed_raw,
                     signed_receipt["signatureB64"],signed_hash,floor_digest))
                if on_stage is not None:
                    on_stage("after_receipt")
                db.execute("""UPDATE test_meta SET revision=revision+1,
                    payload_bytes=payload_bytes+? WHERE id=1""",
                    (len(payload),))
                if on_stage is not None:
                    on_stage("after_accounting")
                self._floor_current(
                    floor_reader,release_history,signed_release,release_root,
                    claim["ownerId"],grant_sha256,now_ms,
                    expected=floor_digest)
                _require(self._charged() <= self.disk_quota,
                         "FIXTURE_DISK_QUOTA")
                db.commit()
                if on_stage is not None:
                    on_stage("after_commit")
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise FixtureCommitRefused("FIXTURE_NONCE_OR_COPY_REPLAY") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                if getattr(exc, "sqlite_errorcode",None) == sqlite3.SQLITE_FULL:
                    raise FixtureCommitRefused("FIXTURE_DISK_QUOTA") from exc
                raise FixtureCommitRefused("FIXTURE_TXN_FAILED") from exc
            except BaseException:
                db.rollback()
                raise
        return {
            "state":"TEST_SINGLE_DB_COMMITTED_DENY_ONLY",
            "snapshotId":sid,"ownerId":claim["ownerId"],
            "nonce":source["nonce"],
            "payloadSha256":digest,
            "signedReceiptSha256":signed_hash,
            "localReceiptSha256":local["receiptSha256"],
            "externalFloorSha256":floor_digest,
            "captureAllowed":False,"productionAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }

    def status(self):
        with closing(self._connect(read_only=True)) as db:
            meta = db.execute(
                "SELECT revision,payload_bytes FROM test_meta WHERE id=1"
            ).fetchone()
            number = db.execute("SELECT count(*) FROM test_snapshots").fetchone()[0]
        return {"revision":meta[0],"payloadBytes":meta[1],"copies":number,
                "payloadQuota":self.payload_quota,"diskQuota":self.disk_quota,
                "captureAllowed":False,"productionAllowed":False}

    def inspect(self, owner_id, capture_key_id, nonce, receipt_key):
        """Read-only recovery: verifies bytes+local receipt+test signature."""
        _require(type(owner_id) is str and owner_id in ALLOWED_OWNERS
                 and type(capture_key_id) is str
                 and KEY_ID.fullmatch(capture_key_id)
                 and type(nonce) is str and NONCE.fullmatch(nonce),
                 "FIXTURE_RECOVERY_ID_INVALID")
        with closing(self._connect(read_only=True)) as db:
            row = db.execute("""SELECT n.proof_sha256,s.id,
                s.owner_id,s.resource_id,s.source_revision,s.captured_ms,
                s.archived_ms,s.display_label,s.payload_sha256,s.payload,
                r.local_receipt_sha256,r.previous_receipt_sha256,
                r.signed_claim,r.signature_b64,r.signed_receipt_sha256,
                r.external_floor_sha256
                FROM test_nonces n
                JOIN test_snapshots s ON s.id=n.snapshot_id
                JOIN test_receipts r ON r.snapshot_id=s.id
                WHERE n.owner_id=? AND n.key_id=? AND n.nonce=?""",
                (owner_id,capture_key_id,nonce)).fetchone()
            orphan = None if row is not None else db.execute(
                """SELECT 1 FROM test_nonces
                WHERE owner_id=? AND key_id=? AND nonce=?""",
                (owner_id,capture_key_id,nonce)).fetchone()
        if row is None:
            _require(orphan is None, "FIXTURE_RECOVERY_INTEGRITY_INVALID")
            return {"state":"TEST_NOT_ADMITTED","productionAllowed":False}
        (proof,sid,owner,resource,revision,captured,archived,label,
         payload_sha,payload,local_hash,prev_hash,signed_raw,signature,
         signed_hash,floor_hash)=row
        _require(type(payload) is bytes
                 and hashlib.sha256(payload).hexdigest() == payload_sha,
                 "FIXTURE_RECOVERY_INTEGRITY_INVALID")
        local = create_receipt(
            sid,owner,resource,revision,captured,archived,label,
            payload_sha,prev_hash)
        _require(local["receiptSha256"] == local_hash,
                 "FIXTURE_RECOVERY_INTEGRITY_INVALID")
        try:
            claim = json.loads(signed_raw.decode("ascii"))
        except (UnicodeError, ValueError, TypeError) as exc:
            raise FixtureCommitRefused(
                "FIXTURE_RECOVERY_INTEGRITY_INVALID") from exc
        _require(canonical_receipt_claim(claim) == signed_raw
                 and hashlib.sha256(signed_raw).hexdigest() == signed_hash
                 and (claim["snapshotId"],claim["ownerId"],
                      claim["resourceId"],claim["sourceRevision"],
                      claim["sourceCapturedAtMs"],claim["archivedAtMs"],
                      claim["displayLabel"],claim["payloadSha256"],
                      claim["captureKeyId"],claim["nonce"],
                      claim["proofSha256"],claim["externalFloorSha256"],
                      claim["previousReceiptSha256"])
                     == (sid,owner,resource,revision,captured,archived,
                         label,payload_sha,capture_key_id,nonce,proof,
                         floor_hash,prev_hash),
                 "FIXTURE_RECOVERY_INTEGRITY_INVALID")
        _verified_signature({"claim":claim,"signatureB64":signature},receipt_key)
        return {
            "state":"TEST_RECEIPT_RECOVERED_DENY_ONLY",
            "snapshotId":sid,"ownerId":owner,"resourceId":resource,
            "payloadSha256":payload_sha,
            "localReceiptSha256":local_hash,
            "signedReceiptSha256":signed_hash,
            "externalFloorSha256":floor_hash,
            "payloadIntegrityVerified":True,
            "fixtureSignatureVerified":True,
            "receiptSigningAuthorityVerified":False,
            "captureAllowed":False,"productionAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }
