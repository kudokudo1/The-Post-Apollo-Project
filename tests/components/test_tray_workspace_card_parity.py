#!/usr/bin/env python3
"""Verify actual Workspace card geometry and glow construction in the tray.

This reads BOTH QML files and checks the source implementation. It never
launches Quickshell, changes native menus, or touches a running compositor.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
workspace = (ROOT / "modules/Workspaces.qml").read_text(encoding="utf-8")
tray = (ROOT / "modules/Tray.qml").read_text(encoding="utf-8")


def block(source: str, ident: str) -> str:
    """Get the complete QML object containing a unique id, honoring braces."""
    matches = list(re.finditer(
        rf"(?m)^\\s*id:\\s*{re.escape(ident)}\\s*$", source))
    assert len(matches) == 1, (ident, "expected exactly one owner")
    position = matches[0].start()
    start = source.rfind("{", 0, position)
    assert start != -1, ident
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError((ident, "unbalanced braces"))


def has(block_text: str, key: str, expression: str) -> None:
    pattern = rf"(?m)^\s*{re.escape(key)}:\s*{re.escape(expression)}\s*$"
    assert re.search(pattern, block_text), (key, expression)


def check_workspace_parity(workspace_id, tray_id, properties):
    reference = block(workspace, workspace_id)
    implementation = block(tray, tray_id)
    for name, value in properties:
        has(reference, name, value)
        has(implementation, name, value)
    return reference, implementation


assert "implicitWidth: visible ? 25 : 0" in workspace
assert "implicitWidth: 25" in tray
assert "implicitHeight: 42" in workspace
assert "implicitHeight: 42" in tray
assert 'color: "transparent"' in block(tray, "trayButton")

# The real active background matches Workspace, including the transparent
# inactive state. Only the source of the active predicate differs:
# focused workspace versus hovered/open native application menu.
w_active, t_active = check_workspace_parity(
    "workspacesIsActiveButtonBackground", "trayActiveButtonBackground",
    [("width", "parent.width"), ("height", "parent.height"),
     ("clip", "false"), ("z", "0"), ("opacity", "0.7")])
assert 'workspacesWorkspaceButton.isActive ? Colors.dark : "transparent"' in w_active
assert 'trayButton.cardEmphasized ? Colors.dark : "transparent"' in t_active

# The oversized backdrop must be INVISIBLE in both source files. It is a
# dedicated effect source, NOT a permanently dark, colored-border mini card.
w_back, t_back = check_workspace_parity(
    "workspacesButtonBackground", "trayButtonBackground",
    [("width", "parent.width + 6"), ("height", "parent.height + 5"),
     ("clip", "false"), ("z", "-1"), ("color", "Colors.dark"),
     ("opacity", "0.0")])
assert "border." not in t_back
assert "opacity: 0.68" not in tray

w_shadow = workspace.split("safeSource: workspacesButtonBackground", 1)[1]
t_shadow = block(tray, "trayButtonBackgroundGlow")
for name, value in [
    ("z", "-1"), ("horizontalOffset", "0"), ("verticalOffset", "0"),
    ("radius", "20"), ("samples", "21")]:
    assert re.search(rf"(?m)^\s*{name}: {re.escape(value)}$", w_shadow)
    has(t_shadow, name, value)
assert "workspacesWorkspaceButton.isActive ? 0.2 : 0.0" in w_shadow
assert "trayButton.cardEmphasized ? 0.2 : 0.0" in t_shadow
assert "safeSource: trayButtonBackground" in t_shadow

# Keep image and text-specific source samplers distinct, but retain exactly
# the same glow radius, sampling, alignment and hover/press energy.
for workspace_id, tray_id in (
    ("workspacesTextGlow", "trayIconGlow"),
    ("workspacesActiveTextGlow", "trayActiveIconGlow"),
):
    a, b = check_workspace_parity(
        workspace_id, tray_id,
        [("horizontalOffset", "0"), ("verticalOffset", "0"),
         ("radius", "14"), ("samples", "15"), ("z", "2"),
         ("transparentBorder", "true")])
    assert "safeSource: workspacesText" in a
    assert "safeSource: trayIcon" in b
    assert "workspacesButtonMouse.pressed ? 1.0" in a
    assert "trayButtonMouse.pressed ? 1.0" in b
    assert "workspacesButtonMouse.containsMouse ? 0.95" in a
    assert "trayButtonMouse.containsMouse ? 0.95" in b

# The tray still uses app-provided artwork, real app menus and the same
# cyan/hover-orange/menu-magenta states; it does not adopt Sway processes.
assert "source: trayButton.modelData.icon" in tray
assert "model: SystemTray.items" in tray
assert "menu: trayButton.modelData.menu" in tray
assert "onOpened: trayDock.openMenuAnchor = trayNativeMenu" in tray
assert 'trayNativeMenu.visible ? Colors.magenta' in tray
assert "trayButtonMouse.containsMouse" in tray
assert "SocialTrayBridge.requestDiscordActivation();" in tray
assert "trayButton.modelData.activate();" in tray
assert "Process {" not in tray
print("Tray ↔ Workspace exact card geometry, backing and dual sampled glows: PASS")
