#!/usr/bin/env python3
"""Focused contracts for the interactive rebase HISTORY surface."""

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


VIEW = "widgets/GitInteractiveRebaseView.qml"
HISTORY = "widgets/GitHistoryView.qml"
GITW = "widgets/GitW.qml"

require(
    VIEW,
    "required property var rebaseService",
    "rebase UI must use the standalone rebase engine",
)
for action in ("pick", "reword", "squash", "fixup", "drop"):
    require(
        VIEW,
        f'"{action}"',
        f"rebase UI must expose {action}",
    )

require(
    VIEW,
    "function moveSelected(delta)",
    "rebase UI must expose commit reordering",
)
require(
    VIEW,
    "rebaseService.moveEntry(selectedIndex, target)",
    "reordering must delegate to the guarded engine plan",
)
require(
    VIEW,
    "rebaseService.setAction(selectedIndex, next)",
    "action changes must delegate to the engine",
)
require(
    VIEW,
    "rebaseService.setMessage(",
    "reword text must be stored in the engine plan",
)
require(
    VIEW,
    "rebaseService.preview(baseInput.text.trim())",
    "BUILD PLAN must use engine preview",
)
require(
    VIEW,
    "rebaseService.arm()",
    "rebase UI must expose explicit ARM",
)
require(
    VIEW,
    "rebaseService.executeArmed()",
    "rebase UI execution must use the armed engine path",
)
require_regex(
    VIEW,
    r"enabledAction:\s*"
    r"rebaseService\.armed.*"
    r"!rebaseService\.previewBusy.*"
    r"!rebaseService\.executionBusy",
    "EXECUTE must require an armed, idle plan",
)
require(
    VIEW,
    "EDIT / PAUSE / LIVE CONFLICT SESSION",
    "unsupported persistent rewrite-session features must be visible as unavailable",
)
require(
    VIEW,
    "REHEARSAL FIRST // LIVE BRANCH MOVES ONLY",
    "UI must communicate rehearsal-before-live-mutation semantics",
)

require_regex(
    HISTORY,
    r'key: "rebase".*'
    r'label: "REBASE".*'
    r'color: Colors\.magenta',
    "REBASE must be a first-class HISTORY submode",
)
require_regex(
    HISTORY,
    r"GitInteractiveRebaseView \{.*"
    r'visible: root\.subMode === "rebase".*'
    r"rebaseService: root\.interactiveRebaseService",
    "HISTORY must host the rebase planner in the REBASE submode",
)
require(
    HISTORY,
    "property var interactiveRebaseService: null",
    "HISTORY must accept the shared rebase service",
)

require_regex(
    GITW,
    r"GitInteractiveRebaseService \{.*"
    r"id: interactiveRebaseService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must instantiate rebase with the shared journal and snapshots",
)
require_regex(
    GITW,
    r"GitHistoryView \{.*"
    r"interactiveRebaseService: interactiveRebaseService",
    "GitW must pass the shared rebase engine into HISTORY",
)

print("Git interactive rebase UI contracts: PASS")
