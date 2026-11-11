#!/usr/bin/env python3
"""C3e-Y signed full CI host-record, distinct witness key and durable replay tests."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Y = _load("c3ey_receiver", HERE / "C3eYSignedHostChallenge.py")
XTEST = _load("c3ey_c3ex_fixtures", ROOT /
              "tests/connections/test_connections_c3ex_identity_running_evidence.py")


class C3eYSignedHostChallengeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("C3EY_DISPOSABLE_ROOT_GITHUB_CI_ONLY")

    def setUp(self):
        self.pair = XTEST.C3eXRunningIdentityDenialTests(
            "test_01_four_real_ed25519_denials_and_snapshots_only_return_ci_flags")
        self.pair.setUp()
        self.witness_key = Ed25519PrivateKey.generate()
        self.epoch, self.sequence = 7, 12
        self.root = Path(tempfile.mkdtemp(prefix=Y.DIR_PREFIX, dir="/run"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.root.chmod(0o700)
        Y.initialize_for_disposable_ci(self.root)
        self.issuer = Y.DisposableCIChallengeIssuer(self.root)
        self.challenge = self.issuer.issue(release_epoch=self.epoch, release_sequence=self.sequence)
        self._sign()

    def _evidence(self):
        return self.pair.encode()

    def _sign(self):
        receipt_key = self.pair.key.public_key()
        pub = Y._public_bytes(receipt_key)
        self.document = {
            "schema": Y.SCHEMA, "role": Y.ROLE,
            "purpose": Y.PURPOSE, "audience": Y.AUDIENCE,
            "releaseEpoch": self.epoch, "releaseSequence": self.sequence,
            "challengeSha256": hashlib.sha256(self.challenge).hexdigest(),
            "evidenceSha256": hashlib.sha256(self._evidence()).hexdigest(),
            "receiptSha256": [hashlib.sha256(f).hexdigest() for f in self.pair.frames],
            "snapshotSha256": hashlib.sha256(
                Y.X._canonical(self.pair.expected)).hexdigest(),
            "receiptKeySha256": hashlib.sha256(pub).hexdigest(),
        }
        self._sign_document()

    def _sign_document(self):
        self.statement = Y.X._canonical(self.document)
        self.signature = self.witness_key.sign(Y.DOMAIN + self.statement)

    def params(self, **changes):
        args = dict(
            ledger_root=self.root, challenge=self.challenge,
            signed_statement=self.statement, witness_signature=self.signature,
            independently_pinned_witness_key=self.witness_key.public_key(),
            independently_pinned_receipt_key=self.pair.key.public_key(),
            evidence_line=self._evidence(), signed_receipts=self.pair.frames,
            independently_measured=self.pair.expected,
            expected_release_epoch=self.epoch, expected_release_sequence=self.sequence,
        )
        args.update(changes)
        return args

    def verify(self, **changes):
        return Y.inspect_and_consume(**self.params(**changes))

    def refused(self, **changes):
        with self.assertRaises(Y.Refused):
            self.verify(**changes)

    def state(self, challenge=None):
        challenge = self.challenge if challenge is None else challenge
        with Y._connect(self.root) as db:
            return db.execute(
                "SELECT state,signed_record_sha256 FROM challenges WHERE digest=?",
                (hashlib.sha256(challenge).hexdigest(),)).fetchone()

    def test_01_complete_signed_record_and_four_denials_consume_once_without_auth(self):
        response = self.verify()
        self.assertEqual(response["schema"], Y.RECEIPT_SCHEMA)
        for key in ("completeHostRecordSignatureVerifiedInCI",
                    "fourSignedDenialsBoundToFullRecordInCI",
                    "separatelyIssuedChallengeConsumedInRootLocalCI"):
            self.assertIs(response[key], True)
        for key in ("externalIssuerCustodyVerified", "externalRollbackResistanceVerified",
                    "independentHostOriginVerified", *Y.X.NEGATIVE):
            self.assertIs(response[key], False)
        self.assertEqual(self.state(), ("consumed", hashlib.sha256(self.statement).hexdigest()))

    def test_02_replay_after_new_verifier_instance_refused(self):
        self.verify()
        self.issuer = Y.DisposableCIChallengeIssuer(self.root)
        self.refused()
        self.assertEqual(self.state()[0], "consumed")

    def test_03_unknown_challenge_refused_without_inserting(self):
        unknown = b"x" * 32
        self.challenge = unknown
        self._sign()
        self.refused()
        self.assertIsNone(self.state(unknown))

    def test_04_invalid_witness_public_key_preserves_challenge(self):
        self.refused(independently_pinned_witness_key=Ed25519PrivateKey.generate().public_key())
        self.assertEqual(self.state(), ("issued", None))
        self.assertIs(self.verify()["separatelyIssuedChallengeConsumedInRootLocalCI"], True)

    def test_05_wrong_receipt_key_fails_prior_to_consume(self):
        self.refused(independently_pinned_receipt_key=Ed25519PrivateKey.generate().public_key())
        self.assertEqual(self.state(), ("issued", None))

    def test_06_same_witness_and_receipt_key_roles_refused(self):
        self.refused(independently_pinned_witness_key=self.pair.key.public_key())
        self.assertEqual(self.state(), ("issued", None))

    def test_07_changed_process_pid_start_or_selinux_without_resigning_refused(self):
        for k,v in (("pid", 1485), ("startTicks", 999999),
                    ("selinux","system_u:system_r:unconfined_service_t:s0")):
            with self.subTest(k=k):
                old=self.pair.records[2]["after"][k]
                self.pair.records[2]["after"][k]=v
                self.refused()
                self.pair.records[2]["after"][k]=old
        self.assertEqual(self.state(), ("issued", None))

    def test_08_resigning_forged_process_observation_cannot_override_expected_pins(self):
        self.pair.records[0]["before"]["rpmSha256"]="1"*64
        self._sign()
        self.refused()
        self.assertEqual(self.state(), ("issued", None))

    def test_09_changed_receipt_byte_without_resigning_fails_full_digest(self):
        frame=self.pair.frames[1]
        self.pair.frames[1]=frame.replace(b"UNAVAILABLE",b"UNAVAILABLZ")
        self.refused()
        self.assertEqual(self.state(), ("issued", None))

    def test_10_valid_full_record_signature_but_replayed_wrong_action_receipt_refused(self):
        self.pair.frames[1]=self.pair.frames[0]
        self._sign()
        self.refused()
        self.assertEqual(self.state(), ("issued", None))

    def test_11_wrong_audience_role_purpose_or_release_floor_refused(self):
        for name,value in (("audience","another-app"), ("role","fake.status"),
                           ("purpose","production.sign-in"), ("releaseEpoch", 8),
                           ("releaseSequence", 13)):
            with self.subTest(name=name):
                old=self.document[name]
                self.document[name]=value
                self._sign_document()
                self.refused()
                self.document[name]=old
                self._sign_document()
        self.refused(expected_release_epoch=8)
        self.refused(expected_release_sequence=13)
        self.assertEqual(self.state(), ("issued", None))

    def test_12_changed_challenge_binding_or_digest_refused(self):
        for name in ("challengeSha256","evidenceSha256","snapshotSha256",
                     "receiptKeySha256"):
            with self.subTest(name=name):
                old=self.document[name]
                self.document[name]="f"*64
                self._sign_document()
                self.refused()
                self.document[name]=old
                self._sign_document()
        self.assertEqual(self.state(), ("issued", None))

    def test_13_noncanonical_duplicate_fields_bad_signature_and_wrong_domain_refused(self):
        self.refused(signed_statement=self.statement+b"\n")
        raw=self.statement.replace(b'"schema":',b'"schema":"bad","schema":',1)
        self.refused(signed_statement=raw)
        self.refused(signed_statement=self.statement.replace(b',"role":',b', "role":',1))
        self.refused(witness_signature=self.witness_key.sign(b"wrong-domain"+self.statement))
        self.refused(witness_signature=b"\x00"*64)
        self.assertEqual(self.state(), ("issued", None))

    def test_14_unique_nonce_inside_bundle_is_mandatory_despite_new_signature(self):
        self.pair.records[3]["clientNonce"]=self.pair.records[0]["clientNonce"]
        self._sign()
        self.refused()
        self.assertEqual(self.state(), ("issued", None))

    def test_15_replacement_same_key_different_host_instance_refused(self):
        replacement=Y.X.Receipt.ReceiptIssuer(self.pair.key)
        nonce=self.pair.records[1]["clientNonce"]
        self.pair.frames[1]=self.pair._seal(replacement,"STATUS",Y.X.REQUEST_ID,nonce)
        self._sign()
        self.refused()
        self.assertEqual(self.state(), ("issued", None))

    def test_16_exactly_one_concurrent_consume_succeeds(self):
        def attempt(_):
            try:
                return self.verify()
            except Y.Refused as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt, range(2)))
        self.assertEqual(sum(isinstance(x,dict) for x in results),1)
        self.assertEqual(self.state()[0],"consumed")

    def test_17_deleted_or_unsafe_ledger_refuses_no_automatic_bootstrap(self):
        db=self.root / Y.DB_FILE
        db.unlink()
        self.refused()
        self.assertFalse(db.exists())

    def test_18_wrong_root_permissions_or_symlinked_database_refused(self):
        self.root.chmod(0o755)
        self.refused()
        self.root.chmod(0o700)
        original=self.root/Y.DB_FILE
        other=self.root/"other.sqlite"
        original.rename(other)
        original.symlink_to(other)
        self.refused()

    def test_19_invalid_type_pins_or_signed_release_numbers_refused(self):
        self.refused(independently_measured={**self.pair.expected,"uid":True})
        self.refused(expected_release_epoch=True)
        self.refused(expected_release_sequence=0)
        self.assertEqual(self.state(),("issued",None))

    def test_20_no_live_native_host_or_production_path(self):
        source=(HERE/"C3eYSignedHostChallenge.py").read_text()
        for forbidden in ("socket.socket(", "subprocess.run(", "systemctl start",
                          "rpm-ostree install", "HostBoundary.authenticated(",
                          "canBeginSignIn\": True", "productionAuthority\": True",
                          "InstalledIdentityCommandAdapterV1("):
            self.assertNotIn(forbidden,source)
        for name in ("externalIssuerCustodyVerified", "externalRollbackResistanceVerified",
                     "independentHostOriginVerified"):
            self.assertIn('"'+name+'": False',source)
        self.assertIn("**X.NEGATIVE",source)
        for name,flag in Y.X.NEGATIVE.items():
            with self.subTest(name=name):
                self.assertIs(flag,False)


    def test_21_caller_list_and_pins_cannot_change_signed_snapshot_during_check(self):
        original = Y.X.inspect_running_denials
        pinned_frames = tuple(self.pair.frames)
        pinned_measurements = dict(self.pair.expected)

        def replace_after_signature(*, evidence_line, signed_receipts,
                                    independently_pinned_receipt_key,
                                    independently_measured):
            # Deliberately alter the original caller objects AFTER the
            # statement's full-record signature and hashes were checked.
            self.pair.frames[0] = b"malicious caller-replaced receipt"
            self.pair.expected["pid"] = 999999
            self.assertIs(type(signed_receipts), tuple)
            self.assertEqual(signed_receipts, pinned_frames)
            self.assertIsNot(independently_measured, self.pair.expected)
            self.assertEqual(independently_measured, pinned_measurements)
            return original(
                evidence_line=evidence_line, signed_receipts=signed_receipts,
                independently_pinned_receipt_key=independently_pinned_receipt_key,
                independently_measured=independently_measured)

        with mock.patch.object(Y.X, "inspect_running_denials",
                               side_effect=replace_after_signature):
            self.assertTrue(self.verify()["completeHostRecordSignatureVerifiedInCI"])
        self.assertEqual(self.state()[0], "consumed")

if __name__=="__main__":
    unittest.main(verbosity=2)
