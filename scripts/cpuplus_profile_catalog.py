#!/usr/bin/env python3
"""Private CPU++ profile catalog. One explicit local request; never applies settings."""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "post-apollo-cpuplus-profiles-v1"
LIMIT = 16
MAX_BYTES = 16384
MAX_REV = 2**53 - 1
RESERVED = {"BALANCED", "DEVELOPMENT", "GAMING", "LOCAL AI", "STABILITY", "CUSTOM"}


def exact(value, fields):
    return isinstance(value, dict) and set(value) == set(fields)


def name(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,31}", value)
            or value != value.strip() or value.upper() in RESERVED):
        raise ValueError("profile name")
    return value


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def targets(value):
    if not exact(value, ("capacityGiB", "swappiness")):
        raise ValueError("target shape")
    cap, policy = value["capacityGiB"], value["swappiness"]
    if (cap is not None and (not integer(cap, 0, 64) or cap % 4)
            or policy is not None and not integer(policy, 0, 200)
            or cap is None and policy is None):
        raise ValueError("target values")
    return {"capacityGiB": cap, "swappiness": policy}


def initial():
    return {"schema": SCHEMA, "revision": 0, "profiles": []}


def validate(document):
    if (not exact(document, ("schema", "revision", "profiles")) or document["schema"] != SCHEMA
            or not integer(document["revision"], 0, MAX_REV)
            or not isinstance(document["profiles"], list) or len(document["profiles"]) > LIMIT):
        raise ValueError("catalog shape")
    seen = set()
    for row in document["profiles"]:
        if not exact(row, ("name", "targets")):
            raise ValueError("profile shape")
        key = name(row["name"]).upper()
        targets(row["targets"])
        if key in seen:
            raise ValueError("duplicate name")
        seen.add(key)
    return document


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def request_valid(request):
    if not isinstance(request, dict):
        raise ValueError("request")
    action = request.get("action")
    fields = {
        "list": ("action",),
        "create": ("action", "expectedRevision", "name", "targets"),
        "edit": ("action", "expectedRevision", "name", "targets"),
        "rename": ("action", "expectedRevision", "name", "newName"),
        "delete": ("action", "expectedRevision", "name"),
    }
    if not isinstance(action, str) or action not in fields or not exact(request, fields[action]):
        raise ValueError("request shape")
    if action != "list":
        if not integer(request["expectedRevision"], 0, MAX_REV):
            raise ValueError("revision")
        name(request["name"])
        if action in ("create", "edit"):
            targets(request["targets"])
        if action == "rename":
            name(request["newName"])
    return action


def mutate(document, request):
    action = request_valid(request)
    validate(document)
    if action == "list":
        return document
    if request["expectedRevision"] != document["revision"] or document["revision"] == MAX_REV:
        raise ValueError("stale revision")
    rows = list(document["profiles"])
    key = request["name"].upper()
    index = next((i for i, row in enumerate(rows) if row["name"].upper() == key), None)
    if action == "create":
        if index is not None or len(rows) >= LIMIT:
            raise ValueError("name collision or full")
        rows.append({"name": request["name"], "targets": targets(request["targets"])})
    else:
        if index is None or rows[index]["name"] != request["name"]:
            raise ValueError("exact profile name required")
        if action == "edit":
            rows[index] = {"name": rows[index]["name"], "targets": targets(request["targets"])}
        elif action == "rename":
            new = request["newName"]
            if any(i != index and row["name"].upper() == new.upper() for i, row in enumerate(rows)):
                raise ValueError("name collision")
            rows[index] = {"name": new, "targets": rows[index]["targets"]}
        elif action == "delete":
            del rows[index]
    return validate({"schema": SCHEMA, "revision": document["revision"]+1, "profiles": rows})


def private(fd, directory=False):
    info = os.fstat(fd)
    if (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        raise ValueError("unsafe profile storage")


def open_file(directory, leaf, flags):
    fd = os.open(leaf, flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                 0o600, dir_fd=directory)
    try:
        private(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def read(directory):
    try:
        fd = open_file(directory, "profiles.json", os.O_RDONLY)
    except FileNotFoundError:
        return initial()
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES:
        raise ValueError("catalog bound")
    return validate(parse(raw))


def encode(value):
    raw = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if len(raw) > MAX_BYTES:
        raise ValueError("catalog bound")
    return raw


def commit(directory, document):
    # All cooperating writers hold the same private lock. Refuse unsafe
    # staging objects; never follow a symlink or overwrite an invalid catalog.
    stage = ".pending"
    try:
        fd = open_file(directory, stage, os.O_RDONLY)
    except FileNotFoundError:
        pass
    else:
        os.close(fd)
        os.unlink(stage, dir_fd=directory)
    fd = open_file(directory, stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encode(document))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(stage, "profiles.json", src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(stage, dir_fd=directory)
        except FileNotFoundError:
            pass


def execute(folder, request):
    action = request_valid(request)
    folder = Path(folder)
    if action != "list":
        folder.parent.mkdir(parents=True, exist_ok=True)
        folder.mkdir(mode=0o700, exist_ok=True)
    try:
        directory = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        if action == "list":
            return initial()
        raise
    try:
        private(directory, directory=True)
        lock = open_file(directory, "profiles.lock", os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            document = read(directory)
            if action == "list":
                return document
            updated = mutate(document, request)
            commit(directory, updated)
            return updated
        finally:
            os.close(lock)
    finally:
        os.close(directory)


def state_folder():
    configured = os.environ.get("XDG_STATE_HOME")
    parent = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".local/state"
    return parent / "post-apollo-cpuplus-profiles"


def main():
    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.readline(MAX_BYTES+1)
        if len(raw) > MAX_BYTES or not raw.endswith(b"\n"):
            raise ValueError("request frame")
        result = execute(state_folder(), parse(raw))
        sys.stdout.buffer.write(encode(result)+b"\n")
        return 0
    except (OSError, ValueError, TypeError, RecursionError):
        # A lost response is not evidence of noncommit; caller must list again.
        print("Profile catalog unavailable or request refused; reload before retry.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
