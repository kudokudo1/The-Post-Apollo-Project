#!/usr/bin/env python3
"""Trash++ explicit V2 pilot snapshot preview/capture, never source mutation.

Quickshell launches this script via python3 -I -B. The only user-operated
verbs are preview and capture for two previously allowlisted source families.
No arbitrary file paths, migration, delete, restore, trash or burn commands.
"""
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys

# -I removes the script directory from sys.path. Add only the trusted app root
# relative to the installed script, never a path or package from the CLI.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.trash.archive_store_v2 import ArchiveError, ArchiveStore
from scripts.trash.archive_v2_location import ArchiveRootError, archive_directory
from scripts.trash.owner_snapshot_adapter_v2 import (
    AdapterError, PilotSnapshotReader, PilotSnapshotAdapter,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
KIND_OWNERS = {"demo": "demo-scrape", "weather": "weather-events"}


class CaptureCliError(Exception):
    """Stable, non-sensitive error code."""


def _preview(reader, source_kind, identity, timestamp):
    if source_kind == "demo":
        return reader.preview_demo(identity, timestamp)
    if source_kind == "weather":
        return reader.preview_weather(identity, timestamp)
    raise CaptureCliError("SOURCE_NOT_ALLOWLISTED")


def execute(action, directory, source_kind, identity, timestamp,
            witness=None, *, home_dir=None):
    """Programmatic test seam; normal CLI derives home from its own process."""
    if action not in ("preview", "capture"):
        raise CaptureCliError("PREVIEW_OR_CAPTURE_ONLY")
    if source_kind not in KIND_OWNERS:
        raise CaptureCliError("SOURCE_NOT_ALLOWLISTED")
    if not isinstance(identity, str) or not isinstance(timestamp, str):
        raise CaptureCliError("INVALID_SOURCE_IDENTITY")
    reader = PilotSnapshotReader(
        data_dir=directory, home_dir=home_dir if home_dir is not None
        else Path.home())
    metadata = _preview(reader, source_kind, identity, timestamp)
    if metadata["ownerId"] != KIND_OWNERS[source_kind]:
        raise CaptureCliError("SOURCE_NOT_ALLOWLISTED")
    if action == "preview":
        if witness is not None:
            raise CaptureCliError("PREVIEW_ARGUMENTS_INVALID")
        return {"ok": True, "kind": "snapshot-preview-v2",
                "readOnly": True, "sourceKind": source_kind,
                "preview": metadata}
    if not isinstance(witness, str) or SHA256.fullmatch(witness) is None:
        raise CaptureCliError("INVALID_SOURCE_WITNESS")
    # Refuse a stale or fabricated witness BEFORE constructing ArchiveStore.
    # Preview of a missing database must never create an empty SQLite file.
    if not hmac.compare_digest(metadata["sourceRevision"], witness):
        raise CaptureCliError("STALE_SOURCE_REFRESH_REQUIRED")
    # Quickshell.dataDir is a shared owner root (often 0755), not the
    # private SQLite root. Create only a dedicated 0700 child, after the
    # explicit confirmation and matching source witness.
    private_root = archive_directory(directory, create=True)
    writer = PilotSnapshotAdapter(
        ArchiveStore(private_root), data_dir=directory,
        home_dir=home_dir if home_dir is not None else Path.home())
    # Re-read the original source again inside capture. The adapter checks
    # the content witness and the store enforces per-owner uniqueness.
    if source_kind == "demo":
        receipt = writer.capture_demo(
            identity, timestamp, expected_revision=witness)
    else:
        receipt = writer.capture_weather(
            identity, timestamp, expected_revision=witness)
    return {"ok": True, "kind": "snapshot-captured-v2", "copyOnly": True,
            "sourceKind": source_kind, "receipt": receipt}


def main(argv):
    try:
        if len(argv) not in (6, 7) or argv[1] not in ("preview", "capture"):
            raise CaptureCliError("PREVIEW_OR_CAPTURE_ONLY")
        if (argv[1] == "preview" and len(argv) != 6
                or argv[1] == "capture" and len(argv) != 7):
            raise CaptureCliError("PREVIEW_OR_CAPTURE_ONLY")
        reply = execute(argv[1], argv[2], argv[3], argv[4], argv[5],
                        argv[6] if len(argv) == 7 else None)
    except (CaptureCliError, AdapterError, ArchiveError,
            ArchiveRootError) as exc:
        reply = {"ok": False, "error": str(exc)}
    except Exception:
        # Fail closed with no user content, paths or a traceback on stdout.
        reply = {"ok": False, "error": "SNAPSHOT_OPERATION_FAILED"}
    print(json.dumps(reply, ensure_ascii=False, separators=(",", ":")))
    return 0 if reply["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
