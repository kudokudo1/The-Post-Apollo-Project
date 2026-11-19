#!/usr/bin/env python3
"""Trash++ ALL Burn: reviewed system GIO Trash plus trashed managed copies.

This is a two-backend, non-atomic operation. It NEVER deletes original sources,
active managed copies, V2 read-only snapshots or Hospital Room records.
Every backend still independently checks its own reviewed revision/digest.
No background execution: a separate explicit UI confirmation is required.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GIO = HERE / "trash_cli.py"
COPIES = HERE / "research_records.py"
CONFIRM = "BURN_ALL_FILES_AND_COPIES_CONFIRMED"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_RESPONSE = 2_097_152


class Refused(Exception):
    pass


def _integer(raw: str) -> int:
    if not isinstance(raw, str) or not re.fullmatch(r"(0|[1-9][0-9]{0,9})", raw):
        raise Refused("INVALID_COUNT_OR_REVISION")
    return int(raw)


def _run(script: Path, args: list[str], timeout: int) -> dict:
    try:
        p = subprocess.run([sys.executable, "-I", "-B", str(script), *args],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("BACKEND_EXECUTION_UNCERTAIN") from exc
    if len(p.stdout.encode("utf-8")) > MAX_RESPONSE:
        raise Refused("BACKEND_RESPONSE_TOO_LARGE")
    try:
        data = json.loads(p.stdout)
    except (TypeError, ValueError) as exc:
        raise Refused("BACKEND_RESPONSE_UNCERTAIN") from exc
    if not isinstance(data, dict) or data.get("ok") is not True or p.returncode:
        raise Refused("BACKEND_REFUSED_" + str(data.get("error", "UNKNOWN"))[:100])
    return data


def _preflight(data_dir: str, file_revision: str, file_count: int,
               copy_revision: int, copy_count: int, copy_digest: str) -> None:
    # Both inventories must match BEFORE either independently guarded writer
    # starts. This cannot make two independent backends atomic.
    gio = _run(GIO, ["index"], 25)
    if (gio.get("kind") != "index" or gio.get("complete") is not True
            or gio.get("revision") != file_revision
            or gio.get("total") != file_count):
        raise Refused("STALE_SYSTEM_TRASH_REFRESH_REQUIRED")
    copies = _run(COPIES, ["list", data_dir], 25)
    if (copies.get("kind") != "managed-research"
            or copies.get("revision") != copy_revision
            or copies.get("binCount") != copy_count
            or copies.get("binDigest") != copy_digest
            or not isinstance(copies.get("items"), list)
            or len([x for x in copies["items"]
                    if isinstance(x, dict) and x.get("state") == "trashed"])
            != copy_count):
        raise Refused("STALE_MANAGED_COPIES_REFRESH_REQUIRED")


def _receipt(name: str, raw: dict, expected: int) -> tuple[list, bool]:
    items = raw.get("burnedItems")
    if (not isinstance(items, list) or len(items) > expected
            or raw.get("burnedCount") != len(items)
            or not all(isinstance(item, dict)
                       and isinstance(item.get("name"), str)
                       and isinstance(item.get("kind"), str)
                       for item in items)):
        raise Refused("INVALID_" + name + "_BURN_RECEIPT")
    if name == "SYSTEM":
        if raw.get("kind") != "burn-all" or raw.get("count") != expected:
            raise Refused("INVALID_SYSTEM_BURN_RECEIPT")
        verified = (raw.get("verified") is True and raw.get("partial") is False
                    and raw.get("remainingCount") == 0
                    and len(items) == expected)
    else:
        if raw.get("kind") != "managed-research":
            raise Refused("INVALID_MANAGED_BURN_RECEIPT")
        verified = raw.get("verified") is True and len(items) == expected
    return items, verified


def combined(data_dir: str, file_revision: str, file_count: int,
             copy_revision: int, copy_count: int, copy_digest: str,
             confirmation: str) -> dict:
    if confirmation != CONFIRM:
        raise Refused("COMBINED_BURN_CONFIRMATION_REQUIRED")
    if (not isinstance(data_dir, str) or not data_dir.startswith("/")
            or "\x00" in data_dir or len(data_dir) > 8192
            or not isinstance(file_revision, str)
            or HEX64.fullmatch(file_revision) is None
            or not isinstance(copy_digest, str)
            or HEX64.fullmatch(copy_digest) is None
            or type(file_count) is not int or type(copy_count) is not int
            or type(copy_revision) is not int
            or not 0 <= file_count <= 2500
            or not 0 <= copy_count <= 2500
            or not 0 <= copy_revision <= 2_147_483_647
            or file_count + copy_count < 1):
        raise Refused("INVALID_COMBINED_BURN_SCOPE")
    _preflight(data_dir, file_revision, file_count,
               copy_revision, copy_count, copy_digest)

    burned: list[dict] = []
    verified = True
    problem = ""
    stage = "NONE"
    # Managed copies go first. If they fail, never start GIO emptying.
    # A failure after the first successful store is explicitly partial.
    try:
        if copy_count:
            stage = "MANAGED"
            result = _run(COPIES, [
                "burn-all", data_dir, str(copy_revision), str(copy_count),
                copy_digest, "BURN_ALL_MANAGED_COPIES_CONFIRMED"
            ], 30)
            items, ok = _receipt("MANAGED", result, copy_count)
            burned.extend(items)
            verified = verified and ok
            if not ok:
                raise Refused("MANAGED_BURN_NOT_FULLY_VERIFIED")
        if file_count:
            stage = "SYSTEM"
            result = _run(GIO, [
                "burn-all", file_revision, str(file_count), "BURN_ALL_CONFIRMED"
            ], 100)
            items, ok = _receipt("SYSTEM", result, file_count)
            burned.extend(items)
            verified = verified and ok
            if not ok:
                raise Refused("SYSTEM_BURN_NOT_FULLY_VERIFIED")
    except Refused as exc:
        problem = str(exc)[:120]
        verified = False

    requested = file_count + copy_count
    # Never claim success from a requested count; only backend receipts count.
    verified = verified and len(burned) == requested and not problem
    return {
        "ok": True, "kind": "combined-burn-all",
        "count": requested, "burnedCount": len(burned),
        "burnedItems": burned, "verified": verified,
        "partial": not verified,
        "message": ("COMBINED_BURN_VERIFIED" if verified
                    else "COMBINED_BURN_PARTIAL_OR_UNVERIFIED"),
        "failureStage": stage if problem else "",
        "error": problem,
        "systemRequested": file_count,
        "managedRequested": copy_count,
    }


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 9 or argv[1] != "burn-all":
            raise Refused("INVALID_ACTION")
        result = combined(argv[2], argv[3], _integer(argv[4]),
                          _integer(argv[5]), _integer(argv[6]),
                          argv[7], argv[8])
    except Refused as exc:
        result = {"ok": False, "error": str(exc)[:140]}
    except Exception:
        result = {"ok": False, "error": "COMBINED_BURN_UNEXPECTED_FAILURE"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
