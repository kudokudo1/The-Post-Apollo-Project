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
        "implicitWidth: 151",
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
        "implicitWidth: 25",
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
        "implicitWidth: 90",
        "implicitHeight: 50",
        "open: menuOpen",
        "normalForegroundColor: Colors.orange",
        "normalDockGlowColor: Colors.orange",
    ),
}

for path, needles in DOCK_MODULES.items():
    source = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        require(source, needle, f"DockButton migration contract for {path}")

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
require(network, "networkDock.pressed ? 0.6 : networkDock.hovered ? 0.8 : 1.0", "Wi-Fi historical exception preserved")
power = (ROOT / "modules/Power.qml").read_text(encoding="utf-8")
require(power, "softGlowSpread: 1", "Power historical design exception")
hospital = (ROOT / "modules/Hospital.qml").read_text(encoding="utf-8")
assert hospital.count("color: Colors.white") >= 2
for path in ("modules/Clock.qml", "modules/Volumebar.qml"):
    source = (ROOT / path).read_text(encoding="utf-8")
    require(source, "contentGlowEnabled: false", "instrument per-cluster glow retained")
    require(source, "0.75", "instrument idle content energy")
    require(source, "0.95", "instrument hover content energy")
