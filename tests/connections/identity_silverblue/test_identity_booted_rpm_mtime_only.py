#!/usr/bin/env python3
"""Adversarial check of real Silverblue RPM timestamp-only variance parser."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("id_c4b_booted_rpm", HERE / "verify_booted_rpm_mtime_only.py")
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
paths = sorted(M.FILES)


def t(path: str) -> str:
    return f".......T.    {path}\n"


class BootedRpmVerifierTests(unittest.TestCase):
    def refused(self, output, rc, reason):
        with self.assertRaises(M.Refused) as raised:
            M.verify_mtime_only(output, rc)
        self.assertEqual(str(raised.exception), reason)

    def test_01_full_signed_roster_mtime_only_is_accepted(self):
        self.assertEqual(M.verify_mtime_only("".join(t(p) for p in paths), 1), 9)

    def test_02_subset_mtime_only_and_no_difference(self):
        self.assertEqual(M.verify_mtime_only(t(paths[0]), 1), 1)
        self.assertEqual(M.verify_mtime_only("", 0), 0)

    def test_03_non_timestamp_integrity_changes_refuse(self):
        for flags in ("S......T.", "..5....T.", "..M....T.", ".....U.T.",
                      "......G T.", ".......T5", ".......T?", "missing   "):
            with self.subTest(flags=flags):
                self.refused(f"{flags}    {paths[0]}\n", 1,
                             "RPM_FILE_DIFFERENCE_NOT_TIMESTAMP_ONLY")

    def test_04_unsigned_other_path_refused(self):
        self.refused(t("/usr/libexec/post-apollo/identity/rogue.py"), 1,
                     "RPM_FILE_OUTSIDE_SIGNED_ROSTER")
        self.refused(t("/etc/passwd"), 1, "RPM_FILE_OUTSIDE_SIGNED_ROSTER")

    def test_05_duplicate_or_mixed_records_refused(self):
        self.refused(t(paths[0]) * 2, 1,
                     "RPM_FILE_DUPLICATE_VERIFICATION_RECORD")
        self.refused(t(paths[0]) + "warning: untrusted package\n", 1,
                     "RPM_FILE_DIFFERENCE_NOT_TIMESTAMP_ONLY")

    def test_06_unexplained_rc_or_unexpected_output_refused(self):
        self.refused("", 1, "UNEXPLAINED_RPM_VERIFIER_FAILURE")
        self.refused(t(paths[0]), 0, "RPM_VERIFIER_RETURN_CODE_REFUSED")
        self.refused(t(paths[0]), 2, "RPM_VERIFIER_RETURN_CODE_REFUSED")
        self.refused(t(paths[0]), 124, "RPM_VERIFIER_RETURN_CODE_REFUSED")

    def test_07_malformed_inputs_and_budget_refused(self):
        self.refused("x" * 5000, 1, "OVERSIZE_RPM_VERIFIER_EVIDENCE")
        self.refused(t(paths[0]), True, "INVALID_RPM_VERIFIER_EVIDENCE")
        self.refused(42, 1, "INVALID_RPM_VERIFIER_EVIDENCE")

    def test_08_guest_stages_helper_without_weakening_verification(self):
        guest = (HERE / "guest_identity_ostree_cycle.sh").read_text()
        host = (HERE / "run_official_silverblue_identity.sh").read_text()
        assert "rpm -V " in guest
        self.assertIn('rpm -V "$pkg" >"$verify_file" 2>&1', guest)
        self.assertIn('rpm -V --nomtime "$pkg" >"$nomtime_file" 2>&1', guest)
        self.assertIn('python3 -I -B "$helper" "$verify_file" "$verify_rc"', guest)
        self.assertIn('SIGNED_IDENTITY_BOOTED_RPM_NON_TIMESTAMP_DISCREPANCY', guest)
        self.assertIn('[[ "$observed" =~ ^0:0:555:[1-9][0-9]*$ ]]', guest)
        self.assertIn('rpm-ostree rollback --reboot', guest)
        self.assertIn('verify_booted_rpm_mtime_only.py', host)
        self.assertIn('chmod 0444 /usr/local/libexec/postapollo-id-ci-verify-rpm.py', host)
        self.assertNotIn('rpm -V --nodeps', guest)
        self.assertNotIn('rpm -V --nofiledigest', guest)
        self.assertNotIn('rpm -V --nomode', guest)
        self.assertNotIn('rpm -V --nouser', guest)
        self.assertNotIn('rpm -V --nogroup', guest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
