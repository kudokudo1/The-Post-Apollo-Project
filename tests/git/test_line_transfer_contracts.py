#!/usr/bin/env python3
"""Focused contracts for guarded worktree-line transfer."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitLineTransferService.qml"


def read() -> str:
    return (ROOT / SERVICE).read_text(encoding="utf-8")


def require(needle: str, message: str) -> None:
    text = read()
    assert needle in text, f"{message}: missing {needle!r}"


def require_regex(pattern: str, message: str) -> None:
    assert re.search(pattern, read(), re.S), message


require(
    "property var operationJournal: null",
    "line transfer must accept the shared operation journal",
)
require(
    "property var snapshotService: null",
    "line transfer must accept the shared snapshot service",
)
require(
    "function preview(destination, path, hunk, line, mode)",
    "line transfer must expose an explicit preview",
)
require(
    'operation: "TRANSFER_LINE"',
    "line transfer evidence must identify its operation",
)
require(
    '"CHANGES/TRANSFER_LINE"',
    "line transfer must have its own journal kind",
)
require(
    'SELECTED PATH HAS STAGED CHANGES',
    "line transfer must refuse staged overlap",
)
require(
    'UNTRACKED OR UNKNOWN SOURCE PATH',
    "line transfer must refuse untracked paths",
)
require(
    'CONFLICTED SOURCE PATH',
    "line transfer must refuse conflicted paths",
)
require(
    'SOURCE HAS AN ACTIVE GIT OPERATION',
    "line transfer must refuse active source operations",
)
require(
    'DESTINATION HAS AN ACTIVE GIT OPERATION',
    "line transfer must refuse active destination operations",
)
require(
    'DESTINATION WORKTREE IS NOT CLEAN',
    "line transfer must require a clean destination",
)
require(
    'if not selected or selected[0] not in "+-"',
    "only actual +/- diff lines may transfer",
)
require(
    'git(source, "show", ":" + path)',
    "line transfer must reconstruct the line patch from index state",
)
require(
    'difflib.unified_diff(base, target',
    "line transfer must create a minimal unified patch",
)
require(
    'hashlib.sha256(patch).hexdigest()',
    "preview must fingerprint the exact line patch",
)
require(
    'SOURCE HEAD CHANGED SINCE PREVIEW',
    "execution must pin source HEAD",
)
require(
    'DESTINATION HEAD CHANGED SINCE PREVIEW',
    "execution must pin destination HEAD",
)
require(
    'SOURCE LINE CHANGED SINCE PREVIEW',
    "execution must regenerate and verify the selected line patch",
)
require(
    'LINE DOES NOT APPLY CLEANLY TO DESTINATION',
    "preview must prove destination applicability",
)
require(
    'SOURCE LINE CANNOT BE REMOVED CLEANLY',
    "MOVE preview must prove source removal applicability",
)
require_regex(
    r'apply = run\(\["git", "-C", destination, "apply".*'
    r'remove = run\(\["git", "-C", source, "apply", "-R".*'
    r'rollback = run\(\["git", "-C", destination, "apply", "-R"',
    "MOVE must apply destination first and roll it back on source-removal failure",
)
require(
    'DESTINATION ROLLBACK FAILED',
    "rollback failure must be explicit",
)
require_regex(
    r"function execute\(\).*"
    r'snapshotPhase = "BEFORE".*'
    r'snapshotService\.capture\(',
    "line execution must capture BEFORE state",
)
require_regex(
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"CHANGES/TRANSFER_LINE".*'
    r'root\.startProcess\(',
    "line mutation must wait for snapshot + journal start",
)
require_regex(
    r"function finishProcess\(\).*"
    r'snapshotPhase = "AFTER".*'
    r'snapshotService\.capture\(',
    "line execution must capture AFTER state",
)
require(
    'out.recoveryClass = "EVIDENCE_ONLY"',
    "line transfer must remain evidence-only until content recovery exists",
)

print("Git line transfer contracts: PASS")
