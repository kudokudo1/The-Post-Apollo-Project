#!/usr/bin/env python3
"""Hospital fixture vs proposed native receipt identity, source-only CI."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import unittest

if (os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("CI") != "true"
        or not os.environ.get("RUNNER_TEMP")
        or not Path(os.environ["RUNNER_TEMP"]).is_dir()
        or not sys.platform.startswith("linux")):
    raise SystemExit("STAFFING_RECEIPT_IDENTITY_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/connections/hospital/staffing"))
sys.path.insert(0, str(ROOT / "hospital-source/bin"))
import StaffingTransportPreflight as T
import StaffingReceiptIdentityPreflight as R
import px_hospital_staffing_transport as HospitalT
import px_hospital_staffing_prepare_commit as HospitalC
import px_hospital_staffing_grants as HospitalG
import px_hospital_staffing_native_peer as HospitalP


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class StaffingReceiptIdentityTests(unittest.TestCase):
    def setUp(self):
        scope = dict(
            roomId="room-ci", patientId="patient-ci",
            repository="org/repo", branch="feature/staffing",
            bedPath="/tmp/staffing-test", assignmentId="1",
            sessionId="session-ci", doctorId="doctor-ci",
            providerId="provider-ci", mode="create",
        )
        self.original = {
            "schema": T.REQUEST_SCHEMA, "kind": "prepare",
            "action": "SESSION_ATTACH", "roomId": scope["roomId"],
            "intent": scope, "requestNonce": b64(b"P"*32),
        }
        self.prepared = {
            "schema": R.PREPARED_SCHEMA,
            "requestNonce": self.original["requestNonce"],
            "roomId": self.original["roomId"],
            "action": self.original["action"],
            "expectedRevision": 5,
            "expectedDigest": "a"*64,
            "writerInstance": "writer-fixture-001",
            "state": "ACTIVE", "expiresInSeconds": 40,
            "operatorAuthenticated": False,
            "requiresExternalConsent": True,
        }
        self.body = {
            "schema": T.GRANT_SCHEMA, "audience": T.AUDIENCE,
            "operation": "SESSION_ATTACH", "scope": scope,
            "roomRevision": 5, "graphDigest": "a"*64,
            "operatorId": "uid:1001", "approvalId": "ci-approval-fixture-01",
            "seatId": "logind-seat0-ciFixture", "hostId": "b"*64,
            "nonce": b64(b"N"*32), "requestNonce": self.original["requestNonce"],
            "writerInstance": "writer-fixture-001", "issuedAt": 1760000000,
            "expiresAt": 1760000025, "operatorUid": 1001,
            "polkitActionId": HospitalG.POLKIT_ACTIONS["SESSION_ATTACH"],
            "policyGeneration": 3, "clientExecutableSha256": "c"*64,
            "issuerReleaseSha256": "d"*64, "reviewDigest": "e"*64,
        }
        self.grant = T.canonical({
            "body": self.body, "signature": b64(b"\x91"*64)})
        self.original_raw = T.canonical(self.original)
        self.prepared_raw = T.canonical(self.prepared)
        self.commit_raw = T.compose_commit(
            self.original_raw, self.prepared["writerInstance"], self.grant)
        self.grant_digest = hashlib.sha256(
            R.GRANT_DOMAIN + T.canonical(self.body)).hexdigest()
        self.fixture = {
            "schema": R.HOSPITAL_FIXTURE_SCHEMA,
            "requestNonce": self.original["requestNonce"],
            "roomId": self.original["roomId"],
            "action": self.original["action"],
            "sessionId": self.original["intent"]["sessionId"],
            "grantDigest": self.grant_digest,
            "fixtureTransactionCommitted": True,
            "nativeInstallationVerified": False,
            "operatorAuthenticated": False,
        }
        self.proposal = {
            "schema": R.PROPOSED_RECEIPT_SCHEMA,
            "protocolVersion": 1, "kind": R.PROPOSED_KIND,
            "requestSchema": T.REQUEST_SCHEMA,
            "requestNonce": self.original["requestNonce"],
            "roomId": self.original["roomId"],
            "action": self.original["action"],
            "sessionId": self.original["intent"]["sessionId"],
            "writerInstance": self.prepared["writerInstance"],
            "expectedRevision": self.prepared["expectedRevision"],
            "revisionAfter": self.prepared["expectedRevision"] + 1,
            "graphDigest": self.prepared["expectedDigest"],
            "grantDigest": self.grant_digest,
            "originalPrepareSha256": hashlib.sha256(self.original_raw).hexdigest(),
            "commitSha256": hashlib.sha256(self.commit_raw).hexdigest(),
            "status": R.PROPOSED_STATUS,
        }

    def check(self, proposal=False, **changes):
        args = {
            "original_prepare_raw": self.original_raw,
            "prepared_raw": self.prepared_raw,
            "commit_raw": self.commit_raw,
        }
        args.update(changes)
        if proposal:
            args.setdefault("proposed_receipt_raw", T.canonical(self.proposal))
            return R.inspect_proposed_receipt_ci_only(**args)
        args.setdefault("fixture_receipt_raw", T.canonical(self.fixture))
        return R.inspect_hospital_fixture_receipt_ci_only(**args)

    def refused(self, reason, proposal=False, **changes):
        with self.assertRaisesRegex(R.ReceiptHold, reason):
            self.check(proposal=proposal, **changes)

    def fixture_changed(self, **changes):
        return T.canonical({**self.fixture, **changes})

    def proposed_changed(self, **changes):
        return T.canonical({**self.proposal, **changes})

    def test_01_actual_hospital_pinned_source_protocols(self):
        self.assertEqual(R.PREPARED_SCHEMA, HospitalC.PREPARED_SCHEMA)
        self.assertEqual(R.HOSPITAL_FIXTURE_SCHEMA, HospitalC.RECEIPT_SCHEMA)
        self.assertEqual(R.REQUEST_SCHEMA, HospitalT.SCHEMA)
        self.assertEqual(R.GRANT_DOMAIN, HospitalG.DOMAIN)
        self.assertEqual(R.PREPARED_FIELDS, set(self.prepared))
        self.assertEqual(R.FIXTURE_FIELDS, set(self.fixture))
        self.assertEqual(R.PROPOSED_FIELDS, set(self.proposal))
        self.assertEqual(T.MAX_FRAME, HospitalT.MAX_FRAME)
        self.assertEqual(T.MAX_FRAME, HospitalP.MAX_PACKET)
        self.assertEqual(T.MAX_GRANT_BYTES, HospitalT.MAX_GRANT_BYTES)
        self.assertEqual(HospitalT.parse_request(self.commit_raw)["kind"], "commit")

    def test_02_valid_fixture_is_never_native(self):
        out = self.check()
        self.assertTrue(out["sourceOnlyHospitalFixtureMatchesCurrentInputs"])
        self.assertTrue(out["fixtureLacksWriterInstanceAndCommitDigest"])
        for name in R.DENIED:
            self.assertIs(out[name], False, name)

    def test_03_wrong_fixture_request_nonce(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(requestNonce=b64(b"Q"*32)))

    def test_04_wrong_fixture_room(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(roomId="other"))

    def test_05_wrong_fixture_action(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(action="DOCTOR_SUCCEED"))

    def test_06_wrong_fixture_session(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(sessionId="other"))

    def test_07_wrong_fixture_grant_digest(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(grantDigest="f"*64))

    def test_08_fixture_native_installation_claim_refused(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(nativeInstallationVerified=True))

    def test_09_fixture_operator_authenticated_claim_refused(self):
        self.refused("HOSPITAL_FIXTURE_RECEIPT_MISMATCH",
                     fixture_receipt_raw=self.fixture_changed(operatorAuthenticated=True))

    def test_10_fixture_extra_approval_field_refused(self):
        self.refused("UNEXPECTED_OR_MISSING_RECORD_FIELDS",
                     fixture_receipt_raw=self.fixture_changed(productionAuthority=True))

    def test_11_proposed_version_and_context_match_without_grant(self):
        out = self.check(proposal=True)
        self.assertTrue(out["proposedReceiptMatchesProvidedSourceBytesInCI"])
        self.assertEqual(out["candidateReceiptSha256"],
                         hashlib.sha256(T.canonical(self.proposal)).hexdigest())
        for name in R.DENIED:
            self.assertIs(out[name], False, name)

    def test_12_proposed_unsupported_schema(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(schema="postapollo.hospital.native-staffing-receipt.v1"))

    def test_13_proposed_unsupported_version(self):
        for bad in (0, 2, True, "1", None):
            with self.subTest(value=bad):
                self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                             proposed_receipt_raw=self.proposed_changed(protocolVersion=bad))

    def test_14_wrong_commit_digest(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(commitSha256="f"*64))

    def test_15_wrong_original_prepare_digest(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(originalPrepareSha256="f"*64))

    def test_16_writer_instance_substitution(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(writerInstance="other-writer-001"))

    def test_17_stale_revision_and_revision_after(self):
        for field in ("expectedRevision", "revisionAfter"):
            with self.subTest(field=field):
                self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                             proposed_receipt_raw=self.proposed_changed(**{field:99}))

    def test_18_wrong_graph_digest(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(graphDigest="f"*64))

    def test_19_wrong_signed_grant_digest(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(grantDigest="f"*64))

    def test_20_wrong_session_or_action(self):
        for name, value in (("sessionId","wrong"),("action","TRASH"),("roomId","wrong")):
            with self.subTest(field=name):
                self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                             proposed_receipt_raw=self.proposed_changed(**{name:value}))

    def test_21_false_receipt_status_or_extra_authority(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(status="COMMITTED"))
        self.refused("UNEXPECTED_OR_MISSING_RECORD_FIELDS",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(operatorAuthorized=True))

    def test_22_replayed_receipt_against_fresh_prepare_refused(self):
        other=dict(self.original,requestNonce=b64(b"Q"*32))
        self.refused("PREPARE_COMMIT_IDENTITY_CHANGED",proposal=True,
                     original_prepare_raw=T.canonical(other))

    def test_23_changed_prepared_source_refused(self):
        changed=dict(self.prepared,expectedDigest="f"*64)
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     prepared_raw=T.canonical(changed))

    def test_24_changed_prepared_writer_refused(self):
        changed=dict(self.prepared,writerInstance="other-writer-001")
        self.refused("PREPARE_COMMIT_IDENTITY_CHANGED",proposal=True,
                     prepared_raw=T.canonical(changed))

    def test_25_unsigned_commit_substitution_refused(self):
        broken=json.loads(self.commit_raw)
        broken["action"]="DOCTOR_SUCCEED"
        self.refused("PREPARE_COMMIT_IDENTITY_CHANGED",proposal=True,
                     commit_raw=T.canonical(broken))

    def test_26_changed_commit_envelope_refused(self):
        broken=json.loads(self.commit_raw)
        inner=json.loads(self.grant)
        inner["body"]["nonce"]=b64(b"Z"*32)
        broken["signedEnvelope"]=b64(T.canonical(inner))
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     commit_raw=T.canonical(broken))

    def test_27_malformed_or_duplicate_receipt_refused(self):
        raw=T.canonical(self.proposal)
        self.refused("NONCANONICAL_RECORD",proposal=True,
                     proposed_receipt_raw=raw+b"\n")
        dup=raw.replace(b'"status":',b'"status":"fake","status":',1)
        self.refused("NONCANONICAL_RECORD",proposal=True,
                     proposed_receipt_raw=dup)

    def test_28_version_bool_masquerading_as_one_refused(self):
        self.refused("PROPOSED_RECEIPT_VERSION_OR_IDENTITY_MISMATCH",proposal=True,
                     proposed_receipt_raw=self.proposed_changed(protocolVersion=True))

    def test_29_repeat_valid_candidate_never_spends_or_authorizes(self):
        a=self.check(proposal=True)
        b=self.check(proposal=True)
        self.assertEqual(a["candidateReceiptSha256"],b["candidateReceiptSha256"])
        self.assertFalse(a["writerTransactionCommittedVerified"])
        self.assertFalse(b["hospitalPersistentReplayProtectionVerified"])

    def test_30_real_unix_sender_observation_is_still_not_trust(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        with a,b:
            a.settimeout(2)
            a.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
            b.send(T.canonical(self.proposal))
            result=R.inspect_proposed_receipt_kernel_packet_ci_only(
                a, expected_uid=os.getuid(),
                original_prepare_raw=self.original_raw,
                prepared_raw=self.prepared_raw,commit_raw=self.commit_raw)
            self.assertEqual(result["observedKernelPeerInCI"]["pid"],os.getpid())
            self.assertFalse(result["independentlyAuthenticatedHospitalWriter"])

    def test_31_wrong_kernel_sender_uid_refused(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        with a,b:
            a.settimeout(2)
            a.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
            b.send(T.canonical(self.proposal))
            with self.assertRaisesRegex(R.ReceiptHold,"KERNEL_SENDER_REFUSED"):
                R.inspect_proposed_receipt_kernel_packet_ci_only(
                    a,expected_uid=os.getuid()+1,
                    original_prepare_raw=self.original_raw,
                    prepared_raw=self.prepared_raw,commit_raw=self.commit_raw)

    def test_32_native_receipt_verifier_remains_off(self):
        with self.assertRaisesRegex(R.ReceiptHold,"NATIVE_WRITER_RECEIPT_AUTHORITY_NOT_INSTALLED"):
            R.run_native_staffing_receipt_verifier(operatorApproved=True)
        self.assertFalse(hasattr(R,"sign_receipt"))
        self.assertFalse(hasattr(R,"consume_nonce"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
