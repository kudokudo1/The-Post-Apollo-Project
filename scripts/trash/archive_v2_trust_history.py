#!/usr/bin/env python3
"""V2l TEST-ONLY protected owner trust history and replay state.

Private SQLite with monotonic authority generation and sticky key revocations.
This is not a runtime authority service, does not handle production trust
roots, and cannot authorize ArchiveStore, Restore or Burn.
"""
from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import stat

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
