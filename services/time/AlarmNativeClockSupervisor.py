#!/usr/bin/env python3
"""BG1-B2B10: foreground native Clock supervisor, fail-closed v1 socket.

This is a REAL AF_UNIX listening process, but NOT an alarm daemon and NOT a
Clock release authority. It never pauses Quickshell, changes FileView state,
acquires an owner lease, schedules, rings or notifies. Production accepts
NO enrolled sessions; only an isolated synthetic CI harness may inject one.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import struct
import sys


def _origin_component():
    path = Path(__file__).resolve().with_name("AlarmInstalledRoleTrustPreflight.py")
    spec = importlib.util.spec_from_file_location("clock_b2b10_origin", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock installed role verifier missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


Origin = _origin_component()
Peer = Origin.Role._Peer

def _session_component():
    path = Path(__file__).resolve().with_name("AlarmSupervisorSessionLedger.py")
    spec = importlib.util.spec_from_file_location("clock_b2b11_session", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock session floor component unavailable")
    component = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = component
    spec.loader.exec_module(component)
    return component

Session = _session_component()

def _protected_enrollment_component():
    path = Path(__file__).resolve().with_name(
        "AlarmProtectedSessionEnrollment.py")
    spec = importlib.util.spec_from_file_location(
        "clock_b2b12_enrollment", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock protected session verifier unavailable")
    component = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = component
    spec.loader.exec_module(component)
    return component

ProtectedEnrollment = _protected_enrollment_component()

def _current_floor_component():
    path=Path(__file__).resolve().with_name("AlarmCurrentFloorWitness.py")
    spec=importlib.util.spec_from_file_location("clock_b2b14_floor",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock current-floor verifier unavailable")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

CurrentFloor=_current_floor_component()

def _final_source_component():
    path=Path(__file__).resolve().with_name("AlarmFinalV2SourceWitness.py")
    spec=importlib.util.spec_from_file_location("clock_b2b16_final_v2",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock native V2 source verifier unavailable")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

FinalV2=_final_source_component()

def _bridge_component():
    path=Path(__file__).resolve().with_name("AlarmBridgeChallengeLedger.py")
    spec=importlib.util.spec_from_file_location("clock_b2b17_bridge",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock bridge preflight unavailable")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

Bridge=_bridge_component()

# Intentionally unprovisioned. Only a separately approved protected
# Clock installation may pin these values in reviewed source/package
# provenance. NO socket request, environment setting, or CLI flag can
# provide them. A signed session without independent trust is DENIED.
APPROVED_CLOCK_RELEASE_ROOT_SHA256 = None
APPROVED_CLOCK_RELEASE_FLOOR = None
# A *separately* trusted installed supervisor must bind these from its own
# protected package and last accepted final source witness. No request,
# environment or QML flag may choose them.
APPROVED_CLOCK_FINAL_V2_SOURCE_PATH = None
APPROVED_CLOCK_FINAL_V2_SOURCE_DIGEST = None
APPROVED_CLOCK_FINAL_V2_SOURCE_UID = None

SOCKET_FILE = "clock-supervisor-v1.sock"
RUNTIME_SUBDIR = "post-apollo-clock"
TEST_RUNTIME = "bg1-clock-supervisor-fixture"
MAX_FRAME = 1024
PROTOCOL = 1
ACTIONS = frozenset(("INSPECT_ORIGIN", "INSPECT_FINAL_V2",
                     "PREPARE_BRIDGE_CHALLENGE", "ACK_BRIDGE_CHALLENGE",
                     "REQUEST_PAUSE",
                     "RELEASE_WRITER", "TAKE_OWNERSHIP", "RING_ALARM"))


class Refused(ValueError):
    """Stable error without trusted path names, alarm titles or notes."""


@dataclass(frozen=True, slots=True)
class SyntheticSessionPin:
    """Test-harness supervisor-owned enrollment, never from socket bytes."""
    pid: int
    ticks: int
    interpreter: str
    role: str
    trust_directory: str
    pinned_root_sha256: str
    minimum_epoch: int
    minimum_sequence: int
    epoch: int = 5  # Synthetic ledger epoch, never live ownership.


def _owned_directory(path, *, exact_mode=0o700):
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise Refused("RUNTIME_DIRECTORY_UNAVAILABLE") from exc
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or stat.S_IMODE(st.st_mode) != exact_mode):
        raise Refused("UNSAFE_RUNTIME_DIRECTORY")


def _runtime_path(runtime, *, synthetic_only):
    root = Path(runtime)
    if (not root.is_absolute()
            or str(root) != os.path.normpath(str(root))
            or root.is_symlink()):
        raise Refused("UNTRUSTED_CLOCK_RUNTIME_PATH")
    if synthetic_only:
        if root.name != TEST_RUNTIME:
            raise Refused("DISPOSABLE_SUPERVISOR_RUNTIME_REQUIRED")
        _owned_directory(root.parent)
    else:
        # A trusted user runtime directory, not a home or /tmp socket.
        if str(root) != f"/run/user/{os.getuid()}":
            raise Refused("INSTALLED_USER_RUNTIME_REQUIRED")
    _owned_directory(root)
    return root


def _unique(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise Refused("DUPLICATE_CLOCK_REQUEST_FIELD")
        data[key] = value
    return data


def _decode_request(line):
    if (type(line) is not bytes or not 1 < len(line) <= MAX_FRAME
            or not line.endswith(b"\\n") or b"\\n" in line[:-1]):
        raise Refused("CLOCK_REQUEST_FRAME_INVALID")
    raw = line[:-1]
    try:
        request = json.loads(raw.decode("utf-8", "strict"),
                             object_pairs_hook=_unique,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 Refused("CLOCK_NONFINITE_NUMBER")))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Refused("CLOCK_REQUEST_JSON_INVALID") from exc
    if (type(request) is not dict or type(request.get("v")) is not int
            or request["v"] != PROTOCOL
            or type(request.get("action")) is not str
            or request["action"] not in ACTIONS):
        raise Refused("CLOCK_REQUEST_OPERATION_REFUSED")
    action = request["action"]
    fields = ({"v", "action", "challenge"}
              if action == "ACK_BRIDGE_CHALLENGE" else {"v", "action"})
    if (set(request) != fields
            or (action == "ACK_BRIDGE_CHALLENGE"
                and (type(request.get("challenge")) is not str
                     or not Bridge.HEX64.fullmatch(request["challenge"])))):
        raise Refused("CLOCK_REQUEST_OPERATION_REFUSED")
    expected = json.dumps(request, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True).encode("ascii")
    if expected != raw:
        raise Refused("CLOCK_REQUEST_NOT_CANONICAL")
    return action, request.get("challenge")


def _response(reason, observed=False):
    # The only positive evidence is origin observation, never an authority.
    return {"v": PROTOCOL, "ok": False, "reason": reason,
            "originObserved": bool(observed), "roleAuthenticated": False,
            "writerStopped": False, "releaseAcknowledged": False,
            "ownsRealAlarmFile": False, "canTransferOwnership": False,
            "canRing": False, "canNotify": False}


def _final_response(reason, *, observed=False, final=False):
    result=_response(reason, observed=observed)
    result.update({
        "finalV2RevisionObserved": bool(final),
        "fileSyncObserved": bool(final),
        "parentDirectorySyncObserved": bool(final),
        "sourceExclusive": False,
        "finalRevisionDurablyLocked": False,
        "oldWriterRestartPrevented": False,
    })
    return result

def _bridge_response(reason, *, observed=False, issued=False, round_trip=False):
    result = _response(reason, observed=observed)
    result.update({
        "channelChallengeIssued": bool(issued),
        "channelRoundTripObserved": bool(round_trip),
        "nativeToQmlChannelAuthenticated": False,
        "quickshellDrainObserved": False,
        "finalRevisionDurablyLocked": False,
        "oldWriterRestartPrevented": False,
    })
    return result


class ClockNativeSupervisor:
    """One foreground AF_UNIX supervisor; never owns or writes alarm data."""

    def __init__(self, runtime_dir, *, synthetic_only=False):
        if type(synthetic_only) is not bool:
            raise Refused("INVALID_SUPERVISOR_MODE")
        self.synthetic = synthetic_only
        self.runtime = _runtime_path(runtime_dir, synthetic_only=synthetic_only)
        self.directory = self.runtime / RUNTIME_SUBDIR
        self.socket_path = self.directory / SOCKET_FILE
        self._listener = None
        self._socket_identity = None
        self._test_pins = {}
        # B2B11: only the explicitly disposable supervisor gets a ledger
        # and holds duplicate kernel pidfds to witness actual process exit.
        # Real foreground mode still has NO trusted session enroller.
        self._session_ledger = None
        self._test_pidfds = {}
        # Only test code may set a disposable source. The installed
        # source and pinned digest are intentionally unprovisioned.
        self._test_final_source = None
        # B2B17: disposable signed-process challenge only, NOT QML auth.
        # Production has no challenge issuer or bridge enrollment.
        self._bridge_challenges = (Bridge.ClockBridgeChallengeLedger()
                                   if self.synthetic else None)

    def add_synthetic_session(self, pin):
        """Only isolated tests can enroll a test subprocess. No CLI for this."""
        if (self.synthetic is not True or type(pin) is not SyntheticSessionPin
                or type(pin.pid) is not int or pin.pid <= 1
                or type(pin.ticks) is not int or pin.ticks <= 0
                or type(pin.interpreter) is not str
                or not pin.interpreter.startswith("/")
                or pin.role != "clock-ui-bridge"
                or type(pin.trust_directory) is not str
                or type(pin.pinned_root_sha256) is not str
                or type(pin.minimum_epoch) is not int
                or type(pin.minimum_sequence) is not int
                or pin.minimum_epoch <= 0 or pin.minimum_sequence <= 0
                or type(pin.epoch) is not int
                or not 1 <= pin.epoch <= Session.MAX_EPOCH
                or pin.epoch < pin.minimum_epoch):
            raise Refused("SYNTHETIC_SESSION_ONLY")
        if self._listener is None:
            raise Refused("SUPERVISOR_NOT_LISTENING")
        if pin.pid in self._test_pins:
            raise Refused("SUPERVISOR_PIN_ALREADY_PRESENT")
        self._test_pins[pin.pid] = pin

    def pin_synthetic_final_v2(self, *, source_path, expected_digest,
                               expected_uid):
        """Pin disposable V2 file outside the socket request protocol."""
        if not self.synthetic or self._listener is None:
            raise Refused("TRUSTED_FINAL_V2_CONTROLLER_UNAVAILABLE")
        if self._test_final_source is not None:
            raise Refused("SYNTHETIC_FINAL_V2_ALREADY_PINNED")
        try:
            witness=FinalV2.ClockFinalV2SourceWitness(
                source_path=source_path, pinned_sha256=expected_digest,
                expected_uid=expected_uid, synthetic_only=True)
        except FinalV2.Refused as exc:
            raise Refused(str(exc)) from exc
        self._test_final_source=witness

    def _observe_final_v2(self, conn):
        """Only a live previously signed session may observe pinned bytes.

        Neither this inspection nor fsync can prohibit a subsequent write,
        so absolutely no writer or ring rights are conferred.
        """
        try:
            if self.synthetic:
                raw=conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                    struct.calcsize("3i"))
                pid,uid,_=struct.unpack("3i",raw)
                pin=self._test_pins.get(pid)
                held=self._test_pidfds.get(pid)
                if (pin is None or held is None
                        or uid!=os.getuid()
                        or self._test_final_source is None
                        or Peer._exited(held)):
                    return False
                result=self._test_final_source.observe()
                if Peer._exited(held):
                    return False
            else:
                path=APPROVED_CLOCK_FINAL_V2_SOURCE_PATH
                digest=APPROVED_CLOCK_FINAL_V2_SOURCE_DIGEST
                uid=APPROVED_CLOCK_FINAL_V2_SOURCE_UID
                if (type(path) is not str or type(digest) is not str
                        or type(uid) is not int):
                    return False
                witness=FinalV2.ClockFinalV2SourceWitness(
                    source_path=path,pinned_sha256=digest,
                    expected_uid=uid,synthetic_only=False)
                result=witness.observe()
            return (result["finalV2RevisionObserved"] is True
                    and result["fileSyncObserved"] is True
                    and result["parentDirectorySyncObserved"] is True
                    and result["writerStopped"] is False
                    and result["canTransferOwnership"] is False
                    and result["canRing"] is False)
        except (FinalV2.Refused, Peer.Refused, ValueError, OSError):
            return False

    def _bridge_identity(self, conn):
        """Observe signed peer and bind a challenge to its live kernel pidfd.

        Test mode only. Socket bytes cannot choose the process, epoch or root.
        There is deliberately no installed QML bridge or real pause path.
        """
        if not self.synthetic or self._bridge_challenges is None:
            return None
        if not self._observe(conn):
            return None
        try:
            raw=conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                struct.calcsize("3i"))
            pid, uid, gid=struct.unpack("3i", raw)
            pin=self._test_pins.get(pid)
            held=self._test_pidfds.get(pid)
            if (pin is None or held is None or pin.pid != pid
                    or uid != os.getuid() or gid != os.getgid()
                    or Peer._exited(held)):
                return None
            st=os.fstat(held)
            return (pin.pid, pin.ticks, pin.epoch,
                    pin.pinned_root_sha256, st.st_dev, st.st_ino)
        except (OSError, Peer.Refused, ValueError, struct.error):
            return None

    def bind(self):
        if self._listener is not None:
            raise Refused("SUPERVISOR_ALREADY_LISTENING")
        _runtime_path(self.runtime, synthetic_only=self.synthetic)
        if self.directory.is_symlink():
            raise Refused("CLOCK_SOCKET_DIRECTORY_LINKED")
        try:
            self.directory.mkdir(mode=0o700, exist_ok=True)
        except OSError as exc:
            raise Refused("CLOCK_SOCKET_DIRECTORY_UNAVAILABLE") from exc
        _owned_directory(self.directory)
        if self.synthetic:
            self._session_ledger = Session.ClockSessionLedger(
                self.directory, synthetic_only=True)
        if os.path.lexists(self.socket_path):
            # Never unlink a path occupied by another active supervisor.
            raise Refused("CLOCK_SOCKET_ALREADY_EXISTS")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        old_umask = os.umask(0o077)
        try:
            listener.bind(str(self.socket_path))
            listener.listen(8)
            os.chmod(self.socket_path, 0o600)
            st = os.lstat(self.socket_path)
            if (not stat.S_ISSOCK(st.st_mode) or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o600):
                raise Refused("CLOCK_SOCKET_UNSAFE")
            self._socket_identity = (st.st_dev, st.st_ino)
            self._listener = listener
        except BaseException:
            listener.close()
            raise
        finally:
            os.umask(old_umask)

    def _observe_installed(self, conn):
        """Observe approved installed process enrollment. NEVER authorize.

        The approved signer/root pin and monotonic floor are intentionally
        unprovisioned. Installing a root file alone does not turn this on.
        """
        if self.synthetic:
            return False
        pin = APPROVED_CLOCK_RELEASE_ROOT_SHA256
        floor = APPROVED_CLOCK_RELEASE_FLOOR
        if (type(pin) is not str or not Origin.HEX.fullmatch(pin)
                or type(floor) is not tuple or len(floor) != 2
                or any(type(x) is not int or x < 1 for x in floor)):
            return False
        try:
            verifier = ProtectedEnrollment.ClockProtectedSessionEnrollment(
                enrollment_directory=ProtectedEnrollment.INSTALL_ENROLLMENT_DIR,
                trust_directory=Origin.TRUST_DIR,
                pinned_root_sha256=pin,
                minimum_epoch=floor[0],
                minimum_sequence=floor[1],
                synthetic_only=False)
            witness=CurrentFloor.ClockCurrentFloorWitness(
                enrollment_directory=ProtectedEnrollment.INSTALL_ENROLLMENT_DIR,
                trust_directory=Origin.TRUST_DIR,
                pinned_root_sha256=pin,
                minimum_epoch=floor[0],minimum_sequence=floor[1],
                synthetic_only=False)
            # Signed root snapshot is independently checked both BEFORE
            # and AFTER kernel-peer observation. No cached floor state
            # may authenticate a session after a newer issuance begins.
            _,bundle=verifier._load()
            previous=witness.compare_session(bundle[0])
            expected=(previous["releaseEpoch"],previous["releaseSequence"],
                      previous["sessionSha256"])
            observed = verifier.inspect(conn)
            _,after=verifier._load()
            if bundle!=after:
                return False
            witness.compare_session(after[0],expected=expected)
        except (ProtectedEnrollment.Refused, CurrentFloor.Refused,
                Origin.Refused, Peer.Refused, ValueError, OSError):
            return False
        return (observed["originObserved"] is True
                and observed["signedSessionObserved"] is True
                and observed["roleAuthenticated"] is False
                and observed["canTransferOwnership"] is False
                and observed["canRing"] is False)

    def _observe(self, conn):
        try:
            raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                  struct.calcsize("3i"))
            pid, uid, gid = struct.unpack("3i", raw)
        except (OSError, struct.error, AttributeError):
            return False
        if not self.synthetic:
            return self._observe_installed(conn)
        if uid != os.getuid() or pid <= 1 or gid < 0:
            return False
        pin = self._test_pins.get(pid)
        if pin is None:
            return False
        witness = None
        try:
            witness = Peer.capture(conn, pin.interpreter)
            if (witness["pid"] != pin.pid or witness["ticks"] != pin.ticks
                    or witness["uid"] != uid or witness["gid"] != gid):
                return False
            probe = Origin.ClockInstalledRoleTrustPreflight(
                trust_directory=pin.trust_directory,
                pinned_root_sha256=pin.pinned_root_sha256,
                expected_role=pin.role, minimum_epoch=pin.minimum_epoch,
                minimum_sequence=pin.minimum_sequence,
                disposable_test_mode=True)
            result = probe.inspect(conn, witness,
                                   expected_pid=pin.pid,
                                   expected_start_ticks=pin.ticks)
            # Observed origin cannot become a production Clock grant.
            verified = (result["originObserved"] is True
                        and result["releaseEpoch"] == pin.epoch
                        and result["releaseSequence"] >= pin.minimum_sequence
                        and result["roleAuthenticated"] is False
                        and result["canTransferOwnership"] is False
                        and result["canRing"] is False)
            if not verified or self._session_ledger is None:
                return False
            self._session_ledger.observe_signed_process(
                pid=pin.pid, ticks=pin.ticks, epoch=pin.epoch,
                release_root_sha256=pin.pinned_root_sha256)
            # The original pinned SO_PEERPIDFD survives this request so
            # the supervisor can later witness actual exit, not infer it
            # from PID reuse or from a signed response.
            retained = os.dup(witness["pidfd"])
            previous = self._test_pidfds.pop(pin.pid, None)
            if previous is not None:
                os.close(previous)
            self._test_pidfds[pin.pid] = retained
            return True
        except (Peer.Refused, Origin.Refused, Session.Refused,
                OSError, ValueError):
            return False
        finally:
            if witness is not None:
                Peer.close(witness)

    def observe_synthetic_session_exit(self, pid):
        """Test-only; the original pidfd MUST have signaled process exit.

        A successful observation does not authorize RELEASED or owner
        takeover, nor does it protect against a real Quickshell restart.
        """
        if not self.synthetic or self._session_ledger is None:
            raise Refused("INSTALLED_SESSION_REVOCATION_UNAVAILABLE")
        pin = self._test_pins.get(pid)
        fd = self._test_pidfds.get(pid)
        if pin is None or fd is None:
            raise Refused("NO_SUPERVISED_TEST_PROCESS_WITNESS")
        try:
            result = self._session_ledger.observe_exited_pidfd(
                pid=pin.pid, ticks=pin.ticks, epoch=pin.epoch,
                pidfd=fd)
        except Session.Refused as exc:
            raise Refused(str(exc)) from exc
        os.close(self._test_pidfds.pop(pid))
        self._test_pins.pop(pid)
        return result

    def _handle(self, conn):
        conn.settimeout(2.0)
        try:
            with conn.makefile("rb") as reader:
                frame = reader.readline(MAX_FRAME + 1)
            action, challenge = _decode_request(frame)
            if action == "INSPECT_ORIGIN":
                observed = self._observe(conn)
                result = _response(
                    "OBSERVED_ONLY_NOT_AUTHORIZED" if observed
                    else "NO_INSTALLED_CLOCK_SESSION_AUTHORITY",
                    observed=observed)
            elif action == "INSPECT_FINAL_V2":
                observed=self._observe(conn)
                final=observed and self._observe_final_v2(conn)
                result=_final_response(
                    "FINAL_V2_SYNC_OBSERVED_ONLY_NOT_AUTHORIZED" if final
                    else "NO_TRUSTED_FINAL_V2_SOURCE_WITNESS",
                    observed=observed, final=final)
            elif action in ("PREPARE_BRIDGE_CHALLENGE",
                            "ACK_BRIDGE_CHALLENGE"):
                identity=self._bridge_identity(conn)
                if identity is None:
                    result=_bridge_response("CLOCK_BRIDGE_SIGNED_PEER_REQUIRED")
                else:
                    try:
                        if action == "PREPARE_BRIDGE_CHALLENGE":
                            token=self._bridge_challenges.issue(identity)
                            result=_bridge_response(
                                "BRIDGE_CHALLENGE_ISSUED_NO_QML_AUTHORITY",
                                observed=True, issued=True)
                            # A one-use challenge goes only over this
                            # independently signed peer's accepted socket.
                            result["challenge"]=token
                        else:
                            self._bridge_challenges.acknowledge(
                                identity, challenge)
                            result=_bridge_response(
                                "BRIDGE_ROUND_TRIP_ONLY_NO_QML_AUTHORITY",
                                observed=True, round_trip=True)
                    except Bridge.Refused as exc:
                        result=_bridge_response(str(exc), observed=True)
            else:
                result = _response("NATIVE_WRITER_HANDOFF_NOT_AUTHORIZED")
        except (Refused, OSError, socket.timeout, ValueError) as exc:
            reason = str(exc) if isinstance(exc, Refused) else \
                     "CLOCK_REQUEST_READ_REFUSED"
            result = _response(reason)
        try:
            conn.sendall(json.dumps(result, sort_keys=True,
                                    separators=(",", ":")).encode() + b"\n")
        except OSError:
            pass
        return result

    def serve_once(self, *, timeout=3.0):
        if self._listener is None:
            raise Refused("SUPERVISOR_NOT_LISTENING")
        self._listener.settimeout(timeout)
        try:
            connection, _ = self._listener.accept()
        except (TimeoutError, OSError) as exc:
            raise Refused("SUPERVISOR_ACCEPT_REFUSED") from exc
        with connection:
            return self._handle(connection)

    def close(self):
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        if self._socket_identity is not None:
            try:
                st = os.lstat(self.socket_path)
                if stat.S_ISSOCK(st.st_mode) and (
                        st.st_dev, st.st_ino) == self._socket_identity:
                    os.unlink(self.socket_path)
            except FileNotFoundError:
                pass
            finally:
                self._socket_identity = None
        self._test_pins.clear()
        for fd in self._test_pidfds.values():
            try:
                os.close(fd)
            except OSError:
                pass
        self._test_pidfds.clear()
        self._session_ledger = None
        if self._bridge_challenges is not None:
            self._bridge_challenges.clear()

    def serve_forever(self):
        self.bind()
        try:
            while True:
                self.serve_once(timeout=None)
        finally:
            self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foreground", action="store_true", required=True)
    args = parser.parse_args(argv)
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    try:
        server = ClockNativeSupervisor(runtime)
        server.serve_forever()
    except (Refused, OSError) as exc:
        print("CLOCK SUPERVISOR REFUSED: " +
              (str(exc) if isinstance(exc, Refused) else
               "UNVERIFIED_HOST_RUNTIME"), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
