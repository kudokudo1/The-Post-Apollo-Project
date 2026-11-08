"""P26: Fedora Silverblue oFono setup stages only an operator-approved host deployment."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))

import PhoneCallingSetupHandoff as gui
import PhoneOfonoInstallSession as session
import PhoneInstallCommandDiscovery as discovery


def present():
    return {
        "schema": "post-apollo.phone.calls-prerequisites.v0",
        "execution": "READ_ONLY_CALL_DIAGNOSIS",
        "state": "PACKAGE_NOT_INSTALLED", "package": "NOT_INSTALLED",
        "serviceLoad": "not-found", "serviceActive": "inactive",
        "systemBus": "UNKNOWN", "hfpVerified": False,
        "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
    }


def status_response(deployments=None):
    if deployments is None:
        deployments = [{"booted": True}, {"booted": False}]
    return SimpleNamespace(
        returncode=0, stdout=json.dumps({"deployments": deployments})
    )


def system_tools(include_ostree=True):
    items = {
        "foot": "/usr/bin/foot", "python3": "/usr/bin/python3",
        "pkcon": "/usr/bin/pkcon", "pkexec": "/usr/bin/pkexec",
        "dnf5": "/usr/bin/dnf5",
    }
    if include_ostree:
        items["rpm-ostree"] = "/usr/bin/rpm-ostree"
    return items.get


class SilverblueSetupTests(unittest.TestCase):
    def test_atomic_host_is_marker_not_fedora_label(self):
        with mock.patch.object(session.os.path, "exists", return_value=True):
            self.assertTrue(session._ostree_host())
        with mock.patch.object(session.os.path, "exists", return_value=False):
            self.assertFalse(session._ostree_host())
        with mock.patch.object(gui, "Path") as pathlib:
            pathlib.return_value.exists.return_value = True
            self.assertTrue(gui._ostree_host())

    def test_exact_host_executable_is_trusted_not_path_override(self):
        self.assertEqual(
            discovery.trusted_program(
                "rpm-ostree", find=lambda _: "/usr/bin/rpm-ostree",
                realpath=lambda s: s),
            "/usr/bin/rpm-ostree"
        )
        self.assertIsNone(discovery.trusted_program(
            "rpm-ostree", find=lambda _: "/tmp/rpm-ostree",
            realpath=lambda s: s))
        with mock.patch.object(discovery.shutil, "which",
                               side_effect=lambda name, path=None:
                               "/tmp/rpm-ostree" if path is None
                               else "/usr/bin/rpm-ostree"):
            self.assertEqual(discovery.find_os_program("rpm-ostree"),
                             "/usr/bin/rpm-ostree")

    def test_host_handoff_requires_ostree_even_when_pkcon_dnf_exist(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=present, is_fedora=lambda: True,
            is_ostree=lambda: True,
            find=system_tools(include_ostree=False),
            already_open=lambda: False, launcher=launcher
        )
        self.assertEqual(result["status"], "PACKAGE_MANAGER_UNAVAILABLE")
        self.assertEqual(result["missingTools"], ["RPM_OSTREE"])
        self.assertFalse(result["packageInstalled"])
        launcher.assert_not_called()

    def test_ostree_host_handoff_uses_same_staged_terminal(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=present, is_fedora=lambda: True,
            is_ostree=lambda: True, find=system_tools(),
            already_open=lambda: False, launcher=launcher
        )
        self.assertEqual(result["status"], "STAGED_TERMINAL_REQUESTED")
        self.assertEqual(result["missingTools"], [])
        self.assertFalse(result["packageInstalled"])
        self.assertFalse(result["hfpVerified"])
        self.assertEqual(launcher.call_args.args[0][:4],
                         ["/usr/bin/foot", "--app-id", gui.INSTALL_APP_ID, "-e"])
        self.assertEqual(launcher.call_args.args[0][-1], "--interactive-ofono")
        self.assertNotIn("rpm-ostree", " ".join(launcher.call_args.args[0]))

    def test_status_requires_current_booted_first_and_no_staged_entry(self):
        good = status_response()
        for deployments in (
            [{"booted": False}, {"booted": True}],
            [{"booted": True, "staged": True}],
            [{"booted": True}, {"booted": True}],
            [],
        ):
            with self.subTest(deployments=deployments):
                runner = mock.Mock(return_value=status_response(deployments))
                self.assertFalse(session._ostree_idle("/usr/bin/rpm-ostree", runner))
                self.assertEqual(runner.call_args.args[0],
                                 ["/usr/bin/rpm-ostree", "status", "--json"])
        self.assertTrue(session._ostree_idle(
            "/usr/bin/rpm-ostree", mock.Mock(return_value=good)))

    def test_declining_explicit_host_consent_never_installs(self):
        runner = mock.Mock(return_value=status_response())
        approve = mock.Mock(return_value="no")
        hold = mock.Mock()
        with mock.patch("builtins.print"):
            result = session.run_session(
                interactive=lambda: True, is_ostree=lambda: True,
                find=system_tools(), runner=runner,
                approve=approve, hold=hold)
        self.assertEqual(result, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("INSTALL OFONO", approve.call_args.args[0])
        hold.assert_not_called()

    def test_pending_deployment_blocks_second_transaction_before_prompt(self):
        runner = mock.Mock(return_value=status_response(
            [{"booted": False}, {"booted": True}]))
        approve = mock.Mock(return_value="INSTALL OFONO")
        with mock.patch("builtins.print"):
            result = session.run_session(
                interactive=lambda: True, is_ostree=lambda: True,
                find=system_tools(), runner=runner, approve=approve,
                hold=mock.Mock())
        self.assertEqual(result, 3)
        runner.assert_called_once()
        approve.assert_not_called()

    def test_untrusted_or_absent_ostree_refuses_even_with_packagekit(self):
        for choice in (None, "/tmp/rpm-ostree"):
            with self.subTest(choice=choice):
                p = {"rpm-ostree": choice, "pkcon": "/usr/bin/pkcon"}
                runner = mock.Mock()
                with mock.patch("builtins.print"):
                    value = session.run_session(
                        interactive=lambda: True, is_ostree=lambda: True,
                        find=p.get, runner=runner, hold=mock.Mock(),
                        approve=mock.Mock(return_value="INSTALL OFONO"))
                self.assertEqual(value, 3)
                runner.assert_not_called()

    def test_malformed_or_unavailable_status_refuses(self):
        for answer in (SimpleNamespace(returncode=2, stdout="{}"),
                       SimpleNamespace(returncode=0, stdout="no JSON"),
                       SimpleNamespace(returncode=0, stdout='{"deployments": null}')):
            with self.subTest(answer=answer.stdout):
                runner = mock.Mock(return_value=answer)
                with mock.patch("builtins.print"):
                    value = session.run_session(
                        interactive=lambda: True, is_ostree=lambda: True,
                        find=system_tools(), runner=runner,
                        approve=mock.Mock(return_value="INSTALL OFONO"),
                        hold=mock.Mock())
                self.assertEqual(value, 3)
                runner.assert_called_once()

    def test_success_only_stages_ofono_with_reboot_message_no_live_action(self):
        runner = mock.Mock(side_effect=[
            status_response(), SimpleNamespace(returncode=0),
        ])
        hold = mock.Mock(return_value="")
        with mock.patch("builtins.print") as printed:
            result = session.run_session(
                interactive=lambda: True, is_ostree=lambda: True,
                find=system_tools(), runner=runner,
                approve=lambda _: "INSTALL OFONO", hold=hold)
        self.assertEqual(result, 0)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args_list[1].args[0],
                         ["/usr/bin/rpm-ostree", "install", "ofono"])
        self.assertEqual(runner.call_args_list[1].kwargs, {"check": False})
        output = " ".join(" ".join(map(str, c.args)) for c in printed.call_args_list)
        self.assertIn("Reboot separately", output)
        self.assertIn("NOT active", output)
        hold.assert_called_once()
        self.assertNotIn("--apply-live", output)
        self.assertNotIn("systemctl", session.Path(__file__).read_text() if hasattr(session, "Path") else "")

    def test_failed_transaction_never_claims_installed_or_reboots(self):
        runner = mock.Mock(side_effect=[
            status_response(), SimpleNamespace(returncode=1),
        ])
        with mock.patch("builtins.print") as printed:
            result = session.run_session(
                interactive=lambda: True, is_ostree=lambda: True,
                find=system_tools(), runner=runner,
                approve=lambda _: "INSTALL OFONO", hold=lambda _: "")
        self.assertEqual(result, 2)
        out = " ".join(str(c.args) for c in printed.call_args_list)
        self.assertIn("did not confirm completion", out)
        self.assertNotIn("Reboot separately", out)


if __name__ == "__main__":
    unittest.main()
