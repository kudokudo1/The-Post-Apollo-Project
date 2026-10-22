#!/usr/bin/env python3
"""B4 read-only Media bridge contracts; live MPD/MPRIS runtime unverified."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
policy = (ROOT / "services/hub/ApolloHubMediaPolicy.js").read_text(encoding="utf-8")
headless = (ROOT / "services/media/HeadlessMediaController.qml").read_text(encoding="utf-8")
mpris = (ROOT / "services/media/MprisPlaybackAdapter.qml").read_text(encoding="utf-8")
deck = (ROOT / "widgets/MediaDeckW.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/apollo-hub-live-bridge.yml").read_text(encoding="utf-8")

for needle in (
    "import Quickshell.Services.Mpris",
    'import "ApolloHubMediaPolicy.js" as MediaPolicy',
    "property var mediaControllerSource: null",
    'property string selectedMprisBusName: ""',
    "onMediaControllerSourceChanged: mediaObservedAtMs = 0",
    "target: bridge.mediaControllerSource",
    "function onSnapshotChanged()",
    'bridge.mediaControllerSource.pendingAction === "snapshot"',
    'bridge.mediaControllerSource.errorText === ""',
    "readonly property var mpdSnapshot: MediaPolicy.mpdSnapshot(",
    "readonly property var mprisPlayers: Mpris.players.values.filter(",
    "org.mpris.MediaPlayer2.playerctld",
    "readonly property var selectedMprisPlayer:",
    "p.dbusName === bridge.selectedMprisBusName",
    "selectedMprisPlayer.playbackState === MprisPlaybackState.Playing",
    "selectedMprisPlayer.playbackState === MprisPlaybackState.Paused",
    "selectedMprisPlayer.playbackState === MprisPlaybackState.Stopped",
    "readonly property var mprisSnapshot: MediaPolicy.mprisSnapshot({",
    "readonly property var mediaSnapshot:",
    "interval: 5000",
    "running: bridge.mediaControllerSource !== null",
):
    assert needle in bridge, f"Missing Media bridge seam: {needle}"
for needle in (
    "function mpdSnapshot(", "function mprisSnapshot(",
    "MAX_MPD_AGE_MS = 15000", '"selection-required"',
    '"player-missing"', "ownedByController: usable",
    "lastKnownLoadedTitle:", "audibleOutputVerified: false",
):
    assert needle in policy, f"Missing Media safety contract: {needle}"
for needle in (
    "property var snapshot: null", "property string pendingAction:",
    "property string errorText:", 'pendingAction === "snapshot"',
    "snapshot = payload.result;",
):
    assert needle in headless, f"Headless controller seam moved: {needle}"
for needle in (
    "readonly property var availablePlayers:",
    "readonly property var activePlayer:",
    "selectedBusName",
    "Mpris.players.values",
):
    assert needle in mpris, f"MPRIS adapter seam moved: {needle}"
assert "HeadlessMediaController {" in deck
assert "MprisPlaybackAdapter {" in deck
assert "Mediaplayer {}" in shell  # Nothing wired into shell for B4.
# No second controller, MPRIS write, process or playback command in the Hub.
for forbidden in (
    "HeadlessMediaController {", "MprisPlaybackAdapter {",
    "Process {", "FileView {", "mediaControllerSource.refresh(",
    "mediaControllerSource.transport(", "mprisPlayer.play(",
    "selectedMprisPlayer.play(", "selectedMprisPlayer.pause(",
    "selectedMprisPlayer.next(", "Quickshell.execDetached(",
):
    assert forbidden not in bridge, f"Hub must remain read-only: {forbidden}"
for forbidden in ("function play(", "function stop(", "function run(",
                  "function transport(", "function selectPlayer("):
    assert forbidden not in policy, f"Projection must not control media: {forbidden}"
for needle in (
    '"services/hub/ApolloHubMediaPolicy.js"',
    '"services/media/HeadlessMediaController.qml"',
    '"services/media/MprisPlaybackAdapter.qml"',
    '"tests/hub/test_apollo_hub_media_bridge.py"',
    '"tests/hub/test_apollo_hub_media_policy.cjs"',
    "python3 tests/hub/test_apollo_hub_media_bridge.py",
    "node tests/hub/test_apollo_hub_media_policy.cjs",
):
    assert needle in workflow, f"B4 CI missing: {needle}"
print("ApolloHub B4 Media shared bridge static contracts passed")
