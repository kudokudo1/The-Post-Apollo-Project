#!/usr/bin/env python3
"""Static bridge seam guards; Node tests exercise the actual projection policy."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
policy = (ROOT / "services/hub/ApolloHubSystemPolicy.js").read_text(encoding="utf-8")
telemetry = (ROOT / "services/system/SystemTelemetry.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/apollo-hub-live-bridge.yml").read_text(encoding="utf-8")

def require(source, value, label):
    assert value in source, f"{label}: missing {value!r}"

for needle in (
    'import "ApolloHubSystemPolicy.js" as SystemPolicy',
    "property var systemSource: null",
    "property double systemObservedAtMs: 0",
    "onSystemSourceChanged: systemObservedAtMs = 0",
    "target: bridge.systemSource",
    "function onLoadingChanged()",
    "function onRefreshed()",
    "bridge.observationNowMs = Date.now()",
    "bridge.systemObservedAtMs = bridge.observationNowMs",
    "readonly property var systemRows:",
    "readonly property var systemSnapshot: SystemPolicy.snapshot(",
    "systemConnected, systemLoading, systemError, systemRows,",
    "systemObservedAtMs, observationNowMs",
    "running: bridge.weatherSource !== null || bridge.systemSource !== null",
):
    require(bridge, needle, "bridge")

for needle in (
    "signal refreshed()",
    "property var systemRows: []",
    "property bool loading: false",
    'property string errorText: ""',
):
    require(telemetry, needle, "shared SystemTelemetry")

for needle in (
    "SystemTelemetry {",
    "id: sharedSystemTelemetry",
    "systemSource: sharedSystemTelemetry",
    "function refreshCpuTileWhenVisible()",
    "function onMenuOpenChanged()",
    "function onActiveTilesChanged()",
    'tile.module === "cpu"',
    "sharedSystemTelemetry.refresh();",
):
    require(shell, needle, "shell shared telemetry")
assert shell.count("SystemTelemetry {") == 1, "Must reuse existing telemetry"
assert shell.count("ApolloHubLiveBridge {") == 1, "Must reuse existing Hub bridge"
assert shell.count("systemSource: sharedSystemTelemetry") == 1
assert "if (!apolloHubWindow.menuOpen)" in shell
assert "if (!Array.isArray(tiles)" in shell
assert "mediaControllerSource: sharedMediaDock.hubMediaController" in shell
assert "weatherSource: weatherService" in shell

for needle in (
    ".pragma library",
    "function observationFresh(",
    "function rowById(",
    "function usagePercent(",
    "function snapshot(",
    '"system:cpu"',
    '"system:memory"',
    '"system:rootfs"',
    '"system:swap"',
    "var MAX_SAMPLE_AGE_MS = 300000",
    'state = "unobserved"',
    'state = "stale"',
    'state = "error"',
    "cpuPercent:",
    "memoryPercent:",
    "rootFilesystemPercent:",
):
    require(policy, needle, "projection policy")

# Exclude explanatory // comments from forbidden executable-token guards.
# The source explicitly documents the avoidance of duplicate subprocesses.
code_only = "\n".join(
    line.split("//", 1)[0] for line in (bridge + "\n" + policy).splitlines()
)
for forbidden in (
    "SystemTelemetry {", "Process {", "Http", "FileView {",
    "systemSource.refresh(", "systemSource.monitorScript(",
    "FanControl {", "pkexec", "subprocess",
):
    assert forbidden not in code_only, f"Bridge must be read-only: {forbidden}"

for needle in (
    "tests/hub/test_apollo_hub_system_bridge.py",
    "tests/hub/test_apollo_hub_system_policy.cjs",
    "node tests/hub/test_apollo_hub_system_policy.cjs",
):
    require(workflow, needle, "CI")

print("ApolloHub CPU++ shared bridge static contracts passed")
