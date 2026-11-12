#!/usr/bin/env python3
"""Trash++ U1: read-only inventory of possible delete-action UI call sites.

This is a triage aid, not a permissions map or a repository-wide authority.
No code execution, imports of discovered source, source-file writes, GIO calls,
Trash, Restore, Burn, path-based delete, or production integration.
"""
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "post-apollo.trash-delete-inventory.u1"
SCAN_DIRS = ("modules", "widgets", "components", "services")
SUFFIXES = frozenset((".qml", ".js", ".mjs", ".py"))
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PER_FILE = 40
MAX_CANDIDATES = 1500

# These deliberately over-include ambiguous action names. Every hit requires
# source-owner review and classification before it can be migrated.
LABEL = re.compile(
    r"\b(?:text|label|title)\s*:\s*[\"']?"
    r"(?:DELETE|REMOVE|TRASH|BURN|CLEAR|PURGE|EMPTY|ERASE)\b", re.I)
HANDLER = re.compile(
    r"\bon(?:Clicked|Triggered|Accepted)\b.*"
    r"(?:delete|remove|trash|burn|purge|erase|clear)", re.I)
METHOD = re.compile(
    r"\b(?:function|def)\s+[A-Za-z_][A-Za-z0-9_]*"
    r"(?:Delete|Remove|Trash|Burn|Purge|Erase|Clear|delete|remove|trash|burn|purge|erase|clear)"
    r"[A-Za-z0-9_]*\s*\(", re.I)
PATTERNS = (("label", LABEL), ("handler", HANDLER), ("method", METHOD))


def _scan_file(path, root):
    """Return bounded code *locations*, never file text or private payloads."""
    try:
        mode = path.lstat()
        if not stat.S_ISREG(mode.st_mode) or mode.st_size > MAX_SOURCE_BYTES:
            return (), True
        raw = path.read_bytes()
        if len(raw) > MAX_SOURCE_BYTES:
            return (), True
        contents = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return (), True
    hits = []
    relative = path.relative_to(root).as_posix()
    for line_number, line in enumerate(contents.splitlines(), start=1):
        if line.lstrip().startswith(("//", "#", "*")):
            continue
        for kind, pattern in PATTERNS:
            if pattern.search(line):
                hits.append({
                    "path": relative, "line": line_number, "matchType": kind,
                    "state": "OWNER_REVIEW_REQUIRED",
                    "trashAllowed": False, "burnAllowed": False,
                })
                break
        if len(hits) == MAX_PER_FILE:
            return tuple(hits), True
    return tuple(hits), False


def inventory(root):
    """Scan fixed source families with no symlink traversal and no writes."""
    root = Path(root)
    findings = []
    incomplete = []
    family_counts = {name: 0 for name in SCAN_DIRS}
    for family in SCAN_DIRS:
        directory = root / family
        if directory.is_symlink():
            incomplete.append(family + "/")
            continue
        if not directory.is_dir():
            incomplete.append(family + "/")
            continue
        for folder, subdirs, files in os.walk(directory, followlinks=False):
            subdirs[:] = sorted(
                d for d in subdirs if not (Path(folder) / d).is_symlink()
            )
            for filename in sorted(files):
                file_path = Path(folder) / filename
                if file_path.suffix not in SUFFIXES:
                    continue
                hits, truncated = _scan_file(file_path, root)
                if truncated:
                    incomplete.append(file_path.relative_to(root).as_posix())
                for hit in hits:
                    if len(findings) < MAX_CANDIDATES:
                        findings.append(hit)
                        family_counts[family] += 1
                    else:
                        incomplete.append("GLOBAL_CANDIDATE_LIMIT")
                        break
    return {
        "schema": SCHEMA,
        "readOnly": True,
        "actionAuthority": False,
        "sourceOwnerApproval": False,
        "state": "INCOMPLETE_REVIEW_REQUIRED"
                 if incomplete else "OWNER_REVIEW_REQUIRED",
        "totals": {"candidateLocations": len(findings),
                   "byFamily": family_counts},
        "incompletePaths": sorted(set(incomplete)),
        "candidates": findings,
    }


def main(argv):
    # The CLI scans its own repository, never a caller-selected filesystem.
    if len(argv) != 1:
        print(json.dumps({"ok": False, "error": "NO_ARGUMENTS_ALLOWED"}))
        return 2
    root = Path(__file__).resolve().parents[2]
    result = inventory(root)
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
