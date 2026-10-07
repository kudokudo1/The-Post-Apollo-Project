#!/usr/bin/env python3
"""Focused contracts for the rich three-way conflict editor UI."""

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


EDITOR = "widgets/GitConflictEditorView.qml"
CHANGES = "widgets/GitChangesView.qml"
GITW = "widgets/GitW.qml"

require(
    EDITOR,
    "required property var conflictService",
    "three-way editor must use the guarded conflict backend",
)
for label in ("BASE", "OURS", "THEIRS", "RESULT"):
    require(
        EDITOR,
        f'label: "{label}"',
        f"three-way editor must expose {label}",
    )

for call in (
    "conflictService.takeOurs(",
    "conflictService.takeTheirs(",
    "conflictService.takeBoth(",
    "conflictService.takeBase(",
):
    require(
        EDITOR,
        call,
        "three-way editor must expose per-block resolution choices",
    )

require(
    EDITOR,
    "TextEdit {",
    "RESULT must be manually editable",
)
require(
    EDITOR,
    "conflictService.setResultText(text)",
    "manual RESULT editing must update backend state",
)
require(
    EDITOR,
    "conflictService.saveDraft()",
    "editor must expose non-staging draft saves",
)
require(
    EDITOR,
    "conflictService.stageResolved()",
    "editor must expose guarded resolved staging",
)
require(
    EDITOR,
    "CONFIRM STAGE",
    "staging must use an explicit confirmation step",
)
require(
    EDITOR,
    "UNRESOLVED",
    "editor must show unresolved block count",
)

require(
    CHANGES,
    "property var conflictEditorService: null",
    "CHANGES must accept the shared conflict editor service",
)
require(
    CHANGES,
    "const conflicts = root.changesService.conflicts || [];",
    "path handoff must inspect unresolved conflicts first",
)
require(
    CHANGES,
    'root.subMode = "conflicts";',
    "unmerged path handoff must open the CONFLICTS camera",
)
require(
    CHANGES,
    "root.selectFile(row);",
    "unmerged path handoff must select the matching conflict row",
)
require(
    CHANGES,
    'root.subMode === "conflicts"',
    "selected-file handling must distinguish the CONFLICTS camera",
)
require(
    CHANGES,
    "root.conflictEditorService.load(",
    "selecting a conflict must invoke the guarded three-way loader",
)
require(
    CHANGES,
    "root.selectedPath",
    "three-way loader must use the selected conflict path",
)
require_regex(
    CHANGES,
    r"GitConflictEditorView {.*"
    r"conflictService:\s*"
    r"root.conflictEditorService",
    "CONFLICTS must host the rich editor",
)

# Existing enclosing-operation controls must remain separate from file editing.
for needle in (
    "root.changesService.continueOperation()",
    "root.changesService.skipOperation()",
    "root.changesService.abortOperation(",
):
    require(
        CHANGES,
        needle,
        "merge/rebase/cherry-pick/revert controls must remain in CHANGES",
    )

require_regex(
    GITW,
    r"GitConflictEditorService {.*"
    r"id: conflictEditorService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must instantiate the conflict editor with shared evidence services",
)
require_regex(
    GITW,
    r"GitChangesView {.*"
    r"conflictEditorService: conflictEditorService",
    "GitW must pass the conflict editor into CHANGES",
)

print("Git rich three-way conflict editor UI contracts: PASS")
