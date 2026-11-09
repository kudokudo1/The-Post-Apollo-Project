#!/usr/bin/env python3
"""C4d source-side adversarial tests. No VM or host system changes."""
from __future__ import annotations

import importlib.util
import json
import os
from unittest import mock
import subprocess
import sys
from pathlib import Path
import tempfile
import threading
import time
import unittest

SOURCE = Path(__file__).parent / "c4b_silverblue/capture_guest_observation.py"
SPEC = importlib.util.spec_from_file_location("c4d_uart", SOURCE)
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def observation(**override):
    value = dict(
        schema=C.SCHEMA,
        signed_rpm_sha256="a" * 64,
        signed_script_sha256="b" * 64,
        running_script_sha256="b" * 64,
        interpreter_sha256="c" * 64,
        service_pid=1337,
        dbus_owner_pid=1337,
        process_start_ticks="1234567",
        service_uid=966,
        service_gid=966,
        systemd_unit="postapollo-connections-status.service",
        selinux_enforcing=True,
        signedGuestOriginAuthenticated=False,
        evidenceCryptographicallyAttested=False,
        hostAuthenticated=False,
        canApprove=False,
        credentialActionsEnabled=False,
        productionAuthority=False,
    )
    value.update(override)
    return C.PREFIX + json.dumps(value, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8")


class C4dSerialCaptureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="c4d-serial-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.boot = self.root / "c2v-silverblue-fixture"
        self.boot.mkdir(mode=0o700)
        self.serial = self.boot / "guest-serial.log"
        self.done = self.root / "vm-done"

    def payload(self, *records):
        body = b"\n".join(
            list(C.REQUIRED_MARKERS[:2]) + list(records) +
            list(C.REQUIRED_MARKERS[2:])) + b"\n"
        self.serial.write_bytes(body)

    def test_01_canonical_report_is_accepted(self):
        self.assertEqual(C.validate_observation(observation()),
                         observation())

    def test_02_claimed_privileges_refuse(self):
        for flag in C.FALSE_FLAGS:
            with self.subTest(flag=flag):
                with self.assertRaises(C.Refused):
                    C.validate_observation(observation(**{flag: True}))

    def test_03_schema_extension_and_missing_keys_refuse(self):
        with self.assertRaises(C.Refused):
            C.validate_observation(observation(secret="not-allowed"))
        with self.assertRaises(C.Refused):
            C.validate_observation(observation().replace(
                b'"service_uid":966,', b""))

    def test_04_contradictory_ids_and_hashes_refuse(self):
        for item in (dict(dbus_owner_pid=999), dict(service_uid=0),
                     dict(running_script_sha256="d" * 64),
                     dict(process_start_ticks="0"),
                     dict(selinux_enforcing=False)):
            with self.subTest(item=item):
                with self.assertRaises(C.Refused):
                    C.validate_observation(observation(**item))

    def test_05_duplicate_json_fields_refuse(self):
        dup = observation().replace(
            b'"service_pid":1337', b'"service_pid":1337,"service_pid":1337')
        with self.assertRaises(C.Refused):
            C.validate_observation(dup)

    def test_06_oversize_non_json_and_missing_marker_refuse(self):
        for record in (b"x" * (C.MAX_LINE + 1),
                       C.PREFIX + b"{broken",
                       observation()[len(C.PREFIX):]):
            with self.subTest(record=record[:20]):
                with self.assertRaises(C.Refused):
                    C.validate_observation(record)

    def test_07_capture_single_real_serial_line_after_full_pass(self):
        self.payload(observation(), observation())
        self.done.write_text("PASS\n")
        self.assertEqual(C.capture(self.root, self.done, poll=0),
                         observation())

    def test_08_conflicting_serial_records_refuse(self):
        self.payload(observation(), observation(service_pid=1555,
                                                dbus_owner_pid=1555))
        self.done.write_text("PASS\n")
        with self.assertRaisesRegex(C.Refused,
                                    "CONFLICTING_GUEST_OBSERVATIONS"):
            C.capture(self.root, self.done, poll=0)

    def test_09_failed_two_reboots_cannot_export(self):
        self.payload(observation())
        self.done.write_text("FAIL\n")
        with self.assertRaisesRegex(C.Refused,
                                    "ORIGINAL_TWO_BOOT_LIFECYCLE_DID_NOT_PASS"):
            C.capture(self.root, self.done, poll=0)

    def test_10_incomplete_guest_security_markers_refuse(self):
        self.serial.write_bytes(observation() + b"\n")
        self.done.write_text("PASS\n")
        with self.assertRaisesRegex(C.Refused,
                                    "REAL_GUEST_SECURITY_OR_ROLLBACK_MARKERS_MISSING"):
            C.capture(self.root, self.done, poll=0)

    def test_11_zero_observation_cannot_pass(self):
        self.serial.write_bytes(b"\n".join(C.REQUIRED_MARKERS) + b"\n")
        self.done.write_text("PASS\n")
        with self.assertRaisesRegex(C.Refused,
                                    "NO_REAL_GUEST_OBSERVATION_CAPTURED"):
            C.capture(self.root, self.done, poll=0)

    def test_12_symlink_serial_source_refuses(self):
        target = self.root / "untrusted.log"
        target.write_bytes(observation())
        self.serial.symlink_to(target)
        self.done.write_text("PASS\n")
        with self.assertRaisesRegex(C.Refused, "GUEST_SERIAL_SOURCE_UNSAFE"):
            C.capture(self.root, self.done, poll=0)

    def test_13_two_guest_directories_refuse(self):
        (self.root / "c2v-silverblue-second").mkdir(mode=0o700)
        self.done.write_text("PASS\n")
        with self.assertRaisesRegex(C.Refused,
                                    "MULTIPLE_GUEST_BOOT_DIRECTORIES"):
            C.capture(self.root, self.done, poll=0)

    def test_14_live_appending_serial_is_captured(self):
        def append():
            time.sleep(.02)
            self.payload(observation())
            time.sleep(.02)
            self.done.write_text("PASS\n")
        writer = threading.Thread(target=append)
        writer.start()
        self.addCleanup(writer.join)
        self.assertEqual(C.capture(self.root, self.done, poll=.005),
                         observation())


    def _collector_cli(self, ready, output):
        return [
            sys.executable, "-B", str(SOURCE),
            "--runner-temp", str(self.root),
            "--complete", str(self.done),
            "--output", str(output),
            "--ready", str(ready),
        ]

    def test_15_delayed_observer_ready_then_fresh_guest_directory_is_accepted(self):
        # Discriminating regression for the exact failed C4d run. No directory
        # exists BEFORE the monitor starts. The new live directory is created
        # only AFTER the monitor's checked readiness barrier.
        self.boot.rmdir()
        private = self.root / "c4d-private"
        private.mkdir(mode=0o700)
        ready = private / "observer-ready"
        output = private / "C4B_OBSERVED.txt"
        env = {**os.environ, "GITHUB_ACTIONS": "true"}
        child = subprocess.Popen(
            self._collector_cli(ready, output), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for _ in range(300):
                if ready.exists() or child.poll() is not None:
                    break
                time.sleep(.01)
            self.assertIsNone(child.poll(), "observer exited before ready")
            self.assertEqual(ready.read_bytes(), b"READY\n")
            self.assertEqual(ready.stat().st_mode & 0o777, 0o600)
            self.assertFalse(self.boot.exists())
            self.boot.mkdir(mode=0o700)
            self.payload(observation())
            self.done.write_text("PASS\n")
            stdout, stderr = child.communicate(timeout=12)
            self.assertEqual(child.returncode, 0, stderr.decode(errors="replace"))
            self.assertEqual(output.read_bytes(), observation() + b"\n")
            self.assertIn(b"C4D_PASS // ONE_BOUNDED_ACTUAL_GUEST_SERIAL_OBSERVATION_EXPORTED",
                          stdout)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)

    def test_16_actual_preexisting_stale_directory_still_refuses(self):
        private = self.root / "c4d-private"
        private.mkdir(mode=0o700)
        ready = private / "observer-ready"
        output = private / "C4B_OBSERVED.txt"
        env = {**os.environ, "GITHUB_ACTIONS": "true"}
        result = subprocess.run(self._collector_cli(ready, output),
                                env=env, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"STALE_C2V_BOOT_DIRECTORY_BEFORE_MONITOR", result.stderr)
        self.assertFalse(ready.exists())
        self.assertFalse(output.exists())

    def test_17_forged_ready_file_does_not_bypass_collector_preflight(self):
        self.boot.rmdir()
        private = self.root / "c4d-private"
        private.mkdir(mode=0o700)
        ready = private / "observer-ready"
        ready.symlink_to(self.root / "attacker-controlled")
        output = private / "C4B_OBSERVED.txt"
        env = {**os.environ, "GITHUB_ACTIONS": "true"}
        result = subprocess.run(self._collector_cli(ready, output),
                                env=env, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"OBSERVER_READINESS_SCOPE_REFUSED", result.stderr)
        self.assertTrue(ready.is_symlink())
        self.assertFalse(output.exists())

    def test_18_insecure_output_directory_cannot_emit_ready(self):
        self.boot.rmdir()
        private = self.root / "c4d-private"
        private.mkdir(mode=0o755)
        ready = private / "observer-ready"
        output = private / "C4B_OBSERVED.txt"
        env = {**os.environ, "GITHUB_ACTIONS": "true"}
        result = subprocess.run(self._collector_cli(ready, output),
                                env=env, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"OUTPUT_DIRECTORY_NOT_PRIVATE", result.stderr)
        self.assertFalse(ready.exists())
        self.assertFalse(output.exists())

    def test_19_normal_c2v_cleanup_unlinks_serial_before_parent_pass(self):
        # Emulates the genuine #42678598917 failure deterministically:
        # the first find opens the existing UART; the second lookup happens
        # AFTER a complete read but BEFORE the parent writes completion.
        self.payload(observation())
        original_find = C.find_serial
        calls = 0
        def vanish_after_drain(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.serial.unlink()
                self.boot.rmdir()
                return None
            return original_find(root)
        def parent_result():
            time.sleep(.03)
            self.done.write_text("PASS\n")
        parent = threading.Thread(target=parent_result)
        parent.start()
        self.addCleanup(parent.join)
        with mock.patch.object(C, "find_serial", side_effect=vanish_after_drain):
            self.assertEqual(C.capture(self.root, self.done, poll=.002),
                             observation())
        self.assertFalse(self.boot.exists())
        self.assertGreaterEqual(calls, 2)

    def test_20_unlink_without_rollback_marker_still_refuses(self):
        self.serial.write_bytes(observation() + b"\n")
        original_find = C.find_serial
        calls = 0
        def vanish_after_drain(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.serial.unlink()
                self.boot.rmdir()
                return None
            return original_find(root)
        self.done.write_text("PASS\n")
        with mock.patch.object(C, "find_serial", side_effect=vanish_after_drain):
            with self.assertRaisesRegex(
                    C.Refused, "REAL_GUEST_SECURITY_OR_ROLLBACK_MARKERS_MISSING"):
                C.capture(self.root, self.done, poll=0)

    def test_21_reappearance_after_unlink_refuses_instead_of_switching(self):
        self.payload(observation())
        original_find = C.find_serial
        calls = 0
        def replace_after_unlink(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.serial.unlink()
                self.boot.rmdir()
                return None
            if calls == 3:
                self.boot.mkdir(mode=0o700)
                self.serial.write_bytes(observation() + b"\n")
            return original_find(root)
        with mock.patch.object(C, "find_serial", side_effect=replace_after_unlink):
            with self.assertRaisesRegex(
                    C.Refused, "GUEST_SERIAL_REAPPEARED_AFTER_REMOVAL"):
                C.capture(self.root, self.done, poll=0)

    def test_22_unlink_followed_by_failure_cannot_export(self):
        self.payload(observation())
        original_find = C.find_serial
        calls = 0
        def vanished(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.serial.unlink()
                self.boot.rmdir()
                return None
            return original_find(root)
        self.done.write_text("FAIL\n")
        with mock.patch.object(C, "find_serial", side_effect=vanished):
            with self.assertRaisesRegex(
                    C.Refused, "ORIGINAL_TWO_BOOT_LIFECYCLE_DID_NOT_PASS"):
                C.capture(self.root, self.done, poll=0)

    def test_23_workflow_waits_for_ready_before_unchanged_c2v_boot(self):
        workflow = (Path(__file__).resolve().parents[2] /
                    ".github/workflows/connections-c4b-silverblue-confined-runtime.yml").read_text()
        self.assertIn('if compgen -G "$RUNNER_TEMP/c2v-silverblue-*" >/dev/null', workflow)
        self.assertIn('--ready "$evidence/observer-ready" &', workflow)
        self.assertIn('C4D_PASS // OBSERVER_READY_BEFORE_C2V_BOOT', workflow)
        self.assertIn('OBSERVER_STARTUP_READY_TIMEOUT', workflow)
        self.assertIn('OBSERVER_EXITED_BEFORE_READY', workflow)
        self.assertLess(workflow.index('observer_ready=0'),
                        workflow.index('timeout 3550s bash tests/connections/c2v_silverblue/boot_official_silverblue.sh'))
        self.assertIn('[[ "$vm_rc" == 0 ]]', workflow)
        self.assertIn('wait "$observer_pid"', workflow)
        self.assertIn('if-no-files-found: error', workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
