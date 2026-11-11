#!/usr/bin/env python3
"""C3e-W: root-owned, disposable CI ledger only; no live host or credentials."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


W = _load("c3ew_pair_ledger", HERE / "C3eWDurablePairConsumption.py")
VTEST = _load("c3ew_vfixtures", ROOT /
              "tests/connections/test_connections_c3ev_signed_guest_diagnostic_pair.py")
FLAGS = (
    "externalIssuerCustodyVerified", "externalRollbackResistanceVerified",
    "signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
    "installedGuestMeasured", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
)


class C3eWDurablePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true"):
            raise RuntimeError("C3EW_DISPOSABLE_ROOT_GITHUB_CI_ONLY")
        VTEST.C3eVSignedPairTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        VTEST.C3eVSignedPairTests.tearDownClass()

    def setUp(self):
        self.pair = VTEST.C3eVSignedPairTests(
            "test_01_real_disposable_signed_and_plain_report_pair_never_grants")
        self.pair.setUp()
        self.addCleanup(self.pair.doCleanups)
        self.dir = Path(tempfile.mkdtemp(prefix="c3er-ci-", dir="/run"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.dir.chmod(0o700)
        W.R.initialize_for_disposable_ci(self.dir)
        self.ledger = W.R.DurableTestVerifier(self.dir)
        self.challenge = self.ledger.issue()
        self._sign_for(self.challenge)

    def _sign_for(self, challenge):
        self.pair.fixture.data["challenge_sha256"] = hashlib.sha256(
            challenge).hexdigest()
        self.pair.fixture._sign()

    def args(self):
        return {**self.pair.arguments(), "ledger_root": self.dir,
                "challenge": self.challenge}

    def verify(self, **changes):
        return W.inspect_and_consume(**{**self.args(), **changes})

    def refuse(self, expected, **changes):
        with self.assertRaises(W.Refused) as caught:
            self.verify(**changes)
        self.assertEqual(str(caught.exception), expected)

    def state(self, challenge=None):
        token = self.challenge if challenge is None else challenge
        db = W.R.connect(self.dir)
        try:
            return db.execute(
                "SELECT state,signed_evidence_sha256 FROM challenges WHERE digest=?",
                (hashlib.sha256(token).hexdigest(),)).fetchone()
        finally:
            db.close()

    def test_01_verified_pair_consumes_once_in_root_ledger_without_grant(self):
        before = hashlib.sha256(self.pair.fixture.report.read_bytes()).hexdigest()
        reply = self.verify()
        self.assertEqual(reply["schema"], W.SCHEMA)
        self.assertTrue(reply["signedAndDiagnosticPairMatchedInCI"])
        self.assertTrue(reply["challengeConsumedDurablyInCI"])
        self.assertEqual(self.state(), ("consumed", before))
        for k in FLAGS:
            self.assertIs(reply[k], False)

    def test_02_separate_verifier_instance_cannot_replay_consumed_nonce(self):
        self.verify()
        self.ledger = W.R.DurableTestVerifier(self.dir)
        self.refuse("C3ER_DURABLE_REFUSED:CHALLENGE_ALREADY_CONSUMED_DURABLY")

    def test_03_signed_uid_mismatch_preserves_issued_nonce_then_good_retry(self):
        self.pair.fixture.data["service_uid"] = 998
        self._sign_for(self.challenge)
        self.refuse("C3EV_PAIR_REFUSED:SIGNED_CLAIM_AND_GUEST_REPORT_DISAGREE")
        self.assertEqual(self.state(), ("issued", None))
        self.pair.fixture.data["service_uid"] = 997
        self._sign_for(self.challenge)
        self.assertTrue(self.verify()["challengeConsumedDurablyInCI"])

    def test_04_wrong_signer_does_not_consume_challenge(self):
        self.pair.fixture._sign(signer=self.pair.fixture.bad_home)
        self.refuse("C3EV_PAIR_REFUSED:C3EQ_SIGNED_CLAIM_REFUSED:"
                    "SIGNED_EVIDENCE_CRYPTO_REFUSED")
        self.assertEqual(self.state(), ("issued", None))

    def test_05_false_guest_authority_cannot_consume_challenge(self):
        self.pair.guest["productionAuthority"] = True
        self.refuse("C3EV_PAIR_REFUSED:C4D_DIAGNOSTIC_REFUSED:"
                    "C4C_CLAIMED_UNAUTHORIZED_AUTHORITY")
        self.assertEqual(self.state(), ("issued", None))

    def test_06_not_issued_challenge_denied_after_matching_signature(self):
        outside = b"Z" * 32
        self._sign_for(outside)
        self.refuse("C3ER_DURABLE_REFUSED:CHALLENGE_NOT_ISSUED",
                    challenge=outside)
        self.assertIsNone(self.state(outside))
        self.assertEqual(self.state(), ("issued", None))

    def test_07_missing_or_corrupt_ledger_refuses_without_bootstrap(self):
        (self.dir / W.R.DB_FILE).unlink()
        self.refuse("DURABLE_CI_LEDGER_UNAVAILABLE")
        self.assertFalse((self.dir / W.R.DB_FILE).exists())

    def test_08_source_path_replaced_after_snapshot_cannot_change_signed_bytes(self):
        original = self.pair.fixture.report.read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        save = W._snapshot
        src = self.pair.fixture.report

        def replace_after_first_snapshot(path, dst, ceiling, code):
            saved = save(path, dst, ceiling, code)
            if dst.name == "evidence.json":
                src.write_bytes(b"untrusted replacement after root copy")
            return saved

        with mock.patch.object(W, "_snapshot", replace_after_first_snapshot):
            reply = self.verify()
        self.assertTrue(reply["challengeConsumedDurablyInCI"])
        self.assertEqual(self.state(), ("consumed", digest))
        self.assertNotEqual(hashlib.sha256(src.read_bytes()).hexdigest(), digest)

    def test_09_concurrent_duplicate_commit_allows_exactly_one(self):
        def attempt(_):
            try:
                return self.verify()
            except W.Refused as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(isinstance(x, dict) for x in results), 1)
        self.assertIn("C3ER_DURABLE_REFUSED:"
                      "CHALLENGE_ALREADY_CONSUMED_DURABLY", results)
        self.assertEqual(self.state()[0], "consumed")

    def test_10_missing_or_invalid_independent_pin_refuses_and_preserves_issued(self):
        self.refuse("C3EV_PAIR_REFUSED:C4D_DIAGNOSTIC_REFUSED:"
                    "INDEPENDENT_HASH_PIN_INVALID",
                    expected_interpreter_sha256="")
        self.assertEqual(self.state(), ("issued", None))

    def test_11_identity_gateway_role_cannot_use_fake_connections_contract(self):
        self.pair.guest["systemd_unit"] = "post-apollo-identity-silverblue-ci.service"
        self.refuse("C3EV_PAIR_REFUSED:C4D_DIAGNOSTIC_REFUSED:"
                    "C4C_ROLE_OR_SELINUX_REFUSED")
        self.assertEqual(self.state(), ("issued", None))

    def test_12_no_live_ui_install_or_credential_path(self):
        source = (HERE / "C3eWDurablePairConsumption.py").read_text()
        for forbidden in ("ConnectionsBroker.qml", "SignedIdentityCommandClient",
                          "InstalledIdentityCommandAdapterV1", "socket.socket(",
                          "subprocess.run(", "systemctl ", "rpm-ostree "):
            self.assertNotIn(forbidden, source)
        for k in FLAGS:
            self.assertIn('"' + k + '": False', source)
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      broker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
