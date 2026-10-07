#!/usr/bin/env python3
"""Focused contracts for the Git change-transfer surface."""

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


VIEW = "widgets/GitChangeTransferView.qml"
CHANGES = "widgets/GitChangesView.qml"

require(
    VIEW,
    "required property var transferService",
    "transfer panel must depend on the transfer backend",
)
require(
    VIEW,
    "required property var branchWorkspaceService",
    "transfer panel must consume real worktree topology",
)
require_regex(
    VIEW,
    r"readonly property var candidates:.*"
    r"branchWorkspaceService\.worktrees\.filter.*"
    r"path !== String\(root\.sourcePath",
    "destination list must exclude the source worktree",
)
require_regex(
    VIEW,
    r"readonly property bool destinationEligible:.*"
    r"!Boolean\(selectedWorktree\.detached\).*"
    r"Number\(selectedWorktree\.dirtyCount \|\| 0\) === 0",
    "UI must only treat clean named worktrees as eligible destinations",
)
require(
    VIEW,
    'label: "MOVE"',
    "transfer panel must expose MOVE mode",
)
require(
    VIEW,
    'label: "COPY"',
    "transfer panel must expose COPY mode",
)
require_regex(
    VIEW,
    r'label:\s*transferService\.previewBusy\s*'
    r'\? "PREVIEWING"\s*'
    r': "PREVIEW"',
    "transfer panel must require an explicit preview action",
)
require(
    VIEW,
    "transferService.preview(",
    "worktree PREVIEW must delegate to the guarded transfer backend",
)
require(
    VIEW,
    "transferService.previewStaged(",
    "staged whole-file preview must use the dedicated guarded backend path",
)
require(
    VIEW,
    "transferService.execute()",
    "execution must delegate to the guarded transfer backend",
)
require_regex(
    VIEW,
    r"readonly property string effectiveLayer:.*"
    r'untrackedSource.*\? "untracked".*'
    r'transferLayer.*\? "staged".*'
    r': "worktree"',
    "transfer view must resolve worktree/staged/untracked content layers",
)
require_regex(
    VIEW,
    r"readonly property bool previewMatchesSelection:.*"
    r"previewLayer.*effectiveLayer",
    "EXECUTE eligibility must match the exact previewed content layer",
)
require_regex(
    VIEW,
    r"readonly property bool previewMatchesSelection:.*"
    r"transferService\.hasPreview.*"
    r"previewDestinationPath.*selectedDestinationPath.*"
    r"previewMode.*transferMode.*"
    r"previewFiles\[0\].*filePath",
    "EXECUTE eligibility must match the exact previewed file/destination/mode",
)
require_regex(
    CHANGES,
    r"function worktreeFileTransferEligible\(\).*"
    r"Boolean\(row\.unstaged\).*"
    r"!Boolean\(row\.staged\).*"
    r"!Boolean\(row\.untracked\)",
    "worktree whole-file transfer must require unstaged-only tracked content",
)
require_regex(
    CHANGES,
    r"function stagedFileTransferEligible\(\).*"
    r"Boolean\(row\.staged\).*"
    r"!Boolean\(row\.unstaged\).*"
    r"!Boolean\(row\.untracked\)",
    "staged whole-file transfer must require staged-only tracked content",
)
require_regex(
    CHANGES,
    r"function untrackedFileTransferEligible\(\).*"
    r"Boolean\(row\.untracked\)",
    "untracked whole-file transfer must remain reachable",
)
require_regex(
    CHANGES,
    r"function fileTransferEligible\(\).*"
    r"worktreeFileTransferEligible\(\).*"
    r"stagedFileTransferEligible\(\).*"
    r"untrackedFileTransferEligible\(\)",
    "whole-file Transfer must admit each supported content layer",
)
require_regex(
    CHANGES,
    r"function hunkTransferEligible\(\).*"
    r"worktreeFileTransferEligible\(\)",
    "hunk Transfer must remain worktree-only",
)
require_regex(
    CHANGES,
    r"function lineTransferEligible\(\).*"
    r"worktreeFileTransferEligible\(\)",
    "line Transfer must remain worktree-only",
)
require(
    VIEW,
    "transferService.previewUntracked(",
    "untracked whole-file preview must use the dedicated guarded backend path",
)
require(
    CHANGES,
    'label: "TRANSFER"',
    "selected-file controls must expose transfer",
)
require_regex(
    CHANGES,
    r"GitChangeTransferView \{.*"
    r"transferService: root\.transferService.*"
    r"branchWorkspaceService: root\.branchWorkspaceService.*"
    r"filePath: root\.selectedPath.*"
    r"transferLayer: root\.transferLayer",
    "Changes overlay must use the shared backend, selected file, and content layer",
)
require_regex(
    CHANGES,
    r"root\.transferLayer\s*=\s*"
    r'requested !== "file".*'
    r'untrackedFileTransferEligible\(\).*'
    r'\? "untracked".*'
    r'stagedFileTransferEligible\(\).*'
    r'\? "staged".*'
    r': "worktree"',
    "opening Transfer must select worktree, staged, or untracked content explicitly",
)
require_regex(
    CHANGES,
    r"function onTransferFinished\(success, detail\).*"
    r"root\.changesService\.refresh\(\).*"
    r"root\.branchWorkspaceService\.refresh\(\)",
    "successful transfer must refresh both source changes and worktree state",
)
require_regex(
    "widgets/GitW.qml",
    r"GitChangesView \{.*"
    r"transferService: changeTransferService.*"
    r"branchWorkspaceService: branchWorkspaceService",
    "GitW must pass shared transfer/worktree services into Changes",
)

print("Git change transfer UI contracts: PASS")
