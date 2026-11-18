#!/usr/bin/env python3
"""BG1-B2B13: protected Clock controller floor + signed session issuance.

Source-only. A privileged owner must separately install/provision a Clock-
specific Ed25519 signer and start an independently supervised controller.
There is no service, private-key loader, IPC issuance route or auto-start
here. The only rootless writer mode is fixed-name disposable test state.
Successful issuance is STILL NOT alarm writer or ringing authorization.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import stat
import sys
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _neighbor(module, alias):
    path = Path(__file__).resolve().with_name(module+".py")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock controller dependency unavailable")
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


Session = _neighbor("AlarmProtectedSessionEnrollment","clock_b2b13_session")
Origin = Session.Origin
Peer = Session.Peer
PROTECTED_STATE = Path("/var/lib/post-apollo/clock/controller-v1")
DISPOSABLE_STATE = "bg1-clock-controller-fixture"
LEDGER = "clock-release-floor-v1.sqlite3"
MAX_VERSION = 2147483647
DENIED = {
    "roleAuthenticated": False, "writerStopped": False,
    "releaseAcknowledged": False, "oldWriterRestartPrevented": False,
    "ownsRealAlarmFile": False, "canTransferOwnership": False,
    "canRing": False, "canNotify": False,
}


class Refused(ValueError):
    """Fixed refusal code; never contain user alarms, keys or paths."""


def _check_directory(path, *, synthetic, role):
    if (not path.is_absolute()
            or str(path) != os.path.normpath(str(path))):
        raise Refused("UNTRUSTED_CONTROLLER_DIRECTORY")
    if synthetic:
        names = {"state": DISPOSABLE_STATE,
                 "enrollment": Session.TEST_ENROLLMENT_NAME}
        if path.name != names[role]:
            raise Refused("DISPOSABLE_CONTROLLER_DIRECTORY_REQUIRED")
        for item in (path.parent, path):
            try:
                st = os.lstat(item)
            except OSError as exc:
                raise Refused("CONTROLLER_DIRECTORY_MISSING") from exc
            if (not stat.S_ISDIR(st.st_mode)
                    or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o700):
                raise Refused("UNSAFE_DISPOSABLE_CONTROLLER_DIRECTORY")
        return
    expected = PROTECTED_STATE if role == "state" else (
        Session.INSTALL_ENROLLMENT_DIR)
    if path != expected:
        raise Refused("PROTECTED_CONTROLLER_DIRECTORY_REQUIRED")
    if os.geteuid() != 0 or os.getuid() != 0:
        raise Refused("PRIVILEGED_CLOCK_CONTROLLER_REQUIRED")
    current = Path("/")
    for part in path.parts[1:]:
        current = current / part
        try:
            st = os.lstat(current)
        except OSError as exc:
            raise Refused("PROTECTED_CONTROLLER_DIRECTORY_MISSING") from exc
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0
                or st.st_mode & 0o022):
            raise Refused("UNSAFE_ROOT_CONTROLLER_ANCESTOR")
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    if (role == "state" and mode != 0o700) or (
            role == "enrollment" and mode not in (0o755,0o700)):
        raise Refused("UNSAFE_ROOT_CONTROLLER_DIRECTORY")


def _database(path, *, synthetic):
    if path.is_symlink():
        raise Refused("CLOCK_FLOOR_LEDGER_SYMLINK")
    fd = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                     os.O_CLOEXEC | getattr(os,"O_NONBLOCK",0),0o600)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
                or st.st_uid != (os.getuid() if synthetic else 0)
                or stat.S_IMODE(st.st_mode) != 0o600):
            raise Refused("UNSAFE_CLOCK_FLOOR_LEDGER")
    except OSError as exc:
        raise Refused("CLOCK_FLOOR_LEDGER_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)
    try:
        db = sqlite3.connect(path,isolation_level=None,timeout=5)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""CREATE TABLE IF NOT EXISTS release_floor (
          slot INTEGER PRIMARY KEY CHECK(slot=1),
          epoch INTEGER NOT NULL,
          sequence INTEGER NOT NULL,
          boot_id TEXT NOT NULL,
          old_writer_pid INTEGER NOT NULL,
          old_writer_ticks INTEGER NOT NULL,
          signer_digest TEXT NOT NULL,
          session_digest TEXT NOT NULL
        )""")
        return db
    except sqlite3.Error as exc:
        raise Refused("CLOCK_FLOOR_LEDGER_INVALID") from exc


def _read(db):
    try:
        row = db.execute(
            "SELECT epoch,sequence,boot_id,old_writer_pid,"
            "old_writer_ticks,signer_digest,session_digest "
            "FROM release_floor WHERE slot=1").fetchone()
    except sqlite3.Error as exc:
        raise Refused("CLOCK_RELEASE_FLOOR_UNREADABLE") from exc
    if row is not None and (
            len(row) != 7 or any(type(row[i]) is not int
                                 for i in (0,1,3,4))
            or not 1 <= row[0] <= MAX_VERSION
            or not 1 <= row[1] <= MAX_VERSION
            or row[3] <= 1 or row[4] <= 0
            or type(row[2]) is not str
            or type(row[5]) is not str or type(row[6]) is not str
            or not Origin.HEX.fullmatch(row[5])
            or not Origin.HEX.fullmatch(row[6])):
        raise Refused("CLOCK_RELEASE_FLOOR_CORRUPT")
    return row


def _durable_publish(directory, name, raw, *, synthetic):
    """Atomic individual file publish (pair may refuse during a crash)."""
    destination = directory/name
    if os.path.lexists(destination):
        before = os.lstat(destination)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != (os.getuid() if synthetic else 0)):
            raise Refused("UNSAFE_EXISTING_SESSION_FILE")
    temporary = directory/(".clock-issue-"+uuid.uuid4().hex)
    fd = None
    try:
        mode = 0o600 if synthetic else 0o644
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW | os.O_CLOEXEC,mode)
        written = 0
        while written < len(raw):
            n = os.write(fd,raw[written:])
            if n <= 0:
                raise Refused("CLOCK_SESSION_WRITE_FAILED")
            written += n
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.replace(temporary,destination)
        dirfd = os.open(directory,os.O_RDONLY | os.O_DIRECTORY |
                        os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except OSError as exc:
        raise Refused("CLOCK_SESSION_WRITE_FAILED") from exc
    finally:
        if fd is not None:
            os.close(fd)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


class ClockReleaseFloorController:
    """Trusted direct-invocation controller, NOT a socket-exposed issuer.

    The signer is an already provisioned private Ed25519 key supplied
    inside an independently privileged controller process; it MUST match
    the protected installed B2B9 public root and independent fingerprint.
    """

    def __init__(self, *, state_directory, enrollment_directory,
                 trust_directory, pinned_root_sha256, minimum_epoch,
                 minimum_sequence, signing_key, synthetic_only=False):
        if (type(synthetic_only) is not bool
                or not isinstance(signing_key,Ed25519PrivateKey)
                or type(minimum_epoch) is not int
                or type(minimum_sequence) is not int
                or not 1 <= minimum_epoch <= MAX_VERSION
                or not 1 <= minimum_sequence <= MAX_VERSION):
            raise Refused("TRUSTED_CLOCK_ISSUER_INPUT_REQUIRED")
        self.synthetic = synthetic_only
        self.state = Path(state_directory)
        self.enrollment = Path(enrollment_directory)
        _check_directory(self.state,synthetic=synthetic_only,role="state")
        _check_directory(self.enrollment,synthetic=synthetic_only,
                         role="enrollment")
        if synthetic_only and self.state.parent != self.enrollment.parent:
            raise Refused("DISPOSABLE_ISSUER_SCOPE_MISMATCH")
        try:
            self.origin = Origin.ClockInstalledRoleTrustPreflight(
                trust_directory=trust_directory,
                pinned_root_sha256=pinned_root_sha256,
                expected_role="clock-ui-bridge",
                minimum_epoch=minimum_epoch,
                minimum_sequence=minimum_sequence,
                disposable_test_mode=synthetic_only)
            installed_key,_,_ = self.origin._load_bundle()
        except (Origin.Refused,ValueError,OSError) as exc:
            raise Refused("CLOCK_ISSUER_ROOT_NOT_APPROVED") from exc
        pub = signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        if (hashlib.sha256(pub).hexdigest()!=pinned_root_sha256
                or installed_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw)!=pub):
            raise Refused("CLOCK_SIGNER_DOES_NOT_MATCH_INSTALLED_ROOT")
        self.signer = signing_key
        self.root_pin = pinned_root_sha256
        self.floor = (minimum_epoch,minimum_sequence)
        self.ledger_path = self.state/LEDGER

    def _db(self):
        _check_directory(self.state,synthetic=self.synthetic,role="state")
        _check_directory(self.enrollment,synthetic=self.synthetic,
                         role="enrollment")
        return _database(self.ledger_path,synthetic=self.synthetic)

    def inspect_floor(self):
        db = self._db()
        try:
            row = _read(db)
        finally:
            db.close()
        return dict({"latestEpoch":row[0] if row else 0,
                     "latestSequence":row[1] if row else 0,
                     "floorRecorded":row is not None,
                     "fixtureOnly":self.synthetic},**DENIED)

    def issue(self, accepted_socket):
        """Issue exactly one signed Clock UI session for the actual peer.

        The durable floor is committed BEFORE publishing the signed files.
        After a crash, the same version cannot be reissued; a higher
        independently signed role version is required for recovery.
        """
        try:
            root,policy_raw,_=self.origin._load_bundle()
            role=Origin.Role._policy(policy_raw)
            witness=Peer.capture(accepted_socket,role["interpreterPath"])
        except (Origin.Refused,Origin.Role.Refused,Peer.Refused,
                ValueError,OSError) as exc:
            raise Refused("CONTROLLER_PEER_OR_SIGNED_ROLE_REFUSED") from exc
        try:
            pid,ticks=witness["pid"],witness["ticks"]
            try:
                observed=self.origin.inspect(
                    accepted_socket,witness,
                    expected_pid=pid,expected_start_ticks=ticks)
            except (Origin.Refused,ValueError,OSError) as exc:
                raise Refused("CONTROLLER_SIGNED_PROCESS_REFUSED") from exc
            if (observed["originObserved"] is not True
                    or observed["roleAuthenticated"] is not False
                    or observed["canTransferOwnership"] is not False
                    or observed["canRing"] is not False):
                raise Refused("UNAPPROVED_CONTROLLER_ISSUE_RIGHTS")
            epoch,sequence=role["releaseEpoch"],role["releaseSequence"]
            if (epoch,sequence) < self.floor:
                raise Refused("CONTROLLER_INDEPENDENT_RELEASE_FLOOR")
            data = {
                "schema":Session.SCHEMA,"purpose":Session.PURPOSE,
                "role":"clock-ui-bridge",
                "bootId":Session._kernel_boot(),
                "pid":pid,"startTicks":ticks,
                "uid":witness["uid"],"gid":witness["gid"],
                "releaseEpoch":epoch,"releaseSequence":sequence,
                "socketScope":Session.SOCKET_SCOPE
            }
            raw = Session.canonical(data)
            Session._manifest(raw)
            signature = self.signer.sign(Session.DOMAIN+raw)
            root.verify(signature,Session.DOMAIN+raw)
            # Recheck signed role and kernel connection immediately
            # before committing the durable floor.
            _,again,_=self.origin._load_bundle()
            if again!=policy_raw:
                raise Refused("CONTROLLER_ROLE_CHANGED_DURING_ISSUE")
            try:
                Peer.verify(accepted_socket,witness,role["interpreterPath"])
            except Peer.Refused as exc:
                raise Refused("CONTROLLER_PROCESS_EXITED") from exc
            db = self._db()
            try:
                db.execute("BEGIN IMMEDIATE")
                old = _read(db)
                if old is not None and (
                        (epoch,sequence) <= (old[0],old[1])):
                    raise Refused("MONOTONIC_CLOCK_RELEASE_REPLAY")
                if old is not None and old[5]!=self.root_pin:
                    raise Refused("CLOCK_RELEASE_ROOT_CHANGED_WITHOUT_APPROVAL")
                if old is not None and (pid,ticks)==(old[3],old[4]):
                    raise Refused("OLD_CLOCK_PROCESS_ALREADY_ENROLLED")
                db.execute("""INSERT INTO release_floor
                    (slot,epoch,sequence,boot_id,old_writer_pid,
                     old_writer_ticks,signer_digest,session_digest)
                    VALUES (1,?,?,?,?,?,?,?)
                    ON CONFLICT(slot) DO UPDATE SET
                    epoch=excluded.epoch,
                    sequence=excluded.sequence,
                    boot_id=excluded.boot_id,
                    old_writer_pid=excluded.old_writer_pid,
                    old_writer_ticks=excluded.old_writer_ticks,
                    signer_digest=excluded.signer_digest,
                    session_digest=excluded.session_digest""",
                    (epoch,sequence,data["bootId"],pid,ticks,self.root_pin,
                     hashlib.sha256(raw).hexdigest()))
                db.execute("COMMIT")
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
            finally:
                db.close()
            # Floor already committed, so partial/crashed publication
            # is fail-closed and can only recover at a higher version.
            _durable_publish(self.enrollment,Session.SESSION_FILE,raw,
                             synthetic=self.synthetic)
            _durable_publish(self.enrollment,Session.SIGNATURE_FILE,
                             signature,synthetic=self.synthetic)
            return dict({"signedSessionPublished":True,
                         "latestEpoch":epoch,
                         "latestSequence":sequence,
                         "fixtureOnly":self.synthetic},**DENIED)
        finally:
            Peer.close(witness)
