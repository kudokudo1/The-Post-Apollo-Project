"""DOC 5: Real filesystem/UID attack evidence against CI-only C5 spend store.

An intentional PASS for rollback-and-respend is an observed *vulnerability of
the unprotected fixture*, never evidence that native consent is safe.
Do not import this module into a runtime, service, or command adapter.
"""
from __future__ import annotations

import os
import pwd
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5SpendFenceReference import (  # noqa: E402
    ACTION, AUDIENCE, ReferenceRefused, TestOnlyC5Fence,
)


def fixture_grant():
    return {
        "audience": AUDIENCE,
        "action": ACTION,
        "grant_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "selection_sha256": "a" * 64,
        "intent_sha256": "b" * 64,
        "source_sha256": "c" * 64,
        "session_id": str(uuid.uuid4()),
        "seat_id": "seat0",
        "issuer_epoch": str(uuid.uuid4()),
        "issued_ms": 1000,
        "expires_ms": 1500,
    }


def assert_denied_authority(test, result):
    for flag in (
        "production_authorized", "native_action_allowed",
        "production_revocation_ack", "retry_allowed", "undo_allowed",
    ):
        test.assertIs(result[flag], False)
    test.assertEqual(result["safe_actions"], [])


class CustodyAttacks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="timew-c5-custody-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "fixture-c5.db"
        self.fence = TestOnlyC5Fence(self.path)
        self.fence.initialize_fixture()
        self.grant = fixture_grant()
        assert_denied_authority(self, self.fence.register_fixture(self.grant))

    def test_same_uid_whole_db_rollback_enables_fixture_respend(self):
        # Explicit counterexample: local SQLite FULL-sync + BEGIN IMMEDIATE is
        # not a replacement-resistant, independent one-use consent keeper.
        pre_spend_db = self.path.read_bytes()
        first = self.fence.spend_fixture(self.grant, now_ms=1100)
        assert_denied_authority(self, first)
        self.assertEqual(self.fence.inspect_fixture(self.grant["grant_id"])[
            "fixture_state"], "SPENT_UNKNOWN_HOLD")

        self.path.write_bytes(pre_spend_db)  # Same-UID rollback in disposable tmp.
        self.assertEqual(self.fence.inspect_fixture(self.grant["grant_id"])[
            "fixture_state"], "ACTIVE_UNTRUSTED_FIXTURE")
        second = self.fence.spend_fixture(self.grant, now_ms=1101)
        self.assertEqual(second["fixture_state"], "SPENT_UNKNOWN_HOLD")
        assert_denied_authority(self, second)
        # The second synthetic spend must NOT be mistaken for native permission.
        # Actual protected C5 must reject this rollback before any side effect.

    def test_same_uid_delete_and_recreate_enables_fixture_respend(self):
        first = self.fence.spend_fixture(self.grant, now_ms=1100)
        assert_denied_authority(self, first)
        self.path.unlink()  # Same-UID replacement under disposable test directory.
        with self.assertRaises(ReferenceRefused):
            self.fence.spend_fixture(self.grant, now_ms=1101)
        self.fence.initialize_fixture()  # Test-only constructor, not runtime API.
        assert_denied_authority(self, self.fence.register_fixture(self.grant))
        second = self.fence.spend_fixture(self.grant, now_ms=1101)
        assert_denied_authority(self, second)
        self.assertEqual(second["fixture_state"], "SPENT_UNKNOWN_HOLD")

    def test_corrupt_store_refuses_instead_of_issuing(self):
        self.path.write_bytes(b"not-an-sqlite-database")
        with self.assertRaises(ReferenceRefused):
            self.fence.spend_fixture(self.grant, now_ms=1100)
        with self.assertRaises(ReferenceRefused):
            self.fence.inspect_fixture(self.grant["grant_id"])

    @unittest.skipUnless(hasattr(os, "fork") and hasattr(os, "setuid"),
                         "Linux fork/setuid test")
    def test_distinct_unprivileged_uid_cannot_replace_root_private_fixture(self):
        # Run once with ordinary runner UID (SKIP) and once with sudo root
        # (real distinct-UID negative test). Still NOT protected native consent.
        if os.geteuid() != 0:
            self.skipTest("requires disposable CI root for cross-UID negative test")
        nobody = pwd.getpwnam("nobody")
        self.assertNotEqual(nobody.pw_uid, 0)
        os.chmod(self.path.parent, 0o700)
        os.chmod(self.path, 0o600)
        rfd, wfd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(rfd)
            try:
                os.setgroups([])
                os.setgid(nobody.pw_gid)
                os.setuid(nobody.pw_uid)

                def is_denied(attempt):
                    try:
                        attempt()
                    except (OSError, ReferenceRefused):
                        return "DENIED"
                    return "ALLOWED"

                def replace_db():
                    replacement = self.path.with_suffix(".replacement")
                    replacement.write_bytes(b"false-unspent")
                    os.replace(replacement, self.path)

                attempts = [
                    is_denied(replace_db),
                    is_denied(lambda: self.path.unlink()),
                    is_denied(lambda: self.fence.spend_fixture(
                        self.grant, now_ms=1100)),
                ]
                report = f"{os.geteuid()}:{','.join(attempts)}".encode("ascii")
                os.write(wfd, report)
            except BaseException as exc:
                os.write(wfd, f"ERROR:{type(exc).__name__}".encode("ascii"))
            finally:
                os.close(wfd)
                os._exit(0)
        os.close(wfd)
        try:
            report = os.read(rfd, 512).decode("ascii")
        finally:
            os.close(rfd)
        _, status = os.waitpid(pid, 0)
        self.assertTrue(os.WIFEXITED(status))
        self.assertEqual(os.WEXITSTATUS(status), 0)
        self.assertEqual(
            report, f"{nobody.pw_uid}:DENIED,DENIED,DENIED",
            "A different real Linux UID must not mutate a root-private CI file",
        )
        # Root-private file protection is a necessary *candidate boundary*, not
        # root enrolment, operator consent, rollback-resistant history or issuer.
        self.assertEqual(self.fence.inspect_fixture(self.grant["grant_id"])[
            "fixture_state"], "ACTIVE_UNTRUSTED_FIXTURE")
        assert_denied_authority(self, self.fence.spend_fixture(
            self.grant, now_ms=1100))


if __name__ == "__main__":
    unittest.main()
