"""Read-only Radio Browser directory. Playback stays with the existing MPD controller.

Radio Browser is a community directory, not a trusted audio-origin registry.
Only publicly shaped HTTPS direct MP3 streams with no URL secrets are exposed;
every load still requires deliberate SELECT/LOAD and passes the MPD backend's
existing strict source validation. Network errors never change playback.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from direct_stream_source import validate_https_audio_url
from headless_mpd import MediaBackendError

_API = "https://de1.api.radio-browser.info/json/stations/search"
_PAGE_SIZE = 50
_REQUEST_ROWS = 150
_MAX_OFFSET = 10_000
_ALLOWED_SEARCH = re.compile(r"^[^\x00-\x1f\x7f]{0,120}$")
_FILTERS = {"genre": "tag", "tag": "tag", "country": "countrycode",
            "name": "name", "language": "language"}


class RadioBrowserCatalogSource:
    id = "radio-browser"

    def __init__(self, fetch=None):
        # Tests inject a fake GET transport; production uses this fixed host.
        self._fetch = fetch

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": "RADIO BROWSER // DIRECTORY",
            "available": True, "reason": "",
            "requirements": ["internet-for-discovery"],
            "capabilities": ["search"],
            "playback": {"available": False,
                         "reason": "Choose station, then existing direct-HTTPS MPD LOAD"},
            "note": "Listings are untrusted; stream support is not guaranteed",
        }

    def search(self, query: str, cursor: str | None = None) -> dict[str, Any]:
        if not isinstance(query, str) or not _ALLOWED_SEARCH.fullmatch(query):
            raise MediaBackendError("INVALID_QUERY", "Radio search must be at most 120 printable characters")
        query = query.strip()
        offset = 0
        if cursor is not None:
            if not isinstance(cursor, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,4})", cursor):
                raise MediaBackendError("INVALID_CURSOR", "Radio page cursor invalid")
            offset = int(cursor)
            if offset > _MAX_OFFSET:
                raise MediaBackendError("INVALID_CURSOR", "Radio directory paging limit exceeded")

        params = {"hidebroken": "true", "is_https": "true",
                  "codec": "MP3", "limit": str(_REQUEST_ROWS), "offset": str(offset),
                  "order": "votes", "reverse": "true"}
        if query:
            head, colon, body = query.partition(":")
            if colon and head.lower() in _FILTERS:
                if not body.strip():
                    raise MediaBackendError("INVALID_QUERY", "Radio filter needs a value")
                params[_FILTERS[head.lower()]] = body.strip()
            else:
                params["name"] = query

        payload = self._request(params)
        items = []
        seen = set()
        for row in payload:
            if not isinstance(row, dict) or row.get("lastcheckok") not in (True, 1):
                continue
            if str(row.get("codec", "")).upper() != "MP3":
                continue
            uri = row.get("url_resolved") or row.get("url")
            try:
                uri = validate_https_audio_url(uri)
            except MediaBackendError:
                continue
            # These commonly reference playlists or redirects, not direct MP3.
            if urlsplit(uri).path.lower().endswith((".m3u", ".m3u8", ".pls", ".asx", ".xspf")):
                continue
            if uri in seen:
                continue
            seen.add(uri)
            name = _clean(row.get("name"), 100)
            if not name:
                continue
            items.append({
                "ref": {"source": "direct-stream", "kind": "stream", "id": uri},
                "title": name,
                "artist": _clean(row.get("country"), 60),
                "album": _clean(row.get("tags"), 100),
                "genre": _clean(row.get("tags"), 100),
                "codec": "MP3", "live": True,
                "stationuuid": _clean(row.get("stationuuid"), 64),
                "bitrate": _bitrate(row.get("bitrate")),
            })
            if len(items) >= _PAGE_SIZE:
                break
        next_offset = offset + _REQUEST_ROWS
        return {
            "items": items, "truncated": len(payload) >= _REQUEST_ROWS,
            "totalObserved": len(items),
            "nextCursor": str(next_offset) if len(payload) >= _REQUEST_ROWS
                          and next_offset <= _MAX_OFFSET else None,
        }

    def _request(self, params: dict[str, str]) -> list[dict[str, Any]]:
        if self._fetch is not None:
            payload = self._fetch(dict(params))
        else:
            # Fixed HTTPS directory host. No station URL is fetched by discovery.
            req = Request(_API + "?" + urlencode(params),
                          headers={"Accept": "application/json",
                                   "User-Agent": "Post-Apollo-HiFi/0.1"})
            try:
                with urlopen(req, timeout=6) as response:
                    raw = response.read(1_500_001)
                if len(raw) > 1_500_000:
                    raise MediaBackendError("SOURCE_PROTOCOL", "Radio directory response too large")
                payload = json.loads(raw)
            except HTTPError as exc:
                raise MediaBackendError("SOURCE_HTTP", f"Radio directory HTTP {exc.code}") from None
            except (URLError, OSError, TimeoutError):
                raise MediaBackendError("SOURCE_OFFLINE", "Radio directory unavailable") from None
            except (ValueError, UnicodeError):
                raise MediaBackendError("SOURCE_PROTOCOL", "Invalid radio directory JSON") from None
        if not isinstance(payload, list) or len(payload) > _REQUEST_ROWS:
            raise MediaBackendError("SOURCE_PROTOCOL", "Invalid radio directory response")
        return payload


def _clean(value: Any, limit: int) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()[:limit] if isinstance(value, str) else ""


def _bitrate(value: Any) -> int:
    try:
        return max(0, min(int(value), 4096))
    except (TypeError, ValueError, OverflowError):
        return 0
