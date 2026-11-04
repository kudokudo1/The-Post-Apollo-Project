"""M2 Clock WORLD favorites: shared store, UI, and no privileged changes.

Source contracts only; see the Node policy test for executable add/remove,
validation, deduplication, and bounded persistence document roundtrips.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/WorldFavoritesPolicy.js").read_text(encoding="utf-8")
TIME_POLICY = (ROOT / "services/time/TimeSettingsPolicy.js").read_text(encoding="utf-8")
WORLD_SEARCH = (ROOT / "services/time/WorldZoneSearch.js").read_text(encoding="utf-8")


class WorldFavoritesIntegrationContracts(unittest.TestCase):
    def test_single_time_service_owns_new_atomic_document(self):
        self.assertIn('import "WorldFavoritesPolicy.js" as Favorites', SERVICE)
        self.assertIn("time-world-favorites-v1.json", SERVICE)
        self.assertIn("time-settings-v1.json", SERVICE)
        self.assertIn("id: worldFavoritesFile", SERVICE)
        self.assertIn("atomicWrites: true", SERVICE)
        self.assertIn("watchChanges: false", SERVICE)
        self.assertIn("onLoaded: timeSettings.loadWorldFavoriteDocument", SERVICE)
        self.assertIn("FileViewError.FileNotFound", SERVICE)
        self.assertIn("FAVORITES FILE INVALID // NOT OVERWRITTEN", SERVICE)
        self.assertEqual(TIMEW.count("FileView {"), 0)
        self.assertNotIn("FileView {", POLICY)
        self.assertNotIn("FileView {", WORLD_SEARCH)
        self.assertIn("MAX_OFFSET_MS = 300000", TIME_POLICY)

    def test_rapid_clicks_coalesce_without_overlapping_writes(self):
        self.assertIn("worldFavoritePendingDocument", SERVICE)
        self.assertIn("worldFavoriteQueuedDocument", SERVICE)
        self.assertIn("if (worldFavoritePendingDocument !== null)", SERVICE)
        self.assertIn("worldFavoriteQueuedDocument = next.document", SERVICE)
        self.assertIn("timeSettings.beginWorldFavoriteWrite(queued)", SERVICE)
        self.assertIn("onSaveFailed: function(error)", SERVICE)
        self.assertIn("FAVORITES_SAVE_FAILED", SERVICE)
        self.assertIn("worldFavoriteCanEdit", SERVICE)
        self.assertIn("worldFavoriteState === \"saving\"", SERVICE)

    def test_only_installed_iana_zones_can_be_starred_or_selected(self):
        self.assertIn("ZoneSearch.contains(installedZones, zoneId)", SERVICE)
        self.assertIn("Favorites.toggle(worldFavoriteZones, zoneId)", SERVICE)
        self.assertIn("WorldZoneSearch.contains(", TIMEW)
        self.assertIn("timew.selectWorldSearchResult(modelData)", TIMEW)
        self.assertIn("function selectWorldSearchResult(zoneId)", TIMEW)
        self.assertIn("worldFavoriteLimit: Favorites.MAX_FAVORITES", SERVICE)
        self.assertIn("var MAX_FAVORITES = 8", POLICY)
        self.assertIn("INVALID_ZONE_OR_DUPLICATE", POLICY)

    def test_world_menu_uses_existing_search_and_preset_strip(self):
        self.assertIn("id: worldFavoritesStrip", TIMEW)
        self.assertIn("id: worldFavoriteToggle", TIMEW)
        self.assertIn("id: favoriteZoneScroll", TIMEW)
        self.assertIn("id: favoriteZoneRow", TIMEW)
        self.assertIn("TimeSettings.worldFavoriteZones", TIMEW)
        self.assertIn("TimeSettings.worldFavoriteCanEdit", TIMEW)
        self.assertIn("TimeSettings.isWorldFavorite(", TIMEW)
        self.assertIn("TimeSettings.toggleWorldFavorite(", TIMEW)
        self.assertIn("Flickable.HorizontalFlick", TIMEW)
        self.assertIn("STAR A ZONE TO SAVE", TIMEW)
        self.assertIn('label: "WORLD"', TIMEW)
        self.assertIn("model: timew.worldZones", TIMEW)
        self.assertIn('id: "clock", name: "CLOCK"', TIMEW)
        self.assertIn('id: "planned", name: "ANGEL"', TIMEW)
        quick_strip = TIMEW.split("readonly property var worldZones:", 1)[1].split("]", 1)[0]
        for zone in ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo"):
            self.assertIn('id: "' + zone + '"', quick_strip)
        self.assertEqual(quick_strip.count("id:"), 4)

    def test_no_system_timezone_or_ntp_mutations(self):
        favorites_service = SERVICE.split(
            "function toggleWorldFavorite(zoneId, installedZones)", 1
        )[1].split("property string zoneChoice:", 1)[0]
        for forbidden in ("set-timezone", "set-ntp", "set-local-rtc",
                          "TimeHostControl.py", "pkexec", "sudo",
                          "chronyd", "Date.set", "Process {"):
            self.assertNotIn(forbidden, favorites_service)
            self.assertNotIn(forbidden, POLICY)
        self.assertIn("return true;", favorites_service)

    def test_schema_version_bound_and_store_failure_are_visible(self):
        self.assertIn("var VERSION = 1", POLICY)
        self.assertIn("UNSUPPORTED_VERSION", POLICY)
        self.assertIn("FAVORITES_FULL", POLICY)
        self.assertIn("FAVORITES NOT SAVED", SERVICE)
        self.assertIn("TimeSettings.worldFavoriteMessage", TIMEW)
        self.assertIn("TimeSettings.worldFavoriteState", TIMEW)


if __name__ == "__main__":
    unittest.main()
