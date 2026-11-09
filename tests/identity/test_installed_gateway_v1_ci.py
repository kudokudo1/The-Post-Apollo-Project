"""Disposable dpkg + systemd installed Identity gateway acceptance V1.

A real signed (CI-generated) .deb is installed by root on an ephemeral
GitHub-hosted Linux runner. A transient systemd service executes the ACTUAL
installed IdentityCommandGateway and sends real Ed25519 Unix socket receipts.
Every login command is DENIED by the fixture's immutable C5/seat gates.
A separate CI test controller holds the release-root key, independently
inspects systemd + /proc, and never supplies authority to the gateway.

NO Fedora workstation, Silverblue boot, real C5 consent, real IdP, permanent
key enrollment, production login, or test-fixture promotion is permitted.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import pwd
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from desktop_command_gateway_v0 import KernelPeer, COMMAND_SOCKET, _peer
from desktop_signed_command_client_v0 import SignedIdentityCommandClient
from installed_gateway_witness_v1 import (
    DOMAIN, PACKAGE, PREFIX, ROLE, SCHEMA, InstalledGatewayWitness,
    WitnessRefused, canonical as installed_canonical,
)
from signed_gateway_origin_probe_v0 import (
    _DOMAIN as ORIGIN_DOMAIN, SCHEMA as ORIGIN_SCHEMA, PURPOSE,
    _start_ticks, SignedGatewayOriginProbe,
    canonical as origin_canonical,
)
from signed_command_receipt_v0 import (
    build_request, verify_receipt, ReceiptRejected,
)

# Exact real modules loaded by the installed IdentityCommandGateway. No
# second OAuth stack, fake native listener or separately trusted repo copy.
MODULES = (
    "desktop_command_gateway_v0.py",
    "desktop_host_lifecycle_v0.py",
    "desktop_context_projection_v0.py",
    "desktop_session_host_v0.py",
    "native_loopback_callback_v0.py",
    "private_context_ipc_v0.py",
    "signed_command_receipt_v0.py",
)
ENTRYPOINT = "identity-gateway-ci"
SERVICE_FILE = ROOT / "tests/identity/fixtures/identity_gateway_installed_ci"
INSTALLED = Path(PREFIX + ENTRYPOINT)


def _run(*argv, timeout=20):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        # No key bytes or private diagnostic URL are printed.
        raise RuntimeError(
            f"Fixture command {argv[0]} failed ({p.returncode}): "
            + p.stderr[-350:])
    return p.stdout.strip()


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _key_digest(private):
    key_bytes = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(key_bytes).hexdigest()


def _systemctl_field(unit, key):
    data = _run("systemctl", "show", unit, "--no-pager",
                "--property=" + key)
    return data.split("=", 1)[-1]


class InstalledIdentityGatewayAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
                or os.environ.get("POST_APOLLO_ID_INSTALL_CI_ONLY") != "1"
                or os.geteuid() == 0 or sys.platform != "linux"):
            raise unittest.SkipTest("Isolated GitHub-hosted CI only")
        cls.uid, cls.gid = os.getuid(), os.getgid()
        cls.username = pwd.getpwuid(cls.uid).pw_name
        cls.py = os.path.realpath(sys.executable)
        cls.tmp = tempfile.TemporaryDirectory(prefix="identity-install-ci-")
        cls.path = Path(cls.tmp.name)
        cls.path.chmod(0o700)
        cls.runtime = cls.path / "native"
        cls.runtime.mkdir(mode=0o700)
        cls.signer_file = cls.path / "signer.ed25519"
        cls.root = Ed25519PrivateKey.generate()
        cls.signer = Ed25519PrivateKey.generate()
        cls.unit = ""
        cls.package_installed = False
        try:
            cls._assert_no_existing_fixture()
            cls._prepare_package()
            _run("sudo", "-n", "dpkg", "-i", str(cls.deb), timeout=40)
            cls.package_installed = True
            cls._assert_installed_files()
            cls._write_signer(cls.signer)
            cls._start_service("a")
            cls._refresh_observers()
        except Exception:
            cls._cleanup()
            raise

    @classmethod
    def _assert_no_existing_fixture(cls):
        q = subprocess.run(["dpkg-query", "-W", "-f=" + "$" + "{Status}",
                            PACKAGE], capture_output=True, text=True)
        if q.returncode == 0 and q.stdout == "install ok installed":
            raise RuntimeError("Refusing preexisting Identity CI package")
        if Path(PREFIX).exists():
            raise RuntimeError("Refusing preexisting Identity installation path")

    @classmethod
    def _prepare_package(cls):
        root = cls.path / "debroot"
        payload = root / PREFIX.lstrip("/")
        payload.mkdir(parents=True)
        for filename in MODULES:
            shutil.copyfile(ROOT / "services/identity" / filename,
                            payload / filename)
        shutil.copyfile(SERVICE_FILE, payload / ENTRYPOINT)
        cls.file_hashes = {}
        for file in sorted(payload.iterdir()):
            file.chmod(0o555)
            cls.file_hashes[str(Path(PREFIX) / file.name)] = _digest(file)
        control = root / "DEBIAN"
        control.mkdir(mode=0o755)
        (control / "control").write_text(
            "Package: " + PACKAGE + "\nVersion: 0.0.1\n"
            "Section: misc\nPriority: optional\nArchitecture: all\n"
            "Maintainer: Identity Center CI <ci@example.invalid>\n"
            "Description: Disposable deny-only Identity Center gateway\n")
        cls.deb = cls.path / (PACKAGE + ".deb")
        _run("dpkg-deb", "--build", "--root-owner-group",
             str(root), str(cls.deb), timeout=30)
        cls.package_sha = _digest(cls.deb)

    @classmethod
    def _assert_installed_files(cls):
        for installed, expected in cls.file_hashes.items():
            cls_match = Path(installed)
            if (_digest(cls_match) != expected or
                    (cls_match.stat().st_mode & 0o777) != 0o555 or
                    cls_match.stat().st_uid != 0):
                raise RuntimeError("Installed payload not the built package")

    @classmethod
    def _write_signer(cls, key):
        from cryptography.hazmat.primitives import serialization
        cls.signer_file.write_bytes(key.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption()))
        cls.signer_file.chmod(0o600)

    @classmethod
    def _start_service(cls, suffix):
        short_id = secrets.token_hex(4)
        cls.unit = f"post-apollo-identity-ci-{short_id}-{suffix}.service"
        _run("sudo", "-n", "systemd-run", "--collect",
             "--unit=" + cls.unit,
             "--property=User=" + cls.username,
             "--property=Group=" + str(cls.gid),
             "--setenv=GITHUB_ACTIONS=true",
             "--setenv=RUNNER_ENVIRONMENT=github-hosted",
             "--setenv=POST_APOLLO_ID_INSTALL_CI_ONLY=1",
             "--setenv=POST_APOLLO_ID_CI_RUNTIME=" + str(cls.runtime),
             "--setenv=POST_APOLLO_ID_CI_SIGNING_KEY=" + str(cls.signer_file),
             cls.py, str(INSTALLED))
        for _ in range(80):
            if (cls.runtime / COMMAND_SOCKET).is_socket():
                pid = int(_systemctl_field(cls.unit, "MainPID"))
                if pid > 1:
                    cls.pid = pid
                    return
            time.sleep(0.1)
        raise RuntimeError("Signed installed command service did not start")

    @classmethod
    def _stop_service(cls):
        if cls.unit:
            subprocess.run(["sudo", "-n", "systemctl", "stop", cls.unit],
                           capture_output=True, text=True, timeout=12)
            cls.unit = ""

    @classmethod
    def _refresh_observers(cls):
        cls.ticks = _start_ticks(cls.pid)
        cls.cgroup = _systemctl_field(cls.unit, "ControlGroup")
        cls.lsm = Path(f"/proc/{cls.pid}/attr/current").read_text().strip()
        cls.peer = KernelPeer(cls.pid, cls.uid, cls.gid)
        release = dict(
            schema=SCHEMA, role=ROLE, epoch=2, sequence=7,
            package=PACKAGE, packageSha256=cls.package_sha,
            receiptKeySha256=_key_digest(cls.signer),
            unit=cls.unit, files=cls.file_hashes,
        )
        cls.release = installed_canonical(release)
        cls.release_sig = cls.root.sign(DOMAIN + cls.release)
        cls.witness = InstalledGatewayWitness(
            signed_release=cls.release,
            release_signature=cls.release_sig,
            pinned_release_root=cls.root.public_key(),
            minimum_epoch=2, minimum_sequence=7,
            expected_pid=cls.pid, expected_start_ticks=cls.ticks,
            expected_uid=cls.uid, expected_gid=cls.gid,
            expected_cgroup=cls.cgroup, expected_lsm=cls.lsm,
            expected_receipt_key_sha256=_key_digest(cls.signer),
            expected_package_file=cls.deb)
        origin = dict(
            schema=ORIGIN_SCHEMA, purpose=PURPOSE,
            releaseEpoch=2, releaseSequence=7,
            entrypointPath=str(INSTALLED),
            entrypointSha256=cls.file_hashes[str(INSTALLED)],
            interpreterPath=cls.py,
            receiptKeySha256=_key_digest(cls.signer),
            uid=cls.uid, gid=cls.gid,
        )
        origin_raw = origin_canonical(origin)
        cls.origin = SignedGatewayOriginProbe(
            signed_policy=origin_raw,
            policy_signature=cls.root.sign(ORIGIN_DOMAIN + origin_raw),
            pinned_release_root=cls.root.public_key(),
            pinned_receipt_key=cls.signer.public_key(),
            minimum_epoch=2, minimum_sequence=7,
            expected_pid=cls.pid, expected_start_ticks=cls.ticks)

    @classmethod
    def _cleanup(cls):
        cls._stop_service()
        if cls.package_installed:
            subprocess.run(["sudo", "-n", "dpkg", "--purge", PACKAGE],
                           capture_output=True, text=True, timeout=30)
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        if Path(PREFIX).exists():
            raise AssertionError("Installed CI gateway left package residue")
        if (subprocess.run(["dpkg-query", "-W", "-f="+"$"+"{Status}",
                            PACKAGE], capture_output=True, text=True).stdout
                == "install ok installed"):
            raise AssertionError("Disposable signed package not removed")

    def _connected_peer(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(2)
            conn.connect(str(self.runtime / COMMAND_SOCKET))
            return _peer(conn)

    def _client(self, *, seat=lambda: True, trust=None, enrollment=None,
                pinned_key=None):
        return SignedIdentityCommandClient(
            socket_path=self.runtime / COMMAND_SOCKET,
            pinned_host_public_key=pinned_key or self.signer.public_key(),
            trusted_server_peer=trust or (
                lambda p: p == self.peer),
            active_seat=seat,
            enrolled_origin_consistent=enrollment or (
                lambda p: self.origin.consistent(p)
                and self.witness.consistent(p)),
        )

    def _signed_denial(self, action):
        nonce = secrets.token_urlsafe(32)
        rid = None if action == "BEGIN" else "CI_NO_LOGIN_REQUEST_01234567"
        request = build_request(action, rid, nonce)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(str(self.runtime / COMMAND_SOCKET))
            conn.sendall(request)
            raw = b""
            while not raw.endswith(b"\n"):
                fragment = conn.recv(1024)
                if not fragment:
                    break
                raw += fragment
        return verify_receipt(raw, pinned_key=self.signer.public_key(),
                              action=action, command_request_id=rid,
                              client_nonce=nonce)

    def test_a_real_signed_installed_supervised_gateway_is_deny_only(self):
        self.assertEqual(self._connected_peer(), self.peer)
        measured = self.witness.inspect(self.peer)
        self.assertTrue(measured.package_matches)
        self.assertTrue(measured.supervisor_matches)
        self.assertTrue(measured.module_bytes_match)
        self.assertFalse(measured.production_authority)
        self.assertFalse(measured.can_begin_sign_in)
        self.assertTrue(self.origin.consistent(self.peer))
        client = self._client()
        response = client.begin()
        self.assertEqual(response.phase, "UNAVAILABLE")
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            reply = self._signed_denial(action)
            self.assertEqual(reply["state"], "UNAVAILABLE")
            self.assertIsNone(reply["requestId"])
        self.assertFalse((self.runtime / "identity-display-v0.sock").exists())

    def test_b_signed_package_process_and_key_spoof_denial(self):
        self.assertFalse(self.witness.consistent(KernelPeer(
            self.pid+1, self.uid, self.gid)))
        self.assertFalse(self.witness.consistent(KernelPeer(
            self.pid, self.uid+1, self.gid)))
        self.assertFalse(self.witness.consistent(KernelPeer(
            self.pid, self.uid, self.gid+1)))
        self.assertFalse(self.origin.consistent(KernelPeer(
            self.pid+1, self.uid, self.gid)))
        with self.assertRaises(WitnessRefused):
            InstalledGatewayWitness(
                signed_release=self.release,
                release_signature=self.release_sig,
                pinned_release_root=Ed25519PrivateKey.generate().public_key(),
                minimum_epoch=2, minimum_sequence=7,
                expected_pid=self.pid, expected_start_ticks=self.ticks,
                expected_uid=self.uid, expected_gid=self.gid,
                expected_cgroup=self.cgroup, expected_lsm=self.lsm,
                expected_receipt_key_sha256=_key_digest(self.signer),
                expected_package_file=self.deb)
        self.assertFalse(self._client(seat=lambda: False).faulted)
        with self.assertRaises(ReceiptRejected):
            self._client(seat=lambda: False).begin()

    def test_c_no_revoked_supervisor_module_or_selinux_origin(self):
        def other(*, cgroup=None, lsm=None, ticks=None, package=None):
            return InstalledGatewayWitness(
                signed_release=self.release,
                release_signature=self.release_sig,
                pinned_release_root=self.root.public_key(),
                minimum_epoch=2, minimum_sequence=7,
                expected_pid=self.pid, expected_start_ticks=ticks or self.ticks,
                expected_uid=self.uid, expected_gid=self.gid,
                expected_cgroup=cgroup or self.cgroup,
                expected_lsm=lsm or self.lsm,
                expected_receipt_key_sha256=_key_digest(self.signer),
                expected_package_file=package or self.deb)
        self.assertFalse(other(cgroup=self.cgroup + "-forged").consistent(self.peer))
        self.assertFalse(other(lsm=self.lsm + "-forged").consistent(self.peer))
        self.assertFalse(other(ticks=str(int(self.ticks)+1)).consistent(self.peer))
        forged = self.path / "forged.deb"
        forged.write_bytes(self.deb.read_bytes() + b"malicious-package")
        self.assertFalse(other(package=forged).consistent(self.peer))
        # REAL chmod of the disposable installed module, then restore it.
        target = PREFIX + "desktop_session_host_v0.py"
        try:
            _run("sudo", "-n", "chmod", "0777", target)
            self.assertFalse(self.witness.consistent(self.peer))
        finally:
            _run("sudo", "-n", "chmod", "0555", target)
        self.assertTrue(self.witness.consistent(self.peer))

    def test_z_restart_and_receipt_key_rotation_require_new_enrollment(self):
        previous_pid = self.pid
        old_witness = self.witness
        old_origin = self.origin
        old_key = self.signer
        old_client = self._client()
        self._stop_service()
        self.assertFalse(old_witness.consistent(self.peer))
        self.signer = Ed25519PrivateKey.generate()
        self._write_signer(self.signer)
        self._start_service("rotated")
        self.assertNotEqual(self.pid, previous_pid)
        # Neither OLD process evidence nor OLD signer key can be retained.
        new_peer = self._connected_peer()
        self.assertEqual(new_peer.pid, self.pid)
        self.assertFalse(old_witness.consistent(new_peer))
        self.assertFalse(old_origin.consistent(new_peer))
        with self.assertRaises(ReceiptRejected):
            old_client.begin()
        # New receipt from installed gateway is also rejected by old key,
        # even if an attacker supplies an approval-looking JSON envelope.
        nonce = secrets.token_urlsafe(32)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(str(self.runtime / COMMAND_SOCKET))
            conn.sendall(build_request("BEGIN", None, nonce))
            raw = b""
            while not raw.endswith(b"\n"):
                raw += conn.recv(1024)
        with self.assertRaises(ReceiptRejected):
            verify_receipt(raw, pinned_key=old_key.public_key(),
                           action="BEGIN", command_request_id=None,
                           client_nonce=nonce)
        # Only the independent authority's NEW enrollment makes fresh
        # module/PID/start/unit/key observations coherent again in CI.
        self._refresh_observers()
        self.assertTrue(self.witness.consistent(new_peer))
        self.assertTrue(self.origin.consistent(new_peer))
        self.assertEqual(self._client().begin().phase, "UNAVAILABLE")
        self.assertFalse((self.runtime / "identity-display-v0.sock").exists())


if __name__ == "__main__":
    unittest.main()
