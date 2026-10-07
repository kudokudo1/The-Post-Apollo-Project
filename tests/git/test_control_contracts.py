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
