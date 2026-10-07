#!/usr/bin/env python3
"""Contracts for Hospital responsibility mapping."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (
    ROOT / "services/hospital/HospitalResponsibilityService.qml"
).read_text(encoding="utf-8")
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
    ("property var roundsService: null", "Rounds evidence"),
    ("property var registryService: null", "Specialist evidence"),
    ("property var assignmentService: null", "Assignment evidence"),
    ("property var durableRooms: []", "durable Room evidence"),
    ("property var durableSessions: []", "persistent session evidence"),
    ("function refreshDurableGraph()", "durable graph refresh"),
    ('"hospital", "rooms"', "PX durable Room query"),
    ('"hospital", "sessions"', "PX persistent session query"),
    ("function roomScore(roomValue, repositoryValue, branchValue)", "room scorer"),
    ("function bestRoom(repositoryValue, branchValue)", "room resolver"),
    ("function specialistsForRoom(roomValue)", "specialist resolver"),
    ("function durableRoomFor(roomValue, repositoryValue, branchValue)", "durable Room resolver"),
    ("function activeSessionForRoom(roomIdValue)", "persistent session resolver"),
    ("function activeAssignmentForRoom(roomValue)", "active assignment"),
    ("function contextFor(repositoryValue, branchValue)", "responsibility context"),
    ("function blockerForWorkItem(itemValue)", "blocker resolver"),
    ("function responsibilityChain(contextValue)", "responsibility chain"),
    ("function contextForWorkItem(itemValue)", "work-item graph context"),
    ("bedPath:", "Bed identity"),
    ("doctorId:", "Doctor identity"),
    ("sessionId:", "session identity"),
    ("assignmentId:", "Assignment identity"),
    ("context.evidence = {", "evidence edge"),
    ('return "EXACT";', "exact confidence"),
    ('return "UNMAPPED";', "unmapped confidence"),
):
    require(SERVICE, needle, label)

for needle, label in (
    ("HospitalResponsibilityService {", "Hospital responsibility host"),
    ("roundsService: roundsService", "Rounds injection"),
    ("registryService: specialistRegistryService", "Specialist injection"),
    ("assignmentService: assignmentService", "Assignment injection"),
    ("responsibilityService: responsibilityService", "Attention injection"),
    ("responsibilityService.refreshDurableGraph();", "live responsibility refresh"),
):
    require(HOSPITAL, needle, label)

for needle, label in (
    ("property var responsibilityService: null", "Attention ownership dependency"),
    ("responsibilityService.contextForWorkItem(item)", "Attention work-item ownership lookup"),
    ('"OWNER // "', "Attention ownership rendering"),
    ('"CHAIN // "', "Attention responsibility chain rendering"),
    ('+ " // ROOM "', "Room identity rendering"),
    ("responsibility.confidence", "ownership confidence rendering"),
):
    require(ATTENTION, needle, label)

for needle, label in (
    ("property var responsibilityService: null", "Queue ownership dependency"),
    ("responsibilityService.contextForWorkItem({", "Queue work-item ownership lookup"),
    ('"OWNER // "', "Queue ownership rendering"),
    ('"CHAIN // "', "Queue responsibility chain rendering"),
    ('+ " // ROOM "', "Queue Room rendering"),
    ("responsibility.assignmentTitle", "Queue Assignment rendering"),
):
    require(QUEUE, needle, label)

for forbidden in (
    "GitHistoryFoldService",
    "GitHistorySplitService",
    "GitHistoryAbsorbService",
    "GitInteractiveRebaseService",
):
    if forbidden in SERVICE or forbidden in ATTENTION:
        errors.append(
            f"Responsibility mapping crossed Git History ownership: {forbidden}"
        )

if errors:
    print("POST-APOLLO HOSPITAL RESPONSIBILITY CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO HOSPITAL RESPONSIBILITY CONTRACTS // PASS")
print("checked PR/repo/branch -> Room/Bed -> Doctor/session -> Assignment/evidence ownership graph")
