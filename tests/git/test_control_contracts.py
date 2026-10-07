#!/usr/bin/env python3
"""Static regression contracts for the Post-Apollo Git/GitHub control plane.

These tests intentionally validate architectural safety seams that can regress
without requiring a running Quickshell session or live GitHub mutations.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
errors = []


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        errors.append(f"missing file: {path}")
        return ""
    return target.read_text(encoding="utf-8")


def require(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle not in text:
        errors.append(f"{label}: {path} missing {needle!r}")


def forbid(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle in text:
        errors.append(f"{label}: {path} unexpectedly contains {needle!r}")


def require_regex(path: str, pattern: str, label: str) -> None:
    text = read(path)
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        errors.append(f"{label}: {path} did not match {pattern!r}")


def no_conflict_markers(path: str) -> None:
    text = read(path)
    marker_patterns = (
        ("<<<<<<<", r"^<<<<<<<(?: .*)?\\r?$"),
        ("=======", r"^=======\\r?$"),
        (">>>>>>>", r"^>>>>>>>(?: .*)?\\r?$"),
    )
    for marker, pattern in marker_patterns:
        if re.search(pattern, text, re.MULTILINE):
            errors.append(f"merge conflict marker {marker!r} in {path}")


# GitHub operation ownership: the generic control service delegates mutations
# to PX rather than embedding raw gh mutation syntax.
require(
    "services/github/GitHubService.qml",
    'px" delete-workflow "$1" "$2"',
    "workflow deletion must route through PX",
)
require(
    "services/github/GitHubService.qml",
    "function runWorkflowBatch(workflowPaths, ref)",
    "workflow batches must carry an explicit optional ref",
)
forbid(
    "services/github/GitHubService.qml",
    "gh api",
    "GitHubService must not own raw GitHub API mutations",
)

# Installed PX identity is a first-class diagnostic because the desktop invokes
# ~/.local/bin/px rather than the source checkout directly.
require(
    "services/github/GitHubService.qml",
    'installed="$HOME/.local/bin/px"',
    "installed PX path must be diagnosed",
)
require(
    "services/github/GitHubService.qml",
    'source="$runtime/bin/px"',
    "runtime PX source must be diagnosed",
)
require(
    "services/github/GitHubService.qml",
    "pxRuntimeState",
    "PX runtime state must remain observable",
)

# Saved workflow procedures are repository-bound and preserve dispatch ref.
require(
    "services/github/WorkflowLibraryStore.qml",
    "property string queueRepository",
    "workflow queue must be repository-bound",
)
require(
    "services/github/WorkflowLibraryStore.qml",
    "property string queueRef",
    "workflow queue must preserve target ref",
)
require(
    "services/github/WorkflowLibraryStore.qml",
    "confirmedOverwrite",
    "saved workflow overwrite must require confirmation",
)
require(
    "services/github/WorkflowLibraryStore.qml",
    "function deleteSet(setRecord, confirmed)",
    "saved workflow deletion must require confirmation",
)

# PR checks/reviews must have concrete evidence fallbacks, not only nullable
# GraphQL rollup fields.
require(
    "services/github/GitHubWorkItemsService.qml",
    'commits/$sha/check-runs?per_page=100',
    "PR check runs must query exact head SHA",
)
require(
    "services/github/GitHubWorkItemsService.qml",
    'commits/$sha/status',
    "PR status contexts must query exact head SHA",
)
require(
    "services/github/GitHubWorkItemsService.qml",
    'pulls/$number/reviews?per_page=100',
    "PR reviews need direct evidence fallback",
)
require(
    "services/github/GitHubWorkItemsService.qml",
    'pulls/$number/requested_reviewers',
    "PR review requests need direct evidence fallback",
)

# Work-item inbox keyboard continuity includes the search editor and keeps
# dynamic row actions reachable while the ListView scrolls.
require_regex(
    "widgets/GitHubWorkItemsView.qml",
    r"component SearchField: Rectangle \{.*registerGitKeyboardControl\(field\).*onTriggered:\s*editor\.forceActiveFocus\(\)",
    "work-item search must participate in shared keyboard routing",
)
require(
    "widgets/GitHubWorkItemsView.qml",
    "sourceList.positionViewAtIndex(",
    "work-item keyboard selection must keep its row visible",
)
require(
    "widgets/GitHubWorkItemsView.qml",
    "cacheBuffer: Math.max(height, 416)",
    "work-item list must keep nearby row controls instantiated for keyboard navigation",
)
require(
    "widgets/GitHubWorkItemsView.qml",
    "keyboardListIndex: sourceRow.index",
    "work-item row actions must identify their ListView row",
)

# Project item destructive actions are guarded at the backend, not only UI.
require(
    "services/github/GitHubProjectsService.qml",
    "function archiveItem(item, confirmed)",
    "project archive must require explicit confirmation",
)
require(
    "services/github/GitHubProjectsService.qml",
    "function removeItem(item, confirmed)",
    "project removal must require explicit confirmation",
)
require(
    "services/github/GitHubProjectsService.qml",
    "function canonicalItemUrl(url)",
    "project membership must use canonical URLs",
)

# BranchMap graph connectors depend on runtime topology accessors. These
# functions are called from Canvas JavaScript and can look unused to static
# cleanup passes even though removing them makes every branch rail disappear.
require(
    "services/git/GitService.qml",
    "function commitAt(index)",
    "branch map must retain topology row access",
)
require(
    "services/git/GitService.qml",
    "function indexOfSha(sha)",
    "branch map must retain parent SHA lookup",
)
require(
    "components/BranchMap.qml",
    "branchMap.topologyService.commitAt(i)",
    "branch map Canvas must read topology rows",
)
require(
    "components/BranchMap.qml",
    "branchMap.topologyService.indexOfSha(parentList[p])",
    "branch map Canvas must resolve parent connectors",
)

# Universal operation journal foundation. Journal records must exist before
# mutations, survive restarts, and remain truthful that Undo is not implemented
# until a recovery engine lands.
require(
    "services/git/GitOperationJournalService.qml",
    "function beginOperation(kind, beforeState, metadata)",
    "operation journal must record mutation start",
)
require(
    "services/git/GitOperationJournalService.qml",
    "function completeOperation(operationId, afterState, detail)",
    "operation journal must record successful after-state",
)
require(
    "services/git/GitOperationJournalService.qml",
    "function failOperation(operationId, afterState, detail)",
    "operation journal must retain failed operations",
)
require(
    "services/git/GitOperationJournalService.qml",
    'status === "RUNNING"\n                    ? "INTERRUPTED"',
    "unfinished operations must become interrupted after restart",
)
require(
    "services/git/GitOperationJournalService.qml",
    'undoState: "NOT_IMPLEMENTED"',
    "journal must not claim Undo before recovery exists",
)
require(
    "services/git/GitOperationJournalService.qml",
    "atomicWrites: true",
    "operation journal persistence must be atomic",
)
# Live repository snapshots now gate journaled mutations. The snapshot must
# capture actual Git state before the operation process can start.
require(
    "services/git/GitRepositorySnapshotService.qml",
    "function capture(label, context)",
    "repository snapshots must expose an asynchronous capture seam",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    'git -C "$repo" for-each-ref',
    "repository snapshots must capture refs",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    'git -C "$repo" write-tree',
    "repository snapshots must capture index tree state",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    'git -C "$repo" status --porcelain=v1 --untracked-files=all',
    "repository snapshots must capture dirty worktree evidence",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    'git -C "$repo" reflog -1',
    "repository snapshots must retain a reflog recovery pointer",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    'git -C "$repo" worktree list --porcelain',
    "repository snapshots must capture worktree topology",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    '"REF_RECOVERABLE"',
    "clean snapshots must classify ref-based recovery",
)
require(
    "services/git/GitRepositorySnapshotService.qml",
    '"EVIDENCE_ONLY"',
    "dirty or active-operation snapshots must stay evidence-only",
)
require_regex(
    "services/git/GitBranchWorkspaceService.qml",
    r"function runAction\(operation, a, b, c\).*snapshotPhase = \"BEFORE\";.*snapshotService\.capture\(",
    "branch/workspace mutations must request BEFORE snapshot before execution",
)
require_regex(
    "services/git/GitBranchWorkspaceService.qml",
    r"if \(root\.snapshotPhase === \"BEFORE\"\).*operationJournal\.beginOperation\(.*root\.executePendingAction\(\)",
    "branch/workspace mutation may execute only after BEFORE snapshot opens journal record",
)
require_regex(
    "services/git/GitBranchWorkspaceService.qml",
    r"function maybeFinishAction\(\).*snapshotPhase = \"AFTER\";.*snapshotService\.capture\(",
    "branch/workspace mutations must capture AFTER state before journal completion",
)
require(
    "services/git/GitBranchWorkspaceService.qml",
    "operationJournal.completeOperation(",
    "branch/workspace success must close the journal record",
)
require(
    "services/git/GitBranchWorkspaceService.qml",
    "operationJournal.failOperation(",
    "branch/workspace failure must close the journal record",
)
require_regex(
    "widgets/GitW.qml",
    r"GitRepositorySnapshotService \{.*id: repositorySnapshotService.*GitOperationJournalService \{.*id: operationJournalService.*GitBranchWorkspaceService \{.*operationJournal: operationJournalService.*snapshotService: repositorySnapshotService",
    "GitW must inject shared snapshot + journal services into branch/workspace mutations",
)
require(
    "services/git/GitOperationJournalService.qml",
    "recoveryClass:",
    "journal entries must persist recovery classification",
)
require(
    ".gitignore",
    "git-operation-journal.json",
    "local journal state must not dirty the Quickshell repository",
)

# Guarded operation recovery starts narrow: only exact clean ref
# transitions with explicit inverse strategies may execute.
require(
    "services/git/GitOperationRecoveryService.qml",
    "function preview(record)",
    "operation recovery must expose a non-mutating preview",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'strategy: "DELETE_CREATED_BRANCH"',
    "branch creation must have an explicit inverse strategy",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'strategy: "RENAME_BRANCH_BACK"',
    "branch rename must have an explicit inverse strategy",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'recoveryClass !== "REF_RECOVERABLE"',
    "recovery must refuse evidence-only operations",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'WORKTREE DIRTY // UNDO WILL NOT DISCARD CONTENT',
    "recovery must refuse dirty worktrees",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'git -C "$repo" update-ref -d "$ref" "$expected"',
    "created-branch Undo must use expected-SHA guarded deletion",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'BRANCH MOVED SINCE RECORDED OPERATION',
    "recovery must refuse stale branch state",
)
require(
    "services/git/GitOperationRecoveryService.qml",
    'UNDO STRATEGY NOT IMPLEMENTED FOR ',
    "unsupported operations must be refused rather than approximated",
)
require_regex(
    "widgets/GitW.qml",
    r"GitOperationRecoveryService \{.*id: operationRecoveryService.*repositoryPath:",
    "GitW must own the shared recovery backend",
)

# Repository safety contracts.
require(
    "services/git/GitRepositoryService.qml",
    "LINE CHANGED // REFRESH BEFORE REMOVING",
    "project-file removal must verify exact selected text",
)
require(
    "services/git/GitRepositoryService.qml",
    "LINE CHANGED // REFRESH BEFORE REPLACING",
    "project-file replacement must verify exact selected text",
)
require(
    "services/git/GitRepositoryService.qml",
    "fsck --full --no-progress",
    "health diagnostics must perform full fsck",
)
require(
    "services/git/GitHistoryService.qml",
    "reflogRecoveryCount",
    "reflog recovery candidates must remain classified",
)

# Hospital evidence uses the local checkout and GitHub evidence as independent
# facts, then explicitly diagnoses their identity seam.
require(
    "services/github/GitEvidenceProvider.qml",
    "function repositorySlugFromOrigin(originValue)",
    "evidence must normalize local Git origin",
)
require(
    "services/github/GitEvidenceProvider.qml",
    "repositoryMatchesLocalOrigin",
    "evidence must expose local/GitHub repository identity",
)
require_regex(
    "services/github/GitEvidenceProvider.qml",
    r"repositoryMatchesLocalOrigin\s*=\s*githubRepository\s*&&\s*checkoutRepository\s*\?\s*githubRepository\s*===\s*checkoutRepository\s*:\s*null",
    "unknown local origin must remain distinct from explicit mismatch",
)
require(
    "services/hospital/HospitalCertificationCoordinator.qml",
    "diagnostics.repositoryMatchesLocalOrigin === false",
    "Hospital must reject explicit evidence repository mismatch",
)
require(
    "services/hospital/HospitalCertificationCoordinator.qml",
    "LOCAL GIT ORIGIN DOES NOT MATCH GITHUB EVIDENCE REPOSITORY",
    "Hospital mismatch refusal must stay explicit",
)

# Recent loader regression: Scope requires the base Quickshell import.
require(
    "services/hospital/HospitalInterpretationService.qml",
    "import Quickshell\n",
    "Hospital interpretation Scope needs base Quickshell import",
)

focused_files = [
    "services/github/GitHubService.qml",
    "services/github/GitHubWorkItemsService.qml",
    "services/github/GitHubProjectsService.qml",
    "services/github/GitEvidenceProvider.qml",
    "services/github/WorkflowLibraryStore.qml",
    "services/git/GitOperationJournalService.qml",
    "services/git/GitOperationRecoveryService.qml",
    "services/git/GitRepositorySnapshotService.qml",
    "services/git/GitRepositoryService.qml",
    "services/git/GitHistoryService.qml",
    "services/hospital/HospitalCertificationCoordinator.qml",
    "services/hospital/HospitalInterpretationService.qml",
    "widgets/GitHubProjectsView.qml",
    "widgets/GitHubProjectsRoadmapView.qml",
    "widgets/GitHubProjectsTableView.qml",
    "widgets/GitHubWorkItemsView.qml",
    "widgets/WorkflowLibraryView.qml",
]

for file_path in focused_files:
    no_conflict_markers(file_path)

if errors:
    print("POST-APOLLO GIT CONTROL CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GIT CONTROL CONTRACTS // PASS")
print(f"checked {len(focused_files)} focused files")
