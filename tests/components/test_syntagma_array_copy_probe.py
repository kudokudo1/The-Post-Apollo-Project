#!/usr/bin/env python3
"""Source-only contract for opt-in array-copy diagnosis; no runtime proof."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
graph = (root / "services/system/GraphHistory.qml").read_text(encoding="utf-8")
notifications = (root / "services/notifications/NotificationsService.qml").read_text(encoding="utf-8")
media = (root / "modules/Mediaplayer.qml").read_text(encoding="utf-8")
ops = (root / "OPERATE/syntagma-ui-lag-probe.md").read_text(encoding="utf-8")

for source in (graph, notifications):
    assert 'Quickshell.env("POST_APOLLO_ARRAY_COPY_PROBE")' in source
    assert 'trim() === "1"' in source
    assert 'readonly property bool arrayCopyProbeEnabled:' in source
    assert "SYNTAGMA_ARRAY_PROBE //" in source

# The graph helpers still use their original bounded copy / arithmetic paths.
assert "function linePoints(values, graphWidth, graphHeight, requiredRange," in graph
assert "const source = Array.isArray(values) ? values.slice() : [];" in graph
assert "if (source.length === 1)" in graph
assert "source.unshift(source[0]);" in graph
assert "points.push(Qt.point(rawX, rawY));" in graph
assert 'recordArrayCopy("linePoints", source.length, copyMs, probeStartMs);' in graph
assert 'recordArrayCopy("linePoints", 0, copyMs, probeStartMs);' in graph
assert 'recordArrayCopy("downsampleHistory", source.length,' in graph
assert 'recordArrayCopy("appendBounded", inputCount, copyMs, probeStartMs);' in graph
assert "while (next.length > limit)" in graph
assert "next.shift();" in graph
assert "Math.max(0, source.length - limit)" in graph
assert "if (probeStartMs)" in graph
assert 'if (now - arrayCopyProbeLastReportMs < 5000)' in graph
assert "arrayCopyProbeBuckets = ({});" in graph
for name in ("count", "maxInput", "copyTotalMs", "workTotalMs", "maxWorkMs"):
    assert name in graph
assert "Process {" not in graph and "Timer {" not in graph

# No changes to durable history, popup pipeline, parsing or retention semantics.
assert "const raw = historyFile.text().trim();" in notifications
assert "document = JSON.parse(raw);" in notifications
assert "const retainedEntries = entries.slice();" in notifications
assert "retainedEntries.sort(function (a, b)" in notifications
assert "const firstRetainedIndex = Math.max(0, retainedEntries.length - maxHistoryEntries);" in notifications
assert "const entry = normalize(retainedEntries[i]);" in notifications
assert "pruneHistory();" in notifications
assert "markNotificationsChanged();" in notifications
assert 'SYNTAGMA_ARRAY_PROBE // notifications-history load' in notifications
assert 'if (probeStartMs)' in notifications

# The Media worker's existing probe is the comparison, not modified by this PR.
assert "media cava-frames 5s count=" in media
assert "receiveCavaFrame(frame)" in media
assert "cavaAmbientTargetHeight" in media

# Existing diagnostics and docs must explain the flag and its limits.
assert "POST_APOLLO_ARRAY_COPY_PROBE=1" in ops
assert "SYNTAGMA_ARRAY_PROBE" in ops
for src in (graph, notifications):
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if "SYNTAGMA_ARRAY_PROBE //" not in line:
            continue
        fragment = "\n".join(lines[i:i + 9])
        for sensitive in ("entry.message", "entry.title", "raw", "secret",
                          "currentTrack", "document.notifications", "historyFile.text"):
            assert sensitive not in fragment, sensitive

print("SYNTAGMA ARRAY COPY PROBE // SOURCE GUARDS PASS; RUNTIME UNTESTED")
