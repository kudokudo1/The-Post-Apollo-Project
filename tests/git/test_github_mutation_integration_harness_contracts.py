#!/usr/bin/env python3
"""Contracts for the opt-in live GitHub mutation integration harness."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = (
    ROOT / "tests/git/integration_github_mutations.py"
).read_text(encoding="utf-8")
errors = []


def require(needle: str, label: str) -> None:
    if needle not in HARNESS:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ("POST_APOLLO_GITHUB_MUTATION_TESTS", "explicit enable gate"),
    ("POST_APOLLO_GITHUB_MUTATION_TEST_REPO", "scratch repository gate"),
    ("POST_APOLLO_GITHUB_MUTATION_CONFIRM", "destructive confirmation gate"),
    ("I_UNDERSTAND_THIS_MUTATES_THE_SCRATCH_REPO", "confirmation phrase"),
    ("kudokudo1/taskbars-post-apollo", "production repository refusal"),
    ("ISSUE LIFECYCLE // PASS", "Issue lifecycle coverage"),
    ("PR LIFECYCLE // PASS", "PR lifecycle coverage"),
    ("REVIEW THREAD LIFECYCLE // PASS", "review-thread coverage"),
    ("POST_APOLLO_TEST_MERGE_QUEUE", "optional Merge Queue gate"),
    ("MERGE QUEUE ENQUEUE/DEQUEUE // PASS", "Merge Queue mutation coverage"),
    ("issue_readback(", "Issue evidence readback"),
    ("pr_readback(", "PR evidence readback"),
    ("reviewThreads(first:100)", "review-thread evidence readback"),
    ("expectedHeadOid:$expectedHeadOid", "Merge Queue head pin"),
    ("jump:false", "no queue jumping"),
    ('"gh", "pr", "close"', "PR cleanup"),
    ('"gh", "issue", "close"', "Issue cleanup"),
    ('"--method",\n            "DELETE"', "branch cleanup"),
):
    require(needle, label)

if errors:
    print("POST-APOLLO GITHUB MUTATION HARNESS CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB MUTATION HARNESS CONTRACTS // PASS")
print("checked explicit gates, live mutation families, readback, and cleanup")
