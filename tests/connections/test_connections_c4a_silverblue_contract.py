#!/usr/bin/env python3
"""C4a source contract only; full success requires REAL Silverblue reboot CI."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "tests/connections/c2v_silverblue/boot_official_silverblue.sh"
GUEST = ROOT / "tests/connections/c2v_silverblue/guest_ostree_reboot_cycle.sh"
GATE = ROOT / "tests/connections/c4a_silverblue/guest_signed_status_gate.sh"
WORKFLOW = ROOT / ".github/workflows/connections-c4a-silverblue-signed-status.yml"


class C4aContract(unittest.TestCase):
    def test_01_existing_offline_real_two_reboot_requirements_remain(self):
        host, guest = HOST.read_text(), GUEST.read_text()
        for required in (
            "Fedora-Silverblue-ostree-x86_64-44-1.7.iso",
            "9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682",
            "-nic none", "C2V_BLOCKED // OFFICIAL_SILVERBLUE_ISO_SHA256_MISMATCH",
            "C2V_PASS // ACTUAL_SILVERBLUE_BOOTED_LAYER_AND_ROLLBACK_SEQUENCE",
        ):
            self.assertIn(required, host)
        for required in (
            "rpm-ostree install --cache-only",
            "rpm-ostree rollback --reboot",
            "C2V_PASS // LAYER_ACTIVE_ONLY_AFTER_REAL_REBOOT",
            "C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER",
            "C2V_PASS // NO_CONNECTIONS_SERVICE_OR_CREDENTIALS_ACTIVATED",
            "C2V_PENDING_DEPLOYMENT_AUTHORITY",
            "status.get(\"transaction\") is not None",
            "C2V_MONITOR_STARTED_IN_SEPARATE_CGROUP",
            "C2V_MONITOR_HANDOFF_COMPLETE",
        ):
            self.assertIn(required, guest)

    def test_02_c4a_opt_in_is_exact_and_preserves_c2v_default(self):
        host, guest = HOST.read_text(), GUEST.read_text()
        self.assertIn('if [[ -v C4A_SERVICE_RPM_DIR', host)
        self.assertIn('c4a_requested=0', host)
        self.assertIn('c4a-opt-in.marker', host)
        self.assertIn('sha256sum --check --status c3d-artifact-manifest.sha256', host)
        self.assertIn('if [[ -f "$data/c4a-opt-in.marker" ]]; then', guest)
        self.assertIn('guest_signed_status_gate.sh', host)
        self.assertIn('set -- /mnt/c2v-offline/c2t-0.1.rpm', guest)
        self.assertIn('set -- "$@" /mnt/c2v-offline/c3d-status.rpm', guest)
        self.assertIn('if [[ -f /var/lib/c4a-signed-service-test ]]; then', guest)
        self.assertIn('local_refs=d.get("requested-local-packages") or []', guest)
        self.assertIn('re.fullmatch(r"sha256:[a-fA-F0-9]{64}:"+re.escape(nevra),ref)', guest)
        self.assertIn('if not (pending and sys.argv[2] in package_refs):', guest)
        self.assertIn('C4A_SIGNED_SERVICE_NOT_VALID_AFTER_REBOOT', guest)
        self.assertIn('C4A_SIGNED_SERVICE_ROLLBACK_NOT_VERIFIED', guest)

    def test_03_signed_service_has_exact_fixed_paths_and_is_never_started(self):
        gate = GATE.read_text()
        self.assertIn('pkg=postapollo-connections-c3d-ci-status', gate)
        for item in (
            "/usr/libexec/post-apollo/connections-status-host",
            "/usr/lib/systemd/system/postapollo-connections-status.service",
            "/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf",
        ):
            self.assertIn(item, gate)
        for item in (
            "SIGNED_PACKAGE_PAYLOAD_PATH_ALLOWLIST_FAILED",
            "SIGNED_PACKAGE_HAS_SCRIPTLETS_OR_TRIGGERS",
            "rpmkeys --dbpath",
            "TEST_SIGNER_UNTRUSTED_BEFORE_EXPLICIT_IMPORT",
            "TEST_ONLY_RPM_SIGNATURE_VERIFIED_ISOLATED_FROM_BOOTED_RPMDB",
            "rpm -V",
            "rpm -qf",
            "SIGNED_FAKE_SERVICE_BOOTED_FILES_OWNED_AND_INTACT",
            "SIGNED_FAKE_SERVICE_REMOVED_BY_REAL_BOOTED_ROLLBACK",
            "ISOLATED_TEST_SIGNER_KEYRING_REMOVED",
            "GUEST_NETWORK_INTERFACE_PRESENT",
            "SELINUX_NOT_ENFORCING",
            "FAKE_SERVICE_ACTIVE",
            "FAKE_SERVICE_ENABLED",
            "FAKE_DBUS_NAME_OWNED",
        ):
            self.assertIn(item, gate)
        self.assertNotIn("systemctl start ", gate)
        self.assertNotIn("systemctl enable ", gate)
        self.assertNotIn("rpm -Uvh", gate)
        self.assertNotIn('rpmkeys --import', gate)
        self.assertIn('keydb=/var/lib/c4a-test-only-rpm-keyring', gate)

    def test_04_full_vm_must_prove_both_signed_boot_and_rollback(self):
        host = HOST.read_text()
        wf = WORKFLOW.read_text()
        for marker in (
            "C4A_PASS // TEST_SIGNER_UNTRUSTED_BEFORE_EXPLICIT_IMPORT",
            "C4A_PASS // TEST_ONLY_RPM_SIGNATURE_VERIFIED_ISOLATED_FROM_BOOTED_RPMDB",
            "C4A_PASS // SIGNED_FAKE_SERVICE_BOOTED_FILES_OWNED_AND_INTACT",
            "C4A_PASS // FAKE_SERVICE_NEVER_STARTED_OR_ENABLED",
            "C4A_PASS // SIGNED_FAKE_SERVICE_REMOVED_BY_REAL_BOOTED_ROLLBACK",
            "C4A_PASS // ISOLATED_TEST_SIGNER_KEYRING_REMOVED",
            "C4A_PASS // SIGNED_FAKE_SERVICE_SILVERBLUE_TWO_REBOOT_SEQUENCE",
        ):
            self.assertIn(marker, host)
        self.assertIn("permissions:\n  contents: read", wf)
        self.assertIn("persist-credentials: false", wf)
        self.assertIn("github.actor == 'kudokudo1'", wf)
        self.assertIn("C4A_SERVICE_RPM_DIR=", wf)
        self.assertIn("build_signed_ci_status.sh", wf)
        self.assertIn("build_signed_test_rpms.sh", wf)
        self.assertIn("boot_official_silverblue.sh", wf)

    def test_05_no_production_permissions_or_secret_dependency(self):
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        status = (ROOT / "services/connections/ConnectionsRequestStatus.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("readonly property bool hostAuthenticated: false", status)
        gate = GATE.read_text()
        for prohibited in ("secret-tool", "POST_APOLLO_FIRMS_MAP_KEY",
                           "http://", "https://", "curl ", "wget "):
            self.assertNotIn(prohibited, gate)
        self.assertIn("EPHEMERAL_SIGNER_NOT_INDEPENDENT_PRODUCTION_TRUST", gate)


    def test_06_c4a_pending_package_authority_rejects_lookalikes(self):
        # Exercise the literal embedded monitor verifier, not a rewritten
        # imitation, using only synthetic disposable JSON inputs.
        import json
        import subprocess
        import sys
        import tempfile

        guest = GUEST.read_text()
        source = guest.split("<<'C2V_PENDING_CHECK'\n", 1)[1].split(
            "\nC2V_PENDING_CHECK", 1
        )[0]
        import ast
        ast.parse(source)

        c2t = "postapollo-connections-c2t-fixture-0.1-1.fc44.noarch"
        c3d = "postapollo-connections-c3d-ci-status-0.1-1.fc44.noarch"
        base = "postapollo-connections-c2t-fixture"

        def check(refs, packages=(), pending=True, transaction=None):
            doc = {
                "transaction": transaction,
                "deployments": [
                    {"pending": pending, "booted": not pending,
                     "requested-local-packages": refs,
                     "packages": list(packages)},
                    {"booted": True},
                ],
            }
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "pending.json"
                p.write_text(json.dumps(doc))
                # Simulate the test-only marker without creating host files.
                mock = ('import os\nos.path.isfile = '
                        'lambda path: path == "/var/lib/c4a-signed-service-test"\n')
                return subprocess.run(
                    [sys.executable, "-c", mock + source, str(p), base],
                    capture_output=True, text=True, check=False,
                ).returncode

        self.assertEqual(check([c2t, c3d]), 0)
        self.assertEqual(
            check(["sha256:" + "a" * 64 + ":" + c2t,
                   "sha256:" + "b" * 64 + ":" + c3d]), 0
        )
        self.assertNotEqual(check([c2t, c3d.replace("-0.1", "-evil-0.1")]), 0)
        self.assertNotEqual(check([c2t], packages=[c3d]), 0)
        self.assertNotEqual(check([c3d], packages=[c2t]), 0)
        self.assertNotEqual(check([c2t, c3d], pending=False), 0)
        self.assertNotEqual(check([c2t, c3d], transaction="busy"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
