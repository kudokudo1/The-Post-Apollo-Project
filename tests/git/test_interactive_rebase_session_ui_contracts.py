#!/usr/bin/env python3
"""Focused contracts for persistent rebase session UI."""

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


SESSION_VIEW = "widgets/GitInteractiveRebaseSessionView.qml"
REBASE_VIEW = "widgets/GitInteractiveRebaseView.qml"
GITW = "widgets/GitW.qml"

require(
    SESSION_VIEW,
    "required property var sessionService",
    "live session surface must use the persistent session backend",
)
require(
    SESSION_VIEW,
    "LIVE REBASE // PERSISTENT SESSION",
    "session surface must clearly identify durable live rebase state",
)
require(
    SESSION_VIEW,
    "LIVE REBASE // EXTERNAL SESSION",
    "foreign Git rebase state must be presented distinctly",
)
require(
    SESSION_VIEW,
    "sessionService.continueSession()",
    "live session must expose continue",
)
require(
    SESSION_VIEW,
    "sessionService.skipSession()",
    "live session must expose skip",
)
require(
    SESSION_VIEW,
    "sessionService.abortSession(true)",
    "confirmed abort must call the persistent session backend",
)
require(
    SESSION_VIEW,
    'label:\n                            root.abortArmed\n                            ? "CONFIRM ABORT REBASE"\n                            : "ARM ABORT"',
    "abort must use a two-step arm/confirm interaction",
)
require(
    SESSION_VIEW,
    "sessionService.conflictFiles",
    "live session must present conflicted paths",
)
require(
    SESSION_VIEW,
    "openChangesRequested(",
    "live session must hand edit/conflict work to CHANGES",
)
require(
    SESSION_VIEW,
    "EDIT PAUSE // MODIFY OR AMEND THE STOPPED COMMIT",
    "edit pauses must explain the expected workflow",
)
require(
    SESSION_VIEW,
    "CONFLICT // RESOLVE IN CHANGES",
    "conflict pauses must explain the expected workflow",
)
require_regex(
    REBASE_VIEW,
    r"GitInteractiveRebaseSessionView \{.*"
    r"visible: root\.sessionVisible.*"
    r"sessionService: root\.rebaseSessionService",
    "persistent session state must overlay the planner while active",
)
require(
    REBASE_VIEW,
    'signal openChangesRequested(string path)',
    "REBASE surface must provide neutral CHANGES handoff",
)
require_regex(
    GITW,
    r"function openChangesForPath\(path\).*"
    r"root\.pushGitNavigationContext\(\).*"
    r'root\.gitView = "changes";.*'
    r"if \(target\).*gitChangesView\.focusPath\(target\);",
    "generic rebase edit handoff must preserve navigation even without a specific path",
)

print("Git persistent rebase session UI contracts: PASS")
