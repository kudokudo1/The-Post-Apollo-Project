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

assert 'Quickshell.env("POST_APOLLO_GIT_STARTUP_TRACE")' in service
assert 'trim() === "1"' in service
assert 'if (!gitService.syntagmaStartupTraceEnabled)' in service
assert 'if (syntagmaStartupTraceEnabled)' in service
assert "SYNTAGMA_STARTUP_TRACE // git scan started" in service
assert "SYNTAGMA_STARTUP_TRACE // git scan finished" in service
assert "SYNTAGMA_STARTUP_TRACE // git refresh finished" in service
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

print("SYNTAGMA GIT STARTUP TRACE // SOURCE GUARDS PASS; RUNTIME UNTESTED")
