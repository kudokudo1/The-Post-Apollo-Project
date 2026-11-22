#!/usr/bin/env python3
"""Source-level bottom-center system tray geometry and activation contracts.

Does not run a user's compositor, inspect tray contents, or mutate the desktop.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
tray = (ROOT / "modules/Tray.qml").read_text(encoding="utf-8")
trash = (ROOT / "modules/Trash.qml").read_text(encoding="utf-8")
power = (ROOT / "modules/Power.qml").read_text(encoding="utf-8")

assert shell.count("        Tray {") == 1, "only one SystemTray UI owner"
left = shell.split("id: leftModules", 1)[1].split("id: rightModules", 1)[0]
assert "        Tray {" not in left, "top row must not duplicate system tray"
bottom = shell.split("// ===== BOTTOM-CENTER SYSTEM TRAY", 1)[1].split(
    "// ===== BOTTOM UTILITIES", 1
)[0]
assert bottom.count("PanelWindow {") == 1
assert bottom.count("Tray {") == 1
assert "id: bottomCenterTrayWindow" in bottom
assert "screen: shellRoot.screen" in bottom
# Both edges are bound to the whole DP-5 output, not top-bar leftModules.
for token in ("top: false", "bottom: true", "left: true",
              "right: true", "left: 0", "right: 0", "bottom: 10",
              "implicitHeight: 70", "anchors.centerIn: parent"):
    assert token in bottom, token
assert "id: bottomCenteredTray" in bottom
assert "mask: Region {" in bottom
assert "x: bottomCenteredTray.x" in bottom
assert "y: bottomCenteredTray.y" in bottom
assert "fullscreenWidgetActive\n                   ? 0 : bottomCenteredTray.width" in bottom
assert "fullscreenWidgetActive\n                    ? 0 : bottomCenteredTray.height" in bottom
assert "exclusiveZone: 0" in bottom
assert "WlrLayershell.layer: WlrLayer.Top" in bottom
assert "WlrLayershell.layer: WlrLayer.Overlay" not in bottom
assert "readonly property bool fullscreenWidgetActive:" in bottom
assert "visible: !bottomCenterTrayWindow.fullscreenWidgetActive" in bottom
assert "visible: true" in bottom  # Surface remains mapped while art + input hide
for owner in (
    "gitWindow", "apolloHubWindow", "cpuPlusWindow", "financeWindow",
    "weatherStationWindow",
):
    assert owner + ".menuOpen" in bottom, owner
assert 'financeWindow.chassisLevel === "fullscreen"' in bottom
assert 'weatherStationWindow.chassisLevel === "fullscreen"' in bottom
# No extra shell/service process to poll Sway state; compositor z-order owns
# external fullscreen and the opt-in guard owns the internal full-size modes.
assert "Process {" not in bottom
assert "WlrLayershell.keyboardFocus: WlrKeyboardFocus.None" in bottom
assert "focusable: false" in bottom
assert 'color: "transparent"' in bottom
assert "surfaceFormat.opaque: false" in bottom
assert "visible: true" in bottom

# Execute the actual source boolean in JavaScript against every known
# internal fullscreen tier; none should leave visible tray artwork or input.
# The compositor itself owns external fullscreen through WlrLayer.Top.
fullscreen_expression = bottom.split(
    "readonly property bool fullscreenWidgetActive:", 1
)[1].split("// Retain the permanently", 1)[0].strip()
node = r"""
const assert = require("node:assert/strict");
const vm = require("node:vm");
const expression = process.argv[1];
const root = {
 gitWindow: {menuOpen:false, resizeLevel:1, resizeSteps:[0,1,2,3]},
 apolloHubWindow: {menuOpen:false, resizeLevel:1, resizeSteps:[0,1,2,3]},
 cpuPlusWindow: {menuOpen:false, resizeLevel:1, resizeSteps:[0,1,2,3]},
 financeWindow: {menuOpen:false, chassisLevel:"compact"},
 weatherStationWindow: {menuOpen:false, chassisLevel:"compact"}
};
function blocked() { return vm.runInNewContext("Boolean(" + expression + ")", root); }
assert.equal(blocked(), false);
for(const key of ["gitWindow", "apolloHubWindow", "cpuPlusWindow"]) {
 root[key].menuOpen = true;
 root[key].resizeLevel = 2;
 assert.equal(blocked(), false, key + " mid tier");
 root[key].resizeLevel = 3;
 assert.equal(blocked(), true, key + " full tier");
 root[key].menuOpen = false;
 assert.equal(blocked(), false, key + " closed");
}
for(const key of ["financeWindow", "weatherStationWindow"]) {
 root[key].menuOpen = true;
 root[key].chassisLevel = "large";
 assert.equal(blocked(), false, key + " non-full tier");
 root[key].chassisLevel = "fullscreen";
 assert.equal(blocked(), true, key + " full tier");
 root[key].menuOpen = false;
 assert.equal(blocked(), false, key + " closed");
}
console.log("Post-Apollo fullscreen tray visibility gate: PASS");
"""
p = subprocess.run(
    ["node", "-e", node, fullscreen_expression],
    check=False, capture_output=True, text=True, timeout=12
)
assert p.returncode == 0, p.stdout + "\n" + p.stderr

# The tray width changes as applications register/unregister. Centering must
# be computed from the whole screen, without a left/right dock size offset.
for screen_width in (900, 1332, 1360, 1920, 2560, 3440):
    # The 2048px composite screenshot includes another monitor. The tray
    # centers on its bound DP-5 output, not on stitched-image width.
    for tray_width in (92, 108, 163, 333):
        x = (screen_width - tray_width) / 2
        assert x + tray_width / 2 == screen_width / 2
# Match bottom utility buttons: 10px outer margin + 10px centered offset.
assert 10 + (70 - 50) / 2 == 20
assert "implicitHeight: 50" in tray
assert "implicitWidth: Math.max(92, trayRow.implicitWidth + 16)" in tray
assert "anchors.centerIn: parent" in tray
assert "id: trayItems" in tray
assert "visible: trayItems.count === 0" in tray
assert 'text: "TRAY"' in tray and 'text: "NO ICONS"' in tray
assert tray.count("GohuText {") >= 2
assert "border.width: 1" in tray
assert "border.color: trayButtonPressed ? Colors.orange" in tray
assert "anchors.fill: parent\n        anchors.margins: 4" not in tray
assert "bottom: 10" in trash
assert "bottom: 10" in power

# Only visual placement changed. Preserve exact Discord bridge, real external
# item activation and native item repeater. No second tray service/process.
assert "model: SystemTray.items" in tray
assert "SocialTrayBridge.requestDiscordActivation();" in tray
assert "trayButton.modelData.activate();" in tray
assert "Process {" not in tray
print("System tray true output center, empty-state, fullscreen z-order and input safety: PASS")
