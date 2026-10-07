#!/usr/bin/env python3
"""Focused contracts for guarded hunk-level change transfer."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitChangeTransferService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(needle: str, message: str) -> None:
    text = read(SERVICE)
    assert needle in text, f"{message}: missing {needle!r}"


def require_regex(pattern: str, message: str) -> None:
    text = read(SERVICE)
    assert re.search(pattern, text, re.S), message


require(
    "function previewHunk(destinationPath, path, hunkIndex, mode)",
    "transfer backend must expose hunk preview",
)
require(
    'pendingPreviewScope = "hunk"',
    "hunk preview must mark its exact scope",
)
require(
    'pendingPreviewHunkIndex = index',
    "hunk preview must preserve the selected hunk index",
)
require(
    '"CHANGES/TRANSFER_HUNK"',
    "hunk transfer must receive its own journal kind",
)
require(
    'git -C "$source" diff --cached --quiet -- "$path"',
    "hunk transfer must refuse staged overlap",
)
require(
    'HUNK DOES NOT APPLY CLEANLY TO DESTINATION',
    "hunk preview must prove destination applicability",
)
require(
    'patch = "".join(header + hunks[idx])',
    "hunk patch must be the file header plus exactly one indexed hunk",
)
require(
    'sha256sum "$patch"',
    "hunk preview must fingerprint the exact patch",
)
require(
    'SOURCE HEAD CHANGED SINCE PREVIEW',
    "hunk execution must retain source HEAD pinning",
)
require(
    'DESTINATION HEAD CHANGED SINCE PREVIEW',
    "hunk execution must retain destination HEAD pinning",
)
require(
    'if [ "$scope" = "hunk" ]; then',
    "execution must regenerate hunk patches by scope",
)
require(
    'HUNK PATCH REGENERATION FAILED',
    "execution must fail closed when the indexed hunk disappears",
)
require(
    'SOURCE CHANGES DIFFER FROM PREVIEW',
    "execution must reject a regenerated hunk whose fingerprint changed",
)
require_regex(
    r'git -C "\$destination" apply --binary "\$patch".*'
    r'git -C "\$source" apply -R --check --binary "\$patch".*'
    r'git -C "\$source" apply -R --binary "\$patch"',
    "hunk MOVE must preserve destination-first apply and rollback-safe source removal",
)
require(
    'out.recoveryClass = "EVIDENCE_ONLY"',
    "hunk transfer must remain evidence-only until content recovery exists",
)

print("Git hunk transfer contracts: PASS")
