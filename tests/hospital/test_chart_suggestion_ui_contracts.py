#!/usr/bin/env python3
"""Contracts for operator-reviewed Hospital Chart memory suggestions."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEW = (ROOT / "widgets/HospitalChartsView.qml").read_text(encoding="utf-8")
SERVICE = (
    ROOT / "services/hospital/HospitalChartService.qml"
).read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ("property bool suggestionPanelOpen: false", "suggestion surface state"),
    ("sourceSuggestions", "scope-aware suggestion source"),
    ("selectedSuggestion", "selected proposal"),
    ("function openSuggestionPanel()", "review entry point"),
    ("function promoteSelectedSuggestion()", "operator promotion"),
    ("function rejectSelectedSuggestion()", "operator rejection"),
    ('"MEMORY SUGGESTIONS // "', "suggestion review header"),
    ('"DOCTOR MEMORY PROPOSAL // #"', "proposal detail"),
    ('"PROVENANCE // ROOM "', "proposal provenance"),
    ('? "PROMOTING" : "PROMOTE"', "promotion control"),
    ('? "REJECTING" : "REJECT"', "rejection control"),
    ("OPERATOR DECISION NOTE // OPTIONAL", "decision note"),
    ("onSuggestionDecision(operation, result)", "decision refresh"),
):
    require(VIEW, needle, label)

for needle, label in (
    ('"chart-suggestions"', "suggestion reads"),
    ('"chart-suggestion-promote"', "promotion backend"),
    ('"chart-suggestion-reject"', "rejection backend"),
    ('"--operator-id"', "operator attribution"),
    ("signal suggestionDecision", "decision event"),
):
    require(SERVICE, needle, label)

if "chart-entry-add" in VIEW:
    errors.append(
        "Suggestion review must use HospitalChartService, not write Chart entries directly"
    )

if errors:
    print("POST-APOLLO HOSPITAL MEMORY PROMOTION UI // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO HOSPITAL MEMORY PROMOTION UI // PASS")
print("checked Doctor proposal -> operator promote/reject -> durable Chart boundary")
