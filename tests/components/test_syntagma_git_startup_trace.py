#!/usr/bin/env python3
"""Source guard for Nurse 3c's disabled-by-default GitService startup trace.

Proves structural intent only; it does not emulate QML or verify live Sway.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
service = (root / "services/git/GitService.qml").read_text(encoding="utf-8")
shell = (root / "shell.qml").read_text(encoding="utf-8")
git = (root / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")
git_panel = (root / "widgets/GitW.qml").read_text(encoding="utf-8")

assert 'Quickshell.env("POST_APOLLO_GIT_STARTUP_TRACE")' in service
assert 'trim() === "1"' in service
assert 'if (!gitService.syntagmaStartupTraceEnabled)' in service
assert 'if (syntagmaStartupTraceEnabled)' in service
assert "SYNTAGMA_STARTUP_TRACE // git scan started" in service
assert "SYNTAGMA_STARTUP_TRACE // git scan finished" in service
assert "SYNTAGMA_STARTUP_TRACE // git refresh finished" in service
assert "SYNTAGMA_STARTUP_TRACE // git slow refresh callback" in service
assert "SYNTAGMA_STARTUP_TRACE // git DONE phases" in service
assert "SYNTAGMA_STARTUP_TRACE // git publish phases" in service
assert "SYNTAGMA_STARTUP_TRACE // git refresh requested" in service
assert "SYNTAGMA_STARTUP_TRACE // git refresh queued" in service
assert 'caller = frames.slice(1, 5).join(" > ")' in service
assert '" pendingAtDone=" + pendingAtDone' in service
assert '" followupQueued=" + (pendingAtDone || staleRead)' in service
assert 'if (syntagmaStartupTraceEnabled) {\n            let caller = "unavailable";' in service
assert "publishParts = publishPendingModels();" in service
assert "if (publishParts)" in service
for name in ("metadata=", "clears=", "local=", "remote=", "topology=", "total="):
    assert name in service
# The branch-model publication was optimized to preserve unchanged rows.
# Keep the startup-trace model paths guarded without requiring full rebuilds.
assert "function branchModelMatches(model, rows, roles)" in service
assert "if (!localUnchanged)" in service
assert "if (!remoteUnchanged)" in service
assert "localBranchRows.append(nextLocalRows[i]);" in service
assert "remoteBranchRows.append(nextRemoteRows[i]);" in service
# Preserve BranchMap delegates by SHA across repeated GitService publications.
assert "function reconcileTopologyRows()" in service
assert "const topologyDelta = reconcileTopologyRows();" in service
assert "topologyRows.move(oldIndex, i, 1);" in service
assert "topologyRows.insert(i, incoming);" in service
assert "topologyRows.setProperty(i, role, incoming[role]);" in service
assert "topologyRows.remove(topologyRows.count - 1);" in service
assert "topologyDelta=" in service
assert service.count("topologyRows.clear();") == 1
assert "topologyRows.clear();" not in service.split(
    "function publishPendingModels()", 1
)[1].split("function allocateLane(", 1)[0]
for name in ("state=", "publish=", "localSelection=", "remoteSelection=",
             "revision=", "available=", "refreshedSignal=", "followup="):
    assert name in service
assert 'duration >= 100' in service
assert 'String(line || "").split("\\t")[0]' in service
assert "callbackSum=" in service and "callbackMax=" in service
assert service.count("gitService.consumeRepoLine(line);") == 2
assert service.count("gitService.consumeRefreshLine(line);") == 2
assert "Component.onCompleted: discoverRepos()" in service
assert 'repoScanProcess.exec([' in service
assert 'refreshProcess.exec([' in service
assert "running: shellRoot.syntagmaLagProbeEnabled" in shell

# Never re-enable the unstable mapped/unmapped Git/Hospital lifecycle.
for widget in (git, hospital):
    assert "visible: true" in widget
    assert "visibilityLifecyclePilot" not in widget

# Avoid rescan of a growing remote-branch model while Git UI is closed.
# The original widgets still compute activity and suggestions when opened.
assert 'root.menuOpen\n                && root.activePage === "git"' in git_panel
assert '&& root.gitView === "control"\n                ? root.remoteActivityPoints()' in git_panel
assert 'root.menuOpen && root.remoteTargetMenuOpen\n                                        ? root.remoteTargetResults(7)' in git_panel
assert 'root.menuOpen && root.remoteTargetMenuOpen\n                                                ? root.remoteTargetResults(7)' in git_panel

# Reopening a fresh Git menu must not rebuild the entire branch model.
# Explicit/manual requests and different repo selections remain unaffected.
assert "readonly property int passiveGitOpenFreshnessMs: 8000" in git_panel
assert "property double lastGitPublishedAtMs: 0" in git_panel
assert "property string lastGitPublishedRepoPath:" in git_panel
assert "const elapsedSincePublish = Date.now() - root.lastGitPublishedAtMs;" in git_panel
assert "root.lastGitPublishedRepoPath === gitService.repoPath" in git_panel
assert "if (!root.gitSnapshotFresh() && !gitService.refreshing)" in git_panel
assert "if (gitService.available && !gitService.lastError)" in git_panel
assert "root.lastGitPublishedAtMs = Date.now();" in git_panel
assert "root.lastGitPublishedRepoPath = gitService.repoPath;" in git_panel

# Passive Git/GitHub mode changes must reuse successful fresh snapshots.
# Explicit REFRESH and Git actions must still call service refresh directly.
assert "function gitSnapshotFresh()" in git_panel
assert "function ensureGitSnapshot()" in git_panel
assert "function githubSnapshotFresh()" in git_panel
assert "function ensureGithubSnapshot()" in git_panel
assert "readonly property int passiveGithubPageFreshnessMs: 15000" in git_panel
assert 'root.lastGithubPublishedRepoSlug === githubService.repoSlug' in git_panel
assert 'root.githubRefreshStartedSlug === githubService.repoSlug' in git_panel
assert 'function onRepoSlugChanged()' in git_panel
assert 'root.githubRefreshStartedSlug !== githubService.repoSlug' in git_panel
assert 'function onRefreshingChanged()' in git_panel
assert "root.lastGithubPublishedAtMs = Date.now();" in git_panel
assert 'root.ensureGitSnapshot();' in git_panel
assert 'root.ensureGithubSnapshot();' in git_panel
assert 'if (githubService.refreshing || root.githubSnapshotFresh())' in git_panel
assert 'root.activePage = "git";\n        root.ensureGitSnapshot();' in git_panel
assert 'root.activePage = "github";\n        root.ensureGitSnapshot();\n        root.ensureGithubSnapshot();' in git_panel
assert 'if (action === "REFRESH")' in git_panel
assert "onTriggered: githubService.refresh()" in git_panel
assert 'if (action === "REFRESH")' in git_panel
assert "gitService.discoverRepos();" in git_panel
assert "function selectRepo(index)" in service
assert "function refresh()" in service

print("SYNTAGMA GIT STARTUP TRACE // SOURCE GUARDS PASS; RUNTIME UNTESTED")
