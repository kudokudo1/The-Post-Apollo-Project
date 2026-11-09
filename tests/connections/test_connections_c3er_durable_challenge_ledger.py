#!/usr/bin/env python3
"""C3e-R: real CI SQLite durable replay tests around C3e-Q signatures.

Only disposable GitHub Linux root CI; never run on an operator workstation.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load(HERE / "C3eRDurableChallengeLedger.py", "c3er_ledger")
QTEST = load(ROOT / "tests/connections/test_connections_c3eq_signed_guest_evidence.py",
             "c3er_q_fixture")


class C3eRDurableReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true"):
            raise RuntimeError("C3ER_DISPOSABLE_ROOT_GITHUB_CI_REQUIRED")
        QTEST.C3eQSignedEvidenceTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        QTEST.C3eQSignedEvidenceTests.tearDownClass()

    def setUp(self):
        self.fixture = QTEST.C3eQSignedEvidenceTests(
            "test_01_actual_detached_signed_test_report_and_one_use_receipt")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = Path(tempfile.mkdtemp(prefix="c3er-ci-", dir="/run"))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.work.chmod(0o700)
        R.initialize_for_disposable_ci(self.work)
        self.ledger = R.DurableTestVerifier(self.work)
        self.challenge = self.ledger.issue()
        self.fixture.data["challenge_sha256"] = hashlib.sha256(
            self.challenge).hexdigest()
        self.fixture._sign()

    def arguments(self):
        f = self.fixture
        return dict(
            evidence=f.report, signature=f.sig,
            public_key=f.pub, pinned_signer=f.fpr,
            expected_rpm_sha256=f.rpm,
            expected_script_sha256=f.script,
            expected_interpreter_sha256=f.interpreter,
            expected_service_pid=4881,
            expected_start_ticks="991337")

    def consume(self, ledger=None, challenge=None, **changes):
        args = {**self.arguments(), **changes}
        return (ledger or self.ledger).consume(
            self.challenge if challenge is None else challenge, **args)

    def refuse(self, code, ledger=None, challenge=None, **changes):
        with self.assertRaises(R.Refused) as err:
            self.consume(ledger=ledger, challenge=challenge, **changes)
        self.assertEqual(str(err.exception), code)

    def test_01_real_signature_consumed_and_record_committed(self):
        result = self.consume()
        self.assertTrue(result["challengeConsumedDurablyInCI"])
        self.assertFalse(result["hostAuthenticated"])
        self.assertFalse(result["credentialActionsEnabled"])
        db = R.connect(self.work)
        try:
            stored = db.execute(
                "SELECT state,signed_evidence_sha256 FROM challenges WHERE digest=?",
                (hashlib.sha256(self.challenge).hexdigest(),)
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(stored[0], "consumed")
        self.assertEqual(stored[1], hashlib.sha256(
            self.fixture.report.read_bytes()).hexdigest())

    def test_01a_changed_evidence_after_signature_check_records_only_verified_bytes(self):
        # Adversarial window: a trusted test hook replaces the caller-owned
        # pathname AFTER Q has verified and parsed the original snapshot,
        # but BEFORE R persists its ledger digest. R must never hash that
        # substituted data or claim it was signature-verified.
        original_bytes = self.fixture.report.read_bytes()
        expected_digest = hashlib.sha256(original_bytes).hexdigest()
        replacement = b"not the original signed evidence"
        self.assertNotEqual(hashlib.sha256(replacement).hexdigest(),
                            expected_digest)
        verify = R.Q.OneUseTestChallenge.verify
        fixture = self.fixture

        def substitute_after_verified(challenge, *args, **kwargs):
            receipt = verify(challenge, *args, **kwargs)
            self.assertEqual(receipt["verifiedEvidenceSHA256"],
                             expected_digest)
            fixture.report.write_bytes(replacement)
            return receipt

        with mock.patch.object(R.Q.OneUseTestChallenge, "verify",
                               substitute_after_verified):
            result = self.consume()
        self.assertTrue(result["challengeConsumedDurablyInCI"])
        db = R.connect(self.work)
        try:
            saved = db.execute(
                "SELECT signed_evidence_sha256 FROM challenges WHERE digest=?",
                (hashlib.sha256(self.challenge).hexdigest(),)
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(saved, (expected_digest,))
        self.assertNotEqual(saved[0],
                            hashlib.sha256(self.fixture.report.read_bytes()).hexdigest())
        self.refuse("CHALLENGE_ALREADY_CONSUMED_DURABLY")

    def test_02_replay_refused_by_fresh_verifier_instance(self):
        self.consume()
        next_process_state = R.DurableTestVerifier(self.work)
        self.refuse("CHALLENGE_ALREADY_CONSUMED_DURABLY",
                    ledger=next_process_state)

    def test_03_real_separate_process_cannot_replay_consumed_challenge(self):
        self.consume()
        code = (
            "import sys; sys.path.insert(0,sys.argv[1]); "
            "import C3eRDurableChallengeLedger as R; "
            "r=R.DurableTestVerifier(sys.argv[2]); "
            "args=dict(evidence=sys.argv[3], signature=sys.argv[4], "
            "public_key=sys.argv[5], pinned_signer=sys.argv[6], "
            "expected_rpm_sha256=sys.argv[7], "
            "expected_script_sha256=sys.argv[8], "
            "expected_interpreter_sha256=sys.argv[9], "
            "expected_service_pid=4881, expected_start_ticks='991337')\n"
            "try:\n r.consume(bytes.fromhex(sys.argv[10]), **args)\n"
            "except R.Refused as e:\n print(str(e)); sys.exit(3)\n"
            "sys.exit(0)"
        )
        f = self.fixture
        completed = subprocess.run(
            [sys.executable, "-B", "-c", code, str(HERE),
             str(self.work), str(f.report), str(f.sig), str(f.pub), f.fpr,
             f.rpm, f.script, f.interpreter, self.challenge.hex()],
            capture_output=True, text=True, timeout=12)
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertIn("CHALLENGE_ALREADY_CONSUMED_DURABLY",
                      completed.stdout)

    def test_04_unknown_not_issued_challenge_refused(self):
        self.refuse("CHALLENGE_NOT_ISSUED", challenge=b"Z" * 32)

    def test_05_missing_ledger_refused_without_silent_bootstrap(self):
        (self.work / R.DB_FILE).unlink()
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception),
                         "LEDGER_MISSING_REFUSE_NOT_BOOTSTRAP")

    def test_06_symlink_ledger_refused(self):
        path = self.work / R.DB_FILE
        real = self.work / "real.sqlite"
        path.rename(real)
        path.symlink_to(real)
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception), "LEDGER_FILE_UNSAFE")

    def test_07_world_readable_ledger_refused(self):
        (self.work / R.DB_FILE).chmod(0o644)
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception), "LEDGER_FILE_UNSAFE")

    def test_08_group_writable_ledger_parent_refused(self):
        self.work.chmod(0o770)
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception), "LEDGER_DIRECTORY_UNSAFE")

    def test_09_corrupt_database_refused(self):
        path = self.work / R.DB_FILE
        path.write_bytes(b"incorrect sqlite data from restore")
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception), "LEDGER_UNAVAILABLE_OR_CORRUPT")

    def test_10_wrong_signed_attestation_preserves_unused_challenge(self):
        self.fixture.data["service_pid"] = 100
        self.fixture.report.write_text(json.dumps(self.fixture.data))
        self.refuse("SIGNED_Q_EVIDENCE_REFUSED:SIGNED_EVIDENCE_CRYPTO_REFUSED")
        db = R.connect(self.work)
        try:
            result = db.execute(
                "SELECT state FROM challenges WHERE digest=?",
                (hashlib.sha256(self.challenge).hexdigest(),)).fetchone()
        finally:
            db.close()
        self.assertEqual(result, ("issued",))
        self.fixture.data["service_pid"] = 4881
        self.fixture._sign()
        self.assertTrue(self.consume()["challengeConsumedDurablyInCI"])

    def test_11_other_test_signer_does_not_consume(self):
        self.fixture._sign(signer=self.fixture.bad_home)
        self.refuse("SIGNED_Q_EVIDENCE_REFUSED:SIGNED_EVIDENCE_CRYPTO_REFUSED")

    def test_12_mismatched_independent_package_does_not_consume(self):
        self.refuse(
            "SIGNED_Q_EVIDENCE_REFUSED:SIGNED_ARTIFACT_OR_INTERPRETER_PIN_MISMATCH",
            expected_rpm_sha256="c" * 64)
        self.assertTrue(self.consume()["challengeConsumedDurablyInCI"])

    def test_13_mismatched_challenge_report_does_not_consume(self):
        self.fixture.data["challenge_sha256"] = "f" * 64
        self.fixture._sign()
        self.refuse(
            "SIGNED_Q_EVIDENCE_REFUSED:CHALLENGE_NOT_BOUND_TO_SIGNED_EVIDENCE")

    def test_14_double_consumption_concurrent_workers_only_one_wins(self):
        def attempt(_):
            try:
                return self.consume(ledger=R.DurableTestVerifier(self.work))
            except R.Refused as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(isinstance(x, dict) for x in results), 1)
        self.assertIn("CHALLENGE_ALREADY_CONSUMED_DURABLY", results)

    def test_15_two_distinct_challenges_consumed_once_each(self):
        second = self.ledger.issue()
        self.assertNotEqual(second, self.challenge)
        self.consume()
        self.fixture.data["challenge_sha256"] = hashlib.sha256(
            second).hexdigest()
        self.fixture._sign()
        self.assertTrue(self.consume(challenge=second)["challengeConsumedDurablyInCI"])
        self.refuse("CHALLENGE_ALREADY_CONSUMED_DURABLY",
                    challenge=second)

    def test_16_existing_ledger_cannot_be_reinitialized(self):
        with self.assertRaises(R.Refused) as err:
            R.initialize_for_disposable_ci(self.work)
        self.assertEqual(str(err.exception), "LEDGER_ALREADY_EXISTS")

    def test_17_missing_or_inconsistent_schema_refuses(self):
        db = sqlite3.connect(self.work / R.DB_FILE)
        try:
            db.execute("DELETE FROM ledger_meta")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception), "LEDGER_SCHEMA_OR_ROOT_MISMATCH")

    def test_18_unexpected_wal_state_refuses(self):
        (self.work / (R.DB_FILE + "-wal")).write_bytes(b"unexpected")
        with self.assertRaises(R.Refused) as err:
            R.DurableTestVerifier(self.work)
        self.assertEqual(str(err.exception), "UNEXPECTED_WAL_FILE")

    def test_19_wrong_scope_or_unprivileged_config_refused(self):
        with self.assertRaises(R.Refused):
            R.DurableTestVerifier("/tmp/c3er-ci-forbidden")
        old = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "false"
        try:
            with self.assertRaises(R.Refused):
                R.DurableTestVerifier(self.work)
        finally:
            if old is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = old

    def test_20_always_denies_real_credential_service(self):
        result = self.consume()
        for field in ("installedGuestMeasured", "hostAuthenticated",
                      "canApprove", "credentialActionsEnabled",
                      "productionAuthority", "signedGuestOriginAuthenticated"):
            self.assertIs(result[field], False)
        services = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (services / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (services / "ConnectionsRequestStatus.qml").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
