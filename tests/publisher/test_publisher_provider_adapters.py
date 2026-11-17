"""P2.A: real provider-specific payload shaping, strictly OFFLINE.

No account tokens, no HTTP, no external platform, no workstation changes.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/publisher/PublisherProviderAdapters.py"
spec = importlib.util.spec_from_file_location("PublisherProviderAdaptersTest", SCRIPT)
assert spec and spec.loader
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

NOW = "2026-11-17T08:00:00Z"


def prepare(provider: str, *, title: str = "Approved title",
            body: str = "Approved announcement", language: str | None = None,
            media=None):
    return adapter.prepare(provider, title, body, NOW, language=language, media=media)


class ProviderAdapterP2ATests(unittest.TestCase):
    def test_discord_webhook_text_shape_disables_mentions(self):
        body = "@everyone Our regular post uses <@123456789> literally"
        result = prepare("discord", body=body)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["operation"], "discord.executeWebhook")
        self.assertEqual(result["payload"]["content"], body)
        self.assertEqual(result["payload"]["allowed_mentions"], {"parse": []})
        self.assertFalse(result["payload"]["tts"])
        self.assertTrue(result["providerConstraints"]["waitForMessageConfirmation"])
        self.assertFalse(result["canDispatch"])
        self.assertFalse(result["sent"])
        self.assertIsNone(result["providerReceipt"])
        self.assertNotIn("webhookUrl", json.dumps(result))
        self.assertNotIn("webhookToken", json.dumps(result))

    def test_discord_exact_limit_no_truncation(self):
        self.assertTrue(prepare("discord",body="x" * 2000)["ok"])
        denied = prepare("discord",body="x" * 2001)
        self.assertEqual(denied["reason"], "DISCORD_CONTENT_LIMIT")
        self.assertNotIn("payload", denied)

    def test_bluesky_post_record_shape(self):
        result = prepare("bluesky",body="Hello Bluesky!",language="en")
        self.assertTrue(result["ok"],result)
        self.assertEqual(result["operation"], "com.atproto.repo.createRecord")
        self.assertEqual(result["payload"]["collection"], "app.bsky.feed.post")
        record = result["payload"]["record"]
        self.assertEqual(record, {
            "$type": "app.bsky.feed.post",
            "text": "Hello Bluesky!",
            "createdAt": NOW,
            "langs": ["en"],
        })
        self.assertTrue(result["providerConstraints"]["requiresVerifiedRepoDid"])
        self.assertNotIn("repo", result["payload"],
                         "no caller-supplied DID may become posting authority")

    def test_bluesky_conservative_length_cap(self):
        self.assertTrue(prepare("bluesky",body="a" * 300)["ok"])
        self.assertEqual(prepare("bluesky",body="a" * 301)["reason"],
                         "BLUESKY_TEXT_LIMIT")
        self.assertEqual(prepare("bluesky",body="🦊" * 301)["reason"],
                         "BLUESKY_TEXT_LIMIT")
        # Conservatively rejects combining sequences rather than overrunning
        # a remote grapheme bound.
        self.assertEqual(prepare("bluesky",body="e\u0301" * 200)["reason"],
                         "BLUESKY_TEXT_LIMIT")
        self.assertNotIn("langs",prepare("bluesky")["payload"]["record"])

    def test_website_is_draft_only_without_invented_endpoint(self):
        result = prepare("website",title="Local bulletin",body="Owned content")
        self.assertTrue(result["ok"])
        self.assertEqual(result["operation"],"postapollo.owned_site.localDraft")
        self.assertEqual(result["payload"]["title"],"Local bulletin")
        self.assertEqual(result["payload"]["body"],"Owned content")
        self.assertEqual(result["payload"]["publicationState"],"draft")
        self.assertIsNone(result["providerConstraints"]["siteEndpoint"])
        self.assertTrue(result["providerConstraints"]["requiresExplicitSiteContract"])
        self.assertFalse(result["canDispatch"])

    def test_no_provider_gets_media_without_upload_pipeline(self):
        for provider in adapter.PROVIDERS:
            with self.subTest(provider=provider):
                result = prepare(provider,media=[{"id":"m1"}])
                self.assertEqual(result["reason"],"MEDIA_ADAPTER_NOT_ENABLED")
                self.assertFalse(result["canDispatch"])
                self.assertNotIn("payload",result)

    def test_invalid_content_refused_without_automatic_changes(self):
        for provider in adapter.PROVIDERS:
            with self.subTest(provider=provider):
                self.assertEqual(prepare(provider,body="")["reason"],"EMPTY_POST")
                self.assertEqual(prepare(provider,body=" \t ")["reason"],"EMPTY_POST")
                self.assertEqual(prepare(provider,body="hello\x00world")["reason"],
                                 "INVALID_BODY")
                self.assertEqual(prepare(provider,title="bad\nheading")["reason"],
                                 "INVALID_TITLE")
                self.assertEqual(prepare(provider,title="")["reason"],"INVALID_TITLE")
        self.assertEqual(prepare("discord",body="x"*10001)["reason"],"INVALID_BODY")
        self.assertEqual(prepare("unlisted")["reason"],"UNSUPPORTED_PROVIDER")

    def test_time_language_and_unicode_constraints(self):
        result = adapter.prepare("bluesky","Title","Good text",
                                 "2026-11-17T08:00:00+04:00")
        self.assertEqual(result["reason"],"INVALID_CREATED_AT")
        self.assertEqual(adapter.prepare("bluesky","T","body",
                            "2026-02-30T08:00:00Z")["reason"],"INVALID_CREATED_AT")
        self.assertEqual(prepare("bluesky",language="en-US")["payload"]
                         ["record"]["langs"],["en-US"])
        self.assertEqual(prepare("bluesky",language="not-a-language")["reason"],
                         "INVALID_LANGUAGE")

    def test_preview_fingerprint_is_stable_not_an_authority(self):
        a=prepare("discord",body="same message")
        b=prepare("discord",body="same message")
        c=prepare("discord",body="different message")
        self.assertEqual(a["previewFingerprint"],b["previewFingerprint"])
        self.assertNotEqual(a["previewFingerprint"],c["previewFingerprint"])
        self.assertEqual(len(a["previewFingerprint"]),64)
        self.assertTrue(a["previewOnly"])
        self.assertEqual(a["reason"],adapter.REASON_BLOCKED)

    def test_dispatch_denies_forged_grant_and_response(self):
        preview = prepare("discord")
        for grant in (None,{}, {"approved":True},
                      {"signed":True,"account":"owner","consent":True},
                      {"receipt":{"message_id":"1234567"},"canDispatch":True}):
            denied=adapter.dispatch(preview,grant=grant)
            self.assertEqual(denied["reason"],adapter.REASON_BLOCKED)
            self.assertFalse(denied["canDispatch"])
            self.assertFalse(denied["sent"])
            self.assertIsNone(denied["providerReceipt"])

    def test_json_contract_refuses_secrets_and_duplicates(self):
        data = {"title":"Creator title","body":"Hello","createdAt":NOW,
                "language":None,"media":[]}
        good=adapter.preview_from_json(json.dumps(data),"discord")
        self.assertTrue(good["ok"])
        self.assertEqual(adapter.preview_from_json(json.dumps(
            {**data,"webhook_url":"secret"}),"discord")["reason"],
            "UNKNOWN_PREVIEW_FIELDS")
        self.assertEqual(adapter.preview_from_json(json.dumps(
            {**data,"access_token":"secret"}),"bluesky")["reason"],
            "UNKNOWN_PREVIEW_FIELDS")
        self.assertEqual(adapter.preview_from_json(
            '{"title":"A","title":"B","body":"X","createdAt":"' + NOW
            + '","language":null,"media":[]}',"discord")["reason"],
            "INVALID_PREVIEW_JSON")
        self.assertEqual(adapter.preview_from_json("{" ,"discord")["reason"],
                         "INVALID_PREVIEW_JSON")
        self.assertEqual(adapter.preview_from_json("x"*14001,"discord")["reason"],
                         "INVALID_PREVIEW_INPUT")

    def test_cli_is_offline_and_emits_one_json_line(self):
        payload = json.dumps({
            "title":"Creator", "body":"Hello from fixture",
            "createdAt":NOW, "language":None, "media":[],
        })
        for provider in adapter.PROVIDERS:
            with self.subTest(provider=provider):
                result=subprocess.run(
                    [sys.executable,"-I","-B",str(SCRIPT),
                     "--provider",provider],
                    input=payload,text=True,capture_output=True,check=True,
                    timeout=3,
                )
                rows=result.stdout.strip().splitlines()
                self.assertEqual(len(rows),1)
                parsed=json.loads(rows[0])
                self.assertTrue(parsed["ok"])
                self.assertFalse(parsed["canDispatch"])
                self.assertFalse(parsed["sent"])
                self.assertEqual(result.stderr,"")

    def test_source_has_no_transport_or_credential_calls(self):
        source=SCRIPT.read_text()
        for prohibited in ("import socket","import requests","import urllib",
                           "import http.client","from urllib","subprocess",
                           "QNetworkAccessManager","webbrowser.open",
                           "urlopen(", "httpx","aiohttp", "open_connection("):
            self.assertNotIn(prohibited,source)
        self.assertNotIn("Authorization: Bearer",source)
        self.assertNotIn("webhooks/{id}/{token}",source)
        self.assertIn("def dispatch(",source)
        self.assertIn("return deny(REASON_BLOCKED)",source)


if __name__ == "__main__":
    unittest.main()
