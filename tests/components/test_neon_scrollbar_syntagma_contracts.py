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
    'property int topInset: 5': "5px upper endpoint",
    'property int bottomInset: 5': "5px lower endpoint",
    'property int leftInset: 5': "horizontal start inset",
    'property int rightEndInset: 5': "horizontal end inset",
    'property bool reserveSpace: true': "reservation contract",
    'readonly property real reservedExtent:': "host reservation API",
    'property bool reserveGlowSpace: false': "glow reservation is independent and opt-in",
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
    'function synchronizeReveal()': "cancelable reveal lifecycle",
    'holdTimer.restart()': "hold before fading",
    'fadeTimer.restart()': "fade completion",
    'onRevealTriggerActiveChanged: synchronizeReveal()': "combined trigger response",
    'parent: root.flickable': "pane-scoped hover reveal",
    'function noteScrollActivity()': "scroll reveal",
    'readonly property bool focusWithinPane:': "focus reveal",
    # Interaction // 012–013, 015, 018–022
    'property string interactionStyle: "progressive"': "progressive glow default",
    'property real barGlowPressedOpacity: 0.76': "pressed glow level",
    'property real starGlowPressedOpacity: 0.86': "star pressed glow",
    'property string trackClickMode: "jump"': "click-to-jump default",
    'root.trackClickMode === "page"': "rare page-step variant",
    'readonly property bool handleHovered:': "handle-only hover",
    'handleMouse.mouseX >= handleLoader.x': "handle X hit zone",
    'handleMouse.mouseY >= handleLoader.y': "handle Y hit zone",
    'property bool scrollChaining: true': "inner-first chaining",
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
