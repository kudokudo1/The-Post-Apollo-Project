#!/usr/bin/env python3
"""Notifications Hub requested visual controls, with no altered policies."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
hub = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
service = (ROOT / "services/notifications/NotificationsService.qml").read_text()

# Three hub scrollbars (history, DND manager, Favorites manager) reuse the
# shared NeonScrollBar's paintable star rather than a bespoke handle.
scrollbars = re.findall(r"\bNeonScrollBar\s*\{([^{}]*)\}", hub)
assert len(scrollbars) == 3, "review all existing Hub scrollbars"
assert all('handleStyle: "star"' in b for b in scrollbars)
assert "starAreaWidth: root.scrollBarAreaWidth" in hub
assert "starHandleSize: 14" in hub
assert "flickable: historyList" in hub
assert "flickable: dndManagerList" in hub
assert "flickable: favoriteManagerList" in hub

# The input text is magenta; only the insertion cursor is orange.
search = hub.split("id: searchInput", 1)[1].split("// ===== FILTER STRIP", 1)[0]
assert "color: Colors.magenta" in search
assert re.search(r'cursorDelegate:\s*Rectangle\s*\{\s*width: 2\s+'
                 r'height: searchInput\.cursorRectangle\.height\s+'
                 r'color: Colors\.orange', search)
assert "text: root.searchQuery" in search
assert "onTextChanged:" in search, "search still filters history"
assert "text: \"SEARCH HISTORY...\"" in search, "placeholder unchanged"

filters = hub.split("id: filterStrip", 1)[1].split("// New second header divider", 1)[0]
found = re.findall(r'filterId: "([^"]+)"', filters)
assert found == ["all", "favorites", "apps", "social",
                 "apollo", "system", "warning", "manager"], found
assert '"all", "favorites", "apps", "social", "apollo", "system", "warning", "manager"' in hub

# Only the ZZ's idle/active label is white. Existing hover/pressed
# semantics and other MiniButtons retain their original colors.
control = hub.split('label: "ZZ"', 1)[1].split("onTriggered:", 1)[0]
assert "whiteLabel: true" in control
assert "activeColor: Colors.white" in control
assert "if (miniButton.whiteLabel && !miniButton.hovered && !miniButton.pressed)" in hub
assert "return Colors.white;" in hub

# No manual expand click: text wraps and ListView delegate/card grows with
# measured content. Preserve action buttons and glow gutters.
glow = hub.split("component GlowText:", 1)[1].split("component MiniButton:", 1)[0]
assert "readonly property real fullTextHeight: glowLabel.contentHeight" in glow
assert "wrapMode: glowText.wrapMode" in glow
assert "verticalAlignment: glowText.wrapMode === Text.NoWrap" in glow
message = hub.split("id: notificationMessage", 1)[1].split("MULTILINE REPORT DECK", 1)[0]
assert "text: notificationEntry.message" in message
assert "height: Math.max(19, Math.ceil(fullTextHeight))" in message
assert "wrapMode: Text.Wrap" in message
assert "elideMode: Text.ElideNone" in message
assert "visible: !notificationEntry.isReport" in message
assert "notificationMessage.y + notificationMessage.height" in hub
assert "reportText.y + reportText.contentHeight" in hub
assert "notificationEntry.extendedReportCardHeight" in hub
assert "notificationEntry.compactCardHeight" in hub
assert "(root.cardGlowVerticalGutter * 2)" in hub
assert "id: bringHereButton" in hub
assert "height: root.cardHeight" not in hub, "card must not be fixed"

# Styling only. Never use this feature to change the data policy.
assert "function toggleFavorite" in service
assert "function snoozeApp" in service
print("Notifications Hub star/search/FAVS/ZZ/full-message contracts: PASS")
