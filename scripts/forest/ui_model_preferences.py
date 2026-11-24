#!/usr/bin/env python3
"""ForestW local UI preferences only. No model, network or authority IO."""
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import uuid

TREES = ("CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH")
MAX_BYTES = 8192
MAX_REVISION = 2**53 - 1
FILE = "model-preferences-v1.json"
LOCK = ".model-preferences-v1.lock"


class Refusal(Exception):
    pass


def exact(value, keys):
    return type(value) is dict and set(value) == set(keys)


def valid_name(value):
    import re
    return type(value) is str and (value == "" or re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value) is not None)


def validate_preferences(value):
    if not exact(value, TREES):
        raise Refusal("INVALID_TREES")
    for entry in value.values():
        if (not exact(entry, ("small", "big", "form", "reasoning"))
                or not valid_name(entry["small"]) or not valid_name(entry["big"])
                or type(entry["form"]) is not str
                or entry["form"] not in ("SMALL", "AUTO", "BIG")
                or type(entry["reasoning"]) is not int
                or not 0 <= entry["reasoning"] <= 3):
            raise Refusal("INVALID_PREFERENCE")
    return value


def defaults():
    return {"version": 1, "revision": 0, "trees": {
        tree: {"small": "", "big": "", "form": "AUTO", "reasoning": 0}
        for tree in TREES}}


def validate_document(doc):
    if (not exact(doc, ("version", "revision", "trees"))
            or type(doc["version"]) is not int or doc["version"] != 1
            or type(doc["revision"]) is not int
            or not 1 <= doc["revision"] <= MAX_REVISION):
        raise Refusal("INVALID_DOCUMENT")
    validate_preferences(doc["trees"])
    return doc


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal("INVALID_JSON") from None


def store_path():
    base = os.environ.get("XDG_DATA_HOME", "")
    if not base or not Path(base).is_absolute():
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "post-apollo" / "forest" / "ui-preferences"


def open_directory(path, create):
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        if not create:
            return None
        raise
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise Refusal("UNSAFE_DIRECTORY")
    return fd


def safe_file(fd, limit=MAX_BYTES):
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1
            or info.st_size > limit):
        raise Refusal("UNSAFE_RECORD")


def read_doc(directory):
    if directory is None:
        return defaults()
    try:
        fd = os.open(FILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
    except FileNotFoundError:
        return defaults()
    try:
        safe_file(fd)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise Refusal("STORE_LIMIT")
        return validate_document(decode(raw))
    finally:
        os.close(fd)


def write_doc(directory, doc):
    raw = (json.dumps(validate_document(doc), separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_BYTES:
        raise Refusal("STORE_LIMIT")
    temp = "." + uuid.uuid4().hex + ".tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, FILE, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temp, dir_fd=directory)
        except FileNotFoundError:
            pass


def run(path, command):
    if exact(command, ("action",)) and command["action"] == "load":
        directory = open_directory(path, False)
        try:
            return read_doc(directory)
        finally:
            if directory is not None:
                os.close(directory)
    if (not exact(command, ("action", "expectedRevision", "trees"))
            or command["action"] != "save"
            or type(command["expectedRevision"]) is not int
            or not 0 <= command["expectedRevision"] < MAX_REVISION):
        raise Refusal("INVALID_COMMAND")
    validate_preferences(command["trees"])
    directory = open_directory(path, True)
    try:
        lock = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                       0o600, dir_fd=directory)
        try:
            safe_file(lock, 0)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refusal("WRITE_BUSY") from None
            old = read_doc(directory)
            if old["revision"] != command["expectedRevision"]:
                raise Refusal("STALE_REVISION")
            if old["trees"] == command["trees"]:
                return old
            doc = {"version": 1, "revision": old["revision"] + 1,
                   "trees": command["trees"]}
            write_doc(directory, doc)
            return doc
        finally:
            os.close(lock)
    finally:
        os.close(directory)


def main():
    raw = sys.stdin.buffer.readline(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or not raw.endswith(b"\n"):
        raise Refusal("INVALID_INPUT")
    doc = run(store_path(), decode(raw))
    print(json.dumps({"source": "FORESTW_LOCAL_UI_PREFERENCES",
                      "production_authority": False, **doc}, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError) as exc:
        print("FORESTW_PREFERENCE_REFUSED", file=sys.stderr)
        sys.exit(1)
