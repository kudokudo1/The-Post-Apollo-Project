#!/usr/bin/env python3
"""Clock BG1-B2B5: fixture-only signed old-writer release challenge/receipt.

An *actual* AF_UNIX peer and independently pinned, purpose-scoped Ed25519
release/old-writer keys are required. However, this verifier does NOT stop
the peer's writes, authorize a real alarm owner, or issue a release ack.

The real Quickshell alarm file is never opened for writing, and the feature
requires disposable synthetic file paths. No CLI, broker hook, or UI entry.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _sibling(name):
    path = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("b2b5_" + name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing bundled Clock component: " + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Peer = _sibling("AlarmPeerIdentity")
Observer = _sibling("AlarmBackgroundObserver")
POLICY_SCHEMA = "postapollo.clock.bg1-b2b5-synthetic-writer-enrollment.v1"
POLICY_PURPOSE = "postapollo.clock.synthetic-writer-release.observe-only"
RELEASE_SCHEMA = "postapollo.clock.bg1-b2b5-synthetic-release-receipt.v1"
AUTH_DOMAIN = b"postapollo.clock.bg1-b2b5-synthetic-enrollment.v1\x00"
RELEASE_DOMAIN = b"postapollo.clock.bg1-b2b5-synthetic-release.v1\x00"
POLICY_KEYS = frozenset(("schema", "purpose", "role",
    "releaseEpoch", "releaseSequence", "sourceScope", "interpreterPath",
    "oldSignerSha256", "uid", "gid"))
RECEIPT_KEYS = frozenset(("schema", "challenge", "sourceDigest",
    "oldEpoch", "newEpoch", "peerPid", "peerStartTicks"))
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_FRAME = 3072
MAX_CHALLENGES = 32
CHALLENGE_TTL_MS = 5000


class Refused(ValueError):
    """Stable code, with no alarm titles, notes, paths or credentials."""


def _json_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, TypeError, RecursionError) as exc:
        raise Refused("UNSERIALIZABLE_MESSAGE") from exc


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Refused("DUPLICATE_SIGNED_FIELD")
        out[key] = value
    return out


def _parse(raw, expected_keys):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_FRAME:
        raise Refused("SIGNED_FRAME_INVALID")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               Refused("INVALID_NUMBER")))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Refused("SIGNED_FRAME_INVALID") from exc
    if type(value) is not dict or set(value) != expected_keys:
        raise Refused("SIGNED_FIELDS_INVALID")
    if _json_bytes(value) != raw:
        raise Refused("NONCANONICAL_SIGNED_MESSAGE")
    return value


def _integer(n, lo=0, hi=2147483647):
    return type(n) is int and lo <= n <= hi


def _source_scope(source):
    return hashlib.sha256((str(os.getuid()) + "\n" +
        str(source.parent.resolve(strict=True) / source.name)).encode()).hexdigest()


def _safe_read_source(source):
    if source.is_symlink():
        raise Refused("SOURCE_LINK_REFUSED")
    fd = None
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        old = os.fstat(fd)
        if (not stat.S_ISREG(old.st_mode) or old.st_uid != os.getuid()
                or old.st_nlink != 1 or stat.S_IMODE(old.st_mode) != 0o600
                or not 0 < old.st_size <= MAX_SOURCE_BYTES):
            raise Refused("SOURCE_RECORD_UNSAFE")
        raw = os.read(fd, MAX_SOURCE_BYTES + 1)
        new = os.fstat(fd)
        if (len(raw) != old.st_size or
                (old.st_dev, old.st_ino, old.st_size, old.st_mtime_ns,
                 old.st_ctime_ns) !=
                (new.st_dev, new.st_ino, new.st_size, new.st_mtime_ns,
                 new.st_ctime_ns)):
            raise Refused("SOURCE_CHANGED_WHILE_READ")
    except OSError as exc:
        raise Refused("SOURCE_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)
    try:
        document = json.loads(raw)
        Observer.validate_snapshot(document)
    except (UnicodeError, ValueError, TypeError, Observer.Refused) as exc:
        raise Refused("INVALID_SAVED_ALARM_DOCUMENT") from exc
    return hashlib.sha256(raw).hexdigest()


def _public_digest(key):
    raw = key.public_bytes(encoding=serialization.Encoding.Raw,
                           format=serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def _policy(raw):
    result = _parse(raw, POLICY_KEYS)
    if (result["schema"] != POLICY_SCHEMA
            or result["purpose"] != POLICY_PURPOSE
            or result["role"] != "clock-ui-bridge"
            or not _integer(result["releaseEpoch"], 1)
            or not _integer(result["releaseSequence"], 1)
            or not _integer(result["uid"], 0, 2**32 - 1)
            or not _integer(result["gid"], 0, 2**32 - 1)
            or type(result["sourceScope"]) is not str
            or not HEX.fullmatch(result["sourceScope"])
            or type(result["oldSignerSha256"]) is not str
            or not HEX.fullmatch(result["oldSignerSha256"])
            or type(result["interpreterPath"]) is not str
            or not result["interpreterPath"].startswith("/")
            or "//" in result["interpreterPath"]
            or "\x00" in result["interpreterPath"]
            or "/../" in result["interpreterPath"]
            or "/./" in result["interpreterPath"]):
        raise Refused("WRONG_SIGNED_CLOCK_RELEASE_POLICY")
    return result


class SignedWriterReleaseFixture:
    """Only confirms a signed test receipt; has no real release capability."""

    def __init__(self, fixture_dir, alarm_file, *,
                 signed_policy, policy_signature,
                 independent_authority: Ed25519PublicKey,
                 independent_old_signer: Ed25519PublicKey,
                 expected_peer_pid, expected_peer_ticks,
                 minimum_epoch, minimum_sequence,
                 synthetic_only=False, clock=None):
        self.root = Path(fixture_dir)
        self.source = Path(alarm_file)
        if (synthetic_only is not True
                or not self.root.is_absolute()
                or self.root.name != "bg1-signed-release-fixture"
                or not self.source.is_absolute()
                or self.source.name != "time-alarms-v2.json"
                or self.source.parent.name != "synthetic-quickshell"
                or self.root.parent != self.source.parent.parent):
            raise Refused("DISPOSABLE_FIXTURE_REQUIRED")
        for path in (self.root, self.source.parent):
            if path.is_symlink():
                raise Refused("FIXTURE_PATH_UNSAFE")
            try:
                st = path.stat()
            except OSError as exc:
                raise Refused("FIXTURE_DIRECTORY_UNAVAILABLE") from exc
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o700):
                raise Refused("FIXTURE_PATH_UNSAFE")
        if (not isinstance(independent_authority, Ed25519PublicKey)
                or not isinstance(independent_old_signer, Ed25519PublicKey)
                or type(policy_signature) is not bytes
                or len(policy_signature) != 64
                or not _integer(expected_peer_pid, 2)
                or not _integer(expected_peer_ticks, 1, 2**64 - 1)
                or not _integer(minimum_epoch, 1)
                or not _integer(minimum_sequence, 1)):
            raise Refused("INDEPENDENT_TRUST_PINS_REQUIRED")
        policy = _policy(signed_policy)
        if ((policy["releaseEpoch"], policy["releaseSequence"]) <
                (minimum_epoch, minimum_sequence)):
            raise Refused("RELEASE_FLOOR_ROLLBACK")
        try:
            independent_authority.verify(policy_signature,
                                         AUTH_DOMAIN + signed_policy)
        except InvalidSignature as exc:
            raise Refused("UNTRUSTED_CLOCK_RELEASE_ISSUER") from exc
        if (policy["oldSignerSha256"] != _public_digest(independent_old_signer)
                or policy["sourceScope"] != _source_scope(self.source)):
            raise Refused("SIGNED_ENROLLMENT_SCOPE_MISMATCH")
        self.policy = policy
        self.signer = independent_old_signer
        self.expected_pid = expected_peer_pid
        self.expected_ticks = expected_peer_ticks
        self.database = self.root / "signed-release-replay-v1.sqlite3"
        self.clock = clock if clock is not None else lambda: int(time.time()*1000)

    def _verify_peer(self, connection, witness):
        if (not isinstance(witness, dict)
                or witness.get("pid") != self.expected_pid
                or witness.get("ticks") != self.expected_ticks
                or witness.get("uid") != self.policy["uid"]
                or witness.get("gid") != self.policy["gid"]):
            raise Refused("UNENROLLED_PROCESS_WITNESS")
        try:
            Peer.verify(connection, witness, self.policy["interpreterPath"])
        except Peer.Refused as exc:
            raise Refused("KERNEL_PEER_OR_EXECUTABLE_CHANGED") from exc

    def _db(self):
        if self.database.is_symlink():
            raise Refused("UNSAFE_REPLAY_DATABASE")
        try:
            fd = os.open(self.database,
                         os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600)
            try:
                st = os.fstat(fd)
                if (not stat.S_ISREG(st.st_mode)
                        or st.st_uid != os.getuid()
                        or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600):
                    raise Refused("UNSAFE_REPLAY_DATABASE")
            finally:
                os.close(fd)
            conn = sqlite3.connect(self.database, isolation_level=None,
                                   timeout=3)
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA busy_timeout=3000")
            conn.execute("CREATE TABLE IF NOT EXISTS challenges("
                         "digest TEXT PRIMARY KEY, source_digest TEXT NOT NULL,"
                         "old_epoch INTEGER NOT NULL, new_epoch INTEGER NOT NULL,"
                         "peer_pid INTEGER NOT NULL, peer_ticks INTEGER NOT NULL,"
                         "issued_at INTEGER NOT NULL, state TEXT NOT NULL"
                         " CHECK(state IN ('issued','consumed')))")
            return conn
        except (OSError, sqlite3.Error) as exc:
            raise Refused("REPLAY_LEDGER_UNAVAILABLE") from exc

    def issue(self, connection, witness, *, expected_source_digest,
              old_epoch, new_epoch):
        self._verify_peer(connection, witness)
        if (type(expected_source_digest) is not str
                or not HEX.fullmatch(expected_source_digest)
                or not _integer(old_epoch, 1)
                or not _integer(new_epoch, 1)
                or new_epoch <= old_epoch):
            raise Refused("INVALID_RELEASE_REQUEST")
        if _safe_read_source(self.source) != expected_source_digest:
            raise Refused("SOURCE_REVISION_MISMATCH")
        now = self.clock()
        if not _integer(now, 1, 8640000000000000):
            raise Refused("UNTRUSTED_CLOCK_SAMPLE")
        challenge = secrets.token_hex(32)
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
            if count >= MAX_CHALLENGES:
                raise Refused("REPLAY_LEDGER_CAPACITY")
            db.execute("INSERT INTO challenges VALUES(?,?,?,?,?,?,?,?)",
                       (hashlib.sha256(challenge.encode()).hexdigest(),
                        expected_source_digest, old_epoch, new_epoch,
                        self.expected_pid, self.expected_ticks, now, "issued"))
            if _safe_read_source(self.source) != expected_source_digest:
                raise Refused("SOURCE_CHANGED_DURING_CHALLENGE")
            self._verify_peer(connection, witness)
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return {"challenge": challenge,
                "sourceDigest": expected_source_digest,
                "oldEpoch": old_epoch, "newEpoch": new_epoch,
                "writerStopped": False, "releaseAcknowledged": False,
                "canTransferOwnership": False, "canRing": False}

    def observe_signed_reply(self, connection, witness, *,
                             signed_reply, signature):
        self._verify_peer(connection, witness)
        data = _parse(signed_reply, RECEIPT_KEYS)
        if (data["schema"] != RELEASE_SCHEMA
                or type(data["challenge"]) is not str
                or not HEX.fullmatch(data["challenge"])
                or type(data["sourceDigest"]) is not str
                or not HEX.fullmatch(data["sourceDigest"])
                or not _integer(data["oldEpoch"], 1)
                or not _integer(data["newEpoch"], 1)
                or not _integer(data["peerPid"], 2)
                or not _integer(data["peerStartTicks"], 1, 2**64-1)
                or type(signature) is not bytes or len(signature) != 64):
            raise Refused("INVALID_SIGNED_RELEASE_REPLY")
        if (data["peerPid"] != self.expected_pid
                or data["peerStartTicks"] != self.expected_ticks):
            raise Refused("RELEASE_PEER_NOT_ENROLLED")
        try:
            self.signer.verify(signature, RELEASE_DOMAIN + signed_reply)
        except InvalidSignature as exc:
            raise Refused("UNTRUSTED_OLD_WRITER_SIGNATURE") from exc
        digest = hashlib.sha256(data["challenge"].encode()).hexdigest()
        now = self.clock()
        if not _integer(now, 1, 8640000000000000):
            raise Refused("UNTRUSTED_CLOCK_SAMPLE")
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT source_digest,old_epoch,new_epoch,"
                             "peer_pid,peer_ticks,issued_at,state "
                             "FROM challenges WHERE digest=?", (digest,)).fetchone()
            if row is None or row[-1] != "issued":
                raise Refused("RELEASE_CHALLENGE_REPLAY_OR_MISSING")
            if (row[:5] != (data["sourceDigest"], data["oldEpoch"],
                            data["newEpoch"], self.expected_pid,
                            self.expected_ticks)
                    or now < row[5] or now > row[5] + CHALLENGE_TTL_MS):
                raise Refused("STALE_OR_MISMATCHED_RELEASE_CHALLENGE")
            if _safe_read_source(self.source) != data["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_BEFORE_RELEASE_OBSERVATION")
            self._verify_peer(connection, witness)
            updated = db.execute(
                "UPDATE challenges SET state='consumed' "
                "WHERE digest=? AND state='issued'", (digest,)).rowcount
            if updated != 1:
                raise Refused("RELEASE_CHALLENGE_REPLAY_OR_MISSING")
            db.execute("COMMIT")
            return {"signatureObserved": True,
                    "independentlyPinnedSignerMatched": True,
                    "peerProcessMatched": True,
                    "writerStopped": False, "releaseAcknowledged": False,
                    "canTransferOwnership": False,
                    "ownsRealAlarmFile": False,
                    "canRing": False, "canNotify": False}
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
