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
    ("function roomScore(roomValue, repositoryValue, branchValue)", "room scorer"),
    ("function bestRoom(repositoryValue, branchValue)", "room resolver"),
    ("function specialistsForRoom(roomValue)", "specialist resolver"),
    ("function activeAssignmentForRoom(roomValue)", "active assignment"),
    ("function contextFor(repositoryValue, branchValue)", "responsibility context"),
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
):
    require(HOSPITAL, needle, label)

for needle, label in (
    ("property var responsibilityService: null", "Attention ownership dependency"),
    ("responsibilityService.contextFor(", "Attention ownership lookup"),
    ('"OWNER // "', "Attention ownership rendering"),
    ('+ " // ROOM "', "Room identity rendering"),
    ("responsibility.confidence", "ownership confidence rendering"),
):
    require(ATTENTION, needle, label)

for needle, label in (
    ("property var responsibilityService: null", "Queue ownership dependency"),
    ("responsibilityService.contextFor(", "Queue ownership lookup"),
    ('"OWNER // "', "Queue ownership rendering"),
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
print("checked repo/branch -> Room -> Specialist/Assignment ownership mapping")
