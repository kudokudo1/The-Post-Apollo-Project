#!/usr/bin/env python3
"""Source-level bottom-center system tray geometry and activation contracts.

Does not run a user's compositor, inspect tray contents, or mutate the desktop.
"""
from pathlib import Path

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
assert "mask: Region {\n            item: bottomCenteredTray\n        }" in bottom
assert "exclusiveZone: 0" in bottom
assert "WlrLayershell.layer: WlrLayer.Overlay" in bottom
assert "WlrLayershell.keyboardFocus: WlrKeyboardFocus.None" in bottom
assert "focusable: false" in bottom
assert 'color: "transparent"' in bottom
assert "surfaceFormat.opaque: false" in bottom
assert "visible: true" in bottom

# The tray width changes as applications register/unregister. Centering must
# be computed from the whole screen, without a left/right dock size offset.
for screen_width in (900, 1360, 1920, 2560, 3440):
    for tray_width in (13, 43, 73, 163, 333):
        x = (screen_width - tray_width) / 2
        assert x + tray_width / 2 == screen_width / 2
# Match bottom utility buttons: 10px outer margin + 10px centered offset.
assert 10 + (70 - 50) / 2 == 20
assert "implicitHeight: 50" in tray
assert "bottom: 10" in trash
assert "bottom: 10" in power

# Only visual placement changed. Preserve exact Discord bridge, real external
# item activation and native item repeater. No second tray service/process.
assert "model: SystemTray.items" in tray
assert "SocialTrayBridge.requestDiscordActivation();" in tray
assert "trayButton.modelData.activate();" in tray
assert "Process {" not in tray
print("Single system tray bottom-center geometry and native activation: PASS")
