"""Clock BG1-B2B2 independently signed role-origin measurement (CI only)."""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/time/AlarmSignedRoleOrigin.py"
PEER = ROOT / "services/time/AlarmPeerIdentity.py"
BROKER = ROOT / "services/time/AlarmOwnershipBroker.py"
LIVE = ROOT / "services/time/AlarmManagerService.qml"
B0 = ROOT / "services/time/AlarmBackgroundObserver.py"
spec = importlib.util.spec_from_file_location("clock_signed_role_probe", MODULE)
Probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = Probe
spec.loader.exec_module(Probe)
peer_spec = importlib.util.spec_from_file_location("clock_peer_identity_test", PEER)
Peer = importlib.util.module_from_spec(peer_spec)
peer_spec.loader.exec_module(Peer)


class ClockSignedRoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clock-b2b2-ci-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.sock_path = str(self.directory / "bg1-ci.sock")
        self.entrypoint = self.directory / "clock-ci-bridge.py"
        self.entrypoint.write_text(
            "import socket,sys,time\n"
            "sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
            "sock.connect(sys.argv[1]);sock.sendall(b'R')\n"
            "time.sleep(60)\n", encoding="utf-8")
        self.entrypoint.chmod(0o644)
        self.interpreter = os.path.realpath(sys.executable)
        self.argv = [self.interpreter, "-I", "-B",
                     str(self.entrypoint), self.sock_path]
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(self.sock_path)
        self.listener.listen(1)
        self.listener.settimeout(5)
        self.process = subprocess.Popen(
            self.argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE)
        self.addCleanup(self.stop_process)
        self.connection, _ = self.listener.accept()
        self.addCleanup(self.connection.close)
        self.connection.settimeout(5)
        self.assertEqual(self.connection.recv(1), b"R")
        self.witness = Peer.capture(self.connection, self.interpreter)
        self.addCleanup(Peer.close, self.witness)
        self.root = Ed25519PrivateKey.generate()
        self.policy = {
            "schema": Probe.SCHEMA,
            "purpose": Probe.PURPOSE,
            "role": "clock-ui-bridge",
            "releaseEpoch": 5,
            "releaseSequence": 14,
            "entrypointPath": str(self.entrypoint),
            "entrypointSha256": hashlib.sha256(
                self.entrypoint.read_bytes()).hexdigest(),
            "interpreterPath": self.interpreter,
            "argv": self.argv,
            "uid": os.getuid(),
            "gid": os.getgid(),
        }

    def stop_process(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate(timeout=3)

    def probe(self, *, fields=None, signing_key=None,
              expected_role="clock-ui-bridge", floor=(5, 14),
              pinned_pid=None, pinned_ticks=None, disposable=True,
              signature=None, signed_bytes=None):
        body = Probe.canonical(fields or self.policy) if signed_bytes is None else signed_bytes
        signer = self.root if signing_key is None else signing_key
        return Probe.SignedClockRoleProbe(
            signed_policy=body,
            policy_signature=signer.sign(Probe.DOMAIN + body)
                if signature is None else signature,
            pinned_release_root=self.root.public_key(),
            expected_role=expected_role,
            minimum_epoch=floor[0], minimum_sequence=floor[1],
            expected_pid=self.process.pid if pinned_pid is None else pinned_pid,
            expected_start_ticks=self.witness["ticks"] if pinned_ticks is None else pinned_ticks,
            disposable_test_mode=disposable)

    def denied(self, fn, reason):
        with self.assertRaises(Probe.Refused) as ctx:
            fn()
        self.assertEqual(str(ctx.exception), reason)

    def test_real_kernel_peer_matches_independently_signed_ci_role(self):
        observation = self.probe().inspect(self.connection, self.witness)
        self.assertIsInstance(observation, Probe.ClockRoleOriginObservation)
        self.assertEqual(observation.role, "clock-ui-bridge")
        self.assertEqual((observation.release_epoch, observation.release_sequence),
                         (5, 14))
        self.assertEqual(observation.observed_pid, self.process.pid)
        self.assertTrue(observation.signature_verified)
        self.assertTrue(observation.process_verified)
        self.assertFalse(observation.role_authenticated)
        self.assertFalse(observation.can_write_alarm_file)
        self.assertFalse(observation.can_ring)
        self.assertFalse(observation.can_notify)
        self.assertTrue(self.probe().consistent(self.connection, self.witness))

    def test_signer_purpose_role_and_downgrade_do_not_cross_boundaries(self):
        self.denied(lambda: self.probe(signing_key=Ed25519PrivateKey.generate()),
                    "UNTRUSTED_RELEASE_SIGNATURE")
        self.denied(lambda: self.probe(expected_role="clock-background-worker"),
                    "WRONG_SIGNED_CLOCK_ROLE")
        self.denied(lambda: self.probe(floor=(5, 15)), "SIGNED_RELEASE_ROLLBACK")
        self.denied(lambda: self.probe(floor=(6, 1)), "SIGNED_RELEASE_ROLLBACK")
        for change in [
            {"purpose": "post-apollo.identity.native-command-gateway.v0"},
            {"schema": "post-apollo.identity.gateway-enrollment.experimental-v0"},
            {"role": "identity-gateway"},
            {"role": ["clock-ui-bridge"]},
            {"uid": True},
            {"releaseSequence": False},
            {"entrypointPath": "/../../tmp/clock"},
            {"argv": [self.interpreter, "-c", "print(1)", str(self.entrypoint)]},
            {"unexpectedAuthority": True},
        ]:
            with self.subTest(change=change):
                self.denied(lambda: self.probe(fields=dict(self.policy, **change)),
                            "SIGNED_POLICY_IDENTITY" if
                            any(k in change for k in ("purpose", "schema", "role",
                                                      "uid", "releaseSequence")) else
                            "SIGNED_PATH_INVALID" if "entrypointPath" in change else
                            "SIGNED_ARGV_INVALID" if "argv" in change else
                            "SIGNED_POLICY_FIELDS")
        self.denied(lambda: self.probe(signature=b"\x00" * 64),
                    "UNTRUSTED_RELEASE_SIGNATURE")
        self.denied(lambda: self.probe(expected_role=["clock-ui-bridge"]),
                    "INDEPENDENT_ROLE_PINS_REQUIRED")

    def test_canonical_policy_and_pinned_independent_pid_required(self):
        self.denied(lambda: self.probe(
            signed_bytes=b'{"purpose":"test","purpose":"admin"}'),
            "SIGNED_POLICY_JSON")
        self.denied(lambda: self.probe(
            signed_bytes=b" " + Probe.canonical(self.policy)),
            "NONCANONICAL_SIGNED_POLICY")
        self.denied(lambda: self.probe(pinned_pid=self.process.pid + 1).inspect(
            self.connection, self.witness), "INDEPENDENT_PROCESS_WITNESS_MISMATCH")
        self.denied(lambda: self.probe(pinned_ticks=self.witness["ticks"] + 1).inspect(
            self.connection, self.witness), "INDEPENDENT_PROCESS_WITNESS_MISMATCH")
        changed = dict(self.witness, uid=self.witness["uid"] + 1)
        self.denied(lambda: self.probe().inspect(self.connection, changed),
                    "INDEPENDENT_PROCESS_WITNESS_MISMATCH")

    def test_real_script_and_cmdline_measurement_refuses_tampering(self):
        good = self.probe()
        self.assertTrue(good.consistent(self.connection, self.witness))
        bad_argv = dict(self.policy, argv=self.argv + ["--unexpected"])
        self.denied(lambda: self.probe(fields=bad_argv).inspect(
            self.connection, self.witness), "UNENROLLED_PROCESS_ARGV")
        original = self.entrypoint.read_text()
        self.entrypoint.write_text(original + "# unapproved change\n")
        self.denied(lambda: good.inspect(self.connection, self.witness),
                    "SIGNED_ENTRYPOINT_DIGEST_MISMATCH")
        self.entrypoint.unlink()
        other = self.directory / "other.py"
        other.write_text(original)
        self.entrypoint.symlink_to(other)
        self.denied(lambda: good.inspect(self.connection, self.witness),
                    "ENTRYPOINT_UNREADABLE")

    def test_disposable_signed_fixture_never_proves_installed_production_role(self):
        production = self.probe(disposable=False)
        self.denied(lambda: production.inspect(self.connection, self.witness),
                    "UNAPPROVED_INSTALL_PREFIX")
        self.assertFalse(production.consistent(self.connection, self.witness))
        # The signed manifest alone cannot create an installed trusted binary.
        self.assertFalse(self.probe().inspect(self.connection, self.witness).can_ring)

    def test_exited_peer_refused_even_with_valid_signature(self):
        signed = self.probe()
        self.assertTrue(signed.consistent(self.connection, self.witness))
        self.process.terminate()
        self.process.wait(timeout=3)
        self.denied(lambda: signed.inspect(self.connection, self.witness),
                    "KERNEL_PEER_UNVERIFIED")

    def test_no_broker_actuation_or_live_role_permissions(self):
        signed = MODULE.read_text()
        broker = BROKER.read_text()
        observer = B0.read_text()
        shell = LIVE.read_text()
        for forbidden in ("notify-send", "SoundEffect", "systemctl",
                          "saveAlarm(", "ringAlarm(", "execDetached("):
            self.assertNotIn(forbidden, signed)
        self.assertIn('"roleAuthenticated": False', broker)
        self.assertIn('"actuationEnabled": False', broker)
        self.assertIn('"ownsAlarmFile": False', broker)
        self.assertNotIn("AlarmSignedRoleOrigin", broker)
        self.assertNotIn("AlarmSignedRoleOrigin", shell)
        self.assertNotIn("AlarmSignedRoleOrigin", observer)


if __name__ == "__main__":
    unittest.main()
