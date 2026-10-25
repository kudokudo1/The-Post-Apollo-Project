#!/usr/bin/env python3
"""Static Syntagma API contracts for the shared NeonScrollBar.

This intentionally supplements (not replaces) the legacy consumer-preservation
contract. Runtime pointer, keyboard and rendering checks remain mandatory.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")


def expect(needle: str, purpose: str) -> None:
    assert needle in SOURCE, f"{purpose}: missing {needle!r}"


CONTRACT = {
    # Configuration // 001–004, 014, 016–017
    "property int orientation: Qt.Vertical": "shared vertical default",
    'property string placement: "auto"': "orientation-specific edge placement",
    'property int edgeInset: 4': "4px edge gap",
    'property string geometryMode: "box"': "box-side alignment is default",
    'property Item geometryHost: null': "explicit owner for special box geometry",
    'property int boxTopInset: 2': "small top box endpoint gap",
    'property int boxBottomInset: 2': "small bottom box endpoint gap",
    'function boxUsableBounds()': "header/footer bounded track",
    'flickable.mapToItem(host, 0, 0)': "measure pane within box",
    'item === flickable || item === root': "skip target and scrollbar in sibling census",
    'boxSideGeometry ? Math.max(0, boxEnd - boxStart)': "box track spans usable side",
    'geometryMode !== "viewport"': "explicit viewport compatibility path",
    'trackTopExtension <= 0': "preserve protruding specialty rails",
    'property bool hostIsScrollingContent:': "detect nested scrolling content hosts",
    'effectiveGeometryHost.parent.contentItem === effectiveGeometryHost':
        "prevent rail anchoring to a parent Flickable's virtual content area",
    'property int topInset: 5': "legacy viewport upper endpoint",
    'property int bottomInset: 5': "5px lower endpoint",
    'property int leftInset: 5': "horizontal start inset",
    'property int rightEndInset: 5': "horizontal end inset",
    'property bool reserveSpace: true': "reservation contract",
    'readonly property real reservedExtent:': "host reservation API",
    'property bool reserveGlowSpace: false': "glow reservation is independent and opt-in",
    'property bool viewportHasEndpointClearance: false':
        "host can avoid duplicate endpoint gaps",
    'effectiveTopInset: viewportHasEndpointClearance ? 0 : topInset':
        "host endpoint inset resolution",
    'starStyle ? starAreaWidth : barAreaWidth': "physical width remains 10/16 by default",
    'reserveGlowSpace ? 2 * effectiveGlowPadding : 0': "optional host-only glow clearance",
    'property bool containGlow: true': "contained glow",
    'clip: containGlow && trackTopExtension <= 0':
        "preserve intentional rail extensions outside the normal track bounds",
    # Availability / reveal // 005–011, 023
    'Math.min(trackLength, Math.max(minimumHandleHeight, proportional))':
        "short bar handles shrink rather than protrude",
    'Math.min(trackLength,': "short star handles shrink rather than protrude",
    'property bool autoHide: true': "legacy auto-hide compatibility",
    'property string visibilityMode: ""': "explicit visibility policies",
    'property string revealMode: "combined"': "combined reveal default",
    'property int fadeDuration: 500': "shared hold/fade timing",
    'property real inactiveOpacity: 0.34': "shared unavailable intensity",
    'visibilityMode !== "" && !scrollable': "explicit persistent-only root fade",
    'effectiveVisibilityMode === "persistent"': "persistent mode distinguish legacy state",
    'function synchronizeReveal()': "cancelable reveal lifecycle",
    'holdTimer.restart()': "hold before fading",
    'fadeTimer.restart()': "fade completion",
    'onRevealTriggerActiveChanged: synchronizeReveal()': "combined trigger response",
    'parent: root.flickable': "pane-scoped hover reveal",
    'function noteScrollActivity()': "scroll reveal",
    'readonly property bool focusWithinPane:': "focus reveal",
    'Window.activeFocusItem': "QtQuick native active-focus property",
    'function keyboardOwnedByTextInput()': "do not hijack editable text inputs",
    'function handleFocusedPaneKey(event)': "host routes keys for focused pane",
    'Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier':
        "preserve existing shortcuts",
    # Interaction // 012–013, 015, 018–022
    'property string interactionStyle: "progressive"': "progressive glow default",
    'property real barGlowPressedOpacity: -1': "pressed glow is derived by default",
    'property real starGlowPressedOpacity: -1': "star pressed glow is derived",
    'function progressivePressedValue(idleValue, hoverValue)': "preserve per-consumer glow identity",
    'root.effectiveBarPressedOpacity': "bar uses derived pressed recipe",
    'root.effectiveStarPressedOpacity': "star uses derived pressed recipe",
    'property string trackClickMode: "jump"': "click-to-jump default",
    'root.trackClickMode === "page"': "rare page-step variant",
    'readonly property bool handleHovered:': "handle-only hover",
    'handleMouse.mouseX >= handleLoader.x': "handle X hit zone",
    'handleMouse.mouseY >= handleLoader.y': "handle Y hit zone",
    'property string nestedScrollMode: "contain"': "operator-selected stop-at-end default",
    'readonly property bool scrollChaining: nestedScrollMode === "chain"':
        "optional explicit chain variant",
    'property bool captureNestedPaneWheel: true': "nested wheel interception enabled",
    'enabled: root.captureNestedPaneWheel && root.nestedPaneDetected':
        "intercept only real nested pane surfaces",
    'blocking: true': "whole-inner-pane boundary containment",
    'event.accepted = true;': "contain wheel even at the inner boundary",
    'property var chainFlickable: null': "explicit outer ownership",
    'chainFlickable[axis] = clamp(outerBefore + remainder, 0, outerMax)':
        "boundary-only outer handoff",
    'property string horizontalWheelMode: "convert"': "wheel-conversion default",
    'property bool reverseWheelDirection: false': "reversible wheel input",
    'Application.styleHints.wheelScrollLines': "system sensitivity",
    'property bool keyboardEnabled: true': "keyboard input",
    'Keys.onPressed: function(event)': "focused scrollbar keyboard support",
    'function handleKey(key, modifiers)': "focus-owner integration API",
}
for snippet, meaning in CONTRACT.items():
    expect(snippet, meaning)

# A detached/reparented HoverHandler must not throw when the visibility
# binding reevaluates while its target or pointer handlers are null.
for needle in (
    "paneHover ? paneHover.hovered : false",
    "handleMouse ? handleMouse.containsMouse : false",
    "handleMouse ? handleMouse.pressed : false",
):
    expect(needle, "null-safe hover/reveal trigger lifecycle")

# The rail may be interactive, but only the handle activates the hover glow.
assert "handleMouse.containsMouse\n                    ?" not in SOURCE, (
    "full-root hover still directly drives an individual handle glow"
)

# Audit 04: the legacy 33px rail extension must not be cut off by root clipping.
assert 'clip: containGlow && trackTopExtension <= 0' in SOURCE

# Physical widths must never be inflated by glow or host reservation.
physical = SOURCE.split('readonly property real crossExtent:', 1)[1].split('readonly property real reservedExtent:', 1)[0]
assert 'effectiveGlowPadding' not in physical, 'physical scrollbar width was inflated by glow padding'
assert 'starAreaWidth' in physical and 'barAreaWidth' in physical

# Keep the existing extension interfaces intact.
for preserved in (
    "property Component railDecoration: null",
    'property string handleStyle: "bar"',
    'property string handleGlowStyle: "rectangular"',
    "property int wheelStep: 42",
    "property bool preserveDragOffset: false",
    "property bool clickToJump: true",
    "property alias railItem: rail",
    "property alias handleItem: handleLoader",
):
    expect(preserved, "legacy compatibility")

print("Neon scrollbar Syntagma API contracts: PASS")
