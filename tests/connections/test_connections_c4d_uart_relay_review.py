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

    def relay(self, payload: bytes, *, regular_target=False, with_stdout=False,
              source_case="regular"):
        path = Path(self.tmp.name) / "c4b-runtime.log"
        if source_case == "directory":
            path.mkdir()
        else:
            path.write_bytes(payload)
            if source_case == "hardlink":
                os.link(path, Path(self.tmp.name) / "second-hardlink")
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

    def test_12_missing_guest_observation_emits_fixed_not_generic_reason(self):
        serial, diagnostic = self.relay(b"no signed observer record\n",
                                        with_stdout=True)
        self.assertEqual(serial, b"")
        self.assertIn(b"C4D_UART_DIAG // GUEST_OBSERVATION_MISSING", diagnostic)
        self.assertNotIn(b"no signed observer record", diagnostic)

    def test_13_duplicate_observations_emit_fixed_reason_and_no_data(self):
        serial, diagnostic = self.relay(
            report() + b"\n" + report() + b"\n", with_stdout=True)
        self.assertEqual(serial, b"")
        self.assertIn(b"C4D_UART_DIAG // GUEST_OBSERVATION_DUPLICATE", diagnostic)
        self.assertNotIn(PREFIX, diagnostic)

    def test_14_bounded_guest_log_size_refuses_with_fixed_code(self):
        serial, diagnostic = self.relay(
            b"X" * (2 * 1024 * 1024 + 1), with_stdout=True)
        self.assertEqual(serial, b"")
        self.assertIn(b"C4D_UART_DIAG // GUEST_RECORD_OVERSIZE", diagnostic)
        self.assertNotIn(PREFIX, diagnostic)

    def test_20_zero_size_guest_capture_reports_exact_empty_file(self):
        serial, diagnostic = self.relay(b"", with_stdout=True)
        self.assertEqual(serial, b"")
        self.assertIn(b"C4D_UART_DIAG // GUEST_RECORD_EMPTY", diagnostic)
        self.assertNotIn(PREFIX, diagnostic)

    def test_21_hardlinked_capture_is_refused_before_parsing(self):
        serial, diagnostic = self.relay(
            report() + b"\n", with_stdout=True, source_case="hardlink")
        self.assertEqual(serial, b"")
        self.assertIn(b"C4D_UART_DIAG // GUEST_RECORD_LINK_COUNT_INVALID",
                      diagnostic)
        self.assertNotIn(PREFIX, diagnostic)

    def test_22_directory_capture_is_refused_before_parsing(self):
        serial, diagnostic = self.relay(
            report() + b"\n", with_stdout=True, source_case="directory")
        self.assertEqual(serial, b"")
        self.assertIn(b"C4D_UART_DIAG // GUEST_RECORD_NOT_REGULAR", diagnostic)
        self.assertNotIn(PREFIX, diagnostic)

    def test_15_relay_defines_only_codes_used_by_host_collector(self):
        # Every source-defined outcome that the host may show must be a
        # fixed label, not a dynamic exception/message or a guest-report byte.
        from importlib.util import module_from_spec, spec_from_file_location
        collector = ROOT / "tests/connections/c4b_silverblue/capture_guest_observation.py"
        spec = spec_from_file_location("c4d_diag", collector)
        self.assertIsNotNone(spec)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        for value in (
            "GUEST_OBSERVATION_DUPLICATE_KEY",
            "GUEST_RECORD_NOT_REGULAR", "GUEST_RECORD_OWNER_MISMATCH",
            "GUEST_RECORD_LINK_COUNT_INVALID", "GUEST_RECORD_EMPTY",
            "GUEST_RECORD_OVERSIZE", "GUEST_LOG_CHANGED", "GUEST_OBSERVATION_MISSING",
            "GUEST_OBSERVATION_DUPLICATE", "GUEST_OBSERVATION_OVERSIZE",
            "GUEST_OBSERVATION_JSON_INVALID", "GUEST_OBSERVATION_SCHEMA_INVALID",
            "GUEST_OBSERVATION_DIGEST_INVALID",
            "GUEST_OBSERVATION_PROCESS_INVALID",
            "GUEST_OBSERVATION_DBUS_PID_MISMATCH",
            "GUEST_OBSERVATION_START_INVALID", "UART_NOT_CHARACTER_DEVICE",
            "UART_WRITE_TIMEOUT", "UART_WRITE_ZERO", "UART_WRITE_INCOMPLETE",
            "LOG_PREP_REFUSED", "UART_OPEN_REFUSED", "UART_WRITE_REFUSED",
        ):
            self.assertIn(value.encode(), module.KNOWN_RELAY_REASONS)
        self.assertIn('reason = phase + "_REFUSED"', self.source)
        self.assertNotIn("type(exc).__name__", self.source)
        self.assertNotIn("print(str(exc)", self.source)

    def test_16_same_process_private_report_writer_before_relay(self):
        guest = GUEST.read_text()
        source = guest.split("stage SIGNED_C3D_RUNNING_HOST_MEASUREMENT_BEGIN", 1)[1]
        self.assertIn('c4d_record_dir=/run/postapollo-c4d-observation', source)
        self.assertIn('install -d -m 0700 "$c4d_record_dir"', source)
        self.assertIn('umask 077', source)
        self.assertNotIn('set -C', source)
        self.assertIn(
            '"$pid" "$assets/c3d-status.rpm" "$c4d_record" '
            "<<'C4B_RUNNING_HOST_PROBE'", source)
        self.assertNotIn('> "$c4d_record"', source)
        self.assertIn('def write_private_report(path, record):', source)
        self.assertIn('os.O_CREAT | os.O_EXCL', source)
        self.assertIn('os.O_NOFOLLOW | os.O_CLOEXEC', source)
        self.assertIn('os.fsync(fd)', source)
        self.assertIn('write_private_report(\n        sys.argv[3]', source)
        self.assertIn('DIRECT_STDOUT_CAPTURE_PRESENT', source)
        self.assertIn('DIRECT_STDOUT_CAPTURE_EMPTY', source)
        self.assertIn(
            '"$c4d_record" /dev/ttyS0 <<\'C4B_SINGLE_UART_RELAY\'', source)
        self.assertLess(source.index('write_private_report(\n        sys.argv[3]'),
                        source.index("stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN"))
        self.assertLess(source.index("C4B_SINGLE_UART_RELAY"),
                        source.index('rm -f -- "$c4d_record"'))
        self.assertLess(source.index('rm -f -- "$c4d_record"'),
                        source.index('rm -rf -- /opt/postapollo-c2o-venv'))
        self.assertIn('rmdir -- "$c4d_record_dir"', source)
        self.assertIn('set -Eeuo pipefail', guest)

    def test_17_actual_exclusive_stdout_capture_retains_0600_bytes(self):
        with tempfile.TemporaryDirectory(prefix="c4d-direct-capture-") as dirname:
            out = Path(dirname) / "observed.txt"
            script = """set -Eeuo pipefail
umask 077
[[ ! -e "$2" && ! -L "$2" ]]
( set -C; /usr/bin/printf '%s\\n' "$1" > "$2" )
"""
            payload = report().decode("ascii")
            result = subprocess.run(["/usr/bin/bash", "-c", script, "probe",
                                     payload, str(out)], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"")
            self.assertEqual(out.read_bytes(), report() + b"\n")
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)
            self.assertEqual(out.stat().st_nlink, 1)

    def test_18_failed_signed_process_propagates_exit_code(self):
        with tempfile.TemporaryDirectory(prefix="c4d-direct-capture-") as dirname:
            out = Path(dirname) / "observed.txt"
            script = """set -Eeuo pipefail
umask 077
( set -C; { /usr/bin/printf '%s\\n' DENIED; exit 9; } > "$1" )
"""
            p = subprocess.run(["/usr/bin/bash", "-c", script, "probe", str(out)],
                               capture_output=True, timeout=5)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(out.read_bytes(), b"DENIED\n")
            self.assertNotIn(PREFIX, out.read_bytes())

    def test_23_preexisting_capture_is_not_overwritten_even_by_symlink(self):
        with tempfile.TemporaryDirectory(prefix="c4d-direct-capture-") as dirname:
            root = Path(dirname)
            real = root / "original"
            real.write_text("PROTECTED", encoding="ascii")
            for name, path in (
                ("file", root / "file"),
                ("symlink", root / "symlink"),
            ):
                with self.subTest(name=name):
                    if name == "file":
                        path.write_text("EXISTS", encoding="ascii")
                    else:
                        path.symlink_to(real)
                    script = """set -Eeuo pipefail
( set -C; /usr/bin/printf '%s\\n' ATTACKER > "$1" )
"""
                    result = subprocess.run(
                        ["/usr/bin/bash", "-c", script, "probe", str(path)],
                        capture_output=True, timeout=5)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(real.read_text(encoding="ascii"), "PROTECTED")
                    if name == "file":
                        self.assertEqual(path.read_text(encoding="ascii"), "EXISTS")

    def test_19_signed_producer_stdout_contract_still_exact_c3eu_schema(self):
        guest = GUEST.read_text()
        self.assertEqual(guest.count(
            'print("C4B_OBSERVED // " + json.dumps(observe(),'), 1)
        self.assertEqual(guest.count("C4B_RUNNING_HOST_PROBE"), 2)
        self.assertIn("GITHUB_ACTIONS=true POST_APOLLO_C4B_TEST_GUEST=1",guest)
        self.assertIn("C4D_PRODUCER_CAPTURE_UNSAFE_AT_CLEANUP",guest)

    def test_11_bounded_full_instrument_log_read_and_existing_c2v_tail(self):
        code = GUEST.read_text()
        self.assertIn("log = os.read(fd, st.st_size + 1)", code)
        self.assertIn("if st.st_size <= 0:", code)
        self.assertIn("if st.st_size > 2 * 1024 * 1024:", code)
        c2v = (ROOT / "tests/connections/c2v_silverblue/guest_ostree_reboot_cycle.sh").read_text()
        self.assertIn("tail -n 110 /var/tmp/c4b-runtime.log", c2v)
        self.assertIn('echo "C4B_CONTROLLER_GUEST_LOG_BEGIN"', c2v)
        self.assertIn('print(payload.decode("ascii").rstrip("\\n"), flush=True)', code)



    def test_32_capture_transition_logged_near_relay_without_record_bytes(self):
        guest = GUEST.read_text()
        self.assertIn("c4d_capture_initial=PRESENT", guest)
        self.assertIn("c4d_capture_initial=EMPTY", guest)
        self.assertIn("c4d_capture_at_relay=PRESENT", guest)
        self.assertIn("c4d_capture_at_relay=EMPTY", guest)
        marker = ('echo "C4D_PRODUCER_DIAG // capture_initial='
                  '$c4d_capture_initial capture_at_relay=$c4d_capture_at_relay"')
        self.assertEqual(guest.count(marker), 1)
        self.assertLess(guest.index('echo "C4D_PRODUCER_DIAG // DIRECT_STDOUT_CAPTURE_PRESENT"'),
                        guest.index("stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN"))
        self.assertLess(guest.index("stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN"),
                        guest.index(marker))
        self.assertLess(guest.index(marker), guest.index("C4B_SINGLE_UART_RELAY"))
        self.assertLess(guest.index(marker), guest.index("  rm -rf -- /opt/postapollo-c2o-venv"))
        self.assertNotIn('C4D_PRODUCER_DIAG // " +', guest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
