#!/usr/bin/env python3
"""PR Control: real-action progress, state gates, usable editor geometry.

Source contracts must not be conflated with Qt visual acceptance or live GitHub
mutation tests. This suite runs without credentials or any network writes.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
source = (root / "widgets/GitHubPullRequestControlView.qml").read_text(encoding="utf-8")
service = (root / "services/github/GitHubPullRequestLifecycleService.qml").read_text(encoding="utf-8")

# The clicked button owns progress, not whichever shared service is busy.
assert 'property string activeLifecycleAction: ""' in source
assert 'property string completedLifecycleAction: ""' in source
assert "property bool completedLifecycleSuccess: false" in source
assert "function startLifecycleAction(token, callback)" in source
assert "activeLifecycleAction = token;" in source
assert "const accepted = callback();" in source
assert "if (!accepted)" in source
assert "root.completedLifecycleSuccess =" in source
assert "mutationSucceeded && evidenceVerified" in source
assert "root.completedLifecycleAction = root.activeLifecycleAction;" in source
assert 'root.activeLifecycleAction = "";' in source

# This follows GitW's Save Workflow loading contract: approach 90% while
# waiting, never show 100% until the backend also verifies the result.
for needle in (
    'property: "loadingProgress"',
    "to: 0.9",
    "duration: 3600",
    "to: 1.0",
    "duration: 260",
    "id: progressFill",
    "color: button.accent",
    "button.loading || button.loadingComplete",
    "(parent.width - 2) * button.loadingProgress",
    "&& root.completedLifecycleSuccess",
    "(enabledAction || loading || loadingComplete) ? 1.0 : 0.36",
):
    assert needle in source, needle

required_tokens = [
    "draft-toggle", "update-branch", "update-rebase", "close-reopen",
    "title", "base", "body", "label-add", "label-remove", "assignee",
    "reviewer", "milestone", "milestone-clear", "comment",
    "review-approve", "review-comment", "review-changes",
]
for token in required_tokens:
    assert f'actionToken: "{token}"' in source, token
    assert f'root.startLifecycleAction("{token}", function()' in source, token
assert 'actionToken: "merge-" + modelData' in source
assert 'root.startLifecycleAction("merge-" + modelData, function()' in source
assert "return root.startLifecycleAction(" not in source
assert re.search(r'label:\s+actionToken:', source) is None
assert re.search(r'onTriggered:\s*root\.lifecycleService\.', source) is None

# Only the active PR lifecycle reports this fill: unrelated queue or thread
# activity must not make unrelated PR buttons appear to have been clicked.
assert '&& root.activeLifecycleAction === actionToken' in source
assert '&& root.lifecycleService.busy' not in source.split(
    'readonly property bool loading:', 1)[1].split('signal triggered()', 1)[0]

# Users can escape an apparently stuck detail view. Actual PR states, not
# optimistic labels, own the dangerous action availability.
assert 'label: "← PULLS"' in source
assert 'enabledAction: true' in source.split('label: "← PULLS"', 1)[1].split(
    'onTriggered:', 1
)[0]
assert 'readonly property bool isOpen:' in source
assert 'readonly property bool isClosed:' in source
assert 'readonly property bool isMerged:' in source
assert "&& (root.isOpen || root.isClosed)" in source
assert "&& root.isOpen" in source
assert "&& !root.pullRequestDraft" in source
assert 'label:\n                            root.isMerged\n                            ? "MERGED"' in source
assert 'root.armOrRun(\n                            "update-branch"' in source
assert 'root.armOrRun(\n                                "close"' in source
assert '"merge-" + modelData' in source

# Surface the raw GitHub failure text in a real scrollable display, rather
# than a single ellipsized line or a success-colored notification.
assert 'GITHUB ERROR // " + root.lifecycleService.lastError' in source
assert "root.lifecycleService.phase" in source
assert "AWAITING VERIFIED RESULT" in source
assert "height: detail ? 94 : 38" in source
assert "contentHeight: Math.max(height, statusText.implicitHeight + 4)" in source
assert "wrapMode: Text.WrapAnywhere" in source
assert "detail: !!root.lifecycleService.lastError" in source
assert "root.lifecycleService.lastError ? Colors.red" in source
assert 'PR CLOSED // REOPEN TO REVIEW' in source
assert 'PR MERGED // READ-ONLY LIFECYCLE' in source

# Reserve 20px for the main star; don't let six fixed-width metadata buttons
# occupy the same row as a now-zero-width shared entry field.
assert "width: Math.max(0, syntagmaPane2.width - 20)" in source
assert 'id: syntagmaPane2' in source
assert 'flickable: syntagmaPane2' in source
assert "width: Math.max(0, parent.width - 103)" in source
meta = source.split('id: metaInput', 1)[1].split('text: "REVIEW / COMMENT"', 1)[0]
assert meta.count("height: 31") >= 1  # explicit second row
assert 'label: "+ LABEL"' in meta
for label in ('"- LABEL"', '"+ ASSIGNEE"', '"+ REVIEWER"', '"MILESTONE"', '"CLEAR"'):
    assert f"label: {label}" in meta
assert "width: Math.max(0, parent.width - 20)" in source  # inline body editor too

# Meta Apollo text input defaults remain explicit even in tiny PR fields.
assert source.count("color: Colors.magenta") >= 2
assert source.count("cursorDelegate: Rectangle { width: 2; color: Colors.orange }") >= 2

# The real service still waits for read-back evidence, not a guessed timer.
for needle in (
    "function reopenPullRequest(",
    "function maybeFinishMutation()",
    "function maybeFinishEvidence()",
    "signal mutationFinished(",
    'lastError =',
    'watchdog.restart()',
):
    assert needle in service, needle

print("PR CONTROL // ACTION FILL, ERROR DISPLAY, STATE & LAYOUT PASS")
