#!/usr/bin/env python3
"""Trash++ source-owned record discovery. Strictly read-only.

The index deliberately has NO archive, trash, restore, burn or file-write
operation. Source stores remain sole writers and retention authorities.
"""
import json
import os
from pathlib import Path
import stat
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

MAX_DATA_DIR_ARG = 4096
MAX_ROWS = 350
MAX_EVENT_DOC_BYTES = 8 * 1024 * 1024
MAX_DOSSIER_DOC_BYTES = 2500000
MAX_CRAWL_DOC_BYTES = 262144
EVENT_SCHEMA = "post-apollo.weather-event-archive.v1"
DOSSIER_SCHEMA = "post-apollo.weather-dossier-archive.v1"
SOURCES = (
    ("weather-events", "WEATHER // EVENT ARCHIVE", "weather-event-archive-v1.json", MAX_EVENT_DOC_BYTES),
    ("weather-dossiers", "WEATHER // DOSSIER ARCHIVE", "weather-dossier-archive-v1.json", MAX_DOSSIER_DOC_BYTES),
    ("demo-scrape", "RESEARCH // DEMO SCRAPES", "crawl-records.json", MAX_CRAWL_DOC_BYTES),
)
SOURCE_IDS = {"gdacs", "usgs", "eonet", "firms"}


class IndexErrorSafe(Exception):
    pass


def _text(value, maximum=160):
    if not isinstance(value, (str, int, float)):
        return ""
    return "".join(c if c.isprintable() else " " for c in str(value))[:maximum].strip()


def _timestamp(value):
    if isinstance(value, bool):
        return 0
    try:
        val = int(value)
        if 100000000000 <= val <= 9999999999999:
            return val
    except (TypeError, ValueError, OverflowError):
        pass
    return 0


def _datetime(ms):
    if ms == 0:
        return "UNKNOWN UTC"
    try:
        return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OverflowError, OSError):
        return "UNKNOWN UTC"


def _read_regular(path, limit):
    """Open fixed-name files without following symlinks; never write or follow arbitrary paths."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise IndexErrorSafe("SOURCE_UNREADABLE") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size < 2 or st.st_size > limit:
            raise IndexErrorSafe("SOURCE_UNSAFE_OR_OVERSIZE")
        raw = os.read(fd, limit + 1)
        if len(raw) > limit:
            raise IndexErrorSafe("SOURCE_UNSAFE_OR_OVERSIZE")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IndexErrorSafe("INVALID_SOURCE_JSON") from exc
    finally:
        os.close(fd)


def _row(source, identity, title, ms, details, kind):
    return {
        "id": _text(identity, 260),
        "source": source,
        "kind": kind,
        "title": _text(title, 150) or "UNTITLED RECORD",
        "recordedAtMs": ms,
        "recordedAt": _datetime(ms),
        "details": _text(details, 210),
        "capabilities": {
            "inspect": True,
            "archive": False,
            "trash": False,
            "restore": False,
            "burn": False,
        },
        "retention": "SOURCE OWNED // READ ONLY",
    }


def _event_rows(doc):
    if (not isinstance(doc, dict) or doc.get("schema") != EVENT_SCHEMA
            or doc.get("version") != 1 or not isinstance(doc.get("events"), dict)
            or len(doc["events"]) > 256):
        raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
    rows = []
    for key, event in doc["events"].items():
        if not isinstance(key, str) or not isinstance(event, dict):
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        source = event.get("sourceId")
        event_id = event.get("eventId")
        snaps = event.get("snapshots")
        if (source not in SOURCE_IDS or not isinstance(event_id, str)
                or not event_id or not isinstance(snaps, list)
                or not 1 <= len(snaps) <= 32
                or key != source + "|" + event_id):
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        for snap in snaps:
            if not isinstance(snap, dict) or _timestamp(snap.get("capturedAtMs")) == 0:
                raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        stamp = max(_timestamp(snap.get("capturedAtMs")) for snap in snaps)
        rows.append(_row("WEATHER // EVENT", "weather-event:" + key,
                         event.get("title") or event_id, stamp,
                         f"{source.upper()} // {event_id} // {len(snaps)} SNAPSHOTS",
                         "EVENT HISTORY"))
    return rows


def _dossier_rows(doc):
    if (not isinstance(doc, dict) or doc.get("schema") != DOSSIER_SCHEMA
            or doc.get("version") != 1 or not isinstance(doc.get("entries"), list)
            or len(doc["entries"]) > 64):
        raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
    rows = []
    last = 0
    for entry in doc["entries"]:
        if not isinstance(entry, dict):
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        source, event_id, seq = (entry.get("sourceId"), entry.get("eventId"),
                                 entry.get("sequence"))
        ms = _timestamp(entry.get("capturedAtMs"))
        if (source not in SOURCE_IDS or not isinstance(event_id, str)
                or not event_id or not isinstance(seq, int) or isinstance(seq, bool)
                or seq <= last or ms == 0 or not isinstance(entry.get("transport"), str)):
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        last = seq
        rows.append(_row("WEATHER // DOSSIER",
                         f"weather-dossier:{source}:{event_id}:{seq}",
                         event_id, ms, f"{source.upper()} // SEQUENCE {seq}",
                         "SAVED DOSSIER"))
    return rows


def _crawl_rows(doc):
    """Metadata only for the established quotes.toscrape.com DEMO source.

    Financial account/transaction data never enters this adapter.
    """
    if not isinstance(doc, list) or len(doc) > 6:
        raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
    rows = []
    seen = set()
    for page in doc:
        if (not isinstance(page, dict) or page.get("schemaVersion") != 1
                or page.get("source") != "finance-demo-scrapy"
                or page.get("readOnly") is not True
                or not isinstance(page.get("title"), str)
                or not isinstance(page.get("observedAt"), str)):
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        uri = page.get("url")
        if not isinstance(uri, str) or len(uri) > 400:
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        try:
            parts = urlsplit(uri)
            accepted = (parts.scheme == "https"
                        and parts.hostname == "quotes.toscrape.com"
                        and parts.port is None
                        and not parts.username and not parts.password)
        except ValueError as exc:
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA") from exc
        if not accepted or uri in seen:
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        seen.add(uri)
        try:
            when = datetime.fromisoformat(page["observedAt"].replace("Z", "+00:00"))
            if when.tzinfo is None:
                raise ValueError("missing timezone")
            ms = int(when.timestamp() * 1000)
        except (ValueError, OverflowError) as exc:
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA") from exc
        if not isinstance(page.get("links"), list) or len(page["links"]) > 32:
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        if not isinstance(page.get("snippets"), list) or len(page["snippets"]) > 3:
            raise IndexErrorSafe("INVALID_SOURCE_SCHEMA")
        rows.append(_row("RESEARCH // DEMO SCRAPE", "demo-scrape:" + uri,
                         page["title"], ms, "QUOTES.TOSCRAPE.COM // DEMO EXPORT",
                         "WEB SCRAPE"))
    return rows


def _source_path(data_dir, home_dir, source):
    if source == "demo-scrape":
        return home_dir / ".local/share/post-apollo/finance-crawler/crawl-records.json"
    filename = SOURCES[0][2] if source == "weather-events" else SOURCES[1][2]
    return data_dir / filename


def index(data_dir, home_dir=None):
    if (not isinstance(data_dir, str) or not data_dir.startswith("/")
            or len(data_dir) > MAX_DATA_DIR_ARG or "\x00" in data_dir):
        raise IndexErrorSafe("INVALID_DATA_DIRECTORY")
    base = Path(data_dir)
    home = Path(home_dir) if home_dir is not None else Path.home()
    entries = []
    sources = []
    for key, label, _, limit in SOURCES:
        path = _source_path(base, home, key)
        try:
            doc = _read_regular(path, limit)
            if doc is None:
                sources.append({"id": key, "label": label, "state": "EMPTY", "count": 0})
                continue
            items = (_event_rows(doc) if key == "weather-events"
                     else _dossier_rows(doc) if key == "weather-dossiers"
                     else _crawl_rows(doc))
            entries.extend(items)
            sources.append({"id": key, "label": label, "state": "READY", "count": len(items)})
        except IndexErrorSafe as exc:
            sources.append({"id": key, "label": label, "state": str(exc), "count": 0})
    if len(entries) > MAX_ROWS:
        raise IndexErrorSafe("INDEX_CAPACITY_EXCEEDED")
    entries.sort(key=lambda r: (-r["recordedAtMs"], r["source"], r["id"]))
    return {"ok": True, "kind": "record-index", "readOnly": True,
            "total": len(entries), "items": entries, "sources": sources}


def main(args):
    try:
        if len(args) != 3 or args[1] != "index":
            raise IndexErrorSafe("READ_ONLY_INDEX_ONLY")
        result = index(args[2])
    except IndexErrorSafe as exc:
        result = {"ok": False, "error": str(exc)}
    except Exception:
        result = {"ok": False, "error": "RECORD_INDEX_FAILED"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
