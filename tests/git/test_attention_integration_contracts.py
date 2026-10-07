#!/usr/bin/env python3
"""Contracts for Hospital GitHub Attention integration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOSPITAL = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
VIEW = (
    ROOT / "widgets/HospitalGitHubAttentionView.qml"
).read_text(encoding="utf-8")
PROVIDER = (
    ROOT / "services/github/GitHubAttentionProvider.qml"
).read_text(encoding="utf-8")
GITW = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ("GitHubAttentionProvider {", "Attention provider host"),
    ("id: attentionCatalogGitService", "repository catalog host"),
    ("function attentionRepositories()", "catalog normalization"),
    ("function refreshGithubAttention()", "Attention refresh seam"),
    ("function openAttention()", "Attention department navigation"),
    ('label: "ATTENTION"', "Attention Hospital tab"),
    ('root.operationsSurface === "attention"', "Attention surface state"),
    ("HospitalGitHubAttentionView {", "Attention presentation"),
    ("interval: 300000", "visible refresh cadence"),
):
    require(HOSPITAL, needle, label)

for needle, label in (
    ('"NEEDS_ME"', "NEEDS_ME filter"),
    ('"FAILED"', "FAILED filter"),
    ('"BLOCKED"', "BLOCKED filter"),
    ('"WAITING"', "WAITING filter"),
    ('"READY"', "READY filter"),
    ("checkFailed", "check evidence"),
    ("reviewDecision", "review evidence"),
    ("mergeStateStatus", "merge blocker evidence"),
    ("signal pullRequestRequested(", "PR navigation signal"),
    ('label: "OPEN PULLS"', "visible PR navigation"),
):
    require(VIEW, needle, label)

for needle, label in (
    ("function openGithubPullRequest(repository, number)", "GitW public PR navigator"),
    ("function continueGithubPullNavigation()", "repository navigation"),
    ("function resolvePendingGithubPullRequest()", "PULLS row resolution"),
    ("gitService.repoIndexOfSlug(repository)", "normal repository catalog lookup"),
    ("root.showGithubPulls()", "normal PULLS navigation"),
    ("root.openPullRequestControl(rows[i])", "normal PR control destination"),
):
    require(GITW, needle, label)

require(
    SHELL,
    "onGithubPullRequestRequested: function(repository, number)",
    "Hospital-to-GitW shell handoff",
)
require(
    SHELL,
    "gitWindow.openGithubPullRequest(",
    "shell must use GitW public navigation seam",
)

if "\\\\'" in PROVIDER:
    errors.append("GitHubAttentionProvider contains malformed double-backslash single-quote escapes")

for forbidden in (
    "GitInteractiveRebaseService",
    "GitInteractiveRebaseView",
    "GitOperationRecoveryService",
    "GitChangeTransferService",
    "GitLineTransferService",
):
    if forbidden in VIEW:
        errors.append(
            f"Attention view crossed Doc 3 exclusion zone: {forbidden}"
        )

if errors:
    print("POST-APOLLO GITHUB ATTENTION INTEGRATION // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB ATTENTION INTEGRATION // PASS")
print("checked catalog -> Hospital Attention -> normal GitW PULLS navigation")
