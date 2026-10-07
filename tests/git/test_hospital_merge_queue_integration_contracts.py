#!/usr/bin/env python3
"""Contracts for Hospital Merge Queue interpretation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOSPITAL = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
ATTENTION = (
    ROOT / "widgets/HospitalGitHubAttentionView.qml"
).read_text(encoding="utf-8")
QUEUE = (
    ROOT / "widgets/HospitalGitHubMergeQueueView.qml"
).read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ('property string attentionSubview: "triage"', "Attention subview state"),
    ("GitHubMergeQueueProvider {", "Hospital Merge Queue provider"),
    ("function openAttentionQueue(repository, branch)", "queue drilldown"),
    ("function closeAttentionQueue()", "queue return path"),
    ('root.attentionSubview === "queue"', "queue visibility state"),
    ("HospitalGitHubMergeQueueView {", "queue presentation"),
    ("interval: 300000", "queue/attention refresh cadence"),
):
    require(HOSPITAL, needle, label)

require(
    ATTENTION,
    "signal queueRequested(string repository, string branch)",
    "Attention must expose queue drilldown",
)
require(ATTENTION, 'label: "QUEUE"', "Attention rows need queue action")
require(
    ATTENTION,
    "root.queueRequested(",
    "Attention queue action must carry repo/base branch",
)

for needle, label in (
    ("queueProvider.entries", "queue ordering"),
    ("modelData.position", "queue position"),
    ("modelData.stateLabel", "native queue state"),
    ("mergeStateStatus", "merge blocker explanation"),
    ("reviewDecision", "review blocker explanation"),
    ("modelData.enqueuer", "who enqueued the item"),
    ("estimatedTimeToMerge", "queue ETA"),
    ("configuration || {}).mergeMethod", "merge method interpretation"),
    ("configuration || {}).mergingStrategy", "merge strategy interpretation"),
    ('label: "OPEN PULLS"', "queue-to-PULLS navigation"),
    ('label: "← ATTENTION"', "queue return navigation"),
):
    require(QUEUE, needle, label)

for forbidden in (
    "GitInteractiveRebase",
    "GitOperationRecoveryService",
    "GitChangeTransferService",
    "GitLineTransferService",
):
    if forbidden in QUEUE or forbidden in ATTENTION:
        errors.append(
            f"Hospital Merge Queue crossed Doc 3 exclusion zone: {forbidden}"
        )

if errors:
    print("POST-APOLLO HOSPITAL MERGE QUEUE INTEGRATION // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO HOSPITAL MERGE QUEUE INTEGRATION // PASS")
print("checked Attention drilldown -> queue order/readiness/blocker interpretation")
