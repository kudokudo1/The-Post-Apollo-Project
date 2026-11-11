#!/usr/bin/env python3
"""V2l TEST-ONLY protected owner trust history and replay state.

Private SQLite with monotonic authority generation and sticky key revocations.
This is not a runtime authority service, does not handle production trust
roots, and cannot authorize ArchiveStore, Restore or Burn.
"""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote
from uuid import uuid4

FILE_NAME = "trashpp-v2l-test-trust.sqlite3"
ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
NONCE = re.compile(r"^[0-9a-f]{32}$")


class TrustHistoryError(Exception):
    """Safe, stable error code without database contents or paths."""


def _check(value, code):
    if not value:
        raise TrustHistoryError(code)


def _regular_file(path, *, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        _check(allow_missing, "SOURCE_TRUST_LEDGER_MISSING")
        return False
    except OSError as exc:
        raise TrustHistoryError("SOURCE_TRUST_LEDGER_UNAVAILABLE") from exc
    _check(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid()
           and st.st_nlink == 1 and st.st_mode & 0o077 == 0,
           "SOURCE_TRUST_LEDGER_UNSAFE")
    return True


class TestOwnerTrustHistory:
    """All changes are confined to an explicit caller-owned 0700 test root."""

    def __init__(self, private_root):
        _check(isinstance(private_root, (str, Path)),
               "SOURCE_TRUST_ROOT_INVALID")
        root = Path(private_root)
        _check(root.is_absolute() and ".." not in root.parts
               and len(str(root)) <= 4096,
               "SOURCE_TRUST_ROOT_INVALID")
        try:
            st = root.lstat()
        except OSError as exc:
            raise TrustHistoryError("SOURCE_TRUST_ROOT_UNAVAILABLE") from exc
        _check(stat.S_ISDIR(st.st_mode)
               and st.st_uid == os.geteuid() and st.st_mode & 0o077 == 0,
               "SOURCE_TRUST_ROOT_UNSAFE")
        self.root = root
        self.path = root / FILE_NAME
        if not _regular_file(self.path, allow_missing=True):
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            except FileExistsError:
                _regular_file(self.path)
            except OSError as exc:
                raise TrustHistoryError("SOURCE_TRUST_CREATE_FAILED") from exc
        self._init()

    def _connect(self):
        _regular_file(self.path)
        for suffix in ("-wal", "-shm"):
            try:
                (self.root / (FILE_NAME + suffix)).lstat()
            except FileNotFoundError:
                continue
            raise TrustHistoryError("SOURCE_TRUST_UNEXPECTED_SIDECAR")
        try:
            db = sqlite3.connect(str(self.path), timeout=5)
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA foreign_keys=ON")
            return db
        except sqlite3.DatabaseError as exc:
            raise TrustHistoryError("SOURCE_TRUST_UNAVAILABLE") from exc

    def _connect_readonly(self):
        """Open the private fixture ledger without enabling any write access."""
        try:
            root = self.root.lstat()
        except OSError as exc:
            raise TrustHistoryError("SOURCE_TRUST_ROOT_UNAVAILABLE") from exc
        _check(stat.S_ISDIR(root.st_mode)
               and root.st_uid == os.geteuid()
               and root.st_mode & 0o077 == 0,
               "SOURCE_TRUST_ROOT_UNSAFE")
        _regular_file(self.path)
        for suffix in ("-wal", "-shm"):
            try:
                (self.root / (FILE_NAME + suffix)).lstat()
            except FileNotFoundError:
                continue
            raise TrustHistoryError("SOURCE_TRUST_UNEXPECTED_SIDECAR")
        try:
            uri = ("file:" + quote(str(self.path), safe="/")
                   + "?mode=ro&cache=private")
            db = sqlite3.connect(uri, uri=True, timeout=5)
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA busy_timeout=5000")
            return db
        except sqlite3.DatabaseError as exc:
            raise TrustHistoryError("SOURCE_TRUST_UNAVAILABLE") from exc

    def _init(self):
        with closing(self._connect()) as db:
            try:
                with db:
                    db.execute("""CREATE TABLE IF NOT EXISTS authority_heads (
                        owner_id TEXT PRIMARY KEY,
                        generation INTEGER NOT NULL,
                        manifest_sha256 TEXT NOT NULL,
                        root_sha256 TEXT NOT NULL,
                        key_id TEXT NOT NULL,
                        issued_ms INTEGER NOT NULL,
                        revoked INTEGER NOT NULL CHECK(revoked IN (0,1))
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS revoked_keys (
                        owner_id TEXT NOT NULL, key_id TEXT NOT NULL,
                        PRIMARY KEY(owner_id, key_id)
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS consumed (
                        owner_id TEXT NOT NULL,
                        key_id TEXT NOT NULL,
                        nonce TEXT NOT NULL,
                        proof_sha256 TEXT NOT NULL,
                        authority_sha256 TEXT NOT NULL,
                        PRIMARY KEY(owner_id,key_id,nonce),
                        UNIQUE(proof_sha256)
                    )""")
                    # V2m fixture admission puts nonce + test payload
                    # in ONE private SQLite transaction.
                    db.execute("""CREATE TABLE IF NOT EXISTS test_copies (
                        snapshot_id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        key_id TEXT NOT NULL,
                        nonce TEXT NOT NULL,
                        proof_sha256 TEXT NOT NULL UNIQUE,
                        authority_sha256 TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        source_revision TEXT NOT NULL,
                        source_captured_ms INTEGER NOT NULL,
                        payload_sha256 TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        UNIQUE(owner_id,key_id,nonce),
                        FOREIGN KEY(owner_id,key_id,nonce)
                            REFERENCES consumed(owner_id,key_id,nonce)
                    )""")
            except sqlite3.DatabaseError as exc:
                raise TrustHistoryError("SOURCE_TRUST_INIT_FAILED") from exc

    def enroll(self, signed_manifest, pinned_root, *, now_ms):
        """Verify root signature BEFORE accepting the next durable floor."""
        from scripts.trash.archive_v2_owner_trust import (
            verify_fixture_authority,
        )
        evidence = verify_fixture_authority(
            signed_manifest, pinned_root, now_ms=now_ms)
        owner = evidence["ownerId"]
        m = signed_manifest["manifest"]
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                prior = db.execute("""SELECT generation,manifest_sha256,
                    root_sha256,key_id,issued_ms FROM authority_heads
                    WHERE owner_id=?""", (owner,)).fetchone()
                if prior is None:
                    _check(evidence["generation"] == 1
                           and evidence["previousManifestSha256"] == "",
                           "SOURCE_AUTHORITY_GENESIS_REQUIRED")
                else:
                    _check(evidence["generation"] == prior[0]+1,
                           "SOURCE_AUTHORITY_GENERATION_REPLAY")
                    _check(evidence["previousManifestSha256"] == prior[1],
                           "SOURCE_AUTHORITY_LINEAGE_REFUSED")
                    _check(evidence["rootFingerprint"] == prior[2],
                           "SOURCE_AUTHORITY_ROOT_CHANGED")
                    _check(m["issuedAtMs"] > prior[4],
                           "SOURCE_AUTHORITY_CLOCK_ROLLBACK")
                retired = db.execute("""SELECT 1 FROM revoked_keys
                    WHERE owner_id=? AND key_id=?""",
                    (owner, evidence["keyId"])).fetchone()
                _check(evidence["revoked"] or retired is None,
                       "SOURCE_AUTHORITY_REVOKED_KEY_REUSED")
                if prior and prior[3] != evidence["keyId"]:
                    # Rotation retires the old key permanently.
                    db.execute("""INSERT OR IGNORE INTO revoked_keys
                        (owner_id,key_id) VALUES(?,?)""",
                        (owner, prior[3]))
                if evidence["revoked"]:
                    db.execute("""INSERT OR IGNORE INTO revoked_keys
                        (owner_id,key_id) VALUES(?,?)""",
                        (owner, evidence["keyId"]))
                db.execute("""INSERT INTO authority_heads
                    (owner_id,generation,manifest_sha256,root_sha256,
                     key_id,issued_ms,revoked)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(owner_id) DO UPDATE SET
                      generation=excluded.generation,
                      manifest_sha256=excluded.manifest_sha256,
                      root_sha256=excluded.root_sha256,
                      key_id=excluded.key_id,
                      issued_ms=excluded.issued_ms,
                      revoked=excluded.revoked""",
                    (owner, evidence["generation"],
                     evidence["manifestSha256"], evidence["rootFingerprint"],
                     evidence["keyId"], m["issuedAtMs"],
                     int(evidence["revoked"])))
                db.commit()
            except TrustHistoryError:
                db.rollback()
                raise
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise TrustHistoryError("SOURCE_TRUST_WRITE_FAILED") from exc
        return {"state": "TEST_AUTHORITY_ENROLLED_DENY_ONLY",
                "ownerId": owner, "generation": evidence["generation"],
                "manifestSha256": evidence["manifestSha256"],
                "productionAllowed": False}

    def consume_under_current_policy(self, authority, proof):
        """Check current generation + nonce together in a single test txn."""
        required = ("ownerId", "keyId", "generation", "manifestSha256",
                    "rootFingerprint", "revoked")
        _check(type(authority) is dict
               and all(x in authority for x in required)
               and type(proof) is dict
               and proof.get("state") == "TEST_SIGNATURE_VALID_DENY_ONLY"
               and proof.get("signatureVerified") is True
               and proof.get("captureAllowed") is False,
               "SOURCE_TRUST_EVIDENCE_INVALID")
        owner, key = authority["ownerId"], authority["keyId"]
        digest = proof.get("proofSha256")
        nonce = proof.get("nonce")
        _check(type(owner) is str and ID.fullmatch(owner)
               and type(key) is str and ID.fullmatch(key)
               and type(nonce) is str and NONCE.fullmatch(nonce)
               and type(digest) is str and SHA.fullmatch(digest)
               and proof.get("ownerId") == owner
               and proof.get("keyId") == key
               and type(authority["generation"]) is int
               and type(authority["manifestSha256"]) is str
               and SHA.fullmatch(authority["manifestSha256"]),
               "SOURCE_TRUST_EVIDENCE_INVALID")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                head = db.execute("""SELECT generation,manifest_sha256,
                    root_sha256,key_id,revoked FROM authority_heads
                    WHERE owner_id=?""", (owner,)).fetchone()
                _check(head is not None, "SOURCE_TRUST_NOT_ENROLLED")
                _check(head == (
                    authority["generation"], authority["manifestSha256"],
                    authority["rootFingerprint"], key, 0),
                    "SOURCE_AUTHORITY_STALE_OR_REVOKED")
                retired = db.execute("""SELECT 1 FROM revoked_keys
                    WHERE owner_id=? AND key_id=?""", (owner,key)).fetchone()
                _check(retired is None, "SOURCE_AUTHORITY_REVOKED_KEY_REUSED")
                db.execute("""INSERT INTO consumed
                    (owner_id,key_id,nonce,proof_sha256,authority_sha256)
                    VALUES(?,?,?,?,?)""",
                    (owner,key,nonce,digest,authority["manifestSha256"]))
                db.commit()
            except TrustHistoryError:
                db.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise TrustHistoryError("SOURCE_NONCE_ALREADY_CONSUMED") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise TrustHistoryError("SOURCE_TRUST_WRITE_FAILED") from exc
        return {"state":"TEST_AUTHORIZED_NONCE_CONSUMED_DENY_ONLY",
                "productionAllowed": False}

    def admit_test_copy(self, authority, proof, payload, *,
                        resource_id, source_revision, source_captured_ms,
                        payload_sha256, on_stage=None):
        """Atomically consume a fixture nonce and insert a synthetic copy.

        on_stage supports injected exception and abrupt-process-exit tests.
        This never writes ArchiveStore, original sources or Quickshell data.
        Signature verification is required by the test-only caller.
        """
        _check(type(authority) is dict and type(proof) is dict
               and proof.get("state") == "TEST_SIGNATURE_VALID_DENY_ONLY"
               and proof.get("signatureVerified") is True
               and proof.get("captureAllowed") is False
               and authority.get("revoked") is False,
               "SOURCE_TRUST_EVIDENCE_INVALID")
        owner, key = authority.get("ownerId"), authority.get("keyId")
        digest, nonce = proof.get("proofSha256"), proof.get("nonce")
        _check(type(owner) is str and ID.fullmatch(owner)
               and type(key) is str and ID.fullmatch(key)
               and proof.get("ownerId") == owner
               and proof.get("keyId") == key
               and type(nonce) is str and NONCE.fullmatch(nonce)
               and type(digest) is str and SHA.fullmatch(digest)
               and type(authority.get("manifestSha256")) is str
               and SHA.fullmatch(authority["manifestSha256"])
               and type(authority.get("rootFingerprint")) is str
               and SHA.fullmatch(authority["rootFingerprint"])
               and type(authority.get("generation")) is int
               and authority["generation"] >= 1
               and type(resource_id) is str and ID.fullmatch(resource_id)
               and proof.get("resourceId") == resource_id
               and type(source_revision) is str and SHA.fullmatch(source_revision)
               and type(payload_sha256) is str and SHA.fullmatch(payload_sha256)
               and type(source_captured_ms) is int and source_captured_ms > 0
               and type(payload) is bytes and 0 < len(payload) <= 8 * 1024 * 1024
               and hashlib.sha256(payload).hexdigest() == payload_sha256,
               "TEST_COPY_SOURCE_INVALID")
        _check(on_stage is None or callable(on_stage),
               "TEST_CRASH_HOOK_INVALID")
        sid = uuid4().hex
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                head = db.execute("""SELECT generation,manifest_sha256,
                    root_sha256,key_id,revoked FROM authority_heads
                    WHERE owner_id=?""", (owner,)).fetchone()
                _check(head is not None, "SOURCE_TRUST_NOT_ENROLLED")
                _check(head == (
                    authority["generation"], authority["manifestSha256"],
                    authority["rootFingerprint"], key, 0),
                    "SOURCE_AUTHORITY_STALE_OR_REVOKED")
                retired = db.execute("""SELECT 1 FROM revoked_keys
                    WHERE owner_id=? AND key_id=?""", (owner,key)).fetchone()
                _check(retired is None, "SOURCE_AUTHORITY_REVOKED_KEY_REUSED")
                db.execute("""INSERT INTO consumed
                    (owner_id,key_id,nonce,proof_sha256,authority_sha256)
                    VALUES(?,?,?,?,?)""",
                    (owner,key,nonce,digest,authority["manifestSha256"]))
                if on_stage is not None:
                    on_stage("after_nonce")
                db.execute("""INSERT INTO test_copies
                    (snapshot_id,owner_id,key_id,nonce,proof_sha256,
                     authority_sha256,resource_id,source_revision,
                     source_captured_ms,payload_sha256,payload)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid,owner,key,nonce,digest,authority["manifestSha256"],
                     resource_id,source_revision,source_captured_ms,
                     payload_sha256,payload))
                if on_stage is not None:
                    on_stage("after_copy")
                db.commit()
                if on_stage is not None:
                    on_stage("after_commit")
            except TrustHistoryError:
                db.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise TrustHistoryError("SOURCE_NONCE_ALREADY_CONSUMED") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise TrustHistoryError("TEST_COPY_WRITE_FAILED") from exc
            except BaseException:
                db.rollback()
                raise
        return {"state": "TEST_ATOMIC_COPY_COMMITTED_DENY_ONLY",
                "snapshotId": sid, "ownerId": owner, "resourceId": resource_id,
                "payloadSha256": payload_sha256,
                "proofSha256": digest, "nonce": nonce,
                "authoritySha256": authority["manifestSha256"],
                "captureAllowed": False, "productionAllowed": False,
                "restoreAllowed": False, "burnAllowed": False}

    def inspect_test_admission(self, owner, key, nonce):
        """Verify committed fixture bytes without returning payload content."""
        _check(type(owner) is str and ID.fullmatch(owner)
               and type(key) is str and ID.fullmatch(key)
               and type(nonce) is str and NONCE.fullmatch(nonce),
               "TEST_ADMISSION_IDENTITY_INVALID")
        with closing(self._connect_readonly()) as db:
            row = db.execute("""SELECT c.proof_sha256,c.authority_sha256,
                s.snapshot_id,s.proof_sha256,s.authority_sha256,
                s.payload_sha256,s.resource_id,s.source_revision,s.payload
                FROM consumed c LEFT JOIN test_copies s
                  ON s.owner_id=c.owner_id AND s.key_id=c.key_id
                  AND s.nonce=c.nonce
                WHERE c.owner_id=? AND c.key_id=? AND c.nonce=?""",
                (owner,key,nonce)).fetchone()
        if row is None:
            return {"state":"TEST_NOT_ADMITTED",
                    "productionAllowed":False}
        if row[2] is None:
            # Can be an older V2l nonce; it is NOT an archived snapshot.
            return {"state":"TEST_NONCE_WITHOUT_COPY",
                    "productionAllowed":False}
        _check(row[0] == row[3] and row[1] == row[4]
               and type(row[2]) is str and len(row[2]) == 32
               and type(row[5]) is str and SHA.fullmatch(row[5])
               and type(row[8]) is bytes
               and hashlib.sha256(row[8]).hexdigest() == row[5],
               "TEST_ADMISSION_INTEGRITY_INVALID")
        return {"state":"TEST_COPY_COMMITTED",
                "snapshotId":row[2], "ownerId":owner,
                "resourceId":row[6], "sourceRevision":row[7],
                "proofSha256":row[0], "authoritySha256":row[1],
                "payloadSha256":row[5],
                "payloadIntegrityVerified":True,
                "productionAllowed":False}

    def test_copy_status(self, owner):
        """Read-only counts, never return even synthetic payload."""
        _check(type(owner) is str and ID.fullmatch(owner),
               "SOURCE_TRUST_OWNER_INVALID")
        with closing(self._connect_readonly()) as db:
            counts = db.execute("""SELECT
                (SELECT count(*) FROM test_copies WHERE owner_id=?),
                (SELECT count(*) FROM consumed WHERE owner_id=?)
                """, (owner,owner)).fetchone()
            _check(counts[0] <= counts[1],
                   "TEST_ADMISSION_INTEGRITY_INVALID")
        return {"testCopies": counts[0], "consumedNonces": counts[1],
                "productionAllowed": False}

    def status(self, owner):
        _check(type(owner) is str and ID.fullmatch(owner),
               "SOURCE_TRUST_OWNER_INVALID")
        with closing(self._connect()) as db:
            head = db.execute("""SELECT generation,manifest_sha256,key_id,
                revoked FROM authority_heads WHERE owner_id=?""",
                (owner,)).fetchone()
            num = db.execute("""SELECT count(*) FROM consumed
                WHERE owner_id=?""", (owner,)).fetchone()[0]
        return {"generation": head[0] if head else 0,
                "manifestSha256": head[1] if head else "",
                "keyId": head[2] if head else "",
                "revoked": bool(head[3]) if head else False,
                "consumedNonces": num, "productionAllowed": False}
