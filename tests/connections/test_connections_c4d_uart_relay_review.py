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

    def relay(self, payload: bytes, *, regular_target=False, with_stdout=False):
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
            return (observed, p.stdout) if with_stdout else observed
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

    def _writer_function(self, fake_os, fake_select, fake_time):
        # Execute the ACTUAL embedded relay function, not a rewritten model.
        marker = "def write_all_serial(fd, payload):\n"
        self.assertEqual(self.source.count(marker), 1)
        code = marker + self.source.split(marker, 1)[1].split(
            "\ntry:\n    payload = selected_line", 1)[0]
        env = {"os": fake_os, "select": fake_select, "time": fake_time}
        exec(compile(code, str(GUEST), "exec"), env)
        return env["write_all_serial"]

    def test_06_partial_uart_write_and_eagain_eventually_sends_exact_bytes(self):
        from types import SimpleNamespace
        target = report() + b"\n"
        output, calls = bytearray(), [0]

        def short_writer(_fd, portion):
            calls[0] += 1
            if calls[0] in (2, 4):
                raise BlockingIOError("simulated UART EAGAIN")
            n = min(13, len(portion))
            output.extend(portion[:n])
            return n

        writer = self._writer_function(
            SimpleNamespace(write=short_writer),
            SimpleNamespace(select=lambda r, w, e, t: ([], w, [])),
            SimpleNamespace(monotonic=lambda: 1.0))
        self.assertEqual(writer(9, target), len(target))
        self.assertEqual(bytes(output), target)
        self.assertGreater(calls[0], 5)

    def test_07_unwritable_serial_refuses_and_does_not_issue_complete_receipt(self):
        from types import SimpleNamespace
        writer = self._writer_function(
            SimpleNamespace(write=lambda _fd, _b: 1),
            SimpleNamespace(select=lambda r, w, e, t: ([], [], [])),
            SimpleNamespace(monotonic=lambda: 1.0))
        with self.assertRaisesRegex(ValueError, "UART_WRITE_TIMEOUT"):
            writer(9, report() + b"\n")

    def test_08_zero_byte_serial_write_fails_closed(self):
        from types import SimpleNamespace
        writer = self._writer_function(
            SimpleNamespace(write=lambda _fd, _b: 0),
            SimpleNamespace(select=lambda r, w, e, t: ([], w, [])),
            SimpleNamespace(monotonic=lambda: 1.0))
        with self.assertRaisesRegex(ValueError, "UART_WRITE_ZERO"):
            writer(9, report() + b"\n")

    def test_05_guest_source_placement_and_deny_only(self):
        code = GUEST.read_text()
        # Original signed C4c probe is validated while the service is running.
        # Mirror a validated *past* observation only after first-boot cleanup,
        # just before the unchanged controller's final 110-line log relay.
        self.assertLess(code.index("C4B_RUNNING_HOST_PROBE\n"),
                        code.index("stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN"))
        self.assertLess(code.index('echo "C4B_PASS // SERVICE_STOP_RELEASES_DBUS_NAME"'),
                        code.index("C4B_SINGLE_UART_RELAY"))
        # The exact previous failure: using the isolated venv interpreter
        # after the same guest phase had already deleted that executable.
        self.assertLess(code.index("C4B_SINGLE_UART_RELAY"),
                        code.index("  rm -rf -- /opt/postapollo-c2o-venv"))
        self.assertIn('timeout --signal=TERM --kill-after=1s 6s "$python" -I -B -', code)
        self.assertIn('python=/opt/postapollo-c2o-venv/bin/python3', code)
        self.assertLess(code.index("  rm -rf -- /opt/postapollo-c2o-venv"),
                        code.index("stage BOOTED_RUNTIME_ACCEPTED"))
        self.assertLess(code.index("C4B_SINGLE_UART_RELAY"),
                        code.index('echo "C4B_PASS // RUNTIME_USERS_VENV_CLEANED_POLICY_RETAINED_FOR_ROLLBACK"'))
        for v in ("os.O_NOFOLLOW", "os.O_NONBLOCK",
                  "hostAuthenticated=False", "productionAuthority=False",
                  'echo "C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED"'):
            self.assertIn(v, code)

    def test_09_old_report_outside_last_16k_mirrored_into_controller_tail(self):
        # Earlier C4c report can be buried by benign teardown logging. The
        # final relay validates the bounded ORIGINAL inode, not just its tail.
        raw = b"booted phase\n" + report() + b"\n" + b"normal teardown\n" * 2400
        emitted, host_tail = self.relay(raw, with_stdout=True)
        self.assertEqual(emitted, report() + b"\n")
        self.assertEqual(host_tail.count(report()), 1)
        self.assertIn(b"C4D_UART_DIAG // ONE_VALID_RECORD_WRITTEN_TO_UART", host_tail)
        # A controller echo of the latest runtime lines will include the
        # mirrored line even if it wasn't present in an earlier tail.
        controller_log = raw + host_tail + b"C4B_PASS // RUNTIME_USERS_CLEANED\n"
        self.assertIn(report(), b"\n".join(controller_log.splitlines()[-110:]))

    def test_10_invalid_report_never_mirrored_to_controller_console(self):
        for raw in (report(hostAuthenticated=True) + b"\n",
                    report() + b"\n" + report() + b"\n",
                    PREFIX + b'{"bad":true}\n'):
            with self.subTest(case=raw[:44]):
                serial, controller = self.relay(raw, with_stdout=True)
                self.assertEqual(serial, b"")
                self.assertNotIn(PREFIX, controller)

    def test_11_bounded_full_instrument_log_read_and_existing_c2v_tail(self):
        code = GUEST.read_text()
        self.assertIn("log = os.read(fd, st.st_size + 1)", code)
        self.assertIn("not 0 < st.st_size <= 2 * 1024 * 1024", code)
        c2v = (ROOT / "tests/connections/c2v_silverblue/guest_ostree_reboot_cycle.sh").read_text()
        self.assertIn("tail -n 110 /var/tmp/c4b-runtime.log", c2v)
        self.assertIn('echo "C4B_CONTROLLER_GUEST_LOG_BEGIN"', c2v)
        self.assertIn('print(payload.decode("ascii").rstrip("\\n"), flush=True)', code)



if __name__ == "__main__":
    unittest.main(verbosity=2)
