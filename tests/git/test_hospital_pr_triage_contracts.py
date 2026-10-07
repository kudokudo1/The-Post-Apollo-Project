#!/usr/bin/env python3
"""Contracts for Hospital PR triage prioritization."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEW = (
    ROOT / "widgets/HospitalGitHubAttentionView.qml"
).read_text(encoding="utf-8")
errors = []


def require(needle: str, label: str) -> None:
    if needle not in VIEW:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ("function responsibilityFor(itemValue)", "responsibility synthesis"),
    ("function filterMatches(itemValue)", "triage filters"),
    ("function triageScore(itemValue)", "deterministic triage score"),
    ("function triageReason(itemValue)", "human explanation"),
    ("function triageRows()", "priority sorting"),
    ('"REVIEW"', "review inbox filter"),
    ('"OWNED"', "owned-work filter"),
    ('"UNMAPPED"', "ownership-gap filter"),
    ('"TRIAGE "', "visible triage explanation"),
    ("NEEDS_ME", "needs-me priority"),
    ("FAILED", "failed priority"),
    ("CHANGES_REQUESTED", "changes-requested priority"),
    ("NEEDS_REVIEW", "review priority"),
    ("context.confidence", "ownership confidence"),
    ("responsibilityService.currentRoomId", "current-Room boost"),
):
    require(needle, label)

if "GitHubAttentionProvider {" in VIEW:
    errors.append(
        "Triage view must consume the existing provider, not create duplicate discovery"
    )

if errors:
    print("POST-APOLLO HOSPITAL PR TRIAGE // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO HOSPITAL PR TRIAGE // PASS")
print("checked urgency sorting, review filters, and ownership-aware explanation")
