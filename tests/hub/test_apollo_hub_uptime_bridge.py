#!/usr/bin/env python3
"""B5 uptime source/bridge contracts; runtime FileView still requires desktop acceptance."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "services/hub/ApolloHubUptimeSource.qml").read_text(encoding="utf-8")
policy = (ROOT / "services/hub/ApolloHubUptimePolicy.js").read_text(encoding="utf-8")
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
module = (ROOT / "services/hub/qmldir").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/apollo-hub-live-bridge.yml").read_text(encoding="utf-8")
layout = (ROOT / "services/hub/ApolloHubLayout.js").read_text(encoding="utf-8")

for needle in (
    "import Quickshell.Io",
    'import "ApolloHubUptimePolicy.js" as UptimePolicy',
    "FileView {", 'path: "/proc/uptime"',
    "watchChanges: false", "printErrors: false", "onLoaded:",
    "uptime.raw = uptimeFile.text();",
    "uptime.observedAtMs = observedNow;",
    "onLoadFailed: function(error)",
    "uptime.observedAtMs = 0;",
    "uptime.loadError = true;",
    "interval: 60000", "onTriggered: uptimeFile.reload()",
    "readonly property var snapshot: UptimePolicy.snapshot(",
): assert needle in source, f"Missing Uptime source contract: {needle}"

for needle in (
    "ApolloHubUptimeSource {", "id: uptimeSource",
    "readonly property var uptimeSnapshot: uptimeSource.snapshot",
): assert needle in bridge, f"Missing B5 bridge seam: {needle}"

for needle in (
    ".pragma library", "function parseSeconds(", "function snapshot(",
    "MAX_SAMPLE_AGE_MS = 150000", 'state = error ? "error"',
    '"unobserved"', '"unavailable"', '"stale"', '"ready"',
    "uptimeSeconds:", "days:", "hours:", "minutes:", "label:",
): assert needle in policy, f"Missing Uptime policy: {needle}"

assert "ApolloHubUptimeSource 1.0 ApolloHubUptimeSource.qml" in module
assert '{ module: "uptime", size: "half" }' in layout
assert shell.count("ApolloHubLiveBridge {") == 1
assert "FileView {" not in bridge, "FileView belongs in dedicated source only"
assert "Process {" not in source and "Process {" not in bridge
for forbidden in ("setText(", "setData(", "writeAdapter(", "SystemTelemetry {",
                  "execDetached(", "command:", "http", "http://", "https://"):
    assert forbidden not in source, f"Uptime source cannot perform writes/IO actions: {forbidden}"
assert source.count("FileView {") == 1
assert source.count("uptimeFile.reload()") == 1
for needle in (
    '"services/hub/ApolloHubUptimeSource.qml"',
    '"services/hub/ApolloHubUptimePolicy.js"',
    '"tests/hub/test_apollo_hub_uptime_bridge.py"',
    '"tests/hub/test_apollo_hub_uptime_policy.cjs"',
    "python3 tests/hub/test_apollo_hub_uptime_bridge.py",
    "node tests/hub/test_apollo_hub_uptime_policy.cjs",
):
    assert needle in workflow, f"Missing B5 CI path/step: {needle}"
print("ApolloHub B5 read-only uptime source contracts passed")
