#!/usr/bin/env python3
"""DOC 2 C4b: observe an actual installed disposable Forest host, NOT enrollment."""
import array
import hashlib
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import subprocess
import sys
import unittest

HOST = Path("/usr/libexec/post-apollo/forest-ci/forest-host")
PYTHON = "/usr/bin/python3"
SELF = "/ci/test_c4b_forest_installed_source_ci.py"
OWNER, RENDERER = 61001, 61003
SHA = os.environ.get("EXPECTED_SOURCE_SHA", "")
BOOT = Path("/proc/sys/kernel/random/boot_id")
HOLD = {
    "schema": "post-apollo.forest.b5b-ci-only", "status": "UNKNOWN_HOLD",
    "sourceAuthenticated": False, "recipientAuthenticated": False,
    "permissionGranted": False, "productionAuthority": False,
    "privateBytesSubmitted": 0, "revocationFencedAck": False, "safeActions": [],
}
TOKENS = {
    "STATUS": (0, True), "LIST_SESSIONS": (0, True),
    "DISCLOSE_PROVISIONAL": (0, True), "RIGHTS": (2, False),
    "STOP": (2, False), "PRIVATE_NOT_ALLOWED": (2, False),
}
DENIED = {
    "independentForestSourceEnrollment": False,
    "operatorEnrolledReleaseRoot": False,
    "protectedHistoryAndChallenge": False,
    "activeUnlockedSeat": False,
    "authenticatedOriginalRecipient": False,
    "protectedPrivateDbCustody": False,
    "forestC5Consent": False,
    "settledOriginalTerminalReceipt": False,
    "privateTitleRead": False,
    "privateBytesEgress": False,
    "productionSignIn": False,
    "safeRetry": False,
}

class Refused(ValueError):
    pass

def ci_guard():
    if (os.environ.get("GITHUB_ACTIONS") != "true" or
            not Path("/.dockerenv").exists() or
            os.getuid() != 0 or os.geteuid() != 0 or
            not re.fullmatch(r"[0-9a-f]{64}", SHA)):
        raise RuntimeError("C4B_FOREST_DISPOSABLE_ROOT_GITHUB_CI_ONLY")

def ids(pid):
    rows = Path("/proc", str(pid), "status").read_text().splitlines()
    return {k: tuple(int(x) for x in next(
        row for row in rows if row.startswith(k + ":")).split()[1:])
        for k in ("Uid", "Gid")}

def ticks(pid):
    # Linux /proc/PID/stat field 22; after the last ') ' field 3 is index 0.
    val = int(Path("/proc", str(pid), "stat").read_text().rsplit(") ", 1)[1].split()[19])
    if val <= 0:
        raise Refused("C4B_INVALID_PROCESS_START")
    return val

def boot_id():
    v = BOOT.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", v):
        raise Refused("C4B_KERNEL_BOOT_ID_UNAVAILABLE")
    return v

def installed_sha():
    f, d = HOST.lstat(), HOST.parent.lstat()
    if ((not stat.S_ISREG(f.st_mode)) or (f.st_uid, f.st_gid,
          stat.S_IMODE(f.st_mode)) != (0, 0, 0o555) or
          not stat.S_ISDIR(d.st_mode) or (d.st_uid, d.st_gid,
          stat.S_IMODE(d.st_mode)) != (0, 0, 0o755)):
        raise Refused("C4B_UNEXPECTED_INSTALLED_SOURCE")
    return hashlib.sha256(HOST.read_bytes()).hexdigest()

def fd_links(pid):
    values = []
    for entry in Path("/proc", str(pid), "fd").iterdir():
        try:
            values.append(os.readlink(entry))
        except FileNotFoundError:
            continue
    return values

def observe(*, pid, host_fd, host_inode, renderer_pid, renderer_inode,
            start, boot, source_sha, uid):
    """A pinned disposable CI source observation; never a protected identity."""
    try:
        if (type(pid) is not int or type(uid) is not int or
                type(start) is not int or type(host_fd) is not int or
                type(host_inode) is not int or type(renderer_pid) is not int or
                type(renderer_inode) is not int or pid == renderer_pid or
                uid != OWNER or start != ticks(pid) or boot != boot_id() or
                source_sha != SHA or installed_sha() != SHA):
            raise Refused("C4B_FOREST_SOURCE_PIN_MISMATCH_HOLD")
        p = Path("/proc", str(pid))
        q = Path("/proc", str(renderer_pid))
        if (ids(pid) != {"Uid": (OWNER,) * 4, "Gid": (OWNER,) * 4} or
                ids(renderer_pid) != {"Uid": (RENDERER,) * 4,
                                       "Gid": (RENDERER,) * 4} or
                os.readlink(p / "exe") != os.path.realpath(PYTHON) or
                os.readlink(q / "exe") != os.path.realpath(PYTHON)):
            raise Refused("C4B_FOREST_WRONG_PROCESS_UID_OR_EXE_HOLD")
        argv = (p / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        if argv != [PYTHON.encode(), b"-I", b"-B", str(HOST).encode(),
                    b"--disposable-test-fd", str(host_fd).encode()]:
            raise Refused("C4B_FOREST_NOT_ORIGINAL_INSTALLED_SCRIPT_HOLD")
        if (os.readlink(p / "fd" / str(host_fd)) != f"socket:[{host_inode}]" or
                f"socket:[{renderer_inode}]" in fd_links(pid) or
                f"socket:[{host_inode}]" in fd_links(renderer_pid) or
                f"socket:[{renderer_inode}]" not in fd_links(renderer_pid) or
                not (p / "cgroup").read_text().strip()):
            raise Refused("C4B_FOREST_ORIGINAL_CHANNEL_NOT_PINNED_HOLD")
    except Refused:
        raise
    except (OSError, ValueError, IndexError, StopIteration) as error:
        # CI-only diagnostics: retain the real kernel refusal as exception cause.
        raise Refused("C4B_FOREST_KERNEL_EVIDENCE_UNAVAILABLE_HOLD") from error
    return {
        "status": "ACTUAL_CI_HOST_PROCESS_OBSERVED_NOT_ENROLLED_HOLD",
        "ciOnlyActualInstalledSourceBytesMatch": True,
        "ciOnlyKernelProcessAndFdObserved": True,
        "ciOnlyDistinctRendererUidObserved": True,
        **DENIED,
    }

def renderer_main(args):
    if os.environ.get("GITHUB_ACTIONS") != "true" or len(args) != 3 or os.getuid() != RENDERER:
        return 2
    try:
        fd, gate, token = int(args[0]), int(args[1]), args[2]
        if token not in TOKENS:
            return 2
        with socket.socket(fileno=fd) as s:
            s.settimeout(7)
            if os.read(gate, 1) != b"G":
                return 2
            os.close(gate)
            if token == "RIGHTS":
                extra = os.memfd_create("public-ci-rights")
                try:
                    s.sendmsg([b"STATUS"], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                           array.array("i", [extra]))])
                finally:
                    os.close(extra)
            else:
                s.sendall(token.encode())
            wire = s.recv(4096)
            _, allow_public = TOKENS[token]
            if allow_public:
                if json.loads(wire) != HOLD or s.recv(4096) != b"":
                    return 2
            elif wire != b"":
                return 2
            return 0
    except (OSError, ValueError):
        return 2

def spawn(uid, args, descriptors):
    return subprocess.Popen(
        args, user=uid, group=uid, extra_groups=[], umask=0o077, cwd="/",
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True, pass_fds=descriptors,
        env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent",
             "LC_ALL": "C", "GITHUB_ACTIONS": "true"})

def wait(child):
    try:
        return child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)
        raise AssertionError("ORIGINAL_PROCESS_TIMEOUT_NO_RETRY") from None

class C4bActualInstalledSourceCI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ci_guard()
        if installed_sha() != SHA:
            raise RuntimeError("C4B_SOURCE_CHECKOUT_AND_RPM_BYTES_DIFFER")

    def scenario(self, token, negative=None):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        gate_read, gate_write = os.pipe()
        host = renderer = None
        pidfd = None
        try:
            host_fd, renderer_fd = b.fileno(), a.fileno()
            host_inode, renderer_inode = os.fstat(host_fd).st_ino, os.fstat(renderer_fd).st_ino
            host = spawn(OWNER, [PYTHON, "-I", "-B", str(HOST),
                                 "--disposable-test-fd", str(host_fd)], (host_fd,))
            renderer = spawn(RENDERER, [PYTHON, "-I", "-B", SELF, "--renderer",
                                       str(renderer_fd), str(gate_read), token],
                             (renderer_fd, gate_read))
            a.close()
            b.close()
            os.close(gate_read)
            gate_read = -1
            pidfd = os.pidfd_open(host.pid)
            poller = select.poll()
            poller.register(pidfd, select.POLLIN)
            self.assertEqual(poller.poll(0), [])
            pinned_boot, pinned_ticks = boot_id(), ticks(host.pid)
            args = dict(pid=host.pid, host_fd=host_fd, host_inode=host_inode,
                        renderer_pid=renderer.pid, renderer_inode=renderer_inode,
                        start=pinned_ticks, boot=pinned_boot, source_sha=SHA, uid=OWNER)
            record = observe(**args)
            for flag in DENIED:
                self.assertIs(record[flag], False, flag)
            if negative:
                negative(args)
            self.assertEqual(observe(**args), record)  # second LIVE observation
            os.write(gate_write, b"G")
            os.close(gate_write)
            gate_write = -1
            self.assertEqual(wait(renderer), 0, "RENDERER_FAILED")
            self.assertEqual(wait(host), TOKENS[token][0], "ORIGINAL_HOST_FAILED")
            self.assertTrue(poller.poll(1000), "ORIGINAL_PIDFD_NOT_TERMINATED")
            self.assertEqual(installed_sha(), SHA)
            self.assertEqual(boot_id(), pinned_boot)
        finally:
            if gate_read >= 0:
                os.close(gate_read)
            if gate_write >= 0:
                os.close(gate_write)
            a.close()
            b.close()
            if pidfd is not None:
                os.close(pidfd)
            for child in (renderer, host):
                if child:
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)

    def test_01_actual_installed_process_and_renderer_status(self):
        self.scenario("STATUS")

    def test_02_list_sessions_still_public_hold(self):
        self.scenario("LIST_SESSIONS")

    def test_03_provisional_output_still_public_hold(self):
        self.scenario("DISCLOSE_PROVISIONAL")

    def test_04_scm_rights_refused_no_ack(self):
        self.scenario("RIGHTS")

    def test_05_stop_not_protected_revocation_ack(self):
        self.scenario("STOP")

    def test_06_private_like_unknown_command_refused(self):
        self.scenario("PRIVATE_NOT_ALLOWED")

    def test_07_tampered_kernel_process_boot_source_pins_refused(self):
        def negative(a):
            for k, bad in (("pid", a["renderer_pid"]), ("start", a["start"] + 1),
                           ("boot", "00000000-0000-0000-0000-000000000000"),
                           ("source_sha", "0" * 64), ("uid", RENDERER)):
                with self.subTest(pin=k), self.assertRaises(Refused):
                    observe(**{**a, k: bad})
        self.scenario("STATUS", negative)

    def test_08_swapped_socket_and_renderer_identity_refused(self):
        def negative(a):
            for k, bad in (("host_inode", a["renderer_inode"]),
                           ("renderer_inode", a["host_inode"]),
                           ("host_fd", a["host_fd"] + 200),
                           ("renderer_pid", a["pid"])):
                with self.subTest(pin=k), self.assertRaises(Refused):
                    observe(**{**a, k: bad})
        self.scenario("STATUS", negative)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--renderer":
        sys.exit(renderer_main(sys.argv[2:]))
    if len(sys.argv) != 1:
        sys.exit(2)
    unittest.main(verbosity=2)
