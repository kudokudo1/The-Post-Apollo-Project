#!/usr/bin/env python3
"""Source-only guards for opt-in background stall diagnostics.

This cannot verify QML runtime responsiveness or identify a slow Qt callback.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
media = (root / "modules/Mediaplayer.qml").read_text(encoding="utf-8")
network = (root / "modules/Network.qml").read_text(encoding="utf-8")
notifications = (root / "widgets/notifications/NotificationsHubW.qml").read_text(encoding="utf-8")
ops = (root / "OPERATE/syntagma-ui-lag-probe.md").read_text(encoding="utf-8")

for source in (media, network, notifications):
    assert 'Quickshell.env("POST_APOLLO_UI_LAG_PROBE")' in source
    assert 'trim() === "1"' in source
    assert "SYNTAGMA_BG_PROBE" in source
    assert "bgLagProbeEnabled" in source

# Preserve the visualizer, MPD polling, and existing data flow.
assert "mediaDock.receiveCavaFrame(frame);" in media
assert "levels = newLevels;" in media
assert "interval: 2000" in media
assert "running: true" in media
assert "media cava-frame synchronous=" in media
assert "media cava-frames 5s count=" in media
assert "if (traceStartMs)" in media

# Preserve the original high-frequency network work and notification consumers.
assert "interval: 500" in network
for running in ("wifiEnabledProcess", "wifiSignalProcess",
                "wifiLinkProcess", "ethernetProcess"):
    assert f"{running}.running = true;" in network
assert "networkLinkProducer.observeDeviceResult(text);" in network
assert "networkInternetHealthProducer.observeDeviceResult(text);" in network
assert "network poll-gap=" in network

# Isolation switch defaults off and suppresses BOTH Network dock timer work
# and its startup commands. It never requests link/radio/route changes.
assert 'Quickshell.env("POST_APOLLO_NETWORK_POLL_PAUSED")' in network
assert 'trim() === "1"' in network
assert "readonly property bool networkPollPaused:" in network
assert "running: !networkDock.networkPollPaused" in network
assert "if (networkDock.networkPollPaused) {" in network
assert "network widget polling PAUSED" in network
assert network.count("Process {") == 5  # Existing command clients, no new ones.
for forbidden in ("nmcli radio wifi off", "nmcli networking off",
                  "nmcli dev disconnect", "systemctl stop NetworkManager"):
    assert forbidden not in network
assert 'reportBgCallback("poll-dispatch"' in network
for stage in ("wifi-radio", "wifi-signal", "wifi-link",
              "device-and-notification-producers", "ethernet-speed"):
    assert f'reportBgCallback("{stage}"' in network

# Preserve filtering, sorting, and model population; log only timing and counts.
assert "filteredNotifications.clear();" in notifications
assert "root.notificationMatches(" in notifications
assert "rows.sort(function(a, b)" in notifications
assert "filteredNotifications.append(rows[j].data);" in notifications
assert "reportBgRebuild(traceStartMs" in notifications
assert "notifications rebuild synchronous=" in notifications
assert 'rendered=" + filteredNotifications.count' in notifications

# Probe log declarations must never interpolate private notification text,
# raw CLI responses, financial records or music titles.
for src in (media, network, notifications):
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if "SYNTAGMA_BG_PROBE //" not in line:
            continue
        fragment = "\n".join(lines[i:i + 4])
        for private in ("entry.message", "this.text", "currentTrack",
                        "payload", "secret", "authToken"):
            assert private not in fragment, (private, fragment)

assert 'SYNTAGMA_(LAG|BG)_PROBE' in ops
print("SYNTAGMA BACKGROUND LAG PROBE // SOURCE GUARDS PASS; RUNTIME UNTESTED")
