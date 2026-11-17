#!/usr/bin/env python3
"""Manually operated local FaceTime-to-iPhone relay client. No native calls.

No recipient or bearer token in argv, URL query, stdout, logs or persistence.
Does nothing unless explicitly run; never starts the relay or iPhone Shortcut.
"""
from __future__ import annotations

import argparse
import getpass
import json
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler, Request, build_opener,
)

from PhoneFaceTimeShortcutRelay import (
    MAX_REQUEST_BYTES, SCHEMA, STATES, TARGET, _load_token,
)

MAX_REPLY_BYTES = 4096
_DENIALS = (
    "faceTimeConnected", "incomingCallObserved", "canAnswer", "canHangup",
    "audioVerified", "videoStreamAvailable",
    "authenticatedAppleFaceTimeSession", "personalDataAccess",
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a private bearer token to an unexpected redirect.
        return None


def request(
    action: str, token: str, port: int, *,
    recipient: str = "", approved: bool = False,
    opener=None,
) -> dict[str, object]:
    """Fixed loopback API client. Not a connected iPhone or a call action."""
    if (action not in ("queue-audio", "queue-video", "status", "cancel")
            or not 1024 <= port <= 65535
            or type(token) is not str or len(token) < 43):
        return {"schema": SCHEMA, "state": "REFUSED"}
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
    }
    body: bytes | None = None
    if action.startswith("queue-"):
        if (approved is not True or type(recipient) is not str
                or len(recipient) > 254 or TARGET.fullmatch(recipient) is None):
            return {"schema": SCHEMA, "state": "REFUSED"}
        body = json.dumps({
            "mode": action.split("-", 1)[1],
            "target": recipient,
        }, separators=(",", ":")).encode("utf-8")
        if len(body) > MAX_REQUEST_BYTES:
            return {"schema": SCHEMA, "state": "REFUSED"}
        path = "/v1/operator/request"
    elif action == "cancel":
        body = b""
        path = "/v1/operator/cancel"
    else:
        path = "/v1/operator/status"
    if body is not None and action.startswith("queue-"):
        headers["Content-Type"] = "application/json"
    url = "http://127.0.0.1:" + str(port) + path
    call = Request(
        url, method="GET" if body is None else "POST",
        headers=headers, data=body)
    adapter = opener if opener is not None else build_opener(_NoRedirect)
    try:
        with adapter.open(call, timeout=4) as response:
            payload = response.read(MAX_REPLY_BYTES + 1)
            if len(payload) > MAX_REPLY_BYTES:
                raise ValueError("invalid response")
            result = json.loads(payload.decode("utf-8"))
            if (type(result) is not dict
                    or result.get("schema") != SCHEMA
                    or result.get("state") not in STATES
                    or type(result.get("iphoneWorkflowReportedRequest")) is not bool
                    or any(result.get(field) is not False for field in _DENIALS)):
                raise ValueError("invalid response")
            # The only displayed data are a bounded enum and non-call ACK.
            return {
                "schema": SCHEMA, "state": result["state"],
                "iphoneWorkflowReportedRequest":
                    result["iphoneWorkflowReportedRequest"],
                "faceTimeConnected": False,
            }
    except (HTTPError, URLError, OSError, ValueError, TypeError,
            UnicodeError):
        return {"schema": SCHEMA, "state": "UNAVAILABLE"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manually queue a FaceTime iPhone Shortcut request (NOT a call)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--queue-audio", action="store_true")
    group.add_argument("--queue-video", action="store_true")
    group.add_argument("--status", action="store_true")
    group.add_argument("--cancel", action="store_true")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--admin-token-file", required=True)
    args = parser.parse_args(argv)
    try:
        token = _load_token(args.admin_token_file)
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({"schema": SCHEMA, "state": "UNAVAILABLE"}))
        return 2
    if args.queue_audio or args.queue_video:
        try:
            # A recipient is never placed on the command line or stdout.
            recipient = getpass.getpass("Private FaceTime recipient: ")
            consent = input("Queue a request for your iPhone? Type PREPARE: ")
        except (EOFError, KeyboardInterrupt):
            return 2
        action = "queue-audio" if args.queue_audio else "queue-video"
        result = request(
            action, token, args.port,
            recipient=recipient, approved=consent == "PREPARE")
    else:
        result = request(
            "status" if args.status else "cancel", token, args.port)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("state") in STATES else 2


if __name__ == "__main__":
    raise SystemExit(main())
