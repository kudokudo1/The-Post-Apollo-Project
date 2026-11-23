#!/usr/bin/env python3
"""Privileged native Hospital Room grant signer, source only, NOT installed.

Runs only on a separately approved root-owned socket-activated systemd unit.
Unlike C5 disposable tests, real execution obtains the client PID/UID/GID
from SO_PEERCRED, observes that PID's actual executable and login1 active
seat, invokes interactive Polkit for the exact protected PX review, and
delivers the signed grant ONLY over an authenticated socket to the protected
PX writer. The caller never receives the signed grant or signing key.

The protected PX writer, installed root keys/policy, consent policy/agent and
operator-authorized installation are external prerequisites and do not yet
exist. Failure to meet any prerequisite DENIES; no fallback to QML, JSON
confirmation, a user SQLite path, a fake reviewer or test keys is allowed.
"""
from __future__ import annotations

import array
import asyncio
import hashlib
import os
from pathlib import Path
import re
import socket
import stat
import struct
import subprocess
import sys
import time

import HospitalNativeIssuerCore as C

SERVICE_SOCKET = "/run/post-apollo/hospital/issuer.sock"
POLKIT = "/usr/bin/pkcheck"
POLKIT_ACTIONS = {
    "TRASH": "org.postapollo.hospital.room-trash",
    "RESTORE": "org.postapollo.hospital.room-restore",
}
MANAGER = "/org/freedesktop/login1"
OWNER = "org.freedesktop.login1"
SESSION = "org.freedesktop.login1.Session"
SO_PEERCRED_FORMAT = "3i"
MAX_IPC = 8192

def _kernel_start(pid):
    if type(pid) is not int or pid < 2:
        C.deny("KERNEL_PID_REFUSED")
    try:
        raw = Path("/proc/%d/stat" % pid).read_text()
        pos = raw.rfind(")")
        if pos < 1 or not raw.startswith(str(pid) + " ("):
            C.deny("KERNEL_STAT_REFUSED")
        tail = raw[pos + 2:].split()
        ticks = int(tail[19])  # field 22, after PID(1)/comm(2)
        if ticks <= 0:
            C.deny("INVALID_PROCESS_START_TICKS")
        return ticks
    except (OSError, ValueError, IndexError) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // UNAVAILABLE_KERNEL_START") from exc

def _kernel_uid(pid, uid, gid):
    try:
        lines = Path("/proc/%d/status" % pid).read_text().splitlines()
        values = {}
        for line in lines:
            if line.startswith(("Uid:", "Gid:")):
                k, raw = line.split(":", 1)
                if k in values:
                    C.deny("DUPLICATE_KERNEL_CREDENTIAL")
                values[k] = [int(x) for x in raw.split()]
        if values.get("Uid") != [uid] * 4 or values.get("Gid") != [gid] * 4:
            C.deny("KERNEL_PEER_UID_GID_CHANGED")
    except (OSError, ValueError) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // KERNEL_PEER_UNAVAILABLE") from exc

def _executable_sha(pid):
    """Hash actual ELF inode via /proc/PID/exe, not a claimed path or cmdline."""
    fd = None
    try:
        fd = os.open("/proc/%d/exe" % pid, os.O_RDONLY | os.O_CLOEXEC)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0
                or before.st_size < 4096 or before.st_size > 32 * 1024 * 1024
                or (stat.S_IMODE(before.st_mode) & 0o022)):
            C.deny("UNTRUSTED_CLIENT_ELF_INODE")
        if os.read(fd, 4) != b"\x7fELF":
            C.deny("ONLY_PINNED_NATIVE_ELF_CLIENTS")
        hasher = hashlib.sha256(b"\x7fELF")
        size = 4
        while size <= 32 * 1024 * 1024:
            block = os.read(fd, min(65536, 32 * 1024 * 1024 + 1 - size))
            if not block:
                break
            hasher.update(block)
            size += len(block)
        after = os.fstat(fd)
        if (size != before.st_size
                or (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            C.deny("NATIVE_CLIENT_EXECUTABLE_REPLACED")
        return hasher.hexdigest()
    except OSError as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // CLIENT_EXECUTABLE_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)

def _peer(sock):
    try:
        raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                              struct.calcsize(SO_PEERCRED_FORMAT))
        pid, uid, gid = struct.unpack(SO_PEERCRED_FORMAT, raw)
        if pid <= 1 or uid <= 0 or gid < 0:
            C.deny("KERNEL_SOCKET_IDENTITY_REFUSED")
        start = _kernel_start(pid)
        _kernel_uid(pid, uid, gid)
        return (pid, uid, gid, start)
    except (OSError, ValueError, struct.error) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // PEER_CREDENTIAL_UNAVAILABLE") from exc

def _same_peer(sock, original, expected_digest):
    current = _peer(sock)
    if current != original or _kernel_start(original[0]) != original[3]:
        C.deny("PEER_PROCESS_REPLACED")
    if _executable_sha(original[0]) != expected_digest:
        C.deny("UNENROLLED_PEER_NATIVE_EXECUTABLE")
    return current

async def _read_logind_session(pid, uid):
    """Real system D-Bus login1 per-process seat, not XDG_SESSION_ID/env/QML."""
    try:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus
        bus = await asyncio.wait_for(
            MessageBus(bus_type=BusType.SYSTEM).connect(), timeout=3)
        try:
            node = await asyncio.wait_for(bus.introspect(OWNER, MANAGER), timeout=3)
            mgr = bus.get_proxy_object(OWNER, MANAGER, node).get_interface(
                "org.freedesktop.login1.Manager")
            path = await asyncio.wait_for(
                mgr.call_get_session_by_pid(pid), timeout=3)
            if (type(path) is not str
                    or not path.startswith("/org/freedesktop/login1/session/")):
                C.deny("NO_KERNEL_PROCESS_LOGIN1_SESSION")
            node = await asyncio.wait_for(bus.introspect(OWNER, path), timeout=3)
            props = bus.get_proxy_object(OWNER, path, node).get_interface(
                "org.freedesktop.DBus.Properties")
            fields = await asyncio.wait_for(props.call_get_all(SESSION), timeout=3)
            values = {k: getattr(v, "value", None) for k, v in fields.items()}
            owner = values.get("User")
            seat = values.get("Seat")
            session_id = values.get("Id")
            if (not isinstance(owner, (tuple, list)) or len(owner) != 2
                    or type(owner[0]) is not int or owner[0] != uid
                    or not isinstance(seat, (tuple, list)) or len(seat) != 2
                    or type(seat[0]) is not str or not seat[0]
                    or type(session_id) is not str or not session_id
                    or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", seat[0])
                    or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", session_id)
                    or values.get("Active") is not True
                    or values.get("State") != "active"
                    or values.get("Remote") is not False
                    or values.get("LockedHint") is not False
                    or values.get("Class") != "user"
                    or values.get("Type") not in ("wayland", "x11", "tty")):
                C.deny("NO_ACTIVE_UNLOCKED_LOCAL_OPERATOR_SEAT")
            return (session_id, seat[0])
        finally:
            bus.disconnect()
    except C.Refused:
        raise
    except Exception as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // LOGIN1_UNAVAILABLE") from exc

def _active_seat(pid, uid):
    try:
        session_id, seat = asyncio.run(_read_logind_session(pid, uid))
    except (RuntimeError, ValueError) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // LOGIN1_SESSION_REFUSED") from exc
    result = "logind-" + seat + "-" + session_id
    if C.ID.fullmatch(result) is None:
        C.deny("PX_SEAT_IDENTIFIER_INVALID")
    return result

def _socket_root_path(path, owner_uid, *, socket_mode=True):
    if type(path) is not str or not path.startswith("/run/post-apollo/hospital/"):
        C.deny("UNTRUSTED_IPC_SOCKET_PATH")
    p = Path(path)
    for parent in (p.parent, p.parent.parent):
        try:
            st = parent.lstat()
        except OSError as exc:
            raise C.Refused("HOSPITAL_NATIVE_HOLD // IPC_PARENT_UNAVAILABLE") from exc
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0
                or (stat.S_IMODE(st.st_mode) & 0o022)):
            C.deny("UNPROTECTED_IPC_ANCESTRY")
    try:
        st = p.lstat()
    except OSError as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // IPC_SOCKET_UNAVAILABLE") from exc
    if (not stat.S_ISSOCK(st.st_mode) or st.st_uid != owner_uid
            or (stat.S_IMODE(st.st_mode) & 0o002)):
        C.deny("UNTRUSTED_IPC_SOCKET_OWNER_OR_MODE")
    return st

def _discard_unexpected_native_rights(ancillary):
    """Close every received SCM_RIGHTS descriptor before ANY packet refusal.

    recvmsg() may install a new fd in a privileged issuer even for a packet
    we later reject because its credentials or length are wrong. Discard all
    delivered rights, including earlier valid descriptors in a malformed
    control record. Linux closes rights withheld by MSG_CTRUNC itself.
    """
    saw_rights = False
    malformed_or_close_failed = False
    for level, kind, raw in ancillary:
        if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
            continue
        saw_rights = True
        handles = array.array("i")
        complete = len(raw) // handles.itemsize * handles.itemsize
        handles.frombytes(raw[:complete])
        if complete != len(raw):
            malformed_or_close_failed = True
        for fd in handles:
            if fd < 0:
                malformed_or_close_failed = True
                continue
            try:
                os.close(fd)
            except OSError:
                malformed_or_close_failed = True
    if malformed_or_close_failed:
        C.deny("UNEXPECTED_NATIVE_RIGHTS_MALFORMED_OR_CLOSE_FAILED")
    if saw_rights:
        C.deny("UNEXPECTED_NATIVE_RIGHTS_CLOSED")


def _packet_recv(sock, *, expected_sender):
    """Require kernel packet sender identity and reject ancillary fd imports.

    A connected Unix socket may be inherited by a different sender process.
    Per-packet SCM_CREDENTIALS is mandatory. File descriptors from untrusted
    SCM_RIGHTS are never accepted or left open, even after a truncated packet.
    """
    if (type(expected_sender) is not tuple or len(expected_sender) != 3
            or any(type(v) is not int for v in expected_sender)):
        C.deny("UNPINNED_PACKET_SENDER")
    if not hasattr(socket, "MSG_CMSG_CLOEXEC"):
        C.deny("NATIVE_RECEIVED_FD_CLOSE_ON_EXEC_UNAVAILABLE")
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    data, ancillary, flags, addr = sock.recvmsg(
        MAX_IPC + 1,
        socket.CMSG_SPACE(struct.calcsize("3i"))
        + socket.CMSG_SPACE(16 * array.array("i").itemsize),
        socket.MSG_CMSG_CLOEXEC)
    # This MUST precede MSG_CTRUNC, missing-credentials and all other denials.
    _discard_unexpected_native_rights(ancillary)
    if (flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
            or addr or not data or len(data) > MAX_IPC):
        C.deny("BOUNDED_NATIVE_PACKET_REFUSED")
    credentials = []
    for level, kind, value in ancillary:
        if (level != socket.SOL_SOCKET or kind != socket.SCM_CREDENTIALS
                or len(value) != struct.calcsize("3i")):
            C.deny("UNEXPECTED_NATIVE_CONTROL_MESSAGE")
        credentials.append(struct.unpack("3i", value))
    if len(credentials) != 1 or credentials[0] != expected_sender:
        C.deny("PACKET_SENDER_DIFFERS_FROM_PINNED_SOCKET_PEER")
    return data

def _writer_exchange(policy, body):
    """Only protected dedicated PX writer receives signed grants. Never QML."""
    _socket_root_path(C.WRITER_SOCKET, policy["pxWriterUid"])
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as s:
            s.settimeout(4)
            s.connect(C.WRITER_SOCKET)
            p = _peer_writer(s)
            # Enable per-packet Linux credentials BEFORE the writer replies.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            if p[1] != policy["pxWriterUid"]:
                C.deny("WRONG_PX_WRITER_UID")
            if _executable_sha(p[0]) != policy["pxWriterExecutableSha256"]:
                C.deny("UNENROLLED_PX_WRITER_EXECUTABLE")
            payload = C.canonical(body)
            if s.send(payload) != len(payload):
                C.deny("PARTIAL_WRITER_PACKET_REFUSED")
            raw = _packet_recv(s, expected_sender=p[:3])
            if (_peer_writer(s) != p
                    or _executable_sha(p[0]) != policy["pxWriterExecutableSha256"]):
                C.deny("PX_WRITER_PROCESS_CHANGED")
            return raw
    except C.Refused:
        raise
    except (OSError, TimeoutError) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // PROTECTED_PX_WRITER_UNAVAILABLE") from exc

def _peer_writer(s):
    try:
        raw = s.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        pid, uid, gid = struct.unpack("3i", raw)
        if pid <= 1 or uid <= 0 or gid < 0:
            C.deny("WRITER_PEER_UNTRUSTED")
        start = _kernel_start(pid)
        _kernel_uid(pid, uid, gid)
        return (pid, uid, gid, start)
    except (OSError, struct.error) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // WRITER_PEER_UNAVAILABLE") from exc

def _polkit_approve(request, prepared, peer, seat):
    """Require real interactive Polkit identity check for this exact source.

    The separately approved action files must require AUTH_SELF (not KEEP).
    Success alone cannot prove a prompt appeared if system rules override it;
    installation review MUST check effective Polkit rules and the active agent.
    """
    action = request["action"]
    msg = ("%s Hospital Room %s (Patient %s, repository %s, "
           "revision %d, graph SHA-256 %s; retain original; seat %s)"
           % (action, prepared["roomId"], prepared["patientId"],
              prepared["repository"], prepared["expectedRevision"],
              prepared["expectedDigest"], seat))
    try:
        done = subprocess.run([
            POLKIT, "--action-id", POLKIT_ACTIONS[action],
            "--process", "%d,%d,%d" % (peer[0], peer[3], peer[1]),
            "--allow-user-interaction",
            "--detail", "polkit.message", msg,
            "--detail", "hospital-room-id", prepared["roomId"],
            "--detail", "hospital-action", action,
            "--detail", "hospital-graph", prepared["expectedDigest"],
            "--detail", "hospital-request-nonce", prepared["requestNonce"],
            "--detail", "hospital-writer-instance", prepared["writerInstance"],
            "--detail", "hospital-policy-generation", str(prepared["policyGeneration"]),
            "--detail", "hospital-review-expires-at", str(prepared["expiresAt"]),
            "--detail", "hospital-patient-id", prepared["patientId"],
            "--detail", "hospital-repository", prepared["repository"],
            "--detail", "hospital-revision", str(prepared["expectedRevision"]),
            "--detail", "hospital-seat-id", seat,
            "--detail", "hospital-retention", "PRESERVE_ORIGINAL_NO_BURN",
        ], capture_output=True, timeout=35, check=False)
        if done.returncode != 0:
            C.deny("OPERATOR_POLKIT_INTERACTION_NOT_APPROVED")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise C.Refused("HOSPITAL_NATIVE_HOLD // POLKIT_UNAVAILABLE") from exc

def _require_independent_room_consent(request, prepared, peer, seat):
    """Hard stop until a separately reviewed native exact-Room consent producer exists.

    A successful Polkit authorization is NOT proof that the requested Room,
    Patient, graph, nonce and preservation terms were visibly confirmed by
    the real operator. There is currently no enrolled, protected producer
    or independent one-use consent custodian. This MUST remain deny-only.

    No QML flag, Polkit exit status, environment variable, caller callback,
    locally generated key, or synthetic display claim can change this result.
    """
    C.deny("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE")


def _native_step(client, policy):
    peer = _peer(client)
    if peer[1] != policy["operatorUid"]:
        C.deny("NONOPERATOR_UID_REFUSED")
    _same_peer(client, peer, policy["clientExecutableSha256"])
    request = C.validate_request(
        _packet_recv(client, expected_sender=peer[:3]))
    _same_peer(client, peer, policy["clientExecutableSha256"])
    first_seat = _active_seat(peer[0], peer[1])
    if C.host_fingerprint() != policy["hostId"]:
        C.deny("INSTALLED_HOST_POLICY_MISMATCH")
    nonce = C.b64(os.urandom(32))
    prepare = {
        "schema": "postapollo.hospital.protected-writer-request.v1",
        "kind": "prepare", "action": request["action"],
        "roomId": request["roomId"], "requestNonce": nonce,
    }
    prepared = C.validate_prepared(
        _writer_exchange(policy, prepare), request, nonce, policy, int(time.time()))
    _same_peer(client, peer, policy["clientExecutableSha256"])
    if first_seat != _active_seat(peer[0], peer[1]):
        C.deny("OPERATOR_SESSION_CHANGED_BEFORE_CONSENT")
    _polkit_approve(request, prepared, peer, first_seat)
    _same_peer(client, peer, policy["clientExecutableSha256"])
    if first_seat != _active_seat(peer[0], peer[1]):
        C.deny("OPERATOR_SESSION_CHANGED_AFTER_CONSENT")
    if prepared["expiresAt"] <= int(time.time()):
        C.deny("PX_PREPARE_EXPIRED_AFTER_APPROVAL")
    # A long interactive Polkit prompt must not authorize a previous or
    # expired root-owned issuer policy after policy rotation/revocation.
    if C.read_policy() != policy:
        C.deny("ISSUER_POLICY_CHANGED_DURING_OPERATOR_APPROVAL")
    if C.host_fingerprint() != policy["hostId"]:
        C.deny("HOST_CHANGED_DURING_OPERATOR_APPROVAL")
    # Polkit only verifies identity/authorization. It does NOT prove that
    # a trusted native agent displayed the exact PX operation and received
    # the operator's explicit confirmation. Until independent consent is
    # enrolled and verified this call MUST always refuse, before key load.
    _require_independent_room_consent(request, prepared, peer, first_seat)
    # Future approved releases may only load the private key after an
    # independently reviewed exact-operation, single-use consent gate.
    # The protected PX writer alone may receive the resulting envelope.
    key = C.load_installed_key()
    signed = C.sign_px_grant(
        request=request, prepared=prepared, operator_uid=peer[1],
        seat_id=first_seat, host_id=policy["hostId"], private_key=key,
    )
    # Source writer must compare all fields with its current DB inside
    # BEGIN IMMEDIATE, consume one-use nonce and commit before replying.
    reply = _writer_exchange(policy, {
        "schema": "postapollo.hospital.protected-writer-request.v1",
        "kind": "commit", "action": request["action"],
        "roomId": request["roomId"], "requestNonce": nonce,
        "writerInstance": prepared["writerInstance"],
        "signedGrant": signed.decode("ascii"),
    })
    return C.validate_commit_receipt(
        reply, request=request, prepared=prepared,
        nonce=nonce, signed_grant=signed,
    )

def main():
    """Never runnable from UI or CLI: only systemd LISTEN_FDS socket path."""
    if (os.name != "posix" or not sys.platform.startswith("linux")
            or os.geteuid() != 0
            or os.environ.get("LISTEN_FDS") != "1"
            or os.environ.get("LISTEN_PID") != str(os.getpid())
            or not os.environ.get("INVOCATION_ID")):
        print("HOSPITAL_NATIVE_HOLD // NOT_APPROVED_SYSTEMD_SOCKET_RUNTIME")
        return 2
    try:
        policy = C.read_policy()
        if C.host_fingerprint() != policy["hostId"]:
            C.deny("HOST_POLICY_MISMATCH")
        _socket_root_path(SERVICE_SOCKET, 0)
        listen = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            if (listen.family != socket.AF_UNIX
                    or listen.type & 0xF != socket.SOCK_SEQPACKET):
                C.deny("UNTRUSTED_SYSTEMD_SOCKET_TYPE")
            listen.settimeout(40)
            with listen.accept()[0] as client:
                client.settimeout(40)
                # A socket-activated caller must WAIT for this READY packet.
                # Credentials on messages queued before SO_PASSCRED was set
                # are not reliable; early request packets fail closed.
                client.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
                ready = C.canonical({
                    "schema": "postapollo.connections.hospital-native-ready.v1",
                    "status": "READY",
                })
                if client.send(ready) != len(ready):
                    C.deny("NATIVE_CLIENT_HANDSHAKE_FAILED")
                response = _native_step(client, policy)
                answer = C.canonical(response)
                if client.send(answer) != len(answer):
                    C.deny("PARTIAL_CLIENT_RECEIPT_REFUSED")
        finally:
            listen.close()
        return 0
    except C.Refused as exc:
        # No grant or private key is ever logged or returned on failure.
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, TimeoutError) as exc:
        print("HOSPITAL_NATIVE_HOLD // NATIVE_IO_UNAVAILABLE", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
