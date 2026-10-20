"""Explicit HTTPS audio-stream source for MPD, without local files or browsers.

Only operator-supplied, public-looking HTTPS streaming endpoints are accepted.
No playlist scraping, third-party video extraction or network preflight.
Do not feed refs obtained from untrusted remote catalogs into this adapter:
DNS redirection to local targets cannot be ruled out from a URL alone.
"""
from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit

from headless_mpd import MediaBackendError


_LABEL = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
_DENIED_HOSTS = ("youtube.com", "youtu.be", "googlevideo.com",
                 "spotify.com", "soundcloud.com", "music.apple.com")


def validate_https_audio_url(value: Any) -> str:
    """Fail closed on local, credentialed or opaque URLs before MPD receives one."""
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise MediaBackendError("INVALID_REF", "HTTPS stream URL must be 1..2048 characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise MediaBackendError("INVALID_REF", "Stream URL contains control characters")
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        raise MediaBackendError("INVALID_REF", "Malformed stream URL") from None
    if (parts.scheme != "https" or not hostname or not parts.netloc
        or parts.username is not None or parts.password is not None
        or parts.query or parts.fragment or port not in (None, 443)):
        raise MediaBackendError(
            "INVALID_REF",
            "Only HTTPS public streams without credentials, query or fragment are allowed",
        )
    host = hostname.lower().rstrip(".")
    if (host in ("localhost", "localhost.localdomain")
        or host.endswith((".local", ".internal", ".localhost", ".test", ".invalid"))
        or host.endswith(tuple("." + denied for denied in _DENIED_HOSTS))
        or host in _DENIED_HOSTS
        or "." not in host or host.startswith("xn--")):
        raise MediaBackendError("INVALID_REF", "Unavailable or restricted streaming host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise MediaBackendError("INVALID_REF", "Direct IP stream targets are not accepted")
    if any(not _LABEL.fullmatch(label) for label in host.split(".")):
        raise MediaBackendError("INVALID_REF", "Stream hostname is not a valid DNS name")
    # Reject whitespace / URL forms ambiguous to external clients.
    if any(ch in value for ch in (" ", "\\", "@")):
        raise MediaBackendError("INVALID_REF", "Stream URL is ambiguous")
    return value


class DirectHttpsStreamSource:
    id = "direct-stream"

    def __init__(self, backend):
        self.backend = backend

    def describe(self) -> dict[str, Any]:
        state = self.backend.probe()
        return {
            "id": self.id,
            "name": "DIRECT HTTPS // LIVE RADIO",
            "available": state["available"],
            "reason": state["reason"],
            "requirements": ["mpd-https-stream"],
            "capabilities": ["inspect", "prepare"] if state["available"] else [],
            "catalog": {"search": False, "list": False},
            "note": "Explicit authorized HTTPS audio stream only; not a YouTube player",
        }

    def inspect(self, media_ref: Any) -> dict[str, Any]:
        if (not isinstance(media_ref, dict) or media_ref.get("source") != self.id
            or media_ref.get("kind") != "stream"):
            raise MediaBackendError("INVALID_REF", "Expected direct-stream media reference")
        url = validate_https_audio_url(media_ref.get("id"))
        parts = urlsplit(url)
        return {
            "ref": {"source": self.id, "kind": "stream", "id": url},
            "title": "LIVE STREAM // " + parts.hostname,
            "artist": "",
            "album": "",
            "duration": None,
            "live": True,
        }

    def prepare(self, media_ref: Any) -> dict[str, Any]:
        item = self.inspect(media_ref)
        return {"requiredKind": "mpd-https-stream", "uri": item["ref"]["id"],
                "item": item}
