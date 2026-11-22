#!/usr/bin/env python3
"""Operator-approved orange preview / magenta activation source contract.

The real buttons, not an unrelated yellow outline, own sampled glyph glows.
This is source evidence; live Qt pointer delivery and animation are separate.
"""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
button=(root/"components/ActionButton.qml").read_text(encoding="utf-8")
mode=(root/"components/ModeButton.qml").read_text(encoding="utf-8")
navigator=(root/"components/WidgetContentKeyboardNavigator.qml").read_text(encoding="utf-8")
fixtures=(root/"tests/navigation/fixtures/WidgetContentKeyboardNative.qml").read_text(encoding="utf-8")

for token in (
    "property bool contentKeyboardPrimary: false",
    "property bool contentKeyboardNavigationActive: false",
    "property var contentNavigator: null",
    "(keyboardSelected || contentKeyboardPrimary) && !selected",
    "contentKeyboardNavigationActive && hovered",
    "&& !contentKeyboardPrimary && !keyboardSelected",
    "property color secondaryHoverFillColor: idleFillColor",
    "pointerSecondaryHovered ? secondaryHoverFillColor : hoverFillColor",
    "keyboardSelectedForegroundColor: hoverForegroundColor",
    "keyboardSelectedBorderColor: Colors.orange",
    "keyboardSelectedContentGlowColor: Colors.orange",
    "selectedForegroundColor: Colors.magenta",
    "selectedBorderColor: Colors.magenta",
    "selectedContentGlowColor: Colors.magenta",
    "selectedSoftGlowColor: Colors.magenta",
    "selectedWideGlowColor:",
    "selectedSoftGlowColor",
):
    assert token in button, token

# Activation belongs to selected (actual owner state), not keyboard focus.
assert button.count(": cursorPrimaryNotActivated\n") == 10
assert ": keyboardSelected\n" not in button
assert "readonly property bool hovered:" in button
assert "mouse.containsMouse" in button
assert "readonly property bool pressed:" in button
assert "interactive && mouse.pressed" in button
mouse_move=button.split("onPositionChanged: function(mouseEvent) {",1)[1].split("\n        }",1)[0]
assert "nav.followPointer(actionButton)" in mouse_move
hover_enter=button.split("onEntered: {",1)[1].split("\n        }",1)[0]
assert "followPointer" not in hover_enter

for token in (
    "readonly property bool secondaryHovered:",
    "keyboardActive && pointerInside && !keyboardSelected",
    "primaryHovered ? hoveredFillColor",
    "selected ? selectedPrimaryColor",
    "selected ? selectedFillColor",
    "selected ? selectedPrimaryColor : hoverPrimaryColor",
    "color: modeButton.perimeterGlowColor",
    "onPositionChanged: modeButton.pointerMoved()",
):
    assert token in mode, token

for token in (
    "property bool keyboardPrimaryActive: false",
    "property var registeredControls: []",
    "function clearContentFlags(item)",
    "function synchronizeButtonCursor(controls)",
    "function followPointer(item)",
    "keyboardPrimaryActive=false;",
    "item.contentKeyboardNavigationActive=keyboardPrimaryActive",
    "item.contentKeyboardPrimary=keyboardPrimaryActive",
    "typeof navigator.selectedItem.contentKeyboardPrimary",
    "function reset()",
    "if(!navigationActive) reset();",
    "node.destructive !== true",
    'kind!=="leftClicked" && kind!=="triggered"',
):
    assert token in navigator, token
assert "border.color: Colors.yellow" not in navigator
assert "color: Colors.magenta\n        }" not in navigator
assert "? Colors.magenta : Colors.orange" in navigator
assert "MouseArea {" not in navigator and "Keys.onPressed" not in navigator
assert "second.contentKeyboardPrimary" in fixtures
assert "localKeys.followPointer(second)" in fixtures

# Specialized universal red X and orange/purple resize controls retain their
# operator-approved visual identity rather than inheriting generic palettes.
close=(root/"components/CloseButton.qml").read_text(encoding="utf-8")
resize=(root/"components/ResizeButton.qml").read_text(encoding="utf-8")
assert "hoverBorderColor: Colors.red" in close
assert "hoverForegroundColor: Colors.red" in close
assert "hoverBorderColor: accentColor" in resize
assert "hoverForegroundColor: accentColor" in resize

print("Unified hover / actual activation contracts: PASS")
