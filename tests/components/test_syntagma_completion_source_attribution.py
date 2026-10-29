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

# Opt-in SplitParser read attribution. The source keeps the existing process
# and timer lifecycle, samples ordinary lines, and logs only static slot labels,
# lengths, monotonically increasing sequence numbers, and handler timings.
git_service = (root / "services/git/GitService.qml").read_text(encoding="utf-8")
hospital_service = sources["hospital-topology"]
for service_name, src in (("git-service", git_service),
                          ("hospital-topology", hospital_service)):
    assert 'function beginSplitRead(slot, line)' in src, service_name
    assert 'function endSplitRead(slot, trace)' in src, service_name
    assert 'if (!subprocessLagProbeEnabled)\n            return null;' in src, service_name
    assert 'size >= 2048 || sequence % 64 === 1' in src, service_name
    assert 'elapsedMs >= 25' in src, service_name
    assert src.count(f'SYNTAGMA_SPLIT_READ_PROBE // service={service_name}') == 2
    helper = src.split('function beginSplitRead(slot, line)', 1)[1].split('function endSplitRead(slot, trace)', 1)[0]
    assert 'String(line || "").length' in helper
    assert 'console.warn(' in helper
    assert 'line +' not in helper and 'line)' not in helper.split('console.warn(', 1)[1]
for slot in ("repo", "refresh", "action"):
    for channel in ("stdout", "stderr"):
        label = f'{slot}-{channel}'
        assert git_service.count(f'beginSplitRead("{label}", line)') == 1, label
        assert git_service.count(f'endSplitRead("{label}", splitReadTrace)') >= 1, label
assert git_service.count("    Process {") == 3
assert git_service.count("    Timer {") >= 1
for channel in ("stdout", "stderr"):
    label = f'topology-{channel}'
    assert hospital_service.count(f'beginSplitRead("{label}", line)') == 1
    assert hospital_service.count(f'endSplitRead("{label}", splitReadTrace)') == 1
assert hospital_service.count("    Process {") == 1
assert hospital_service.count("    Timer {") == 1

print("SYNTAGMA V5 COMPLETION + SPLIT READ ATTRIBUTION // SOURCE GUARDS PASS; RUNTIME UNTESTED")
