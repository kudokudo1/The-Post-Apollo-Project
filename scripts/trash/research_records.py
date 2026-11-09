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
MAX_STORE_BYTES = 131072
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
    return hashlib.sha256((page["url"] + "\n" + page["observedAt"]).encode()).hexdigest()[:32]


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
                or set(r) != {"id", "state", "archivedAtMs", "page"}
                or r["state"] not in ("archived", "trashed")
                or type(r["archivedAtMs"]) is not int
                or not 1 <= r["archivedAtMs"] <= 9999999999999):
            _fail("MANAGED_STORE_INVALID")
        try:
            normalized = _page(dict(r["page"], schemaVersion=1,
                                    source="finance-demo-scrapy", readOnly=True))
        except (LifecycleError, TypeError, ValueError):
            _fail("MANAGED_STORE_INVALID")
        if (r["page"] != normalized or not isinstance(r["id"], str)
                or r["id"] != _identity(normalized) or r["id"] in seen):
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


def _summary(document, result="INDEX"):
    items = []
    for record in document["records"]:
        page = record["page"]
        when = _ms(page["observedAt"])
        items.append({
            "id": record["id"], "kind": "SAVED RESEARCH",
            "source": "RESEARCH // DEMO COPY",
            "title": page["title"], "url": page["url"],
            "recordedAtMs": when, "recordedAt": page["observedAt"],
            "archivedAtMs": record["archivedAtMs"],
            "state": record["state"],
            "details": "SOURCE OWNED COPY // " + page["observedAt"],
            "capabilities": {
                "archive": False,
                "trash": record["state"] == "archived",
                "restore": record["state"] == "trashed",
                "burn": record["state"] == "trashed"
            },
        })
    items.sort(key=lambda r: (-r["archivedAtMs"], r["id"]))
    return {"ok": True, "kind": "managed-research", "result": result,
            "revision": document["revision"], "total": len(items), "items": items}


def operate(action, data_dir, record_id="", expected_revision=None,
            confirmation="", when="", home_dir=None):
    if action not in ("list", "archive", "trash", "restore", "burn"):
        _fail("ACTION_NOT_PERMITTED")
    if action == "burn" and confirmation != "BURN_SAVED_COPY_CONFIRMED":
        _fail("BURN_CONFIRMATION_REQUIRED")
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
        if action == "archive":
            page = _source_page(record_id, when, home_dir or Path.home())
            rid = _identity(page)
            if any(r["id"] == rid for r in document["records"]):
                _fail("COPY_ALREADY_EXISTS")
            if len(document["records"]) >= MAX_RECORDS:
                _fail("MANAGED_STORE_CAPACITY")
            document["records"].append({
                "id": rid, "state": "archived",
                "archivedAtMs": int(datetime.now(timezone.utc).timestamp()*1000),
                "page": page
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
        return _summary(document, action.upper())
    finally:
        if lockfd is not None:
            os.close(lockfd)
        os.close(dirfd)


def main(argv):
    try:
        if len(argv) == 3 and argv[1] == "list":
            result = operate("list", argv[2])
        elif len(argv) == 6 and argv[1] == "archive":
            result = operate("archive", argv[2], argv[3], int(argv[5]),
                             when=argv[4])
        elif len(argv) == 5 and argv[1] in ("trash", "restore"):
            result = operate(argv[1], argv[2], argv[3], int(argv[4]))
        elif len(argv) == 6 and argv[1] == "burn":
            result = operate("burn", argv[2], argv[3], int(argv[4]), argv[5])
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
