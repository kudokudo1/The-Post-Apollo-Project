"""YouTube Data API v3 catalog ONLY. No media playback, audio extraction or download.

Requires a user-supplied API key in YOUTUBE_API_KEY, never in the repository.
The official embedded-player API does not permit hidden/background playback.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from headless_mpd import MediaBackendError

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]{10,128}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,256}$")
_API_BASE = "https://www.googleapis.com/youtube/v3/"


def _required_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise MediaBackendError("INVALID_ARGUMENT", f"Invalid {field}")
    return value.strip()


def _video_item(video_id: str, snippet: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref": {"source": "youtube", "kind": "video", "id": video_id},
        "title": snippet.get("title") or video_id,
        "artist": snippet.get("channelTitle") or "",
        "channelId": snippet.get("channelId") or "",
        "description": snippet.get("description") or "",
        "playback": {"available": False,
                     "reason": "A supported visible YouTube player must be integrated separately"},
    }


class YouTubeCatalogSource:
    id = "youtube"

    def __init__(self, api_key: str | None = None, fetch=None):
        self._key = api_key if api_key is not None else os.environ.get("YOUTUBE_API_KEY", "")
        self._fetch = fetch

    def describe(self) -> dict[str, Any]:
        configured = bool(self._key)
        return {
            "id": self.id, "name": "YOUTUBE // CATALOG",
            "available": configured,
            "reason": "" if configured else "Configure YOUTUBE_API_KEY to browse the catalog",
            "requirements": ["youtube-data-api-key"],
            "capabilities": ["search", "inspect", "list"] if configured else [],
            "playback": {"available": False, "reason": "No compliant playback backend registered"},
        }

    def _request(self, resource: str, params: dict[str, str]) -> dict[str, Any]:
        if not self._key:
            raise MediaBackendError("SOURCE_NOT_CONFIGURED", "YouTube catalog requires YOUTUBE_API_KEY")
        if resource not in ("search", "videos", "playlistItems"):
            raise MediaBackendError("INVALID_REQUEST", "Unsupported YouTube Data API resource")
        if self._fetch is not None:
            payload = self._fetch(resource, dict(params))
        else:
            query = urlencode({**params, "key": self._key})
            url = _API_BASE + resource + "?" + query
            try:
                req = Request(url, headers={"Accept": "application/json", "User-Agent": "Post-Apollo-HiFi/0.1"})
                with urlopen(req, timeout=6) as response:
                    raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise MediaBackendError("SOURCE_PROTOCOL", "YouTube response too large")
                payload = json.loads(raw)
            except HTTPError as exc:
                # Exception repr/url can expose the API key. Never echo either.
                if exc.code in (401, 403):
                    raise MediaBackendError("SOURCE_PERMISSION", "YouTube API rejected credentials/quota") from None
                raise MediaBackendError("SOURCE_HTTP", f"YouTube HTTP {exc.code}") from None
            except (URLError, OSError, TimeoutError):
                raise MediaBackendError("SOURCE_OFFLINE", "YouTube API currently unreachable") from None
            except (UnicodeError, ValueError):
                raise MediaBackendError("SOURCE_PROTOCOL", "Invalid YouTube API JSON") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise MediaBackendError("SOURCE_PROTOCOL", "Invalid YouTube catalog response shape")
        return payload

    def search(self, query: str, cursor: str | None = None) -> dict[str, Any]:
        query = _required_text(query, "query", 256)
        params = {"part": "snippet", "q": query, "type": "video", "maxResults": "25"}
        if cursor is not None:
            params["pageToken"] = self._cursor(cursor)
        payload = self._request("search", params)
        items = []
        for row in payload["items"]:
            if not isinstance(row, dict):
                continue
            video_id = row.get("id", {}).get("videoId") if isinstance(row.get("id"), dict) else None
            if isinstance(video_id, str) and _VIDEO_ID.fullmatch(video_id):
                items.append(_video_item(video_id, row.get("snippet") or {}))
        return {"items": items, "nextCursor": payload.get("nextPageToken"), "truncated": False,
                "totalObserved": len(items)}

    def list(self, collection_ref: dict[str, Any], cursor: str | None = None) -> dict[str, Any]:
        if not isinstance(collection_ref, dict) or (collection_ref.get("source"), collection_ref.get("kind")) != ("youtube", "playlist"):
            raise MediaBackendError("INVALID_REF", "Expected YouTube playlist reference")
        playlist_id = _required_text(collection_ref.get("id"), "playlist id", 128)
        if not _PLAYLIST_ID.fullmatch(playlist_id):
            raise MediaBackendError("INVALID_REF", "Invalid playlist id")
        params = {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": "50"}
        if cursor is not None:
            params["pageToken"] = self._cursor(cursor)
        payload = self._request("playlistItems", params)
        items = []
        for row in payload["items"]:
            if not isinstance(row, dict):
                continue
            details = row.get("contentDetails") or {}
            snippet = row.get("snippet") or {}
            video_id = details.get("videoId") or (snippet.get("resourceId") or {}).get("videoId")
            if isinstance(video_id, str) and _VIDEO_ID.fullmatch(video_id):
                items.append(_video_item(video_id, snippet))
        return {"items": items, "nextCursor": payload.get("nextPageToken"), "truncated": False,
                "totalObserved": len(items), "collection": collection_ref}

    def inspect(self, media_ref: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(media_ref, dict) or (media_ref.get("source"), media_ref.get("kind")) != ("youtube", "video"):
            raise MediaBackendError("INVALID_REF", "Expected a YouTube video reference")
        video_id = _required_text(media_ref.get("id"), "video id", 11)
        if not _VIDEO_ID.fullmatch(video_id):
            raise MediaBackendError("INVALID_REF", "Invalid YouTube video id")
        payload = self._request("videos", {"part": "snippet", "id": video_id, "maxResults": "1"})
        for row in payload["items"]:
            if isinstance(row, dict) and row.get("id") == video_id:
                return _video_item(video_id, row.get("snippet") or {})
        raise MediaBackendError("NOT_FOUND", "Video unavailable in YouTube catalog")

    def prepare(self, media_ref: dict[str, Any]) -> dict[str, Any]:
        # Do not call any external API or attempt playback to "work around" policy.
        raise MediaBackendError(
            "PLAYBACK_UNAVAILABLE",
            "YouTube catalog items cannot be loaded until a supported visible player is registered",
        )

    @staticmethod
    def _cursor(value: str) -> str:
        if not isinstance(value, str) or not _TOKEN.fullmatch(value):
            raise MediaBackendError("INVALID_ARGUMENT", "Invalid pagination token")
        return value
