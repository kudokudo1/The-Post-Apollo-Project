#!/usr/bin/env python3
"""C2k real-process, disposable-only status launcher regression tests."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "services/connections/ConnectionsHostReadOnlyLauncher.py"
SOCKET_PATH = Path("post-apollo/connections-status-v1.sock")
sys.path.insert(0, str(ROOT / "services/connections"))
from ConnectionsHostStatusInspect import probe  # noqa: E402


class C2kReadOnlyLauncherTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="connections-c2k-")
        self.addCleanup(self.scratch.cleanup)
        self.runtime = Path(self.scratch.name) / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "PYTHONNOUSERSITE": "1",
        }
        self.processes = []

    def _launch(self, args=None, env=None):
        p = subprocess.Popen(
            [sys.executable, "-I", str(LAUNCHER)] + (
                ["--run-readonly"] if args is None else args
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env if env is None else env,
            cwd=self.scratch.name,
        )
        self.processes.append(p)
        self.addCleanup(self._stop, p)
        return p

    @staticmethod
    def _stop(p):
        if p.poll() is None:
            p.terminate()
        try:
            p.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate(timeout=3)

    def _wait_socket(self, p):
        path = self.runtime / SOCKET_PATH
        until = time.monotonic() + 5
        while time.monotonic() < until:
            if p.poll() is not None:
                _out, err = p.communicate(timeout=1)
                self.fail("Launcher died before startup: " + err.decode())
            if path.exists():
                return path
            time.sleep(0.03)
        self.fail("Explicit launcher did not create its test socket")

    def test_01_no_implicit_start_or_unrecognized_arguments(self):
        for args in ([], ["--start"], ["--run-readonly", "--allow-key"]):
            p = self._launch(args=args)
            out, err = p.communicate(timeout=3)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(out, b"")
            self.assertIn(b"C2K_REFUSED_NO_APPROVED_RUNTIME_LAUNCH", err)
            self.assertFalse((self.runtime / SOCKET_PATH).exists())

    def test_02_status_observed_but_never_authenticated_or_authorized(self):
        p = self._launch()
        path = self._wait_socket(p)
        info = path.lstat()
        self.assertTrue(stat.S_ISSOCK(info.st_mode))
        self.assertEqual(info.st_uid, os.geteuid())
        self.assertEqual(info.st_mode & 0o077, 0)
        observation = probe({"XDG_RUNTIME_DIR": str(self.runtime)})
        self.assertEqual(observation["status"], "OBSERVED_UNVERIFIED")
        self.assertEqual(observation["state"], "IDLE")
        for field in ("hostAuthenticated", "credentialPresent",
                      "grantActive", "canApprove"):
            self.assertIs(observation[field], False, field)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
            c.settimeout(1)
            c.connect(str(path))
            c.sendall(b"STATUS V1\n")
            raw = c.recv(768)
        obj = json.loads(raw)
        self.assertEqual(set(obj), {"schema", "provider", "state", "readonly"})
        self.assertEqual(obj["state"], "IDLE")
        self.assertEqual(obj["provider"], "nasa-firms")
        self.assertIs(obj["readonly"], True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
            c.settimeout(1)
            c.connect(str(path))
            c.sendall(b"APPROVE\n")
            self.assertEqual(c.recv(768), b"")
        self.assertIsNone(p.poll())

    def test_03_second_launcher_cannot_replace_running_server(self):
        owner = self._launch()
        path = self._wait_socket(owner)
        inode = path.lstat().st_ino
        duplicate = self._launch()
        _out, err = duplicate.communicate(timeout=3)
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn(b"C2K_REFUSED_UNSAFE_OR_OCCUPIED_HOST_RUNTIME", err)
        self.assertEqual(path.lstat().st_ino, inode)
        self.assertIsNone(owner.poll())
        self.assertEqual(probe(self.env)["status"], "OBSERVED_UNVERIFIED")

    def test_04_sigterm_removes_only_owned_socket(self):
        marker = self.runtime / "not-owned-by-launcher.txt"
        marker.write_text("keep")
        p = self._launch()
        path = self._wait_socket(p)
        p.terminate()
        self.assertEqual(p.wait(timeout=3), 0)
        self.assertFalse(path.exists())
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(probe(self.env)["status"], "HOST_NOT_FOUND")

    def test_05_unsafe_runtime_and_symlink_are_refused(self):
        bad = dict(self.env)
        bad["XDG_RUNTIME_DIR"] = "relative/path"
        p = self._launch(env=bad)
        self.assertEqual(p.wait(timeout=3), 2)

        self.runtime.chmod(0o755)
        p = self._launch()
        self.assertEqual(p.wait(timeout=3), 2)
        self.assertFalse((self.runtime / SOCKET_PATH).exists())
        self.runtime.chmod(0o700)

        alias = Path(self.scratch.name) / "link"
        alias.symlink_to(self.runtime, target_is_directory=True)
        bad["XDG_RUNTIME_DIR"] = str(alias)
        p = self._launch(env=bad)
        self.assertEqual(p.wait(timeout=3), 2)
        self.assertFalse((self.runtime / SOCKET_PATH).exists())

    def test_06_importing_module_does_not_launch_a_host(self):
        # External tests use -I and a pinned file location, not PYTHONPATH.
        spec = importlib.util.spec_from_file_location("c2k_import_only", LAUNCHER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.run_readonly))
        self.assertFalse((self.runtime / SOCKET_PATH).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
