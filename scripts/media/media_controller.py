"""Universal Hi-Fi controller v0: separate browser, selection, load and session.

No Qt, Quickshell or PulseAudio dependencies. Internet catalog is opt-in.
Adapters are supplied at construction; the controller owns routing decisions.
"""
from __future__ import annotations

from typing import Any

from headless_mpd import LocalMpdSource, MediaBackendError, MpdBackend
from youtube_catalog import YouTubeCatalogSource
from media_intent_store import IntentStore
from mpd_audio_probe import MpdAudioEvidenceProbe
from direct_stream_source import DirectHttpsStreamSource
from radio_browser_catalog import RadioBrowserCatalogSource, validate_browse_client


class MediaController:
    protocol_version = 1

    def __init__(self, backend: MpdBackend | None = None,
                 intent_store: IntentStore | None = None, radio_relay=None):
        mpd = backend if backend is not None else MpdBackend()
        if radio_relay is not None:
            mpd.radio_relay = radio_relay
        self.backends = {mpd.id: mpd}
        local = LocalMpdSource(mpd)
        youtube = YouTubeCatalogSource()
        stream = DirectHttpsStreamSource(mpd)
        radio = RadioBrowserCatalogSource(relay=radio_relay)
        self.sources = {local.id: local, youtube.id: youtube, stream.id: stream,
                        radio.id: radio}
        self.audio_probe = MpdAudioEvidenceProbe(mpd)
        self.browse_context: dict[str, Any] | None = None
        self.selection: dict[str, Any] | None = None
        # Optional source-scoped radio clients; default Hi-Fi remains legacy.
        self.browse_contexts: dict[str, dict[str, Any]] = {}
        self.scoped_selections: dict[str, dict[str, Any]] = {}
        self.loaded: dict[str, Any] | None = None
        self.active_backend: str | None = None
        self.owned_active_id: str | None = None
        # Ownership belongs to the playing queue entry, not the next cassette.
        self.owned_active: dict[str, Any] | None = None
        self.generation = 0
        self.intent_store = intent_store
        self.persistence_error: str | None = None
        if intent_store is not None:
            self._restore_intent()

    def _save_intent(self) -> None:
        if self.intent_store is None:
            return
        try:
            # A session relay URL vanishes on service restart. Do not persist
            # an unusable loaded radio stream or accidentally adopt playback.
            durable = (None if self.loaded and
                       self.loaded["ref"]["source"] == "radio-browser"
                       else self.loaded)
            self.intent_store.save(self.selection, durable)
            self.persistence_error = None
        except (OSError, ValueError, PermissionError, UnicodeError):
            # The MPD mutation may already have happened; never falsely report
            # playback failure just because a subsequent state save failed.
            self.persistence_error = "STATE_SAVE_FAILED"

    def _restore_intent(self) -> None:
        try:
            saved = self.intent_store.load()
        except (OSError, ValueError, PermissionError, UnicodeError):
            self.persistence_error = "STATE_LOAD_FAILED"
            return
        self.selection = saved.get("selection")
        pending = saved.get("loaded")
        # Never adopt control of the currently playing MPD song. A saved queue
        # ID is only usable when it still matches the exact saved library URI.
        if pending:
            try:
                matches = [x for x in self.backends["mpd"].queue()
                           if str(x.get("queueId")) == pending["queueId"]
                           and x.get("ref") == pending["ref"]]
            except MediaBackendError:
                matches = []
            if len(matches) == 1:
                self.loaded = {"ref": pending["ref"], "item": matches[0],
                               "backend": "mpd", "queueId": pending["queueId"]}
                self.active_backend = "mpd"
        self.owned_active_id = None
        self.owned_active = None
        if self.selection or self.loaded:
            self._advance()

    def _queue_matches(self, backend: MpdBackend, entry: dict[str, Any]) -> bool:
        target_id, target_ref = entry["queueId"], entry["ref"]
        if target_ref.get("source") == "radio-browser":
            uri = entry.get("cueUri")
            return bool(uri and getattr(backend, "radio_relay", None)
                        and backend.radio_relay.owns(uri)
                        and any(str(x.get("queueId")) == target_id
                                and x.get("ref", {}).get("id") == uri
                                for x in backend.queue()))
        return any(str(x.get("queueId")) == target_id
                   and x.get("ref") == target_ref for x in backend.queue())

    def _verify_loaded_queue(self) -> MpdBackend:
        backend = self._bound_backend()
        assert self.loaded is not None
        if not self._queue_matches(backend, self.loaded):
            self.loaded = None
            if self.owned_active_id is None:
                self.active_backend = None
            self._save_intent()
            self._advance()
            raise MediaBackendError("LOADED_TRACK_STALE",
                                    "Saved MPD queue item disappeared or changed")
        return backend

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
            if prepared.get("requiredKind", "") in getattr(
                backend, "required_kinds", (backend.required_kind,))
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
        if self.owned_active_id is None or self.owned_active is None:
            raise MediaBackendError("NO_OWNED_PLAYBACK", "Start playback through this controller first")
        current = backend.observe()["current"]
        current_id = str(current["queueId"]) if current and current.get("queueId") else None
        if current_id != self.owned_active_id:
            self.owned_active_id = None
            self.owned_active = None
            self._advance()
            raise MediaBackendError("PLAYBACK_CHANGED_EXTERNALLY",
                                    "MPD's current track changed outside this controller")
        if not self._queue_matches(backend, self.owned_active):
            self.owned_active_id = None
            self.owned_active = None
            self._advance()
            raise MediaBackendError("OWNED_TRACK_STALE",
                                    "The active MPD queue entry changed")
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
                self.owned_active = None
                self._advance()
            result["ownedByController"] = (
                self.owned_active_id is not None and current_id == self.owned_active_id
            )
            return result
        except MediaBackendError as exc:
            return {"backend": self.active_backend, "state": "unavailable",
                    "observed": False, "reason": exc.reason,
                    "ownedByController": False, "current": None}

    def _loaded_radio_health(self) -> dict[str, Any] | None:
        if not self.loaded or self.loaded.get("ref", {}).get("source") != "radio-browser":
            return None
        relay = getattr(self.backends["mpd"], "radio_relay", None)
        observe = getattr(relay, "health", None)
        if not callable(observe):
            return {"state": "unknown", "bytesReceived": 0, "errorCode": None}
        return observe(self.loaded.get("cueUri"))

    def _client(self, args: dict[str, Any]) -> str:
        return validate_browse_client(args.get("client", "default"))

    def _selection_for(self, client: str) -> dict[str, Any] | None:
        return self.selection if client == "default" else self.scoped_selections.get(client)

    def _source_for_client(self, ref: dict[str, str], client: str) -> Any:
        source = self._source(ref["source"])
        if client != "default" and source.id != "radio-browser":
            raise MediaBackendError("UNSUPPORTED",
                                    "Scoped operations require Radio Browser")
        return source

    def snapshot(self, client: str = "default") -> dict[str, Any]:
        client = validate_browse_client(client)
        return {
            "generation": self.generation,
            "persistence": {"enabled": self.intent_store is not None,
                            "error": self.persistence_error},
            "sources": [source.describe() for source in self.sources.values()],
            "browse": (self.browse_context if client == "default"
                       else self.browse_contexts.get(client)),
            "selection": self._selection_for(client),
            "loaded": self.loaded,
            "session": self._session(),
            "radioHealth": self._loaded_radio_health(),
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
            return self.snapshot(self._client(args))
        if op == "audio_evidence":
            return self.audio_probe.observe()

        if op == "search":
            client = self._client(args)
            source = self._source(args.get("source", "local-mpd"))
            if client != "default" and source.id != "radio-browser":
                raise MediaBackendError("UNSUPPORTED",
                                        "Scoped searches require Radio Browser")
            query = args.get("query")
            cursor = args.get("cursor")
            if not callable(getattr(source, "search", None)):
                raise MediaBackendError("UNSUPPORTED", "Source does not support catalog search")
            if source.id == "radio-browser":
                result = source.search(query, cursor, client=client)
            elif source.id == "youtube":
                result = source.search(query, cursor)
            else:
                if cursor is not None:
                    raise MediaBackendError("PAGINATION_UNSUPPORTED",
                                            "MPD library search is not paginated")
                result = source.search(query)
            # A search updates browsing only. Selection/loaded/MPD stay untouched.
            browse = {"source": source.id, "query": query,
                      "items": result["items"], "truncated": result["truncated"],
                      "totalObserved": result["totalObserved"],
                      "nextCursor": result.get("nextCursor")}
            if client == "default":
                self.browse_context = browse
            else:
                self.browse_contexts[client] = browse
            self._advance()
            return {"browse": browse}

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
            client = self._client(args)
            ref = self._media_ref(args.get("ref"))
            source = self._source_for_client(ref, client)
            return {"item": (source.inspect(ref, client=client)
                             if source.id == "radio-browser" else source.inspect(ref))}

        if op == "select":
            client = self._client(args)
            ref = self._media_ref(args.get("ref"))
            source = self._source_for_client(ref, client)
            item = (source.inspect(ref, client=client)
                    if source.id == "radio-browser" else source.inspect(ref))
            selected = item["ref"].copy()
            if client == "default":
                self.selection = selected
                self._save_intent()
            else:
                self.scoped_selections[client] = selected
            self._advance()
            return {"selection": selected}

        if op == "load":
            client = self._client(args)
            ref = (args.get("ref") if args.get("ref") is not None
                   else self._selection_for(client))
            ref = self._media_ref(ref)
            source = self._source_for_client(ref, client)
            autoplay = args.get("autoplay", False)
            if not isinstance(autoplay, bool):
                raise MediaBackendError("INVALID_ARGUMENT", "autoplay must be boolean")
            prepared = (source.prepare(ref, client=client)
                        if source.id == "radio-browser" else source.prepare(ref))
            backend = self._backend_for(prepared)
            # Cue is only an addid: it does not call playid or interrupt MPD.
            queue_id = backend.cue(prepared)
            self.loaded = {"ref": prepared["item"]["ref"], "item": prepared["item"],
                           "backend": backend.id, "queueId": queue_id}
            if ref["source"] == "radio-browser":
                self.loaded["cueUri"] = prepared["uri"]
            self.active_backend = backend.id
            # A queued cassette must not revoke ownership of the station
            # still playing. PLAY performs the actual ownership transfer.
            self._advance()
            self._save_intent()
            if autoplay:
                backend.play_id(queue_id)
                current = backend.observe().get("current")
                if not current or str(current.get("queueId")) != queue_id:
                    raise MediaBackendError("PLAY_NOT_CONFIRMED",
                                            "MPD did not confirm the queued station")
                self.owned_active_id = queue_id
                self.owned_active = self.loaded.copy()
                self._advance()
            return {"loaded": self.loaded, "autoplay": autoplay,
                    "commandIssued": True, "session": self._session()}

        if op == "queue":
            backend = self.backends["mpd"]
            return {"items": backend.queue()}

        if op == "queue_add":
            client = self._client(args)
            ref = self._media_ref(args.get("ref"))
            source = self._source_for_client(ref, client)
            prepared = (source.prepare(ref, client=client)
                        if source.id == "radio-browser" else source.prepare(ref))
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
                if self.owned_active_id is None:
                    self.active_backend = None
                self._save_intent()
            self._advance()
            return {"removed": queue_id, "commandIssued": True}

        if op == "play":
            if not self.loaded:
                raise MediaBackendError("NO_LOADED_MEDIA", "Select and load music first")
            backend = self._verify_loaded_queue()
            target = self.loaded.copy()
            backend.play_id(target["queueId"])
            current = backend.observe().get("current")
            if not current or str(current.get("queueId")) != target["queueId"]:
                # Never claim transfer unless MPD reports the requested ID.
                raise MediaBackendError("PLAY_NOT_CONFIRMED",
                                        "MPD did not confirm the loaded station")
            self.owned_active_id = target["queueId"]
            self.owned_active = target
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
                # NEXT/PREVIOUS move beyond the explicitly owned station.
                # Never adopt a different queue entry without a fresh PLAY.
                self.owned_active_id = None
                self.owned_active = None
            if op == "stop":
                # Preserve loaded cassette while relinquishing live playback.
                self.owned_active_id = None
                self.owned_active = None
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
