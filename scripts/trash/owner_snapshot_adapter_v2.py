#!/usr/bin/env python3
"""Trash++ V2b owner-aware source-copy pilot, disconnected from live widget.

This imports the *existing* allowlisted V1 Weather/demo readers, revalidates
the selected source at capture time, and stores only a separate V2 copy.
No generic filesystem scan, CLI, source writes, Trash, Restore or Burn.
"""
import hashlib
import hmac
import json
from pathlib import Path
import re

from scripts.trash.archive_store_v2 import ArchiveStore
from scripts.trash import research_records as source

WITNESS = re.compile(r"^[0-9a-f]{64}$")


class AdapterError(Exception):
    """Stable error codes; do not include user source payloads or paths."""


def _root(value):
    if not isinstance(value, (str, Path)):
        raise AdapterError("INVALID_OWNER_ROOT")
    path = Path(value)
    if (not path.is_absolute() or ".." in path.parts
            or len(str(path)) > 4096):
        raise AdapterError("INVALID_OWNER_ROOT")
    return path


def _bytes(value):
    # Source-normalized JSON makes the selected record's digest independent
    # of irrelevant whitespace or unrelated records in the owner file.
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise AdapterError("SOURCE_PAYLOAD_INVALID") from exc


def _prepared(owner, identifier, label, captured, record):
    payload = _bytes(record)
    revision = hashlib.sha256(payload).hexdigest()
    # ArchiveStore labels are at most 120 printable characters. The Weather
    # owner permits longer titles; sanitize *display only*, not source bytes.
    visible_label = "".join(c for c in label if c.isprintable())[:120]
    return {
        "ownerId": owner,
        "resourceId": identifier,
        "sourceRevision": revision,
        "capturedAtMs": captured,
        "displayLabel": visible_label,
        "_payload": payload,
    }


def _preview(prepared):
    # Never include the private payload in metadata/read-only discovery.
    return {key: value for key, value in prepared.items()
            if key != "_payload"}


class PilotSnapshotAdapter:
    """Manual, opt-in disposable source copying; not a source owner writer.

    The caller supplies the expected SHA-256 witness from preview. Capture
    *re-reads and validates* the selected owner item using V1's trusted,
    fixed-path source reader, and refuses stale/mismatched bytes.
    """

    def __init__(self, archive, *, data_dir, home_dir):
        if not isinstance(archive, ArchiveStore):
            raise AdapterError("INVALID_ARCHIVE_STORE")
        self.archive = archive
        self.data_dir = _root(data_dir)
        self.home_dir = _root(home_dir)

    def _demo(self, url, observed_at):
        try:
            page = source._source_page(url, observed_at, self.home_dir)
            observed_ms = source._ms(page["observedAt"])
        except source.LifecycleError as exc:
            raise AdapterError(str(exc)) from exc
        except (UnicodeError, TypeError, ValueError) as exc:
            raise AdapterError("SOURCE_VALIDATION_FAILED") from exc
        record_id = "page-" + hashlib.sha256(page["url"].encode("utf-8")).hexdigest()[:32]
        return _prepared("demo-scrape", record_id, page["title"], observed_ms, page)

    def _weather(self, event_key, last_captured_ms):
        if (type(last_captured_ms) is int
                and 1 <= last_captured_ms <= 9999999999999):
            stamp = str(last_captured_ms)
        elif (isinstance(last_captured_ms, str)
              and last_captured_ms.isascii()
              and last_captured_ms.isdecimal()
              and 1 <= len(last_captured_ms) <= 13
              and 1 <= int(last_captured_ms) <= 9999999999999):
            stamp = str(int(last_captured_ms))
        else:
            raise AdapterError("INVALID_EVENT_TIMESTAMP")
        # The legacy V1 owner reader requires the exact event key and latest
        # snapshot timestamp; the full-content witness below catches a rewrite
        # that retains the same timestamp.
        try:
            event = source._source_event(event_key, stamp, self.data_dir)
        except source.LifecycleError as exc:
            raise AdapterError(str(exc)) from exc
        except (UnicodeError, TypeError, ValueError) as exc:
            raise AdapterError("SOURCE_VALIDATION_FAILED") from exc
        record_id = ("event-" +
                     hashlib.sha256(event["eventKey"].encode("utf-8")).hexdigest()[:32])
        return _prepared("weather-events", record_id, event["title"],
                         event["lastCapturedAtMs"], event)

    def preview_demo(self, url, observed_at):
        return _preview(self._demo(url, observed_at))

    def preview_weather(self, event_key, last_captured_ms):
        return _preview(self._weather(event_key, last_captured_ms))

    def _capture(self, prepared, expected_revision):
        if (not isinstance(expected_revision, str)
                or WITNESS.fullmatch(expected_revision) is None):
            raise AdapterError("INVALID_SOURCE_WITNESS")
        if not hmac.compare_digest(prepared["sourceRevision"], expected_revision):
            raise AdapterError("STALE_SOURCE_REFRESH_REQUIRED")
        return self.archive.save(
            prepared["ownerId"], prepared["resourceId"],
            prepared["sourceRevision"], prepared["_payload"],
            display_label=prepared["displayLabel"],
            captured_ms=prepared["capturedAtMs"])

    def capture_demo(self, url, observed_at, *, expected_revision):
        return self._capture(self._demo(url, observed_at), expected_revision)

    def capture_weather(self, event_key, last_captured_ms, *, expected_revision):
        return self._capture(self._weather(event_key, last_captured_ms),
                             expected_revision)
