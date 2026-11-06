"""Trusted Fedora executable lookup even with an incomplete desktop PATH."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services" / "phone" / "PhoneInstallCommandDiscovery.py"
spec = importlib.util.spec_from_file_location("phone_install_discovery", FILE)
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class InstallerCommandDiscoveryTests(unittest.TestCase):
    def test_trimmed_path_still_finds_os_executable(self):
        calls = []
        def which(name, path=None):
            calls.append((name, path))
            return None if path is None else "/usr/bin/dnf5"
        with mock.patch.object(tools.shutil, "which", side_effect=which):
            result = tools.find_os_program("dnf5")
        self.assertEqual(result, "/usr/bin/dnf5")
        self.assertEqual(calls, [("dnf5", None), ("dnf5", "/usr/bin:/bin")])

    def test_hostile_path_entry_is_ignored_in_favor_of_system_program(self):
        calls = []
        def which(name, path=None):
            calls.append(path)
            return "/home/user/fake/dnf5" if path is None else "/usr/bin/dnf5"
        with mock.patch.object(tools.shutil, "which", side_effect=which):
            result = tools.find_os_program("dnf5")
        self.assertEqual(result, "/usr/bin/dnf5")
        self.assertEqual(calls, [None, "/usr/bin:/bin"])

    def test_always_refuses_non_installer_programs_and_non_absolute_paths(self):
        with mock.patch.object(tools.shutil, "which") as which:
            self.assertIsNone(tools.find_os_program("anything"))
            which.assert_not_called()
        for value in (None, "", "dnf5", "/tmp/dnf5", 2, True):
            with self.subTest(value=value):
                p = tools.trusted_program(
                    "dnf5", find=lambda name: value,
                    realpath=lambda x: x)
                self.assertIsNone(p)

    def test_accepts_system_bins_and_rejects_symlink_outside_system(self):
        self.assertEqual(tools.trusted_program(
            "foot", find=lambda _: "/usr/bin/foot",
            realpath=lambda x: "/usr/bin/foot"), "/usr/bin/foot")
        self.assertEqual(tools.trusted_program(
            "foot", find=lambda _: "/bin/foot",
            realpath=lambda x: "/usr/bin/foot"), "/bin/foot")
        self.assertIsNone(tools.trusted_program(
            "pkexec", find=lambda _: "/usr/bin/pkexec",
            realpath=lambda _: "/home/user/pkexec"))

    def test_dnf_alias_only_when_pointing_to_dnf5(self):
        commands = {"dnf5": None, "dnf": "/usr/bin/dnf"}
        def finder(name):
            return commands.get(name)
        self.assertEqual(tools.trusted_dnf5(
            find=finder, realpath=lambda x:
            "/usr/bin/dnf5" if x == "/usr/bin/dnf" else x),
            "/usr/bin/dnf")
        self.assertIsNone(tools.trusted_dnf5(
            find=finder, realpath=lambda x:
            "/usr/bin/dnf-3" if x == "/usr/bin/dnf" else x))
        self.assertIsNone(tools.trusted_dnf5(
            find=finder, realpath=lambda x:
            "/usr/bin/dnf4" if x == "/usr/bin/dnf" else x))

    def test_dnf5_named_binary_rejects_non_dnf5_target(self):
        commands = {"dnf5": "/usr/bin/dnf5", "dnf": None}
        self.assertIsNone(tools.trusted_dnf5(
            find=commands.get, realpath=lambda _: "/usr/bin/dnf-3"))
        self.assertEqual(tools.trusted_dnf5(
            find=commands.get, realpath=lambda _: "/usr/bin/dnf5"),
            "/usr/bin/dnf5")

    def test_faulty_resolver_fails_closed(self):
        def fail(_):
            raise OSError("SECRET")
        self.assertIsNone(tools.trusted_program(
            "pkexec", find=lambda _: "/usr/bin/pkexec", realpath=fail))
        self.assertIsNone(tools.trusted_dnf5(
            find=lambda name: "/usr/bin/" + name, realpath=fail))

    def test_no_host_mutation_or_phone_access(self):
        source = FILE.read_text()
        for forbidden in (
            "subprocess.Popen", "subprocess.run", "sudo ", "pkexec ",
            "install ofono", "bluetoothctl", "systemctl start",
            "os.system(", "shell=True", "sendMessage(", "getContacts(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
