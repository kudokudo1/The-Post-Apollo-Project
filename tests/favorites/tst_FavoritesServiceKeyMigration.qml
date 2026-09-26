import QtQuick
import QtTest
import "../../services/favorites" as FavoritesBackend

TestCase {
    name: "FavoritesServiceKeyMigration"

    function test_replace_preserves_position() {
        const result = FavoritesBackend.FavoritesService.replaced(
            ["app:keep", "mode:2:legacy", "task|keep"],
            "mode:2:legacy",
            "file:/home/mapple/report.txt"
        );

        verify(result.changed);
        compare(
            JSON.stringify(result.values),
            JSON.stringify(["app:keep", "file:/home/mapple/report.txt", "task|keep"])
        );
    }

    function test_replace_collapses_existing_canonical_duplicate() {
        const result = FavoritesBackend.FavoritesService.replaced(
            ["file:/home/mapple/report.txt", "mode:2:legacy", "task|keep"],
            "mode:2:legacy",
            "file:/home/mapple/report.txt"
        );

        verify(result.changed);
        compare(
            JSON.stringify(result.values),
            JSON.stringify(["file:/home/mapple/report.txt", "task|keep"])
        );
    }

    function test_replace_does_nothing_when_legacy_key_is_absent() {
        const result = FavoritesBackend.FavoritesService.replaced(
            ["app:keep"],
            "mode:2:legacy",
            "file:/home/mapple/report.txt"
        );

        verify(!result.changed);
        compare(JSON.stringify(result.values), JSON.stringify(["app:keep"]));
    }
}
