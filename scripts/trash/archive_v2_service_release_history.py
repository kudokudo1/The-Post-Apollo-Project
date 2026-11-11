#!/usr/bin/env python3
"""V2s authority-signed release sequence, test-only durable revocation floor.

Every signing root is an EXTERNALLY_PINNED_TEST_ROOT fixture. This is NOT a
production authority ledger, systemd trust source, authenticated time source,
service enrollment, ArchiveStore admission or signer. It creates only a
private synthetic SQLite ledger at an explicitly supplied 0700 test root.
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

from scripts.trash.archive_v2_owner_trust import ROOT_FIELDS, ROOT_ORIGIN
from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, Ed25519PublicKey, InvalidSignature,
    KEY_ID, SHA,
)

SCHEMA = "post-apollo.trashpp.fixture-service-release.v2s"
FILE_NAME = "trashpp-v2s-test-release-history.sqlite3"
FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "rootKeyId",
    "ownerId", "sequence", "grantSha256", "previousReleaseSha256",
    "issuedAtMs", "validFromMs", "validUntilMs", "revoked",
))
ENVELOPE = frozenset(("release", "signatureB64"))
MAX_VALIDITY_MS = 24 * 60 * 60 * 1000


class ServiceReleaseError(Exception):
    """Fixed refusal codes, no sensitive host paths or private bytes."""


def _need(ok, code):
    if not ok:
        raise ServiceReleaseError(code)


def _ms(v):
    return type(v) is int and 1 <= v <= 9999999999999


def canonical_release(release):
    _need(type(release) is dict and set(release) == FIELDS,
          "RELEASE_SCHEMA_INVALID")
    _need(release["schema"] == SCHEMA
          and release["audience"] == AUDIENCE
          and release["purpose"] == PURPOSE
          and release["policyOrigin"] == "TEST_FIXTURE_ONLY",
          "RELEASE_SCOPE_INVALID")
    _need(type(release["ownerId"]) is str
          and release["ownerId"] in ALLOWED_OWNERS
          and type(release["rootKeyId"]) is str
          and KEY_ID.fullmatch(release["rootKeyId"])
          and type(release["grantSha256"]) is str
          and SHA.fullmatch(release["grantSha256"])
          and type(release["sequence"]) is int
          and 1 <= release["sequence"] <= 1000000000
          and type(release["revoked"]) is bool,
          "RELEASE_FIELDS_INVALID")
    predecessor = release["previousReleaseSha256"]
    _need(type(predecessor) is str
          and (predecessor == "" if release["sequence"] == 1
               else SHA.fullmatch(predecessor) is not None),
          "RELEASE_LINEAGE_INVALID")
    _need(all(_ms(release[field]) for field in (
          "issuedAtMs", "validFromMs", "validUntilMs"))
          and release["validFromMs"] <= release["issuedAtMs"]
              < release["validUntilMs"]
          and release["validUntilMs"] - release["validFromMs"]
              <= MAX_VALIDITY_MS,
          "RELEASE_TIME_INVALID")
    raw = json.dumps(release, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _need(len(raw) <= 2048, "RELEASE_TOO_LARGE")
    return raw


def verify_fixture_release(envelope, pinned_root, *, now_ms):
    _need(type(envelope) is dict and set(envelope) == ENVELOPE,
          "RELEASE_ENVELOPE_INVALID")
    _need(type(pinned_root) is dict and set(pinned_root) == ROOT_FIELDS
          and pinned_root["origin"] == ROOT_ORIGIN,
          "RELEASE_TRUST_NOT_PROVISIONED")
    release = envelope["release"]
    raw = canonical_release(release)
    _need(type(pinned_root["rootKeyId"]) is str
          and pinned_root["rootKeyId"] == release["rootKeyId"]
          and type(pinned_root["publicKeyBytes"]) is bytes
          and len(pinned_root["publicKeyBytes"]) == 32,
          "RELEASE_ROOT_MISMATCH")
    _need(_ms(now_ms) and release["issuedAtMs"] <= now_ms + 30000
          and release["validFromMs"] <= now_ms < release["validUntilMs"],
          "RELEASE_EXPIRED")
    encoded = envelope["signatureB64"]
    _need(type(encoded) is str and len(encoded) == 88,
          "RELEASE_SIGNATURE_INVALID")
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ServiceReleaseError("RELEASE_SIGNATURE_INVALID") from exc
    _need(len(signature) == 64
          and base64.b64encode(signature).decode("ascii") == encoded,
          "RELEASE_SIGNATURE_INVALID")
    _need(Ed25519PublicKey is not None, "RELEASE_CRYPTO_UNAVAILABLE")
    try:
        Ed25519PublicKey.from_public_bytes(
            pinned_root["publicKeyBytes"]).verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise ServiceReleaseError("RELEASE_SIGNATURE_REFUSED") from exc
    return {
        "state": "TEST_RELEASE_SIGNATURE_VALID_DENY_ONLY",
        "ownerId": release["ownerId"],
        "sequence": release["sequence"],
        "grantSha256": release["grantSha256"],
        "releaseSha256": hashlib.sha256(raw).hexdigest(),
        "previousReleaseSha256": release["previousReleaseSha256"],
        "rootSha256": hashlib.sha256(
            pinned_root["publicKeyBytes"]).hexdigest(),
        "issuedAtMs": release["issuedAtMs"],
        "revoked": release["revoked"],
        "signatureVerified": True,
        "sourceAuthorityVerified": False,
        "captureAllowed": False,
        "productionAllowed": False,
    }


def _file_safe(path, *, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        _need(allow_missing, "RELEASE_HISTORY_MISSING")
        return False
    except OSError as exc:
        raise ServiceReleaseError("RELEASE_HISTORY_UNAVAILABLE") from exc
    _need(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid()
          and st.st_nlink == 1 and st.st_mode & 0o077 == 0,
          "RELEASE_HISTORY_UNSAFE")
    return True


class TestServiceReleaseHistory:
    """Separate test-only authority release high-water mark and retirements."""

    def __init__(self, private_root):
        _need(isinstance(private_root, (str, Path)),
              "RELEASE_ROOT_INVALID")
        root = Path(private_root)
        _need(root.is_absolute() and ".." not in root.parts
              and len(str(root)) <= 4096,
              "RELEASE_ROOT_INVALID")
        try:
            st = root.lstat()
        except OSError as exc:
            raise ServiceReleaseError("RELEASE_ROOT_UNAVAILABLE") from exc
        _need(stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid()
              and st.st_mode & 0o077 == 0,
              "RELEASE_ROOT_UNSAFE")
        self.root = root
        self.path = root / FILE_NAME
        if not _file_safe(self.path, allow_missing=True):
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            except FileExistsError:
                _file_safe(self.path)
            except OSError as exc:
                raise ServiceReleaseError("RELEASE_HISTORY_CREATE_FAILED") from exc
        with closing(self._connect()) as db:
            try:
                with db:
                    db.execute("""CREATE TABLE IF NOT EXISTS release_heads(
                        owner_id TEXT PRIMARY KEY,
                        sequence INTEGER NOT NULL,
                        release_sha256 TEXT NOT NULL,
                        grant_sha256 TEXT NOT NULL,
                        root_sha256 TEXT NOT NULL,
                        issued_ms INTEGER NOT NULL,
                        revoked INTEGER NOT NULL CHECK(revoked IN (0,1))
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS retired_grants(
                        owner_id TEXT NOT NULL,
                        grant_sha256 TEXT NOT NULL,
                        PRIMARY KEY(owner_id,grant_sha256)
                    )""")
            except sqlite3.DatabaseError as exc:
                raise ServiceReleaseError("RELEASE_HISTORY_INIT_FAILED") from exc

    def _guard(self):
        st = self.root.lstat()
        _need(stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid()
              and st.st_mode & 0o077 == 0,
              "RELEASE_ROOT_UNSAFE")
        _file_safe(self.path)
        for suffix in ("-wal", "-shm"):
            try:
                (self.root / (FILE_NAME + suffix)).lstat()
            except FileNotFoundError:
                continue
            raise ServiceReleaseError("RELEASE_UNEXPECTED_SIDECAR")

    def _connect(self, *, readonly=False):
        self._guard()
        try:
            if readonly:
                uri = ("file:" + quote(str(self.path), safe="/")
                       + "?mode=ro&cache=private")
                db = sqlite3.connect(uri, timeout=5, uri=True)
                db.execute("PRAGMA query_only=ON")
            else:
                db = sqlite3.connect(str(self.path), timeout=5)
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=5000")
            return db
        except sqlite3.DatabaseError as exc:
            raise ServiceReleaseError("RELEASE_HISTORY_UNAVAILABLE") from exc

    def enroll(self, signed_release, pinned_root, *, now_ms):
        """Require a valid authority signature and contiguous release history."""
        verified = verify_fixture_release(
            signed_release, pinned_root, now_ms=now_ms)
        owner, grant = verified["ownerId"], verified["grantSha256"]
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                head = db.execute("""SELECT sequence,release_sha256,
                    grant_sha256,root_sha256,issued_ms,revoked FROM release_heads
                    WHERE owner_id=?""", (owner,)).fetchone()
                if head is None:
                    _need(verified["sequence"] == 1
                          and verified["previousReleaseSha256"] == "",
                          "RELEASE_GENESIS_REQUIRED")
                else:
                    _need(verified["sequence"] == head[0] + 1,
                          "RELEASE_SEQUENCE_ROLLBACK")
                    _need(verified["previousReleaseSha256"] == head[1],
                          "RELEASE_PREDECESSOR_MISMATCH")
                    _need(verified["rootSha256"] == head[3],
                          "RELEASE_ROOT_CHANGED")
                    _need(verified["issuedAtMs"] > head[4],
                          "RELEASE_ISSUANCE_ROLLBACK")
                retired = db.execute("""SELECT 1 FROM retired_grants
                    WHERE owner_id=? AND grant_sha256=?""",
                    (owner, grant)).fetchone()
                _need(retired is None, "RELEASE_GRANT_RETIRED")
                if head and head[2] != grant:
                    db.execute("""INSERT OR IGNORE INTO retired_grants
                        (owner_id,grant_sha256) VALUES(?,?)""",
                        (owner,head[2]))
                if verified["revoked"]:
                    db.execute("""INSERT OR IGNORE INTO retired_grants
                        (owner_id,grant_sha256) VALUES(?,?)""",
                        (owner,grant))
                db.execute("""INSERT INTO release_heads
                    (owner_id,sequence,release_sha256,grant_sha256,
                     root_sha256,issued_ms,revoked) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(owner_id) DO UPDATE SET
                        sequence=excluded.sequence,
                        release_sha256=excluded.release_sha256,
                        grant_sha256=excluded.grant_sha256,
                        root_sha256=excluded.root_sha256,
                        issued_ms=excluded.issued_ms,
                        revoked=excluded.revoked""",
                    (owner, verified["sequence"], verified["releaseSha256"],
                     grant, verified["rootSha256"], verified["issuedAtMs"],
                     int(verified["revoked"])))
                db.commit()
            except ServiceReleaseError:
                db.rollback()
                raise
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise ServiceReleaseError("RELEASE_HISTORY_WRITE_FAILED") from exc
        return {"state":"TEST_RELEASE_ENROLLED_DENY_ONLY",
                "sequence":verified["sequence"],"ownerId":owner,
                "releaseSha256":verified["releaseSha256"],
                "productionAllowed":False}

    def require_current(self, signed_release, pinned_root, *, owner_id,
                        grant_sha256, now_ms):
        """Read-only high-water check; stale or revoked release always denies."""
        verified = verify_fixture_release(
            signed_release, pinned_root, now_ms=now_ms)
        _need(type(owner_id) is str and owner_id in ALLOWED_OWNERS
              and type(grant_sha256) is str and SHA.fullmatch(grant_sha256)
              and verified["ownerId"] == owner_id
              and verified["grantSha256"] == grant_sha256,
              "RELEASE_GRANT_BINDING_MISMATCH")
        with closing(self._connect(readonly=True)) as db:
            head = db.execute("""SELECT sequence,release_sha256,
                grant_sha256,root_sha256,issued_ms,revoked FROM release_heads
                WHERE owner_id=?""", (owner_id,)).fetchone()
            retired = db.execute("""SELECT 1 FROM retired_grants
                WHERE owner_id=? AND grant_sha256=?""",
                (owner_id,grant_sha256)).fetchone()
        _need(head is not None, "RELEASE_NOT_ENROLLED")
        _need(head == (verified["sequence"],verified["releaseSha256"],
                       verified["grantSha256"],verified["rootSha256"],
                       verified["issuedAtMs"],int(verified["revoked"])),
              "RELEASE_STALE_OR_CHANGED")
        _need(not verified["revoked"] and retired is None,
              "RELEASE_REVOKED")
        return {"state":"TEST_RELEASE_CURRENT_DENY_ONLY",
                "ownerId":owner_id,"sequence":verified["sequence"],
                "releaseSha256":verified["releaseSha256"],
                "grantSha256":grant_sha256,
                "captureAllowed":False,"productionAllowed":False}

    def status(self, owner_id):
        _need(type(owner_id) is str and owner_id in ALLOWED_OWNERS,
              "RELEASE_OWNER_INVALID")
        with closing(self._connect(readonly=True)) as db:
            head = db.execute("""SELECT sequence,release_sha256,grant_sha256,
                revoked FROM release_heads WHERE owner_id=?""",
                (owner_id,)).fetchone()
        return {"sequence":head[0] if head else 0,
                "releaseSha256":head[1] if head else "",
                "grantSha256":head[2] if head else "",
                "revoked":bool(head[3]) if head else False,
                "productionAllowed":False}
