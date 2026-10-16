"""Universal Hi-Fi controller v0: separate browser, selection, load and session.

No Qt, Quickshell or PulseAudio dependencies. Internet catalog is opt-in.
Adapters are supplied at construction; the controller owns routing decisions.
"""
from __future__ import annotations

from typing import Any

from headless_mpd import LocalMpdSource, MediaBackendError, MpdBackend
from youtube_catalog import YouTubeCatalogSource


class MediaController:
    protocol_version = 1

    def __init__(self, backend: MpdBackend | None = None):
        mpd = backend if backend is not None else MpdBackend()
        self.backends = {mpd.id: mpd}
        local = LocalMpdSource(mpd)
        youtube = YouTubeCatalogSource()
        self.sources = {local.id: local, youtube.id: youtube}
        self.browse_context: dict[str, Any] | None = None
        self.selection: dict[str, Any] | None = None
        self.loaded: dict[str, Any] | None = None
        self.active_backend: str | None = None
        self.owned_active_id: str | None = None
        self.generation = 0

    def _advance(self) -> None:
        self.generation += 1

    def _source(self, source_id: Any) -> Any:
        if not isinstance(source_id, str) or source_id not in self.sources:
            raise MediaBackendError("UNKNOWN_SOURCE", "Source not registered")
        return self.sources[source_id]

    def _media_ref(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            raise MediaBackendError("INVALID_REF", "Expected a media reference object")
        self._source(value.get("source"))
        return value

    def _backend_for(self, prepared: dict[str, Any]) -> MpdBackend:
        eligible = [
            backend for backend in self.backends.values()
            if backend.required_kind == prepared.get("requiredKind")
            and backend.probe()["available"]
        ]
        if not eligible:
            raise MediaBackendError("NO_COMPATIBLE_BACKEND", "No available backend can cue this source")
        if len(eligible) != 1:
            raise MediaBackendError("AMBIGUOUS_BACKEND", "Backend selection needs an explicit override")
        return eligible[0]

    def _bound_backend(self) -> MpdBackend:
        if self.active_backend not in self.backends:
            raise MediaBackendError("NO_LOADED_MEDIA", "Load a track before controlling playback")
        return self.backends[self.active_backend]

    def _verify_current_ownership(self) -> MpdBackend:
        backend = self._bound_backend()
        if self.owned_active_id is None:
            raise MediaBackendError("NO_OWNED_PLAYBACK", "Start playback through this controller first")
        current = backend.observe()["current"]
        current_id = str(current["queueId"]) if current and current.get("queueId") else None
        if current_id != self.owned_active_id:
            self.owned_active_id = None
            self._advance()
            raise MediaBackendError("PLAYBACK_CHANGED_EXTERNALLY",
                                    "MPD's current track changed outside this controller")
        return backend

    def _session(self) -> dict[str, Any]:
        if not self.active_backend:
            return {"backend": None, "state": "unloaded", "observed": True,
                    "current": None, "ownedByController": False}
        try:
            result = self._bound_backend().observe()
            current = result.get("current")
            current_id = str(current["queueId"]) if current and current.get("queueId") else None
            # Observing a mismatch invalidates ownership but never modifies MPD.
            if self.owned_active_id is not None and current_id != self.owned_active_id:
                self.owned_active_id = None
                self._advance()
            result["ownedByController"] = (
                self.owned_active_id is not None and current_id == self.owned_active_id
            )
            return result
        except MediaBackendError as exc:
            return {"backend": self.active_backend, "state": "unavailable",
                    "observed": False, "reason": exc.reason,
                    "ownedByController": False, "current": None}

    def snapshot(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "sources": [source.describe() for source in self.sources.values()],
            "browse": self.browse_context,
            "selection": self.selection,
            "loaded": self.loaded,
            "session": self._session(),
            "visualization": {"mode": "desktop", "playerAvailable": False},
            "audio": {"playerVolume": "unavailable", "playerCava": "unavailable"},
        }

    def dispatch(self, op: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        if args is None:
            args = {}
        if not isinstance(op, str) or not isinstance(args, dict):
            raise MediaBackendError("INVALID_REQUEST", "Expected operation and arguments object")

        if op == "health":
            return {"api": self.protocol_version, "ready": True,
                    "backend": self.backends["mpd"].probe()}
        if op == "sources":
            return {"sources": [source.describe() for source in self.sources.values()]}
        if op == "snapshot":
            return self.snapshot()

        if op == "search":
            source = self._source(args.get("source", "local-mpd"))
            query = args.get("query")
            cursor = args.get("cursor")
            if source.id == "youtube":
                result = source.search(query, cursor)
            else:
                if cursor is not None:
                    raise MediaBackendError("PAGINATION_UNSUPPORTED",
                                            "MPD library search is not paginated")
                result = source.search(query)
            # A search updates browsing only. Selection/loaded/MPD stay untouched.
            self.browse_context = {"source": source.id, "query": query,
                                   "items": result["items"], "truncated": result["truncated"],
                                   "totalObserved": result["totalObserved"],
                                   "nextCursor": result.get("nextCursor")}
            self._advance()
            return {"browse": self.browse_context}

        if op == "list":
            source = self._source(args.get("source"))
            if not hasattr(source, "list"):
                raise MediaBackendError("UNSUPPORTED", "Source cannot list collections")
            result = source.list(args.get("collection"), args.get("cursor"))
            self.browse_context = {"source": source.id, "collection": args.get("collection"),
                                   "items": result["items"], "truncated": result["truncated"],
                                   "totalObserved": result["totalObserved"],
                                   "nextCursor": result.get("nextCursor")}
            self._advance()
            return {"browse": self.browse_context}

        if op == "inspect":
            ref = self._media_ref(args.get("ref"))
            return {"item": self._source(ref["source"]).inspect(ref)}

        if op == "select":
            ref = self._media_ref(args.get("ref"))
            item = self._source(ref["source"]).inspect(ref)
            self.selection = item["ref"].copy()
            self._advance()
            return {"selection": self.selection}

        if op == "load":
            ref = args.get("ref") if args.get("ref") is not None else self.selection
            ref = self._media_ref(ref)
            autoplay = args.get("autoplay", False)
            if not isinstance(autoplay, bool):
                raise MediaBackendError("INVALID_ARGUMENT", "autoplay must be boolean")
            prepared = self._source(ref["source"]).prepare(ref)
            backend = self._backend_for(prepared)
            # Cue is only an addid: it does not call playid or interrupt MPD.
            queue_id = backend.cue(prepared)
            self.loaded = {"ref": prepared["item"]["ref"], "item": prepared["item"],
                           "backend": backend.id, "queueId": queue_id}
            self.active_backend = backend.id
            self._advance()
            if autoplay:
                backend.play_id(queue_id)
                self.owned_active_id = queue_id
                self._advance()
            return {"loaded": self.loaded, "autoplay": autoplay,
                    "commandIssued": True, "session": self._session()}

        if op == "queue":
            backend = self.backends["mpd"]
            return {"items": backend.queue()}

        if op == "queue_add":
            ref = self._media_ref(args.get("ref"))
            prepared = self._source(ref["source"]).prepare(ref)
            backend = self._backend_for(prepared)
            queue_id = backend.cue(prepared)
            self._advance()
            return {"queueId": queue_id, "ref": prepared["item"]["ref"],
                    "commandIssued": True}

        if op == "queue_remove":
            queue_id = args.get("queueId")
            if not isinstance(queue_id, str) or not queue_id.isdecimal():
                raise MediaBackendError("INVALID_ARGUMENT", "Valid queueId string required")
            current = self.backends["mpd"].observe().get("current")
            active_id = str(current["queueId"]) if current and current.get("queueId") else None
            if queue_id == active_id:
                raise MediaBackendError("ACTIVE_TRACK", "Cannot remove the current MPD track")
            self.backends["mpd"].remove(queue_id)
            if self.loaded and queue_id == self.loaded["queueId"]:
                self.loaded = None
                self.active_backend = None
                self.owned_active_id = None
            self._advance()
            return {"removed": queue_id, "commandIssued": True}

        if op == "play":
            if not self.loaded:
                raise MediaBackendError("NO_LOADED_MEDIA", "Select and load music first")
            backend = self._bound_backend()
            backend.play_id(self.loaded["queueId"])
            self.owned_active_id = self.loaded["queueId"]
            self._advance()
            return {"commandIssued": True, "session": self._session()}

        if op in ("pause", "stop", "next", "previous", "seek_relative"):
            backend = self._verify_current_ownership()
            seconds = args.get("seconds") if op == "seek_relative" else None
            if op == "seek_relative" and (isinstance(seconds, bool)
                                           or not isinstance(seconds, int)):
                raise MediaBackendError("INVALID_ARGUMENT", "Integer seconds required")
            backend.transport(op, seconds)
            if op in ("next", "previous"):
                observed = backend.observe()
                current = observed.get("current")
                self.owned_active_id = (
                    str(current["queueId"]) if current and current.get("queueId") else None
                )
            if op == "stop":
                # Preserve loaded cassette while relinquishing live playback.
                self.owned_active_id = None
            self._advance()
            return {"commandIssued": True, "session": self._session()}

        if op == "set_player_volume" or op == "set_visualization_mode":
            raise MediaBackendError("UNAVAILABLE",
                                    "Player-only audio routing/visualizer not verified")

        raise MediaBackendError("UNKNOWN_OPERATION", "Unknown operation: " + op)

    def request(self, request: Any) -> dict[str, Any]:
        request_id = request.get("id") if isinstance(request, dict) else None
        try:
            if not isinstance(request, dict) or request.get("version") != self.protocol_version:
                raise MediaBackendError("INVALID_REQUEST", "Expected version 1 JSON object")
            result = self.dispatch(request.get("op"), request.get("args", {}))
            return {"version": self.protocol_version, "id": request_id, "ok": True,
                    "result": result, "error": None, "generation": self.generation}
        except MediaBackendError as exc:
            return {"version": self.protocol_version, "id": request_id, "ok": False,
                    "result": None, "error": {"code": exc.code, "reason": exc.reason},
                    "generation": self.generation}
        except (TypeError, ValueError, KeyError) as exc:
            return {"version": self.protocol_version, "id": request_id, "ok": False,
                    "result": None, "error": {"code": "INVALID_REQUEST",
                                             "reason": str(exc)[:250]},
                    "generation": self.generation}
