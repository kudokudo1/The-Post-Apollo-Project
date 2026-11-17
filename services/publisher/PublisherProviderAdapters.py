#!/usr/bin/env python3
"""P2.A provider-specific OFFLINE payload adapters, never a network dispatcher.

The code prepares local previews of text-only requests for the owning
provider. It knows no provider account, credential, destination URI or
transport. It cannot send. Real posting requires a separately reviewed
Connections/Identity host grant and a transport with reconciliation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

VERSION = 1
PROVIDERS = ("discord", "bluesky", "website")
MAX_TITLE = 120
MAX_BODY = 10000
REASON_BLOCKED = "TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED"
LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
# Conservative cap: 300 Python codepoints <= 300 grapheme clusters.
# This rejects some valid emoji/combining text rather than overestimating
# remote capacity. Revalidate at future provider execution time.
BLUESKY_MAX_CODEPOINTS = 300


def deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False, "reason": reason,
        "canDispatch": False, "sent": False, "providerReceipt": None,
    }


def valid_text(value: Any, limit: int, *, allow_newline: bool) -> bool:
    if not isinstance(value, str) or len(value) > limit:
        return False
    for char in value:
        n = ord(char)
        if n == 0 or n == 127 or (n < 32 and not (
            allow_newline and char in ("\n", "\t"))):
            return False
    return True


def check_created_at(raw: Any) -> str | None:
    if not isinstance(raw, str) or len(raw) > 40:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", raw) is None:
        return None
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
        return None
    return raw


def prepare_discord(body: str) -> dict[str, Any]:
    if not body.strip():
        return deny("EMPTY_POST")
    if len(body) > 2000:
        return deny("DISCORD_CONTENT_LIMIT")
    return {
        "operation": "discord.executeWebhook",
        "payload": {
            "content": body,
            "allowed_mentions": {"parse": []},
            "tts": False,
        },
        "providerConstraints": {
            "maxContentCharacters": 2000,
            "waitForMessageConfirmation": True,
            "forumThreadRequiredWhenApplicable": True,
        },
        "requiredHostEvidence": [
            "verified_webhook_channel_ownership",
            "signed_calling_process",
            "operator_consented_post.text_scope",
            "active_revocable_grant",
            "message_id_confirmation",
        ],
    }


def prepare_bluesky(body: str, created_at: str, language: str | None) -> dict[str, Any]:
    if not body.strip():
        return deny("EMPTY_POST")
    if len(body) > BLUESKY_MAX_CODEPOINTS or len(body.encode("utf-8")) > 3000:
        return deny("BLUESKY_TEXT_LIMIT")
    record: dict[str, Any] = {
        "$type": "app.bsky.feed.post",
        "text": body,
        "createdAt": created_at,
    }
    if language is not None:
        record["langs"] = [language]
    return {
        "operation": "com.atproto.repo.createRecord",
        # This is a RECORD ONLY. The request's repo DID and PDS URL must
        # come from a future verified host binding, never a local alias.
        "payload": {
            "collection": "app.bsky.feed.post",
            "record": record,
        },
        "providerConstraints": {
            "maxConservativeCodepoints": BLUESKY_MAX_CODEPOINTS,
            "requiresVerifiedRepoDid": True,
            "requiresAuthenticatedPds": True,
        },
        "requiredHostEvidence": [
            "verified_did_and_pds_host",
            "signed_calling_process",
            "operator_consented_post.text_scope",
            "active_revocable_grant",
            "at_uri_and_cid_confirmation",
        ],
    }


def prepare_website(title: str, body: str) -> dict[str, Any]:
    if not body.strip():
        return deny("EMPTY_POST")
    # No website-standard publishing endpoint exists. This is explicitly
    # an internal content shape for a later, site-specific owned API contract.
    return {
        "operation": "postapollo.owned_site.localDraft",
        "payload": {
            "schema": "postapollo.publisher.owned_site.local_draft.v1",
            "title": title,
            "body": body,
            "publicationState": "draft",
        },
        "providerConstraints": {
            "siteEndpoint": None,
            "requiresExplicitSiteContract": True,
        },
        "requiredHostEvidence": [
            "verified_site_ownership",
            "approved_site_specific_endpoint_contract",
            "signed_calling_process",
            "operator_consented_post.text_scope",
            "active_revocable_grant",
            "site_receipt_reconciliation",
        ],
    }


def prepare(provider: Any, title: Any, body: Any,
            created_at: Any, *, language: Any = None,
            media: Any = None) -> dict[str, Any]:
    """Prepare ONE text-only provider plan, with NO possible dispatch."""
    if provider not in PROVIDERS:
        return deny("UNSUPPORTED_PROVIDER")
    if not valid_text(title, MAX_TITLE, allow_newline=False) or not title.strip():
        return deny("INVALID_TITLE")
    if not valid_text(body, MAX_BODY, allow_newline=True):
        return deny("INVALID_BODY")
    now = check_created_at(created_at)
    if now is None:
        return deny("INVALID_CREATED_AT")
    if language is not None and (
        not isinstance(language, str) or LANGUAGE.fullmatch(language) is None):
        return deny("INVALID_LANGUAGE")
    if media not in (None, []):
        return deny("MEDIA_ADAPTER_NOT_ENABLED")
    if provider == "discord":
        result = prepare_discord(body)
    elif provider == "bluesky":
        result = prepare_bluesky(body, now, language)
    else:
        result = prepare_website(title, body)
    if "ok" in result and result["ok"] is False:
        return result
    # A body digest identifies a preview for comparison only. It is NOT
    # remote idempotency, a signature, a content commitment or a receipt.
    digest = hashlib.sha256(json.dumps(
        [VERSION, provider, title, body, now, language],
        separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "previewVersion": VERSION,
        "provider": provider,
        "requiredScope": "post.text",
        "previewFingerprint": digest,
        "previewOnly": True,
        "canDispatch": False,
        "sent": False,
        "providerReceipt": None,
        "reason": REASON_BLOCKED,
        **result,
    }


def dispatch(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Hard-deny even when a caller forges an approval flag or receipt."""
    return deny(REASON_BLOCKED)


def preview_from_json(raw: str, provider: str) -> dict[str, Any]:
    """Strict fixture/preview envelope. No account ID, URI or secret field."""
    if not isinstance(raw, str) or len(raw) > 14000:
        return deny("INVALID_PREVIEW_INPUT")
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        data = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, TypeError):
        return deny("INVALID_PREVIEW_JSON")
    if not isinstance(data, dict) or set(data) != {
        "title", "body", "createdAt", "language", "media",
    }:
        return deny("UNKNOWN_PREVIEW_FIELDS")
    return prepare(provider, data["title"], data["body"],
                   data["createdAt"], language=data["language"],
                   media=data["media"])


def main(argv: list[str]) -> int:
    import argparse
    import sys
    parser = argparse.ArgumentParser(
        description="P2.A OFFLINE provider payload preview (never sends)")
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    arguments = parser.parse_args(argv)
    try:
        raw = sys.stdin.read(14001)
    except (OSError, UnicodeError):
        result = deny("INVALID_PREVIEW_INPUT")
    else:
        result = preview_from_json(raw, arguments.provider)
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
