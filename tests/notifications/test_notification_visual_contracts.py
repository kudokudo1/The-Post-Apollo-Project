#!/usr/bin/env python3
"""Static contracts for notification panel geometry and neon effect rendering."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HUB = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text(encoding="utf-8")
POPUP = (ROOT / "modules/Notifications.qml").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


# Full notification hub keeps the shared surface chassis, but sources its
# glow from the orange border so translucent glass does not turn orange.
for needle, message in (
    ("property int frameInset: 8", "hub frame gutter"),
    ("property int frameCloseGlowRadius: 6", "hub close glow radius"),
    ("property real frameCloseGlowOpacity: 0.58", "hub close glow strength"),
    ("property int frameWideGlowRadius: 8", "hub wide glow radius"),
    ("property real frameWideGlowOpacity: 0.16", "hub wide glow strength"),
    ("Rectangle {\n            id: frameGlowSource", "hub border-only glow source"),
    ("safeSource: frameGlowSource", "hub border glow source wiring"),
    ("WindowPanelFrame {\n            id: frame", "shared hub chassis"),
    ("fillColor: Colors.black\n            fillOpacity: root.backgroundOpacity", "hub glass fill"),
    ("borderWidth: 2\n            borderColor: Colors.orange", "hub orange frame"),
    ("glowVisible: false", "hub disables full-rectangle chassis glow"),
):
    require(HUB, needle, message)

assert HUB.count("safeSource: frameGlowSource") == 2

# History cards keep a subtle aura while returning close to the old vertical
# density. The ListView itself intentionally remains clipped.
for needle, message in (
    ("property int cardSpacing: 2", "compact card spacing"),
    ("property int cardGlowVerticalGutter: 5", "card vertical glow gutter"),
    ("property int cardCloseGlowSpread: 2", "card close glow spread"),
    ("property real cardCloseGlowOpacity: 0.28", "card close glow strength"),
    ("property int cardWideGlowSpread: 5", "card wide glow spread"),
    ("property real cardWideGlowOpacity: 0.06", "card wide glow strength"),
    ("+ (root.cardGlowVerticalGutter * 2)", "delegate reserves both glow gutters"),
    ("topMargin: root.cardGlowVerticalGutter", "card sits inside reserved top gutter"),
    ("WindowPanelFrame {\n                            id: card", "history card shared chassis"),
    ("glowColor: notificationEntry.notificationColor", "semantic card glow color"),
):
    require(HUB, needle, message)

assert "id: cardGlowSource" not in HUB
assert "cardGlowRadius" not in HUB
require(HUB, "clip: true", "history viewport clipping stays enabled")

# Transient popup: preserve the visible 420x150 card, move its top edge down
# 2px to 4px from screen top, and move it 2px farther right to a 15px margin.
for needle, message in (
    ("implicitWidth: 444", "popup glow-host width"),
    ("implicitHeight: 164", "popup glow-host height"),
    ("top: 2", "popup native top margin"),
    ("right: 3", "popup native right margin"),
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
