"""M13 controlled vector-sidecar launch, no install, no shell, no background orphan."""
import contextlib
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services"/"company"))
import CompanyVectorSidecarLaunch as bridge


class SidecarLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.executable=self.home.joinpath(*bridge.RELATIVE_EXECUTABLE)

    def installed(self):
        self.executable.parent.mkdir(parents=True,exist_ok=True)
        self.executable.write_text("#!/bin/sh\nexit 0\n")
        self.executable.chmod(0o700)

    def verify_uid(self):
        # Test runner is expected to be a normal user. Root is explicitly
        # refused in production, and should not produce synthetic success.
        if os.geteuid()==0:
            self.skipTest("test requires non-root CI identity")

    def test_absent_binary_has_truthful_probe_and_no_side_effect(self):
        self.verify_uid()
        result=bridge.probe(self.home)
        self.assertEqual(result["status"],"NOT_INSTALLED")
        self.assertFalse(result["runtimeLaunched"])
        self.assertFalse(result["nativeQtVerified"])
        self.assertEqual(list(self.home.iterdir()),[])

    def test_exact_owner_executable_only(self):
        self.verify_uid()
        self.installed()
        self.assertEqual(bridge.trusted_executable(self.home),self.executable)
        self.executable.chmod(0o777)
        self.assertIsNone(bridge.trusted_executable(self.home))
        self.executable.chmod(0o700)
        self.executable.unlink()
        external=self.home/"fake-binary"
        external.write_text("#!/bin/sh\nexit 0\n")
        self.executable.symlink_to(external)
        self.assertIsNone(bridge.trusted_executable(self.home))

    def test_parent_dir_group_writable_denied(self):
        self.verify_uid()
        self.installed()
        self.executable.parent.chmod(0o777)
        self.assertIsNone(bridge.trusted_executable(self.home))

    def test_root_and_uid_mismatch_denied(self):
        self.installed()
        for uid,euid in ((0,0),(1000,0),(1001,1002)):
            with self.subTest(uid=uid,euid=euid),\
                 patch.object(bridge.os,"getuid",return_value=uid),\
                 patch.object(bridge.os,"geteuid",return_value=euid):
                self.assertIsNone(bridge.trusted_executable(self.home))

    def test_offline_and_online_are_explicit_and_only_supported_modes(self):
        self.verify_uid()
        self.installed()
        for action,expected in [
            ("offline",[]),("online",["--styled-online"])]:
            captured=[]
            def exec_mock(path,args):
                captured.append((path,args))
                raise OSError("testing exec")
            with self.subTest(action=action),\
                 patch.object(bridge.os,"execv",side_effect=exec_mock):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    code=bridge.main([action],home=self.home)
                self.assertEqual(code,70)
                self.assertEqual(captured,[(str(self.executable),
                                           [str(self.executable),*expected])])
                self.assertEqual(
                    __import__("json").loads(output.getvalue())["status"],
                    "LAUNCH_FAILED")
                self.assertNotIn("--owner-local-hubs",str(captured))
                self.assertNotIn("--mock-hub",str(captured))

    def test_missing_and_invalid_actions_cannot_start_anything(self):
        self.verify_uid()
        self.installed()
        for args in ([],["run"],["online","--owner-local-hubs"],
                     ["offline","--sample=FLINT"],["install"],["close"]):
            with self.subTest(args=args),\
                 patch.object(bridge.os,"execv",side_effect=AssertionError):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    code=bridge.main(args,home=self.home)
                self.assertEqual(code,2)
                self.assertIn("INVALID_ACTION",output.getvalue())

    def test_failed_install_does_not_launch(self):
        self.verify_uid()
        with patch.object(bridge.os,"execv",side_effect=AssertionError):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(bridge.main(["online"],home=self.home),69)
            self.assertIn("NOT_INSTALLED",output.getvalue())

    def test_qml_control_has_separate_consent_close_and_fallback(self):
        qml=(ROOT/"widgets"/"CompanyCoveragePane.qml").read_text()
        self.assertIn("VECTOR VIEW ▸",qml)
        self.assertIn("CLOSE VECTOR",qml)
        self.assertIn("OFFLINE TEST",qml)
        self.assertIn("ONLINE STREETS",qml)
        self.assertIn("vectorConsentOpen",qml)
        self.assertIn("vectorRunner.running=false",qml)
        self.assertIn('Quickshell.shellPath("services/company/CompanyVectorSidecarLaunch.py")',qml)
        self.assertIn('online ? "online" : "offline"',qml)
        self.assertIn("OpenFreeMap",qml)
        self.assertIn("No Company hub, worker, or client data",qml)
        self.assertIn("CompanyStreetMap {",qml)
        self.assertIn("Canvas {",qml)
        self.assertNotIn("startDetached()",qml)
        self.assertNotIn("owner-local-hubs",qml)
        self.assertNotIn("quickshell --restart",qml)

if __name__=="__main__":
    unittest.main()
