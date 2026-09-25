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
            JSON.stringify([
                "app:keep",
                "file:/home/mapple/report.txt",
                "task|keep"
            ])
        );
    }

    function test_replace_collapses_existing_canonical_duplicate() {
        const result = FavoritesBackend.FavoritesService.replaced(
            [
                "file:/home/mapple/report.txt",
                "mode:2:legacy",
                "task|keep"
            ],
            "mode:2:legacy",
            "file:/home/mapple/report.txt"
        );

        verify(result.changed);
        compare(
            JSON.stringify(result.values),
            JSON.stringify([
                "file:/home/mapple/report.txt",
                "task|keep"
            ])
        );
    }

    function test_replace_does_nothing_when_legacy_key_is_absent() {
        const result = FavoritesBackend.FavoritesService.replaced(
            ["app:keep"],
            "mode:2:legacy",
            "file:/home/mapple/report.txt"
        );

        verify(!result.changed);
        compare(
            JSON.stringify(result.values),
            JSON.stringify(["app:keep"])
        );
    }

    function test_replace_rejects_empty_or_identical_keys() {
        verify(
            !FavoritesBackend.FavoritesService.replaced(
                ["app:keep"],
                "",
                "file:/tmp/a"
            ).changed
        );
        verify(
            !FavoritesBackend.FavoritesService.replaced(
                ["file:/tmp/a"],
                "file:/tmp/a",
                "file:/tmp/a"
            ).changed
        );
    }
}
