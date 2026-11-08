#!/usr/bin/env python3
"""C3e-E: separate-process CI authority with its OWN signed-release history.

Disposable GPG keys and two distinct SQLite ledgers. No real external host,
root custody, TPM, app client identity, native RPM install, or production key.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"
AUTHORITY_SCRIPT = HERE / "C3eAuthorityOwnedFloor.py"


def import_source(name, path):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


durable = import_source("c3ee_test_durable", "C3eDurableFloor.py")
proof = import_source("c3ee_test_proof", "C3eExternalFloorProof.py")


def gpg(home, *args):
    p = subprocess.run(
        ["gpg", "--homedir", str(home), "--batch", "--yes",
         "--pinentry-mode", "loopback", "--passphrase", "", *args],
        capture_output=True, text=True, timeout=25, stdin=subprocess.DEVNULL)
    if p.returncode:
        raise AssertionError("disposable GPG fixture failure: " + p.stderr[-900:])
    return p.stdout


class C3eEAuthorityOwnedFloorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sandbox = tempfile.TemporaryDirectory(prefix="c3ee-process-test-")
        cls.root = Path(cls.sandbox.name)
        cls.homes, cls.fprs, cls.public = {}, {}, {}
        for key in ("release-root", "release-delegated", "external-anchor", "forger"):
            home = cls.root / ("gpg-" + key)
            home.mkdir(mode=0o700)
            os.chmod(home, 0o700)
            gpg(home, "--quick-generate-key",
                "C3eE Test " + key + " <" + key + "@example.invalid>",
                "ed25519", "sign", "0")
            listed = gpg(home, "--with-colons", "--fingerprint", "--list-keys")
            fprs = [line.split(":")[9] for line in listed.splitlines()
                    if line.startswith("fpr:")]
            if len(fprs) != 1:
                raise AssertionError("unexpected disposable keyring")
            cls.fprs[key] = fprs[0]
            cls.homes[key] = home
            pub = cls.root / (key + ".asc")
            pub.write_text(gpg(home, "--armor", "--export", fprs[0]))
            cls.public[key] = pub

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="case-", dir=self.root)
        self.folder = Path(self.temporary.name)
        self.node = "synthetic-client-01"
        self.authority_db = self.folder / "authority-owned.sqlite"
        self.client_db = self.folder / "client-owned.sqlite"
        self.policy = self.folder / "policy.json"
        self.policy_sig = self.folder / "policy.sig"
        self.manifest = self.folder / "manifest.json"
        self.manifest_sig = self.folder / "manifest.sig"
        self.artifact = self.folder / "synthetic-status.rpm"
        self.issue(3, 8, b"fake-signed-release-8")
        for path in (self.authority_db, self.client_db):
            durable.bootstrap(
                path, trusted_root_pin=self.fprs["release-root"],
                initial_epoch=3, initial_sequence=8)

    def tearDown(self):
        self.temporary.cleanup()

    def issue(self, epoch, sequence, payload):
        self.artifact.write_bytes(payload)
        meta = {
            "sequence": sequence, "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        policy = {
            "schema": proof.admission.POLICY_SCHEMA,
            "release_id": proof.admission.RELEASE_ID,
            "epoch": epoch, "min_sequence": sequence,
            "signers": [{
                "fingerprint": self.fprs["release-delegated"], "state": "active"
            }],
            "approved_artifacts": [meta],
        }
        manifest = {
            "schema": proof.admission.MANIFEST_SCHEMA,
            "release_id": proof.admission.RELEASE_ID, **meta,
        }
        self.policy.write_text(json.dumps(
            policy, sort_keys=True, separators=(",", ":")))
        self.manifest.write_text(json.dumps(
            manifest, sort_keys=True, separators=(",", ":")))
        gpg(self.homes["release-root"], "--detach-sign",
            "--output", str(self.policy_sig), str(self.policy))
        gpg(self.homes["release-delegated"], "--detach-sign",
            "--output", str(self.manifest_sig), str(self.manifest))

    def _config(self):
        return [
            sys.executable, "-B", str(AUTHORITY_SCRIPT),
            "--state-db", str(self.authority_db),
            "--release-root-public", str(self.public["release-root"]),
            "--release-root-pin", self.fprs["release-root"],
            "--anchor-secret-home", str(self.homes["external-anchor"]),
            "--anchor-pin", self.fprs["external-anchor"],
            "--node-id", self.node,
        ]

    def command(self, request, *, config=None):
        p = subprocess.run(
            config or self._config(),
            input=json.dumps(request), text=True,
            capture_output=True, timeout=15, check=False)
        try:
            body = json.loads(p.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(
                "invalid authority output: " + p.stdout + p.stderr) from e
        return p.returncode, body

    def assert_refusal(self, reason, request, *, config=None):
        status, response = self.command(request, config=config)
        self.assertEqual(status, 2, response)
        self.assertEqual(response, {"refused": reason})
        return response

    def release_request(self):
        return {
            "op": "advance", "policy": str(self.policy),
            "policy_signature": str(self.policy_sig),
            "delegated_public": str(self.public["release-delegated"]),
            "manifest": str(self.manifest),
            "manifest_signature": str(self.manifest_sig),
            "artifact": str(self.artifact),
        }

    def advance(self):
        status, response = self.command(self.release_request())
        self.assertEqual(status, 0, response)
        self.assertEqual(response["status"],
                         "C3EE_SIGNED_RELEASE_COMMITTED_TEST_ONLY")
        return response

    def attest_request(self, challenge="a" * 64):
        return {
            "op": "attest", "node_id": self.node,
            "release_root_pin": self.fprs["release-root"],
            "challenge": challenge,
        }

    def remote_proof(self, challenge):
        status, response = self.command(self.attest_request(challenge))
        if status != 0:
            raise RuntimeError(response.get("refused", "unavailable"))
        return (base64.b64decode(response["proof_b64"]),
                base64.b64decode(response["signature_b64"]))

    def client_admit(self, callback=None):
        return proof.admit_with_external_proof(
            db_path=self.client_db,
            anchor_public=self.public["external-anchor"],
            anchor_pin=self.fprs["external-anchor"],
            node_id=self.node,
            release_root_pin=self.fprs["release-root"],
            request_proof=callback or self.remote_proof,
            root_public=self.public["release-root"],
            policy=self.policy, policy_signature=self.policy_sig,
            delegated_public=self.public["release-delegated"],
            manifest=self.manifest, manifest_signature=self.manifest_sig,
            artifact=self.artifact,
        )

    def test_01_explicitly_bootstrapped_but_empty_authority_will_not_attest(self):
        self.assert_refusal(
            "NO_VERIFIED_RELEASE_HISTORY", self.attest_request())
        self.assertEqual(durable.inspect(self.authority_db)[1:3], (3, 8))

    def test_02_authority_advances_from_actual_signed_release_not_client_floor(self):
        self.assertEqual(self.advance()["sequence"], 8)
        self.assertEqual(self.client_admit(), proof.SUCCESS)
        self.assertEqual(durable.inspect(self.client_db)[1:3], (3, 8))
        status, answer = self.command(self.attest_request())
        self.assertEqual(status, 0, answer)
        statement = json.loads(base64.b64decode(answer["proof_b64"]))
        self.assertEqual(statement["minimum_release_sequence"], 8)
        self.assertEqual(statement["minimum_policy_epoch"], 3)

    def test_03_caller_cannot_choose_what_floor_is_signed(self):
        self.advance()
        request = self.attest_request()
        request["minimum_release_sequence"] = 999999
        self.assert_refusal("ATTEST_REQUEST_SHAPE_REFUSED", request)
        attempt = self.release_request()
        attempt["epoch"] = 999999
        self.assert_refusal("ADVANCE_REQUEST_SHAPE_REFUSED", attempt)
        status, answer = self.command(self.attest_request())
        self.assertEqual(status, 0)
        statement = json.loads(base64.b64decode(answer["proof_b64"]))
        self.assertEqual(statement["minimum_release_sequence"], 8)

    def test_04_client_restore_detected_using_unrestored_external_history(self):
        self.advance()
        self.assertEqual(self.client_admit(), proof.SUCCESS)
        old_client = self.folder / "old-client-checkpoint"
        shutil.copy2(self.client_db, old_client)
        self.issue(4, 9, b"fake-signed-release-9")
        self.advance()
        self.assertEqual(self.client_admit(), proof.SUCCESS)
        self.assertEqual(durable.inspect(self.client_db)[1:3], (4, 9))
        shutil.copy2(old_client, self.client_db)
        self.assertEqual(durable.inspect(self.client_db)[1:3], (3, 8))
        # The authority still knows release 9. An old valid signed release
        # cannot be admitted even after the client restores its old DB.
        self.issue(3, 8, b"fake-signed-release-8")
        with self.assertRaises(proof.Refused) as err:
            self.client_admit()
        self.assertIn("POLICY_ROLLBACK_REFUSED", str(err.exception))
        self.issue(4, 9, b"fake-signed-release-9")
        self.assertEqual(self.client_admit(), proof.SUCCESS)
        self.assertEqual(durable.inspect(self.client_db)[1:3], (4, 9))

    def test_05_unsigned_or_tampered_advance_refused_without_state_change(self):
        self.advance()
        before = durable.inspect(self.authority_db)
        self.issue(4, 9, b"fake-signed-release-9")
        self.manifest.write_text(self.manifest.read_text() + " ")
        self.assert_refusal(
            "SIGNED_RELEASE_REFUSED_CRYPTO_REFUSED_INVALID_DETACHED_SIGNATURE",
            self.release_request())
        self.assertEqual(durable.inspect(self.authority_db), before)

    def test_06_authority_rejects_older_valid_signed_release(self):
        self.advance()
        self.issue(4, 9, b"fake-signed-release-9")
        self.advance()
        self.issue(3, 8, b"fake-signed-release-8")
        self.assert_refusal(
            "SIGNED_RELEASE_REFUSED_CRYPTO_REFUSED_POLICY_ROLLBACK_REFUSED",
            self.release_request())
        self.assertEqual(durable.inspect(self.authority_db)[1:3], (4, 9))

    def test_07_signed_proof_replay_refused_by_fresh_verifier_challenge(self):
        self.advance()
        old_response = self.remote_proof("b" * 64)
        with self.assertRaises(proof.Refused) as err:
            self.client_admit(callback=lambda challenge: old_response)
        self.assertEqual(str(err.exception), "REPLAYED_OR_UNSOLICITED_PROOF")

    def test_08_wrong_node_root_and_nonce_refused(self):
        self.advance()
        fake_node = self.attest_request()
        fake_node["node_id"] = "another-node"
        self.assert_refusal("UNAUTHORIZED_NODE", fake_node)
        fake_root = self.attest_request()
        fake_root["release_root_pin"] = self.fprs["forger"]
        self.assert_refusal("UNAUTHORIZED_RELEASE_ROOT", fake_root)
        bad_nonce = self.attest_request("untrusted")
        self.assert_refusal("INVALID_VERIFIER_CHALLENGE", bad_nonce)

    def test_09_authority_state_loss_fails_closed_no_auto_bootstrap(self):
        self.advance()
        self.authority_db.unlink()
        self.assert_refusal("AUTHORITY_LEDGER_UNAVAILABLE", self.attest_request())
        self.assert_refusal("AUTHORITY_LEDGER_UNAVAILABLE", self.release_request())
        self.assertFalse(self.authority_db.exists())

    def test_10_authority_signing_key_cannot_be_substituted(self):
        self.advance()
        args = self._config()
        i = args.index("--anchor-secret-home") + 1
        args[i] = str(self.homes["forger"])
        self.assert_refusal("PINNED_AUTHORITY_SIGNER_UNAVAILABLE",
                            self.attest_request(), config=args)

    def test_11_arbitrary_requests_cannot_read_keys_or_reset_history(self):
        self.advance()
        for name in ("reset", "export-key", "set-floor", "install", "grant"):
            self.assert_refusal("UNSUPPORTED_AUTHORITY_OPERATION",
                                {"op": name})
        self.assertEqual(durable.inspect(self.authority_db)[1:3], (3, 8))

    def test_12_authority_backup_rollback_remains_a_known_vulnerability(self):
        # Explicitly demonstrate what this simulation DOES NOT prevent:
        # replacing the *authority* ledger with an older good snapshot.
        self.advance()
        backup = self.folder / "old-authority-checkpoint"
        shutil.copy2(self.authority_db, backup)
        self.issue(4, 9, b"fake-signed-release-9")
        self.advance()
        shutil.copy2(backup, self.authority_db)
        status, reply = self.command(self.attest_request())
        self.assertEqual(status, 0, reply)
        stale = json.loads(base64.b64decode(reply["proof_b64"]))
        self.assertEqual(stale["minimum_release_sequence"], 8)
        self.assertEqual(durable.inspect(self.authority_db)[2], 8)

    def test_13_real_production_broker_remains_disabled(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        source = AUTHORITY_SCRIPT.read_text()
        for token in ("systemctl start", "rpm --import", "secret-tool"):
            self.assertNotIn(token, source)
        for file in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eAuthorityOwnedFloor", file.read_text(), file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
