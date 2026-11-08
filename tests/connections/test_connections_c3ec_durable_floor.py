#!/usr/bin/env python3
"""C3e-C real GPG + SQLite restarts/rollback/rotation/crash fixture tests.

Uses disposable CI keys and files only. External floors here are SYNTHETIC,
not OS-backed monotonic counters or an operator-enrolled root.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eDurableFloor.py"
spec = importlib.util.spec_from_file_location("c3ec_floor_tests", SOURCE)
assert spec and spec.loader
floor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(floor)


def gpg(home: Path, *args: str) -> str:
    res = subprocess.run(
        ["gpg", "--homedir", str(home), "--batch", "--yes",
         "--pinentry-mode", "loopback", "--passphrase", "", *args],
        capture_output=True, text=True, timeout=30,
        stdin=subprocess.DEVNULL, check=False)
    if res.returncode:
        raise AssertionError("disposable GPG fixture command failed: " + res.stderr[-1200:])
    return res.stdout


class C3eCDurableFloorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory(prefix="c3ec-test-")
        cls.parent = Path(cls.root.name)
        cls.keys, cls.fingerprints, cls.public = {}, {}, {}
        for role in ("root", "a", "b"):
            home = cls.parent / ("key_" + role)
            home.mkdir(mode=0o700)
            os.chmod(home, 0o700)
            gpg(home, "--quick-generate-key",
                "C3eC Disposable " + role + " <" + role + "@example.invalid>",
                "ed25519", "sign", "0")
            listing = gpg(home, "--with-colons", "--fingerprint", "--list-keys")
            fprs = [line.split(":")[9] for line in listing.splitlines()
                    if line.startswith("fpr:")]
            assert len(fprs) == 1
            cls.keys[role] = home
            cls.fingerprints[role] = fprs[0]
            pub = cls.parent / (role + ".asc")
            pub.write_text(gpg(home, "--armor", "--export", fprs[0]))
            cls.public[role] = pub

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="case-", dir=self.parent)
        self.work = Path(self.temp.name)
        self.db = self.work / "checkpoint.sqlite"
        self.external_epoch, self.external_sequence = 3, 8
        self.policy = self.work / "policy.json"
        self.policy_sig = self.work / "policy.sig"
        self.manifest = self.work / "manifest.json"
        self.manifest_sig = self.work / "manifest.sig"
        self.artifact = self.work / "fake-test.rpm"
        self.signer = "a"
        self.issue(3, 8, b"synthetic package 8")
        floor.bootstrap(
            self.db, trusted_root_pin=self.fingerprints["root"],
            initial_epoch=3, initial_sequence=8)

    def tearDown(self):
        self.temp.cleanup()

    def issue(self, epoch: int, sequence: int, payload: bytes, *,
              signer: str = "a", signers=None, signed_policy_additions=None):
        self.signer = signer
        self.artifact.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        metadata = {"sequence": sequence, "sha256": digest, "size": len(payload)}
        p = {
            "schema": floor.admission.POLICY_SCHEMA,
            "release_id": floor.admission.RELEASE_ID,
            "epoch": epoch,
            "min_sequence": sequence,
            "signers": signers or [
                {"fingerprint": self.fingerprints[signer], "state": "active"}],
            "approved_artifacts": [metadata],
        }
        if signed_policy_additions:
            p.update(signed_policy_additions)
        m = {"schema": floor.admission.MANIFEST_SCHEMA,
             "release_id": floor.admission.RELEASE_ID, **metadata}
        self.policy.write_text(json.dumps(p, sort_keys=True, separators=(",", ":")))
        self.manifest.write_text(json.dumps(m, sort_keys=True, separators=(",", ":")))
        gpg(self.keys["root"], "--output", str(self.policy_sig),
            "--detach-sign", str(self.policy))
        gpg(self.keys[signer], "--output", str(self.manifest_sig),
            "--detach-sign", str(self.manifest))

    def admit(self, **overrides):
        opts = dict(
            external_root_pin=self.fingerprints["root"],
            external_epoch_floor=self.external_epoch,
            external_sequence_floor=self.external_sequence,
            root_public=self.public["root"],
            policy=self.policy, policy_signature=self.policy_sig,
            delegated_public=self.public[self.signer],
            manifest=self.manifest, manifest_signature=self.manifest_sig,
            artifact=self.artifact,
        )
        opts.update(overrides)
        db_path = opts.pop("db_path", self.db)
        return floor.admit_and_record(db_path, **opts)

    def expect_refusal(self, code, **overrides):
        with self.assertRaises(floor.Refused) as e:
            self.admit(**overrides)
        self.assertEqual(str(e.exception), code)

    def test_01_bootstrap_is_explicit_and_untrusted_missing_db_refuses(self):
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))
        with self.assertRaises(floor.Refused):
            floor.bootstrap(self.db, trusted_root_pin=self.fingerprints["root"],
                            initial_epoch=3, initial_sequence=8)
        absent = self.work / "missing.db"
        self.expect_refusal("LEDGER_MISSING_REQUIRES_EXPLICIT_BOOTSTRAP", db_path=absent)
        self.assertFalse(absent.exists())

    def test_02_signed_release_commits_and_survives_new_connection(self):
        self.assertEqual(self.admit(), floor.SUCCESS)
        observed = floor.inspect(self.db)
        self.assertEqual(observed[:3], (self.fingerprints["root"], 3, 8))
        self.assertEqual(observed[4], hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        self.assertEqual(self.admit(), floor.SUCCESS)
        self.assertEqual(floor.inspect(self.db), observed)
        # A fresh Python interpreter must recover the same committed state.
        read_code = (
            "import importlib.util,sys; from pathlib import Path; "
            "sp=importlib.util.spec_from_file_location('c3ec_child',sys.argv[1]); "
            "m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); "
            "print(m.inspect(Path(sys.argv[2]))[1:3])"
        )
        child = subprocess.run(
            [sys.executable, "-I", "-B", "-c", read_code,
             str(SOURCE), str(self.db)],
            capture_output=True, text=True, timeout=8, check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout.strip(), "(3, 8)")

    def test_03_signed_release_advances_policy_and_sequence_after_restart(self):
        self.admit()
        self.issue(4, 9, b"synthetic package 9")
        self.assertEqual(self.admit(), floor.SUCCESS)
        self.assertEqual(floor.inspect(self.db)[1:3], (4, 9))
        # Reissue an old but valid root-signed policy. The ledger refuses it.
        self.issue(3, 8, b"synthetic package 8")
        self.expect_refusal("POLICY_ROLLBACK_REFUSED")
        self.assertEqual(floor.inspect(self.db)[1:3], (4, 9))

    def test_04_same_epoch_cannot_silently_replace_signed_policy(self):
        self.admit()
        self.issue(3, 9, b"synthetic package 9")
        self.expect_refusal("EQUIVOCAL_POLICY_AT_SAME_EPOCH")
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))

    def test_05_same_sequence_cannot_be_rebound_to_other_artifact(self):
        self.admit()
        self.issue(4, 8, b"replaced package same sequence")
        self.expect_refusal("EQUIVOCAL_RELEASE_AT_SAME_SEQUENCE")
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))

    def test_06_root_signed_rotation_revokes_old_manifest_signer(self):
        self.admit()
        signers = [
            {"fingerprint": self.fingerprints["a"], "state": "revoked"},
            {"fingerprint": self.fingerprints["b"], "state": "active"},
        ]
        self.issue(4, 9, b"synthetic package 9", signer="b", signers=signers)
        self.assertEqual(self.admit(), floor.SUCCESS)
        self.assertEqual(floor.inspect(self.db)[1:3], (4, 9))
        self.issue(5, 10, b"synthetic package 10", signer="a", signers=signers)
        self.expect_refusal("CRYPTO_REFUSED_REVOKED_SIGNER")
        self.assertEqual(floor.inspect(self.db)[1:3], (4, 9))

    def test_07_different_external_root_fails_before_db_update(self):
        self.expect_refusal("CRYPTO_REFUSED_ROOT_PIN_MISMATCH",
                            external_root_pin=self.fingerprints["b"])
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))

    def test_08_tampered_signed_policy_does_not_change_checkpoint(self):
        self.admit()
        prior = floor.inspect(self.db)
        self.policy.write_text(self.policy.read_text() + " ")
        self.expect_refusal("CRYPTO_REFUSED_INVALID_DETACHED_SIGNATURE")
        self.assertEqual(floor.inspect(self.db), prior)

    def test_09_symlinked_manifest_is_rejected_even_with_valid_signature(self):
        victim = self.work / "manifest-real.json"
        self.manifest.rename(victim)
        self.manifest.symlink_to(victim)
        self.expect_refusal("UNSAFE_SNAPSHOT_INPUT")
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))

    def test_10_truncated_and_corrupted_sqlite_refuses_without_recovery(self):
        self.db.write_bytes(b"not sqlite")
        with self.assertRaises(floor.Refused):
            floor.inspect(self.db)
        with self.assertRaises(floor.Refused):
            self.admit()

    def test_11_external_newer_floor_blocks_replayed_db_snapshot(self):
        self.admit()
        old_db = self.work / "old-database-copy"
        shutil.copy2(self.db, old_db)
        self.issue(4, 9, b"synthetic package 9")
        self.admit()
        self.assertEqual(floor.inspect(self.db)[1:3], (4, 9))
        # Model a machine backup that restores the older *valid* SQLite state.
        shutil.copy2(old_db, self.db)
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))
        self.external_epoch, self.external_sequence = 4, 9
        self.issue(3, 8, b"synthetic package 8")
        self.expect_refusal("CRYPTO_REFUSED_POLICY_ROLLBACK_REFUSED")
        self.issue(4, 9, b"synthetic package 9")
        self.admit()
        self.assertEqual(floor.inspect(self.db)[1:3], (4, 9))

    def test_12_external_floor_must_not_be_missing_or_zero(self):
        self.expect_refusal("EXTERNAL_ANCHOR_INVALID", external_epoch_floor=0)
        self.expect_refusal("EXTERNAL_ANCHOR_INVALID", external_sequence_floor=0)
        self.expect_refusal("EXTERNAL_ANCHOR_INVALID", external_root_pin="")
        self.assertEqual(floor.inspect(self.db)[1:3], (3, 8))

    def test_13_uncommitted_sqlite_write_rolls_back_after_process_loss(self):
        self.admit()
        before = floor.inspect(self.db)
        # An actual child process dies while a write transaction is open.
        # SQLite must roll the journal back on the next independent opener.
        crash_code = (
            "import os,sqlite3,sys; "
            "db=sqlite3.connect(sys.argv[1],isolation_level=None); "
            "db.execute('BEGIN IMMEDIATE'); "
            "db.execute('UPDATE checkpoint SET epoch_floor=99 WHERE id=1'); "
            "os._exit(47)"
        )
        child = subprocess.run(
            [sys.executable, "-I", "-B", "-c", crash_code, str(self.db)],
            capture_output=True, text=True, timeout=8, check=False)
        self.assertEqual(child.returncode, 47, child.stderr)
        self.assertEqual(floor.inspect(self.db), before)

    def test_14_ledger_file_cannot_be_world_readable_or_symlinked(self):
        self.db.chmod(0o644)
        self.expect_refusal("UNSAFE_LEDGER_FILE")
        self.db.chmod(0o600)
        proxy = self.work / "ledger-link"
        proxy.symlink_to(self.db)
        self.expect_refusal("INVALID_LEDGER_PATH", db_path=proxy)

    def test_15_competing_updates_converge_monotonically(self):
        self.admit()
        # Produce two distinct root-signed snapshots with increasing epochs.
        self.issue(4, 9, b"synthetic package 9")
        older = self.work / "older"
        older.mkdir()
        older_set = {}
        for p in (self.policy, self.policy_sig, self.manifest, self.manifest_sig,
                  self.artifact):
            target = older / p.name
            shutil.copy2(p, target)
            older_set[p.name] = target
        self.issue(5, 10, b"synthetic package 10")
        newer = dict(policy=self.policy, policy_signature=self.policy_sig,
                     manifest=self.manifest, manifest_signature=self.manifest_sig,
                     artifact=self.artifact)
        old = dict(policy=older_set[self.policy.name],
                   policy_signature=older_set[self.policy_sig.name],
                   manifest=older_set[self.manifest.name],
                   manifest_signature=older_set[self.manifest_sig.name],
                   artifact=older_set[self.artifact.name])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.admit, **overrides)
                       for overrides in (old, newer)]
            outcomes = []
            for f in futures:
                try:
                    outcomes.append(f.result())
                except floor.Refused as e:
                    outcomes.append(str(e))
        self.assertIn(floor.SUCCESS, outcomes)
        self.assertEqual(floor.inspect(self.db)[1:3], (5, 10))

    def test_16_no_production_broker_or_host_authority_is_changed(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        source = SOURCE.read_text()
        for prohibited in ("rpm --import", "systemctl start", "secret-tool",
                           "credentialActionsEnabled = true"):
            self.assertNotIn(prohibited, source)
        for p in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eDurableFloor", p.read_text(), p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
