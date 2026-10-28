#!/usr/bin/env python3
"""Source-only checks for V5 completion-to-QML array-copy attribution.

Does not claim a runtime root cause. No Quickshell instance is launched.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
files = {
    "git-history": root / "services/git/GitHistoryService.qml",
    "hospital-topology": root / "services/hospital/HospitalService.qml",
}
sources = {name: path.read_text(encoding="utf-8") for name, path in files.items()}

for name, src in sources.items():
    assert 'Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE")' in src, name
    assert 'readonly property bool subprocessLagProbeEnabled:' in src, name
    assert 'if (!subprocessLagProbeEnabled)\n            return;' in src, name
    assert f'SYNTAGMA_SUBPROCESS_PROBE // service={name}' in src, name
    assert src.count('SYNTAGMA_SUBPROCESS_PROBE //') == 1, name
    function = src.split('function traceSubprocessLag(stage, size)', 1)[1].split('\n    }', 1)[0]
    assert '" stage=" + stage + " size=" + Number(size || 0)' in function
    assert '" tsMs=" + Date.now()' in function
    for forbidden in ("this.text", "stdoutText", "stderrText", "repositoryPath", "repoPath", "command:", "payload"):
        assert forbidden not in function, (name, forbidden)

git = sources["git-history"]
expected = ["queryProcess", "reflogProcess", "inspectProcess",
            "detailProcess", "diffProcess", "actionProcess"]
blocks = re.split(r"\n    Process \{", git)[1:]
assert len(blocks) == len(expected)
for name, block in zip(expected, blocks):
    assert f"\n        id: {name}" in block, name
    assert block.count("onStreamFinished: {") == 2, name
    assert block.count("onExited: function(code, exitStatus) {") == 1, name
    for stage in ("stdout", "stderr", "exit"):
        begin = f'traceSubprocessLag("{name}:{stage}:begin"'
        end = f'traceSubprocessLag("{name}:{stage}:end"'
        assert block.count(begin) == block.count(end) == 1, (name, stage)
        assert block.index(begin) < block.index(end), (name, stage)
        if stage == "exit":
            assert block.index(begin) < block.index(f"root.{name.removesuffix('Process')}ExitSeen = true;"), name

hospital = sources["hospital-topology"]
assert hospital.count("    Process {") == 1
for begin, operation, end in (
    ("commit-copy:begin", "const rows = pendingTopologyRows.slice();", "commit-copy:end"),
    ("topology-publish:begin", "topologyRows.clear();", "topology-publish:end"),
):
    start = hospital.index(f'traceSubprocessLag("{begin}"')
    op = hospital.index(operation, start)
    finish = hospital.index(f'traceSubprocessLag("{end}"')
    assert start < op < finish, begin
# Process invocations, timer counts, and existing execution contracts untouched.
assert git.count("    Process {") == 6
assert hospital.count("    Timer {") == 1
assert hospital.count("    Process {") == 1
print("SYNTAGMA V5 COMPLETION ATTRIBUTION // SOURCE GUARDS PASS; RUNTIME UNTESTED")
