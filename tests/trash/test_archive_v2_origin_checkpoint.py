"""V2t test-only signed checkpoint and Linux cgroup origin observations.

Uses V2s in-memory root/source signers, a second in-memory checkpoint
signer, a temporary AF_UNIX socket and private synthetic SQLite stores.
"""
import base64
import hashlib
import io
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

import test_archive_v2_service_release_history as base_release
from scripts.trash.archive_v2_origin_checkpoint import (
    SCHEMA, FixtureOriginError, _read_cgroup_v2, canonical_checkpoint,
    measure_fixture_origin, verify_fixture_checkpoint,
)
from scripts.trash.archive_v2_signed_capture import AUDIENCE, PURPOSE
from scripts.trash.archive_v2_service_release_history import (
    canonical_release,
)

NOW = 1760000500000


def pub(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class SourceOriginCheckpointV2tTests(unittest.TestCase):
    def setUp(self):
        self.pre = base_release.SignedServiceReleaseV2sTests("runTest")
        self.pre.setUp()
        self.addCleanup(self.pre.doCleanups)
        self.f = self.pre.fixture
        self.checkpoint_key = Ed25519PrivateKey.generate()
        self.checkpoint_root = {
            "rootKeyId":"fixture-checkpoint-root",
            "publicKeyBytes":pub(self.checkpoint_key),
            "origin":"EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.origin_policy = {
            "origin":"TEST_FIXTURE_ONLY",
            "ownerId":"demo-scrape",
            "expectedUid":os.getuid(),
            "expectedGid":os.getgid(),
            "expectedCgroupV2":_read_cgroup_v2(os.getpid()),
        }
        self.checkpoint_fields = {
            "schema":SCHEMA, "audience":AUDIENCE, "purpose":PURPOSE,
            "policyOrigin":"TEST_FIXTURE_ONLY",
            "rootKeyId":"fixture-checkpoint-root",
            "ownerId":"demo-scrape",
            "sequence":1,
            "releaseSha256":hashlib.sha256(
                canonical_release(self.pre.release)).hexdigest(),
            "grantSha256":self.pre.grant_sha,
            "issuedAtMs":1760000400000,
            "validFromMs":1760000400000,
            "validUntilMs":1760000600000,
        }

    def signed_checkpoint(self, fields=None, *, key=None):
        fields = self.checkpoint_fields if fields is None else fields
        key = self.checkpoint_key if key is None else key
        return {"checkpoint":fields,"signatureB64":base64.b64encode(
            key.sign(canonical_checkpoint(fields))).decode("ascii")}

    def send(self, *, checkpoint=None, origin=None, root=None, release=None,
             history=None, sign_service_grant=None):
        return self.f.send(
            signed_service_grant=(
                self.pre.grant if sign_service_grant is None
                else sign_service_grant),
            signed_service_release=(
                self.pre.signed() if release is None else release),
            service_release_history=(
                self.pre.history if history is None else history),
            origin_policy=(
                self.origin_policy if origin is None else origin),
            signed_checkpoint=(
                self.signed_checkpoint() if checkpoint is None else checkpoint),
            checkpoint_root=(
                self.checkpoint_root if root is None else root))

    def counts(self):
        return self.f.ledger.test_copy_status("demo-scrape")

    def test_kernel_cgroup_and_second_root_checkpoint_commit_both_witnesses(self):
        self.pre.enroll()
        matched = verify_fixture_checkpoint(
            self.signed_checkpoint(),self.checkpoint_root,
            history=self.pre.history,signed_release=self.pre.signed(),
            release_root=self.f.trust_root,owner_id="demo-scrape",
            grant_sha256=self.pre.grant_sha,now_ms=NOW)
        self.assertTrue(matched["checkpointSignatureVerified"])
        self.assertFalse(matched["independentAnchorVerified"])
        reply=self.send()
        self.assertTrue(reply["ok"], reply)
        self.assertTrue(reply["cgroupObservedBeforeCommit"])
        self.assertTrue(reply["externalCheckpointChecked"])
        self.assertFalse(reply["systemdUnitVerified"])
        for flag in ("sourceProcessVerified","archiveCopyAuthorized",
                     "captureAllowed","productionAllowed","burnAllowed",
                     "restoreAllowed"):
            self.assertFalse(reply[flag])
        row=self.f.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)
        self.assertEqual(row["originWitnessSha256"],
                         reply["originWitnessSha256"])
        self.assertEqual(row["checkpointSha256"],
                         reply["checkpointSha256"])
        self.assertTrue(row["payloadIntegrityVerified"])
        self.assertEqual(self.counts()["testCopies"],1)
        self.assertFalse((self.f.root/"trashpp-archive-v2.sqlite3").exists())

    def test_checkpoint_wrong_signer_refused_before_nonce(self):
        self.pre.enroll()
        forged=self.signed_checkpoint(key=Ed25519PrivateKey.generate())
        reply=self.send(checkpoint=forged)
        self.assertEqual(reply["error"],"CHECKPOINT_SIGNATURE_REFUSED")
        self.assertEqual(self.counts()["consumedNonces"],0)

    def test_checkpoint_root_must_be_independent_of_release_root(self):
        self.pre.enroll()
        root=dict(self.f.trust_root)
        reply=self.send(root=root)
        self.assertEqual(reply["error"],"CHECKPOINT_ROOT_MISMATCH")
        # An independently provided key with identical public bytes is
        # explicitly forbidden, even if its key label happens to match.
        root=dict(self.checkpoint_root,
                  publicKeyBytes=self.f.trust_root["publicKeyBytes"])
        reply=self.send(root=root)
        self.assertEqual(reply["error"],"CHECKPOINT_ROOT_NOT_DISTINCT")
        self.assertEqual(self.counts()["consumedNonces"],0)

    def test_checkpoint_stale_after_new_release_even_if_current_release_valid(self):
        self.pre.enroll()
        second=self.pre.next_release(self.pre.release)
        self.pre.enroll(self.pre.signed(second))
        reply=self.send(release=self.pre.signed(second))
        self.assertEqual(reply["error"],"CHECKPOINT_STALE_OR_CHANGED")
        self.assertEqual(self.counts()["testCopies"],0)

    def test_checkpoint_owner_and_grant_binding_refused(self):
        self.pre.enroll()
        wrong=dict(self.checkpoint_fields,grantSha256="f"*64)
        reply=self.send(checkpoint=self.signed_checkpoint(wrong))
        self.assertEqual(reply["error"],"CHECKPOINT_BINDING_MISMATCH")
        wrong=dict(self.checkpoint_fields,ownerId="weather-events")
        reply=self.send(checkpoint=self.signed_checkpoint(wrong))
        self.assertEqual(reply["error"],"CHECKPOINT_BINDING_MISMATCH")
        self.assertEqual(self.counts()["consumedNonces"],0)

    def test_missing_release_history_or_checkpoint_root_refused(self):
        self.pre.enroll()
        r=self.f.send(
            signed_service_grant=self.pre.grant,
            signed_service_release=self.pre.signed(),
            service_release_history=self.pre.history,
            signed_checkpoint=self.signed_checkpoint(),
            origin_policy=self.origin_policy)
        self.assertEqual(r["error"],"CHECKPOINT_COMPONENTS_REQUIRED")
        r=self.f.send(signed_service_grant=self.pre.grant,
                      signed_checkpoint=self.signed_checkpoint(),
                      checkpoint_root=self.checkpoint_root)
        self.assertEqual(r["error"],"CHECKPOINT_COMPONENTS_REQUIRED")
        self.assertEqual(self.counts()["testCopies"],0)

    def test_cgroup_policy_mismatch_refused(self):
        self.pre.enroll()
        origin=dict(self.origin_policy,expectedCgroupV2="/different-fixture")
        reply=self.send(origin=origin)
        self.assertEqual(reply["error"],"ORIGIN_CGROUP_MISMATCH")
        self.assertEqual(self.counts()["consumedNonces"],0)

    def test_wrong_cgroup_owner_or_uid_and_untrusted_policy_refused(self):
        self.pre.enroll()
        policies=[
            (dict(self.origin_policy,ownerId="weather-events"),
             "ORIGIN_POLICY_MISMATCH"),
            (dict(self.origin_policy,expectedUid=os.getuid()+1),
             "ORIGIN_POLICY_MISMATCH"),
            (dict(self.origin_policy,origin="PRODUCTION"),
             "ORIGIN_TRUST_NOT_PROVISIONED"),
        ]
        for policy,code in policies:
            self.assertEqual(self.send(origin=policy)["error"],code)
        self.assertEqual(self.counts()["testCopies"],0)

    def test_legacy_v1_cgroup_and_relative_path_fail_closed(self):
        with patch("builtins.open",return_value=io.BytesIO(
                b"2:cpu:/user.slice/test.service\n")):
            with self.assertRaisesRegex(FixtureOriginError,
                                        "ORIGIN_CGROUP_UNSUPPORTED"):
                _read_cgroup_v2(os.getpid())
        with patch("builtins.open",return_value=io.BytesIO(
                b"0::../../escape\n")):
            with self.assertRaisesRegex(FixtureOriginError,
                                        "ORIGIN_CGROUP_INVALID"):
                _read_cgroup_v2(os.getpid())
        with patch("builtins.open",return_value=io.BytesIO(
                b"0::/\n0::/again\n")):
            with self.assertRaisesRegex(FixtureOriginError,
                                        "ORIGIN_CGROUP_UNSUPPORTED"):
                _read_cgroup_v2(os.getpid())

    def test_unsupported_cgroup_member_refused_before_fixture_copy(self):
        self.pre.enroll()
        with patch("scripts.trash.archive_v2_origin_checkpoint._read_cgroup_v2",
                   side_effect=FixtureOriginError("ORIGIN_CGROUP_UNSUPPORTED")):
            result=self.send()
        self.assertEqual(result["error"],"ORIGIN_CGROUP_UNSUPPORTED")
        self.assertEqual(self.counts()["consumedNonces"],0)

    def test_cgroup_membership_changes_before_final_guard_rollback(self):
        self.pre.enroll()
        original=measure_fixture_origin
        calls=[]
        def changed(*args,**kwargs):
            calls.append(True)
            if len(calls)==2:
                raise FixtureOriginError("ORIGIN_CGROUP_MISMATCH")
            return original(*args,**kwargs)
        with patch("scripts.trash.archive_v2_fixture_socket."
                   "measure_fixture_origin",side_effect=changed):
            result=self.send()
        self.assertEqual(result["error"],"ORIGIN_CGROUP_MISMATCH")
        self.assertGreaterEqual(len(calls),2)
        self.assertEqual(self.counts()["testCopies"],0)
        self.assertEqual(self.counts()["consumedNonces"],0)

    def test_checkpoint_release_changes_before_final_commit_rollback(self):
        self.pre.enroll()
        second=self.pre.next_release(self.pre.release)
        original=verify_fixture_checkpoint
        calls=[]
        def rotate(*args,**kwargs):
            calls.append(True)
            if len(calls)==2:
                self.pre.enroll(self.pre.signed(second))
            return original(*args,**kwargs)
        with patch("scripts.trash.archive_v2_fixture_socket."
                   "verify_fixture_checkpoint",side_effect=rotate):
            result=self.send()
        self.assertEqual(result["error"],"RELEASE_STALE_OR_CHANGED")
        self.assertGreaterEqual(len(calls),2)
        self.assertEqual(self.counts()["testCopies"],0)
        self.assertEqual(self.counts()["consumedNonces"],0)
        self.assertEqual(self.pre.history.status("demo-scrape")["sequence"],2)

    def test_invalid_checkpoint_schema_scope_and_expiry_refused(self):
        for changed,code in (
            ({"schema":"unsupported"},"CHECKPOINT_SCOPE_INVALID"),
            ({"purpose":"burn"},"CHECKPOINT_SCOPE_INVALID"),
            ({"ownerId":"hospital"},"CHECKPOINT_FIELDS_INVALID"),
            ({"sequence":True},"CHECKPOINT_FIELDS_INVALID"),
            ({"releaseSha256":"bad"},"CHECKPOINT_FIELDS_INVALID"),
            ({"validUntilMs":1760200000000},"CHECKPOINT_TIME_INVALID"),
            ({"anotherField":1},"CHECKPOINT_SCHEMA_INVALID"),
        ):
            with self.assertRaisesRegex(FixtureOriginError,code):
                canonical_checkpoint(dict(self.checkpoint_fields,**changed))

    def test_legacy_v2s_synthetic_receipt_does_not_claim_v2t_checks(self):
        self.pre.enroll()
        reply=self.f.send(
            signed_service_grant=self.pre.grant,
            signed_service_release=self.pre.signed(),
            service_release_history=self.pre.history)
        self.assertTrue(reply["ok"],reply)
        self.assertFalse(reply["cgroupObservedBeforeCommit"])
        self.assertFalse(reply["externalCheckpointChecked"])
        row=self.f.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)
        self.assertEqual(row["originWitnessSha256"],"")
        self.assertEqual(row["checkpointSha256"],"")

    def test_no_runtime_issuer_systemd_or_live_archive_service(self):
        from scripts.trash import archive_v2_origin_checkpoint as module
        source=Path(module.__file__).read_text("utf-8")
        self.assertNotIn("Ed25519PrivateKey",source)
        self.assertNotIn("ArchiveStore(",source)
        self.assertNotIn("Quickshell.dataDir",source)
        self.assertNotIn(".bind(",source)
        self.assertNotIn(".listen(",source)
        self.assertFalse(hasattr(module,"main"))


if __name__=="__main__":
    unittest.main()
