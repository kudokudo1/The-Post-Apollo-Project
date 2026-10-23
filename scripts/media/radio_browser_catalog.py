"""Read-only Radio Browser directory. Playback stays with the existing MPD controller.

Radio Browser is a community directory, not a trusted audio-origin registry.
Only station metadata and stable UUID references are exposed to the UI.
A selected station's private URI can only reach a guarded loopback relay,
never MPD directly. Network failures do not change the existing loaded song.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from direct_stream_source import validate_https_audio_url
from headless_mpd import MediaBackendError

# Fixed, trusted directory endpoints only. No station URL becomes an HTTP
# request during discovery. Fallback is bounded by the CLI's 5s timeout.
_API_MIRRORS = (
    "https://de1.api.radio-browser.info/json/stations/search",
    "https://all.api.radio-browser.info/json/stations/search",
)
_PAGE_SIZE = 50
_REQUEST_ROWS = 150
_MAX_OFFSET = 10_000
_ALLOWED_SEARCH = re.compile(r"^[^\x00-\x1f\x7f]{0,120}$")
_FILTERS = {"genre": "tag", "tag": "tag", "country": "countrycode",
            "name": "name", "language": "language"}
_DEFAULT_CLIENT = "default"
_MAX_BROWSE_CLIENTS = 4
_CLIENT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")


def validate_browse_client(client: str) -> str:
    if not isinstance(client, str) or not _CLIENT_ID.fullmatch(client):
        raise MediaBackendError("INVALID_CLIENT", "Invalid radio browsing client")
    return client


class _RejectRedirects(HTTPRedirectHandler):
    """Never follow a directory mirror redirect to an untrusted network host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RadioBrowserCatalogSource:
    id = "radio-browser"

    def __init__(self, fetch=None, relay=None):
        # Tests inject a fake GET transport; production uses fixed trusted mirrors.
        self._fetch = fetch
        self._relay = relay
        # Each consumer sees only its own latest search batch. The old default
        # client remains the unscoped Hi-Fi API. Playback and relay are shared.
        self._browse_batches: dict[str, tuple[dict[str, Any], dict[str, str]]] = {}
        self._known_stations: dict[str, dict[str, Any]] = {}
        self._station_urls: dict[str, str] = {}

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": "RADIO BROWSER // DIRECTORY",
            "available": True, "reason": "",
            "requirements": ["internet-for-discovery"],
            "capabilities": ["search", "inspect"] + (["prepare"] if self._relay else []),
            "playback": {"available": self._relay is not None,
                         "reason": ("Guarded local MP3 relay; requires explicit LOAD and PLAY"
                                    if self._relay else "Radio relay not registered")},
            "note": "Listings are untrusted; stream support is not guaranteed",
        }

    def search(self, query: str, cursor: str | None = None,
               client: str = _DEFAULT_CLIENT) -> dict[str, Any]:
        client = validate_browse_client(client)
        if client not in self._browse_batches and len(self._browse_batches) >= _MAX_BROWSE_CLIENTS:
            raise MediaBackendError("CLIENT_LIMIT", "Too many radio browse clients")
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
        known = {}
        station_urls = {}
        scanned = 0
        for row in payload:
            scanned += 1
            if not isinstance(row, dict) or row.get("lastcheckok") not in (True, 1):
                continue
            if str(row.get("codec", "")).upper() != "MP3":
                continue
            uri = row.get("url_resolved") or row.get("url")
            try:
                uri = validate_https_audio_url(uri)
                station_id = str(uuid.UUID(str(row.get("stationuuid", ""))))
            except (MediaBackendError, ValueError, AttributeError):
                continue
            # These commonly reference playlists or redirects, not direct MP3.
            if urlsplit(uri).path.lower().endswith((".m3u", ".m3u8", ".pls", ".asx", ".xspf")):
                continue
            if uri in seen or station_id in known:
                continue
            seen.add(uri)
            name = _clean(row.get("name"), 100)
            if not name:
                continue
            item = {
                "ref": {"source": self.id, "kind": "station", "id": station_id},
                "title": name,
                "artist": _clean(row.get("countrycode"), 2),
                "album": _clean(row.get("tags"), 100),
                "genre": _clean(row.get("tags"), 100),
                "codec": "MP3", "live": True,
                "stationuuid": station_id,
                "streamHost": urlsplit(uri).hostname,
                "bitrate": _bitrate(row.get("bitrate")),
                "playback": {"available": self._relay is not None,
                             "reason": "Guarded MP3 relay" if self._relay
                                       else "Relay unavailable"},
            }
            items.append(item)
            known[station_id] = item
            station_urls[station_id] = uri
            if len(items) >= _PAGE_SIZE:
                break
        # Cursor follows the number of rows actually consumed, not the
        # requested batch size: usable hits after row 50 must not be skipped.
        self._browse_batches[client] = (known, station_urls)
        if client == _DEFAULT_CLIENT:
            # Preserve the historical fields for older tests and consumers.
            self._known_stations = known
            self._station_urls = station_urls
        next_offset = offset + scanned
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
            # No arbitrary redirects. Fallback stays on approved Radio Browser
            # mirror names and within the existing 5-second socket timeout.
            opener = build_opener(_RejectRedirects())
            payload = None
            error = "SOURCE_OFFLINE"
            for endpoint in _API_MIRRORS:
                req = Request(endpoint + "?" + urlencode(params),
                              headers={"Accept": "application/json",
                                       "User-Agent": "Post-Apollo-HiFi/0.1"})
                try:
                    with opener.open(req, timeout=1.8) as response:
                        raw = response.read(1_500_001)
                    if len(raw) > 1_500_000:
                        raise MediaBackendError("SOURCE_PROTOCOL", "Radio directory response too large")
                    payload = json.loads(raw)
                    break
                except HTTPError:
                    error = "SOURCE_HTTP"
                except (URLError, OSError, TimeoutError):
                    error = "SOURCE_OFFLINE"
                except (ValueError, UnicodeError):
                    error = "SOURCE_PROTOCOL"
            if payload is None:
                raise MediaBackendError(error, "Radio directory unavailable or invalid") from None
        if not isinstance(payload, list) or len(payload) > _REQUEST_ROWS:
            raise MediaBackendError("SOURCE_PROTOCOL", "Invalid radio directory response")
        return payload

    def inspect(self, media_ref: Any, client: str = _DEFAULT_CLIENT) -> dict[str, Any]:
        client = validate_browse_client(client)
        if (not isinstance(media_ref, dict)
                or media_ref.get("source") != self.id
                or media_ref.get("kind") != "station"):
            raise MediaBackendError("INVALID_REF", "Expected radio-directory station")
        station_id = media_ref.get("id")
        batch = self._browse_batches.get(client, ({}, {}))
        item = batch[0].get(station_id)
        if item is None:
            raise MediaBackendError("INVALID_REF", "Station not in current radio results")
        return item.copy()

    def prepare(self, media_ref: Any, client: str = _DEFAULT_CLIENT) -> dict[str, Any]:
        # A UUID must have been returned to this particular browsing client.
        # Other clients' stations and private origin URLs stay inaccessible.
        client = validate_browse_client(client)
        item = self.inspect(media_ref, client)
        if self._relay is None:
            raise MediaBackendError("PLAYBACK_UNAVAILABLE",
                                    "Guarded radio relay not available")
        uri = self._browse_batches[client][1].get(item["stationuuid"])
        if not uri:
            raise MediaBackendError("INVALID_REF", "Station URI not in current results")
        return {"requiredKind": "mpd-guarded-radio",
                "uri": self._relay.register(uri), "item": item}


def _clean(value: Any, limit: int) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()[:limit] if isinstance(value, str) else ""


def _bitrate(value: Any) -> int:
    try:
        return max(0, min(int(value), 4096))
    except (TypeError, ValueError, OverflowError):
        return 0
