#!/usr/bin/env python3
"""C3e-Z: signed synthetic Identity release bound to C3e-Y deny-only witness."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


Z=_load("c3ez_composition",HERE/"C3eZReleaseBoundHostEvidence.py")
YTEST=_load("c3ez_yfixture",ROOT/"tests/connections/test_connections_c3ey_signed_host_challenge.py")


class C3eZReleaseBoundIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform!="linux" or os.geteuid()!=0 or os.environ.get("GITHUB_ACTIONS")!="true":
            raise RuntimeError("C3EZ_DISPOSABLE_ROOT_GITHUB_CI_ONLY")

    def setUp(self):
        self.y=YTEST.C3eYSignedHostChallengeTests(
            "test_01_complete_signed_record_and_four_denials_consume_once_without_auth")
        self.y.setUp()
        self.addCleanup(self.y.doCleanups)
        self.root_key=Ed25519PrivateKey.generate()
        self.files={path:hashlib.sha256(("CI-FILE:"+path).encode()).hexdigest()
                    for path in Z.I.FILES}
        self.files[Z.GATEWAY_ENTRYPOINT]=self.y.pair.expected["entrypointSha256"]
        self.doc={
            "schema":Z.I.SCHEMA,"role":Z.I.ROLE,"package":Z.I.PACKAGE,
            "unit":Z.I.UNIT,"epoch":self.y.epoch,"sequence":self.y.sequence,
            "rpmSha256":self.y.pair.expected["rpmSha256"],
            "receiptKeySha256":hashlib.sha256(Z.Y._public_bytes(
                self.y.pair.key.public_key())).hexdigest(),
            "files":dict(self.files),
        }
        self._sign_release()

    def _sign_release(self):
        self.raw=Z.I._canonical(self.doc)
        self.signature=self.root_key.sign(Z.I.DOMAIN+self.raw)

    def args(self,**changes):
        params={
            **self.y.params(),
            "signed_release":self.raw,
            "release_signature":self.signature,
            "independently_pinned_release_root":self.root_key.public_key(),
            "independently_measured_files":self.files,
        }
        params.update(changes)
        return params

    def verify(self,**changes):
        return Z.inspect_release_and_consume(**self.args(**changes))

    def refused(self,**changes):
        with self.assertRaises(Z.Refused):
            self.verify(**changes)

    def state(self):
        return self.y.state()

    def test_01_valid_release_and_signed_host_replay_path_only_yields_ci_diagnostics(self):
        result=self.verify()
        self.assertEqual(result["schema"],Z.SCHEMA)
        self.assertIs(result["releaseSourceAndRuntimePinsMatchedInCI"],True)
        self.assertIs(result["releaseReceiptSignerMatchedInCI"],True)
        self.assertIs(result["fullRecordChallengeConsumedInRootLocalCI"],True)
        for key in (*Z.NEGATIVE,*Z.Y.X.NEGATIVE):
            self.assertIs(result[key],False)
        self.assertEqual(self.state()[0],"consumed")

    def test_02_wrong_release_root_preserves_preissued_challenge(self):
        self.refused(independently_pinned_release_root=Ed25519PrivateKey.generate().public_key())
        self.assertEqual(self.state(),("issued",None))
        self.assertIs(self.verify()["fullRecordChallengeConsumedInRootLocalCI"],True)

    def test_03_wrong_receipt_key_or_witness_key_preserves_nonce(self):
        self.refused(independently_pinned_receipt_key=Ed25519PrivateKey.generate().public_key())
        self.refused(independently_pinned_witness_key=Ed25519PrivateKey.generate().public_key())
        self.assertEqual(self.state(),("issued",None))

    def test_04_same_key_used_for_multiple_roles_refused(self):
        self.refused(independently_pinned_release_root=self.y.witness_key.public_key())
        self.refused(independently_pinned_release_root=self.y.pair.key.public_key())
        self.assertEqual(self.state(),("issued",None))

    def test_05_modified_release_signature_or_bytes_refused(self):
        self.refused(release_signature=b"\x00"*64)
        self.refused(signed_release=self.raw+b" ")
        self.refused(signed_release=self.raw+b"\n")
        self.refused(signed_release=self.raw.replace(b'"schema":',
                                                   b'"schema":"other","schema":',1))
        self.assertEqual(self.state(),("issued",None))

    def test_06_release_rpm_digest_matches_full_host_snapshot(self):
        self.doc["rpmSha256"]="f"*64
        self._sign_release()
        self.refused()
        self.assertEqual(self.state(),("issued",None))

    def test_07_release_entrypoint_digest_must_match_runtime_pin(self):
        self.files[Z.GATEWAY_ENTRYPOINT]="f"*64
        self.doc["files"]=dict(self.files)
        self._sign_release()
        self.refused()
        self.assertEqual(self.state(),("issued",None))

    def test_08_signed_release_extra_or_missing_module_refused(self):
        path=Z.I.UNIT_PATH
        self.doc["files"].pop(path)
        self._sign_release()
        self.refused()
        self.assertEqual(self.state(),("issued",None))

    def test_09_signed_release_wrong_service_or_role_refused(self):
        for field,value in (("unit","different.service"),
                            ("role","postapollo.connections.c4d-status"),
                            ("package","unknown-package"),
                            ("schema","different-release-schema")):
            with self.subTest(field=field):
                original=self.doc[field]
                self.doc[field]=value
                self._sign_release()
                self.refused()
                self.doc[field]=original
        self.assertEqual(self.state(),("issued",None))

    def test_10_signed_release_epoch_and_sequence_must_equal_issued_challenge(self):
        for field in ("epoch","sequence"):
            with self.subTest(field=field):
                original=self.doc[field]
                self.doc[field]=original+1
                self._sign_release()
                self.refused()
                self.doc[field]=original
        self.assertEqual(self.state(),("issued",None))

    def test_11_caller_release_floor_cannot_be_changed_on_valid_evidence(self):
        self.refused(expected_release_epoch=self.y.epoch+1)
        self.refused(expected_release_sequence=self.y.sequence+1)
        self.refused(expected_release_epoch=True)
        self.assertEqual(self.state(),("issued",None))

    def test_12_mismatched_independent_source_files_or_wrong_roster_refused(self):
        self.refused(independently_measured_files={
            **self.files,Z.I.UNIT_PATH:"f"*64})
        missing=dict(self.files)
        missing.pop(Z.I.UNIT_PATH)
        self.refused(independently_measured_files=missing)
        self.refused(independently_measured_files={**self.files,"/tmp/unknown":"f"*64})
        self.assertEqual(self.state(),("issued",None))

    def test_13_caller_modified_running_pid_and_executable_hash_refused(self):
        self.refused(independently_measured={**self.y.pair.expected,"pid":1489})
        self.refused(independently_measured={
            **self.y.pair.expected,"entrypointSha256":"f"*64})
        self.assertEqual(self.state(),("issued",None))

    def test_14_runtime_witness_signature_invalid_preserves_challenge(self):
        self.refused(witness_signature=b"\x00"*64)
        self.refused(signed_statement=self.y.statement+b"\n")
        self.assertEqual(self.state(),("issued",None))

    def test_15_complete_signed_release_valid_but_host_evidence_replaced_refused(self):
        forged=self.y.pair.records[0]["before"]
        forged["startTicks"]+=1
        self.refused()
        self.assertEqual(self.state(),("issued",None))

    def test_16_challenge_consumption_is_single_use_across_restart(self):
        self.verify()
        self.y.issuer=Z.Y.DisposableCIChallengeIssuer(self.y.root)
        self.refused()
        self.assertEqual(self.state()[0],"consumed")

    def test_17_simultaneous_duplicate_requests_allow_one_commit(self):
        def attempt(_):
            try:
                return self.verify()
            except Z.Refused as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,range(2)))
        self.assertEqual(sum(type(x) is dict for x in results),1)
        self.assertEqual(self.state()[0],"consumed")

    def test_18_original_caller_pin_dicts_frozen_before_y_verification(self):
        original=Z.I.assess_synthetic_release
        pins=dict(self.y.pair.expected)
        files=dict(self.files)

        def change_caller_after_release(*args,**kwargs):
            result=original(*args,**kwargs)
            self.y.pair.expected["pid"]=99999
            self.files[Z.I.UNIT_PATH]="f"*64
            self.assertEqual(kwargs["independently_measured_files"],files)
            return result

        with mock.patch.object(Z.I,"assess_synthetic_release",
                               side_effect=change_caller_after_release):
            self.assertIs(self.verify()["fullRecordChallengeConsumedInRootLocalCI"],True)
        self.assertEqual(self.state()[0],"consumed")
        self.assertNotEqual(self.y.pair.expected,pins)

    def test_19_malformed_pin_types_and_absent_ledger_refused(self):
        self.refused(independently_measured_files=[])
        self.refused(independently_measured={**self.y.pair.expected,"uid":True})
        (self.y.root/Z.Y.DB_FILE).unlink()
        self.refused()

    def test_20_release_authority_flags_remain_hard_false(self):
        source=(HERE/"C3eZReleaseBoundHostEvidence.py").read_text()
        for phrase in ("socket.socket(", "subprocess.run(", "systemctl start",
                       "rpm-ostree install", "HostBoundary.authenticated(",
                       "canBeginSignIn\": True", "productionAuthority\": True"):
            self.assertNotIn(phrase,source)
        self.assertTrue(all(flag is False for flag in Z.NEGATIVE.values()))
        self.assertTrue(all(flag is False for flag in Z.Y.X.NEGATIVE.values()))
        self.assertIn("**Y.X.NEGATIVE",source)


if __name__=="__main__":
    unittest.main(verbosity=2)
