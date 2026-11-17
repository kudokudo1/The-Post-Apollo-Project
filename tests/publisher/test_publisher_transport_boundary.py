"""P2.B account binding and transport mock tests; no live network/credentials."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


def load(name: str, filename: str):
    path=ROOT/"services"/"publisher"/filename
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boundary=load("PublisherTransportBoundaryTest","PublisherTransportBoundary.py")
adapters=load("PublisherProviderAdaptersP2B","PublisherProviderAdapters.py")

NOW="2026-11-17T08:00:00Z"
DIGEST="a"*64


def preview(provider="discord",body="Local fixture only"):
    result=adapters.prepare(provider,"Test title",body,NOW,language="en",media=[])
    assert result["ok"], result
    return result


def request(provider="discord",**overrides):
    p=preview(provider)
    data={
        "version":1,"provider":provider,"scope":"post.text",
        "identityId":"identity-1","context":"organization",
        "accountAlias":"Example account","destinationAlias":"Example channel",
        "jobId":22,"jobStatus":"reviewed",
        "draftDigest":DIGEST,"previewFingerprint":p["previewFingerprint"],
    }
    data.update(overrides)
    return p,data


class PublisherTransportP2B(unittest.TestCase):
    def test_candidate_only_no_transport(self):
        for platform in boundary.PROVIDERS:
            with self.subTest(provider=platform):
                p,intent=request(platform)
                result=boundary.local_candidate(p,intent)
                self.assertTrue(result["ok"],result)
                self.assertEqual(result["phase"],"UNTRUSTED_LOCAL_CANDIDATE")
                self.assertEqual(result["reason"],boundary.BROKER_REASON)
                self.assertEqual(len(result["candidateFingerprint"]),64)
                self.assertFalse(result["hostBrokerConnected"])
                self.assertFalse(result["bindingVerified"])
                self.assertFalse(result["canDispatch"])
                self.assertFalse(result["sent"])
                self.assertIsNone(result["providerReceipt"])
                self.assertEqual(result["requiredHostEvidence"],
                                 list(boundary.REQUIRED_EVIDENCE))
                self.assertNotIn("accountAlias",result)
                self.assertNotIn("destinationAlias",result)

    def test_local_binding_rejects_mismatch(self):
        p,intent=request()
        self.assertEqual(boundary.local_candidate(p,{
            **intent,"provider":"bluesky"})["reason"],
            "PREVIEW_PROVIDER_OR_SCOPE_MISMATCH")
        self.assertEqual(boundary.local_candidate(p,{
            **intent,"previewFingerprint":"f"*64})["reason"],
            "STALE_PREVIEW_FINGERPRINT")
        self.assertEqual(boundary.local_candidate({
            **p,"operation":"postapollo.owned_site.localDraft"},intent)["reason"],
            "INVALID_PROVIDER_OPERATION")
        self.assertEqual(boundary.local_candidate({
            **p,"providerReceipt":{"id":"123"}},intent)["reason"],
            "UNTRUSTED_PROVIDER_PREVIEW")
        self.assertEqual(boundary.local_candidate({
            **p,"sent":True},intent)["reason"],
            "UNTRUSTED_PROVIDER_PREVIEW")

    def test_no_queue_review_or_local_identity_is_authorization(self):
        p,intent=request()
        for status in ("scheduled","needs_review","blocked","published",None):
            with self.subTest(status=status):
                self.assertEqual(boundary.local_candidate(p,{
                    **intent,"jobStatus":status})["reason"],
                    "JOB_REQUIRES_MANUAL_REVIEW")
        for identity in ("", "user:1", "identity-0", "identity-1\nadmin"):
            self.assertEqual(boundary.local_candidate(p,{
                **intent,"identityId":identity})["reason"],
                "INVALID_IDENTITY_CONTEXT")
        for alias in ("bad\nchannel","", "a"*81):
            self.assertEqual(boundary.local_candidate(p,{
                **intent,"destinationAlias":alias})["reason"],
                "INVALID_ACCOUNT_OR_DESTINATION_ALIAS")
        for context in ("unknown","tenant",None):
            self.assertEqual(boundary.local_candidate(p,{
                **intent,"context":context})["reason"],
                "INVALID_IDENTITY_CONTEXT")

    def test_reject_unknown_secrets_and_forged_approval(self):
        p,intent=request()
        for extra in ("password","access_token","hostGrant","approved",
                      "webhookUrl","connectionSocket","signedEvidence"):
            with self.subTest(extra=extra):
                self.assertEqual(boundary.local_candidate(p,{
                    **intent,extra:"fake"})["reason"],
                    "INVALID_BINDING_FIELDS")
        self.assertEqual(boundary.local_candidate(p,{
            **intent,"scope":"post.video"})["reason"],"UNSUPPORTED_SCOPE")
        self.assertEqual(boundary.local_candidate(p,{
            **intent,"draftDigest":"xxx"})["reason"],
            "INVALID_CONTENT_FINGERPRINT")
        self.assertEqual(boundary.local_candidate(p,{
            **intent,"jobId":True})["reason"],"INVALID_JOB_ID")
        self.assertEqual(boundary.local_candidate(p,{
            **intent,"version":2})["reason"],"UNSUPPORTED_BINDING_VERSION")

    def test_structural_candidate_cannot_be_escalated_by_fake_broker(self):
        p,intent=request("bluesky")
        candidate=boundary.local_candidate(p,intent)
        fake_grants=[
            {},None,True,
            {"approved":True,"role":"owner","scope":"post.text"},
            {"signed":True,"issuer":"Connections","accountMatches":True},
            {"consent":True,"expiresAtMs":9999999999999,
             "notRevoked":True,"transportConnected":True},
        ]
        for fake in fake_grants:
            with self.subTest(fake=fake):
                result=boundary.authorize(candidate,fake,{"job":"reviewed"})
                self.assertFalse(result["canDispatch"])
                self.assertFalse(result["sent"])
                self.assertIsNone(result["providerReceipt"])
                self.assertEqual(result["reason"],boundary.BROKER_REASON)
                self.assertFalse(boundary.deliver(candidate,fake)["canDispatch"])
        self.assertFalse(adapters.dispatch(candidate,grant={"approved":True})["canDispatch"])

    def test_fingerprint_changes_with_account_destination_and_draft(self):
        p,original=request()
        initial=boundary.local_candidate(p,original)["candidateFingerprint"]
        for changed in (
            {"accountAlias":"Different account"},
            {"destinationAlias":"Different channel"},
            {"context":"personal"},
            {"draftDigest":"b"*64},
            {"jobId":23},
        ):
            self.assertNotEqual(initial,boundary.local_candidate(
                p,{**original,**changed})["candidateFingerprint"])
        self.assertEqual(initial,boundary.local_candidate(
            p,original)["candidateFingerprint"])

    def test_simulated_timeout_requires_reconciliation_not_retry(self):
        first=boundary.fixture_transition("fixture_prepared","begin")
        self.assertTrue(first["simulation"])
        self.assertEqual(first["fixtureState"],"fixture_pending")
        unknown=boundary.fixture_observe(first["fixtureState"],{
            "type":"timeout","accountMatches":True,"contentMatches":True})
        self.assertEqual(unknown["fixtureState"],"fixture_unknown")
        self.assertTrue(unknown["requiresReconciliation"])
        self.assertFalse(unknown["retryAutomatically"])
        self.assertFalse(unknown["realPosted"])
        self.assertFalse(unknown["canDispatch"])
        self.assertIsNone(unknown["providerReceipt"])
        notfound=boundary.fixture_observe(unknown["fixtureState"],{
            "type":"not_found","accountMatches":True,"contentMatches":True})
        self.assertEqual(notfound["fixtureState"],"fixture_unknown")
        self.assertFalse(notfound["retryAutomatically"])
        duplicate=boundary.fixture_transition("fixture_unknown","begin")
        self.assertFalse(duplicate["ok"])
        self.assertEqual(duplicate["reason"],"FIXTURE_RETRY_OR_ORDER_REFUSED")

    def test_simulated_positive_ack_never_real_receipt(self):
        ready=boundary.fixture_transition("fixture_prepared","begin")
        ack=boundary.fixture_observe(ready["fixtureState"],{
            "type":"positive_mock_receipt","accountMatches":True,
            "contentMatches":True})
        self.assertEqual(ack["fixtureState"],"fixture_confirmed")
        self.assertTrue(ack["simulation"])
        self.assertFalse(ack["realPosted"])
        self.assertIsNone(ack["providerReceipt"])
        self.assertFalse(ack["canDispatch"])
        more=boundary.fixture_transition("fixture_confirmed","begin")
        self.assertEqual(more["reason"],"FIXTURE_RETRY_OR_ORDER_REFUSED")

    def test_simulated_wrong_account_or_content_blocks(self):
        ready=boundary.fixture_transition("fixture_prepared","begin")
        for props in ({"accountMatches":False,"contentMatches":True},
                      {"accountMatches":True,"contentMatches":False}):
            result=boundary.fixture_observe("fixture_pending",{
                "type":"positive_mock_receipt",**props})
            self.assertFalse(result["ok"])
            self.assertEqual(result["fixtureState"],"fixture_blocked")
            self.assertFalse(result["sent"])

    def test_strict_json_rejects_duplicate_keys_and_untrusted_fields(self):
        p,intent=request()
        self.assertEqual(boundary.strict_candidate_json(json.dumps(intent))["candidate"],
                         intent)
        self.assertEqual(boundary.strict_candidate_json(json.dumps({
            **intent,"grant":"pretend"}))["reason"],"INVALID_BINDING_FIELDS")
        self.assertEqual(boundary.strict_candidate_json(
            '{"version":1,"version":1}')["reason"],"INVALID_CANDIDATE_JSON")
        self.assertEqual(boundary.strict_candidate_json("{")["reason"],
                         "INVALID_CANDIDATE_JSON")
        self.assertEqual(boundary.strict_candidate_json("x"*14001)["reason"],
                         "INVALID_CANDIDATE_INPUT")

    def test_source_has_no_network_or_secret_backend(self):
        source=(ROOT/"services/publisher/PublisherTransportBoundary.py").read_text()
        for blocked in ("import socket","import urllib","requests.post",
                        "QNetworkAccessManager","import http.client",
                        "from subprocess","import subprocess","open(","connect(",
                        "Authorization: Bearer","webhook_url",
                        "secret_service","os.environ", "eval("):
            self.assertNotIn(blocked,source)
        self.assertIn("return refuse(BROKER_REASON)",source)
        self.assertIn('"canDispatch": False',source)
        self.assertIn('"providerReceipt": None',source)


if __name__ == "__main__":
    unittest.main()
