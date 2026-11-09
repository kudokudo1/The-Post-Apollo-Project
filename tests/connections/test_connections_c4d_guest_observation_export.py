#!/usr/bin/env python3
"""C4d source-side adversarial tests. No VM or host system changes."""
from __future__ import annotations

import importlib.util
import json
import os
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
