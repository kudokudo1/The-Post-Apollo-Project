#!/usr/bin/env python3
"""MACHINE M1g: explicit save/list/load of local metadata-only checkpoints.

Separate from PX Hospital; no session restoration, screenshots, or background
capture. Save input is one bounded JSON line on stdin, never command argv.
List/load do not create storage when the database does not exist.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import uuid

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 262144
MAX_DOC_BYTES = 262144
MAX_LABEL = 48
MAX_LIST = 30
MAX_OUTPUTS = 16
MAX_WORKSPACES = 128
MAX_WINDOWS = 512


class StoreError(ValueError):
    pass


def db_path():
    base = os.environ.get("XDG_DATA_HOME", "").strip()
    if base:
        home = Path(base).expanduser()
    else:
        home = Path.home() / ".local" / "share"
    return home / "post-apollo" / "machine" / "machine.db"


def _check_dir(directory, *, create):
    if create:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not directory.is_dir() or directory.is_symlink():
        raise StoreError("INVALID STORE DIRECTORY")
    info = directory.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise StoreError("UNSAFE STORE DIRECTORY PERMISSIONS")


def _check_db(path):
    if path.is_symlink():
        raise StoreError("UNSAFE DATABASE LINK")
    if not path.exists():
        return False
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise StoreError("UNSAFE DATABASE PERMISSIONS")
    return True


def connect(*, writable):
    path = db_path()
    if not writable and not path.exists() and not path.is_symlink():
        return None
    _check_dir(path.parent, create=writable)
    exists = _check_db(path)
    if writable and not exists:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError:
            _check_db(path)
        else:
            os.close(fd)
    if writable:
        conn = sqlite3.connect(str(path), timeout=5.0)
    else:
        from urllib.parse import quote
        conn = sqlite3.connect("file:" + quote(str(path), safe="/") + "?mode=ro",
                               uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, SCHEMA_VERSION) or (not writable and version != SCHEMA_VERSION):
        conn.close()
        raise StoreError("UNSUPPORTED STORAGE SCHEMA")
    if writable:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        with conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                label TEXT NOT NULL,
                saved_at_utc TEXT NOT NULL,
                captured_at_utc TEXT NOT NULL,
                document_json TEXT NOT NULL
            )""")
            conn.execute("PRAGMA user_version=1")
    return conn


def _name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise StoreError("INVALID METADATA")
    if any(ord(x) < 32 or ord(x) == 127 for x in value):
        raise StoreError("INVALID METADATA")
    return value


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise StoreError("INVALID METADATA")


def _number(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise StoreError("INVALID GEOMETRY")
    return value


def _utc(value):
    if not isinstance(value, str) or len(value) > 48:
        raise StoreError("INVALID CAPTURE TIME")
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise StoreError("INVALID CAPTURE TIME") from exc
    if parsed.utcoffset() != dt.timedelta(0):
        raise StoreError("CAPTURE TIME MUST BE UTC")
    return parsed.isoformat()


def _array(doc, key, limit):
    items = doc[key]
    if not isinstance(items, list) or len(items) > limit:
        raise StoreError("INVALID METADATA")
    return items


def validate(document):
    """Strictly reject unexpected/private fields and inconsistent relationships."""
    _keys(document, ("schema_version", "kind", "preview_only",
                     "captured_at_utc", "label",
                     "outputs", "workspaces", "windows"))
    if (type(document["schema_version"]) is not int
            or document["schema_version"] != SCHEMA_VERSION
            or document["kind"] != "sway-layout-selection-preview"
            or document["preview_only"] is not True):
        raise StoreError("UNSUPPORTED CHECKPOINT INPUT")
    captured = _utc(document["captured_at_utc"])
    label = document["label"]
    if not isinstance(label, str) or len(label) > MAX_LABEL:
        raise StoreError("INVALID CHECKPOINT LABEL")
    if any(ord(x) < 32 or ord(x) == 127 for x in label):
        raise StoreError("INVALID CHECKPOINT LABEL")
    outputs = _array(document, "outputs", MAX_OUTPUTS)
    workspaces = _array(document, "workspaces", MAX_WORKSPACES)
    windows = _array(document, "windows", MAX_WINDOWS)
    if not outputs:
        raise StoreError("NO SELECTED MONITORS")
    cleaned_outputs = []
    connectors = set()
    for entry in outputs:
        _keys(entry, ("connector", "rect"))
        connector = _name(entry["connector"])
        if connector in connectors:
            raise StoreError("DUPLICATE MONITOR")
        connectors.add(connector)
        rect = entry["rect"]
        _keys(rect, ("x", "y", "width", "height"))
        cleaned_outputs.append({"connector": connector, "rect": {
            "x": _number(rect["x"], -100000, 100000),
            "y": _number(rect["y"], -100000, 100000),
            "width": _number(rect["width"], 1, 100000),
            "height": _number(rect["height"], 1, 100000)}})
    cleaned_workspaces = []
    workspace_names = set()
    for entry in workspaces:
        _keys(entry, ("name", "output"))
        name = _name(entry["name"])
        output = _name(entry["output"])
        if name in workspace_names or output not in connectors:
            raise StoreError("INCONSISTENT WORKSPACE")
        workspace_names.add(name)
        cleaned_workspaces.append({"name": name, "output": output})
    cleaned_windows = []
    for entry in windows:
        _keys(entry, ("app_id", "workspace", "floating"))
        app = _name(entry["app_id"])
        ws = _name(entry["workspace"])
        if ws not in workspace_names or type(entry["floating"]) is not bool:
            raise StoreError("INCONSISTENT WINDOW")
        cleaned_windows.append({"app_id": app, "workspace": ws,
                                "floating": entry["floating"]})
    return {"schema_version": SCHEMA_VERSION,
            "kind": "sway-layout-selection-preview", "preview_only": True,
            "captured_at_utc": captured,
            "label": label.strip() or "CHECKPOINT",
            "outputs": cleaned_outputs, "workspaces": cleaned_workspaces,
            "windows": cleaned_windows}


def _summary(row):
    doc = json.loads(row["document_json"])
    doc = validate(doc)
    return {"id": row["id"], "label": row["label"],
            "saved_at_utc": row["saved_at_utc"],
            "captured_at_utc": row["captured_at_utc"],
            "counts": {"outputs": len(doc["outputs"]),
                       "workspaces": len(doc["workspaces"]),
                       "windows": len(doc["windows"])}}


def save(payload):
    # Validation deliberately happens before opening or creating any database.
    document = validate(payload)
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > MAX_DOC_BYTES:
        raise StoreError("CHECKPOINT TOO LARGE")
    saved = dt.datetime.now(dt.timezone.utc).isoformat()
    checkpoint_id = str(uuid.uuid4())
    conn = connect(writable=True)
    try:
        with conn:
            conn.execute(
                "INSERT INTO checkpoints (id, schema_version, label, saved_at_utc, "
                "captured_at_utc, document_json) VALUES (?, ?, ?, ?, ?, ?)",
                (checkpoint_id, SCHEMA_VERSION, document["label"], saved,
                 document["captured_at_utc"], raw))
        row = conn.execute("SELECT * FROM checkpoints WHERE id=?",
                           (checkpoint_id,)).fetchone()
        if row is None:
            raise StoreError("SAVE NOT CONFIRMED")
        return {"status": "saved", "checkpoint": _summary(row)}
    finally:
        conn.close()


def listing():
    conn = connect(writable=False)
    if conn is None:
        return {"status": "listed", "checkpoints": []}
    try:
        rows = conn.execute(
            "SELECT * FROM checkpoints ORDER BY saved_at_utc DESC, id DESC LIMIT ?",
            (MAX_LIST,)).fetchall()
        return {"status": "listed", "checkpoints": [_summary(row) for row in rows]}
    finally:
        conn.close()


def load(checkpoint_id):
    try:
        checkpoint_id = str(uuid.UUID(checkpoint_id))
    except (ValueError, AttributeError) as exc:
        raise StoreError("INVALID CHECKPOINT ID") from exc
    conn = connect(writable=False)
    if conn is None:
        raise StoreError("CHECKPOINT NOT FOUND")
    try:
        row = conn.execute("SELECT * FROM checkpoints WHERE id=?", (checkpoint_id,)).fetchone()
        if row is None:
            raise StoreError("CHECKPOINT NOT FOUND")
        document = validate(json.loads(row["document_json"]))
        return {"status": "loaded", "checkpoint": _summary(row),
                "document": document, "read_only": True}
    finally:
        conn.close()


def _decode_input():
    payload = sys.stdin.buffer.readline(MAX_INPUT_BYTES + 1)
    if not payload or len(payload) > MAX_INPUT_BYTES or not payload.endswith(b"\n"):
        raise StoreError("INVALID OR OVERSIZED SAVE REQUEST")
    try:
        value = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise StoreError("INVALID SAVE REQUEST") from exc
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description="Post-Apollo MACHINE local checkpoints")
    choices = parser.add_subparsers(dest="command", required=True)
    choices.add_parser("save")
    choices.add_parser("list")
    load_parser = choices.add_parser("load")
    load_parser.add_argument("id")
    args = parser.parse_args(argv)
    try:
        if args.command == "save":
            result = save(_decode_input())
        elif args.command == "list":
            result = listing()
        else:
            result = load(args.id)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (StoreError, sqlite3.Error, OSError, ValueError) as exc:
        # Never echo serialized payloads, file contents, or native SQL errors.
        reason = str(exc) if isinstance(exc, StoreError) else "STORAGE UNAVAILABLE"
        print(json.dumps({"status": "error", "reason": reason}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
