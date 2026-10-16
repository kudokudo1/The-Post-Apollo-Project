"""Durable user-private Hi-Fi selection/loaded intent, not playback ownership.

Persist only source-qualified references and MPD queue coordinates. Loading an
intent never mutates MPD and never adopts a playing track automatically.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any


def default_state_path() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return root / "post-apollo-media" / "controller-intent-v1.json"


def _valid_ref(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    source, kind, identifier = value.get("source"), value.get("kind"), value.get("id")
    if (source, kind) not in (("local-mpd", "track"), ("youtube", "video")):
        return False
    return isinstance(identifier, str) and 0 < len(identifier) <= 4096 and not any(
        ch in identifier for ch in "\x00\r\n"
    )


class IntentStore:
    version = 1

    def __init__(self, path: Path | None = None):
        self.path = path or default_state_path()

    def _secure_directory(self, create: bool) -> None:
        parent = self.path.parent
        if parent.is_symlink():
            raise PermissionError("State directory cannot be a symlink")
        if create:
            parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = parent.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PermissionError("State directory must be user-owned and private (0700)")

    def load(self) -> dict[str, Any]:
        if not self.path.parent.exists():
            return {}
        self._secure_directory(create=False)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.path, flags)
        except FileNotFoundError:
            return {}
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise PermissionError("State file must be user-owned and private")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                raw = handle.read(16385)
            if len(raw) > 16384:
                raise ValueError("State file exceeds safety limit")
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("version") != self.version:
                return {}
            selection = data.get("selection")
            loaded = data.get("loaded")
            result: dict[str, Any] = {}
            if _valid_ref(selection):
                result["selection"] = selection
            if (isinstance(loaded, dict)
                and _valid_ref(loaded.get("ref"))
                and loaded["ref"]["source"] == "local-mpd"
                and isinstance(loaded.get("queueId"), str)
                and loaded["queueId"].isascii() and loaded["queueId"].isdecimal()):
                result["loaded"] = {"ref": loaded["ref"], "queueId": loaded["queueId"]}
            return result
        finally:
            os.close(fd)

    def save(self, selection: Any, loaded: Any) -> None:
        self._secure_directory(create=True)
        if selection is not None and not _valid_ref(selection):
            raise ValueError("Invalid selection intent")
        minimal = None
        if loaded is not None:
            ref = loaded.get("ref") if isinstance(loaded, dict) else None
            ident = loaded.get("queueId") if isinstance(loaded, dict) else None
            if (not _valid_ref(ref) or ref["source"] != "local-mpd"
                or not isinstance(ident, str) or not ident.isascii() or not ident.isdecimal()):
                raise ValueError("Invalid loaded MPD intent")
            minimal = {"ref": ref, "queueId": ident}
        data = json.dumps({"version": self.version, "selection": selection,
                           "loaded": minimal}, ensure_ascii=False).encode("utf-8")
        if len(data) > 16384:
            raise ValueError("State too large")
        fd, name = tempfile.mkstemp(prefix=".intent-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb", closefd=False) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(fd)
            # Atomic in-place replace within private directory.
            os.replace(name, self.path)
        finally:
            os.close(fd)
            if os.path.exists(name):
                os.unlink(name)
