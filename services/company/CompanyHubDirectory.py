#!/usr/bin/env python3
"""Owner-local, non-personal Company hub *claims* directory.

These are operator-reported place/service labels, NEVER verified company
coverage, authenticated membership, employee data or client records.
No automatic imports, external API calls or permission grants.
"""
from __future__ import annotations

import fcntl
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any

SCHEMA = "post-apollo.company-hubs.local.v1"
MAX_HUBS = 150
MAX_BYTES = 131072
MAX_REQUEST_BYTES = 2048
ID_RE = re.compile(r"^hub-[1-9][0-9]{0,7}$")
CODE_RE = re.compile(r"^[A-Z]{2,3}$")
CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
FAMILIES = {"BENEFITS", "HEALTHCARE", "EDUCATION", "EMPLOYMENT",
            "REINTEGRATION", "HOUSING"}
COUNTRIES = {"US", "CAN", "MEX"}
FIELDS = {"create": {"label", "organizationLabel", "city",
                      "regionCode", "countryCode", "longitude",
                      "latitude", "serviceFamily"},
          "archive": {"hubId"}, "restore": {"hubId"}}


class HubError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def initial() -> dict:
    return {"schema": SCHEMA, "revision": 0, "nextId": 1, "hubs": []}


def directory() -> Path:
    home = os.environ.get("XDG_DATA_HOME", "")
    base = Path(home) if home else Path.home() / ".local" / "share"
    if not base.is_absolute() or ".." in base.parts:
        raise HubError("UNSAFE_ROOT")
    return base / "post-apollo" / "company"


def _secure_dir(path: Path, create: bool = False) -> bool:
    # Refuse pre-existing symlink paths and non-owner/other-readable leaf dirs.
    if not path.exists() and not path.is_symlink():
        if not create:
            return False
        parent = path.parent
        if not parent.exists() or parent.is_symlink():
            raise HubError("UNSAFE_DIRECTORY")
        path.mkdir(mode=0o700)
    try:
        st = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise HubError("UNSAFE_DIRECTORY")
    return True


def ensure_root(create: bool) -> bool:
    # Post-Apollo and Company are private, non-symlink directories.
    data = directory()
    for path in (data.parent, data):
        if not _secure_dir(path, create=create):
            return False
    return True


def _secure_file(path: Path) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise HubError("UNSAFE_FILE")
    return True


def _clean_text(value: Any, maximum: int = 90, optional: bool = False) -> str:
    if type(value) is not str or len(value) > maximum or CONTROLS.search(value):
        raise HubError("INVALID_FIELD")
    clean = value.strip()
    if not clean and not optional:
        raise HubError("INVALID_FIELD")
    return clean


def _coordinates(lon: Any, lat: Any) -> tuple[float, float]:
    if type(lon) not in (int, float) or type(lat) not in (int, float):
        raise HubError("INVALID_COORDINATES")
    if not math.isfinite(lon) or not math.isfinite(lat):
        raise HubError("INVALID_COORDINATES")
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise HubError("INVALID_COORDINATES")
    return round(float(lon), 6), round(float(lat), 6)


def _hub(value: Any) -> dict:
    expected = {"id", "label", "organizationLabel", "city", "regionCode",
                "countryCode", "longitude", "latitude", "serviceFamily",
                "reported", "archived"}
    if type(value) is not dict or set(value) != expected:
        raise HubError("INVALID_DOCUMENT")
    if type(value["id"]) is not str or not ID_RE.fullmatch(value["id"]):
        raise HubError("INVALID_DOCUMENT")
    if value["reported"] is not True or type(value["archived"]) is not bool:
        raise HubError("INVALID_DOCUMENT")
    country = value["countryCode"]
    region = value["regionCode"]
    family = value["serviceFamily"]
    if country not in COUNTRIES or type(country) is not str:
        raise HubError("INVALID_DOCUMENT")
    if type(region) is not str or not CODE_RE.fullmatch(region):
        raise HubError("INVALID_DOCUMENT")
    if family not in FAMILIES or type(family) is not str:
        raise HubError("INVALID_DOCUMENT")
    lon, lat = _coordinates(value["longitude"], value["latitude"])
    return {**value,
            "label": _clean_text(value["label"], 90),
            "organizationLabel": _clean_text(value["organizationLabel"], 90),
            "city": _clean_text(value["city"], 80),
            "longitude": lon, "latitude": lat}


def validate(doc: Any) -> dict:
    if type(doc) is not dict or set(doc) != {"schema", "revision", "nextId", "hubs"}:
        raise HubError("INVALID_DOCUMENT")
    if doc["schema"] != SCHEMA:
        raise HubError("UNSUPPORTED_VERSION")
    revision, next_id, hubs = doc["revision"], doc["nextId"], doc["hubs"]
    if (type(revision) is not int or not 0 <= revision < 1000000000
            or type(next_id) is not int or not 1 <= next_id < 1000000000
            or type(hubs) is not list or len(hubs) > MAX_HUBS):
        raise HubError("INVALID_DOCUMENT")
    seen: set[str] = set()
    output: list[dict] = []
    maximum = 0
    for item in hubs:
        hub = _hub(item)
        if hub["id"] in seen:
            raise HubError("DUPLICATE_ID")
        seen.add(hub["id"])
        maximum = max(maximum, int(hub["id"].split("-")[1]))
        output.append(hub)
    if maximum >= next_id:
        raise HubError("INVALID_DOCUMENT")
    return {"schema": SCHEMA, "revision": revision, "nextId": next_id,
            "hubs": output}


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for name, value in pairs:
        if name in result:
            raise HubError("INVALID_JSON")
        result[name] = value
    return result


def decode(payload: bytes) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise HubError("INVALID_JSON") from None


def load() -> dict:
    if not ensure_root(create=False):
        return initial()
    path = directory() / "hubs-v1.json"
    if not _secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise HubError("UNSAFE_FILE")
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HubError("FILE_TOO_LARGE")
    return validate(decode(data))


def apply(doc: Any, request: Any) -> dict:
    current = validate(doc)
    if type(request) is not dict:
        raise HubError("INVALID_REQUEST")
    action = request.get("action")
    if action not in FIELDS or set(request) != {"action", "expectedRevision", *FIELDS[action]}:
        raise HubError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != current["revision"]):
        raise HubError("REVISION_CONFLICT")
    if action == "create":
        if len(current["hubs"]) >= MAX_HUBS:
            raise HubError("HUB_CAPACITY")
        record = {name: request[name] for name in FIELDS["create"]}
        record.update({"id": f"hub-{current['nextId']}", "reported": True,
                       "archived": False})
        current["hubs"].append(_hub(record))
        current["nextId"] += 1
    else:
        hub_id = request["hubId"]
        if type(hub_id) is not str or not ID_RE.fullmatch(hub_id):
            raise HubError("INVALID_ID")
        hub = next((h for h in current["hubs"] if h["id"] == hub_id), None)
        if hub is None:
            raise HubError("NOT_FOUND")
        next_value = action == "archive"
        if hub["archived"] == next_value:
            raise HubError("NO_CHANGE")
        hub["archived"] = next_value
    current["revision"] += 1
    return validate(current)


def save(doc: dict) -> None:
    data = (json.dumps(validate(doc), separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    if len(data) > MAX_BYTES:
        raise HubError("FILE_TOO_LARGE")
    ensure_root(create=True)
    path = directory() / "hubs-v1.json"
    _secure_file(path)
    fd, tmp = tempfile.mkstemp(prefix=".hubs-v1-", dir=directory())
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        rootfd = os.open(directory(), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(rootfd)
        finally:
            os.close(rootfd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp):
            os.unlink(tmp)


def run(operation: str) -> dict:
    if operation == "read":
        return {"ok": True, "document": load()}
    if operation != "update":
        raise HubError("INVALID_REQUEST")
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
        raise HubError("INVALID_REQUEST")
    request = decode(raw)
    ensure_root(create=True)
    lock_path = directory() / ".hubs-v1.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise HubError("UNSAFE_FILE")
        fcntl.flock(fd, fcntl.LOCK_EX)
        new_doc = apply(load(), request)
        save(new_doc)
        return {"ok": True, "document": new_doc}
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def main() -> int:
    try:
        result = run(sys.argv[1] if len(sys.argv) == 2 else "")
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except HubError as exc:
        print(json.dumps({"ok": False, "error": exc.code}))
        return 2
    except (OSError, TypeError):
        print(json.dumps({"ok": False, "error": "IO_UNAVAILABLE"}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
