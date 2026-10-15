#!/usr/bin/env python3
"""Static regression contract for GitHub Projects item removal.

Proves the confirmation path keeps failed deletions visible and reconciles
an accepted remote deletion before the follow-up project refresh. This is
not a live GitHub/Quickshell runtime test.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
service = (root / "services/github/GitHubProjectsService.qml").read_text(
    encoding="utf-8"
)

remove = service.split("    function removeItem(item, confirmed) {", 1)[1].split(
    "    function linkRepository(", 1
)[0]
finish = service.split("    function maybeFinish() {", 1)[1].split(
    "    Process {", 1
)[0]
timeout = service.split("    Timer {", 1)[1]

assert 'if (!confirmed)' in remove
assert 'if (!number || !id)' in remove
assert 'exec gh project item-delete "$1" --owner "$2" --id "$3" --format json' in remove
assert 'const started = startOperation(' in remove
assert 'if (started) {' in remove
assert 'pendingRemovedItemId = id;' in remove
assert 'pendingRemovedProjectNumber = number;' in remove

failure = finish.split("        if (exitCode !== 0) {", 1)[1].split(
    "        try {", 1
)[0]
success = finish.split('        if (finishedOperation === "remove-item") {', 2)[-1]
assert 'pendingRemovedItemId = "";' in failure
assert 'pendingRemovedProjectNumber = 0;' in failure
assert 'items = items.filter(function(item) {' not in failure
assert 'if (removedId && selectedNumber() === removedProject)' in success
assert 'items = items.filter(function(item) {' in success
assert 'return root.itemId(item) !== removedId;' in success
assert 'stateText = "REMOVE ACCEPTED // REFRESHING PROJECT";' in success
assert success.index('items = items.filter') < success.index(
    'mutationFinished(true, finishedOperation);'
)
assert 'root.refreshSelectedProject();' in success
assert 'root.pendingRemovedItemId = "";' in timeout
assert 'root.pendingRemovedProjectNumber = 0;' in timeout

print("GITHUB PROJECT REMOVE // ACKNOWLEDGED-LIST CONTRACT PASS")
