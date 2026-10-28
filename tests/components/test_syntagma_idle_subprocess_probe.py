#!/usr/bin/env python3
"""Read-only source guards for expanded background subprocess stall markers.

Only verifies source-level invariants. Not a Qt runtime or causality test.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
git = (root / "services/git/GitService.qml").read_text(encoding="utf-8")
telemetry = (root / "services/system/SystemTelemetry.qml").read_text(encoding="utf-8")

for service, source in (("git-service", git), ("system-telemetry", telemetry)):
    assert 'Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE")' in source
    assert 'trim() === "1"' in source
    assert "readonly property bool subprocessLagProbeEnabled:" in source
    assert "function traceSubprocessLag(stage, size)" in source
    assert "if (!subprocessLagProbeEnabled)\n            return;" in source
    assert f'SYNTAGMA_SUBPROCESS_PROBE // service={service}' in source
    assert source.count("SYNTAGMA_SUBPROCESS_PROBE //") == 1
    helper = source.split("function traceSubprocessLag(stage, size)", 1)[1].split("\n    }", 1)[0]
    assert '" stage=" + stage + " size=" + Number(size || 0)' in helper
    assert '" tsMs=" + Date.now()' in helper
    for forbidden in ("this.text", "repoPath", "stdoutText", "payload", "source", "user"):
        assert forbidden not in helper, (service, forbidden)

for label, consumer in (("repo", "consumeRepoLine"), ("refresh", "consumeRefreshLine")):
    section = git.split(f"        id: {'repoScanProcess' if label == 'repo' else 'refreshProcess'}", 1)[1].split("    Process {", 1)[0]
    begin = f'traceSubprocessLag("{label}:DONE:begin"'
    end = f'traceSubprocessLag("{label}:DONE:end"'
    assert section.count(begin) == 1, label
    assert section.count(end) == 2, label  # Both startup-trace paths
    assert section.index(begin) < section.index(f"gitService.{consumer}(line);")
    assert '&& String(line || "").split("\\t")[0] === "DONE"' in section
    assert 'if (probeDone)' in section
    # The QML id repoRows is private to the Scope; accessing it through
    # gitService.repoRows throws a runtime TypeError in onRead(DONE).
    # The public repoCount property is intentionally exported by GitService.
    if label == "repo":
        assert 'readonly property int repoCount: repoRows.count' in git
        assert section.count('gitService.repoCount') == 3
        assert 'gitService.repoRows.count' not in section
for marker, call in (
    ("refresh:publish:begin", "publishParts = publishPendingModels();"),
    ("refresh:refreshed:begin", "refreshed();"),
):
    before = git.index(f'traceSubprocessLag("{marker}"')
    assert before < git.index(call, before), marker
for stage in ("refresh:publish:end", "refresh:refreshed:end",
              "action:exit:begin", "action:exit:end"):
    assert f'traceSubprocessLag("{stage}"' in git
assert git.count("    Process {") == 3
for key in ("actionBusy", "actionProcessDoneSeen", "actionExitFallback.restart();"):
    assert key in git

for stage in ("stdout:begin", "parse:begin", "parse:end", "publish:begin",
              "publish:end", "parse-or-publish:error", "refreshed:begin",
              "refreshed:end", "monitor-observation:begin",
              "monitor-observation:end", "stdout:end", "stderr:begin",
              "stderr:end"):
    assert f'traceSubprocessLag("{stage}"' in telemetry, stage
assert telemetry.index('traceSubprocessLag("parse:begin"') < telemetry.index('JSON.parse(text || "{}")')
assert telemetry.index('traceSubprocessLag("publish:begin"') < telemetry.index("systemTelemetry.thermalRows =")
assert telemetry.index('traceSubprocessLag("refreshed:begin"') < telemetry.index("systemTelemetry.refreshed();")
assert telemetry.count("    Process {") == 1
assert "Timer {" not in telemetry
assert "monitorProcess.exec([" in telemetry
assert '"/usr/bin/python3"' in telemetry

print("SYNTAGMA IDLE SUBPROCESS DIAGNOSTICS // SOURCE GUARDS PASS; RUNTIME UNTESTED")
