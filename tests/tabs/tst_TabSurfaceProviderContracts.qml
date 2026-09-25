import QtQuick
import QtTest
import "../../services/tabs"

TestCase {
    name: "Team5TabSurfaceProviderContracts"

    TabSurfaceProvider {
        id: provider
        active: false
    }

    function test_providerRecordKeyStaysProviderLocal() {
        compare(provider.providerRecordKey({
            id: "kitty:7",
            appName: "Kitty"
        }), "kitty:7");

        compare(provider.providerRecordKey({
            appName: "Pretty Name"
        }), "");
    }

    function test_identityEvidencePreservesKittyCoordinates() {
        const evidence = provider.identityEvidence({
            id: "kitty:7",
            provider: "KITTY",
            appName: "Kitty",
            windowName: "42",
            kittyAddress: "unix:/tmp/kitty",
            kittyTabId: 7,
            processPids: [7002, 7001, 7002]
        });

        compare(evidence.providerKey, "kitty:7");
        compare(evidence.provider, "KITTY");
        compare(evidence.kittyAddress, "unix:/tmp/kitty");
        compare(evidence.kittyTabId, 7);
        compare(evidence.processPids.length, 3);

        verify(evidence.canonicalId === undefined);
        verify(evidence.semanticKey === undefined);
    }

    function test_identityEvidencePreservesAtSpiCacheCoordinates() {
        const evidence = provider.identityEvidence({
            id: "atspi-cache::1.42:/org/a11y/atspi/accessible/7",
            provider: "AT-SPI-CACHE",
            appName: "Example",
            windowName: "Example Window",
            busName: ":1.42",
            objectPath: "/org/a11y/atspi/accessible/7"
        });

        compare(evidence.busName, ":1.42");
        compare(
            evidence.objectPath,
            "/org/a11y/atspi/accessible/7"
        );
    }

    function test_identityEvidencePreservesAccessibilityRole() {
        const evidence = provider.identityEvidence({
            id: "libatspi:/example/path",
            provider: "LIBATSPI",
            path: "/example/path",
            role: 37,
            roleName: "page tab"
        });

        compare(evidence.path, "/example/path");
        compare(evidence.role, 37);
        compare(evidence.roleName, "page tab");
    }

    function test_normalizedProcessPidsForSignature() {
        const pids = provider.normalizedProcessPids({
            processPids: [7002, 0, 1, 7001, 7002, "7003"]
        });

        compare(pids.length, 3);
        compare(pids[0], 7001);
        compare(pids[1], 7002);
        compare(pids[2], 7003);
    }

    function test_signatureChangesWhenPidEvidenceChanges() {
        const a = [{
            provider: "KITTY",
            id: "kitty:7",
            tabTitle: "shell",
            appName: "Kitty",
            windowName: "42",
            kittyAddress: "unix:/tmp/kitty",
            kittyTabId: 7,
            processPids: [7001]
        }];

        const b = [{
            provider: "KITTY",
            id: "kitty:7",
            tabTitle: "shell",
            appName: "Kitty",
            windowName: "42",
            kittyAddress: "unix:/tmp/kitty",
            kittyTabId: 7,
            processPids: [7002]
        }];

        verify(
            provider.tabRowsSignature(a)
            !== provider.tabRowsSignature(b)
        );
    }

    function test_signatureIgnoresPidOrderingAndDuplicates() {
        const a = [{
            provider: "KITTY",
            id: "kitty:7",
            tabTitle: "shell",
            processPids: [7002, 7001, 7002]
        }];

        const b = [{
            provider: "KITTY",
            id: "kitty:7",
            tabTitle: "shell",
            processPids: [7001, 7002]
        }];

        compare(
            provider.tabRowsSignature(a),
            provider.tabRowsSignature(b)
        );
    }

    function test_controlSignatureSuppressesIdenticalHeartbeats() {
        const a = [{
            _tabControlRecord: true,
            provider: "LIBATSPI",
            id: "libatspi-control:/a/b",
            path: "/a/b",
            controlName: "New Tab",
            appName: "Example",
            windowName: "Example Window",
            role: 43,
            roleName: "push button",
            selected: false
        }];

        const b = [{
            _tabControlRecord: true,
            provider: "LIBATSPI",
            id: "libatspi-control:/a/b",
            path: "/a/b",
            controlName: "New Tab",
            appName: "Example",
            windowName: "Example Window",
            role: 43,
            roleName: "push button",
            selected: false
        }];

        compare(
            provider.controlRowsSignature(a),
            provider.controlRowsSignature(b)
        );
    }

    function test_controlSignatureTracksMeaningfulEvidence() {
        const base = [{
            provider: "LIBATSPI",
            id: "libatspi-control:/a/b",
            path: "/a/b",
            controlName: "New Tab",
            appName: "Example",
            windowName: "Example Window",
            role: 43,
            roleName: "push button",
            selected: false
        }];

        const selected = [{
            provider: "LIBATSPI",
            id: "libatspi-control:/a/b",
            path: "/a/b",
            controlName: "New Tab",
            appName: "Example",
            windowName: "Example Window",
            role: 43,
            roleName: "push button",
            selected: true
        }];

        verify(
            provider.controlRowsSignature(base)
            !== provider.controlRowsSignature(selected)
        );
    }

    function test_activationResultHonorsProviderFailure() {
        const failed = provider.parseActivationResult(
            '{"ok": false, "error": "TARGET GONE"}'
        );

        verify(!failed.ok);
        compare(failed.message, "TARGET GONE");
    }

    function test_activationResultHonorsProviderSuccess() {
        const passed = provider.parseActivationResult(
            '{"ok": true, "error": ""}'
        );

        verify(passed.ok);
        compare(passed.message, "");
    }

    function test_activationResultRejectsMalformedOutput() {
        const malformed = provider.parseActivationResult("not-json");

        verify(!malformed.ok);
        verify(
            malformed.message.indexOf("TAB ACTIVATION PARSE:") === 0
        );
    }

    function test_instrumentationLeaseObservationsExposeOnlyRuntimeCoordinates() {
        const observations = provider.instrumentationLeaseObservations([
            {
                id: "devtools:9222:ABC",
                provider: "DEVTOOLS",
                debugPort: 9222,
                targetId: "ABC",
                appName: "Brave"
            },
            {
                id: "kitty:7",
                provider: "KITTY",
                kittyAddress: "unix:@kitty-seven",
                kittyTabId: 7,
                processPids: [7001]
            },
            {
                id: "libatspi:/tab/1",
                provider: "LIBATSPI",
                path: "/tab/1"
            }
        ]);

        compare(observations.length, 2);

        compare(observations[0].kind, "devtools-port");
        compare(observations[0].value, 9222);
        compare(observations[0].providerKey, "devtools:9222:ABC");

        compare(observations[1].kind, "kitty-listen-on");
        compare(observations[1].value, "unix:@kitty-seven");
        compare(observations[1].providerKey, "kitty:7");

        verify(observations[0].canonicalId === undefined);
        verify(observations[1].applicationId === undefined);
    }

    function test_instrumentationLeaseObservationsDeduplicateCoordinates() {
        const observations = provider.instrumentationLeaseObservations([
            {
                id: "devtools:9222:A",
                provider: "DEVTOOLS",
                debugPort: 9222
            },
            {
                id: "devtools:9222:B",
                provider: "DEVTOOLS",
                debugPort: 9222
            },
            {
                id: "kitty:1",
                provider: "KITTY",
                kittyAddress: "unix:@same"
            },
            {
                id: "kitty:2",
                provider: "KITTY",
                kittyAddress: "unix:@same"
            }
        ]);

        compare(observations.length, 2);
    }

    function test_bridgeDiagnosticsScopeLeaseCompleteness() {
        const kinds = provider.instrumentationObservationCompleteKinds([
            "KITTY SOCKETS:1",
            "KITTY TABS:2",
            "KITTY ERROR:NONE",
            "DEVTOOLS PORTS:9222",
            "DEVTOOLS TARGETS:3",
            "DEVTOOLS ERROR:NONE"
        ]);

        compare(kinds.length, 2);
        compare(kinds[0], "devtools-port");
        compare(kinds[1], "kitty-listen-on");
    }

    function test_providerFailureWithholdsOnlyFailedCompleteness() {
        const kinds = provider.instrumentationObservationCompleteKinds([
            "KITTY SOCKETS:1",
            "KITTY ERROR:NONE",
            "DEVTOOLS PORTS:NONE",
            "DEVTOOLS ERROR:DISCOVERY: permission denied"
        ]);

        compare(kinds.length, 1);
        compare(kinds[0], "kitty-listen-on");
    }

    function test_fallbackCountDiagnosticsDoNotClaimCompleteness() {
        const kinds = provider.instrumentationObservationCompleteKinds([
            "KITTY:2",
            "DEVTOOLS:4"
        ]);

        compare(kinds.length, 0);
    }

    function test_instrumentationLeaseSnapshotCombinesEvidenceAndScope() {
        const snapshot = provider.instrumentationLeaseSnapshot(
            [{
                id: "devtools:9444:A",
                provider: "DEVTOOLS",
                debugPort: 9444
            }],
            [
                "DEVTOOLS ERROR:NONE",
                "KITTY ERROR:socket failed"
            ]
        );

        compare(snapshot.observations.length, 1);
        compare(snapshot.observations[0].kind, "devtools-port");
        compare(snapshot.completeKinds.length, 1);
        compare(snapshot.completeKinds[0], "devtools-port");
    }

    function test_nativeLifecycleIsProviderSpecific() {
        verify(provider.hasNativeLifecycleControl({
            provider: "DEVTOOLS",
            debugPort: 9222,
            targetId: "ABC"
        }));

        verify(!provider.hasNativeLifecycleControl({
            provider: "LIBATSPI",
            path: "/tab/1"
        }));

        verify(!provider.hasNativeLifecycleControl({
            provider: "DEVTOOLS",
            debugPort: 0,
            targetId: "ABC"
        }));
    }

    function test_providerDoesNotInventIdentityFromDisplayText() {
        const evidence = provider.identityEvidence({
            provider: "DEVTOOLS",
            appName: "Brave",
            windowName: "https://example.test",
            debugPort: 9222,
            targetId: "ABC"
        });

        compare(evidence.providerKey, "");
        verify(evidence.desktopEntryId === undefined);
        verify(evidence.applicationId === undefined);
        verify(evidence.canonicalId === undefined);
    }
}
