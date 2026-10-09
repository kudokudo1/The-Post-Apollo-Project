#!/usr/bin/env python3
"""Static contracts for notification panel geometry and neon effect rendering."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HUB = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text(encoding="utf-8")
POPUP = (ROOT / "modules/Notifications.qml").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


# Full notification hub uses the shared window chassis and keeps the glow
# inside the existing 8px native-window gutter.
for needle, message in (
    ("property int frameInset: 8", "hub frame gutter"),
    ("property int frameCloseGlowSpread: 6", "hub close glow spread"),
    ("property real frameCloseGlowOpacity: 0.46", "hub close glow strength"),
    ("property int frameWideGlowSpread: 8", "hub wide glow spread"),
    ("property real frameWideGlowOpacity: 0.16", "hub wide glow strength"),
    ("WindowPanelFrame {\n            id: frame", "shared hub chassis"),
    ("fillColor: Colors.black\n            fillOpacity: root.backgroundOpacity", "hub glass fill"),
    ("borderWidth: 2\n            borderColor: Colors.orange", "hub orange frame"),
):
    require(HUB, needle, message)

assert "id: frameGlowSource" not in HUB
assert "frameGlowRadius" not in HUB

# Each history card reserves enough vertical space for its 12px wide bloom,
# even though the ListView itself intentionally remains clipped.
for needle, message in (
    ("property int cardGlowVerticalGutter: 12", "card vertical glow gutter"),
    ("property int cardCloseGlowSpread: 4", "card close glow spread"),
    ("property real cardCloseGlowOpacity: 0.50", "card close glow strength"),
    ("property int cardWideGlowSpread: 12", "card wide glow spread"),
    ("property real cardWideGlowOpacity: 0.14", "card wide glow strength"),
    ("+ (root.cardGlowVerticalGutter * 2)", "delegate reserves both glow gutters"),
    ("topMargin: root.cardGlowVerticalGutter", "card sits inside reserved top gutter"),
    ("WindowPanelFrame {\n                            id: card", "history card shared chassis"),
    ("glowColor: notificationEntry.notificationColor", "semantic card glow color"),
):
    require(HUB, needle, message)

assert "id: cardGlowSource" not in HUB
assert "cardGlowRadius" not in HUB
require(HUB, "clip: true", "history viewport clipping stays enabled")

# Transient popup: preserve the visible 420x150 card and 20px right placement,
# but move its top edge to exactly 2px and reserve side/bottom glow space.
for needle, message in (
    ("implicitWidth: 444", "popup glow-host width"),
    ("implicitHeight: 164", "popup glow-host height"),
    ("top: 0", "popup native top margin"),
    ("right: 8", "popup native right margin"),
    ("topMargin: 2", "visible card two-pixel top placement"),
    ("leftMargin: 12", "popup left glow gutter"),
    ("rightMargin: 12", "popup right glow gutter"),
    ("height: 150", "visible popup card height"),
    ("WindowPanelFrame {\n                id: notificationCard", "popup shared chassis"),
    ("closeGlowSpread: 4\n                closeGlowOpacity: 0.55", "popup close glow"),
    ("wideGlowSpread: 12\n                wideGlowOpacity: 0.14", "popup wide glow"),
):
    require(POPUP, needle, message)

assert "RectangularShadow {" not in POPUP

print("Notification visual contracts: PASS")
