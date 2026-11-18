"""B2B19: two real AF_UNIX peer processes + signed native origin + V2 fsync.

All sockets, keys, source bytes and processes are disposable. This is NOT
an authenticated QML receiving channel, nor an installed Clock owner.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/time/AlarmKernelPairedFinalWitness.py"
HARNESS = ROOT / "tests/time/test_clock_bg1_b2b10_native_supervisor.py"
QML = ROOT / "services/time/AlarmManagerService.qml"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


Pair = load(MODULE, "clock_b2b19_actual_kernel_pair")
Fixture = load(HARNESS, "clock_b2b19_signed_harness")
Role = Fixture.Role

CLIENT = """
import socket,sys
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.connect(sys.argv[1])
sys.stdout.write("CONNECTED\\\\n")
sys.stdout.flush()
sys.stdin.buffer.read(1)
s.close()
""".replace('CONNECTED\\\\n', 'CONNECTED\\n')


class ClockPairedKernelHandoffTests(unittest.TestCase):
    def setUp(self):
        self.h = Fixture.ClockNativeSupervisorTests(
            methodName="test_real_af_unix_signed_client_is_only_observed_never_authorized")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.root = self.h.root
        self.h.script.write_text(CLIENT, encoding="utf-8")
        self.h.script.chmod(0o600)
        self.qml_script = self.root / "qml-process-standin.py"
        self.qml_script.write_text(CLIENT, encoding="utf-8")
        self.qml_script.chmod(0o600)
        self.socket_path = self.root / "clock-paired-test.sock"
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(str(self.socket_path))
        self.listener.listen(3)
        self.listener.settimeout(4)
        self.addCleanup(self.listener.close)
        self.native = None
        self.qml = None
        self.native_conn = None
        self.qml_conn = None
        self.pair = None
        self.addCleanup(self.cleanup_peers)

        self.source_dir = self.root / Pair.Final.DISPOSABLE_PARENT
        self.source_dir.mkdir(mode=0o700)
        self.source = self.source_dir / Pair.Final.SOURCE_NAME
        self.raw = (json.dumps({
            "version": 2, "nextId": 2,
            "alarms": [{"id": 1, "name": "PRIVATE TEST TITLE"}]
        }, indent=2) + "\n").encode()
        self.source.write_bytes(self.raw)
        self.source.chmod(0o600)
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def cleanup_peers(self):
        if self.pair is not None:
            self.pair.close()
        for conn in (self.native_conn, self.qml_conn):
            if conn is not None:
                conn.close()
        for proc in (self.native, self.qml):
            if proc is not None:
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate(timeout=3)

    def connect_child(self, path, *, native, extra=()):
        argv = [self.h.exe, "-I", "-B", str(path),
                str(self.socket_path), *extra]
        if native:
            self.h.write_trust(argv)
        child = subprocess.Popen(argv, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        conn, _ = self.listener.accept()
        ready = child.stdout.readline()
        self.assertEqual(ready, b"CONNECTED\n")
        ticks = Role._Peer._start_ticks(child.pid)
        return child, conn, ticks

    def start_pair(self, *, native_pin_updates=None, qml_pin_updates=None,
                   sign_native=True):
        self.native, self.native_conn, native_ticks = self.connect_child(
            self.h.script, native=sign_native)
        self.qml, self.qml_conn, qml_ticks = self.connect_child(
            self.qml_script, native=False, extra=("standin",))
        native_data = dict(
            pid=self.native.pid, ticks=native_ticks,
            executable=self.h.exe, trust_directory=str(self.h.trust),
            pinned_root_sha256=self.h.fingerprint, epoch=5, sequence=12)
        native_data.update(native_pin_updates or {})
        qml_data = dict(pid=self.qml.pid, ticks=qml_ticks,
                        executable=self.h.exe)
        qml_data.update(qml_pin_updates or {})
        self.pair = Pair.ClockKernelPairedFinalWitness(
            native_pin=Pair.NativePin(**native_data),
            qml_pin=Pair.QmlProcessPin(**qml_data),
            source_path=self.source, source_digest=self.digest,
            source_uid=os.getuid(), synthetic_only=True)
        return self.pair

    def assert_denied(self, action, reason):
        with self.assertRaises(Pair.Refused) as result:
            action()
        self.assertEqual(str(result.exception), reason)

    def assert_no_rights(self, record):
        self.assertIs(record["ok"], False)
        for field in Pair.NO_AUTHORITY:
            self.assertEqual(record[field], Pair.NO_AUTHORITY[field], field)

    def acknowledge_pair(self, pair):
        nonce = pair.prepare_pair_challenge()
        self.assertRegex(nonce, r"^[0-9a-f]{64}$")
        confirmed = pair.acknowledge_pair_challenge(nonce)
        self.assertTrue(confirmed["oneUseNativeRoundTripObserved"])
        self.assert_no_rights(confirmed)
        return nonce

    def test_real_two_process_pair_and_final_source_sync_are_observation_only(self):
        pair = self.start_pair()
        pair.connect_native(self.native_conn)
        pair.connect_qml_standin(self.qml_conn)
        result = pair.inspect_pair()
        self.assertTrue(result["signedNativeOriginObserved"])
        self.assertTrue(result["qmlKernelPeerObserved"])
        self.assertTrue(result["pairedProcessesAlive"])
        self.assert_no_rights(result)
        self.assertFalse(result["oneUseNativeRoundTripObserved"])
        self.acknowledge_pair(pair)
        final = pair.inspect_final_candidate(
            candidate_generation=7, expected_generation=7,
            candidate_digest=self.digest)
        self.assertTrue(final["candidateGenerationMatchesPin"])
        self.assertTrue(final["fileSyncObserved"])
        self.assertTrue(final["parentDirectorySyncObserved"])
        self.assert_no_rights(final)
        packet = json.dumps(final)
        for sensitive in (self.digest, str(self.source), "PRIVATE TEST TITLE",
                          str(self.h.trust)):
            self.assertNotIn(sensitive, packet)

    def test_unsigned_or_wrong_release_root_native_refuses_before_pairing(self):
        pair = self.start_pair(native_pin_updates={"pinned_root_sha256": "f"*64})
        self.assert_denied(lambda: pair.connect_native(self.native_conn),
                           "SIGNED_NATIVE_ORIGIN_NOT_OBSERVED")
        self.assert_denied(lambda: pair.connect_qml_standin(self.qml_conn),
                           "SIGNED_NATIVE_REQUIRED_FIRST")
        self.assert_denied(pair.inspect_pair, "BOTH_PINNED_PEERS_REQUIRED")

    def test_wrong_native_process_start_ticks_refuses(self):
        pair = self.start_pair(native_pin_updates={"ticks": 1})
        self.assert_denied(
            lambda: pair.connect_native(self.native_conn),
            "KERNEL_PEER_DOES_NOT_MATCH_PIN")

    def test_wrong_qml_process_start_ticks_refuses(self):
        pair = self.start_pair(qml_pin_updates={"ticks": 1})
        pair.connect_native(self.native_conn)
        self.assert_denied(
            lambda: pair.connect_qml_standin(self.qml_conn),
            "KERNEL_PEER_DOES_NOT_MATCH_PIN")

    def test_one_use_pair_challenge_replay_and_wrong_nonce_refuse(self):
        pair = self.start_pair()
        pair.connect_native(self.native_conn)
        pair.connect_qml_standin(self.qml_conn)
        original = pair.prepare_pair_challenge()
        wrong = ("f" if original[0] != "f" else "e") + original[1:]
        self.assert_denied(
            lambda: pair.acknowledge_pair_challenge(wrong),
            "CLOCK_BRIDGE_CHALLENGE_MISMATCH")
        self.assert_denied(
            lambda: pair.acknowledge_pair_challenge(original),
            "CLOCK_BRIDGE_CHALLENGE_NOT_PENDING")
        self.assert_denied(
            pair.prepare_pair_challenge,
            "CLOCK_BRIDGE_CHALLENGE_ALREADY_ISSUED")
        self.assert_denied(
            lambda: pair.inspect_final_candidate(
                candidate_generation=3, expected_generation=3,
                candidate_digest=self.digest),
            "ONE_USE_NATIVE_ROUND_TRIP_REQUIRED")

    def test_distinct_process_roles_required_at_construction(self):
        self.native, self.native_conn, native_ticks = self.connect_child(
            self.h.script, native=True)
        pin = Pair.NativePin(
            pid=self.native.pid, ticks=native_ticks, executable=self.h.exe,
            trust_directory=str(self.h.trust),
            pinned_root_sha256=self.h.fingerprint, epoch=5, sequence=12)
        qml = Pair.QmlProcessPin(
            pid=self.native.pid, ticks=native_ticks, executable=self.h.exe)
        self.assert_denied(lambda: Pair.ClockKernelPairedFinalWitness(
            native_pin=pin, qml_pin=qml, source_path=self.source,
            source_digest=self.digest, source_uid=os.getuid(),
            synthetic_only=True), "CLOCK_PEER_ROLES_NOT_SEPARATE")

    def test_native_and_qml_pidfd_exit_invalidate_pair(self):
        pair = self.start_pair()
        pair.connect_native(self.native_conn)
        pair.connect_qml_standin(self.qml_conn)
        self.assertTrue(pair.inspect_pair()["pairedProcessesAlive"])
        self.qml.terminate()
        self.qml.wait(timeout=3)
        self.assert_denied(pair.inspect_pair,
                           "CLOCK_PAIRED_PROCESS_CONTINUITY_LOST")

    def test_altered_signed_native_manifest_refuses_after_admission(self):
        pair = self.start_pair()
        pair.connect_native(self.native_conn)
        pair.connect_qml_standin(self.qml_conn)
        self.assertTrue(pair.inspect_pair()["signedNativeOriginObserved"])
        self.h.signature_file.write_bytes(b"0"*64)
        self.h.signature_file.chmod(0o600)
        self.assert_denied(pair.inspect_pair,
                           "CLOCK_PAIRED_PROCESS_CONTINUITY_LOST")

    def test_final_candidate_cannot_supply_authority_or_source_pins(self):
        pair = self.start_pair()
        pair.connect_native(self.native_conn)
        pair.connect_qml_standin(self.qml_conn)
        self.acknowledge_pair(pair)
        for kwargs in (
            dict(candidate_generation=3, expected_generation=4,
                 candidate_digest=self.digest),
            dict(candidate_generation=True, expected_generation=1,
                 candidate_digest=self.digest),
            dict(candidate_generation=3, expected_generation=3,
                 candidate_digest="f"*64),
            dict(candidate_generation=-1, expected_generation=-1,
                 candidate_digest=self.digest),
        ):
            with self.subTest(kwargs=kwargs):
                self.assert_denied(
                    lambda: pair.inspect_final_candidate(**kwargs),
                    "FINAL_CANDIDATE_NOT_INDEPENDENTLY_BOUND")

    def test_file_mutation_after_pairing_refuses_final_sync(self):
        pair = self.start_pair()
        pair.connect_native(self.native_conn)
        pair.connect_qml_standin(self.qml_conn)
        self.acknowledge_pair(pair)
        self.source.write_bytes(b'{"version":2,"nextId":1,"alarms":[]}\n')
        self.source.chmod(0o600)
        before = self.source.read_bytes()
        self.assert_denied(lambda: pair.inspect_final_candidate(
            candidate_generation=5, expected_generation=5,
            candidate_digest=self.digest), "FINAL_SOURCE_SYNC_NOT_OBSERVED")
        self.assertEqual(self.source.read_bytes(), before)

    def test_uninstalled_production_constructor_is_impossible(self):
        with self.assertRaisesRegex(Pair.Refused,
                                    "PRODUCTION_QML_CONTROL_NOT_IMPLEMENTED"):
            Pair.ClockKernelPairedFinalWitness(
                native_pin=None, qml_pin=None,
                source_path=None, source_digest=None,
                source_uid=os.getuid(), synthetic_only=False)

    def test_explicitly_no_qml_receiver_activation_or_old_writer_stop(self):
        qml = QML.read_text(encoding="utf-8")
        self.assertIn('readonly property bool nativeWriterDrainBridgeInstalled: false',qml)
        self.assertIn('readonly property string alarmWriterBarrierPhase: "ACTIVE"',qml)
        self.assertNotIn('function authorizeAlarmWriter(',qml)
        self.assertEqual(qml.count("alarmFile.setText("),1)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode),0o600)


if __name__ == "__main__":
    unittest.main()
