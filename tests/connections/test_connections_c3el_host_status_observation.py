#!/usr/bin/env python3
"""C3e-L: test host verifies caller; client also checks the *actual* host peer.

Use only in the disposable GitHub runner via sudo -n. The executable and
trusted bootstrap pins are synthetic and do NOT establish production authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"
SOURCE = HERE / "C3eLHostStatusObservation.py"
KTEST = ROOT / "tests/connections/test_connections_c3ek_protected_witness.py"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

adapter = load("c3el_observation", SOURCE)
k = load("c3el_previous_k", KTEST)

CLIENT = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import C3eLHostStatusObservation as adapter
print("READY", flush=True)
pins = json.loads(sys.stdin.readline())
try:
    evidence = adapter.observe(**pins)
    print(json.dumps({"evidence": evidence}), flush=True)
except adapter.Refused as err:
    print(json.dumps({"refused": str(err),
                      "hostAuthenticated": False,
                      "credentialActionsEnabled": False}), flush=True)
'''


class C3eLHostStatusObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.geteuid() != 0 or not sys.platform.startswith("linux"):
            raise RuntimeError("C3EL_DISPOSABLE_CI_ROOT_REQUIRED")
        k.C3eKProtectedWitnessTests.setUpClass()

    def setUp(self):
        self.fx = k.C3eKProtectedWitnessTests(
            "test_01_separate_uid_reads_only_floor_and_leaves_db_intact")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)

    def _start_client(self):
        uid, gid = self.fx.client_uid, self.fx.client_gid
        def drop():
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", CLIENT, str(HERE)], preexec_fn=drop,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self.fx._stop, process)
        self.assertEqual(process.stdout.readline().strip(), "READY")
        return process

    def _pins(self, host):
        enrolled = hashlib.sha256(json.dumps([
            "c3ek-runner-test-01", "A" * 40, "B" * 40
        ], separators=(",", ":")).encode()).hexdigest()
        return {
            "socket_path": str(self.fx.socket),
            "expected_host_pid": host.pid,
            "expected_host_uid": 0,
            "expected_host_gid": 0,
            "expected_host_start": k.kernel_start(host.pid),
            "expected_enrollment_sha256": enrolled,
            "minimum_policy_epoch": 4,
            "minimum_release_sequence": 9,
        }

    def _ask(self, process, pins):
        process.stdin.write(json.dumps(pins) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            stderr = process.stderr.read()
            self.fail("CLIENT_NO_EVIDENCE rc=%r stderr=%r" % (
                process.poll(), stderr[-2000:]))
        self.assertEqual(process.wait(timeout=5), 0)
        return json.loads(line)

    def _host_and_client(self):
        client = self._start_client()
        host = self.fx._server(client)
        return client, host, self._pins(host)

    def test_01_reverse_kernel_host_identity_and_floor_observed(self):
        before = hashlib.sha256(self.fx.witness.read_bytes()).hexdigest()
        client, host, pins = self._host_and_client()
        result = self._ask(client, pins)["evidence"]
        self.assertEqual(result["schema"], adapter.CLIENT_SCHEMA)
        self.assertTrue(result["transport_peer_verified"])
        self.assertEqual(result["host_uid_observed"], 0)
        self.assertEqual(result["observed_policy_epoch"], 4)
        self.assertEqual(result["observed_release_sequence"], 9)
        self.assertEqual(result["enrollment_sha256"], pins["expected_enrollment_sha256"])
        self.assertIs(result["hostAuthenticated"], False)
        self.assertIs(result["canApprove"], False)
        self.assertIs(result["credentialActionsEnabled"], False)
        self.assertIs(result["productionAuthority"], False)
        self.assertNotIn("release_root_pin", result)
        self.assertEqual(host.wait(timeout=5), 0)
        self.assertEqual(before, hashlib.sha256(self.fx.witness.read_bytes()).hexdigest())

    def test_02_expected_host_pid_cannot_be_replaced_by_client_process(self):
        client, host, pins = self._host_and_client()
        pins["expected_host_pid"] = client.pid
        pins["expected_host_start"] = k.kernel_start(client.pid)
        self.assertEqual(self._ask(client, pins)["refused"],
                         "HOST_KERNEL_IDENTITY_MISMATCH")

    def test_03_stale_host_start_tick_refused(self):
        client, host, pins = self._host_and_client()
        pins["expected_host_start"] = "1"
        self.assertEqual(self._ask(client, pins)["refused"],
                         "EXPECTED_HOST_PROCESS_STALE")

    def test_04_nonroot_expected_host_uid_is_not_valid_trust_pin(self):
        client, host, pins = self._host_and_client()
        pins["expected_host_uid"] = self.fx.client_uid
        self.assertEqual(self._ask(client, pins)["refused"],
                         "UNTRUSTED_OR_INVALID_TEST_HOST_PIN")

    def test_05_other_enrollment_digest_rejected(self):
        client, host, pins = self._host_and_client()
        pins["expected_enrollment_sha256"] = "0" * 64
        self.assertEqual(self._ask(client, pins)["refused"],
                         "HOST_ENROLLMENT_MISMATCH")

    def test_06_older_observed_release_cannot_meet_newer_required_floor(self):
        client, host, pins = self._host_and_client()
        pins["minimum_release_sequence"] = 10
        self.assertEqual(self._ask(client, pins)["refused"],
                         "HOST_RELEASE_FLOOR_REFUSED")

    def test_07_missing_host_socket_is_refused(self):
        client = self._start_client()
        pins = self._pins(type("P", (), {"pid": os.getpid()})())
        self.assertEqual(self._ask(client, pins)["refused"],
                         "HOST_SOCKET_UNSAFE")

    def test_08_socket_symlink_not_a_valid_host(self):
        client, host, pins = self._host_and_client()
        alias = self.fx.public / "alias.sock"
        alias.symlink_to(self.fx.socket)
        pins["socket_path"] = str(alias)
        self.assertEqual(self._ask(client, pins)["refused"],
                         "HOST_SOCKET_PATH_UNEXPECTED")

    def test_09_host_response_extra_fields_do_not_create_permissions(self):
        doc = self._good_response()
        doc["canApprove"] = True
        self.assert_refused("HOST_RESPONSE_SHAPE_INVALID", doc)

    def test_10_host_response_claiming_authority_is_refused(self):
        doc = self._good_response()
        doc["authorized"] = True
        self.assert_refused("HOST_RESPONSE_CLAIMS_AUTHORITY", doc)

    def test_11_bool_floor_is_not_an_integer_floor(self):
        doc = self._good_response()
        doc["minimum_policy_epoch"] = True
        self.assert_refused("HOST_RELEASE_FLOOR_REFUSED", doc)

    def test_12_duplicated_response_fields_are_refused(self):
        data = b'{"schema":"x","schema":"y"}'
        with self.assertRaises(adapter.Refused) as error:
            adapter.validate_status(
                data, expected_enrollment_sha256="1" * 64,
                minimum_policy_epoch=4, minimum_release_sequence=9)
        self.assertEqual(str(error.exception), "HOST_RESPONSE_DUPLICATE_FIELD")

    def test_13_status_not_a_grant_in_production_policy(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        for path in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eLHostStatusObservation", path.read_text())

    def _good_response(self):
        return {
            "schema": adapter.HOST_SCHEMA,
            "minimum_policy_epoch": 4,
            "minimum_release_sequence": 9,
            "enrollment_sha256": "1" * 64,
            "authorized": False, "writable": False,
        }

    def assert_refused(self, reason, data):
        with self.assertRaises(adapter.Refused) as error:
            adapter.validate_status(
                json.dumps(data).encode(),
                expected_enrollment_sha256="1" * 64,
                minimum_policy_epoch=4,
                minimum_release_sequence=9)
        self.assertEqual(str(error.exception), reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
