#!/usr/bin/env python3
"""V3c // root-only disposable Linux separate-UID high-water witness tests.

THIS TEST IS ONLY FOR AN EPHEMERAL GITHUB ACTIONS RUNNER. It creates two
synthetic UIDs' temporary directories under /tmp and deliberately triggers
process death around SQLite COMMIT. No real system user or archive is changed.
"""
from __future__ import annotations

import base64
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/trash"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from scripts.trash import archive_v3c_separate_uid_highwater_fixture as fixture
from scripts.trash import archive_v3b_signed_rollback_witness as witness
from scripts.trash.archive_v2_signed_capture import AUDIENCE, PURPOSE
import test_archive_v2_external_floor_reader as v2w


def pub(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def signed(key, claim):
    return {
        "claim": copy.deepcopy(claim),
        "signatureB64": base64.b64encode(
            key.sign(witness.canonical_claim(claim))).decode("ascii"),
    }


def child_main(mode, root, arg):
    """Drops privileges in parent BEFORE executing this child entrypoint."""
    if mode == "broker-read":
        try:
            os.open(root / fixture.DB_NAME, os.O_RDONLY)
        except PermissionError as exc:
            assert exc.errno in (errno.EACCES, errno.EPERM)
            print('{"brokerDenied":true}')
            return
        raise AssertionError("broker successfully opened authority DB")
    request = json.loads(arg)
    if mode == "initialize":
        output = fixture.initialize(root)
    elif mode == "inspect":
        output = fixture.inspect(root)
    elif mode == "record":
        pin = request["pin"]
        pin["publicKeyBytes"] = base64.b64decode(pin["publicKeyBytes"])
        output = fixture.record(
            root,
            old_envelope=request["old"],
            new_envelope=request["new"],
            pin=pin, floor=request["floor"],
            floor_signer_public_key=base64.b64decode(
                request["floorSignerPublicKey"]),
            expected_owner_id=request["expectedOwner"],
            expected_grant_sha256=request["expectedGrant"],
            crash_point=request.get("crashPoint"),
        )
    else:
        raise AssertionError("unknown fixture test command")
    print(json.dumps(output, sort_keys=True))


@unittest.skipUnless(os.name == "posix" and os.geteuid() == 0,
                     "Root-only separate UID fixture; no host execution")
class TestV3cSeparateUidAuthority(unittest.TestCase):
    def setUp(self):
        for uid in (fixture.TEST_OWNER_UID, fixture.TEST_BROKER_UID):
            try:
                pwd.getpwuid(uid)
            except KeyError:
                continue
            self.skipTest("synthetic UID already provisioned; refuse")
        self.base = Path(tempfile.mkdtemp(
            prefix=fixture.PARENT_PREFIX, dir="/tmp"))
        self.addCleanup(shutil.rmtree, self.base)
        self.base.chmod(0o711)
        self.root = self.base / "authority"
        self.broker_dir = self.base / "broker"
        self.root.mkdir(mode=0o700)
        self.broker_dir.mkdir(mode=0o700)
        os.chown(self.root, fixture.TEST_OWNER_UID, fixture.TEST_OWNER_UID)
        os.chown(self.broker_dir, fixture.TEST_BROKER_UID,
                 fixture.TEST_BROKER_UID)
        self.root.chmod(0o700)
        self.broker_dir.chmod(0o700)
        # V2w real disposable signed floor + V2s signed release history.
        v = v2w.ReadOnlyExternalFloorV2wTests("runTest")
        v.setUp()
        self.addCleanup(v.doCleanups)
        self.floor = v.verify()
        self.floor_signer = v.pin["publicKeyBytes"]
        self.grant = v.previous.grant_sha
        self.owner = self.floor["ownerId"]
        self.signer = Ed25519PrivateKey.generate()
        self.pin = {
            "rootKeyId": "v3c-independent-ci-signer",
            "publicKeyBytes": pub(self.signer),
            "origin": witness.PIN_ORIGIN,
        }
        self.claim = {
            "schema": witness.KIND, "audience": AUDIENCE,
            "purpose": PURPOSE, "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": self.pin["rootKeyId"],
            "ownerId": self.owner, "grantSha256": self.grant,
            "epoch": self.floor["epoch"],
            "floorSequence": self.floor["sequence"],
            "floorSha256": self.floor["externalFloorSha256"],
            "releaseSha256": self.floor["releaseSha256"],
            "witnessSequence": 1,
            "previousWitnessSha256": "", "revoked": False,
        }
        self.first = signed(self.signer, self.claim)
        init_rc, init_result = self.run_child("initialize")
        self.assertEqual(init_rc, 0, "V3C child initialization failed: " + str(init_result))
        self.assertDenied(init_result)
        self.assertEqual(self.head()["sequence"], 0)

    def run_child(self, mode, data=None, *, as_broker=False, crash=None):
        def identity():
            os.umask(0o077)
            os.setgroups([])
            uid = (fixture.TEST_BROKER_UID if as_broker
                   else fixture.TEST_OWNER_UID)
            os.setgid(uid)
            os.setuid(uid)

        request = {}
        if mode == "record":
            request = {
                "pin": {
                    "rootKeyId": self.pin["rootKeyId"],
                    "publicKeyBytes": base64.b64encode(
                        self.pin["publicKeyBytes"]).decode("ascii"),
                    "origin": self.pin["origin"],
                },
                "old": data[0],
                "new": data[1],
                "floor": self.floor,
                "floorSignerPublicKey": base64.b64encode(
                    self.floor_signer).decode("ascii"),
                "expectedOwner": self.owner,
                "expectedGrant": self.grant,
                "crashPoint": crash,
            }
        result = subprocess.run(
            [sys.executable, "-B", "-I", str(Path(__file__).resolve()),
             "child", mode, str(self.root), json.dumps(request)],
            capture_output=True, text=True, timeout=20, preexec_fn=identity)
        if result.returncode == 0:
            return 0, json.loads(result.stdout)
        return result.returncode, result.stderr

    def head(self):
        rc, output = self.run_child("inspect")
        self.assertEqual(rc, 0, output)
        self.assertDenied(output)
        return output

    def assertDenied(self, result):
        self.assertFalse(result["independentAnchorAuthenticated"])
        self.assertFalse(result[
            "externallyProtectedMonotonicAuthorityVerified"])
        self.assertFalse(result["authorityOwnerRollbackDetectable"])
        self.assertFalse(result["trustedClockVerified"])
        self.assertFalse(result["sourceOwnerApprovalVerified"])
        for name in (
            "captureAllowed", "productionAllowed", "restoreAllowed",
            "burnAllowed", "automaticRetryAllowed", "deleteOriginalAllowed",
        ):
            self.assertIs(result[name], False, name)
        self.assertEqual(result["safeActions"], [])

    def advance(self, old=None, *, revoke=False):
        previous = self.first if old is None else old
        claim = copy.deepcopy(previous["claim"])
        claim["witnessSequence"] += 1
        claim["previousWitnessSha256"] = hashlib.sha256(
            witness.canonical_claim(previous["claim"])).hexdigest()
        claim["revoked"] = revoke
        return signed(self.signer, claim)

    def record(self, old, new, *, crash=None):
        return self.run_child("record", (old, new), crash=crash)

    def test_distinct_kernel_uid_and_broker_access_denied(self):
        self.assertEqual(self.root.lstat().st_uid, fixture.TEST_OWNER_UID)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(self.broker_dir.lstat().st_uid,
                         fixture.TEST_BROKER_UID)
        self.assertEqual(self.run_child("broker-read", as_broker=True),
                         (0, {"brokerDenied": True}))
        rc, detail = self.run_child("inspect", as_broker=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("V3C_TEST_UID_OR_PATH_REFUSED", detail)

    def test_signed_initial_and_advanced_commit_is_deny_only(self):
        rc, initial = self.record(None, self.first)
        self.assertEqual(rc, 0, initial)
        self.assertEqual(initial["sequence"], 1)
        self.assertDenied(initial)
        nxt = self.advance()
        rc, result = self.record(self.first, nxt)
        self.assertEqual(rc, 0, result)
        self.assertEqual(result["sequence"], 2)
        self.assertDenied(result)
        self.assertEqual(self.head()["sequence"], 2)
        info = (self.root / fixture.DB_NAME).lstat()
        self.assertEqual(info.st_uid, fixture.TEST_OWNER_UID)
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
        self.assertEqual(info.st_nlink, 1)

    def test_stale_predecessor_fork_and_replay_refuse(self):
        self.assertEqual(self.record(None, self.first)[0], 0)
        later = self.advance()
        self.assertEqual(self.record(self.first, later)[0], 0)
        # A duplicate identical reply is observable without double insert.
        rc, result = self.record(self.first, later)
        self.assertEqual(rc, 0, result)
        self.assertEqual(result["state"],
                         "TEST_IDENTICAL_COMMIT_OBSERVED_DENY_ONLY")
        self.assertEqual(self.record(None, self.first)[0], 1)
        fork_claim = copy.deepcopy(later["claim"])
        fork_claim["revoked"] = True
        fork = signed(self.signer, fork_claim)
        self.assertNotEqual(self.record(self.first, fork)[0], 0)
        gap_claim = copy.deepcopy(later["claim"])
        gap_claim["witnessSequence"] = 4
        gap = signed(self.signer, gap_claim)
        self.assertNotEqual(self.record(later, gap)[0], 0)
        self.assertEqual(self.head()["sequence"], 2)

    def test_signed_revoke_can_advance_but_unrevoke_refuses(self):
        self.assertEqual(self.record(None, self.first)[0], 0)
        revoked = self.advance(revoke=True)
        rc, out = self.record(self.first, revoked)
        self.assertEqual(rc, 0, out)
        self.assertDenied(out)
        new = self.advance(old=revoked, revoke=False)
        self.assertNotEqual(self.record(revoked, new)[0], 0)
        self.assertEqual(self.head()["sequence"], 2)

    def test_crash_before_commit_rolls_back_and_after_commit_survives(self):
        self.assertEqual(self.record(None, self.first)[0], 0)
        later = self.advance()
        rc, info = self.record(self.first, later, crash="before_commit")
        self.assertEqual(rc, 93, info)
        self.assertEqual(self.head()["sequence"], 1)
        rc, info = self.record(self.first, later, crash="after_commit")
        self.assertEqual(rc, 94, info)
        self.assertEqual(self.head()["sequence"], 2)
        rc, out = self.record(self.first, later)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["state"],
                         "TEST_IDENTICAL_COMMIT_OBSERVED_DENY_ONLY")

    def test_invalid_signature_and_wrong_grant_refuse_without_writing(self):
        foreign = Ed25519PrivateKey.generate()
        bad = signed(foreign, self.claim)
        self.assertNotEqual(self.record(None, bad)[0], 0)
        changed = copy.deepcopy(self.claim)
        changed["grantSha256"] = "a" * 64
        self.assertNotEqual(self.record(None,
                                        signed(self.signer, changed))[0], 0)
        self.assertEqual(self.head()["sequence"], 0)

    def test_authority_owner_rollback_not_protected_externally(self):
        # A root/authority compromise can restore an older VALID DB.
        # The independent, immutable/monotonic anchor is still MISSING.
        self.assertEqual(self.record(None, self.first)[0], 0)
        old_bytes = (self.root / fixture.DB_NAME).read_bytes()
        later = self.advance()
        self.assertEqual(self.record(self.first, later)[0], 0)
        self.assertEqual(self.head()["sequence"], 2)
        dbfile = self.root / fixture.DB_NAME
        # Root is deliberately able to replace the entire fixture.
        newfile = self.root / "restored-old-head.sqlite3"
        newfile.write_bytes(old_bytes)
        os.chown(newfile, fixture.TEST_OWNER_UID, fixture.TEST_OWNER_UID)
        newfile.chmod(0o600)
        os.replace(newfile, dbfile)
        back = self.head()
        self.assertEqual(back["sequence"], 1)
        self.assertFalse(back["externallyProtectedMonotonicAuthorityVerified"])
        self.assertFalse(back["authorityOwnerRollbackDetectable"])
        # The broker cannot even read the compromised authority file.
        self.assertEqual(self.run_child("broker-read", as_broker=True),
                         (0, {"brokerDenied": True}))

    def test_symlink_or_insecure_database_refuses(self):
        target = self.root / fixture.DB_NAME
        original = self.root / "saved-original.sqlite3"
        target.rename(original)
        target.symlink_to(original)
        rc, err = self.run_child("inspect")
        self.assertNotEqual(rc, 0)
        target.unlink()
        original.rename(target)
        target.chmod(0o666)
        rc, err = self.run_child("inspect")
        self.assertNotEqual(rc, 0)
        target.chmod(0o600)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "child":
        try:
            child_main(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
        except fixture.FixtureRefusal as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1)
    elif len(sys.argv) == 1:
        unittest.main()
    else:
        raise SystemExit("V3c root-only CI fixture requires test args")
