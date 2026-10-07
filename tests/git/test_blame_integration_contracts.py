#!/usr/bin/env python3
"""Contracts for Blame/provenance integration into GitW + History."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITW = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
HISTORY = (ROOT / "widgets/GitHistoryView.qml").read_text(encoding="utf-8")
BLAME = (ROOT / "widgets/GitBlameView.qml").read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


# History owns only a neutral provenance request; the provenance implementation
# remains outside History surgery.
require(
    HISTORY,
    "signal blameRequested(string path, string revision)",
    "History provenance signal",
)
require(HISTORY, 'label: "BLAME"', "commit inspector Blame action")
require(
    HISTORY,
    "root.historyService.selectedFile",
    "Blame action requires selected file",
)
require(
    HISTORY,
    "root.historyService.selectedSha",
    "Blame action pins historical revision",
)

# GitW hosts the standalone organ and overlays it over History.
for needle, label in (
    ("property bool blameOpen: false", "Blame overlay state"),
    ("GitBlameService {", "Blame service host"),
    ("GitBlameView {", "Blame presentation host"),
    ("blameService: blameService", "Blame dependency injection"),
    ("function openBlameForPath(path, revision, line)", "provenance navigator"),
    ("function closeBlame()", "provenance close path"),
    ("function openCommitFromBlame(sha)", "Blame to commit inspector"),
    ("function openHistoryFromBlame(sha, path, line)", "Blame to History"),
    ("onBlameRequested: function(path, revision)", "History to Blame wiring"),
    ("function onCommitRequested(sha)", "service commit handoff"),
    ("function onHistoryRequested(sha, path, line)", "service History handoff"),
):
    require(GITW, needle, label)

# Source provenance navigates back through the canonical History inspector and
# existing file-diff service rather than inventing another commit viewer.
require(
    GITW,
    'root.gitView = "history"',
    "provenance handoff must return to History",
)
require(
    GITW,
    'gitHistoryView.inspectorMode = "detail"',
    "COMMIT opens commit detail",
)
require(
    GITW,
    'gitHistoryView.inspectorMode = "file"',
    "HIST opens file inspector",
)
require(
    GITW,
    'gitHistoryView.selectCommit(commit, "")',
    "History uses canonical commit selection",
)
require(
    GITW,
    "historyService.showFileDiff(commit, target)",
    "History uses canonical file-diff reader",
)

# The standalone view must retain its source-line -> History/commit controls.
for needle, label in (
    ('label: "HIST"', "row History action"),
    ('label: "COMMIT"', "row commit action"),
    ('label: "OPEN HISTORY"', "detail History action"),
    ('label: "OPEN COMMIT"', "detail commit action"),
):
    require(BLAME, needle, label)

# Blame integration must not depend on Doc 3's rewrite/recovery organs.
for forbidden in (
    "GitHistoryFoldService",
    "GitHistorySplitService",
    "GitHistoryAbsorbService",
    "GitInteractiveRebaseService",
    "GitOperationRecoveryService",
    "GitChangeTransferService",
    "GitLineTransferService",
):
    if forbidden in BLAME:
        errors.append(
            f"Blame view crossed local-history surgery boundary: {forbidden}"
        )

if errors:
    print("POST-APOLLO BLAME INTEGRATION CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO BLAME INTEGRATION CONTRACTS // PASS")
print("checked History inspector -> Blame -> commit/file History navigation")
