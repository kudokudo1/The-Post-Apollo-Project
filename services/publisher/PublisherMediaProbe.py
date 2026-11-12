#!/usr/bin/env python3
"""P1.2: inspect one explicit local media URL. No writes, uploads or scanning.

Only user-owned, ordinary files inside the current home directory qualify.
A receipt binds the source URL to inode/device/size/mtime, *not* to content:
verification before preview detects changes but cannot prevent a later race.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

IMAGE_LIMIT = 32 * 1024 * 1024
VIDEO_LIMIT = 1024 * 1024 * 1024
EXTENSIONS = {
    ".png": ("image", "image/png", IMAGE_LIMIT),
    ".jpg": ("image", "image/jpeg", IMAGE_LIMIT),
    ".jpeg": ("image", "image/jpeg", IMAGE_LIMIT),
    ".webp": ("image", "image/webp", IMAGE_LIMIT),
    ".mp4": ("video", "video/mp4", VIDEO_LIMIT),
    ".webm": ("video", "video/webm", VIDEO_LIMIT),
    ".mov": ("video", "video/quicktime", VIDEO_LIMIT),
}
STAMP = re.compile(r"^[0-9a-f]{64}$")


def refusal(reason: str) -> dict:
    return {"ok": False, "reason": reason}


def decode_uri(raw: str) -> Path:
    if not isinstance(raw, str) or len(raw) > 4096:
        raise ValueError("INVALID_URI")
    try:
        uri = urlsplit(raw)
        if uri.scheme != "file" or uri.netloc or uri.query or uri.fragment:
            raise ValueError("LOCAL_FILE_URI_REQUIRED")
        if not uri.path.startswith("/"):
            raise ValueError("ABSOLUTE_FILE_REQUIRED")
        decoded = unquote(uri.path, errors="strict")
        if any(c in decoded for c in ("\x00", "\n", "\r")):
            raise ValueError("UNSAFE_PATH")
        path = Path(decoded)
        if any(part in ("..", ".") for part in decoded.split("/")):
            raise ValueError("PATH_TRAVERSAL")
        root = Path.home().resolve(strict=True)
        real = path.resolve(strict=True)
        if not real.is_relative_to(root) or real == root:
            raise ValueError("OUTSIDE_HOME")
        # A file chooser is not permission to reach dotfile credentials.
        relative = real.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            raise ValueError("HIDDEN_SOURCE")
        if path.is_symlink():
            raise ValueError("SYMLINK_FILE")
        return path
    except (OSError, UnicodeError):
        raise ValueError("FILE_UNAVAILABLE") from None


def sniff(extension: str, signature: bytes) -> bool:
    if extension == ".png":
        return signature.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in (".jpg", ".jpeg"):
        return signature.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return signature[:4] == b"RIFF" and signature[8:12] == b"WEBP"
    if extension in (".mp4", ".mov"):
        return len(signature) >= 12 and signature[4:8] == b"ftyp"
    if extension == ".webm":
        return signature.startswith(b"\x1a\x45\xdf\xa3")
    return False


def inspect(raw: str, expected: str | None = None) -> dict:
    try:
        path = decode_uri(raw)
        # No symlink final component; O_NONBLOCK prevents special-file hangs.
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                return refusal("NOT_OWNED_REGULAR_FILE")
            if info.st_nlink != 1:
                return refusal("HARDLINK_SOURCE")
            ext = path.suffix.lower()
            if ext not in EXTENSIONS:
                return refusal("UNSUPPORTED_MEDIA")
            kind, mime, limit = EXTENSIONS[ext]
            if info.st_size < 1 or info.st_size > limit:
                return refusal("MEDIA_SIZE_LIMIT")
            if not sniff(ext, os.read(fd, 32)):
                return refusal("MEDIA_SIGNATURE_MISMATCH")
            canonical = path.resolve(strict=True)
            root = Path.home().resolve(strict=True)
            if not canonical.is_relative_to(root):
                return refusal("OUTSIDE_HOME")
            title = canonical.name
            if len(title) > 160 or any(ord(ch) < 32 or ord(ch) == 127 for ch in title):
                return refusal("INVALID_DISPLAY_NAME")
            identity = "|".join([
                str(info.st_dev), str(info.st_ino), str(info.st_size),
                str(info.st_mtime_ns),
            ])
            stamp = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            if expected is not None:
                if not STAMP.fullmatch(expected):
                    return refusal("INVALID_STAMP")
                if stamp != expected:
                    return refusal("SOURCE_CHANGED")
            return {
                "ok": True,
                "sourceUrl": canonical.as_uri(),
                "title": title,
                "kind": kind,
                "mime": mime,
                "sizeBytes": info.st_size,
                "stamp": stamp,
            }
        finally:
            os.close(fd)
    except ValueError as exc:
        return refusal(str(exc))
    except OSError:
        return refusal("FILE_UNAVAILABLE")


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "inspect":
        result = inspect(argv[1])
    elif len(argv) == 3 and argv[0] == "verify":
        result = inspect(argv[1], argv[2])
    else:
        result = refusal("INVALID_REQUEST")
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
