#!/usr/bin/env python3
"""Banking M2: operator-picked local CSV read, bounded and strictly read-only.

Input: one JSON line {version:1,token:"file-N",fileUrl:"file:///...csv"}
Output: one prefixed JSON line. No source names/paths, CSV, or exception text
are logged; CSV is returned solely on stdout to the requesting UI process.
This is NOT an account connector, writer, or durable financial data store.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from urllib.parse import unquote_to_bytes, urlsplit

PREFIX = "FINANCEW_BANKING_FILE_RESULT "
MAX_INPUT_BYTES = 4096
MAX_FILE_BYTES = 65536
TOKEN_PATTERN = re.compile(r"file-[1-9][0-9]{0,7}\Z")
BAD_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class Reject(Exception):
    def __init__(self, code: str):
        self.code = code


def selected_path(file_url: str) -> str:
    if not isinstance(file_url, str) or len(file_url) > 3000:
        raise Reject("INVALID_FILE_SELECTION")
    if CONTROL.search(file_url) or BAD_ESCAPE.search(file_url):
        raise Reject("INVALID_FILE_SELECTION")
    try:
        parts = urlsplit(file_url)
        if (parts.scheme != "file"
                or parts.netloc not in ("", "localhost")
                or parts.query or parts.fragment
                or not parts.path.startswith("/")):
            raise Reject("LOCAL_FILE_REQUIRED")
        decoded = unquote_to_bytes(parts.path).decode("utf-8", errors="strict")
    except (UnicodeError, ValueError) as exc:
        raise Reject("INVALID_FILE_SELECTION") from exc
    if (not decoded.startswith("/") or "//" in decoded or
            CONTROL.search(decoded) or "\x00" in decoded or
            any(part in ("", ".", "..") for part in decoded.split("/")[1:]) or
            not decoded.lower().endswith(".csv")):
        raise Reject("LOCAL_CSV_REQUIRED")
    return decoded


def safe_read(file_url: str) -> str:
    path = selected_path(file_url)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise Reject("CANNOT_OPEN_LOCAL_FILE") from exc
    try:
        first = os.fstat(descriptor)
        if (not stat.S_ISREG(first.st_mode) or first.st_uid != os.getuid()
                or first.st_size <= 0 or first.st_size > MAX_FILE_BYTES):
            raise Reject("FILE_NOT_OWNED_REGULAR_OR_EXCEEDS_64K")
        chunks = []
        received = 0
        while True:
            fragment = os.read(descriptor, min(16384, MAX_FILE_BYTES + 1 - received))
            if not fragment:
                break
            chunks.append(fragment)
            received += len(fragment)
            if received > MAX_FILE_BYTES:
                raise Reject("FILE_EXCEEDS_64K")
        last = os.fstat(descriptor)
        if (first.st_ino != last.st_ino or first.st_dev != last.st_dev
                or first.st_size != last.st_size
                or first.st_mtime_ns != last.st_mtime_ns
                or received != last.st_size):
            raise Reject("FILE_CHANGED_WHILE_READING")
        try:
            return b"".join(chunks).decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise Reject("UTF8_CSV_REQUIRED") from exc
    except OSError as exc:
        raise Reject("CANNOT_READ_LOCAL_FILE") from exc
    finally:
        os.close(descriptor)


def answer(payload: dict) -> None:
    sys.stdout.write(PREFIX + json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    token = ""
    try:
        raw = sys.stdin.buffer.readline(MAX_INPUT_BYTES + 1)
        if (not raw.endswith(b"\n") or len(raw) > MAX_INPUT_BYTES
                or b"\x00" in raw):
            raise Reject("INVALID_REQUEST")
        request = json.loads(raw.decode("utf-8", errors="strict"))
        if not isinstance(request, dict) or set(request) != {"version", "token", "fileUrl"}:
            raise Reject("INVALID_REQUEST")
        token = request["token"]
        if (type(request["version"]) is not int or request["version"] != 1
                or not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token)):
            raise Reject("INVALID_REQUEST")
        content = safe_read(request["fileUrl"])
        answer({"version": 1, "token": token, "ok": True, "csv": content})
        return 0
    except (Reject, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        code = exc.code if isinstance(exc, Reject) else "INVALID_REQUEST"
    except OSError:
        code = "LOCAL_FILE_READ_FAILED"
    answer({"version": 1, "token": token if isinstance(token, str) and TOKEN_PATTERN.fullmatch(token) else "",
            "ok": False, "error": code})
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
