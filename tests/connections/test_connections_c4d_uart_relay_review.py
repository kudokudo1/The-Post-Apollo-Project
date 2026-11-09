#!/usr/bin/env python3
"""C4d independent review: actual guest diagnostic->PTY path, no production."""
from __future__ import annotations
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import tty
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUEST = ROOT / "tests/connections/c4b_silverblue/guest_confined_runtime.sh"
PREFIX = b"C4B_OBSERVED // "


def report(**patch):
    d = dict(schema="postapollo.connections.c4b-booted-signed-host-observation.v1",
             signed_rpm_sha256="a"*64, signed_script_sha256="b"*64,
             running_script_sha256="b"*64, interpreter_sha256="c"*64,
             service_pid=1234, dbus_owner_pid=1234,
             process_start_ticks="523948", service_uid=978,
             service_gid=978,
             systemd_unit="postapollo-connections-status.service",
             selinux_enforcing=True, signedGuestOriginAuthenticated=False,
             evidenceCryptographicallyAttested=False, hostAuthenticated=False,
             canApprove=False, credentialActionsEnabled=False,
             productionAuthority=False)
    d.update(patch)
    return PREFIX + json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


class DirectGuestRelayReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="c4d-review-")
        self.addCleanup(self.tmp.cleanup)
        guest = GUEST.read_text()
        needle = "<<'C4B_SINGLE_UART_RELAY' || true\n"
        self.assertEqual(guest.count(needle), 1)
        self.source = guest.split(needle, 1)[1].split(
            "\nC4B_SINGLE_UART_RELAY\n", 1)[0]

    def relay(self, payload: bytes, *, regular_target=False):
        path = Path(self.tmp.name) / "c4b-runtime.log"
        path.write_bytes(payload)
        master, slave = pty.openpty()
        try:
            tty.setraw(slave)
            if regular_target:
                target = Path(self.tmp.name) / "not-a-tty"
                target.write_bytes(b"unchanged")
                dest = str(target)
            else:
                dest = os.ttyname(slave)
            p = subprocess.run([sys.executable, "-I", "-B", "-",
                                str(path), dest],
                               input=self.source.encode(), capture_output=True,
                               timeout=5)
            self.assertEqual(p.returncode, 0, p.stderr)
            ready = select.select([master], [], [], .15)[0]
            observed = os.read(master, 4096) if ready else b""
            if regular_target:
                self.assertEqual(target.read_bytes(), b"unchanged")
            return observed
        finally:
            os.close(master)
            os.close(slave)

    def test_01_real_pty_receives_one_report_without_controller_tail(self):
        raw = b"old logs\n" * 500 + report() + b"\n"
        self.assertEqual(self.relay(raw), report() + b"\n")

    def test_02_missing_and_invalid_report_never_emit(self):
        for raw in (b"no observation\n",
                    PREFIX + b'{"bad":1}\n',
                    report(hostAuthenticated=True) + b"\n",
                    report(running_script_sha256="d"*64) + b"\n"):
            with self.subTest(raw=raw[:40]):
                self.assertEqual(self.relay(raw), b"")

    def test_03_duplicate_report_refuses(self):
        self.assertEqual(self.relay(report()+b"\n"+report()+b"\n"), b"")

    def test_04_no_write_to_nonserial_file(self):
        self.assertEqual(self.relay(report()+b"\n", regular_target=True), b"")

    def test_05_guest_source_placement_and_deny_only(self):
        code = GUEST.read_text()
        self.assertLess(code.index("C4B_RUNNING_HOST_PROBE\n"),
                        code.index("C4B_SINGLE_UART_RELAY"))
        self.assertLess(code.index("C4B_SINGLE_UART_RELAY"),
                        code.index("stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN"))
        for v in ("os.O_NOFOLLOW", "os.O_NONBLOCK",
                  "hostAuthenticated=False", "productionAuthority=False",
                  'echo "C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED"'):
            self.assertIn(v, code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
