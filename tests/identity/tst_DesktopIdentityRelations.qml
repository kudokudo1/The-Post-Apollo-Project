import QtQuick
import QtTest
import "../../services/identity"

TestCase {
    name: "Team7DesktopIdentityRelations"

    DesktopIdentityEvidence {
        id: identity
    }

    DesktopIdentityRelations {
        id: relations
    }

    function team6AudioObservation(pid) {
        return {
            provider: "PIPEWIRE",
            providerKey: "sink-input:63",
            lifetimeClass: "ephemeral",
            generation: 5,
            raw: {
                streamIndex: 63,
                applicationProcessId: String(pid),
                applicationProcessBinary: "firefox",
                applicationId: "firefox",
                applicationName: "Firefox",
                mediaName: "AudioStream"
            },
            aliases: [
                {
                    kind: "application.id",
                    value: "firefox",
                    normalized: "firefox"
                }
            ],
            relationships: []
        };
    }

    function test_explicitProviderRelationMaterializes() {
        const sway = identity.swayWindowObservation({
            id: 100,
            appId: "firefox",
            pid: 4401
        }, 1);

        const process = identity.processObservation({
            pid: 4401,
            ppid: 1,
            comm: "firefox"
        }, 1);

        const edges = relations.explicitEdges([sway, process]);

        compare(edges.length, 1);
        compare(edges[0].kind, "EXACT_PID");
        compare(edges[0].leftKey, "sway-con:100");
        compare(edges[0].rightKey, "pid:4401");
        compare(edges[0].strength, identity.strengthExact);
    }

    function test_sharedPidBecomesOneEvidenceGroup() {
        const process = identity.processObservation({
            pid: 4401,
            comm: "firefox"
        }, 2);

        const sway = identity.swayWindowObservation({
            id: 101,
            appId: "firefox",
            pid: 4401
        }, 2);

        const surface = identity.surfaceObservation({
            provider: "KITTY",
            providerKey: "kitty:9",
            appName: "Kitty",
            processPids: [4401],
            kittyTabId: 9
        }, 2);

        const audio = team6AudioObservation(4401);
        const groups = relations.pidGroups([
            process,
            sway,
            surface,
            audio
        ]);

        compare(groups.length, 1);
        compare(groups[0].pid, 4401);

        // Four observers of one PID remain one evidence family, not six
        // pairwise "confirmations".
        compare(groups[0].members.length, 4);
        compare(groups[0].evidenceFamily, "pid");
    }

    function test_devtoolsPortCanAttachSurfaceToProcess() {
        const surface = identity.surfaceObservation({
            provider: "DEVTOOLS",
            providerKey: "devtools:9222:ABC",
            appName: "Brave",
            debugPort: 9222,
            targetId: "ABC"
        }, 4);

        const process = identity.processObservation({
            pid: 5510,
            comm: "brave",
            args: "/usr/bin/brave --remote-debugging-port=9222"
        }, 4);

        const edges = relations.debugPortEdges([
            surface,
            process
        ]);

        compare(edges.length, 1);
        compare(
            edges[0].kind,
            relations.relationDebugPortOwner
        );
        compare(edges[0].rightKey, "pid:5510");
        compare(edges[0].details.debugPort, 9222);
    }

    function test_devtoolsPortSplitArgumentFormAlsoMatches() {
        const process = identity.processObservation({
            pid: 5511,
            comm: "electron",
            args: "electron --remote-debugging-port 9307 app.js"
        }, 4);

        compare(
            relations.processOwnsDebugPort(process, 9307),
            true
        );
        compare(
            relations.processOwnsDebugPort(process, 9308),
            false
        );
    }

    function test_surfaceLaunchDebugPortAttachesToProcess() {
        const launch = identity.surfaceLaunchObservation({
            correlationId: "launch-devtools",
            appliedCapabilities: ["DEVTOOLS"],
            bootstrap: {
                correlationId: "launch-devtools",
                debugAddress: "127.0.0.1",
                debugPort: 9225
            }
        }, 5);

        const process = identity.processObservation({
            pid: 5520,
            comm: "code",
            args: "/usr/bin/code --remote-debugging-port=9225"
        }, 5);

        const edges = relations.debugPortEdges([
            launch,
            process
        ]);

        compare(edges.length, 1);
        compare(edges[0].leftProvider, "SURFACE_LAUNCH");
        compare(edges[0].rightKey, "pid:5520");
        compare(
            edges[0].kind,
            relations.relationDebugPortOwner
        );
    }

    function test_surfaceLaunchKittyEndpointAttachesToSurface() {
        const launch = identity.surfaceLaunchObservation({
            correlationId: "launch-kitty",
            appliedCapabilities: ["KITTY_REMOTE"],
            bootstrap: {
                correlationId: "launch-kitty",
                kittyListenOn: "unix:@appcontrol-kitty-77"
            }
        }, 6);

        const surface = identity.surfaceObservation({
            provider: "KITTY",
            providerKey: "kitty:12",
            appName: "Kitty",
            kittyAddress: "unix:@appcontrol-kitty-77",
            kittyTabId: 12,
            processPids: []
        }, 6);

        const edges = relations.kittyEndpointEdges([
            launch,
            surface
        ]);

        compare(edges.length, 1);
        compare(
            edges[0].kind,
            relations.relationKittyEndpoint
        );
        compare(
            edges[0].leftKey,
            "surface-launch:launch-kitty"
        );
        compare(edges[0].rightKey, "kitty:12");
        compare(edges[0].strength, identity.strengthExact);
    }

    function test_differentKittyEndpointDoesNotJoin() {
        const launch = identity.surfaceLaunchObservation({
            correlationId: "launch-kitty-a",
            bootstrap: {
                correlationId: "launch-kitty-a",
                kittyListenOn: "unix:@kitty-a"
            }
        }, 1);

        const surface = identity.surfaceObservation({
            provider: "KITTY",
            providerKey: "kitty:44",
            kittyAddress: "unix:@kitty-b"
        }, 1);

        compare(
            relations.kittyEndpointEdges([
                launch,
                surface
            ]).length,
            0
        );
    }

    function test_normalizedAliasMatchStaysHeuristic() {
        const desktop = identity.desktopEntryObservation({
            id: "org.mozilla.firefox.desktop",
            name: "",
            startupClass: "",
            command: []
        });

        const sway = identity.swayWindowObservation({
            id: 201,
            appId: "org.mozilla.firefox",
            pid: 0
        }, 1);

        const edges = relations.aliasEdges([desktop, sway]);

        let found = false;

        for (let i = 0; i < edges.length; i++) {
            if (edges[i].kind
                    === relations.relationTokenNormalized) {
                found = true;
                compare(
                    edges[i].strength,
                    identity.strengthHeuristic
                );
            }
        }

        verify(found);
    }

    function test_suffixAliasMatchPreservesDonorHeuristic() {
        const desktop = identity.desktopEntryObservation({
            id: "org.mozilla.firefox.desktop",
            name: "",
            startupClass: "",
            command: []
        });

        const sway = identity.swayWindowObservation({
            id: 202,
            appId: "firefox",
            pid: 0
        }, 1);

        const edges = relations.aliasEdges([desktop, sway]);

        let found = false;

        for (let i = 0; i < edges.length; i++) {
            if (edges[i].kind
                    === relations.relationTokenSuffix) {
                found = true;
                compare(
                    edges[i].strength,
                    identity.strengthHeuristic
                );
            }
        }

        verify(found);
    }

    function test_ambiguousDesktopCandidatesAreBothRetained() {
        const desktopShort = identity.desktopEntryObservation({
            id: "firefox.desktop",
            name: "",
            startupClass: "",
            command: []
        });

        const desktopLong = identity.desktopEntryObservation({
            id: "org.mozilla.firefox.desktop",
            name: "",
            startupClass: "",
            command: []
        });

        const sway = identity.swayWindowObservation({
            id: 203,
            appId: "firefox",
            pid: 0
        }, 1);

        const edges = relations.aliasEdges([
            desktopShort,
            desktopLong,
            sway
        ]);

        const found = ({});

        for (let i = 0; i < edges.length; i++) {
            const item = edges[i];

            if (item.leftKey === "sway-con:203"
                    && item.rightProvider === "DESKTOP_ENTRY") {
                found[item.rightKey] = true;
            }

            if (item.rightKey === "sway-con:203"
                    && item.leftProvider === "DESKTOP_ENTRY") {
                found[item.leftKey] = true;
            }
        }

        verify(
            !!found["desktop-entry:firefox.desktop"]
        );
        verify(
            !!found["desktop-entry:org.mozilla.firefox.desktop"]
        );

        // Relation discovery reports both candidates. It does not choose the
        // first DesktopEntry in catalog order.
        compare(Object.keys(found).length, 2);
    }

    function test_relationSnapshotHasNoResolutionVerdict() {
        const snapshot = relations.relationSnapshot([]);

        verify(snapshot.explicitEdges !== undefined);
        verify(snapshot.pidGroups !== undefined);
        verify(snapshot.debugPortEdges !== undefined);
        verify(snapshot.kittyEndpointEdges !== undefined);
        verify(snapshot.aliasEdges !== undefined);

        verify(snapshot.status === undefined);
        verify(snapshot.semanticKey === undefined);
        verify(snapshot.canonicalId === undefined);
    }
}
