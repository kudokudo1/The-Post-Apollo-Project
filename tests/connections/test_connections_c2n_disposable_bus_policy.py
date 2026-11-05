#!/usr/bin/env python3
"""C2n CI-only real D-Bus system-like policy smoke with disposable OS principals.

NEVER run on a workstation. The GitHub workflow creates three disposable
accounts on its own short-lived Ubuntu runner before executing this test.
This is NOT a production host installation or service identity attestation.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
POLICY = (ROOT / "services/connections/experiments/c2n_package"
          / "org.postapollo.ConnectionsStatus1.conf.template")
FIXTURE = ROOT / "tests/connections/fixtures/C2nBusPolicyFixture.py"
SERVICE = "postapollo-connections"
READER = "c2n-reader-ci"
OUTSIDER = "c2n-outsider-ci"
FLAG = "POST_APOLLO_C2N_TEST_BUS_ONLY"


def build_config(path: Path) -> None:
    fragment = ET.parse(POLICY).getroot()
    root = ET.Element("busconfig")
    ET.SubElement(root, "type").text = "system"
    ET.SubElement(root, "listen").text = "unix:tmpdir=/tmp"
    ET.SubElement(root, "auth").text = "EXTERNAL"
    admission = ET.SubElement(root, "policy", context="default")
    ET.SubElement(admission, "allow", user="*")
    ET.SubElement(admission, "allow", send_destination="org.freedesktop.DBus")
    # An isolated bare system-like bus does not import the standard receive
    # rules. Emulate default unicast receipt while testing our send/own policy.
    ET.SubElement(admission, "allow", receive_sender="*")
    # In a real system bus, one method return/error is allowed in response
    # to a requested call. The isolated bare bus needs these baseline rules.
    ET.SubElement(admission, "allow",
                  send_type="method_return", send_requested_reply="true")
    ET.SubElement(admission, "allow",
                  send_type="error", send_requested_reply="true")
    for policy in list(fragment):
        root.append(policy)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


class C2nCrossUidPolicySmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only the dedicated GitHub workflow may invoke this; deny accidental runs.
        if os.environ.get("POST_APOLLO_C2N_CI_CROSS_UID") != "1":
            raise RuntimeError("C2N_REFUSED_CROSS_UID_OUTSIDE_DISPOSABLE_CI")
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("C2N_REFUSED_NOT_GITHUB_ACTIONS")
        temp = tempfile.TemporaryDirectory(prefix="c2n-systemlike-bus-")
        cls.tmp = temp
        cls.addClassCleanup(temp.cleanup)
        # GitHub checkout is private to the runner UID. Copy only this fake
        # fixture into an explicitly world-readable disposable CI directory.
        os.chmod(temp.name, 0o755)
        cls.fixture_path = Path(temp.name) / "C2nBusPolicyFixture.py"
        shutil.copyfile(FIXTURE, cls.fixture_path)
        os.chmod(cls.fixture_path, 0o644)
        cfg = Path(temp.name) / "config.xml"
        build_config(cfg)
        cls.daemon = subprocess.Popen(
            ["dbus-daemon", f"--config-file={cfg}", "--nofork", "--print-address=1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        )
        cls.addClassCleanup(cls.stop_process, cls.daemon)
        address = cls.daemon.stdout.readline().decode().strip()
        if not address.startswith("unix:"):
            err = cls.daemon.stderr.read(3000).decode(errors="replace")
            raise RuntimeError("D-Bus test daemon did not start: " + err)
        cls.address = address

    @staticmethod
    def stop_process(p):
        if p.poll() is None:
            if getattr(p, "_c2n_group", False):
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                p.terminate()
        try:
            p.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            if getattr(p, "_c2n_group", False):
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                p.kill()
            p.communicate(timeout=3)

    @classmethod
    def args(cls, user, mode):
        return [
            "sudo", "-n", "-u", user, "env",
            f"C2N_TEST_BUS_ADDRESS={cls.address}", f"{FLAG}=1",
            sys.executable, "-I", "-B", str(cls.fixture_path), mode,
        ]

    @classmethod
    def call(cls, user, mode):
        return subprocess.run(
            cls.args(user, mode), stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=6,
        )

    @classmethod
    def start_host(cls):
        p = subprocess.Popen(
            cls.args(SERVICE, "serve"), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
        )
        p._c2n_group = True
        try:
            ready, _, _ = select.select([p.stdout], [], [], 8)
            if not ready:
                raise RuntimeError("No service readiness notification")
            line = p.stdout.readline().strip()
            if line != "READY":
                raise RuntimeError("Test service refused name: " + line)
            return p
        except Exception:
            cls.stop_process(p)
            raise

    def test_01_only_proposed_service_uid_can_own_bus_name(self):
        for user in (READER, OUTSIDER):
            with self.subTest(user=user):
                p = self.call(user, "claim")
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout.strip(), "OWN_REFUSED")
        host = self.start_host()
        try:
            self.assertIsNone(host.poll())
            duplicate = self.call(OUTSIDER, "claim")
            self.assertEqual(duplicate.stdout.strip(), "OWN_REFUSED")
        finally:
            self.stop_process(host)

    def test_02_reader_status_allowed_but_approve_denied(self):
        host = self.start_host()
        try:
            reader = self.call(READER, "status")
            self.assertEqual(reader.returncode, 0, reader.stderr)
            self.assertEqual(reader.stdout.strip(), "STATUS_READONLY_UNVERIFIED")
            approval = self.call(READER, "approve")
            self.assertEqual(approval.returncode, 0, approval.stderr)
            self.assertEqual(approval.stdout.strip(), "METHOD_REFUSED")
        finally:
            self.stop_process(host)

    def test_03_untrusted_uid_cannot_call_status_or_approve(self):
        host = self.start_host()
        try:
            for mode in ("status", "approve"):
                call = self.call(OUTSIDER, mode)
                self.assertEqual(call.returncode, 0, call.stderr)
                self.assertEqual(call.stdout.strip(), "METHOD_REFUSED")
        finally:
            self.stop_process(host)

    def test_04_bad_address_and_ci_gate_block_fixture(self):
        env = dict(os.environ)
        env.pop(FLAG, None)
        env["C2N_TEST_BUS_ADDRESS"] = self.address
        result = subprocess.run([sys.executable, "-I", "-B", str(FIXTURE), "serve"],
                                env=env, capture_output=True, timeout=4)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"C2N_REFUSED_NOT_ISOLATED_CI", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
