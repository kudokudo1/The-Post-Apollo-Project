#!/usr/bin/env python3
"""Trash++ managed demo-research copies: source never mutated.

ARCHIVE copies a strictly validated quotes.toscrape.com demonstration page
into an independent, bounded Trash++ record store. TRASH / RESTORE / BURN
operate ONLY on those managed copies, never on the Finance-owned crawl,
Weather history, Hospital evidence, or arbitrary filesystem paths.
"""
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4

STORE_NAME = "trashpp-research-copies-v1.json"
LOCK_NAME = "trashpp-research-copies-v1.lock"
STORE_SCHEMA = "post-apollo.trash-managed-research.v1"
CRAWL_PATH = ".local/share/post-apollo/finance-crawler/crawl-records.json"
MAX_CRAWL_BYTES = 262144
MAX_STORE_BYTES = 1048576
MAX_WEATHER_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_EVENT_COPY_BYTES = 65536
WEATHER_EVENT_NAME = "weather-event-archive-v1.json"
WEATHER_EVENT_SCHEMA = "post-apollo.weather-event-archive.v1"
WEATHER_SOURCES = {"gdacs", "usgs", "eonet", "firms"}
MAX_RECORDS = 64
MAX_PAGES = 6
MAX_DATA_DIR = 4096
MAX_REVISION = 2147483647


class LifecycleError(Exception):
    pass


def _fail(reason):
    raise LifecycleError(reason)


def _safe_text(value, maximum):
    if not isinstance(value, str):
        _fail("INVALID_RESEARCH_PAGE")
    return "".join(c if c.isprintable() else " " for c in value.strip())[:maximum]


def _url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 400:
        _fail("INVALID_RESEARCH_PAGE")
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.hostname != "quotes.toscrape.com"
                or parsed.username or parsed.password or parsed.port is not None
                or parsed.fragment):
            _fail("SOURCE_NOT_ALLOWLISTED")
    except ValueError:
        _fail("SOURCE_NOT_ALLOWLISTED")
    return value


def _ms(value):
    if not isinstance(value, str) or len(value) > 64:
        _fail("INVALID_RESEARCH_PAGE")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            _fail("INVALID_RESEARCH_PAGE")
        stamp = int(dt.timestamp() * 1000)
        if not 1 <= stamp <= 9999999999999:
            _fail("INVALID_RESEARCH_PAGE")
        return stamp
    except (ValueError, OverflowError):
        _fail("INVALID_RESEARCH_PAGE")


def _page(raw):
    if (not isinstance(raw, dict) or raw.get("schemaVersion") != 1
            or raw.get("source") != "finance-demo-scrapy"
            or raw.get("readOnly") is not True):
        _fail("SOURCE_NOT_ALLOWLISTED")
    url = _url(raw.get("url"))
    title = _safe_text(raw.get("title"), 150)
    when = _safe_text(raw.get("observedAt"), 64)
    _ms(when)
    if not title:
        _fail("INVALID_RESEARCH_PAGE")
    links = raw.get("links")
    snippets = raw.get("snippets")
    if (not isinstance(links, list) or len(links) > 32
            or not isinstance(snippets, list) or len(snippets) > 3):
        _fail("INVALID_RESEARCH_PAGE")
    clean_links = list(dict.fromkeys(_url(link) for link in links))
    clean_snippets = [_safe_text(txt, 240) for txt in snippets]
    return {"url": url, "title": title, "observedAt": when,
            "links": clean_links, "snippets": clean_snippets}


def _identity(page):
    # Legacy v1 demo copies used this immutable hash as their actual ID.
    return hashlib.sha256((page["url"] + "\n" + page["observedAt"]).encode()).hexdigest()[:32]


def _event_key(key):
    if not isinstance(key, str) or len(key) > 240 or "|" not in key:
        _fail("INVALID_EVENT_IDENTITY")
    source, event_id = key.split("|", 1)
    if source not in WEATHER_SOURCES or not event_id or len(event_id) > 180:
        _fail("INVALID_EVENT_IDENTITY")
    return source, event_id


def _event_snapshot(raw, source, event_id):
    if (not isinstance(raw, dict) or raw.get("sourceId") != source
            or raw.get("eventId") != event_id
            or raw.get("eventKey") != source + "|" + event_id
            or type(raw.get("capturedAtMs")) is not int
            or not 1 <= raw["capturedAtMs"] <= 9999999999999
            or not isinstance(raw.get("payload"), dict)):
        _fail("INVALID_WEATHER_EVENT")
    return raw["capturedAtMs"]


def _event(value):
    """Validate the complete source-owned public event before copying bytes.

    Original snapshots and payload are preserved in the immutable copy.
    Nothing in this function writes back to the Weather archive.
    """
    if not isinstance(value, dict):
        _fail("INVALID_WEATHER_EVENT")
    source, event_id = _event_key(value.get("eventKey"))
    if (value.get("sourceId") != source or value.get("eventId") != event_id
            or not isinstance(value.get("title"), str)
            or not isinstance(value.get("typeLabel"), str)
            or type(value.get("firstCapturedAtMs")) is not int
            or type(value.get("lastCapturedAtMs")) is not int):
        _fail("INVALID_WEATHER_EVENT")
    snaps = value.get("snapshots")
    if not isinstance(snaps, list) or not 1 <= len(snaps) <= 32:
        _fail("INVALID_WEATHER_EVENT")
    times = [_event_snapshot(row, source, event_id) for row in snaps]
    if (min(times) != value["firstCapturedAtMs"]
            or max(times) != value["lastCapturedAtMs"]):
        _fail("INVALID_WEATHER_EVENT")
    try:
        encoded = json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError):
        _fail("INVALID_WEATHER_EVENT")
    if len(encoded) > MAX_EVENT_COPY_BYTES:
        _fail("EVENT_COPY_TOO_LARGE")
    return value


def _source_event(key, stamp, data_dir):
    source, event_id = _event_key(key)
    doc = _regular_json(Path(data_dir) / WEATHER_EVENT_NAME,
                        MAX_WEATHER_ARCHIVE_BYTES)
    if (not isinstance(doc, dict) or doc.get("schema") != WEATHER_EVENT_SCHEMA
            or doc.get("version") != 1 or not isinstance(doc.get("events"), dict)
            or len(doc["events"]) > 256):
        _fail("WEATHER_EVENT_SOURCE_UNAVAILABLE")
    raw = doc["events"].get(key)
    if raw is None:
        _fail("STALE_WEATHER_EVENT_REFRESH")
    event = _event(raw)
    if (event["sourceId"] != source or event["eventId"] != event_id
            or str(event["lastCapturedAtMs"]) != stamp):
        _fail("STALE_WEATHER_EVENT_REFRESH")
    return event


def _record_origin(record):
    # Duplicate protection applies only to active copies, NOT those sitting
    # in Trash. Each new copy gets a fresh independent UUID.
    if "event" in record:
        event = record["event"]
        return "weather:" + event["eventKey"] + ":" + str(event["lastCapturedAtMs"])
    return "demo:" + _identity(record["page"])


def _regular_json(path, max_bytes):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError:
        _fail("SOURCE_UNREADABLE")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not 2 <= st.st_size <= max_bytes:
            _fail("SOURCE_UNSAFE")
        data = os.read(fd, max_bytes + 1)
        if len(data) > max_bytes:
            _fail("SOURCE_UNSAFE")
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            _fail("SOURCE_INVALID_JSON")
    finally:
        os.close(fd)


def _source_page(url, when, home_dir):
    source = _regular_json(Path(home_dir) / CRAWL_PATH, MAX_CRAWL_BYTES)
    if not isinstance(source, list) or len(source) > MAX_PAGES:
        _fail("DEMO_SOURCE_MISSING_OR_INVALID")
    matches = []
    seen = set()
    for raw in source:
        page = _page(raw)
        if page["url"] in seen:
            _fail("SOURCE_DUPLICATE_URL")
        seen.add(page["url"])
        if page["url"] == url and page["observedAt"] == when:
            matches.append(page)
    if len(matches) != 1:
        _fail("STALE_DEMO_SOURCE_REFRESH")
    return matches[0]


def _empty():
    return {"schema": STORE_SCHEMA, "version": 1, "revision": 0, "records": []}


def _validate_store(value):
    if (not isinstance(value, dict) or set(value) != {"schema", "version", "revision", "records"}
            or value["schema"] != STORE_SCHEMA or value["version"] != 1
            or type(value["revision"]) is not int
            or not 0 <= value["revision"] <= MAX_REVISION
            or not isinstance(value["records"], list)
            or len(value["records"]) > MAX_RECORDS):
        _fail("MANAGED_STORE_INVALID")
    seen = set()
    for r in value["records"]:
        if (not isinstance(r, dict)
                or r["state"] not in ("archived", "trashed")
                or type(r.get("archivedAtMs")) is not int
                or not 1 <= r["archivedAtMs"] <= 9999999999999
                or not isinstance(r.get("id"), str)
                or len(r["id"]) != 32
                or any(c not in "0123456789abcdef" for c in r["id"])
                or r["id"] in seen):
            _fail("MANAGED_STORE_INVALID")
        if set(r) == {"id", "state", "archivedAtMs", "page"}:
            try:
                normalized = _page(dict(r["page"], schemaVersion=1,
                                        source="finance-demo-scrapy", readOnly=True))
            except (LifecycleError, TypeError, ValueError):
                _fail("MANAGED_STORE_INVALID")
            if r["page"] != normalized:
                _fail("MANAGED_STORE_INVALID")
            # Previously hashed IDs remain valid, and new copies use random
            # 32-char IDs to avoid colliding with an item still in the bin.
        elif set(r) == {"id", "state", "archivedAtMs", "event"}:
            try:
                _event(r["event"])
            except (LifecycleError, TypeError, ValueError):
                _fail("MANAGED_STORE_INVALID")
        else:
            _fail("MANAGED_STORE_INVALID")
        seen.add(r["id"])
    return value


def _root(data_dir):
    if (not isinstance(data_dir, str) or len(data_dir) > MAX_DATA_DIR
            or not os.path.isabs(data_dir) or "\x00" in data_dir):
        _fail("INVALID_DATA_DIRECTORY")
    try:
        return os.open(data_dir, os.O_RDONLY | os.O_DIRECTORY
                       | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        _fail("DATA_DIRECTORY_UNAVAILABLE")


def _read_store(dirfd):
    try:
        fd = os.open(STORE_NAME, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0), dir_fd=dirfd)
    except FileNotFoundError:
        return _empty()
    except OSError:
        _fail("MANAGED_STORE_UNSAFE")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not 2 <= st.st_size <= MAX_STORE_BYTES:
            _fail("MANAGED_STORE_UNSAFE")
        raw = os.read(fd, MAX_STORE_BYTES + 1)
        if len(raw) > MAX_STORE_BYTES:
            _fail("MANAGED_STORE_UNSAFE")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            _fail("MANAGED_STORE_INVALID")
        return _validate_store(data)
    finally:
        os.close(fd)


def _write_store(dirfd, document):
    _validate_store(document)
    raw = (json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_STORE_BYTES:
        _fail("MANAGED_STORE_CAPACITY")
    temp = "." + STORE_NAME + "." + uuid4().hex + ".tmp"
    fd = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dirfd)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as f:
            fd = None
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, STORE_NAME, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        os.fsync(dirfd)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temp, dir_fd=dirfd)
        except FileNotFoundError:
            pass


def _lock(dirfd):
    try:
        fd = os.open(LOCK_NAME, os.O_RDWR | os.O_CREAT
                     | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dirfd)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            _fail("MANAGED_STORE_UNSAFE")
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd
    except OSError:
        _fail("MANAGED_STORE_LOCK_FAILED")


def _bin_identity(document):
    """Inventory witness of only trashed managed-copy IDs, sorted and bounded."""
    ids = sorted(r["id"] for r in document["records"] if r["state"] == "trashed")
    digest = hashlib.sha256("\\n".join(ids).encode("ascii")).hexdigest()
    return len(ids), digest


def _summary(document, result="INDEX"):
    items = []
    for record in document["records"]:
        if "event" in record:
            event = record["event"]
            when = event["lastCapturedAtMs"]
            iso = datetime.fromtimestamp(when / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            kind, source = "SAVED EVENT", "WEATHER // EVENT COPY"
            title, url = event["title"], ""
            details = (event["sourceId"].upper() + " // " + event["eventId"]
                       + " // " + str(len(event["snapshots"])) + " SNAPSHOTS")
        else:
            page = record["page"]
            when = _ms(page["observedAt"])
            iso = page["observedAt"]
            kind, source = "SAVED RESEARCH", "RESEARCH // DEMO COPY"
            title, url = page["title"], page["url"]
            details = "SOURCE OWNED COPY // " + page["observedAt"]
        items.append({
            "id": record["id"], "kind": kind,
            "source": source, "title": title, "url": url,
            "recordedAtMs": when, "recordedAt": iso,
            "archivedAtMs": record["archivedAtMs"],
            "state": record["state"], "details": details,
            "capabilities": {
                "archive": False,
                "trash": record["state"] == "archived",
                "restore": record["state"] == "trashed",
                "burn": record["state"] == "trashed"
            },
        })
    items.sort(key=lambda r: (-r["archivedAtMs"], r["id"]))
    bin_count, bin_digest = _bin_identity(document)
    return {"ok": True, "kind": "managed-research", "result": result,
            "revision": document["revision"], "total": len(items),
            "binCount": bin_count, "binDigest": bin_digest, "items": items}


def operate(action, data_dir, record_id="", expected_revision=None,
            confirmation="", when="", home_dir=None, expected_count=None,
            expected_digest=""):
    if action not in ("list", "archive", "archive-event", "trash", "restore", "burn",
                      "burn-all"):
        _fail("ACTION_NOT_PERMITTED")
    if action == "burn" and confirmation != "BURN_SAVED_COPY_CONFIRMED":
        _fail("BURN_CONFIRMATION_REQUIRED")
    if action == "burn-all" and confirmation != "BURN_ALL_MANAGED_COPIES_CONFIRMED":
        _fail("BURN_ALL_CONFIRMATION_REQUIRED")
    dirfd = _root(data_dir)
    lockfd = None
    try:
        if action != "list":
            lockfd = _lock(dirfd)
        document = _read_store(dirfd)
        if action == "list":
            return _summary(document)
        if (type(expected_revision) is not int
                or expected_revision != document["revision"]):
            _fail("STALE_MANAGED_REVISION")
        if document["revision"] >= MAX_REVISION:
            _fail("MANAGED_STORE_CAPACITY")
        # Snapshot receipt candidates BEFORE mutation, from the validated
        # source-managed store, then return them ONLY after a durable write.
        receipt_before = (
            [item for item in _summary(document)["items"]
             if item["state"] == "trashed"
             and (action == "burn-all" or item["id"] == record_id)]
            if action in ("burn", "burn-all") else []
        )
        if action == "burn-all":
            current_count, current_digest = _bin_identity(document)
            if (type(expected_count) is not int or expected_count < 1
                    or current_count != expected_count
                    or not isinstance(expected_digest, str)
                    or len(expected_digest) != 64
                    or expected_digest != current_digest):
                _fail("STALE_MANAGED_BIN")
            # Authoritative source-owned archived copies are not touched.
            # This only removes the already-trashed managed snapshot copies.
            document["records"] = [
                r for r in document["records"] if r["state"] != "trashed"
            ]
        elif action in ("archive", "archive-event"):
            if action == "archive":
                content_key, content = "page", _source_page(
                    record_id, when, home_dir or Path.home())
            else:
                content_key, content = "event", _source_event(
                    record_id, when, data_dir)
            candidate = {content_key: content}
            if any(r["state"] == "archived"
                   and _record_origin(r) == _record_origin(candidate)
                   for r in document["records"]):
                _fail("COPY_ALREADY_EXISTS")
            if len(document["records"]) >= MAX_RECORDS:
                _fail("MANAGED_STORE_CAPACITY")
            document["records"].append({
                "id": uuid4().hex, "state": "archived",
                "archivedAtMs": int(datetime.now(timezone.utc).timestamp()*1000),
                content_key: content
            })
        else:
            if (not isinstance(record_id, str) or len(record_id) != 32
                    or any(c not in "0123456789abcdef" for c in record_id)):
                _fail("UNKNOWN_MANAGED_RECORD")
            entry = next((x for x in document["records"] if x["id"] == record_id), None)
            if entry is None:
                _fail("UNKNOWN_MANAGED_RECORD")
            if action == "trash":
                if entry["state"] != "archived":
                    _fail("NOT_ARCHIVED")
                entry["state"] = "trashed"
            elif action == "restore":
                if entry["state"] != "trashed":
                    _fail("NOT_IN_TRASH")
                entry["state"] = "archived"
            elif action == "burn":
                if entry["state"] != "trashed":
                    _fail("BURN_REQUIRES_TRASH_FIRST")
                # This removes only the independent Trash++ copy from its
                # own atomic JSON store. No source file is ever touched.
                document["records"].remove(entry)
        document["revision"] += 1
        _write_store(dirfd, document)
        result = _summary(document, action.upper())
        if action in ("burn", "burn-all"):
            result["verified"] = True
            result["burnedCount"] = len(receipt_before)
            result["burnedItems"] = [
                {"id": item["id"], "kind": item["kind"],
                 "name": item["title"], "source": item["source"]}
                for item in receipt_before
            ]
        return result
    finally:
        if lockfd is not None:
            os.close(lockfd)
        os.close(dirfd)


def main(argv):
    try:
        if len(argv) == 3 and argv[1] == "list":
            result = operate("list", argv[2])
        elif len(argv) == 6 and argv[1] in ("archive", "archive-event"):
            result = operate(argv[1], argv[2], argv[3], int(argv[5]),
                             when=argv[4])
        elif len(argv) == 5 and argv[1] in ("trash", "restore"):
            result = operate(argv[1], argv[2], argv[3], int(argv[4]))
        elif len(argv) == 6 and argv[1] == "burn":
            result = operate("burn", argv[2], argv[3], int(argv[4]), argv[5])
        elif len(argv) == 7 and argv[1] == "burn-all":
            result = operate("burn-all", argv[2], expected_revision=int(argv[3]),
                             expected_count=int(argv[4]), expected_digest=argv[5],
                             confirmation=argv[6])
        else:
            _fail("ACTION_NOT_PERMITTED")
    except (LifecycleError, ValueError) as exc:
        result = {"ok": False, "error": str(exc)[:110]}
    except Exception:
        result = {"ok": False, "error": "MANAGED_RESEARCH_OPERATION_FAILED"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
