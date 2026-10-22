#!/usr/bin/env python3
"""B3 Network passive-source integration contracts (runtime still required)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
policy = (ROOT / "services/hub/ApolloHubNetworkPolicy.js").read_text(encoding="utf-8")
dock = (ROOT / "modules/Network.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/apollo-hub-live-bridge.yml").read_text(encoding="utf-8")

for name in (
    "import Quickshell.Networking",
    'import "ApolloHubNetworkPolicy.js" as NetworkPolicy',
    "Networking.devices",
    "DeviceType.Wifi",
    "DeviceType.Ethernet",
    "activeWifiNetwork",
    "network.connected === true",
    "readonly property var networkSnapshot: NetworkPolicy.snapshot({",
    "wifiSignal: activeWifiNetwork ? activeWifiNetwork.signalStrength : null",
    "ethernetConnected:",
    "property var networkDockSource: null",
    "wifiLinkSpeedMbps: networkDockSource",
    "networkDockSource.observedWifiLinkMbps",

):
    assert name in bridge, f"Bridge missing passive Network source: {name}"

# Use the same Quickshell networking module/type grammar as the existing
# Network dock; don't introduce another nmcli/iw/ethtool observer.
for needle in ("import Quickshell.Networking", "Networking.devices",
               "DeviceType.Wifi", "DeviceType.Ethernet"):
    assert needle in dock, f"Network dock source moved: {needle}"

for needle in (
    ".pragma library", "function snapshot(", "function signalPercent(",
    "function linkSpeedMbps(", "linkSpeedApproximate:",
    'internetState: "unverified"', "signalPercent:", '? "unavailable"',
):
    assert needle in policy, f"Missing projection policy: {needle}"

# Ignore comments when checking forbidden executable tokens.
code_only = "\n".join(line.split("//", 1)[0]
                       for line in (bridge + "\n" + policy).splitlines())
for forbidden in (
    "Process {", "SystemTelemetry {", "Network {", "FileView {",
    "nmcli", "ethtool", "curl", "iw dev", "connect(", "disconnect(",
    "checkConnectivity(", "execDetached(", "refresh()",
):
    assert forbidden not in code_only, f"Extra polling/control prohibited: {forbidden}"

# One existing Network instance supplies both icon UI and its iw speed reading.
assert shell.count("Network {") == 1
assert "id: sharedNetworkDock" in shell
assert "networkDockSource: sharedNetworkDock" in shell
assert "readonly property real observedWifiLinkMbps:" in dock
assert "root.wifiEnabled && root.active" in dock
assert "root.linkSpeed" in dock
assert dock.count('id: wifiLinkProcess') == 1
assert dock.count('interval: 500') == 1
assert "ApolloHubLiveBridge {" in shell
assert "liveBridge: apolloHubLive" in shell
assert "systemSnapshot: SystemPolicy.snapshot(" in bridge
assert "weatherSnapshot:" in bridge

for needle in (
    '"services/hub/ApolloHubNetworkPolicy.js"',
    '"tests/hub/test_apollo_hub_network_policy.cjs"',
    '"tests/hub/test_apollo_hub_network_bridge.py"',
    "python3 tests/hub/test_apollo_hub_network_bridge.py",
    "node tests/hub/test_apollo_hub_network_policy.cjs",
):
    assert needle in workflow, f"Network CI trigger or step missing: {needle}"

print("ApolloHub Network bridge static contracts passed")
