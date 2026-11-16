"""P51 POSIX parser/unit-origin denial tests, no actual host privilege.

The separate P51 GitHub workflow also starts a genuine isolated systemd
service under a dedicated UID; these pure tests enforce data/permission
denial even on fabricated process data or missing service.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalSystemdOriginP51 as Origin


class CandidateTests(unittest.TestCase):
    def test_all_source_success_claims_remain_denied(self):
        for result in (Origin.OBSERVED, Origin.REFUSED):
            for key in (
                "installedHostVerified",
                "signedReleaseIndependentlyEnrolled",
                "selinuxEnforcingVerified", "logindSeatVerified",
                "c3eChallengeConsumed", "c5HumanConsentVerified",
                "keyReleaseAuthorized", "personalSaveAuthorized",
            ):
                self.assertIs(result[key], False)
            self.assertNotIn("pid", str(result).lower())
            self.assertNotIn("profile", str(result).lower())
            self.assertNotIn("contact", str(result).lower())
            self.assertNotIn("note", str(result).lower())

    def test_noninstalled_development_environment_denies(self):
        # The CI root integration test is the only place where we stage
        # an actual unit. Ordinary source checkout is never authenticated.
        with patch.object(Origin, "_source_present", side_effect=OSError("private")):
            self.assertEqual(Origin.observe_installed_status_candidate(),
                             Origin.REFUSED)

    def test_proc_stat_parser_uses_kernel_start_ticks_not_proc_comm(self):
        data = (Path("/proc") / str(os.getpid()) / "stat").read_bytes()
        self.assertGreater(Origin._start_ticks(data, os.getpid()), 0)
        unusual_comm = data.replace(b" (", b" (a b) c (d) ", 1)
        self.assertGreater(Origin._start_ticks(unusual_comm, os.getpid()), 0)
        for malformed in (
            b"1 (bad) S",
            b"bad",
            b"0 (zero) S",
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    Origin._start_ticks(malformed, os.getpid())

    def test_invalid_unit_fields_and_replay_view_refuse(self):
        expected = {
            "MainPID": "222", "User": Origin.USER,
            "Group": Origin.USER,
            "ControlGroup": "/system.slice/" + Origin.UNIT,
            "FragmentPath": str(Origin.UNIT_PATH),
            "LoadState": "loaded", "ActiveState": "active",
            "SubState": "running",
        }
        for field, bad in (
            ("MainPID", "abc"), ("MainPID", "1"),
            ("User", "root"), ("Group", "root"),
            ("ControlGroup", "/user.slice/other.service"),
            ("FragmentPath", "/tmp/forged.service"),
            ("ActiveState", "inactive"), ("SubState", "dead"),
        ):
            with self.subTest(field=field):
                snapshot = dict(expected)
                snapshot[field] = bad
                with patch.object(Origin, "_source_present"), \
                     patch.object(Origin, "_systemd_show", return_value=snapshot), \
                     patch.object(Origin, "_kernel_process") as proc:
                    self.assertEqual(
                        Origin.observe_installed_status_candidate(),
                        Origin.REFUSED,
                    )
                    proc.assert_not_called()

    def test_actual_unit_reader_rejects_duplicate_fields_and_bad_exit(self):
        base = {
            "MainPID": "1", "User": "foo",
            "Group": "foo", "FragmentPath": "/run/unit",
            "ControlGroup": "/system.slice/foo",
            "ActiveState": "active", "SubState": "running",
            "LoadState": "loaded",
        }
        lines = "\n".join(k + "=" + v for k, v in base.items()).encode()
        for raw, code in (
            (lines + b"\nMainPID=999\n", 0),
            (lines + b"\nEvilToken=1\n", 0),
            (lines, 1),
            (b"X" * 9000, 0),
        ):
            with patch.object(Origin.subprocess, "run", return_value=SimpleNamespace(
                returncode=code, stdout=raw,
            )):
                with self.assertRaises(ValueError):
                    Origin._systemd_show()

    def test_kernel_credential_nonzero_capabilities_and_no_new_privs_refuse(self):
        pid = os.getpid()
        uid, gid = os.geteuid(), os.getegid()
        valid = (
            f"Uid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
            f"Gid:\t{gid}\t{gid}\t{gid}\t{gid}\n"
            "CapEff:\t0000000000000000\nNoNewPrivs:\t1\n"
        ).encode()
        Origin._proc_credentials(valid, uid, gid)
        for case in (
            valid.replace(b"NoNewPrivs:\t1", b"NoNewPrivs:\t0"),
            valid.replace(b"0000000000000000", b"0000000000000001"),
            valid.replace(b"Uid:\t", b"Uid:\t999999\t", 1),
            valid + b"Uid:\t0\t0\t0\t0\n",
        ):
            with self.subTest(case=case[-50:]):
                with self.assertRaises(ValueError):
                    Origin._proc_credentials(case, uid, gid)

    def test_root_source_observer_no_production_keys_and_host_writes(self):
        code = (ROOT / "services/phone/PhonePersonalSystemdOriginP51.py").read_text()
        for required in (
            '"/usr/bin/systemctl"', '"MainPID"', '"ControlGroup"',
            '"/proc"', '"O_NOFOLLOW"', 'pwd.getpwnam',
            '"NoNewPrivs"', '"CapEff"', "systemdCandidateObserved",
        ):
            self.assertIn(required, code)
        for forbidden in (
            "PhonePersonalKeyProvision", "PhonePersonalContactVault",
            "PhonePersonalProtectedKey", "PhonePersonalSaveOrchestrator",
            "import dbus", "secret-tool", "Vault.commit(",
            "os.system(", "Popen(", "shell=True", "print(",
        ):
            self.assertNotIn(forbidden, code)

if __name__ == "__main__":
    unittest.main()
