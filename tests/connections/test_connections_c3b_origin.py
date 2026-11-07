#!/usr/bin/env python3
"""Offline C3b negative/positive tests; no host queries, credentials or grants."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3b_origin/C3bOriginCheck.py"
spec = importlib.util.spec_from_file_location("c3b_test_origin", SOURCE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def valid():
    return {
        "owner_first": ":1.73",
        "owner_last": ":1.73",
        "bus_pid": 4567,
        "bus_uid": 987,
        "main_pid": 4567,
        "systemd_user": "postapollo-connections",
        "systemd_active": "active",
        "unit_fragment": m.UNIT_PATH,
        "unit_cgroup": "/system.slice/" + m.UNIT,
        "proc_uids": [987, 987, 987, 987],
        "proc_args": [
            "/opt/postapollo-c2o-venv/bin/python3",
            m.HOST,
            "--read-only",
        ],
        "proc_cgroup": "/system.slice/" + m.UNIT,
        "proc_context": "system_u:system_r:postapollo_connections_t:s0",
        "proc_no_new_privs": True,
        "expected_uid": 987,
        "selinux_mode": "Enforcing",
        "kernel_enforcing": "1",
        "protected_files": {
            name: {"owner": 0, "mode": 0o644, "regular": True, "symlink": False}
            for name in m.FILES
        },
        "protected_dirs": {
            name: {"owner": 0, "mode": 0o755, "directory": True, "symlink": False}
            for name in m.PROTECTED_DIRS
        },
    }


class C3bOriginPolicyTests(unittest.TestCase):
    def denied(self, snapshot, status):
        result = m.evaluate(snapshot)
        self.assertEqual(result["status"], status)
        self.assertEqual(set(result), {"status", *m.DENIED_FLAGS})
        for name, expected in m.DENIED_FLAGS.items():
            self.assertIs(result[name], expected)

    def test_01_coherent_os_snapshot_is_still_not_authentication(self):
        self.denied(valid(), "C3B_OS_ORIGIN_COHERENT_TEST_ONLY")

    def test_02_reject_malformed_or_substituted_bus_owner(self):
        for changed in (":1.74", "org.postapollo.ConnectionsStatus1", "1.73", None):
            snapshot = valid()
            snapshot["owner_first"] = changed
            expected = ("C3B_OWNER_CHANGED" if changed == ":1.74" else "C3B_INVALID_OWNER")
            self.denied(snapshot, expected)
        snapshot = valid()
        snapshot["owner_last"] = ":1.74"
        self.denied(snapshot, "C3B_OWNER_CHANGED")

    def test_03_reject_bus_pid_and_systemd_pid_mismatch(self):
        for value in (4568, 0, True, "4567"):
            snapshot = valid()
            snapshot["bus_pid"] = value
            self.denied(snapshot, "C3B_PID_MISMATCH")

    def test_04_reject_any_wrong_or_root_uid(self):
        for key, value in [
            ("bus_uid", 0), ("bus_uid", 999),
            ("expected_uid", 0), ("expected_uid", True),
            ("proc_uids", [987, 0, 987, 987]),
            ("proc_uids", [987, 987, 987]), ("proc_uids", "987"),
        ]:
            snapshot = valid()
            snapshot[key] = value
            self.denied(snapshot, "C3B_UID_MISMATCH")

    def test_05_reject_unexpected_systemd_unit_and_command(self):
        for key, value, status in [
            ("systemd_user", "root", "C3B_UNIT_MISMATCH"),
            ("systemd_active", "failed", "C3B_UNIT_MISMATCH"),
            ("unit_fragment", "/tmp/untrusted.service", "C3B_UNIT_MISMATCH"),
            ("proc_args", ["/bin/bash", m.HOST, "--read-only"], "C3B_COMMAND_MISMATCH"),
            ("proc_args", ["/opt/postapollo-c2o-venv/bin/python3", m.HOST, "--approve"], "C3B_COMMAND_MISMATCH"),
            ("proc_args", ["/opt/postapollo-c2o-venv/bin/python3", m.HOST, "--read-only", "extra"], "C3B_COMMAND_MISMATCH"),
            ("proc_cgroup", "/user.slice/untrusted", "C3B_CGROUP_MISMATCH"),
            ("proc_args", [m.INTERPRETER + "-replacement", m.HOST, "--read-only"], "C3B_COMMAND_MISMATCH"),
            ("proc_args", [m.INTERPRETER + ".14", m.HOST, "--read-only"], "C3B_COMMAND_MISMATCH"),
        ]:
            snapshot = valid()
            snapshot[key] = value
            self.denied(snapshot, status)

    def test_06_reject_unconfined_selinux_and_non_enforcing_kernel(self):
        for key, value in [
            ("proc_context", "system_u:system_r:unconfined_service_t:s0"),
            ("proc_context", "unconfined_u:unconfined_r:postapollo_connections_t:s0"),
            ("proc_no_new_privs", False), ("proc_no_new_privs", 1),
            ("selinux_mode", "Permissive"), ("kernel_enforcing", "0"),
        ]:
            snapshot = valid()
            snapshot[key] = value
            self.denied(snapshot, "C3B_CONFINEMENT_MISMATCH")

    def test_06b_kernel_attr_current_nul_terminator_is_not_domain_data(self):
        context = "system_u:system_r:postapollo_connections_t:s0"
        self.assertEqual(m.normalize_kernel_context(context + "\x00"), context)
        self.assertEqual(m.normalize_kernel_context(context + "\x00\x00"), context)
        self.assertEqual(m.normalize_kernel_context(context + "\x00unsafe"),
                         context + "\x00unsafe")
        snapshot = valid()
        snapshot["proc_context"] = m.normalize_kernel_context(context + "\x00")
        self.denied(snapshot, "C3B_OS_ORIGIN_COHERENT_TEST_ONLY")

    def test_07_reject_unprotected_service_unit_and_dbus_policy(self):
        for name in m.FILES:
            for key, value in [
                ("owner", 1000), ("owner", True), ("mode", 0o666),
                ("regular", False), ("symlink", True),
            ]:
                snapshot = valid()
                snapshot["protected_files"][name][key] = value
                self.denied(snapshot, "C3B_UNPROTECTED_FILE")
        snapshot = valid()
        del snapshot["protected_files"][m.POLICY]
        self.denied(snapshot, "C3B_FILES_MISMATCH")

    def test_07b_reject_matching_but_forged_unit_cgroup_suffix(self):
        # Previous endswith check would have accepted these two false sources.
        snapshot = valid()
        snapshot["unit_cgroup"] = "/user.slice/fake" + m.EXPECTED_CGROUP
        snapshot["proc_cgroup"] = snapshot["unit_cgroup"]
        self.denied(snapshot, "C3B_CGROUP_MISMATCH")

    def test_07c_reject_untrusted_parent_directory_paths(self):
        for path in m.PROTECTED_DIRS:
            for key, value in (
                    ("owner", 1000), ("owner", True), ("mode", 0o775),
                    ("directory", False), ("symlink", True)):
                snapshot = valid()
                snapshot["protected_dirs"][path][key] = value
                self.denied(snapshot, "C3C_UNPROTECTED_DIRECTORY")
        snapshot = valid()
        del snapshot["protected_dirs"]["/opt"]
        self.denied(snapshot, "C3C_DIRECTORIES_MISMATCH")
        snapshot = valid()
        snapshot["protected_dirs"]["/tmp"] = {
            "owner": 0, "mode": 0o755, "directory": True, "symlink": False
        }
        self.denied(snapshot, "C3C_DIRECTORIES_MISMATCH")

    def test_08_reject_unexpected_evidence_fields(self):
        for snapshot in (None, [], {}, {"owner_first": ":1.2"}):
            self.denied(snapshot, "C3B_INVALID_EVIDENCE")
        snapshot = valid()
        snapshot["grantActive"] = True
        self.denied(snapshot, "C3B_INVALID_EVIDENCE")

    def test_09_production_remains_completely_disconnected(self):
        actual = SOURCE.read_text()
        self.assertNotIn("secret-tool", actual)
        self.assertNotIn("POST_APOLLO_FIRMS_MAP_KEY", actual)
        self.assertNotIn("grantEnabled", actual)
        base = ROOT / "services/connections"
        self.assertIn(
            "readonly property bool credentialActionsEnabled: false",
            (base / "ConnectionsBroker.qml").read_text(),
        )
        self.assertIn(
            "readonly property bool hostAuthenticated: false",
            (base / "ConnectionsRequestStatus.qml").read_text(),
        )
        for path in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3bOriginCheck", path.read_text(), path)

    def test_10_unapproved_test_entry_refuses_before_host_observation(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(SOURCE), "--verify-disposable"],
            env={"GITHUB_ACTIONS": "false", "POST_APOLLO_C3B_TEST_GUEST": "1"},
            capture_output=True, text=True, timeout=4,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("C3B_REFUSED_NOT_DISPOSABLE_GUEST", result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
