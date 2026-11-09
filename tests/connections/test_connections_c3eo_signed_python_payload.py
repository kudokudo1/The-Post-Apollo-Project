#!/usr/bin/env python3
"""C3e-O signed C3d RPM payload byte provenance. Fedora container CI only.

The root signer and RPM are disposable test artifacts from the C3d builder.
No signed package is installed, no trusted key is imported to the host.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eOSignedPythonPayloadGate.py"
spec = importlib.util.spec_from_file_location("c3eo_payload", SOURCE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class C3eOSignedPythonPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.geteuid() != 0 or os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("C3EO_REQUIRES_DISPOSABLE_FEDORA_CI_ROOT")
        cls.original_rpm = Path(os.environ["C3EO_RPM"])
        cls.original_public = Path(os.environ["C3EO_PUBLIC"])
        cls.pin = Path(os.environ["C3EO_FINGERPRINT"]).read_text().strip()
        cls.repo = ROOT
        assert cls.original_rpm.is_file() and cls.original_public.is_file()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="c3eo-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.rpm = self.home / "signed.rpm"
        self.pub = self.home / "public.asc"
        shutil.copy2(self.original_rpm, self.rpm)
        shutil.copy2(self.original_public, self.pub)
        self.rpm.chmod(0o600)
        self.pub.chmod(0o600)
        self.source = self.home / "source"
        self.source.mkdir(mode=0o700)
        for relative, _ in gate.EXPECTED.values():
            p = self.source / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.repo / relative, p)
        self.args = {
            "rpm_file": self.rpm,
            "public_key": self.pub,
            "pinned_fingerprint": self.pin,
            "source_root": self.source,
        }

    def verified(self, **changes):
        return gate.verify(**{**self.args, **changes})

    def refused(self, expected, **changes):
        with self.assertRaises(gate.Refused) as err:
            self.verified(**changes)
        self.assertEqual(str(err.exception), expected)

    def test_01_real_rpm_signature_and_exact_three_source_payloads(self):
        state = self.verified()
        self.assertEqual(state["schema"], gate.SCHEMA)
        self.assertEqual(state["rpm_sha256"],
                         hashlib.sha256(self.rpm.read_bytes()).hexdigest())
        self.assertTrue(state["package_signature_checked_ci"])
        self.assertTrue(state["host_script_is_python_not_native_elf"])
        self.assertEqual(set(state["payload_sha256"]), set(gate.EXPECTED))
        for path, (reference, mode) in gate.EXPECTED.items():
            self.assertEqual(state["payload_sha256"][path],
                             hashlib.sha256((self.source / reference).read_bytes()).hexdigest())
        for key in ("hostAuthenticated", "canApprove",
                    "credentialActionsEnabled", "productionAuthority",
                    "installedGuestMeasured"):
            self.assertIs(state[key], False)

    def test_02_wrong_independent_signer_pin_refused(self):
        self.refused("RPM_SIGNER_PIN_MISMATCH", pinned_fingerprint="F" * 40)

    def test_03_tampered_signed_package_refused(self):
        data = bytearray(self.rpm.read_bytes())
        data[-24] ^= 1
        self.rpm.write_bytes(data)
        self.refused("CI_TOOL_REFUSED")

    def test_04_bad_key_not_accepted_into_isolated_rpmdb(self):
        self.pub.write_text("not an OpenPGP public key\n")
        self.refused("CI_TOOL_REFUSED")

    def test_05_changed_host_script_cannot_match_signed_rpm_payload(self):
        path = self.source / gate.EXPECTED[
            "/usr/libexec/post-apollo/connections-status-host"][0]
        path.write_bytes(path.read_bytes().replace(
            b"C2O_CI_SERVICE_READY", b"C2O_CI_SERVICE_FORGED"))
        self.refused("RPM_PAYLOAD_SOURCE_MISMATCH")

    def test_06_changed_service_unit_cannot_match_signed_rpm_payload(self):
        path = self.source / gate.EXPECTED[
            "/usr/lib/systemd/system/postapollo-connections-status.service"][0]
        path.write_bytes(path.read_bytes().replace(
            b"Restart=no", b"Restart=always"))
        self.refused("RPM_PAYLOAD_SOURCE_MISMATCH")

    def test_07_changed_dbus_policy_cannot_match_signed_rpm_payload(self):
        path = self.source / gate.EXPECTED[
            "/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf"][0]
        path.write_bytes(path.read_bytes().replace(
            b"<deny own=", b"<allow own="))
        self.refused("RPM_PAYLOAD_SOURCE_MISMATCH")

    def test_08_symlink_source_is_not_trusted(self):
        expected = self.source / gate.EXPECTED[
            "/usr/libexec/post-apollo/connections-status-host"][0]
        real = expected.with_name("saved.script")
        expected.rename(real)
        expected.symlink_to(real)
        self.refused("RPM_PAYLOAD_MODE_OR_TYPE_REFUSED")

    def test_09_world_writable_source_is_not_trusted(self):
        expected = self.source / gate.EXPECTED[
            "/usr/libexec/post-apollo/connections-status-host"][0]
        expected.chmod(0o666)
        self.refused("RPM_PAYLOAD_MODE_OR_TYPE_REFUSED")

    def test_10_missing_source_cannot_be_silently_replaced(self):
        expected = self.source / gate.EXPECTED[
            "/usr/libexec/post-apollo/connections-status-host"][0]
        expected.unlink()
        self.refused("RPM_MEMBER_NOT_FOUND")

    def test_11_untrusted_package_path_is_refused(self):
        link = self.home / "signed-link.rpm"
        link.symlink_to(self.rpm)
        self.refused("SIGNED_INPUT_UNSAFE", rpm_file=link)

    def test_12_non_ci_run_never_trusts_source(self):
        old = os.environ["GITHUB_ACTIONS"]
        os.environ["GITHUB_ACTIONS"] = "false"
        try:
            self.refused("DISPOSABLE_CI_REQUIRED")
        finally:
            os.environ["GITHUB_ACTIONS"] = old

    def test_13_false_or_malformed_pins_are_rejected(self):
        for bad in ("", "f" * 40, "0" * 39, "0" * 64, None):
            with self.subTest(pin=bad):
                self.refused("INVALID_PIN", pinned_fingerprint=bad)

    def test_14_no_install_or_production_grant_path_in_source(self):
        data = SOURCE.read_text()
        self.assertNotIn('"--install"', data)
        self.assertNotIn('"--upgrade"', data)
        self.assertIn('"--dbpath"', data)
        self.assertNotIn("subprocess.Popen(", data)
        qml = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (qml / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (qml / "ConnectionsRequestStatus.qml").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
