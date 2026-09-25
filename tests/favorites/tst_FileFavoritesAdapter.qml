import QtQuick
import QtTest
import "../../services/favorites" as FavoritesBackend

TestCase {
    name: "FileFavoritesAdapter"

    readonly property var fileEntry: ({
        _fileRecord: true,
        id: "file:/home/mapple/Documents/report.txt",
        name: "report.txt",
        label: "◇  report.txt",
        path: "/home/mapple/Documents/report.txt",
        isDir: false,
        isParent: false,
        kind: "f",
        mime: "text/txt",
        detail: "/home/mapple/Documents/report.txt"
    })

    readonly property var directoryEntry: ({
        _fileRecord: true,
        id: "file:/home/mapple/Documents",
        name: "Documents",
        label: "⌯🗁๋࣭⭑  Documents/",
        path: "/home/mapple/Documents",
        isDir: true,
        isParent: false,
        kind: "d",
        mime: "inode/directory",
        detail: "/home/mapple/Documents"
    })

    readonly property var parentEntry: ({
        _fileRecord: true,
        id: "file:parent:/home/mapple/Documents",
        name: "..",
        label: "⌯🗁๋࣭⭑  ..",
        path: "/home/mapple",
        isDir: true,
        isParent: true,
        kind: "d",
        mime: "inode/directory",
        detail: "/home/mapple"
    })

    function test_provider_identity_is_preserved() {
        compare(
            FavoritesBackend.FileFavoritesAdapter.providerIdentity(fileEntry),
            "file:/home/mapple/Documents/report.txt"
        );
        compare(
            FavoritesBackend.FileFavoritesAdapter.canonicalFavoriteKey(directoryEntry),
            "file:/home/mapple/Documents"
        );
    }

    function test_parent_navigation_record_is_not_persistable() {
        verify(!FavoritesBackend.FileFavoritesAdapter.canPersist(parentEntry));
        compare(
            FavoritesBackend.FileFavoritesAdapter.canonicalFavoriteKey(parentEntry),
            ""
        );
    }

    function test_legacy_key_matches_certified_fallback_shape() {
        compare(
            FavoritesBackend.FileFavoritesAdapter.legacyFavoriteKey(fileEntry, 2),
            "mode:2:◇  report.txt"
        );
        compare(
            FavoritesBackend.FileFavoritesAdapter.legacyFavoriteKey(directoryEntry, 2),
            "mode:2:⌯🗁๋࣭⭑  Documents/"
        );
    }

    function test_canonical_membership_wins_over_legacy() {
        const canonical =
            FavoritesBackend.FileFavoritesAdapter.canonicalFavoriteKey(fileEntry);
        const legacy =
            FavoritesBackend.FileFavoritesAdapter.legacyFavoriteKey(fileEntry, 2);

        compare(
            FavoritesBackend.FileFavoritesAdapter.matchingFavoriteKey(
                fileEntry,
                2,
                [legacy, canonical]
            ),
            canonical
        );
    }

    function test_legacy_membership_remains_recognized() {
        const legacy =
            FavoritesBackend.FileFavoritesAdapter.legacyFavoriteKey(fileEntry, 2);

        compare(
            FavoritesBackend.FileFavoritesAdapter.matchingFavoriteKey(
                fileEntry,
                2,
                [legacy]
            ),
            legacy
        );
        verify(
            FavoritesBackend.FileFavoritesAdapter.isFavorite(
                fileEntry,
                2,
                [legacy]
            )
        );
    }

    function test_lazy_migration_replaces_legacy_in_place() {
        const legacy =
            FavoritesBackend.FileFavoritesAdapter.legacyFavoriteKey(fileEntry, 2);
        const canonical =
            FavoritesBackend.FileFavoritesAdapter.canonicalFavoriteKey(fileEntry);

        compare(
            FavoritesBackend.FileFavoritesAdapter.migratedKeysForEntry(
                fileEntry,
                2,
                ["app:keep", legacy, "task|keep"]
            ),
            ["app:keep", canonical, "task|keep"]
        );
    }

    function test_duplicate_legacy_and_canonical_collapse() {
        const legacy =
            FavoritesBackend.FileFavoritesAdapter.legacyFavoriteKey(fileEntry, 2);
        const canonical =
            FavoritesBackend.FileFavoritesAdapter.canonicalFavoriteKey(fileEntry);

        compare(
            FavoritesBackend.FileFavoritesAdapter.migratedKeysForEntry(
                fileEntry,
                2,
                [canonical, legacy]
            ),
            [canonical]
        );
    }

    function test_reconstruction_reference_is_identity_only() {
        const ref =
            FavoritesBackend.FileFavoritesAdapter.reconstructionReference(
                "file:/home/mapple/Documents/report.txt"
            );

        verify(ref !== null);
        compare(ref.provider, "files");
        compare(ref.identity, "file:/home/mapple/Documents/report.txt");
        compare(ref.path, "/home/mapple/Documents/report.txt");
    }

    function test_parent_key_cannot_reconstruct() {
        compare(
            FavoritesBackend.FileFavoritesAdapter.reconstructionReference(
                "file:parent:/home/mapple/Documents"
            ),
            null
        );
    }
}
