#!/usr/bin/env python3
"""Purpose-separated TimeW and Hospital signing: source-only hostile CI."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

if (sys.platform != "linux" or os.environ.get("CI") != "true"
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or not Path(os.environ.get("RUNNER_TEMP", "/nonexistent")).is_dir()):
    raise SystemExit("C3E_PURPOSE_PROOF_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_integration"))
sys.path.insert(0, str(ROOT / "tests/connections"))
sys.path.insert(0, str(ROOT / "hospital-source/bin"))

import ConnectionsPurposeBoundEvidencePreflight as P
import test_connections_hospital_staffing_receipt_identity_preflight as F


def fp(private):
    return hashlib.sha256(private.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw)).hexdigest()


def identity():
    return str(uuid.uuid4())


class TwoDomainProofTests(unittest.TestCase):
    def setUp(self):
        self.k_time = Ed25519PrivateKey.generate()
        self.k_hospital = Ed25519PrivateKey.generate()
        self.k_foreign = Ed25519PrivateKey.generate()
        self.host = "ci-untrusted-host"
        self.now = 1763658000000
        self.time_challenge = b"T" * 32
        self.h_challenge = b"H" * 32
        self.selection = {
            "schema": P.TimeW.ScopeA.SCHEMA,
            "audience": P.TimeW.ScopeA.AUDIENCE,
            "challenge_sha256": hashlib.sha256(self.time_challenge).hexdigest(),
            "selection_id": identity(), "compositor_epoch": identity(),
            "surface_lifetime_id": identity(), "surface_generation": 1,
            "live_con_id": 34, "app_id": "brave", "output": "DP-3",
            "workspace": "1", "floating": True, "fullscreen_mode": 0,
            "before_rect": {"x": 4, "y": 5, "width": 500, "height": 400},
            "target_rect": {"x": 20, "y": 40, "width": 650, "height": 430},
            "checkpoint_id": identity(), "window_key": identity(),
            "seat_id": "seat0", "session_id": identity(),
            "issued_ms": self.now, "expires_ms": self.now + 3000,
        }
        f = F.StaffingReceiptIdentityTests(
            "test_01_actual_hospital_pinned_source_protocols")
        f.setUp()
        self.original, self.prepared, self.commit = (
            f.original_raw, f.prepared_raw, f.commit_raw)
        self.query_id = identity()
        self.hquery = P.Hospital.candidate_query_ci_only(
            original_prepare_raw=self.original, prepared_raw=self.prepared,
            commit_raw=self.commit, query_id=self.query_id,
            challenge=self.h_challenge, issued_ms=self.now,
            expires_ms=self.now + 3000, now_ms=self.now
        )["candidateQueryRawForTestOnly"]
        self.time_source = P.TimeW.make_packet_ci_only(
            selection=self.selection, challenge=self.time_challenge,
            now_ms=self.now)

    def doc(self, kind, *, key=None, changed=None):
        private = key or (self.k_time if kind == "time" else self.k_hospital)
        purpose, audience, source, challenge, domain = (
            (P.TIMEW_PURPOSE, P.TIMEW_AUDIENCE,
             self.time_source, self.time_challenge, P.TIMEW_DOMAIN)
            if kind == "time" else
            (P.HOSPITAL_PURPOSE, P.HOSPITAL_AUDIENCE,
             self.hquery, self.h_challenge, P.HOSPITAL_DOMAIN))
        obj = {
            "schema": P.SCHEMA, "purpose": purpose, "audience": audience,
            "sourceSha256": hashlib.sha256(source).hexdigest(),
            "challengeSha256": hashlib.sha256(challenge).hexdigest(),
            "signerKeySha256": fp(private), "hostId": self.host,
            "releaseEpoch": 3, "releaseSequence": 5,
            "issuedMs": self.now, "expiresMs": self.now+1000,
        }
        obj.update(changed or {})
        raw = P._canonical(obj)
        return raw, private.sign(domain + raw)

    def params(self, kind, **overrides):
        raw, sig = self.doc(kind)
        private = self.k_time if kind == "time" else self.k_hospital
        foreign = self.k_hospital if kind == "time" else self.k_time
        result = {
            "signed_proof_raw": raw, "signature": sig,
            "independently_pinned_signer_key": private.public_key(),
            "separately_expected_signer_sha256": fp(private),
            "separately_expected_other_role_key_sha256": fp(foreign),
            "revoked_signer_sha256": (),
            "expected_host_id": self.host,
            "minimum_release_epoch": 3,
            "minimum_release_sequence": 5,
            "now_ms": self.now,
        }
        result.update(overrides)
        return result

    def call(self, kind, *, selection=None, challenge=None,
             hquery=None, **params):
        args = self.params(kind, **params)
        if kind == "time":
            return P.inspect_timew_scope_a_ci_only(
                selection=self.selection if selection is None else selection,
                challenge=self.time_challenge if challenge is None else challenge,
                **args)
        return P.inspect_hospital_recover_ci_only(
            original_prepare_raw=self.original, prepared_raw=self.prepared,
            commit_raw=self.commit,
            candidate_query_raw=self.hquery if hquery is None else hquery,
            expected_query_id=self.query_id,
            expected_challenge=self.h_challenge if challenge is None else challenge,
            **args)

    def refused(self, kind, match, **opts):
        with self.assertRaisesRegex(P.ScopedEvidenceHold, match):
            self.call(kind, **opts)

    def test_01_both_domains_verify_test_signature_but_no_authority(self):
        for kind in ("time", "hospital"):
            with self.subTest(kind=kind):
                result = self.call(kind)
                self.assertTrue(result["callerPinnedFixtureSignatureVerified"])
                self.assertEqual(result["originalMutationOutcome"], "UNKNOWN")
                self.assertEqual(result["fixtureProofPurpose"],
                                 P.TIMEW_PURPOSE if kind=="time" else P.HOSPITAL_PURPOSE)
                for k in P.DENIED:
                    self.assertIs(result[k], False, k)

    def test_02_roles_use_distinct_keys_and_signed_audiences(self):
        self.assertNotEqual(fp(self.k_time), fp(self.k_hospital))
        t = self.doc("time")[0]
        h = self.doc("hospital")[0]
        self.assertNotEqual(t, h)
        self.assertNotEqual(P.TIMEW_DOMAIN, P.HOSPITAL_DOMAIN)
        self.assertNotEqual(P.TIMEW_AUDIENCE, P.HOSPITAL_AUDIENCE)

    def test_03_key_alias_denied_even_if_signature_correct(self):
        self.refused("time", "SIGNER_SUBSTITUTION_OR_ROLE_KEY_ALIAS",
                     separately_expected_other_role_key_sha256=fp(self.k_time))
        self.refused("hospital", "SIGNER_SUBSTITUTION_OR_ROLE_KEY_ALIAS",
                     separately_expected_other_role_key_sha256=fp(self.k_hospital))

    def test_04_independent_key_pin_substitution_denied(self):
        self.refused("time", "SIGNER_SUBSTITUTION_OR_ROLE_KEY_ALIAS",
                     separately_expected_signer_sha256=fp(self.k_foreign))
        self.refused("hospital", "SIGNER_SUBSTITUTION_OR_ROLE_KEY_ALIAS",
                     independently_pinned_signer_key=self.k_foreign.public_key())

    def test_05_wrong_release_or_issuer_signer_refused(self):
        other_raw, other_sig = self.doc("time", key=self.k_foreign)
        self.refused("time", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=other_raw, signature=other_sig)

    def test_06_wrong_signature_or_replayed_other_domain_signature(self):
        t, ts = self.doc("time")
        _, hs = self.doc("hospital")
        self.refused("time", "WRONG_SIGNATURE_OR_PURPOSE_DOMAIN",
                     signed_proof_raw=t, signature=hs)
        self.refused("time", "WRONG_SIGNATURE_OR_PURPOSE_DOMAIN",
                     signature=b"Z"*64)

    def test_07_signature_uses_exact_domain_prefix(self):
        raw, _ = self.doc("time")
        wrong = self.k_time.sign(P.HOSPITAL_DOMAIN + raw)
        self.refused("time", "WRONG_SIGNATURE_OR_PURPOSE_DOMAIN",
                     signed_proof_raw=raw,signature=wrong)

    def test_08_signed_but_wrong_audience_refused(self):
        raw, sig = self.doc("time",changed={"audience":P.HOSPITAL_AUDIENCE})
        self.refused("time", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw, signature=sig)
        raw, sig = self.doc("hospital",changed={"audience":P.TIMEW_AUDIENCE})
        self.refused("hospital", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw, signature=sig)

    def test_09_signed_but_wrong_purpose_refused(self):
        raw, sig = self.doc("time",changed={"purpose":P.HOSPITAL_PURPOSE})
        self.refused("time", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw, signature=sig)
        raw, sig = self.doc("hospital",changed={"purpose":P.TIMEW_PURPOSE})
        self.refused("hospital", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw, signature=sig)

    def test_10_foreign_identity_c3eaf_purpose_never_grants(self):
        raw, sig = self.doc("time",changed={
            "purpose":"postapollo.connections.c3eaf-deny-only-ci-key-role-binding"})
        self.refused("time", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw, signature=sig)

    def test_11_proof_cannot_claim_committed_or_move_authority(self):
        raw, sig=self.doc("hospital",changed={"status":"COMMITTED"})
        self.refused("hospital", "PROOF_FIELDS_OR_CANONICAL_BYTES_CHANGED",
                     signed_proof_raw=raw,signature=sig)
        raw, sig=self.doc("time",changed={"canMoveWindow":True})
        self.refused("time", "PROOF_FIELDS_OR_CANONICAL_BYTES_CHANGED",
                     signed_proof_raw=raw,signature=sig)

    def test_12_changed_timew_surface_generation_scope_or_geometry_refused(self):
        for change in (
            {"selection_id":identity()}, {"surface_lifetime_id":identity()},
            {"surface_generation":2}, {"session_id":identity()},
            {"seat_id":"seat1"}, {"live_con_id":35},
            {"target_rect":{"x":20,"y":40,"width":700,"height":430}}):
            with self.subTest(change=change):
                selected={**self.selection,**change}
                self.refused("time", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                             selection=selected)

    def test_13_changed_scope_a_challenge_denied_before_signature(self):
        self.refused("time", "TIMEW_FIXTURE_REFUSED",
                     challenge=b"U"*32)
        changed=dict(self.selection, challenge_sha256=hashlib.sha256(b"U"*32).hexdigest())
        self.refused("time", "CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     selection=changed,challenge=b"U"*32)

    def test_14_hospital_query_forged_status_refused(self):
        obj=json.loads(self.hquery)
        obj["status"]="COMMITTED"
        self.refused("hospital", "HOSPITAL_QUERY_REFUSED",
                     hquery=P._canonical(obj))

    def test_15_hospital_original_query_challenge_swapped_refused(self):
        self.refused("hospital", "HOSPITAL_QUERY_REFUSED",challenge=b"U"*32)

    def test_16_hospital_changed_query_id_or_grant_digest_refused(self):
        for key,value in (("queryId",identity()),("grantDigest","f"*64),
                          ("requestNonce","different"),("commitSha256","f"*64)):
            with self.subTest(k=key):
                obj=json.loads(self.hquery)
                obj[key]=value
                self.refused("hospital","HOSPITAL_QUERY_REFUSED",
                             hquery=P._canonical(obj))

    def test_17_release_floor_or_revoked_root_rejected(self):
        self.refused("time","RELEASE_FLOOR_DOWNGRADE",
                     minimum_release_epoch=4)
        self.refused("hospital","RELEASE_FLOOR_DOWNGRADE",
                     minimum_release_sequence=6)
        self.refused("time","REVOKED_SIGNER",
                     revoked_signer_sha256=(fp(self.k_time),))

    def test_18_invalid_revocation_roster_and_false_floor(self):
        self.refused("time","INVALID_REVOCATION_ROSTER",
                     revoked_signer_sha256=(fp(self.k_foreign),fp(self.k_foreign)))
        self.refused("hospital","INVALID_REVOCATION_ROSTER",
                     revoked_signer_sha256=[fp(self.k_time)])
        self.refused("time","INVALID_PROOF_INTEGER",
                     minimum_release_epoch=True)

    def test_19_wrong_host_and_source_hash_refused(self):
        raw,sig=self.doc("time",changed={"hostId":"other-host"})
        self.refused("time","CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw,signature=sig)
        raw,sig=self.doc("hospital",changed={"sourceSha256":"f"*64})
        self.refused("hospital","CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED",
                     signed_proof_raw=raw,signature=sig)

    def test_20_proof_stale_or_overlong_clock_refused(self):
        for field,v in (("expiresMs",self.now),
                        ("issuedMs",self.now+20),
                        ("expiresMs",self.now+6000)):
            with self.subTest(field=field):
                raw,sig=self.doc("time",changed={field:v})
                self.refused("time","EXPIRED_OR_UNBOUNDED_FIXTURE",
                             signed_proof_raw=raw,signature=sig)

    def test_21_duplicate_or_noncanonical_signed_proof_refused(self):
        raw,sig=self.doc("time")
        self.refused("time","DUPLICATE_SIGNED_PROOF_FIELD",
                     signed_proof_raw=raw[:-1]+b',"schema":"duplicate"}',
                     signature=sig)
        self.refused("time","PROOF_FIELDS_OR_CANONICAL_BYTES_CHANGED",
                     signed_proof_raw=json.dumps(json.loads(raw)).encode(),
                     signature=sig)

    def test_22_bad_key_and_signature_lengths_refused(self):
        self.refused("time","PUBLIC_SIGNER_KEY_REQUIRED",
                     independently_pinned_signer_key=None)
        self.refused("hospital","SIGNED_PROOF_FRAME_BOUNDS",signature=b"0"*63)
        self.refused("time","SIGNED_PROOF_FRAME_BOUNDS",
                     signed_proof_raw=b"A"*(P.MAX_RECORD+1))

    def test_23_signatures_do_not_prove_replay_protection(self):
        one=self.call("time")
        two=self.call("time")
        self.assertEqual(one,two)
        self.assertFalse(one["challengeReplayOrSpendProtected"])
        h_one=self.call("hospital")
        h_two=self.call("hospital")
        self.assertEqual(h_one,h_two)
        self.assertFalse(h_two["durableOutcomeJournalVerified"])

    def test_24_native_verifier_refuses_even_with_apparent_approval(self):
        with self.assertRaisesRegex(P.ScopedEvidenceHold,
                                    "INDEPENDENT_ISSUER_AND_C5_NATIVE_ORIGIN_NOT_INSTALLED"):
            P.run_native_purpose_proof_verifier(
                c5Consent=True, hospitalWriterAuthenticated=True,
                swayAuthenticated=True, approvedByOwner=True)

    def test_25_source_has_no_signing_key_or_host_dispatch(self):
        code=(ROOT/"tests/connections/c3e_integration/ConnectionsPurposeBoundEvidencePreflight.py").read_text()
        for bad in ("Ed25519PrivateKey", "subprocess.", "sqlite3.connect(",
                    "socket.socket(", "os.open(", "sendall(", "swaymsg"):
            self.assertNotIn(bad,code)
        self.assertIn('"productionAuthority": False',code)
        self.assertIn('"sameGrantCOMMITRetryAllowed": False',code)


if __name__=="__main__":
    unittest.main(verbosity=2)
