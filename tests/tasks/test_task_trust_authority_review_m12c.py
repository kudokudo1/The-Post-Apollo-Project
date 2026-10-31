#!/usr/bin/env python3
"""M12c pure synthetic governance tests, not real credentials or approvals."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tests/tasks/fixtures/TaskTrustAuthorityPolicyM12c.py"
MANIFEST = ROOT / "tests/tasks/fixtures/task_trust_authority_review_m12c.json"
spec = importlib.util.spec_from_file_location("m12c_trust_policy", MODULE)
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)

KEY = "a" * 64
NEW = "b" * 64
HASH = "c" * 64


def anchor():
    return {
        "rootProvenance": "OPERATOR_CONTROLLED_OUTSIDE_RELEASE",
        "trustedKeyId": "TRUSTKEY_0001",
        "trustedKeyFingerprint": KEY, "generationFloor": 7,
        "revokedKeyIds": [],
        "roles": {
            "custodian": "CUSTODIAN_0001", "signer": "SIGNER_0001",
            "reviewer": "REVIEWER_0001", "operator": "OPERATOR_0001"
        }
    }


def release():
    return {
        "keyId": "TRUSTKEY_0001", "keyFingerprint": KEY,
        "generation": 8, "artifactDigest": HASH,
        "declaredSigner": "SIGNER_0001",
        "releaseSuppliedTrustRoot": False
    }


def proof():
    return {
        "signatureVerifiedAgainstExternalRoot": True,
        "artifactBytesVerifiedAgainstSignedManifest": True,
        "generationFloorReadFromIndependentStore": True,
        "identityAndApprovalEvidenceExternal": True,
        "approvedByReviewer": True, "operatorReleaseReview": True
    }


def rotation():
    return {
        "oldKeyId": "TRUSTKEY_0001", "newKeyId": "TRUSTKEY_0002",
        "newFingerprint": NEW, "newGenerationFloor": 8,
        "releaseSuppliedTrustRoot": False
    }


def rotation_proof():
    return {
        "oldRootEndorsementVerified": True,
        "newRootPossessionVerified": True,
        "independentCustodianApproval": True,
        "independentReviewerApproval": True,
        "operatorTrustRootReview": True,
        "generationFloorPersistedExternally": True
    }


class TrustAuthorityReviewTests(unittest.TestCase):
    def test_valid_synthetic_release_is_review_only_not_operational(self):
        a, r, evidence = anchor(), release(), proof()
        out = policy.assess_release(a, r, evidence)
        self.assertEqual(out["status"], "SYNTHETIC_REVIEW_ELIGIBLE")
        self.assertFalse(out["productionAuthorized"])
        self.assertFalse(out["trustStoreChanged"])
        self.assertFalse(out["activationApproved"])
        self.assertFalse(out["review"]["actualSignatureVerificationPerformedHere"])
        self.assertTrue(out["review"]["operatorActivationDecisionStillRequired"])
        self.assertEqual(a, anchor())
        self.assertEqual(r, release())
        self.assertEqual(evidence, proof())

    def test_missing_anchor_or_release_self_bootstrap_is_refused(self):
        for a in (None, {}, {"trustedKeyId": "TRUSTKEY_0001"}):
            self.assertEqual(policy.assess_release(a, release(), proof())["status"],
                             "REFUSED")
        a = anchor()
        a["rootProvenance"] = "SAME_CANDIDATE_FOLDER"
        self.assertEqual(policy.assess_release(a, release(), proof())["reason"],
                         "INVALID_ANCHOR_POLICY")
        r = release()
        r["releaseSuppliedTrustRoot"] = True
        self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                         "INVALID_RELEASE_DESCRIPTOR")

    def test_role_collision_and_unapproved_signer_refuse(self):
        a = anchor()
        a["roles"]["reviewer"] = a["roles"]["signer"]
        self.assertEqual(policy.assess_release(a, release(), proof())["reason"],
                         "SEPARATION_OF_DUTIES_REQUIRED")
        r = release()
        r["declaredSigner"] = "OTHER_SIGNER_0001"
        self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                         "UNAUTHORIZED_SIGNER")

    def test_wrong_or_revoked_signing_key_refused(self):
        a = anchor()
        a["revokedKeyIds"] = ["TRUSTKEY_0001"]
        self.assertEqual(policy.assess_release(a, release(), proof())["reason"],
                         "TRUSTED_KEY_REVOKED")
        r = release()
        r["keyId"] = "TRUSTKEY_9999"
        self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                         "UNTRUSTED_OR_REVOKED_SIGNER_KEY")
        r = release()
        r["keyFingerprint"] = NEW
        self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                         "UNTRUSTED_OR_REVOKED_SIGNER_KEY")

    def test_generation_floor_blocks_rollback_and_same_generation_replay(self):
        for generation in (1, 7):
            r = release()
            r["generation"] = generation
            self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                             "RELEASE_ROLLBACK_OR_REPLAY")
        a = anchor()
        a["generationFloor"] = 8
        self.assertEqual(policy.assess_release(a, release(), proof())["reason"],
                         "RELEASE_ROLLBACK_OR_REPLAY")

    def test_false_or_missing_external_evidence_never_grants_review(self):
        for key in proof():
            evidence = proof()
            evidence[key] = False
            out = policy.assess_release(anchor(), release(), evidence)
            self.assertEqual(out["reason"], "EXTERNAL_RELEASE_EVIDENCE_INCOMPLETE",
                             key)
            self.assertFalse(out["productionAuthorized"])
        for evidence in ({}, None, {"signatureVerifiedAgainstExternalRoot": True}):
            self.assertEqual(policy.assess_release(anchor(), release(), evidence)["reason"],
                             "EXTERNAL_RELEASE_EVIDENCE_REQUIRED")

    def test_boolean_string_and_malformed_identifiers_refuse(self):
        for value in (True, -1, "8"):
            a = anchor()
            a["generationFloor"] = value
            self.assertEqual(policy.assess_release(a, release(), proof())["status"],
                             "REFUSED")
        # Zero means no release accepted yet; bootstrap floor is valid.
        fresh = anchor()
        fresh["generationFloor"] = 0
        self.assertEqual(policy.assess_release(fresh, release(), proof())["status"],
                         "SYNTHETIC_REVIEW_ELIGIBLE")
        r = release()
        r["generation"] = True
        self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                         "INVALID_RELEASE_DESCRIPTOR")
        r = release()
        r["artifactDigest"] = "not-a-digest"
        self.assertEqual(policy.assess_release(anchor(), r, proof())["reason"],
                         "INVALID_RELEASE_DESCRIPTOR")

    def test_rotation_only_external_candidate_no_trust_store_mutation(self):
        a, p, e = anchor(), rotation(), rotation_proof()
        out = policy.assess_rotation(a, p, e)
        self.assertEqual(out["status"], "SYNTHETIC_REVIEW_ELIGIBLE")
        self.assertEqual(out["reason"], "ROTATION_PENDING_EXTERNAL_APPROVAL")
        self.assertFalse(out["productionAuthorized"])
        self.assertFalse(out["trustStoreChanged"])
        self.assertFalse(out["activationApproved"])
        self.assertFalse(out["review"]["actualTrustRootInstalledHere"])
        self.assertEqual(a, anchor())
        self.assertEqual(p, rotation())
        self.assertEqual(e, rotation_proof())

    def test_rotation_requires_all_separate_review_and_floor_evidence(self):
        for key in rotation_proof():
            evidence = rotation_proof()
            evidence[key] = False
            self.assertEqual(
                policy.assess_rotation(anchor(), rotation(), evidence)["reason"],
                "ROTATION_EVIDENCE_INCOMPLETE", key)

    def test_rotation_rejects_old_key_reuse_revocation_and_floor_decrease(self):
        for changes in (
            {"newKeyId": "TRUSTKEY_0001"},
            {"newFingerprint": KEY},
            {"newGenerationFloor": 6},
            {"releaseSuppliedTrustRoot": True},
            {"oldKeyId": "TRUSTKEY_9999"}
        ):
            p = rotation()
            p.update(changes)
            self.assertEqual(policy.assess_rotation(anchor(), p, rotation_proof())["reason"],
                             "INVALID_ROTATION_PROPOSAL")
        a = anchor()
        a["revokedKeyIds"] = ["TRUSTKEY_0002"]
        self.assertEqual(policy.assess_rotation(a, rotation(), rotation_proof())["reason"],
                         "INVALID_ROTATION_PROPOSAL")

    def test_manifest_decisions_remain_open_and_permissions_denied(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["milestone"], "M12c")
        self.assertEqual(data["classification"], "PROPOSED_TRUST_AUTHORITY_DECISION_ONLY")
        self.assertEqual(set(data["openDecisions"]), {
            "TRUST_ROOT_CUSTODIAN", "SIGNER_AND_RELEASE_REVIEWER",
            "APPROVED_RELEASE_CHANNEL", "ROLLBACK_RESISTANT_GENERATION",
            "KEY_ROTATION_AND_REVOCATION", "HOST_EXECUTABLE_THREAT_MODEL",
        })
        self.assertTrue(all(x["status"] == "OPEN" for x in data["openDecisions"].values()))
        self.assertTrue(all(x is False for x in data["authority"].values()))
        self.assertTrue(all(x["status"] == "OPEN" for x in data["m12bProductionChecks"]))

    def test_no_real_host_or_task_writer_mounted(self):
        fixture = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("Quickshell.dataDir", fixture)
        self.assertNotIn("apollo-hub-todo-v1.json", fixture)
        self.assertNotIn("subprocess", fixture)
        self.assertNotIn("crypto.createPrivateKey", fixture)
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        self.assertIn("readonly property bool guardedWriterEnabled: false", store)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("return stage(TodoPolicy."), 9)
        self.assertNotIn("TaskTrustAuthorityPolicyM12c", shell + store)


if __name__ == "__main__":
    unittest.main(verbosity=2)
