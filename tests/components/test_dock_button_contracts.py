#!/usr/bin/env python3
"""Static contracts for the shared dock button and approved numeric grammar."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/DockButton.qml").read_text(encoding="utf-8")
GIT = (ROOT / "modules/Git.qml").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "components/Basicbutton.qml.template").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ("default property alias contentData: contentHost.data", "custom module artwork slot"),
    ("property bool open: false", "persistent open state"),
    ("property Item contentGlowSource: contentHost", "exact custom artwork glow source"),
    ("property color openFillColor: Colors.yellow", "canonical yellow open fill"),
    ("property color openForegroundColor: Colors.magenta", "canonical magenta open foreground"),
    ("property color openGlowColor: Colors.magenta", "canonical magenta open glow"),
    ("property real contentGlowOpenOpacity: 1.0", "Git content glow energy"),
    ("property real softGlowOpenOpacity: 0.86", "Git tight halo energy"),
    ("property real wideGlowOpenOpacity: 0.22", "Git front wash energy"),
    ("property real softGlowSpread: 3", "Git tight halo spread"),
    ("property real wideGlowSpread: 10", "Git wide wash spread"),
    ("signal leftClicked(var mouseEvent)", "left-click contract"),
    ("signal rightClicked(var mouseEvent)", "right-click contract"),
    ("signal wheel(var wheelEvent)", "wheel forwarding contract"),
    ("property real contentGlowHoverRadius: contentGlowActiveRadius", "per-state glow radius override"),
    ("property int contentGlowHoverSamples: contentGlowActiveSamples", "per-state glow sample override"),
    ("readonly property bool hovered:", "hover state contract"),
    ("readonly property bool pressed:", "pressed state contract"),
    ("id: contentLayer", "content and content glow must share the legacy Git stacking plane"),
    ("mapToItem(contentLayer, 0, 0)", "content glow geometry must be local to the content stacking plane"),
):
    require(COMPONENT, needle, message)

# Apollo Hub's centered, styled-calendar cluster is sampled once as a
# direct child. Its moving x/y must keep the glow in the same position.
HUB_DOCK = (ROOT / "modules/ApolloHub.qml").read_text(encoding="utf-8")
for needle in ("property bool trackArtworkGlowLocally: true",
               "readonly property bool artworkIsLocalSource:",
               "contentHost.x + dockButton.contentGlowSource.x",
               "contentHost.y + dockButton.contentGlowSource.y",
               "contentGlowSource.mapToItem(contentLayer, 0, 0)"):
    require(COMPONENT, needle, "optional local dock artwork tracking")
for needle in ("contentGlowSource: hubMark",
               "trackArtworkGlowLocally: true",
               'textFormat: Text.StyledText',
               "normalContentGlowColor: Colors.magenta"):
    require(HUB_DOCK, needle, "Apollo Hub single-cluster glow")

# Automatic direct-child placement must preserve the original fallback for
# whole-content, deeply nested, or reviewed special art. Do not make the
# effect sample its own host or drop source teardown protection.
assert "sourceAttached && dockButton.trackArtworkGlowLocally" in COMPONENT
assert "dockButton.contentGlowSource.parent === contentHost" in COMPONENT
assert "contentGlowSource.mapToItem(contentLayer, 0, 0)" in COMPONENT
assert "safeSource: dockButton.contentGlowSource" in COMPONENT
assert "requestedVisible: dockButton.contentGlowEnabled" in COMPONENT
require(QMLDIR, "DockButton 1.0 DockButton.qml", "component registration")
require(GIT, "DockButton {", "Git must prove the reusable component")
require(GIT, "open: menuOpen", "Git open state must drive the component")
require(GIT, "contentGlowSource: gitMark", "Git glow must stay attached to the exact mark")
require(GIT, "onLeftClicked:", "Git must use component left-click behavior")
assert "signal rightClicked" not in GIT, "Git must inherit DockButton right-click signal without redeclaring it"
assert "onRightClicked:" not in GIT, "Git must not recursively re-emit the inherited right-click signal"
require(TEMPLATE, "DockButton {", "future button template must use reusable component")
require(TEMPLATE, "contentGlowSource: templateText", "template must demonstrate exact content glow targeting")
require(COMPONENT, "z: 0\n\n        Item {\n            id: contentHost", "content layer must stay below the root-level front wash")

for forbidden in ("RectangularShadow {", "DropShadow {", "MouseArea {"):
    assert forbidden not in GIT, f"Git should not duplicate DockButton internals: {forbidden}"

print("Dock button contracts: PASS")


DOCK_MODULES = {
    "modules/Applauncher.qml": (
        "DockButton {",
        "implicitWidth: 65",
        "implicitHeight: 50",
        "normalForegroundColor: Colors.white",
        "normalDockGlowColor: Colors.cyan",
    ),
    "modules/Bluetooth.qml": (
        "DockButton {",
        "implicitWidth: 85",
        "implicitHeight: 50",
        "normalForegroundColor: Colors.white",
        "normalDockGlowColor: Colors.cyan",
    ),
    "modules/Calendar.qml": (
        "DockButton {",
        "implicitWidth: 113",
        "implicitHeight: 50",
        "radius: 7",
        "normalDockGlowColor: Colors.cyan",
    ),
    "modules/Clock.qml": (
        "DockButton {",
        "Math.ceil(clockRow.implicitWidth)",
        "implicitHeight: 50",
        "contentGlowEnabled: false",
        "clockArea.is24Hour ? Colors.orange : Colors.cyan",
    ),
    "modules/Cpu.qml": (
        "DockButton {",
        "implicitWidth: 70",
        "implicitHeight: 50",
        "open: menuOpen",
        "normalDockGlowColor: Colors.cyan",
    ),
    "modules/Git.qml": (
        "DockButton {",
        "implicitHeight: 50",
        "open: menuOpen",
    ),
    "modules/Hospital.qml": (
        "DockButton {",
        "implicitHeight: 50",
        "Math.max(72, hospitalMark.implicitWidth + 18)",
        "open: menuOpen",
        "normalDockGlowColor: Colors.magenta",
    ),
    "modules/Network.qml": (
        "DockButton {",
        "implicitHeight: 50",
        "root.implicitWidth + 8",
        "contentGlowEnabled: false",
        "normalDockGlowColor: root.networkGlowColor",
    ),
    "modules/NotificationsHub.qml": (
        "DockButton {",
        "implicitWidth: 130",
        "implicitHeight: 50",
        "open: menuOpen",
        "normalForegroundColor: Colors.white",
    ),
    "modules/Power.qml": (
        "DockButton {",
        "id: powerButton",
        "width: 50",
        "height: 50",
        "normalForegroundColor: Colors.white",
        "normalDockGlowColor: Colors.cyan",
        "wideGlowIdleOpacity: 0.0",
    ),
    "modules/Sessions.qml": (
        "DockButton {",
        "Math.max(65, Math.ceil(sessionsIcon.implicitWidth) + 16)",
        "implicitHeight: 50",
        "open: menuOpen",
        "normalDockGlowColor: Colors.omnitrix",
    ),
    "modules/Volumebar.qml": (
        "DockButton {",
        "implicitHeight: 50",
        "Math.max(130, Math.ceil(root.implicitWidth) + (contentEdgePadding * 2))",
        "contentGlowEnabled: false",
        "onWheel: function(wheelEvent)",
    ),
    "modules/Weather.qml": (
        "DockButton {",
        "implicitWidth: Math.ceil(weatherContent.implicitWidth) + 6",
        "implicitHeight: 50",
        "open: menuOpen",
        "normalForegroundColor: weatherColor",
        "normalDockGlowColor: weatherColor",
        "hoverDockGlowColor: Colors.orange",
        "pressedDockGlowColor: Colors.magenta",
        "contentGlowSource: weatherGlowArtwork",
        "openFillColor: Colors.yellow",
    ),
}

for path, needles in DOCK_MODULES.items():
    source = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        require(source, needle, f"DockButton migration contract for {path}")

# Social uses the operator's exact Unicode phone-and-stars mark. Only
# the ☎︎ core receives the interactive module color; the star ornaments
# stay white even when Social's standard open foreground becomes magenta.
# Keep a single sampled source instead of layering a recolored PNG on top.
social_module = (ROOT / "modules/Sessions.qml").read_text(encoding="utf-8")
for needle in (
    "NotoText {",
    "id: sessionsIcon",
    "anchors.centerIn: parent",
    "font.pixelSize: 22",
    "textFormat: Text.StyledText",
    "color: Colors.white",
    'text: "࣪˖<font color=\'" + sessionsDock.foregroundColor',
    '"+ "\'>☎︎</font>๋࣭✧"',
    "normalForegroundColor: Colors.omnitrix",
    "hoverForegroundColor: Colors.omnitrix",
    "pressedForegroundColor: Colors.omnitrix",
    "contentGlowSource: sessionsIcon",
    "onLeftClicked: {",
    "Qt.callLater(function () {",
    "sessionsDock.messagingWindow.menuOpen =",
):
    require(social_module, needle, "Social telephone dock identity")
assert "Sessions.png" not in social_module
assert "ColorOverlay {" not in social_module
assert "SafeDropShadow {" not in social_module
assert social_module.count("contentGlowSource: sessionsIcon") == 1
assert social_module.count("NotoText {") == 1

LEGACY_ROOT_MOUSE_IDS = (
    "appmenuMouse",
    "bluetoothDockMouse",
    "calendarMouse",
    "clockMouse",
    "cpuMouse",
    "networkDockMouse",
    "powerMouse",
    "sessionsMouse",
    "volumebarDockMouse",
    "weatherMouse",
)

for path in DOCK_MODULES:
    source = (ROOT / path).read_text(encoding="utf-8")
    for legacy_id in LEGACY_ROOT_MOUSE_IDS:
        assert f"id: {legacy_id}" not in source, (
            f"{path} reintroduced legacy root MouseArea {legacy_id}"
        )

# Composite containers are intentionally not a single DockButton:
# Workspaces owns many workspace buttons, Tray owns many tray-item buttons,
# Notifications.qml is the popup surface, and stub modules remain empty.
for path in (
    "modules/Workspaces.qml",
    "modules/Tray.qml",
    "modules/Notifications.qml",
):
    source = (ROOT / path).read_text(encoding="utf-8")
    assert "DockButton {" not in source, (
        f"{path} should not be flattened into one root DockButton"
    )

# Operator-selected dock defaults are distinct from mode/action/chassis defaults.
for needle in (
    "normalContentGlowColor: Colors.cyan",
    "hoverContentGlowColor: Colors.orange",
    "pressedContentGlowColor: Colors.magenta",
    "normalDockGlowColor: Colors.cyan",
    "hoverDockGlowColor: Colors.orange",
    "pressedDockGlowColor: Colors.magenta",
    "contentGlowIdleOpacity: 0.75",
    "contentGlowHoverOpacity: 0.95",
    "contentGlowActiveRadius: 14",
    "contentGlowActiveSamples: 15",
    "softGlowIdleOpacity: 0.40",
    "softGlowHoverOpacity: 0.50",
    "wideGlowIdleOpacity: 0.07",
):
    require(COMPONENT, needle, "operator-approved dock grammar")

for needle in (
    "normalContentGlowColor: Colors.orange",
    "hoverContentGlowColor: Colors.orange",
    "pressedContentGlowColor: Colors.orange",
    "normalDockGlowColor: Colors.yellow",
    "hoverDockGlowColor: Colors.yellow",
    "pressedDockGlowColor: Colors.yellow",
):
    require(GIT, needle, "Git keeps distinct semantic colors")

for name in ("Applauncher", "Bluetooth", "Calendar", "Cpu", "NotificationsHub"):
    source = (ROOT / f"modules/{name}.qml").read_text(encoding="utf-8")
    for state, color in (("normal", "cyan"), ("hover", "orange"), ("pressed", "magenta")):
        require(source, f"{state}ContentGlowColor: Colors.{color}", "default icon glow state")
        require(source, f"{state}DockGlowColor: Colors.{color}", "default chassis glow state")
    assert "contentGlowIdleOpacity:" not in source
    assert "contentGlowHoverOpacity:" not in source

network = (ROOT / "modules/Network.qml").read_text(encoding="utf-8")
# Restored source-local Qt layer effects preserve the original text geometry.
# Crucially only the shadow COLOR alpha varies, not the composite layer opacity.
assert network.count("layer.effect: DropShadow {") == 7
assert "SafeDropShadow {" not in network
assert "mapToItem(parent, 0, 0)" not in network
assert network.count("color: networkDock.sampledGlowColor") == 6
assert network.count("radius: networkDock.contentGlowRadius") == 6
assert network.count("samples: networkDock.contentGlowSamples") == 6
assert "opacity: networkDock.contentGlowOpacity" not in network
require(network, "root.networkGlowColor.a * networkDock.contentGlowOpacity", "shadow-only alpha")
require(network, "source: networkIconRow", "historical icon layer")
for target in ("networkOpen", "networkText", "networkClose", "networkSignalText", "networkSpeedText"):
    require(network, f"id: {target}", "original network glyph source")
assert "readonly property real contentGlowRadius:" in COMPONENT
assert "readonly property int contentGlowSamples:" in COMPONENT
power = (ROOT / "modules/Power.qml").read_text(encoding="utf-8")
require(power, "softGlowSpread: 1", "Power historical design exception")
# Two visually parallel destructive confirmations share hover illumination.
# This is a cosmetic parity check only; their separate command/cancel wiring
# and the historical top-level Power recipe must remain unchanged.
require(
    power,
    "opacity: confirmshutdownMouse.pressed ? 0.55 : confirmshutdownMouse.containsMouse ? 0.55 : 0",
    "Shutdown confirmation hover glow",
)
require(
    power,
    "opacity: confirmrebootMouse.pressed ? 0.55 : confirmrebootMouse.containsMouse ? 0.55 : 0",
    "Reboot confirmation hover glow parity",
)
for command, action in (
    ('command: ["systemctl", "reboot"]', "rebootProcess.running = true"),
    ('command: ["systemctl", "poweroff"]', "shutdownProcess.running = true"),
    ('command: ["swaylock"]', "lockProcess.running = true"),
    ('command: ["swaymsg", "exit"]', "logoutProcess.running = true"),
):
    require(power, command, "Power action command unchanged")
    require(power, action, "Power action trigger unchanged")
require(power, "confirmShutdown = false;", "Shutdown cancel pathway retained")
require(power, "confirmReboot = false;", "Reboot cancel pathway retained")
require(power, "contentGlowIdleOpacity: 0.30", "Power historical content intensity")
require(power, "contentGlowIdleRadius: 19", "Power historical glow geometry")
require(power, "softGlowSpread: 1", "Power historical perimeter recipe")
require(power, "wideGlowIdleOpacity: 0.0", "Power historical absence of idle front wash")

# Power confirmation overlays keep exclusive keyboard focus; never allow
# Return/arrow keys to act on the hidden normal menu. Escape cancels only the
# confirmation and restores the normal menu (not a power action).
confirm_guard = power.index("if (confirmShutdown || confirmReboot) {")
menu_guard = power.index("if (!menuOpen)", confirm_guard)
normal_escape = power.index("if (event.key === Qt.Key_Escape)", menu_guard)
assert confirm_guard < menu_guard < normal_escape, "Confirmation must preempt normal key handling"
confirmation_keys = power[confirm_guard:menu_guard]
for needle in (
    "if (event.key === Qt.Key_Escape)",
    "confirmShutdown = false;",
    "confirmReboot = false;",
    "menuOpen = true;",
    "event.accepted = true;",
    "return;",
):
    assert needle in confirmation_keys, ("Power confirmation keyboard isolation", needle)
assert "Process.running" not in confirmation_keys
assert "lockProcess.running" not in confirmation_keys
assert "logoutProcess.running" not in confirmation_keys
assert "shutdownProcess.running" not in confirmation_keys
assert "rebootProcess.running" not in confirmation_keys
for keyword in ("Qt.Key_Up", "Qt.Key_Down", "Qt.Key_Return", "Qt.Key_Enter"):
    assert keyword not in confirmation_keys, "Destructive confirmation must not bind hidden-menu keys"


hospital = (ROOT / "modules/Hospital.qml").read_text(encoding="utf-8")
assert hospital.count("color: dock.foregroundColor") == 3, (
    "Hospital heartbeats must follow the center glyph foreground/open-state identity"
)
assert "color: Colors.white" not in hospital
for path in ("modules/Clock.qml", "modules/Volumebar.qml"):
    source = (ROOT / path).read_text(encoding="utf-8")
    require(source, "contentGlowEnabled: false", "instrument per-cluster glow retained")
    require(source, "0.75", "instrument idle content energy")
    require(source, "0.95", "instrument hover content energy")
