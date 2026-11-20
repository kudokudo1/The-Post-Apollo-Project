#!/usr/bin/env python3
"""CI-only proposed Hospital recovery query binding; no native writer access."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import sys
import unittest
import uuid

if (os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("CI") != "true"
        or not os.environ.get("RUNNER_TEMP")
        or not Path(os.environ["RUNNER_TEMP"]).is_dir()
        or not sys.platform.startswith("linux")):
    raise SystemExit("HOSPITAL_STAFFING_RECOVER_QUERY_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/connections/hospital/staffing"))
sys.path.insert(0, str(ROOT / "tests/connections"))
sys.path.insert(0, str(ROOT / "hospital-source/bin"))

import StaffingRecoveryQueryPreflight as Q
import StaffingTransportPreflight as T
from test_connections_hospital_staffing_receipt_identity_preflight import (
    StaffingReceiptIdentityTests as Fixture,
)


class RecoveryQueryTests(unittest.TestCase):
    def setUp(self):
        case = Fixture("test_01_actual_hospital_pinned_source_protocols")
        case.setUp()
        self.source = {
            "original_prepare_raw": case.original_raw,
            "prepared_raw": case.prepared_raw,
            "commit_raw": case.commit_raw,
        }
        self.query_id = str(uuid.UUID("11111111-1111-4111-8111-111111111111"))
        self.challenge = b"C" * 32
        self.now = 1760000000000
        self.args = dict(**self.source, query_id=self.query_id,
                         challenge=self.challenge, issued_ms=self.now,
                         expires_ms=self.now + 1000, now_ms=self.now)
        self.good = Q.candidate_query_ci_only(**self.args)
        self.query = json.loads(self.good["candidateQueryRawForTestOnly"])

    def inspect(self, raw=None, **context):
        args = dict(self.source)
        args.update(context)
        return Q.inspect_candidate_query_ci_only(
            candidate_query_raw=self.good["candidateQueryRawForTestOnly"]
            if raw is None else raw, now_ms=self.now, **args)

    def change(self, **fields):
        return T.canonical({**self.query, **fields})

    def fail(self, why, raw=None, **context):
        with self.assertRaisesRegex(Q.RecoveryQueryHold, why):
            self.inspect(raw=raw, **context)

    def test_01_exact_source_and_query_match_is_still_unknown(self):
        out = self.inspect()
        self.assertEqual(out["originalCommitOutcome"], "UNKNOWN")
        self.assertTrue(out["noSameGrantRetryEverFromThisObservation"])
        self.assertEqual(set(self.query), Q.FIELDS)
        for name in Q.DENIED:
            self.assertIs(out[name], False, name)

    def test_02_query_kind_and_schema_not_native_action(self):
        self.assertEqual(self.query["kind"], Q.KIND)
        self.assertNotEqual(self.query["kind"], T.COMMIT)
        self.fail("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED",
                  raw=self.change(kind=T.COMMIT))
        self.fail("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED",
                  raw=self.change(schema=T.REQUEST_SCHEMA))

    def test_03_identity_fields_unreplayable_to_another_request(self):
        changed = ("requestNonce", "roomId", "action", "sessionId",
                   "writerInstance", "grantDigest", "grantNonce",
                   "approvalId", "reviewDigest", "commitSha256",
                   "originalPrepareSha256", "preparedSha256",
                   "originalScopeSha256", "graphDigest", "expectedRevision")
        for key in changed:
            with self.subTest(field=key):
                value = 99 if key=="expectedRevision" else "other"
                self.fail("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED",
                          raw=self.change(**{key:value}))

    def test_04_changed_original_prepared_is_denied(self):
        prepared = json.loads(self.source["prepared_raw"])
        prepared["writerInstance"] = "writer-other-001"
        self.fail("INVALID_ORIGINAL_SOURCE",
                  prepared_raw=T.canonical(prepared))

    def test_05_changed_commit_denied(self):
        commit = json.loads(self.source["commit_raw"])
        commit["roomId"] = "other-room"
        self.fail("INVALID_ORIGINAL_SOURCE",
                  commit_raw=T.canonical(commit))

    def test_06_different_fresh_query_cannot_reuse_old_bytes(self):
        other = dict(self.args, query_id=str(uuid.uuid4()), challenge=b"D"*32)
        candidate = Q.candidate_query_ci_only(**other)
        self.assertNotEqual(candidate["candidateSha256ForTestOnly"],
                            self.good["candidateSha256ForTestOnly"])
        self.fail("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED",
                  raw=self.change(queryId=other["query_id"]))

    def test_07_invalid_query_uuid(self):
        for bad in ("no", str(uuid.uuid1()), self.query_id.upper(), None):
            with self.subTest(id=bad):
                with self.assertRaisesRegex(Q.RecoveryQueryHold,
                                            "INVALID_QUERY_ID"):
                    Q.candidate_query_ci_only(**dict(self.args,query_id=bad))

    def test_08_invalid_challenge_bytes(self):
        for bad in (None, "", b"short", b"x"*33):
            with self.subTest(challenge=type(bad).__name__):
                with self.assertRaisesRegex(Q.RecoveryQueryHold,
                                            "UNTRUSTED_CHALLENGE_LENGTH"):
                    Q.candidate_query_ci_only(**dict(self.args,challenge=bad))

    def test_09_stale_query_and_overlong_lease(self):
        for values in ((0,1,2),(self.now,self.now+5001,self.now+1),
                       (self.now,self.now+1,self.now+1),
                       (self.now+20,self.now+30,self.now)):
            issued,expires,now=values
            with self.subTest(values=values):
                with self.assertRaisesRegex(Q.RecoveryQueryHold,
                                            "QUERY_STALE_OR_UNBOUNDED"):
                    Q.candidate_query_ci_only(
                        **dict(self.args,issued_ms=issued,
                               expires_ms=expires,now_ms=now))

    def test_10_invalid_clock_type_and_overflow(self):
        for bad in (True, None, -1, 9007199254740992, "1760000000000"):
            with self.subTest(v=bad):
                with self.assertRaisesRegex(Q.RecoveryQueryHold,
                                            "INVALID_QUERY_TIME"):
                    Q.candidate_query_ci_only(**dict(self.args,now_ms=bad))

    def test_11_unknown_fields_and_missing_fields(self):
        self.fail("QUERY_FIELDS_CHANGED",raw=self.change(canRetry=True))
        broken = dict(self.query)
        del broken["grantDigest"]
        self.fail("QUERY_FIELDS_CHANGED",raw=T.canonical(broken))

    def test_12_duplicate_json_and_noncanonical_frame(self):
        bad = (self.good["candidateQueryRawForTestOnly"][:-1]
               + b',"queryId":"duplicate"}')
        self.fail("INVALID_QUERY_FRAME",raw=bad)
        self.fail("INVALID_QUERY_FRAME",
                  raw=json.dumps(self.query).encode())

    def test_13_changed_challenge_or_unpadded_b64(self):
        self.fail("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED",
                  raw=self.change(challengeB64=base64.urlsafe_b64encode(
                      b"D"*32).rstrip(b"=").decode()))
        self.fail("INVALID_QUERY_CHALLENGE",
                  raw=self.change(challengeB64="not-base64"))

    def test_14_status_forgery_and_protocol_version(self):
        self.fail("QUERY_FIELDS_CHANGED",raw=self.change(status="COMMITTED"))
        for value in (0, 2, True, "1"):
            with self.subTest(version=value):
                self.fail("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED",
                          raw=self.change(protocolVersion=value))

    def test_15_native_service_never_installed(self):
        with self.assertRaisesRegex(Q.RecoveryQueryHold,
                                    "NATIVE_RECOVERY_REQUEST_NOT_APPROVED_OR_INSTALLED"):
            Q.run_native_staffing_recover_query(approved=True,
                                                canSendRecoveryQuery=True)

    def test_16_ci_fixture_does_not_provide_replay_ledger(self):
        first = self.inspect()
        second = self.inspect()
        self.assertEqual(first["candidateSha256ForTestOnly"],
                         second["candidateSha256ForTestOnly"])
        self.assertFalse(second["challengeReplayProtected"])
        self.assertFalse(second["writerReceiptAuthenticated"])
        self.assertFalse(second["canSendRecoveryQuery"])

    def test_17_unknown_reply_cannot_be_inspected_or_promoted(self):
        self.assertFalse(hasattr(Q, "verify_native_receipt"))
        self.assertFalse(hasattr(Q, "dispatch_recover"))
        self.assertFalse(hasattr(Q, "retry_original_commit"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
