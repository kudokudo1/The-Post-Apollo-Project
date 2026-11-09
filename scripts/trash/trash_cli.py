#!/usr/bin/env python3
"""Post-Apollo Trash adapter: GIO-owned index, restore and explicit burn.

GIO owns the Freedesktop Trash across mounts. Never derive deletion paths from
original filenames or scan ~/.local/share/Trash directly. This is invoked only
from explicit Trash widget buttons; no timers or automatic deletion.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote

PAGE_SIZE = 80
MAX_ITEMS = 2500
MAX_LIST_BYTES = 1048576
MAX_ARG = 8192
ACTION_TIMEOUT = 75


class TrashError(Exception):
    pass


def _error_text(message):
    return "".join(char if char.isprintable() else " " for char in str(message))[:180]


def _gio():
    executable = shutil.which("gio")
    if not executable:
        raise TrashError("GIO_NOT_INSTALLED")
    return executable


def _run(args, timeout=20):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise TrashError("GIO_TIMEOUT")
    except OSError:
        raise TrashError("GIO_EXECUTION_FAILED")


def _revision(rows):
    raw = json.dumps([[row["uri"], row["original"]] for row in rows],
                     ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _display(raw):
    return _error_text(raw)[:170]


def parse_listing(output):
    """Reject malformed/partial listings rather than authorize unknown items.

    gio trash --list emits a trash:/// URI followed by TAB and original path.
    Directory traversal is never used, so external mount trash is included.
    """
    if not isinstance(output, str) or len(output.encode("utf-8")) > MAX_LIST_BYTES:
        raise TrashError("TRASH_INDEX_TOO_LARGE")
    lines = output.splitlines()
    if len(lines) > MAX_ITEMS:
        raise TrashError("TRASH_INDEX_TOO_MANY_ITEMS")
    rows = []
    seen = set()
    for line in lines:
        if "\t" not in line:
            raise TrashError("TRASH_LIST_FORMAT_UNSUPPORTED")
        uri, original = line.split("\t", 1)
        if (not uri.startswith("trash:///") or len(uri) > MAX_ARG
                or not original.startswith("/") or len(original) > MAX_ARG
                or "\x00" in uri or "\x00" in original or uri in seen):
            raise TrashError("TRASH_LIST_FORMAT_UNSUPPORTED")
        if "\r" in uri or "\r" in original:
            raise TrashError("TRASH_LIST_FORMAT_UNSUPPORTED")
        seen.add(uri)
        # Prefer actual original filename; escaped trash names may be renamed.
        name = Path(original).name or unquote(uri.rsplit("/", 1)[-1])
        rows.append({"uri": uri, "original": original,
                     "name": _display(name),
                     "originLabel": _display(original)})
    rows.sort(key=lambda item: (item["original"].casefold(), item["uri"]))
    return rows


def inventory():
    gio = _gio()
    process = _run([gio, "trash", "--list"])
    if process.returncode != 0:
        raise TrashError("GIO_LIST_FAILED: " + _error_text(process.stderr))
    return gio, parse_listing(process.stdout)


def index(page=0):
    if not isinstance(page, int) or page < 0 or page > 9999:
        raise TrashError("INVALID_PAGE")
    _, rows = inventory()
    start = page * PAGE_SIZE
    return {"ok": True, "kind": "index", "items": rows[start:start + PAGE_SIZE],
            "total": len(rows), "page": page, "pageSize": PAGE_SIZE,
            "hasMore": start + PAGE_SIZE < len(rows),
            "revision": _revision(rows), "complete": True}


def _selected(rows, uri, original):
    if (not isinstance(uri, str) or not uri.startswith("trash:///")
            or len(uri) > MAX_ARG or not isinstance(original, str)
            or len(original) > MAX_ARG):
        raise TrashError("INVALID_SELECTION")
    for row in rows:
        if row["uri"] == uri and row["original"] == original:
            return row
    raise TrashError("STALE_OR_UNKNOWN_TRASH_ITEM")


def item_action(action, uri, original, confirmation=""):
    if action not in ("restore", "burn"):
        raise TrashError("UNKNOWN_ACTION")
    if action == "burn" and confirmation != "BURN_CONFIRMED":
        raise TrashError("BURN_CONFIRMATION_REQUIRED")
    gio, rows = inventory()
    row = _selected(rows, uri, original)
    if action == "restore" and os.path.lexists(row["original"]):
        raise TrashError("RESTORE_TARGET_EXISTS")
    # A URI is used only after positive inventory matching. No raw filesystem
    # deletion, shell=True, flag interpolation or path-based traversal.
    command = [gio, "trash", "--restore", row["uri"]] if action == "restore" \
              else [gio, "remove", row["uri"]]
    result = _run(command, timeout=ACTION_TIMEOUT)
    if result.returncode != 0:
        raise TrashError(("GIO_RESTORE_FAILED: " if action == "restore"
                          else "GIO_BURN_FAILED: ") + _error_text(result.stderr))
    return {"ok": True, "kind": action, "name": row["name"],
            "message": "RESTORED" if action == "restore" else "BURNED"}


def burn_all(revision, count, confirmation):
    if confirmation != "BURN_ALL_CONFIRMED":
        raise TrashError("BURN_ALL_CONFIRMATION_REQUIRED")
    gio, rows = inventory()
    if (not isinstance(revision, str) or len(revision) != 64
            or not isinstance(count, str) or not count.isdecimal()
            or int(count) != len(rows) or int(count) == 0
            or revision != _revision(rows)):
        raise TrashError("TRASH_CHANGED_REFRESH_REQUIRED")
    # System Trash can include multiple mounts. This only executes after a
    # separate deliberate CONFIRM BURN ALL click on a complete GIO inventory.
    result = _run([gio, "trash", "--empty"], timeout=ACTION_TIMEOUT)
    if result.returncode != 0:
        raise TrashError("GIO_EMPTY_FAILED: " + _error_text(result.stderr))
    return {"ok": True, "kind": "burn-all", "count": len(rows),
            "message": "BURN_ALL_COMPLETED"}


def main(argv):
    try:
        if len(argv) == 2 and argv[1] == "index":
            result = index()
        elif len(argv) == 3 and argv[1] == "index":
            try:
                page = int(argv[2])
            except ValueError:
                raise TrashError("INVALID_PAGE")
            result = index(page)
        elif len(argv) == 4 and argv[1] == "restore":
            result = item_action("restore", argv[2], argv[3])
        elif len(argv) == 5 and argv[1] == "burn":
            result = item_action("burn", argv[2], argv[3], argv[4])
        elif len(argv) == 5 and argv[1] == "burn-all":
            result = burn_all(argv[2], argv[3], argv[4])
        else:
            raise TrashError("INVALID_ACTION")
    except TrashError as exc:
        result = {"ok": False, "error": _error_text(exc)}
    except Exception:
        result = {"ok": False, "error": "UNEXPECTED_BACKEND_FAILURE"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
