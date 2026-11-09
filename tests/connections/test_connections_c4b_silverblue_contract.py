#!/usr/bin/env python3
"""C4b source contract: no host mutations; full acceptance needs real VM logs."""
from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUEST = (ROOT / "tests/connections/c4b_silverblue/guest_confined_runtime.sh")
OSTREE = (ROOT / "tests/connections/c2v_silverblue/guest_ostree_reboot_cycle.sh")
BOOT = (ROOT / "tests/connections/c2v_silverblue/boot_official_silverblue.sh")
WORKFLOW = (ROOT / ".github/workflows/connections-c4b-silverblue-confined-runtime.yml")
C4A = (ROOT / "tests/connections/c4a_silverblue/guest_signed_status_gate.sh")
C3B = (ROOT / "tests/connections/c3b_origin/C3bOriginCheck.py")
C2R = (ROOT / "tests/connections/c2r_selinux_domain/postapollo_connections.te")
SIGNED_C2R_HOST_SOURCE = (ROOT / "tests/connections/c2r_selinux_domain/C2rStatusHost.py")
SIGNED_C3D_UNIT_SOURCE = (ROOT / "services/connections/experiments/c2n_package/postapollo-connections-status.service.template")
SIGNED_C3D_RPM_SPEC = (ROOT / "tests/connections/c3d_provenance/signed-status.spec")
POLICY_GATE = (ROOT / "tests/connections/c4b_silverblue/guest_signed_policy_gate.sh")
POLICY_BUILDER = (ROOT / "tests/connections/c4b_silverblue/build_signed_composed_policy.sh")
POLICY_SPEC = (ROOT / "tests/connections/c4b_silverblue/signed-compose-policy.spec")


class C4bContracts(unittest.TestCase):
    def test_01_opt_in_requires_existing_signed_c4a(self):
        host, guest = BOOT.read_text(), OSTREE.read_text()
        self.assertIn("c4b_requested=0", host)
        self.assertIn('if [[ -v C4B_RUNTIME_ASSETS_DIR', host)
        self.assertIn('[[ "$c4a_requested" == 1 ]]', host)
        self.assertIn('C4B_BLOCKED // C4A_SIGNED_PACKAGE_REQUIRED', host)
        self.assertIn('sha256sum --check --status c4b-runtime-manifest.sha256', host)
        self.assertIn('c4b-opt-in.marker', host)
        self.assertIn('if [[ -f "$data/c4b-opt-in.marker" ]]; then', guest)
        self.assertIn('[[ -f "$c4a_mode" ]]', guest)
        self.assertIn('if [[ -f "$c4b_mode" ]]; then', guest)
        self.assertIn('c4b_execute booted', guest)
        self.assertIn('c4b_execute rolledback', guest)
        self.assertIn('C4B_CONTROLLER_LAST_STAGE', guest)
        self.assertIn('C4B_OBSERVER_STAGE', guest)
        self.assertIn('C4B_INDEPENDENT_OBSERVER_NOT_RUNNING', guest)
        self.assertIn('C4B_RUNTIME_PHASE_FAILED_OR_TIMED_OUT_', guest)
        self.assertIn("C4B_DIAG_MONITOR_FATAL //", guest)
        self.assertIn("C4B_DIAG_UART1_READY // first_boot", guest)
        self.assertIn("C4B_DIAG_PENDING_HEAD //", guest)
        self.assertIn("C4B_DIAG_PENDING_REJECTED // attempt=", guest)
        self.assertIn("C4B_DIAG_CONTROLLER_FATAL //", guest)
        self.assertIn("C4B_DIAG_RUNTIME_LAST_STAGE //", guest)
        self.assertIn("C4B_DIAG_RUNTIME_LOG_BEGIN", guest)
        self.assertIn("C4B_DIAG_RUNTIME_LOG_END", guest)
        self.assertIn("c4b-controller-fatal.log", guest)
        self.assertIn("tail -n 100 /var/tmp/c4b-runtime.log", guest)
        self.assertIn("if [[ \"$reason\" == C4B_RUNTIME_*", guest)
        self.assertIn('cat /var/tmp/c4b-controller-fatal.log >/dev/ttyS1', guest)
        self.assertIn("C4B_DIAG_POWEROFF_WITNESS //", guest)
        self.assertIn("c4b-shutdown-witness.service", guest)
        self.assertIn("c4b_controller_failure_relay", guest)
        self.assertIn("C4B_DIAG_WITNESS_DISABLE_FAILED", guest)
        self.assertIn("C4B_DIAG_WITNESS_CLEANUP_FAILED", guest)
        self.assertIn("Before=poweroff.target", guest)
        self.assertIn("WantedBy=poweroff.target", guest)
        self.assertIn("ConditionPathExists=/var/lib/c4b-runtime-ci-only", guest)
        self.assertIn('cat /var/tmp/c4b-monitor-fatal-summary.log >/dev/ttyS1', guest)
        self.assertIn("C4B_HOST_DIAGNOSTIC_UART_BEGIN", host)
        self.assertIn('c4b_secondary_serial=(-serial "file:$tmp/c4b-diagnostic-serial.log")', host)
        self.assertIn('"${c4b_secondary_serial[@]}"', host)
        self.assertIn("C4B_DIAG_WORKER_EXIT //", guest)
        self.assertIn("C4B_DIAG_RPM_OSTREE_WORKER_LOG_BEGIN", guest)
        self.assertIn("c4b_emergency_relay", guest)
        self.assertIn("c4b-monitor-fatal-summary.log", guest)
        self.assertIn("timeout --signal=TERM --kill-after=2s 9s", guest)
        self.assertIn('if [[ "$rc" -ne 0 ]] && declare -F c4b_emergency_relay', guest)
        self.assertIn('timeout --signal=TERM --kill-after=15s 560s', guest)
        self.assertIn('C4B_CONFINED_RUNTIME_NOT_VERIFIED', guest)
        self.assertIn('C4B_RUNTIME_CLEANUP_OR_ROLLBACK_NOT_VERIFIED', guest)

    def test_02_original_signed_two_reboot_rollback_gate_preserved(self):
        host, guest = BOOT.read_text(), OSTREE.read_text()
        for needle in (
            "Fedora-Silverblue-ostree-x86_64-44-1.7.iso",
            "9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682",
            "-nic none",
            "C4A_PASS // SIGNED_FAKE_SERVICE_SILVERBLUE_TWO_REBOOT_SEQUENCE",
            "C2V_PASS // ACTUAL_SILVERBLUE_BOOTED_LAYER_AND_ROLLBACK_SEQUENCE",
            "C4B_PASS // REAL_SILVERBLUE_SIGNED_FAKE_SERVICE_OS_ORIGIN_AND_ROLLBACK",
        ):
            self.assertIn(needle, host)
        for needle in (
            "rpm-ostree install --cache-only", "rpm-ostree rollback --reboot",
            "C2V_PENDING_DEPLOYMENT_AUTHORITY",
            "status.get(\"transaction\") is not None",
            "C2V_PASS // LAYER_ACTIVE_ONLY_AFTER_REAL_REBOOT",
            "C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER",
            "C2V_PASS // NO_CONNECTIONS_SERVICE_OR_CREDENTIALS_ACTIVATED",
            "C4A_SIGNED_SERVICE_NOT_VALID_AFTER_REBOOT",
            "C4A_SIGNED_SERVICE_ROLLBACK_NOT_VERIFIED",
        ):
            self.assertIn(needle, guest)

    def test_03_confined_host_identity_and_adversarial_guards(self):
        script = GUEST.read_text()
        for needle in (
            "REFUSED_OUTSIDE_DISPOSABLE_C4A", "SELINUX_NOT_ENFORCING",
            "GUEST_HAS_NETWORK_INTERFACE",
            "SEMODULE_UNAVAILABLE", "SIGNED_POLICY_RPM_NOT_COMPOSED",
            "COMPOSED_SELINUX_POLICY_NOT_LOADED",
            "C4B_PASS // SELINUX_POLICY_LOADED_WITH_ENFORCING_KERNEL",
            "COMPOSED_IMMUTABLE_EXECUTABLE_LABEL_CHECK", "SIGNED_OSTREE_EXECUTABLE_NOT_LABELED",
            "postapollo_connections_exec_t", "postapollo_connections_t",
            "NoNewPrivs:", "FAKE_SERVICE_DID_NOT_REMAIN_ACTIVE", "C3bOriginCheck.py",
            "POST_APOLLO_C3B_TEST_GUEST=1",
            "C2R_PASS // SELINUX_REFUSED_WORLD_READABLE_PROBE",
            "UNAUTHORIZED_DBUS_OWNERSHIP_REFUSED",
            "client_check c4b-reader status OBSERVED_UNVERIFIED",
            "client_check c4b-reader approve METHOD_REFUSED",
            "client_check c4b-outsider claim OWN_REFUSED",
            "systemctl stop", "SERVICE_STOP_RELEASES_DBUS_NAME",
            "COMPOSED_POLICY_RETAINED_FOR_ROLLBACK",
            "RUNTIME_USERS_VENV_CLEANED_POLICY_RETAINED_FOR_ROLLBACK",
            "SIGNED_CONFINED_FAKE_HOST_STOPPED_AND_REAL_SILVERBLUE_ROLLBACK",
        ):
            self.assertIn(needle, script)
        for forbidden in (
            "setenforce ", "usroverlay", "mount -o remount,rw",
            "systemctl enable ", "systemctl unmask ",
            "secret-tool ", "curl ", "wget ", "--permissive",
            "rpm --import", "dnf install", "rpm -Uvh",
            "POST_APOLLO_FIRMS_MAP_KEY", "--export-secret-key",
        ):
            # usroverlay in comments explicitly rejected, not invoked.
            if forbidden == "usroverlay":
                self.assertNotIn("rpm-ostree usroverlay", script)
            else:
                self.assertNotIn(forbidden, script)

    def test_04_origin_probe_and_policy_reused_not_rewritten(self):
        workflow = WORKFLOW.read_text()
        script = GUEST.read_text()
        self.assertIn("postapollo_connections.pp", workflow)
        self.assertIn("C3bOriginCheck.py", workflow)
        self.assertIn("BusPolicyClient.py", workflow)
        self.assertIn("dbus-next==0.2.3", workflow)
        self.assertIn(
            "58948f9aff9db08316734c0be2a120f6dc502124d9642f55e90ac82ffb16a18b",
            workflow,
        )
        self.assertIn("postapollo_connections", POLICY_BUILDER.read_text())
        self.assertIn("postapollo_connections", POLICY_BUILDER.read_text())
        self.assertIn('if [[ "$c4b_requested" == 1 ]]; then', BOOT.read_text())
        self.assertIn("C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY",
                      BOOT.read_text())
        self.assertIn("C3B_OS_ORIGIN_COHERENT_TEST_ONLY", C3B.read_text())
        # These source guards take effect only after the independently
        # reviewed C3b #1553 reaches main. Never copy that owner source here.
        c3b = C3B.read_text()
        self.assertIn("--verify-disposable-silverblue-opt", c3b)
        self.assertIn('C4B_OPT_LINK = "var/opt"', c3b)
        self.assertIn('C4B_OPT_REALPATH = "/var/opt"', c3b)
        self.assertIn("def _verified_c4b_opt_guest()", c3b)
        self.assertIn("def _valid_opt_proof(", c3b)
        self.assertIn("os.readlink(\"/opt\")", c3b)
        self.assertIn("os.lstat(\"/opt\")", c3b)
        self.assertIn("init_daemon_domain", C2R.read_text())
        self.assertIn("stage COMPOSED_POLICY_VERIFICATION_BEGIN", script)
        self.assertIn("stage COMPOSED_IMMUTABLE_EXECUTABLE_LABEL_CHECK", script)
        self.assertNotIn("restorecon -F", script)
        self.assertNotIn("semodule -i", script)
        self.assertNotIn("semodule -r", script)
        self.assertIn("C4B_STAGE // phase=", script)
        self.assertIn("C4B_EXIT // phase=", script)
        self.assertIn('exec >>/var/tmp/c4b-runtime.log 2>&1', script)
        self.assertIn("GITHUB_ACTIONS=true POST_APOLLO_C3B_TEST_GUEST=1", script)
        # C4b requests the C3b-owner's explicit, independently gated
        # Silverblue-only path. Default --verify-disposable stays untouched.
        self.assertIn("POST_APOLLO_C4B_TEST_GUEST=1", script)
        self.assertIn("--verify-disposable-silverblue-opt", script)
        self.assertIn("C3B_OS_ORIGIN_VERIFICATION_BEGIN", script)
        self.assertIn("DBUS_SYSTEMD_PID_UID_SELINUX_ORIGIN_REJECTED", script)
        self.assertNotIn("--verify-disposable-physical", script)
        self.assertIn('python=/opt/postapollo-c2o-venv/bin/python3', script)
        self.assertIn('python3 -m venv --without-pip /opt/postapollo-c2o-venv', script)
        self.assertIn("C3B_REJECTED_ORIGIN_ANCESTOR_DIAG_BEGIN", script)
        self.assertIn("C4B_DIAG_C3B_UNPROTECTED_DIRECTORY //", script)
        self.assertIn("C4B_DIAG_C3B_ANCESTOR_VIOLATION_COUNT //", script)
        self.assertIn("C4B_DIAG_C3B_OPT_LINK //", script)
        self.assertIn("C4B_DIAG_C3B_OPT_CHAIN //", script)
        self.assertIn("C4B_DIAG_C3B_OPT_CHAIN_STAT_REFUSED //", script)
        self.assertIn('os.readlink("/opt")', script)
        self.assertIn('os.path.realpath("/opt")', script)
        self.assertIn('("/var", "/var/opt", resolved)', script)
        self.assertIn("C4B_DIAG_C3B_OPT_LINK_READ_REFUSED //", script)
        self.assertIn('fail "DBUS_SYSTEMD_PID_UID_SELINUX_ORIGIN_REJECTED"', script)
        self.assertIn("os.lstat(path)", script)
        self.assertIn("mode & 0o022 or not directory or symlink", script)
        self.assertIn("for path in probe.PROTECTED_DIRS", script)
        self.assertIn('fail "DBUS_SYSTEMD_PID_UID_SELINUX_ORIGIN_REJECTED"', script)

    def test_045_signed_policy_is_composed_before_immutable_boot(self):
        host, guest = BOOT.read_text(), OSTREE.read_text()
        gate, builder, spec = (POLICY_GATE.read_text(),
                               POLICY_BUILDER.read_text(),
                               POLICY_SPEC.read_text())
        workflow = WORKFLOW.read_text()
        for value in (
            "c4b-policy.rpm", "c4b-policy-public.asc",
            "c4b-policy-artifact-manifest.sha256",
            "c4b-guest-signed-policy-gate.sh",
            "SIGNED_POLICY_RPM_COMPOSED_ENTRYPOINT_LABEL_BEFORE_REBOOT",
            "SIGNED_POLICY_RPM_AND_TEST_KEYRING_REMOVED_BY_ROLLBACK",
        ):
            self.assertIn(value, host)
        for value in (
            "c4b_policy_gate", "C4B_SIGNED_POLICY_PRELAYER_VERIFICATION_FAILED",
            "C4B_SIGNED_COMPOSED_POLICY_NOT_VALID_AFTER_REBOOT",
            "C4B_SIGNED_POLICY_ROLLBACK_VERIFICATION_FAILED",
            "postapollo-connections-c4b-policy-ci-0.1-1.fc44.noarch",
            'set -- "$@" /mnt/c2v-offline/c4b-policy.rpm',
        ):
            self.assertIn(value, guest)
        for value in (
            "rpmkeys --dbpath", "C4B_PASS // SIGNED_POLICY_VERIFIED_WITH_SEPARATE_TEST_ONLY_KEYRING",
            "C4B_PASS // SIGNED_POLICY_RPM_COMPOSED_ENTRYPOINT_LABEL_BEFORE_REBOOT",
            "C4B_PASS // SIGNED_POLICY_RPM_AND_TEST_KEYRING_REMOVED_BY_ROLLBACK",
            'semodule -l | grep -Fq postapollo_connections',
            "postapollo_connections_exec_t",
        ):
            self.assertIn(value, gate)
        self.assertIn("%post", spec)
        self.assertIn("%postun", spec)
        self.assertIn("/usr/sbin/semodule -i", spec)
        self.assertIn("/usr/sbin/semodule -r", spec)
        self.assertIn("C4B_POLICY_UNEXPECTED_PAYLOAD", builder)
        self.assertIn("rpmsign --addsign", builder)
        self.assertIn("build_signed_composed_policy.sh", workflow)
        # The C3b owner's opt profile must use the ORIGINAL C3d-signed host,
        # not C4b's now-closed physical-shebang derivative experiment #1551.
        self.assertTrue(SIGNED_C2R_HOST_SOURCE.read_bytes().startswith(
            b"#!/opt/postapollo-c2o-venv/bin/python3\n"
        ))
        self.assertIn(
            "ExecStart=/usr/libexec/post-apollo/connections-status-host --read-only",
            SIGNED_C3D_UNIT_SOURCE.read_text(),
        )
        self.assertNotIn("prepare_physical_status_host.py", workflow)
        self.assertNotIn("c4b-physical-status-host.py", workflow)
        self.assertIn("build_signed_ci_status.sh", workflow)
        self.assertIn("c4b-policy.rpm", workflow)
        self.assertIn("sha256sum --check --status c4b-policy-artifact-manifest.sha256", workflow)
        for forbidden in ("setenforce ", "rpm-ostree usroverlay",
                          "mount -o remount,rw", "POST_APOLLO_FIRMS_MAP_KEY"):
            self.assertNotIn(forbidden, builder + gate + spec)

    def test_048_fedora_service_primary_group_cleanup_fails_closed(self):
        # Real Silverblue #42508631401 proved origin and client negatives,
        # but userdel removed postapollo-connections' private primary group
        # before a later groupdel tried deleting it a second time.
        script = GUEST.read_text()
        self.assertIn(
            'userdel postapollo-connections || fail "TEST_USER_REMOVAL_FAILED"',
            script,
        )
        self.assertIn(
            'groupdel c4b-clients || fail "CLIENT_GROUP_REMOVAL_FAILED"',
            script,
        )
        self.assertIn(
            'groupdel postapollo-status-readers || fail "READER_GROUP_REMOVAL_FAILED"',
            script,
        )
        self.assertIn(
            'if getent group postapollo-connections >/dev/null; then',
            script,
        )
        self.assertIn(
            'groupdel postapollo-connections || fail "SERVICE_GROUP_REMOVAL_FAILED"',
            script,
        )
        self.assertIn(
            'C4B_DIAG // SERVICE_PRIMARY_GROUP_ALREADY_ABSENT_AFTER_USERDEL',
            script,
        )
        self.assertIn(
            'check_accounts_absent\n  echo "C4B_PASS // TEST_USERS_AND_GROUPS_FULLY_ABSENT"',
            script,
        )
        self.assertNotIn(
            'groupdel postapollo-connections || fail "TEST_GROUP_REMOVAL_FAILED"',
            script,
        )
        # The skip is only valid AFTER all three userdel operations;
        # test-owned reader groups still require explicit successful delete.
        begin = script.index('userdel c4b-reader && userdel c4b-outsider &&')
        last_check = script.index('  check_accounts_absent\n  echo "C4B_PASS // TEST_USERS_AND_GROUPS_FULLY_ABSENT"')
        self.assertLess(begin, script.index('  if getent group postapollo-connections', begin))
        self.assertLess(script.index('groupdel c4b-clients', begin), last_check)
        self.assertLess(script.index('groupdel postapollo-status-readers', begin), last_check)
        self.assertLess(last_check, script.index('stage COMPOSED_POLICY_RETAINED_FOR_ROLLBACK'))

    def test_049_boot_composed_signed_dbus_policy_keeps_logind_healthy(self):
        # C3d's D-Bus policy already exists in immutable /usr on first boot.
        # Rebooting the system broker during C4b previously preceded a
        # logind ListInhibitors timeout; never hide that by bypassing inhibitors.
        script = GUEST.read_text()
        self.assertNotIn("systemctl restart dbus-broker.service", script)
        self.assertNotIn("systemctl restart systemd-logind.service", script)
        self.assertNotIn("systemctl reboot -i", script)
        self.assertNotIn("--check-inhibitors=no", script)
        self.assertIn("stage DBUS_BOOT_COMPOSED_POLICY_CHECK_BEGIN", script)
        self.assertIn("DBUS_POLICY_NOT_OWNED_BY_SIGNED_C3D_RPM", script)
        self.assertIn("SIGNED_DBUS_POLICY_FILE_UNSAFE", script)
        self.assertIn("BOOTED_DBUS_BROKER_NOT_ACTIVE", script)
        # First real VM on this branch proved that just avoiding a restart
        # left the signed service unable to acquire its D-Bus name. Fedora's
        # dbus-broker supports in-place policy reload instead of restart.
        self.assertIn("stage DBUS_POLICY_GRACEFUL_RELOAD_BEGIN", script)
        self.assertIn("systemctl reload dbus-broker.service", script)
        self.assertIn("GUEST_ONLY_DBUS_CONFIG_RELOAD_FAILED", script)
        self.assertIn("C4B_PASS // SIGNED_DBUS_POLICY_RELOADED_WITHOUT_SYSTEM_BUS_RESTART", script)
        self.assertIn("check_logind_bus_health() {", script)
        self.assertIn("org.freedesktop.DBus GetNameOwner s org.freedesktop.login1", script)
        self.assertIn("org.freedesktop.login1.Manager ListInhibitors", script)
        self.assertIn("LOGIND_DBUS_OWNER_UNAVAILABLE_", script)
        self.assertIn("LOGIND_INHIBITOR_QUERY_UNRESPONSIVE_", script)
        self.assertIn("DBUS_BROKER_REPLACED_DURING_CONFIG_RELOAD", script)
        self.assertIn("DBUS_BROKER_IDENTITY_CHANGED_ON_CONFIG_RELOAD", script)
        self.assertIn("LOGIND_OWNER_CHANGED_DURING_CONFIG_RELOAD", script)
        before = script.index("  check_logind_bus_health BEFORE_C4B_POLICY_RELOAD")
        reload_at = script.index("  timeout --signal=TERM --kill-after=5s 45s systemctl reload dbus-broker.service", before)
        after_reload = script.index("  check_logind_bus_health AFTER_C4B_POLICY_RELOAD", reload_at)
        denied = script.index("  client_check c4b-reader claim OWN_REFUSED", after_reload)
        service = script.index("  stage EXPLICIT_SIGNED_FAKE_SERVICE_START_BEGIN", denied)
        cleanup = script.index("  check_logind_bus_health AFTER_C4B_RUNTIME_CLEANUP")
        accepted = script.index("  stage BOOTED_RUNTIME_ACCEPTED", cleanup)
        self.assertLess(before, reload_at)
        self.assertLess(reload_at, after_reload)
        self.assertLess(after_reload, denied)
        self.assertLess(denied, service)
        self.assertLess(cleanup, accepted)
        self.assertIn(
            "install -D -m 0644 %{_sourcedir}/org.postapollo.ConnectionsStatus1.conf.template",
            SIGNED_C3D_RPM_SPEC.read_text(),
        )

    def test_050_running_signed_python_host_observed_in_real_c4b_guest(self):
        script = GUEST.read_text()
        gate = POLICY_GATE.read_text()
        self.assertIn(
            'c3d_saved=/var/lib/c4b-runtime-assets/c3d-status.rpm', gate)
        self.assertIn(
            'install -m 0600 "$c3d_source" "$c3d_saved"', gate)
        self.assertIn(
            "C4B_PASS // SIGNED_C3D_PUBLIC_RPM_SNAPSHOT_RETAINED_FOR_RUNNING_OBSERVATION",
            gate)
        self.assertIn(
            '-s "$assets/c3d-status.rpm" ]] || fail "MISSING_OFFLINE_FIXTURES"',
            script)
        self.assertIn('stage SIGNED_C3D_RUNNING_HOST_MEASUREMENT_BEGIN', script)
        self.assertIn('GITHUB_ACTIONS=true POST_APOLLO_C4B_TEST_GUEST=1', script)
        self.assertIn('"$pid" "$assets/c3d-status.rpm"', script)
        self.assertIn('SIGNED_C3D_RUNNING_HOST_MEASUREMENT_REFUSED', script)
        self.assertIn(
            'C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED',
            script)
        self.assertLess(
            script.index('C3B_OS_ORIGIN_VERIFICATION_BEGIN'),
            script.index('SIGNED_C3D_RUNNING_HOST_MEASUREMENT_REFUSED'))
        self.assertLess(
            script.index('SIGNED_C3D_RUNNING_HOST_MEASUREMENT_REFUSED'),
            script.index('stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN'))
        begin = "import grp, hashlib, json, os, pwd, re, stat, subprocess, sys\n"
        self.assertEqual(script.count(begin), 1)
        python_body = begin + script.split(begin, 1)[1].split(
            "\nC4B_RUNNING_HOST_PROBE", 1)[0]
        ast.parse(python_body)
        for needle in (
            '"/run/ostree-booted"', '"MainPID", UNIT',
            '"GetConnectionUnixProcessID"', '"GetConnectionUnixUser"',
            '"/proc/{pid}/stat"', '"/proc/{pid}/exe"',
            '"/proc/{pid}/cmdline"', '"/proc/{pid}/attr/current"',
            '"/proc/{pid}/status"', '"NoNewPrivs:"',
            '"--checksig", "-v", rpm',
            '"[%{FILENAMES}\t%{FILEDIGESTS}\n]"',
            '"--read-only"', 'os.O_NOFOLLOW',
            'signedGuestOriginAuthenticated=False',
            'evidenceCryptographicallyAttested=False',
            'hostAuthenticated=False', 'credentialActionsEnabled=False',
            'productionAuthority=False',
        ):
            if needle == '"NoNewPrivs:"':
                self.assertIn("NoNewPrivs:", python_body)
            else:
                self.assertIn(needle, python_body)
        self.assertNotIn("rpm --import", python_body)
        self.assertNotIn("systemctl enable", python_body)
        self.assertNotIn("subprocess.Popen", python_body)
        self.assertNotIn("os.system(", python_body)

    def test_05_fully_disposable_ci_and_production_deny_only(self):
        workflow = WORKFLOW.read_text()
        script = GUEST.read_text()
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("github.actor == 'kudokudo1'", workflow)
        self.assertIn("C4A_SERVICE_RPM_DIR=", workflow)
        self.assertIn("C4B_RUNTIME_ASSETS_DIR=", workflow)
        self.assertIn("timeout 3550s", workflow)
        self.assertIn("tests/connections/test_connections_c2n_policy_contract.py", workflow)
        self.assertIn("C4B_PASS // PRODUCTION_CREDENTIALS_GRANTS_AND_HOST_AUTH_DISABLED", workflow)
        self.assertIn("GUEST_HAS_NETWORK_INTERFACE", script)
        broker = ROOT / "services/connections/ConnectionsBroker.qml"
        status = ROOT / "services/connections/ConnectionsRequestStatus.qml"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      broker.read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      status.read_text())
        self.assertIn("C4A_PASS // SIGNED_FAKE_SERVICE_BOOTED_FILES_OWNED_AND_INTACT",
                      C4A.read_text())
        self.assertNotIn("POST_APOLLO_FIRMS_MAP_KEY", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
