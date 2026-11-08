#!/usr/bin/env python3
"""C3e-D real GPG signatures: external freshness proof must bind each challenge.

All signing keys are disposable fixtures. This tests policy/mechanics only:
the CI "authority" has no protected independent release history or custody.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eExternalFloorProof.py"
spec = importlib.util.spec_from_file_location("c3ed_test_proof", SOURCE)
assert spec and spec.loader
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


def gpg(home: Path, *args):
    r = subprocess.run(
        ["gpg", "--homedir", str(home), "--batch", "--yes",
         "--pinentry-mode", "loopback", "--passphrase", "", *args],
        capture_output=True, text=True, timeout=25, check=False,
        stdin=subprocess.DEVNULL)
    if r.returncode:
        raise AssertionError("synthetic GPG fixture error: " + r.stderr[-800:])
    return r.stdout


class C3eDSignedExternalFloorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = tempfile.TemporaryDirectory(prefix="c3ed-ci-")
        cls.home = Path(cls.container.name)
        cls.keyhomes, cls.fingerprints, cls.public = {}, {}, {}
        for name in ("root", "release", "anchor", "other"):
            p = cls.home / ("gpg_" + name)
            p.mkdir(mode=0o700)
            os.chmod(p, 0o700)
            gpg(p, "--quick-generate-key",
                "C3eD Disposable " + name + " <" + name + "@example.invalid>",
                "ed25519", "sign", "0")
            listed = gpg(p, "--with-colons", "--fingerprint", "--list-keys")
            fingerprints = [line.split(":")[9] for line in listed.splitlines()
                            if line.startswith("fpr:")]
            if len(fingerprints) != 1:
                raise AssertionError("invalid synthetic signer")
            cls.keyhomes[name] = p
            cls.fingerprints[name] = fingerprints[0]
            pub = cls.home / (name + ".asc")
            pub.write_text(gpg(p, "--armor", "--export", fingerprints[0]))
            cls.public[name] = pub

    @classmethod
    def tearDownClass(cls):
        cls.container.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="run-", dir=self.home)
        self.dir = Path(self.temp.name)
        self.node = "synthetic-node-01"
        self.db = self.dir / "checkpoint.sqlite"
        self.policy = self.dir / "policy.json"
        self.policy_sig = self.dir / "policy.sig"
        self.manifest = self.dir / "manifest.json"
        self.manifest_sig = self.dir / "manifest.sig"
        self.artifact = self.dir / "fake-status.rpm"
        self.proof_serial = 0
        self.epoch, self.sequence = 3, 8
        self.issue(3, 8, b"synthetic package 8")
        proof.durable.bootstrap(
            self.db, trusted_root_pin=self.fingerprints["root"],
            initial_epoch=3, initial_sequence=8)

    def tearDown(self):
        self.temp.cleanup()

    def issue(self, epoch, sequence, artifact):
        self.artifact.write_bytes(artifact)
        meta = {
            "sequence": sequence, "sha256": hashlib.sha256(artifact).hexdigest(),
            "size": len(artifact),
        }
        policy_doc = {
            "schema": proof.admission.POLICY_SCHEMA,
            "release_id": proof.admission.RELEASE_ID,
            "epoch": epoch, "min_sequence": sequence,
            "signers": [
                {"fingerprint": self.fingerprints["release"], "state": "active"}
            ],
            "approved_artifacts": [meta],
        }
        manifest_doc = {
            "schema": proof.admission.MANIFEST_SCHEMA,
            "release_id": proof.admission.RELEASE_ID, **meta,
        }
        self.policy.write_text(json.dumps(
            policy_doc, sort_keys=True, separators=(",", ":")))
        self.manifest.write_text(json.dumps(
            manifest_doc, sort_keys=True, separators=(",", ":")))
        gpg(self.keyhomes["root"], "--output", str(self.policy_sig),
            "--detach-sign", str(self.policy))
        gpg(self.keyhomes["release"], "--output", str(self.manifest_sig),
            "--detach-sign", str(self.manifest))

    def oracle(self, *, signer="anchor", overrides=None, reuse=None,
               invalid_signature=False):
        """Simulates an independent signing authority answering a challenge."""
        def response(challenge):
            if reuse is not None:
                return reuse
            values = {
                "schema": proof.SCHEMA, "audience": proof.AUDIENCE,
                "release_id": proof.admission.RELEASE_ID,
                "node_id": self.node, "challenge": challenge,
                "release_root_pin": self.fingerprints["root"],
                "minimum_policy_epoch": self.epoch,
                "minimum_release_sequence": self.sequence,
            }
            values.update(overrides or {})
            message = json.dumps(
                values, sort_keys=True, separators=(",", ":")).encode()
            self.proof_serial += 1
            msg_path = self.dir / f"external-{self.proof_serial}.json"
            sig_path = self.dir / f"external-{self.proof_serial}.sig"
            msg_path.write_bytes(message)
            gpg(self.keyhomes[signer], "--detach-sign",
                "--output", str(sig_path), str(msg_path))
            signature = sig_path.read_bytes()
            if invalid_signature:
                signature = signature[:-1] + bytes([signature[-1] ^ 1])
            return message, signature
        return response

    def admit(self, oracle=None, **overrides):
        arguments = {
            "db_path": self.db,
            "anchor_public": self.public["anchor"],
            "anchor_pin": self.fingerprints["anchor"],
            "node_id": self.node,
            "release_root_pin": self.fingerprints["root"],
            "request_proof": oracle if oracle is not None else self.oracle(),
            "root_public": self.public["root"],
            "policy": self.policy, "policy_signature": self.policy_sig,
            "delegated_public": self.public["release"],
            "manifest": self.manifest, "manifest_signature": self.manifest_sig,
            "artifact": self.artifact,
        }
        arguments.update(overrides)
        return proof.admit_with_external_proof(**arguments)

    def refuses(self, code, oracle=None, **overrides):
        before = proof.durable.inspect(self.db)
        with self.assertRaises(proof.Refused) as failure:
            self.admit(oracle=oracle, **overrides)
        self.assertEqual(str(failure.exception), code)
        self.assertEqual(proof.durable.inspect(self.db), before)

    def test_01_genuine_distinct_anchor_accepts_real_gpg_policy(self):
        self.assertEqual(self.admit(), proof.SUCCESS)
        self.assertEqual(proof.durable.inspect(self.db)[1:3], (3, 8))

    def test_02_anchor_can_sign_fresh_larger_floor_and_update_release(self):
        self.admit()
        self.epoch, self.sequence = 4, 9
        self.issue(4, 9, b"synthetic package 9")
        self.assertEqual(self.admit(), proof.SUCCESS)
        self.assertEqual(proof.durable.inspect(self.db)[1:3], (4, 9))
        self.issue(3, 8, b"synthetic package 8")
        self.refuses("RELEASE_CHECKPOINT_REFUSED_CRYPTO_REFUSED_POLICY_ROLLBACK_REFUSED")

    def test_03_old_signed_proof_fails_new_verifier_challenge(self):
        captured = []
        def cache_once(challenge):
            response = self.oracle()(challenge)
            captured.append(response)
            return response
        self.assertEqual(self.admit(oracle=cache_once), proof.SUCCESS)
        self.refuses("REPLAYED_OR_UNSOLICITED_PROOF",
                     oracle=self.oracle(reuse=captured[0]))

    def test_04_wrong_key_cannot_sign_anchor_proof(self):
        self.refuses("EXTERNAL_SIGNATURE_REFUSED",
                     oracle=self.oracle(signer="other"))

    def test_05_swapped_anchor_public_key_refused_by_pin(self):
        self.refuses("EXTERNAL_ANCHOR_PIN_MISMATCH",
                     anchor_public=self.public["other"])

    def test_06_release_root_cannot_be_its_own_external_anchor(self):
        self.refuses("EXTERNAL_ANCHOR_NOT_INDEPENDENT",
                     anchor_public=self.public["root"],
                     anchor_pin=self.fingerprints["root"])

    def test_07_proof_is_specific_to_the_node(self):
        self.refuses("WRONG_SIGNED_NODE",
                     oracle=self.oracle(overrides={"node_id": "synthetic-node-02"}))

    def test_08_proof_is_specific_to_release_root_and_release_id(self):
        self.refuses("WRONG_SIGNED_RELEASE_ROOT", oracle=self.oracle(
            overrides={"release_root_pin": self.fingerprints["other"]}))
        self.refuses("WRONG_SIGNED_RELEASE", oracle=self.oracle(
            overrides={"release_id": "unauthorized-release"}))

    def test_09_proof_cannot_be_repurposed_to_other_api(self):
        self.refuses("WRONG_SIGNED_PROOF_PURPOSE", oracle=self.oracle(
            overrides={"audience": "credential-grant"}))

    def test_10_absent_unreachable_or_malformed_authority_fails_closed(self):
        def unavailable(challenge):
            raise ConnectionError("offline test-only authority unavailable")
        self.refuses("EXTERNAL_AUTHORITY_UNAVAILABLE", oracle=unavailable)
        self.refuses("INVALID_AUTHORITY_RESPONSE",
                     oracle=lambda _: {"not": "signed"})
        self.refuses("INVALID_SIGNATURE_SIZE",
                     oracle=lambda _: (b"{}", b""))

    def test_11_zero_bool_or_reduced_floor_is_refused(self):
        for val in (0, False, "3", -1):
            self.refuses("INVALID_SIGNED_FLOORS",
                         oracle=self.oracle(overrides={"minimum_policy_epoch": val}))
        self.assertEqual(self.admit(), proof.SUCCESS)
        self.epoch, self.sequence = 4, 9
        self.issue(4, 9, b"synthetic package 9")
        self.assertEqual(self.admit(), proof.SUCCESS)
        self.issue(3, 8, b"synthetic package 8")
        # Even a genuine freshly signed *stale* floor cannot bypass SQLite.
        self.epoch, self.sequence = 3, 8
        self.refuses("RELEASE_CHECKPOINT_REFUSED_POLICY_ROLLBACK_REFUSED")

    def test_12_modified_signature_and_modified_message_are_rejected(self):
        self.refuses("EXTERNAL_SIGNATURE_REFUSED",
                     oracle=self.oracle(invalid_signature=True))
        def modified(challenge):
            document, sig = self.oracle()(challenge)
            return document + b" ", sig
        self.refuses("EXTERNAL_SIGNATURE_REFUSED", oracle=modified)

    def test_13_no_caller_controlled_nonce_or_wrong_node_parameter(self):
        self.refuses("INVALID_NODE_ID", node_id="../etc/hosts")
        self.refuses("WRONG_SIGNED_NODE", node_id="another-node-01")

    def test_14_unauthorized_root_policy_change_rejected_after_anchor(self):
        self.admit()
        self.policy.write_text(self.policy.read_text() + " ")
        self.refuses("RELEASE_CHECKPOINT_REFUSED_CRYPTO_REFUSED_INVALID_DETACHED_SIGNATURE")

    def test_15_no_silent_bootstrap_and_no_production_paths(self):
        missing = self.dir / "missing-ledger.db"
        self.refuses("RELEASE_CHECKPOINT_REFUSED_LEDGER_MISSING_REQUIRES_EXPLICIT_BOOTSTRAP",
                     db_path=missing)
        self.assertFalse(missing.exists())
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        for path in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eExternalFloorProof", path.read_text(), path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
