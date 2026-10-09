#!/usr/bin/env python3
"""End-to-end structural acceptance contracts for the Hospital control surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RECEPTION = (
    ROOT / "services/hospital/HospitalReceptionistService.qml"
).read_text(encoding="utf-8")
HOST = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
ATTENTION = (
    ROOT / "widgets/HospitalGitHubAttentionView.qml"
).read_text(encoding="utf-8")
QUEUE = (
    ROOT / "widgets/HospitalGitHubMergeQueueView.qml"
).read_text(encoding="utf-8")
RESPONSIBILITY = (
    ROOT / "services/hospital/HospitalResponsibilityService.qml"
).read_text(encoding="utf-8")
INTERPRETATION = (
    ROOT / "services/hospital/HospitalInterpretationService.qml"
).read_text(encoding="utf-8")
CHAT = (
    ROOT / "widgets/HospitalRoomChatView.qml"
).read_text(encoding="utf-8")
ADAPTER = (
    ROOT / "services/hospital/HospitalRoomConversationAdapter.qml"
).read_text(encoding="utf-8")

errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


# Reception is the front door for both Hospital-wide operations and GitHub triage.
for needle, label in (
    ("Attention, Merge Queue", "Reception capability advertisement"),
    ('target === "attention"', "Reception Attention route"),
    ('target === "merge_queue"', "Reception Merge Queue route"),
    ('request("attention", raw)', "Reception Attention parser"),
    ('request("merge_queue", raw)', "Reception Merge Queue parser"),
):
    require(RECEPTION, needle, label)

# The host turns those deterministic Reception routes into concrete surfaces.
for needle, label in (
    ('if (target === "attention")', "Attention host dispatch"),
    ("root.openAttention();", "Attention host route"),
    ('if (target === "merge_queue")', "Merge Queue host dispatch"),
    ("githubService.repoSlug", "current patient repository source"),
    ('root.openAttentionQueue(repo, "");', "direct Merge Queue route"),
    ("function openAttention()", "Attention surface opener"),
    ("function openAttentionQueue(repository, branch)", "Merge Queue opener"),
    ("function closeAttentionQueue()", "Merge Queue return path"),
):
    require(HOST, needle, label)

# Triage hands into the queue and both surfaces share durable ownership evidence.
for needle, label in (
    ("signal queueRequested(string repository, string branch)", "Triage queue handoff"),
    ("responsibilityService.contextForWorkItem(item)", "Triage ownership lookup"),
):
    require(ATTENTION, needle, label)

for needle, label in (
    ("property var responsibilityService: null", "Queue responsibility dependency"),
    ("responsibilityService.contextForWorkItem({", "Queue ownership lookup"),
):
    require(QUEUE, needle, label)

for needle, label in (
    ("function contextForWorkItem(itemValue)", "responsibility work-item context"),
    ("function responsibilityChain(contextValue)", "responsibility chain"),
    ("context.evidence = {", "responsibility evidence"),
):
    require(RESPONSIBILITY, needle, label)

for needle, label in (
    ("onQueueRequested: function(repository, branch)", "Triage host handoff"),
    ("root.openAttentionQueue(", "Triage to queue navigation"),
    ("onCloseRequested: root.closeAttentionQueue()", "Queue to triage navigation"),
):
    require(HOST, needle, label)

# Doctor chat remains live/actionable while the final acceptance surface is composed.
for needle, label in (
    ("adapter.sending && adapter.liveStreamText", "live Doctor stream"),
    ("richMessageActions: true", "rich Doctor chat"),
):
    require(CHAT, needle, label)

for needle, label in (
    ('eventType !== "provider.stream"', "stream event consumption"),
    ("id: liveStreamTimer", "stream polling"),
):
    require(ADAPTER, needle, label)

# Hospital AI is advisory only: it may suggest, but deterministic action still
# requires explicit operator acceptance.
for needle, label in (
    ('lastStatus =\n            "AI // REVIEW REQUIRED";', "AI review gate"),
    ("function acceptSuggestion()", "explicit AI acceptance"),
    ("suggestionAccepted(suggestion);", "accepted suggestion signal"),
    ("function dismissSuggestion()", "AI dismissal path"),
):
    require(INTERPRETATION, needle, label)

if errors:
    print("POST-APOLLO HOSPITAL ACCEPTANCE // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO HOSPITAL ACCEPTANCE // PASS")
print("Reception -> Attention/Triage -> Merge Queue -> responsibility/evidence")
print("Doctor live chat remains actionable; AI remains suggest + human accept")
