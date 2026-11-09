#!/usr/bin/env python3
"""C2v rollback failure evidence contracts. Static only; no host/VM mutation.

These checks preserve the exact signed C4b second-real-reboot acceptance gate.
They do not prove the actual rpm-ostree rollback command succeeds.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUEST = ROOT / "tests/connections/c2v_silverblue/guest_ostree_reboot_cycle.sh"
HOST = ROOT / "tests/connections/c2v_silverblue/boot_official_silverblue.sh"


class C2vRollbackEvidenceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guest = GUEST.read_text()
        cls.host = HOST.read_text()

    def test_01_rollback_command_remains_authoritative_and_fail_closed(self):
        src = self.guest
        self.assertEqual(
            src.count('if rpm-ostree rollback --reboot > "$rollback_output" 2>&1; then'),
            1,
        )
        self.assertIn('echo rollback_pending > "$stagefile"', src)
        self.assertIn('failure "RPM_OSTREE_ROLLBACK_FAILED"', src)
        self.assertIn('rollback_rc="$?"', src)
        self.assertIn('c2v_rollback_failure_diagnostic "$rollback_rc"', src)
        self.assertIn('C2V_ROLLBACK_COMMAND_RETURNED_ZERO // second_boot_still_required', src)
        self.assertNotIn('rpm-ostree rollback --reboot || true', src)
        self.assertNotIn('rpm-ostree rollback --reboot || :', src)
        self.assertNotIn('rpm-ostree usroverlay', src)
        begin = src.index('echo rollback_pending > "$stagefile"')
        command = src.index('if rpm-ostree rollback --reboot > "$rollback_output" 2>&1; then', begin)
        evidence = src.index('c2v_rollback_failure_diagnostic "$rollback_rc"', command)
        fail = src.index('failure "RPM_OSTREE_ROLLBACK_FAILED"', evidence)
        rollback_branch = src.index('  rollback_pending)', fail)
        self.assertLess(begin, command)
        self.assertLess(command, evidence)
        self.assertLess(evidence, fail)
        self.assertLess(fail, rollback_branch)

    def test_02_only_failure_collects_bounded_read_only_evidence(self):
        src = self.guest
        for needle in (
            'c2v_rollback_failure_diagnostic() {',
            "C2V_DIAG_ROLLBACK_COMMAND_RC //",
            "C2V_DIAG_ROLLBACK_STDOUT_STDERR_BEGIN",
            "C2V_DIAG_ROLLBACK_STDOUT_STDERR_END",
            "C2V_DIAG_ROLLBACK_RPM_OSTREE_JSON_BEGIN",
            "C2V_DIAG_ROLLBACK_OSTREE_ADMIN_BEGIN",
            "C2V_DIAG_ROLLBACK_SYSTEMD_UNITS_BEGIN",
            "C2V_DIAG_ROLLBACK_RPM_OSTREE_JOURNAL_BEGIN",
            "C2V_DIAG_ROLLBACK_FAILURE_REPORT_BEGIN",
            "C2V_DIAG_ROLLBACK_FAILURE_REPORT_END",
            'tail -c 6000 "$rollback_output"',
            '8s rpm-ostree status --json',
            '8s ostree admin status',
            '6s systemctl show',
            '6s journalctl -b',
            'head -c 15000 "$evidence" >/dev/ttyS0',
            'head -c 15000 "$evidence" >/dev/ttyS1',
            'if [[ -f "$c4b_mode" && -c /dev/ttyS1 ]]; then',
            "/run/c2v-rpm-ostree-rollback-command.log",
            "/run/c2v-rpm-ostree-rollback-failure.log",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, src)
        self.assertNotIn('echo "C2V_PASS // RPM_OSTREE_ROLLBACK_FAILED"', src)

    def test_03_genuine_second_boot_and_rollback_gates_remain_unchanged(self):
        src = self.guest
        for expected in (
            'C2V_PASS // LAYER_ACTIVE_ONLY_AFTER_REAL_REBOOT',
            'C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER',
            'C2V_PASS // NO_CONNECTIONS_SERVICE_OR_CREDENTIALS_ACTIVATED',
            'failure "ROLLED_BACK_RPM_STILL_IN_BOOTED_DATABASE"',
            'failure "ROLLED_BACK_USR_STILL_HAS_LAYER"',
            'failure "SELINUX_WEAKENED"',
            'failure "C4A_SIGNED_SERVICE_ROLLBACK_NOT_VERIFIED"',
            'failure "C4B_SIGNED_POLICY_ROLLBACK_VERIFICATION_FAILED"',
            'failure "C4B_RUNTIME_CLEANUP_OR_ROLLBACK_NOT_VERIFIED"',
            'c4b_execute rolledback',
            'echo complete > "$stagefile"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, src)
        self.assertIn('C2V_PASS // ACTUAL_SILVERBLUE_BOOTED_LAYER_AND_ROLLBACK_SEQUENCE', self.host)
        self.assertIn('C4B_PASS // REAL_SILVERBLUE_SIGNED_FAKE_SERVICE_OS_ORIGIN_AND_ROLLBACK', self.host)

    def test_04_independent_c4b_observer_samples_a_nonreturning_command(self):
        src = self.guest
        self.assertEqual(src.count("c2v_rollback_observer_start() {"), 1)
        self.assertIn('[[ -f "$c4b_mode" && -c /dev/ttyS1 ]] || return 0', src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_TICK //", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_PROCESSES_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_UNIT_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_OSTREE_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_RPM_OSTREE_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_JOURNAL_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_LOGIND_UNIT_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_INHIBITORS_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_INHIBITORS_RC //", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_LOGIND_BUS_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_LOGIND_BUS_RC //", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_LOGIND_JOURNAL_BEGIN", src)
        self.assertIn("loginctl list-inhibitors --no-pager", src)
        self.assertIn("org.freedesktop.login1.Manager ListInhibitors", src)
        self.assertIn("systemd-logind.service dbus-broker.service", src)
        self.assertIn("7s", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_COMMAND_OUTPUT_BEGIN", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_EXIT //", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_STARTED // non-authoritative", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_START_FAILED // non-authoritative", src)
        self.assertIn("C2V_DIAG_ROLLBACK_OBSERVER_NOT_READY // non-authoritative", src)
        for error in (
            "C2V_DIAG_ROLLBACK_OBSERVER_FILE_CREATE_FAILED // non-authoritative",
            "C2V_DIAG_ROLLBACK_OBSERVER_CHMOD_FAILED // non-authoritative",
            "C2V_DIAG_ROLLBACK_OBSERVER_RESET_FAILED // non-authoritative",
            "C2V_DIAG_ROLLBACK_OBSERVER_FINISH_MARK_FAILED // non-authoritative",
        ):
            with self.subTest(error=error):
                self.assertIn(error, src)
        self.assertIn("touch /run/c2v-rpm-rollback-observer-finished ||", src)
        self.assertIn("systemd-run --quiet", src)
        self.assertIn("--unit=c2v-rpm-rollback-observer", src)
        self.assertIn("--property=Type=exec", src)
        self.assertIn(">/dev/ttyS1 2>&1 || true", src)
        self.assertIn('touch /run/c2v-rpm-rollback-observer-finished', src)
        self.assertIn("timeout --signal=TERM --kill-after=2s 5s rpm-ostree status --json", src)
        self.assertIn("timeout --signal=TERM --kill-after=2s 5s ostree admin status", src)
        self.assertIn("timeout --signal=TERM --kill-after=2s 5s journalctl -b", src)
        self.assertIn("for n in $(seq 1 55); do", src)
        self.assertIn("sleep 20", src)
        stage = src.index('echo rollback_pending > "$stagefile"')
        start = src.index("c2v_rollback_observer_start", stage)
        begin = src.index("C2V_ROLLBACK_COMMAND_BEGIN // actual", start)
        command = src.index('if rpm-ostree rollback --reboot > "$rollback_output" 2>&1; then', begin)
        self.assertLess(stage, start)
        self.assertLess(start, begin)
        self.assertLess(begin, command)
        observer = src[
            src.index("c2v_rollback_observer_start() {"):
            src.index("stagefile=/var/lib/c2v-transaction-stage")
        ]
        for forbidden in (
            "systemctl reboot",
            "systemctl poweroff",
            "rpm-ostree rollback --reboot",
            "rpm-ostree install ",
            "C2V_PASS //",
            "C4B_PASS //",
            'echo complete > "$stagefile"',
            "setenforce",
            "curl ",
            "wget ",
            "shutdown -",
            "systemctl restart",
            "systemctl mask",
            "systemctl stop",
            "systemctl disable",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, observer)

    def test_05_host_progress_and_os_error_still_fail_closed(self):
        src = self.host
        for marker in (
            "C2V_HOST_PHASE // iteration=",
            "C4B_HOST_OBSERVER_BYTES // iteration=",
            "C4B_HOST_RECENT_OBSERVER_MARKER //",
            "C2V_HOST_STALL_WARNING //",
            "C4B_HOST_KNOWN_OS_ERROR //",
            "C2V_HOST_FAILURE_PHASE //",
            "C2V_HOST_FAILURE_REASON //",
            "LOGIND_INHIBITOR_TIMEOUT",
            "OBSERVATION_DEADLINE_EXHAUSTED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, src)
        # Phase and stale-UART information is observational. In particular,
        # silence alone may not terminate or falsely accept a real boot.
        self.assertIn("if (( i - last_guest_byte_progress_iteration >= 180 && i % 30 == 0 )); then", src)
        self.assertIn("no_serial_growth_for_at_least_360s", src)
        self.assertEqual(src.count("result=LOGIND_INHIBITOR_TIMEOUT"), 1)
        self.assertIn("error: Checking systemd inhibitor locks: Timeout was reached", src)
        self.assertIn("C2V_ROLLBACK_COMMAND_BEGIN // actual rpm-ostree rollback --reboot", src)
        self.assertIn("if [[ \"$result\" != PASS ]]; then", src)
        self.assertIn("C2V_BLOCKED // SILVERBLUE_LAYER_REBOOT_ROLLBACK_RESULT=$result", src)
        self.assertIn("C4B_HOST_DIAGNOSTIC_UART_BEGIN", src)
        self.assertIn("C4B_PASS // SIGNED_POLICY_RPM_AND_TEST_KEYRING_REMOVED_BY_ROLLBACK", src)
        self.assertIn("C4B_PASS // SIGNED_CONFINED_FAKE_HOST_STOPPED_AND_REAL_SILVERBLUE_ROLLBACK", src)
        self.assertIn("C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER", src)
        self.assertIn("for i in $(seq 1 700); do", src)
        for forbidden in (
            "result=PASS #",
            "result=PASS; #",
            "systemctl reboot -i",
            "--check-inhibitors=no",
            "--ignore-inhibitors",
            "rpm-ostree rollback --reboot || true",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)
        # The authoritative host PASS must precede checks for C4a/C4b
        # exact signed removal markers; no diagnostics can create these.
        self.assertLess(
            src.index("if [[ \"$result\" != PASS ]]; then"),
            src.index("C4B_PASS // SIGNED_POLICY_RPM_AND_TEST_KEYRING_REMOVED_BY_ROLLBACK"),
        )

    def test_06_no_diagnostics_can_create_a_success_signal(self):
        source = self.guest
        begin = source.index("c2v_rollback_failure_diagnostic() {")
        end = source.index("\ntrap 'rc=$?;", begin)
        diagnostic = source[begin:end]
        for forbidden in (
            "systemctl reboot",
            "systemctl poweroff",
            "rpm-ostree rollback --reboot",
            "rpm-ostree install",
            "C2V_PASS //",
            "C4B_PASS //",
            "echo complete >",
            "echo rollback_pending >",
            "C3B_PASS //",
            "setenforce",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, diagnostic)
        # The only path allowed for a failed rollback is an existing fatal
        # service exit, not a successful poweroff or synthetic stage change.
        self.assertIn('failure "RPM_OSTREE_ROLLBACK_FAILED"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
