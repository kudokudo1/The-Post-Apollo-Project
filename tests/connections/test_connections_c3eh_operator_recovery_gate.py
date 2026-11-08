#!/usr/bin/env python3
"""C3e-H disposable operator signature gate for pending-release supersession."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    assert sp and sp.loader
    module = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(module)
    return module


gate = load("c3eh_operator", HERE / "C3eOperatorRecoveryGate.py")
previous = load(
    "c3eh_prior_crash_tests",
    ROOT / "tests/connections/test_connections_c3eg_split_commit_recovery.py",
)


def gpg(home, *args):
    command = ["gpg", "--homedir", str(home), "--batch", "--yes",
               "--pinentry-mode", "loopback", "--passphrase", "", *args]
    p = subprocess.run(
        command, capture_output=True, text=True,
        timeout=25, stdin=subprocess.DEVNULL, check=False)
    if p.returncode:
        raise AssertionError("disposable operator GPG command failed: " + p.stderr[-900:])
    return p.stdout


class C3eHOperatorRecoveryGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous.C3eGSplitCommitRecoveryTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        previous.C3eGSplitCommitRecoveryTests.tearDownClass()

    def setUp(self):
        self.fx = previous.C3eGSplitCommitRecoveryTests(
            "test_02_signed_release_flows_through_intent_and_two_commits")
        self.fx.setUp()
        self.operator_home = self.fx.fx.fx.folder / "gpg_operator"
        self.operator_home.mkdir(mode=0o700)
        os.chmod(self.operator_home, 0o700)
        gpg(self.operator_home, "--quick-generate-key",
            "C3eH Test Operator <c3eh@example.invalid>", "ed25519", "sign", "0")
        listing = gpg(self.operator_home, "--with-colons",
                      "--fingerprint", "--list-keys")
        pins = [line.split(":")[9] for line in listing.splitlines()
                if line.startswith("fpr:")]
        self.assertEqual(len(pins), 1)
        self.operator_pin = pins[0]
        self.operator_pub = self.fx.fx.fx.folder / "operator.asc"
        self.operator_pub.write_text(
            gpg(self.operator_home, "--armor", "--export", self.operator_pin))
        self.approval_path = self.fx.fx.fx.folder / "operator-approval.json"
        self.signature_path = self.fx.fx.fx.folder / "operator-approval.sig"
        self.latest = None

    def tearDown(self):
        self.fx.tearDown()

    def prepare(self):
        self.fx.prepare_nine()
        self.fx.crash_at("client-committed")
        self.assertEqual(self.fx.phase()["phase"], "client_committed")
        self.fx.fx.fx.issue(5, 10, b"fake-signed-release-10")
        self.fx.fx.fx.advance()
        self.sign_approval()

    def expected(self):
        db = gate.split._db(self.fx.fx.location)
        try:
            saved = gate.split._witness(db)
            pending = gate.split._intent(db)
        finally:
            db.close()
        self.assertIsNotNone(pending)
        fx = self.fx.fx.fx
        now = int(time.time())
        return dict(
            schema=gate.SCHEMA, action=gate.ACTION, audience=gate.AUDIENCE,
            release_id=gate.admission.RELEASE_ID, node_id=self.fx.fx.node,
            release_root_pin=self.fx.fx.root_pin,
            authority_anchor_pin=self.fx.fx.anchor_pin,
            operator_signer_pin=self.operator_pin,
            pending_intent_sha256=gate.intent_digest(saved, pending),
            new_policy_epoch=5, new_release_sequence=10,
            new_policy_sha256=hashlib.sha256(fx.policy.read_bytes()).hexdigest(),
            new_artifact_sha256=hashlib.sha256(fx.artifact.read_bytes()).hexdigest(),
            authority_policy_floor=5, authority_release_floor=10,
            issued_at=now-5, expires_at=now+120,
        )

    def sign_approval(self, *, changes=None, signer_home=None, raw=None):
        values = self.expected()
        values.update(changes or {})
        if raw is None:
            raw = json.dumps(values, sort_keys=True, separators=(",", ":"))
        self.approval_path.write_text(raw)
        gpg(signer_home or self.operator_home, "--detach-sign",
            "--output", str(self.signature_path), str(self.approval_path))
        self.latest = values

    def args(self, **overrides):
        fx = self.fx.fx.fx
        opts = dict(
            witness_db=self.fx.fx.location, client_db=fx.client_db,
            operator_public=self.operator_pub, operator_pin=self.operator_pin,
            operator_signed_approval=self.approval_path,
            operator_signature=self.signature_path,
            authority_anchor_public=fx.public["external-anchor"],
            authority_anchor_pin=self.fx.fx.anchor_pin,
            node_id=self.fx.fx.node, release_root_pin=self.fx.fx.root_pin,
            request_proof=fx.remote_proof,
            release_root_public=fx.public["release-root"],
            policy=fx.policy, policy_signature=fx.policy_sig,
            delegated_public=fx.public["release-delegated"],
            manifest=fx.manifest, manifest_signature=fx.manifest_sig,
            artifact=fx.artifact,
        )
        opts.update(overrides)
        return opts

    def check(self, **overrides):
        return gate.inspect_operator_supersession(**self.args(**overrides))

    def refuses(self, code, **overrides):
        before = self.fx.phase()
        with self.assertRaises(gate.Refused) as error:
            self.check(**overrides)
        self.assertEqual(str(error.exception), code)
        self.assertEqual(self.fx.phase(), before)

    def test_01_strict_operator_approval_authenticates_pending_and_new_release(self):
        self.prepare()
        self.assertEqual(self.check(), gate.SUCCESS)
        self.assertEqual(self.fx.phase()["phase"], "client_committed")
        self.assertTrue(self.fx.phase()["pending"])

    def test_02_no_pending_intent_does_not_request_operator_recovery(self):
        self.fx.fx.fx.advance()
        self.refuses("NO_PENDING_INTENT")

    def test_03_operator_signature_missing_or_modified_is_rejected(self):
        self.prepare()
        self.approval_path.write_text(self.approval_path.read_text() + " ")
        self.refuses("OPERATOR_SIGNATURE_REFUSED")
        self.sign_approval()
        self.signature_path.write_bytes(b"not a detached signature")
        self.refuses("OPERATOR_SIGNATURE_REFUSED")

    def test_04_wrong_operator_key_and_pin_refuse(self):
        self.prepare()
        self.refuses("OPERATOR_PIN_MISMATCH",
                     operator_public=self.fx.fx.fx.public["forger"])
        self.refuses("OPERATOR_KEY_NOT_INDEPENDENT",
                     operator_pin=self.fx.fx.root_pin)
        self.refuses("OPERATOR_KEY_NOT_INDEPENDENT",
                     operator_pin=self.fx.fx.anchor_pin)

    def test_05_expired_future_issued_and_excess_validity_refused(self):
        self.prepare()
        now = int(time.time())
        for values in (
            {"issued_at": now-200, "expires_at": now-1},
            {"issued_at": now+100, "expires_at": now+200},
            {"issued_at": now-1000, "expires_at": now+300},
            {"issued_at": True, "expires_at": now+100},
        ):
            self.sign_approval(changes=values)
            self.refuses("OPERATOR_APPROVAL_EXPIRED_OR_INVALID")

    def test_06_replayed_approval_for_other_pending_intent_refuses(self):
        self.prepare()
        self.sign_approval(changes={"pending_intent_sha256": "0"*64})
        self.refuses("SIGNED_APPROVAL_CONTEXT_MISMATCH")

    def test_07_wrong_node_root_anchor_and_scope_refuse(self):
        self.prepare()
        for field, value in (
            ("node_id", "synthetic-other-node"),
            ("release_root_pin", self.fx.fx.fx.fprs["forger"]),
            ("authority_anchor_pin", self.fx.fx.fx.fprs["forger"]),
            ("audience", "postapollo.credentials.grant"),
            ("action", "reset-trust"),
        ):
            self.sign_approval(changes={field:value})
            self.refuses("SIGNED_APPROVAL_CONTEXT_MISMATCH")

    def test_08_forged_target_digest_epoch_sequence_and_floor_refuse(self):
        self.prepare()
        for field, value in (
            ("new_policy_epoch", 6), ("new_release_sequence", 11),
            ("new_policy_sha256", "a"*64),
            ("new_artifact_sha256", "a"*64),
            ("authority_policy_floor", 6), ("authority_release_floor", 11),
        ):
            self.sign_approval(changes={field:value})
            self.refuses("SIGNED_APPROVAL_CONTEXT_MISMATCH")

    def test_09_invalid_signed_json_duplicate_or_extra_fields_refused(self):
        self.prepare()
        raw = self.approval_path.read_text()
        self.sign_approval(raw=raw[:-1]+',"node_id":"another-node"}')
        self.refuses("DUPLICATE_SIGNED_APPROVAL_FIELD")
        self.sign_approval(changes={"unauthorized": "field"})
        self.refuses("INVALID_SIGNED_APPROVAL_SHAPE")

    def test_10_fresh_authority_signature_must_still_match_new_release(self):
        self.prepare()
        self.refuses(
            "FRESH_AUTHORITY_REFUSED_AUTHORITY_PROOF_UNAVAILABLE",
            request_proof=lambda _: (_ for _ in ()).throw(OSError("unavailable")))
        old = self.fx.fx.fx.remote_proof("a"*64)
        self.refuses(
            "FRESH_AUTHORITY_REFUSED_INVALID_AUTHORITY_PROOF_REPLAYED_OR_UNSOLICITED_PROOF",
            request_proof=lambda _: old)

    def test_11_unsigned_or_changed_candidate_refused_even_with_operator_signoff(self):
        self.prepare()
        self.fx.fx.fx.manifest.write_text(self.fx.fx.fx.manifest.read_text()+" ")
        self.refuses("NEW_SIGNED_RELEASE_REFUSED_SIGNED_RELEASE_REFUSED_INVALID_DETACHED_SIGNATURE")

    def test_12_approval_is_readonly_and_does_not_clear_journal(self):
        self.prepare()
        before = self.fx.phase()
        self.assertEqual(self.check(), gate.SUCCESS)
        self.assertEqual(self.check(), gate.SUCCESS)
        self.assertEqual(self.fx.phase(), before)

    def test_13_symlinked_operator_material_refused(self):
        self.prepare()
        target = self.fx.fx.fx.folder / "approval-real"
        self.approval_path.rename(target)
        self.approval_path.symlink_to(target)
        self.refuses("UNSAFE_OPERATOR_SIGNATURE_INPUT")

    def test_14_changed_client_state_not_approved(self):
        self.prepare()
        with sqlite3.connect(self.fx.fx.fx.client_db) as db:
            db.execute("UPDATE checkpoint SET artifact_digest=? WHERE id=1",
                       ("b"*64,))
        self.refuses("CLIENT_PENDING_STATE_CONFLICT")

    def test_15_real_broker_and_authority_remain_unmodified(self):
        self.prepare()
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base/"ConnectionsRequestStatus.qml").read_text())
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base/"ConnectionsBroker.qml").read_text())
        for p in (*base.glob("*.qml"), *base.glob("*.js"), base/"qmldir"):
            self.assertNotIn("C3eOperatorRecoveryGate", p.read_text(), p)
        source = (HERE/"C3eOperatorRecoveryGate.py").read_text()
        for forbidden in ("UPDATE witness", "DELETE FROM split_intent",
                          "systemctl start", "rpm --import", "secret-tool"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
