#!/usr/bin/env python3
"""C3e-C: CI-only, crash-durable release floor and root pin.

An independent root-signed release is verified using C3e-A on *snapshotted*
bytes, then a single SQLite IMMEDIATE transaction advances policy/release
floors. An explicit external floor is REQUIRED on every call. Ordinary SQLite
files are not tamper-proof and do not replace a hardware/operator trust anchor.

No keys, package install, daemon activation, production grant or network.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from urllib.parse import quote

_spec = importlib.util.spec_from_file_location(
    "c3ec_signed_admission", Path(__file__).with_name("C3eReleaseAdmission.py"))
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3EC_SIGNED_ADMISSION_NOT_PRESENT")
admission = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(admission)

SCHEMA = """CREATE TABLE checkpoint (
    id INTEGER PRIMARY KEY CHECK (id=1),
    release_id TEXT NOT NULL CHECK (release_id='postapollo-connections-status'),
    root_pin TEXT NOT NULL,
    epoch_floor INTEGER NOT NULL CHECK (epoch_floor>=1),
    sequence_floor INTEGER NOT NULL CHECK (sequence_floor>=1),
    policy_digest TEXT NOT NULL,
    artifact_digest TEXT NOT NULL
)"""
COLUMNS = """root_pin, epoch_floor, sequence_floor,
             policy_digest, artifact_digest"""
SUCCESS = "C3EC_TEST_DURABLE_RELEASE_FLOOR_NOT_PRODUCTION_AUTH"
FILE_LIMITS = {
    "root": 100_000,
    "policy": admission.MAX_JSON,
    "policy_sig": 100_000,
    "delegate": 100_000,
    "manifest": admission.MAX_JSON,
    "manifest_sig": 100_000,
    "artifact": admission.MAX_ARTIFACT,
}


class Refused(Exception):
    pass


def _deny(reason: str):
    raise Refused(reason)


def _anchor(pin: str, epoch: int, sequence: int):
    try:
        admission._fingerprint(pin)
        admission._integer(epoch, 1, "INVALID_EPOCH_ANCHOR")
        admission._integer(sequence, 1, "INVALID_SEQUENCE_ANCHOR")
    except admission.Refused:
        _deny("EXTERNAL_ANCHOR_INVALID")


def _db_path(path: Path):
    if not path.is_absolute() or path.is_symlink():
        _deny("INVALID_LEDGER_PATH")
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        _deny("LEDGER_MISSING_REQUIRES_EXPLICIT_BOOTSTRAP")
    except OSError:
        _deny("INVALID_LEDGER_PATH")
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or
            stat.S_IMODE(st.st_mode) & 0o077 or st.st_nlink != 1):
        _deny("UNSAFE_LEDGER_FILE")


def _connect(path: Path):
    _db_path(path)
    try:
        db = sqlite3.connect(
            "file:" + quote(str(path)) + "?mode=rw", uri=True,
            timeout=8, isolation_level=None)
        db.execute("PRAGMA busy_timeout=8000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        return db
    except sqlite3.Error:
        _deny("STORAGE_UNAVAILABLE")


def bootstrap(path: Path, *, trusted_root_pin: str,
              initial_epoch: int, initial_sequence: int):
    """Explicit, one-time *synthetic* trust enrollment (never silent recovery)."""
    _anchor(trusted_root_pin, initial_epoch, initial_sequence)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        _deny("LEDGER_ALREADY_EXISTS_OR_UNSAFE_PATH")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600)
        os.close(fd)
    except OSError:
        _deny("LEDGER_BOOTSTRAP_FAILED")
    db = None
    try:
        db = _connect(path)
        db.execute("BEGIN IMMEDIATE")
        db.execute(SCHEMA)
        db.execute(
            """INSERT INTO checkpoint
               (id, release_id, root_pin, epoch_floor, sequence_floor,
                policy_digest, artifact_digest)
               VALUES (1, ?, ?, ?, ?, '', '')""",
            (admission.RELEASE_ID, trusted_root_pin,
             initial_epoch, initial_sequence))
        db.execute("COMMIT")
    except (sqlite3.Error, Refused):
        if db:
            db.execute("ROLLBACK")
        _deny("LEDGER_BOOTSTRAP_FAILED")
    finally:
        if db:
            db.close()


def _read(db):
    try:
        rows = db.execute("SELECT " + COLUMNS + " FROM checkpoint").fetchall()
    except sqlite3.Error:
        _deny("LEDGER_CORRUPT_OR_UNINITIALIZED")
    if len(rows) != 1:
        _deny("LEDGER_CORRUPT_OR_UNINITIALIZED")
    pin, epoch, seq, policy_hash, artifact_hash = rows[0]
    _anchor(pin, epoch, seq)
    if (not isinstance(policy_hash, str) or
            not isinstance(artifact_hash, str) or
            (policy_hash and not admission.SHA256.fullmatch(policy_hash)) or
            (artifact_hash and not admission.SHA256.fullmatch(artifact_hash))):
        _deny("LEDGER_CORRUPT_OR_UNINITIALIZED")
    return pin, epoch, seq, policy_hash, artifact_hash


def inspect(path: Path) -> tuple[str, int, int, str, str]:
    """Read-only inspection; never create a missing ledger."""
    db = _connect(path)
    try:
        return _read(db)
    finally:
        db.close()


def _stage_one(source: Path, target: Path, size_limit: int):
    """Snapshot a bounded regular file via O_NOFOLLOW before verification."""
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as src:
            before = os.fstat(src.fileno())
            if (not stat.S_ISREG(before.st_mode) or
                    before.st_size < 1 or before.st_size > size_limit):
                _deny("UNSAFE_SNAPSHOT_INPUT")
            written = 0
            with target.open("xb") as dst:
                while True:
                    chunk = src.read(min(65536, size_limit + 1 - written))
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > size_limit:
                        _deny("UNSAFE_SNAPSHOT_INPUT")
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
            after = os.fstat(src.fileno())
            if (written != before.st_size or
                    (before.st_dev, before.st_ino, before.st_mtime_ns,
                     before.st_ctime_ns, before.st_size) !=
                    (after.st_dev, after.st_ino, after.st_mtime_ns,
                     after.st_ctime_ns, after.st_size)):
                _deny("SOURCE_CHANGED_DURING_SNAPSHOT")
    except (OSError, ValueError):
        _deny("UNSAFE_SNAPSHOT_INPUT")


def admit_and_record(db_path: Path, *, external_root_pin: str,
                     external_epoch_floor: int, external_sequence_floor: int,
                     root_public: Path, policy: Path, policy_signature: Path,
                     delegated_public: Path, manifest: Path,
                     manifest_signature: Path, artifact: Path) -> str:
    """Verify a stable candidate snapshot, then commit monotonic floors.

    Independent external trust/freshness inputs are supplied by the caller,
    never accepted from the candidate or automatically inferred from SQLite.
    This function does *not* install or run the verified artifact.
    """
    _anchor(external_root_pin, external_epoch_floor, external_sequence_floor)
    db_path = Path(db_path)
    _db_path(db_path)
    sources = {
        "root": Path(root_public), "policy": Path(policy),
        "policy_sig": Path(policy_signature),
        "delegate": Path(delegated_public), "manifest": Path(manifest),
        "manifest_sig": Path(manifest_signature), "artifact": Path(artifact),
    }
    with tempfile.TemporaryDirectory(prefix="c3ec-verified-snapshot-") as work:
        folder = Path(work)
        copied = {}
        for name, src in sources.items():
            copied[name] = folder / name
            _stage_one(src, copied[name], FILE_LIMITS[name])
        try:
            result = admission.verify(
                copied["root"], external_root_pin, copied["policy"],
                copied["policy_sig"], copied["delegate"], copied["manifest"],
                copied["manifest_sig"], copied["artifact"],
                external_epoch_floor, external_sequence_floor)
        except admission.Refused as error:
            _deny("CRYPTO_REFUSED_" + str(error))
        if result != "C3E_TEST_POLICY_ACCEPTED_NO_PRODUCTION_AUTH":
            _deny("CRYPTO_PROOF_UNEXPECTED")
        policy_doc = admission._unique_json(copied["policy"])
        manifest_doc = admission._unique_json(copied["manifest"])
        policy_epoch = policy_doc["epoch"]
        sequence = manifest_doc["sequence"]
        policy_hash = hashlib.sha256(copied["policy"].read_bytes()).hexdigest()
        artifact_hash = hashlib.sha256(copied["artifact"].read_bytes()).hexdigest()
        if artifact_hash != manifest_doc["sha256"]:
            _deny("SNAPSHOT_ARTIFACT_MISMATCH")

        db = _connect(db_path)
        in_transaction = False
        try:
            db.execute("BEGIN IMMEDIATE")
            in_transaction = True
            pin, old_epoch, old_seq, old_policy, old_artifact = _read(db)
            if pin != external_root_pin:
                _deny("ENROLLED_ROOT_PIN_MISMATCH")
            if policy_epoch < max(old_epoch, external_epoch_floor):
                _deny("POLICY_ROLLBACK_REFUSED")
            if sequence < max(old_seq, external_sequence_floor):
                _deny("RELEASE_ROLLBACK_REFUSED")
            if policy_epoch == old_epoch and old_policy and policy_hash != old_policy:
                _deny("EQUIVOCAL_POLICY_AT_SAME_EPOCH")
            if sequence == old_seq and old_artifact and artifact_hash != old_artifact:
                _deny("EQUIVOCAL_RELEASE_AT_SAME_SEQUENCE")
            db.execute(
                """UPDATE checkpoint SET epoch_floor=?, sequence_floor=?,
                   policy_digest=?, artifact_digest=? WHERE id=1""",
                (max(policy_epoch, old_epoch, external_epoch_floor),
                 max(sequence, old_seq, external_sequence_floor),
                 policy_hash if policy_epoch > old_epoch or not old_policy
                     else old_policy,
                 artifact_hash if sequence > old_seq or not old_artifact
                     else old_artifact))
            db.execute("COMMIT")
            in_transaction = False
        except (sqlite3.Error, Refused):
            if in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
    return SUCCESS
