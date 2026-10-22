#!/usr/bin/env python3
"""Focused contracts for journaled Git CONTROL sync actions."""

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


SERVICE = "services/git/GitService.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "Git control service must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "Git control service must accept the shared snapshot service",
)

journal_helper = re.search(
    r"function shouldJournalProcessAction\(processAction\) \{(.*?)\n    \}",
    read(SERVICE),
    re.S,
)
assert journal_helper, "journal-action classifier must exist"
helper_body = journal_helper.group(1)

for operation in ("fetch", "pull", "push", "track-checkout", "clone"):
    assert f'"{operation}"' in helper_body, (
        f"{operation} must be classified as a journaled CONTROL mutation"
    )

for operation in ("status", "diff", "log"):
    assert f'"{operation}"' not in helper_body, (
        f"{operation} must stay outside the CONTROL mutation journal"
    )

require_regex(
    SERVICE,
    r'if \(processAction === "clone"\).*'
    r'operationJournal\.beginOperation\(\s*'
    r'"CONTROL/CLONE".*'
    r'cloneBoundaryBeforeSnapshot\(\).*'
    r'startPendingActionProcess\(\)',
    "clone must use a dedicated external-boundary journal start instead of a repository BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(pendingProcessAction === "clone"\).*'
    r'finalizeControlAction\(\s*'
    r'cloneBoundaryAfterSnapshot\(\)',
    "clone must close its journal with synthetic external after-state evidence",
)

require_regex(
    SERVICE,
    r"function journalSnapshot\(snapshot\).*"
    r'pendingProcessAction === "push".*'
    r'out\.recoveryClass = "EVIDENCE_ONLY".*'
    r"CONTROL PUSH MUTATES REMOTE REF STATE",
    "push must not claim recovery from local-only snapshots",
)
require_regex(
    SERVICE,
    r"function runAction\(kind\).*"
    r'snapshotPhase = "BEFORE";.*'
    r'snapshotService\.capture\(',
    "journaled CONTROL actions must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(gitService\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"CONTROL/".*'
    r'gitService\.startPendingActionProcess\(\)',
    "CONTROL mutation execution must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function finishActionProcess\(\).*"
    r'snapshotPhase = "AFTER";.*'
    r'snapshotService\.capture\(',
    "CONTROL mutations must capture AFTER state before journal completion",
)
require(
    SERVICE,
    "operationJournal.completeOperation(",
    "successful CONTROL mutations must close their journal record",
)
require(
    SERVICE,
    "operationJournal.failOperation(",
    "failed or uncertain CONTROL mutations must close their journal record",
)
require_regex(
    SERVICE,
    r'if \(raw === "__PA_DONE__"\) \{\s*'
    r'finishActionProcess\(\);',
    "process completion marker must enter the journal-aware completion seam",
)
require(
    SERVICE,
    "CONTROL ACTION TIMEOUT // STATE UNCERTAIN",
    "CONTROL timeout must be journaled as uncertain state",
)
require_regex(
    "widgets/GitW.qml",
    r"GitService \{.*"
    r"id: gitService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must inject shared journal + snapshots into Git control",
)

# Checked-out PULL already fetches. The explicit fetch belongs only to
# the background-local-branch route, and each selected PULL prunes its remote.
pull_section = re.search(r"'  pull\)',(.*?)'  push\)'", read(SERVICE), re.S)
assert pull_section, "PULL branch must be present"
pull_source = pull_section.group(1)
assert pull_source.count('git -C "$repo" fetch --prune "$remote"') == 1, (
    "background-only prefetch must not run before checked-out git pull"
)
assert 'git -C "$repo" pull --ff-only --prune' in pull_source
assert 'git -C "$repo" pull --no-rebase --prune' in pull_source
assert 'BACKGROUND MERGE REFUSED' in pull_source
assert 'git -C "$repo" merge-base --is-ancestor' in pull_source

# Trace stays opt-in and may not bypass the BEFORE/AFTER journal boundaries.
for marker in (
    'POST_APOLLO_GIT_SYNC_TRACE',
    'BEFORE_SNAPSHOT_COMPLETE',
    'GIT_PROCESS_COMPLETE',
    'AFTER_SNAPSHOT_COMPLETE',
):
    require(SERVICE, marker, "Git sync stage timing must remain measurable")

print("Git CONTROL sync journal contracts: PASS")
