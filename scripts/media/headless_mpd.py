"""MPD wire protocol and local-library source for the headless Hi-Fi.

Uses Python's standard library; never launches a browser, Quickshell or pactl.
One short-lived local MPD connection per operation. MPD owns sound playback.
"""
from __future__ import annotations

import socket
from typing import Any


class MediaBackendError(Exception):
    """A backend request was rejected or the backend is unavailable."""

    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def mpd_quote(value: str | int | float) -> str:
    """Quote an entire MPD argument; disallow command-line injection."""
    raw = str(value)
    if "\n" in raw or "\r" in raw or "\x00" in raw:
        raise MediaBackendError("INVALID_ARGUMENT", "Control characters in MPD argument")
    return '"' + raw.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_records(lines: list[str]) -> list[dict[str, str]]:
    """MPD emits new records on file/directory/playlist keys."""
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        if key.lower() in ("file", "directory", "playlist") and current:
            records.append(current)
            current = {}
        if key not in current:
            current[key] = value
    if current:
        records.append(current)
    return records


def properties(lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition(": ")
        if sep:
            result[key] = value
    return result


def track_item(row: dict[str, str]) -> dict[str, Any]:
    uri = row.get("file", "")
    return {
        "ref": {"source": "local-mpd", "kind": "track", "id": uri},
        "title": row.get("Title") or uri.rsplit("/", 1)[-1],
        "artist": row.get("Artist", ""),
        "album": row.get("Album", ""),
        "duration": row.get("duration") or row.get("Time") or None,
        "queueId": row.get("Id"),
        "queuePosition": row.get("Pos"),
    }


class MpdBackend:
    id = "mpd"
    required_kind = "mpd-local-track"

    def __init__(self, host: str = "127.0.0.1", port: int = 6600, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def command(self, verb: str, *args: str | int | float) -> list[str]:
        if not verb.isascii() or not verb.replace("_", "").isalnum():
            raise MediaBackendError("INVALID_ARGUMENT", "Invalid MPD command")
        wire = verb + "".join(" " + mpd_quote(arg) for arg in args) + "\n"
        try:
            with socket.create_connection((self.host, self.port), self.timeout) as conn:
                conn.settimeout(self.timeout)
                with conn.makefile("r", encoding="utf-8", errors="replace") as reader:
                    greeting = reader.readline(256)
                    if not greeting.startswith("OK MPD "):
                        raise MediaBackendError("BACKEND_PROTOCOL", "No valid MPD greeting")
                    conn.sendall(wire.encode("utf-8"))
                    output: list[str] = []
                    # Bound response size; no unbounded search/list responses.
                    total = 0
                    for _ in range(50000):
                        line = reader.readline(65537)
                        if not line or len(line) > 65536:
                            raise MediaBackendError("BACKEND_PROTOCOL", "Truncated/oversize MPD reply")
                        text = line.rstrip("\r\n")
                        if text == "OK":
                            return output
                        if text.startswith("ACK "):
                            raise MediaBackendError("BACKEND_REJECTED", text[:400])
                        total += len(line)
                        if total > 5_000_000:
                            raise MediaBackendError("BACKEND_PROTOCOL", "MPD reply too large")
                        output.append(text)
                    raise MediaBackendError("BACKEND_PROTOCOL", "Too many MPD reply lines")
        except (OSError, UnicodeError) as exc:
            raise MediaBackendError("BACKEND_OFFLINE", type(exc).__name__ + ": " + str(exc)) from exc

    def probe(self) -> dict[str, Any]:
        try:
            state = properties(self.command("status"))
        except MediaBackendError as exc:
            return {"id": self.id, "available": False, "reason": exc.reason,
                    "capabilities": []}
        return {
            "id": self.id,
            "available": True,
            "reason": "",
            "capabilities": ["cue", "play", "pause", "stop", "next",
                             "previous", "seek", "queue", "observe"],
            "state": state.get("state", "unknown"),
        }

    def observe(self) -> dict[str, Any]:
        status = properties(self.command("status"))
        song = properties(self.command("currentsong"))
        return {
            "backend": self.id,
            "state": status.get("state", "unknown"),
            "elapsed": status.get("elapsed"),
            "duration": status.get("duration"),
            "queueLength": int(status.get("playlistlength", 0)),
            "current": track_item(song) if song.get("file") else None,
            "observed": True,
        }

    def queue(self) -> list[dict[str, Any]]:
        return [track_item(row) for row in parse_records(self.command("playlistinfo"))
                if row.get("file")]

    def cue(self, request: dict[str, Any]) -> str:
        if request.get("requiredKind") != self.required_kind:
            raise MediaBackendError("UNSUPPORTED", "MPD cannot cue this media kind")
        uri = request.get("uri", "")
        if not isinstance(uri, str) or not uri:
            raise MediaBackendError("INVALID_REF", "No MPD library file supplied")
        response = properties(self.command("addid", uri))
        song_id = response.get("Id")
        if not song_id or not song_id.isdecimal():
            raise MediaBackendError("BACKEND_PROTOCOL", "MPD addid returned no song ID")
        # addid queues a track without starting playback.
        return song_id

    def play_id(self, song_id: str) -> None:
        if not song_id.isdecimal():
            raise MediaBackendError("INVALID_ARGUMENT", "Invalid MPD queue ID")
        self.command("playid", song_id)

    def transport(self, op: str, seconds: int | None = None) -> None:
        commands = {
            "pause": ("pause", ("1",)),
            "stop": ("stop", ()),
            "next": ("next", ()),
            "previous": ("previous", ()),
        }
        if op == "seek_relative":
            if seconds is None or seconds == 0 or abs(seconds) > 600:
                raise MediaBackendError("INVALID_ARGUMENT", "Seek must be ±1..600 seconds")
            self.command("seekcur", f"{seconds:+d}")
            return
        if op not in commands:
            raise MediaBackendError("UNSUPPORTED", "MPD transport not supported: " + op)
        verb, args = commands[op]
        self.command(verb, *args)

    def add(self, uri: str) -> str:
        return self.cue({"requiredKind": self.required_kind, "uri": uri})

    def remove(self, song_id: str) -> None:
        if not song_id.isdecimal():
            raise MediaBackendError("INVALID_ARGUMENT", "Invalid MPD queue ID")
        self.command("deleteid", song_id)

    def clear(self) -> None:
        self.command("clear")


class LocalMpdSource:
    id = "local-mpd"

    def __init__(self, backend: MpdBackend):
        self.backend = backend

    def describe(self) -> dict[str, Any]:
        p = self.backend.probe()
        return {
            "id": self.id, "name": "LOCAL // MPD LIBRARY",
            "available": p["available"], "reason": p["reason"],
            "requirements": ["mpd-local-track"],
            "capabilities": ["search", "inspect", "prepare"] if p["available"] else [],
        }

    def search(self, query: str) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 256:
            raise MediaBackendError("INVALID_ARGUMENT", "Search requires 1..256 characters")
        rows = [track_item(row) for row in parse_records(self.backend.command("search", "any", query))
                if row.get("file")]
        return {"items": rows[:100], "totalObserved": len(rows),
                "truncated": len(rows) > 100}

    def inspect(self, media_ref: dict[str, str]) -> dict[str, Any]:
        uri = self._valid_ref(media_ref)
        rows = parse_records(self.backend.command("lsinfo", uri))
        exact = [row for row in rows if row.get("file") == uri]
        if len(exact) != 1:
            raise MediaBackendError("NOT_FOUND", "No exact track in the MPD library")
        return track_item(exact[0])

    def prepare(self, media_ref: dict[str, str]) -> dict[str, Any]:
        item = self.inspect(media_ref)
        return {"requiredKind": "mpd-local-track",
                "uri": item["ref"]["id"], "item": item}

    def _valid_ref(self, value: Any) -> str:
        if not isinstance(value, dict) or value.get("source") != self.id or value.get("kind") != "track":
            raise MediaBackendError("INVALID_REF", "Expected a local-mpd track reference")
        uri = value.get("id")
        if not isinstance(uri, str) or not uri or len(uri) > 4096:
            raise MediaBackendError("INVALID_REF", "Invalid MPD track ID")
        return uri
