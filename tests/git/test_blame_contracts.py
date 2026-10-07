#!/usr/bin/env python3
"""Focused static contracts for the standalone Git blame/provenance service."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = ROOT / "services/git/GitBlameService.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


def require_regex(text: str, pattern: str, label: str) -> None:
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        errors.append(f"{label}: did not match {pattern!r}")


if not SERVICE_PATH.exists():
    errors.append("missing services/git/GitBlameService.qml")
    service = ""
else:
    service = SERVICE_PATH.read_text(encoding="utf-8")

require(
    service,
    'cmd=(git -C "$repo" blame --line-porcelain --root)',
    "blame must use porcelain output with root commit identities",
)
require(
    service,
    'cmd+=(--follow)',
    "blame must support rename following",
)
require(
    service,
    'cmd+=("$range")',
    "blame must support explicit line ranges",
)
require(
    service,
    'cmd+=(-- "$path")',
    "blame path must be passed after --",
)
require(
    service,
    'property string revision: "WORKTREE"',
    "worktree provenance must be the default",
)
require(
    service,
    "function isUncommittedSha(sha)",
    "worktree-only lines must be classified explicitly",
)
require(
    service,
    "signal commitRequested(string sha)",
    "service must expose a neutral commit handoff",
)
require(
    service,
    "signal historyRequested(string sha, string path, int line)",
    "service must expose a neutral History handoff",
)
require(
    service,
    "function requestHistoryForRow(index)",
    "rows must be able to request History without importing GitW",
)

for field in (
    "originalLine",
    "finalLine",
    "author",
    "authorMail",
    "authorTime",
    "authorTimezone",
    "summary",
    "sourcePath",
    "previousSha",
    "previousPath",
):
    require(
        service,
        field,
        f"provenance row must retain {field}",
    )

require_regex(
    service,
    r"previous\.sha\s*===\s*row\.sha"
    r".*previous\.sourcePath\s*===\s*row\.sourcePath"
    r".*previous\.endLine\s*\+\s*1\s*===\s*row\.finalLine"
    r".*previous\.originalEndLine\s*\+\s*1\s*===\s*row\.originalLine",
    "ownership groups must be contiguous in both final and source locations",
)
require(
    service,
    "function rowsForRange(startLine, endLine)",
    "loaded provenance must support line/range filtering",
)
require(
    service,
    "function groupsForRange(startLine, endLine)",
    "loaded provenance groups must support line/range filtering",
)

# This service is intentionally read-only. It may inspect revisions, but it
# must not grow a generic mutation seam while Doc 3 owns repository mutation
# history/recovery.
for forbidden in (
    "runAction(",
    "GitOperationJournalService",
    "GitBranchWorkspaceService",
    "git reset ",
    "git checkout ",
    "git switch ",
    "git commit ",
    "git rebase ",
    "git merge ",
    "git cherry-pick ",
):
    if forbidden in service:
        errors.append(
            f"read-only provenance boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO GIT BLAME CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GIT BLAME CONTRACTS // PASS")
print("checked standalone provenance service")
