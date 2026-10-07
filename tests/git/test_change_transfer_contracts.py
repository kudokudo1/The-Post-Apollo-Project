#!/usr/bin/env python3
"""Focused contracts for safe Git change transfer."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


def require_regex(path: str, pattern: str, message: str) -> None:
    text = read(path)
    assert re.search(pattern, text, re.S), f"{message}: {path}"


SERVICE = "services/git/GitChangeTransferService.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "change transfer must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "change transfer must accept the shared snapshot service",
)
require(
    SERVICE,
    'DESTINATION BELONGS TO A DIFFERENT REPOSITORY',
    "transfer must stay within one repository",
)
require(
    SERVICE,
    'DESTINATION WORKTREE IS NOT CLEAN',
    "first transfer slice must require a clean destination",
)
require(
    SERVICE,
    'UNTRACKED OR UNKNOWN SOURCE PATH',
    "first transfer slice must refuse untracked source paths",
)
require(
    SERVICE,
    'SELECTED PATH HAS STAGED CHANGES',
    "first transfer slice must refuse staged selected paths",
)
require(
    SERVICE,
    'CONFLICTED SOURCE PATH',
    "transfer must refuse conflicted selected paths",
)
require(
    SERVICE,
    'SOURCE HAS AN ACTIVE GIT OPERATION',
    "transfer must refuse active source operations",
)
require(
    SERVICE,
    'DESTINATION HAS AN ACTIVE GIT OPERATION',
    "transfer must refuse active destination operations",
)
require(
    SERVICE,
    'git -C "$source" diff --binary --full-index --',
    "preview must build an exact binary-capable patch",
)
require(
    SERVICE,
    'git -C "$destination" apply --check --binary "$patch"',
    "preview must verify destination applicability",
)
require(
    SERVICE,
    'sha256sum "$patch"',
    "preview must fingerprint the exact transfer patch",
)
require(
    SERVICE,
    'SOURCE HEAD CHANGED SINCE PREVIEW',
    "execution must pin the source HEAD",
)
require(
    SERVICE,
    'DESTINATION HEAD CHANGED SINCE PREVIEW',
    "execution must pin the destination HEAD",
)
require(
    SERVICE,
    'SOURCE CHANGES DIFFER FROM PREVIEW',
    "execution must verify the source patch fingerprint again",
)
require_regex(
    SERVICE,
    r'git -C "\$destination" apply --binary "\$patch".*'
    r'git -C "\$source" apply -R --check --binary "\$patch".*'
    r'git -C "\$source" apply -R --binary "\$patch"',
    "MOVE must apply destination first and only then remove the source patch",
)
require(
    SERVICE,
    'DESTINATION ROLLED BACK',
    "failed source removal must roll destination back",
)
require(
    SERVICE,
    'DESTINATION ROLLBACK FAILED',
    "rollback failure must be explicit instead of hidden",
)
require_regex(
    SERVICE,
    r"function execute\(\).*"
    r'snapshotPhase = "BEFORE".*'
    r'snapshotService\.capture\(',
    "transfer execution must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"CHANGES/TRANSFER".*'
    r'root\.executeTransferProcess\(\)',
    "transfer mutation must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function maybeFinishTransfer\(\).*"
    r'snapshotPhase = "AFTER".*'
    r'snapshotService\.capture\(',
    "transfer must capture AFTER state before journal completion",
)
require(
    SERVICE,
    'out.recoveryClass = "EVIDENCE_ONLY"',
    "transfer must stay evidence-only until content recovery exists",
)
require_regex(
    "widgets/GitW.qml",
    r"GitChangeTransferService \{.*"
    r"id: changeTransferService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must own the shared change transfer backend",
)

print("Git change transfer contracts: PASS")
