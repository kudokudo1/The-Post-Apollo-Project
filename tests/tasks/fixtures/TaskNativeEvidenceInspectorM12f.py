#!/usr/bin/env python3
"""M12f read-only disposable M11g fixture + SQLite authority evidence inspector.

No file creation, host launch, production paths, native Quickshell execution,
credentials or migration. Native tags are operator-supplied observations,
not an independently authenticated callback trace or stage attestation.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

SOURCE_NAME = "fixture-only.json"
FOLDER_NAME = "m11e-fileview-test"
DB_NAME = "handoff-test.db"
MAX_BYTES = 2048
ALLOWED_PHASES = frozenset({
    "JSON_ACTIVE", "FREEZE_REQUESTED", "JSON_QUIESCED", "RECOVERY_REVIEW"
})
TAGS = frozenset({
    "ATTACH_REQUEST", "HOST_HELLO", "FILE_INITIAL_LOAD",
    "STAGE_REQUEST", "HOST_ADMIT", "FILE_SAVED", "FILE_READBACK_OK",
    "HOST_SETTLED", "FREEZE_REQUEST", "HOST_FROZEN", "HOST_EXIT",
    "FILE_SAVE_FAILURE", "FILE_LOAD_FAILURE", "FILE_READBACK_MISMATCH",
    "HOST_REFUSAL", "RECOVERY_REVIEW", "STOP_REQUEST"
})
ORDER = ("STAGE_REQUEST", "HOST_ADMIT", "FILE_SAVED",
         "FILE_READBACK_OK", "HOST_SETTLED")


class EvidenceRefusal(ValueError):
    pass


def require(ok: bool, code: str):
    if not ok:
        raise EvidenceRefusal(code)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_FIXTURE_KEY")
        result[key] = value
    return result


def private_folder(file: Path):
    require(isinstance(file, Path) and file.is_absolute() and
            ".." not in file.parts and file.name == SOURCE_NAME and
            file.parent.name == FOLDER_NAME,
            "M11E_DISPOSABLE_SOURCE_ONLY")
    folder = file.parent
    try:
        s = folder.lstat()
    except OSError:
        raise EvidenceRefusal("PRIVATE_FIXTURE_DIRECTORY_REQUIRED") from None
    require(stat.S_ISDIR(s.st_mode) and not folder.is_symlink() and
            s.st_uid == os.geteuid() and
            stat.S_IMODE(s.st_mode) == 0o700,
            "PRIVATE_FIXTURE_DIRECTORY_REQUIRED")
    return folder


def private_file(file: Path, maximum: int):
    try:
        s = file.lstat()
        require(stat.S_ISREG(s.st_mode) and not file.is_symlink() and
                s.st_uid == os.geteuid() and s.st_nlink == 1 and
                stat.S_IMODE(s.st_mode) == 0o600 and
                0 < s.st_size <= maximum, "PRIVATE_FIXTURE_FILE_REQUIRED")
        fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            a = os.fstat(fd)
            raw = bytearray()
            while len(raw) <= maximum:
                piece = os.read(fd, maximum + 1 - len(raw))
                if not piece:
                    break
                raw.extend(piece)
            b = os.fstat(fd)
            z = file.lstat()
            ident = lambda x: (x.st_dev, x.st_ino, x.st_size,
                               x.st_mtime_ns, x.st_ctime_ns)
            require(ident(s) == ident(a) == ident(b) == ident(z) and
                    len(raw) == s.st_size and len(raw) <= maximum,
                    "FIXTURE_READ_CHANGED")
            return bytes(raw)
        finally:
            os.close(fd)
    except EvidenceRefusal:
        raise
    except OSError:
        raise EvidenceRefusal("PRIVATE_FIXTURE_FILE_REQUIRED") from None



def acquire_disposable_lock(folder: Path):
    # Hold the same existing M10p lifetime lock while inspecting. This only
    # fences cooperating M11g owners, not arbitrary noncooperating writers.
    lockfile = folder / "handoff-test.lock"
    try:
        meta = lockfile.lstat()
        require(stat.S_ISREG(meta.st_mode) and not lockfile.is_symlink() and
                meta.st_uid == os.geteuid() and meta.st_nlink == 1 and
                stat.S_IMODE(meta.st_mode) == 0o600,
                "PRIVATE_FIXTURE_LOCK_REQUIRED")
        fd = os.open(lockfile, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            observed = os.fstat(fd)
            require((observed.st_dev,observed.st_ino) ==
                    (meta.st_dev,meta.st_ino),
                    "PRIVATE_FIXTURE_LOCK_REQUIRED")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        return fd
    except BlockingIOError:
        raise EvidenceRefusal("NATIVE_HOST_STILL_OWNS_FIXTURE") from None
    except EvidenceRefusal:
        raise
    except OSError:
        raise EvidenceRefusal("PRIVATE_FIXTURE_LOCK_REQUIRED") from None


def fixture_snapshot(file: Path):
    private_folder(file)
    first = private_file(file, MAX_BYTES)
    second = private_file(file, MAX_BYTES)
    require(first == second, "FIXTURE_SOURCE_DRIFT")
    try:
        data = json.loads(first.decode("utf-8"), object_pairs_hook=unique)
    except EvidenceRefusal:
        raise
    except (ValueError, UnicodeError):
        raise EvidenceRefusal("INVALID_FIXTURE_JSON") from None
    require(type(data) is dict and
            set(data) == {"fixture", "revision", "counter", "marker"} and
            data["fixture"] == "M11E_SYNTHETIC_ONLY" and
            data["marker"] == "sample" and
            type(data["revision"]) is int and
            type(data["counter"]) is int and
            0 <= data["counter"] <= 1000000 and
            data["revision"] == data["counter"],
            "INVALID_FIXTURE_DOCUMENT")
    return first, data


def journal_snapshot(folder: Path):
    db = folder / DB_NAME
    private_file(db, 1048576)
    # SQLITE OPEN READONLY. Requires completed/closed disposable host for a
    # meaningful final state; SQLite may access existing WAL/shm sidecars.
    uri = "file:" + quote(str(db), safe="/") + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=0.2) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            require(version == 1, "UNSUPPORTED_TEST_JOURNAL")
            columns = {row[1] for row in connection.execute(
                "PRAGMA table_info(authority)")}
            require(columns == {"id","phase","epoch","owner_id",
                                "pending_stage","source_hash","reason"},
                    "UNSUPPORTED_TEST_JOURNAL")
            rows = connection.execute(
                "SELECT id,phase,epoch,owner_id,pending_stage,source_hash,"
                "reason FROM authority").fetchall()
            require(len(rows) == 1 and rows[0]["id"] == 1,
                    "INVALID_TEST_JOURNAL")
            row = rows[0]
            require(row["phase"] in ALLOWED_PHASES and
                    type(row["epoch"]) is int and 0 <= row["epoch"] < 999999999 and
                    type(row["owner_id"]) is str and
                    re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,95}",
                                 row["owner_id"]) is not None,
                    "INVALID_TEST_JOURNAL")
            pending = row["pending_stage"] is not None
            if pending:
                require(type(row["pending_stage"]) is str and
                        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,95}",
                                     row["pending_stage"]) is not None,
                        "INVALID_TEST_JOURNAL")
            return {"phase": row["phase"], "epoch": row["epoch"],
                    "pending": pending}
    except EvidenceRefusal:
        raise
    except sqlite3.Error:
        raise EvidenceRefusal("JOURNAL_READ_REFUSED") from None


def trace_observation(tags):
    require(type(tags) is list and len(tags) <= 32 and
            all(type(x) is str and x in TAGS for x in tags),
            "INVALID_OPERATOR_TRACE")
    # Native tag evidence is supplied by the operator, not captured here.
    progress = 0
    chains = 0
    for tag in tags:
        if tag in ("FILE_SAVE_FAILURE","FILE_LOAD_FAILURE",
                   "FILE_READBACK_MISMATCH","HOST_EXIT",
                   "RECOVERY_REVIEW","HOST_REFUSAL"):
            progress = 0
        elif tag == "STAGE_REQUEST":
            progress = 1
        elif progress > 0 and tag == ORDER[progress]:
            progress += 1
            if progress == len(ORDER):
                chains += 1
                progress = 0
        elif tag in ORDER:
            progress = 0
    return {"operatorTraceSupplied": bool(tags),
            "operatorReportedCompleteChains": chains,
            "nativeEventsIndependentlyCaptured": False,
            "nativeStageAttributionProven": False}


def inspect(fixture_file: Path, expected_counter: int, expected_phase: str,
            tags=None):
    require(type(expected_counter) is int and 0 <= expected_counter <= 100,
            "EXPECTED_COUNTER_REQUIRED")
    require(expected_phase in ALLOWED_PHASES,
            "EXPECTED_PHASE_REQUIRED")
    folder = private_folder(fixture_file)
    lock_fd = acquire_disposable_lock(folder)
    try:
        raw, document = fixture_snapshot(fixture_file)
        journal = journal_snapshot(folder)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
    obs = trace_observation([] if tags is None else tags)
    passed = (document["counter"] == expected_counter and
              journal["phase"] == expected_phase)
    # Report is intentionally free of owner/stage IDs, filenames, source
    # text, path, hashes, profile keys, QML logs and user-supplied contents.
    return {
        "milestone": "M12f", "scope": "M11E_SYNTHETIC_ONLY",
        "status": "SYNTHETIC_JOURNAL_MATCH" if passed
                  else "SYNTHETIC_EXPECTATION_MISMATCH",
        "sourceSchemaValid": True, "sourceStableRead": True,
        "observedCounter": document["counter"],
        "journalPhase": journal["phase"], "journalEpoch": journal["epoch"],
        "journalPending": journal["pending"],
        "sourceMatchesExpectedCounter": document["counter"] == expected_counter,
        "journalMatchesExpectedPhase": journal["phase"] == expected_phase,
        "readOnlyCodePath": True, "productionWriterAuthorized": False,
        "realTasksDataAccess": False, "nativeRuntimeExecutedByInspector": False,
        "independentNativeAcceptance": False, **obs
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="M12f read-only M11e disposable evidence inspector")
    parser.add_argument("--fixture-file", required=True, type=Path)
    parser.add_argument("--expected-counter", required=True, type=int)
    parser.add_argument("--expected-phase", required=True, choices=sorted(ALLOWED_PHASES))
    parser.add_argument("--operator-native-tags", default="")
    args = parser.parse_args(argv)
    try:
        tags = args.operator_native_tags.split(",") if args.operator_native_tags else []
        report = inspect(args.fixture_file, args.expected_counter,
                         args.expected_phase, tags)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["status"] == "SYNTHETIC_JOURNAL_MATCH" else 1
    except (EvidenceRefusal, OSError, TypeError, ValueError):
        print(json.dumps({"milestone":"M12f","status":"EVIDENCE_REFUSED",
                          "productionWriterAuthorized":False,
                          "independentNativeAcceptance":False},sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
