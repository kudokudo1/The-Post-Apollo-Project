#!/usr/bin/env python3
"""MACHINE checkpoint display names and notes, separate from saved geometry.

DORMANT: No CLI, QML binding, background work or import-time file access.
An explicit authorized caller can attach a bounded personal annotation to an
existing checkpoint UUID in the same private SQLite database. The original
checkpoint row, legacy JSON, geometry v2 row, timestamps and version=1
remain untouched. All updates are optimistic, transactional and reversible
by a later update, not by modifying captured state.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid

import MachineCheckpointStore as legacy

TABLE = "machine_checkpoint_annotations"
MAX_DISPLAY_NAME = 48
MAX_NOTE_CHARS = 1024
MAX_NOTE_BYTES = 4096
MAX_REVISION = 2**31 - 1


class AnnotationError(ValueError):
    pass


def _canonical_id(checkpoint_id):
    if not isinstance(checkpoint_id, str):
        raise AnnotationError("INVALID CHECKPOINT ID")
    try:
        normalized = str(uuid.UUID(checkpoint_id))
    except (ValueError, AttributeError) as exc:
        raise AnnotationError("INVALID CHECKPOINT ID") from exc
    if normalized != checkpoint_id:
        raise AnnotationError("INVALID CHECKPOINT ID")
    return normalized


def _display_name(value):
    if not isinstance(value, str):
        raise AnnotationError("INVALID CHECKPOINT NAME")
    result = value.strip()
    if (not 1 <= len(result) <= MAX_DISPLAY_NAME
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in result)):
        raise AnnotationError("INVALID CHECKPOINT NAME")
    return result


def _note(value):
    if (not isinstance(value, str) or len(value) > MAX_NOTE_CHARS
            or any((ord(ch) < 32 and ch != "\n") or ord(ch) == 127
                   for ch in value)):
        raise AnnotationError("INVALID CHECKPOINT NOTE")
    try:
        raw = value.encode("utf-8")
    except UnicodeError as exc:
        raise AnnotationError("INVALID CHECKPOINT NOTE") from exc
    if len(raw) > MAX_NOTE_BYTES:
        raise AnnotationError("INVALID CHECKPOINT NOTE")
    return value


def _revision(value):
    if type(value) is not int or not 0 <= value < MAX_REVISION:
        raise AnnotationError("INVALID ANNOTATION REVISION")
    return value


def _existing(conn, checkpoint_id):
    row = conn.execute(
        "SELECT id, label FROM checkpoints WHERE id=?",
        (checkpoint_id,)).fetchone()
    if row is None:
        raise AnnotationError("CHECKPOINT NOT FOUND")
    return row


def _annotation_table_exists(conn):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone() is not None


def _table(conn):
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
        checkpoint_id TEXT PRIMARY KEY
            REFERENCES checkpoints(id) ON DELETE CASCADE,
        display_name TEXT NOT NULL,
        note TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK (revision >= 1),
        updated_at_utc TEXT NOT NULL
    )""")


def _result(checkpoint_id, original_label, row):
    if row is None:
        return {
            "status": "loaded", "checkpoint_id": checkpoint_id,
            "original_label": original_label, "display_name": original_label,
            "note": "", "revision": 0, "updated_at_utc": None,
            "read_only": True, "capture_modified": False,
        }
    if (type(row["revision"]) is not int
            or not 1 <= row["revision"] <= MAX_REVISION):
        raise AnnotationError("INVALID STORED ANNOTATION")
    return {
        "status": "loaded", "checkpoint_id": checkpoint_id,
        "original_label": original_label,
        "display_name": _display_name(row["display_name"]),
        "note": _note(row["note"]),
        "revision": row["revision"],
        "updated_at_utc": row["updated_at_utc"],
        "read_only": True, "capture_modified": False,
    }


def get_annotation(checkpoint_id):
    """Existing checkpoint only, no DB creation, migration or Sway read."""
    checkpoint_id = _canonical_id(checkpoint_id)
    conn = legacy.connect(writable=False)
    if conn is None:
        raise AnnotationError("CHECKPOINT NOT FOUND")
    try:
        existing = _existing(conn, checkpoint_id)
        row = None
        if _annotation_table_exists(conn):
            row = conn.execute(
                f"SELECT * FROM {TABLE} WHERE checkpoint_id=?",
                (checkpoint_id,)).fetchone()
        return _result(checkpoint_id, existing["label"], row)
    finally:
        conn.close()



def list_annotation_names():
    """Read only names for the exact visible legacy checkpoint list.

    Never return private notes during ordinary list browsing. Do not
    create the optional table or mutate SQLite when it does not exist.
    """
    conn = legacy.connect(writable=False)
    if conn is None:
        return {"status": "listed", "read_only": True, "items": []}
    try:
        if not _annotation_table_exists(conn):
            return {"status": "listed", "read_only": True, "items": []}
        rows = conn.execute(
            f"SELECT a.checkpoint_id, a.display_name, a.revision "
            f"FROM {TABLE} AS a INNER JOIN checkpoints AS c "
            "ON c.id=a.checkpoint_id "
            "WHERE a.checkpoint_id IN "
            "(SELECT id FROM checkpoints ORDER BY saved_at_utc DESC, id DESC "
            "LIMIT ?) ORDER BY c.saved_at_utc DESC, c.id DESC",
            (legacy.MAX_LIST,)).fetchall()
        items = []
        for row in rows:
            revision = row["revision"]
            if type(revision) is not int or not 1 <= revision <= MAX_REVISION:
                raise AnnotationError("INVALID STORED ANNOTATION")
            items.append({
                "checkpoint_id": _canonical_id(row["checkpoint_id"]),
                "display_name": _display_name(row["display_name"]),
                "revision": revision,
            })
        return {"status": "listed", "read_only": True, "items": items}
    finally:
        conn.close()


def set_annotation(checkpoint_id, *, display_name, note, expected_revision,
                   stage_hook=None):
    """Update only the metadata sidecar with stale-editor protection.

    Caller must supply both complete fields and the revision previously read.
    A failed update rolls back, preserving the old annotation and every
    original capture/geometry row. stage_hook is a synthetic test seam only.
    """
    checkpoint_id = _canonical_id(checkpoint_id)
    display_name = _display_name(display_name)
    note = _note(note)
    expected_revision = _revision(expected_revision)

    # An absent database or UUID must NEVER create a new machine.db.
    preflight = legacy.connect(writable=False)
    if preflight is None:
        raise AnnotationError("CHECKPOINT NOT FOUND")
    try:
        _existing(preflight, checkpoint_id)
    finally:
        preflight.close()

    conn = legacy.connect(writable=True)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            # Take the metadata write lock before validating revision or
            # creating the sidecar. DDL and update then roll back together.
            conn.execute("BEGIN IMMEDIATE")
            existing = _existing(conn, checkpoint_id)
            _table(conn)
            previous = conn.execute(
                f"SELECT revision FROM {TABLE} WHERE checkpoint_id=?",
                (checkpoint_id,)).fetchone()
            current_revision = previous["revision"] if previous else 0
            if current_revision != expected_revision:
                raise AnnotationError("STALE CHECKPOINT ANNOTATION")
            if stage_hook is not None:
                stage_hook("before_write")
            next_revision = current_revision + 1
            timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
            if previous is None:
                conn.execute(
                    f"INSERT INTO {TABLE} "
                    "(checkpoint_id, display_name, note, revision, updated_at_utc) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (checkpoint_id, display_name, note,
                     next_revision, timestamp))
            else:
                updated = conn.execute(
                    f"UPDATE {TABLE} SET display_name=?, note=?, revision=?, "
                    "updated_at_utc=? WHERE checkpoint_id=? AND revision=?",
                    (display_name, note, next_revision, timestamp,
                     checkpoint_id, expected_revision))
                if updated.rowcount != 1:
                    raise AnnotationError("STALE CHECKPOINT ANNOTATION")
            if stage_hook is not None:
                stage_hook("after_write")
        row = conn.execute(
            f"SELECT * FROM {TABLE} WHERE checkpoint_id=?",
            (checkpoint_id,)).fetchone()
        if row is None:
            raise AnnotationError("ANNOTATION WRITE UNVERIFIED")
        result = _result(checkpoint_id, existing["label"], row)
        return dict(result, status="updated", read_only=False)
    finally:
        conn.close()
