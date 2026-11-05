"""M15 host bridge security, lifecycle and explicit install contracts."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[2] / "experiments" / "company-vector-qt"


def load(module, filename):
    spec = importlib.util.spec_from_file_location(module, HERE / filename)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


bridge = load("company_vector_host_bridge_m15", "CompanyVectorHostBridge.py")
installer = load("company_vector_host_installer_m15", "install_host_bridge_m15.py")


class BridgeTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("tests require unprivileged user")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def populate(self):
        for parts in bridge.LAB_FILES:
            file = self.home.joinpath(*parts)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"\x7fELF")
            file.chmod(0o700 if parts == bridge.LAB_FILES[0] else 0o600)

    def test_missing_or_symlinked_lab_refused_without_launch(self):
        self.assertEqual(bridge.probe(self.home)["status"], "NOT_INSTALLED")
        self.populate()
        source = self.home.joinpath(*bridge.LAB_FILES[0])
        source.unlink()
        outside = self.home / "outside"
        outside.write_bytes(b"\x7fELF")
        source.symlink_to(outside)
        with patch.object(bridge.os, "execve", side_effect=AssertionError("must not exec")):
            self.assertEqual(bridge.main([], self.home), 69)

    def test_group_writable_executable_refused(self):
        self.populate()
        executable = self.home.joinpath(*bridge.LAB_FILES[0])
        executable.chmod(0o722)
        self.assertEqual(bridge.probe(self.home)["status"], "NOT_INSTALLED")

    def test_qt_unverified_fails_closed(self):
        self.populate()
        with patch.object(bridge, "_check_host_qt", return_value=False), patch.object(bridge.os, "execve", side_effect=AssertionError):
            self.assertEqual(bridge.probe(self.home)["status"], "HOST_QT_UNVERIFIED")
            self.assertEqual(bridge.main([], self.home), 69)

    def test_offline_and_online_replace_same_pid_without_toolbox_spawn(self):
        self.populate()
        executable = self.home.joinpath(*bridge.LAB_FILES[0])
        for args, expected in (([], []), (["--styled-online"], ["--styled-online"])):
            invocations = []

            def intercept(path, argv, env):
                invocations.append((path, argv, env))
                raise OSError("synthetic exec refusal")

            with self.subTest(args=args), patch.object(bridge, "probe", return_value={"status": "READY"}), patch.object(bridge.os, "execve", side_effect=intercept):
                self.assertEqual(bridge.main(args, self.home), 70)
            self.assertEqual(len(invocations), 1)
            path, argv, env = invocations[0]
            self.assertEqual(path, str(executable))
            self.assertEqual(argv, [str(executable), *expected])
            self.assertIn(str(self.home / "postapollo-vector-lab/maplibre-install/lib64"), env["LD_LIBRARY_PATH"])
            self.assertNotIn("--owner-local-hubs", argv)

    def test_invalid_args_cannot_execute(self):
        self.populate()
        for args in (["--online"], ["--owner-local-hubs"], ["--styled-online", "--capture"], ["--probe", "--styled-online"]):
            with self.subTest(args=args), patch.object(bridge.os, "execve", side_effect=AssertionError):
                self.assertEqual(bridge.main(args, self.home), 2)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("tests require unprivileged user")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.source = HERE / "CompanyVectorHostBridge.py"

    def target(self):
        return self.home.joinpath(*installer.TARGET_PARTS)

    def test_inspection_does_not_write_and_explicit_install_remove(self):
        self.assertEqual(installer.perform("check", self.home, self.source)["status"], "NOT_INSTALLED")
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(installer.perform("install", self.home, self.source)["status"], "INSTALLED")
        self.assertEqual(self.target().read_bytes(), self.source.read_bytes())
        self.assertEqual(stat.S_IMODE(self.target().stat().st_mode), 0o700)
        self.assertEqual(installer.perform("install", self.home, self.source)["status"], "ALREADY_INSTALLED")
        self.assertEqual(installer.perform("remove", self.home, self.source)["status"], "REMOVED")
        self.assertFalse(self.target().exists())

    def test_existing_foreign_file_never_overwritten_or_removed(self):
        self.target().parent.mkdir(parents=True)
        self.target().write_text("foreign binary")
        self.target().chmod(0o700)
        self.assertEqual(installer.perform("install", self.home, self.source)["status"], "REFUSED_EXISTING")
        self.assertEqual(installer.perform("remove", self.home, self.source)["status"], "REFUSED_EXISTING")
        self.assertEqual(self.target().read_text(), "foreign binary")

    def test_symlink_destination_refused(self):
        self.target().parent.mkdir(parents=True)
        other = self.home / "other"
        other.write_text("external")
        self.target().symlink_to(other)
        self.assertEqual(installer.perform("install", self.home, self.source)["status"], "REFUSED_EXISTING")
        self.assertEqual(other.read_text(), "external")

    def test_unsafe_directory_refused(self):
        parent = self.home / ".local"
        parent.mkdir(mode=0o777)
        parent.chmod(0o777)
        self.assertEqual(installer.perform("install", self.home, self.source)["status"], "UNSAFE_DIRECTORY")
        self.assertFalse(self.target().exists())


if __name__ == "__main__":
    unittest.main()
