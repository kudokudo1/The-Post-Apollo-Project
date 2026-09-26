import QtQuick
import QtTest
import "../../services/favorites" as FavoritesBackend

TestCase {
    name: "FileFavoriteResolutionClient"

    QtObject {
        id: fakeFileService

        property string lastIdentity: ""
        property int callCount: 0
        property bool acceptRequests: true
        property bool emitSynchronously: false
        property var synchronousResolution: null

        signal favoriteResolutionFinished(
            string identity,
            var resolution
        )

        function resolveFavoriteIdentity(identity) {
            lastIdentity = String(identity || "");
            callCount += 1;

            if (emitSynchronously)
                favoriteResolutionFinished(
                    lastIdentity,
                    synchronousResolution
                );

            return acceptRequests;
        }

        function reset() {
            lastIdentity = "";
            callCount = 0;
            acceptRequests = true;
            emitSynchronously = false;
            synchronousResolution = null;
        }
    }

    FavoritesBackend.FileFavoriteResolutionClient {
        id: client
        fileService: fakeFileService
    }

    SignalSpy {
        id: completionSpy
        target: client
        signalName: "resolutionFinished"
    }

    function init() {
        fakeFileService.reset();
        client.pendingIdentities = ({});
        completionSpy.clear();
    }

    function test_forwards_canonical_identity_to_file_service() {
        verify(
            client.resolveFavoriteKey(
                "file:/home/mapple/Documents/report.txt"
            )
        );

        compare(fakeFileService.callCount, 1);
        compare(
            fakeFileService.lastIdentity,
            "file:/home/mapple/Documents/report.txt"
        );
        compare(
            client.pendingCount(
                "file:/home/mapple/Documents/report.txt"
            ),
            1
        );
    }

    function test_parent_navigation_key_never_reaches_provider() {
        verify(
            !client.resolveFavoriteKey(
                "file:parent:/home/mapple/Documents"
            )
        );

        compare(fakeFileService.callCount, 0);
    }

    function test_relays_resolved_provider_result_unchanged() {
        const identity =
            "file:/home/mapple/Documents/report.txt";
        const row = {
            _fileRecord: true,
            id: identity,
            name: "report.txt",
            path: "/home/mapple/Documents/report.txt",
            isDir: false,
            isParent: false
        };
        const resolution = {
            status: "resolved",
            identity: identity,
            path: row.path,
            reason: "",
            row: row
        };

        verify(client.resolveFavoriteKey(identity));
        fakeFileService.favoriteResolutionFinished(
            identity,
            resolution
        );

        compare(completionSpy.count, 1);
        compare(completionSpy.signalArguments[0][0], identity);
        compare(
            completionSpy.signalArguments[0][1],
            resolution
        );
        compare(client.pendingCount(identity), 0);
    }

    function test_relays_missing_without_guessing() {
        const identity = "file:/tmp/does-not-exist";
        const resolution = {
            status: "missing",
            identity: identity,
            path: "/tmp/does-not-exist",
            reason: "target-does-not-exist",
            row: null
        };

        verify(client.resolveFavoriteKey(identity));
        fakeFileService.favoriteResolutionFinished(
            identity,
            resolution
        );

        compare(completionSpy.count, 1);
        compare(
            completionSpy.signalArguments[0][1].status,
            "missing"
        );
        compare(
            completionSpy.signalArguments[0][1].reason,
            "target-does-not-exist"
        );
    }

    function test_unrequested_provider_signal_is_ignored() {
        fakeFileService.favoriteResolutionFinished(
            "file:/tmp/other",
            {
                status: "resolved",
                identity: "file:/tmp/other",
                row: {}
            }
        );

        compare(completionSpy.count, 0);
    }

    function test_synchronous_invalid_completion_is_not_lost() {
        const identity = "file:relative-path";

        fakeFileService.emitSynchronously = true;
        fakeFileService.acceptRequests = false;
        fakeFileService.synchronousResolution = {
            status: "invalid",
            identity: identity,
            path: "",
            reason: "invalid-canonical-file-identity",
            row: null
        };

        verify(!client.resolveFavoriteKey(identity));
        compare(completionSpy.count, 1);
        compare(
            completionSpy.signalArguments[0][1].status,
            "invalid"
        );
        compare(client.pendingCount(identity), 0);
    }

    function test_duplicate_requests_pair_with_duplicate_results() {
        const identity = "file:/tmp/a";

        verify(client.resolveFavoriteKey(identity));
        verify(client.resolveFavoriteKey(identity));
        compare(client.pendingCount(identity), 2);

        fakeFileService.favoriteResolutionFinished(
            identity,
            { status: "missing", identity: identity, row: null }
        );
        compare(completionSpy.count, 1);
        compare(client.pendingCount(identity), 1);

        fakeFileService.favoriteResolutionFinished(
            identity,
            { status: "missing", identity: identity, row: null }
        );
        compare(completionSpy.count, 2);
        compare(client.pendingCount(identity), 0);
    }
}
