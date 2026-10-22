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

# Popups take perimeter identity from the event's origin/domain, not
# an exclusive filter or severity. The shared policy owns classification.
for needle, message in (
    ('import "../services/notifications/NotificationFacets.js" as NotificationFacets',
     "popup imports the shared origin/domain policy"),
    ("required property var context", "popup receives normalized event context"),
    ("organizationFacets: NotificationFacets.facetsFor({",
     "popup uses the independent notification facets"),
    ('"context": notificationCard.context',
     "popup preserves explicit Apollo origin and domain"),
    ('organizationFacets.origin === "apollo" ? Colors.orange',
     "Apollo source color stays orange"),
    ('organizationFacets.domain === "social" ? Colors.omnitrix',
     "external Social source color stays Omnitrix green"),
    ('organizationFacets.domain === "system" ? Colors.white',
     "external System source color stays white"),
    (": Colors.cyan", "generic Apps remain cyan"),
    ("borderColor: notificationCard.organizationColor",
     "popup frame follows organization color"),
    ("glowColor: notificationCard.organizationColor",
     "popup glow follows the same organization color"),
):
    require(POPUP, needle, message)

assert "borderColor: Colors.cyan\n\n                glowColor: Colors.cyan" not in POPUP


# Receipt/update time uses existing persisted timestamps. In history, the
# time must be directly to the right of the icon and above the source label.
for needle, message in (
    ("id: receivedTimestamp", "history timestamp widget"),
    ("top: appIconBox.top", "timestamp shares icon's top row"),
    ("left: appIconBox.right", "timestamp sits beside app icon"),
    ("top: receivedTimestamp.bottom", "source is directly below timestamp"),
    ("required property double createdAt", "historical receipt timestamp role"),
    ("required property double updatedAt", "historical update timestamp role"),
    ("eventTimestamp(notificationEntry.createdAt, notificationEntry.updatedAt)", "history timestamp binding"),
    ('"createdAt": Number(entry.createdAt || 0)', "history model carries receipt time"),
    ('"updatedAt": Number(entry.updatedAt || 0)', "history model carries update time"),
):
    require(HUB, needle, message)

for needle, message in (
    ("function eventTimestamp(createdAt, updatedAt)", "popup time formatter"),
    ("required property double createdAt", "popup receipt timestamp role"),
    ("required property double updatedAt", "popup update timestamp role"),
    ("text: notificationsWindow.eventTimestamp(notificationCard.createdAt, notificationCard.updatedAt)", "popup timestamp line"),
):
    require(POPUP, needle, message)

# Eight compact filter controls follow the exact declared visual order,
# including FAVS immediately after COMBI for keyboard + pointer parity;
# the underlying 'all' ID remains COMBI's broad filter semantics.
filter_strip = HUB.split('id: filterStrip')[1].split('// New second header divider')[0]
assert '(width - (spacing * 7)) / 8' in filter_strip, "eight filters must fit the existing strip"
expected_filters = [
    ('all', 'COMBI', 'Colors.yellow'),
    ('favorites', 'FAVS', 'Colors.magenta'),
    ('apps', 'APPS', 'Colors.cyan'),
    ('social', 'SOCIAL', 'root.omnitrixGreen'),
    ('apollo', 'APOLLO', 'Colors.orange'),
    ('system', 'SYSTEM', 'Colors.white'),
    ('warning', 'WARNING', 'Colors.red'),
    ('manager', 'MANAGER', 'Colors.magenta'),
]
import re
actual_filters = re.findall(
    r'filterId: "([^"]+)"\s+label: "([^"]+)"\s+accentColor: ([\w.]+)',
    filter_strip,
)
assert actual_filters == expected_filters, f"filter identities/order drifted: {actual_filters!r}"
assert '"all", "favorites", "apps", "social", "apollo", "system", "warning", "manager"' in HUB, "keyboard tabs must match visual order"

# Favorites Manager shares screen space but cannot eliminate the existing
# DND list, destructive confirmation, history list or scrollbars.
for needle, description in (
    ("id: managerSourceSections", "two-section manager layout"),
    ("id: dndManagerSection", "DND manager section"),
    ("id: favoriteManagerSection", "Favorites manager section"),
    ("id: dndManagerList", "DND source manager"),
    ("id: favoriteManagerList", "Favorites source manager"),
    ("model: NotificationsService.favoriteSources", "persistent favorites manager model"),
    ("id: removeFavoriteButton", "UNFAV control"),
    ("activeColor: Colors.magenta", "favorite identity color"),
    ("flickable: dndManagerList", "DND manager scrollbar"),
    ("flickable: favoriteManagerList", "Favorites manager scrollbar"),
    ("root.managerSelectionSection === \"favorites\"", "favorite keyboard selection state"),
    ("root.managerSelectionSection === \"dnd\"", "DND keyboard selection state"),
):
    require(HUB, needle, description)

# Native action controls are conditional: the existing 420x150 popup
# geometry must not change for ordinary notifications.
for needle, message in (
    ("implicitWidth: 444", "native window glow gutter preserved"),
    ("implicitHeight: 164", "native window height preserved"),
    ("height: 150", "visible popup card height preserved"),
    ("id: externalActionRow", "native action row exists"),
    ("visible: notificationCard.externalActions.length > 0", "actions hidden when no live callbacks exist"),
    ("model: notificationCard.externalActions", "actions are backed by live model"),
    ("anchors.bottom: externalActionRow.visible ? externalActionRow.top : undefined", "text stops above actions"),
    ("maximumLineCount: externalActionRow.visible ? 2 : 3", "message height adapts to action row"),
    ("NotificationsService.invokeExternalAction(", "native action click is connected"),
):
    require(POPUP, needle, message)

# Site images must stay recognizable. Recoloring arbitrary opaque browser
# payloads can flatten real favicons into a magenta/black checkerboard.
# Keep Post-Apollo's black backing / magenta border and its intentionally
# designed magenta/black YouTube asset, but render all other image pixels
# without an additional effect pass.
youtube_svg = (ROOT / "assets/notifications/youtube.svg").read_text(encoding="utf-8")
assert 'fill="#C74EC7"' in youtube_svg, "YouTube icon background must be magenta"
assert 'fill="#000000"' in youtube_svg, "YouTube play triangle must be black"
for surface, name in ((HUB, "history"), (POPUP, "popup")):
    assert "Colorize {" not in surface, f"{name}: no HSL recolor of website images"
    assert "ColorOverlay {" not in surface, f"{name}: no alpha-only tint squares"
    assert "Colors.black" in surface, f"{name}: website black backing"
assert 'notificationEntry.website !== "" ? Colors.black : Colors.dark' in HUB
assert 'notificationEntry.website !== ""\n                                    ? Colors.magenta : notificationEntry.sourceColor' in HUB
hub_icon = HUB.split("id: appIconImage", 1)[1].split("// ONE icon only:", 1)[0]
assert "source: notificationEntry.resolvedAppIcon" in hub_icon
assert "fillMode: Image.PreserveAspectFit" in hub_icon
assert "visible: notificationEntry.website" not in hub_icon, (
    "Do not hide the site Image behind a separate image effect"
)
assert HUB.count("id: appIconImage") == 1, "history draws exactly one site image"
popup_icon = POPUP.split("id: notificationIcon", 1)[1].split("// ===== TEXT", 1)[0]
assert "notificationCard.websiteIcon" in popup_icon
assert "fillMode: Image.PreserveAspectFit" in popup_icon
assert "visible: notificationCard.website" not in popup_icon
assert POPUP.count("id: notificationIcon") == 1, "popup draws exactly one site image"

# Website SITE/APP scope goes next to the lower-right Bring Here arrow, not
# into the top ZZ/DND/CLEAR/× row. Preserve card and action geometry.
top_buttons = HUB.split("id: appControls", 1)[1].split("// ===== NOTIFICATION TITLE", 1)[0]
footer_buttons = HUB.split("id: cardFooterActions", 1)[1].split("// ===== CUSTOM SCROLL BAR", 1)[0]
assert 'notificationEntry.targetWholeApp ? "APP"' not in top_buttons
assert 'notificationEntry.targetWholeApp ? "APP"' in footer_buttons
assert footer_buttons.index('notificationEntry.targetWholeApp ? "APP"') < footer_buttons.index('id: bringHereButton')
assert 'spacing: 5' in footer_buttons
assert 'right: cardFooterActions.left' in HUB, "reserve actual footer row width beside message"
assert 'label: "ZZ"' in top_buttons and 'label: "DND"' in top_buttons
assert 'label: "CLEAR ALL"' in top_buttons and 'label: "×"' in top_buttons

print("Notification visual contracts: PASS")
