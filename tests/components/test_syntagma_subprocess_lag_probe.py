#!/usr/bin/env python3
"""Source-only guards: opt-in QML subprocess completion stall discriminator.

These checks do not measure runtime CPU or identify a guilty subprocess.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
paths = {
    "hospital-audit": "services/hospital/HospitalAuditService.qml",
    "hospital-rounds": "services/hospital/HospitalRoundsService.qml",
    "github-attention": "services/github/GitHubAttentionProvider.qml",
    "github-service": "services/github/GitHubService.qml",
}
sources = {name: (root / path).read_text(encoding="utf-8")
           for name, path in paths.items()}

for name, source in sources.items():
    assert 'Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE")' in source, name
    assert 'trim() === "1"' in source, name
    assert "readonly property bool subprocessLagProbeEnabled:" in source, name
    assert "function traceSubprocessLag(stage, size)" in source, name
    assert "if (!subprocessLagProbeEnabled)\n            return;" in source, name
    assert f'SYNTAGMA_SUBPROCESS_PROBE // service={name}' in source, name
    assert '" stage=" + stage + " size=" + Number(size || 0)' in source, name
    assert '" tsMs=" + Date.now()' in source, name
    assert source.count('SYNTAGMA_SUBPROCESS_PROBE //') == 1, name

audit = sources["hospital-audit"]
for stage in ("stdout:begin", "stdout:end", "stderr:begin", "stderr:end",
              "exit:begin", "exit:end", "complete:begin", "parse:begin",
              "parse:end", "audited:begin", "audited:end"):
    assert f'"{stage}"' in audit, stage
assert audit.count("    Process {") == 1
assert audit.index('traceSubprocessLag("parse:begin"') < audit.index("parseAudit(payload);")
assert audit.index('traceSubprocessLag("audited:begin"') < audit.index("audited();")

rounds = sources["hospital-rounds"]
for stage, operation in (
    ("rooms-copy:begin", "const nextRooms = rooms.slice();"),
    ("floors-copy:begin", "const nextFloors = floors.slice();"),
    ("rooms-sort-copy:begin", "const orderedRooms = rooms.slice().sort("),
    ("floors-sort-copy:begin", "const orderedFloors = floors.slice().sort("),
):
    marker = f'traceSubprocessLag("{stage}"'
    assert marker in rounds and operation in rounds
    assert rounds.index(marker) < rounds.index(operation), stage
assert rounds.index('traceSubprocessLag("metrics:begin"') < rounds.index("for (let i = 0; i < rooms.length; ++i)")
assert 'traceSubprocessLag("metrics:end", rooms.length);' in rounds

attention = sources["github-attention"]
for stage in ("stdout:begin", "stdout:end", "stderr:begin", "stderr:end",
              "exit:begin", "exit:end", "complete:begin", "parse:begin",
              "parse:end"):
    assert f'"{stage}"' in attention, stage
assert attention.count("    Process {") == 1
assert attention.index('traceSubprocessLag("parse:begin"') < attention.index('parseResponse(output || "{}");')

github = sources["github-service"]
processes = re.split(r"\n    Process \{", github)[1:]
expected = (
    "evidenceRunsProcess", "inspectorProcess", "inspectorLogsProcess",
    "remoteActionProcess", "factoryProcess", "pxRuntimeProcess",
    "workflowsProcess", "runsProcess",
)
assert len(processes) == len(expected)
for name, process in zip(expected, processes):
    assert f"\n        id: {name}" in process, name
    for marker in ("stdout:begin", "stderr:begin", "exit:begin"):
        assert f'traceSubprocessLag("{name}:{marker}"' in process, (name, marker)
    assert process.count('githubService.traceSubprocessLag("') == 3, name

# Keep the diagnostics read-only: no new process or timer added, and never
# interpolate raw stdout/stderr into marker text. Only stage and size are used.
for name, source in sources.items():
    assert "function traceSubprocessLag(stage, size)" in source
    section = source.split("function traceSubprocessLag(stage, size)", 1)[1].split("\n    }", 1)[0]
    for forbidden in ("this.text", "stdoutText", "stderrText",
                      "payload", "authToken", "repository"):
        assert forbidden not in section, (name, forbidden)
for source in (audit, attention, github):
    assert "Timer {\n        id: subprocessLag" not in source
    assert "Process {\n        id: subprocessLag" not in source

print("SYNTAGMA SUBPROCESS LAG PROBE // SOURCE GUARDS PASS; RUNTIME UNTESTED")
