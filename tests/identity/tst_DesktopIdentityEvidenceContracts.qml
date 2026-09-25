import QtQuick
import QtTest
import "../../services/identity"

TestCase {
    name: "Team7DesktopIdentityEvidenceContracts"

    DesktopIdentityEvidence {
        id: identity
    }

    function aliasByKind(observation, kind) {
        const aliases = observation.aliases || [];

        for (let i = 0; i < aliases.length; i++) {
            if (aliases[i].kind === kind)
                return aliases[i];
        }

        return null;
    }

    function relationshipByKind(observation, kind) {
        const relationships = observation.relationships || [];

        for (let i = 0; i < relationships.length; i++) {
            if (relationships[i].kind === kind)
                return relationships[i];
        }

        return null;
    }

    function test_normalizationIsEvidenceOnly() {
        compare(
            identity.normalizeToken("org.mozilla.Firefox.desktop"),
            "orgmozillafirefox"
        );

        compare(
            identity.normalizeToken("Brave-browser"),
            "bravebrowser"
        );
    }

    function test_desktopEntryObservationPreservesRawFacts() {
        const observation = identity.desktopEntryObservation({
            id: "org.mozilla.firefox.desktop",
            name: "Firefox",
            genericName: "Web Browser",
            comment: "Browse the Web",
            startupClass: "firefox",
            command: ["/usr/bin/firefox", "%U"]
        });

        compare(observation.provider, "DESKTOP_ENTRY");
        compare(
            observation.providerKey,
            "desktop-entry:org.mozilla.firefox.desktop"
        );
        compare(observation.lifetimeClass, identity.lifetimePersistent);

        compare(observation.raw.id, "org.mozilla.firefox.desktop");
        compare(observation.raw.startupClass, "firefox");
        compare(observation.raw.command[0], "/usr/bin/firefox");

        const commandAlias = aliasByKind(
            observation,
            "desktop-entry.command-basename"
        );

        verify(commandAlias !== null);
        compare(commandAlias.value, "firefox");

        // Provider observations must not quietly become semantic identities.
        verify(observation.semanticKey === undefined);
        verify(observation.canonicalId === undefined);
    }

    function test_missingDesktopIdDoesNotInventNameIdentity() {
        const observation = identity.desktopEntryObservation({
            name: "Pretty Display Name",
            command: ["/usr/bin/example"]
        });

        compare(observation.providerKey, "");
        compare(observation.raw.name, "Pretty Display Name");
    }

    function test_swayWindowKeepsWindowAndPidSeparate() {
        const observation = identity.swayWindowObservation({
            id: 991,
            name: "Project - Firefox",
            appId: "firefox",
            className: "firefox",
            instance: "Navigator",
            pid: 4401,
            workspace: "2",
            output: "DP-5",
            focused: true
        }, 7);

        compare(observation.provider, "SWAY");
        compare(observation.providerKey, "sway-con:991");
        compare(observation.generation, 7);
        compare(observation.raw.pid, 4401);

        const relation = relationshipByKind(
            observation,
            "EXACT_PID"
        );

        verify(relation !== null);
        compare(relation.targetProvider, "PROCFS");
        compare(relation.targetKey, "pid:4401");
        compare(relation.strength, identity.strengthExact);

        verify(observation.semanticKey === undefined);
    }

    function test_processObservationKeepsPidEphemeral() {
        const observation = identity.processObservation({
            pid: 5000,
            ppid: 1000,
            comm: "firefox",
            exe: "/usr/lib64/firefox/firefox",
            args: "/usr/lib64/firefox/firefox -contentproc",
            user: "mapple"
        }, 2);

        compare(observation.provider, "PROCFS");
        compare(observation.providerKey, "pid:5000");
        compare(observation.lifetimeClass, identity.lifetimeEphemeral);

        const parent = relationshipByKind(
            observation,
            "PROC_PARENT"
        );

        verify(parent !== null);
        compare(parent.targetKey, "pid:1000");
    }

    function test_surfaceObservationPreservesTeam5Coordinates() {
        const observation = identity.surfaceObservation({
            provider: "KITTY",
            providerKey: "kitty:7",
            appName: "Kitty",
            windowName: "1",
            role: 37,
            roleName: "page tab",
            processPids: [7001, 7002, 7002],
            kittyAddress: "unix:/tmp/kitty",
            kittyTabId: 7
        }, 11);

        compare(observation.provider, "KITTY");
        compare(observation.providerKey, "kitty:7");
        compare(observation.raw.kittyTabId, 7);
        compare(observation.raw.role, 37);
        compare(observation.raw.roleName, "page tab");
        compare(observation.raw.processPids.length, 2);
        compare(observation.relationships.length, 2);

        compare(
            observation.relationships[0].kind,
            "PROVIDER_PROCESS_PID"
        );

        verify(observation.semanticKey === undefined);
    }

    function test_surfaceTextIsAliasNotCanonicalIdentity() {
        const observation = identity.surfaceObservation({
            provider: "DEVTOOLS",
            providerKey: "devtools:9222:ABC",
            appName: "Brave",
            windowName: "https://example.test",
            debugPort: 9222,
            targetId: "ABC"
        }, 3);

        const alias = aliasByKind(
            observation,
            "surface.app-name"
        );

        verify(alias !== null);
        compare(alias.value, "Brave");
        compare(alias.normalized, "brave");
        verify(observation.canonicalId === undefined);
    }

    function test_surfaceLaunchObservationKeepsInstanceClockSeparate() {
        const observation = identity.surfaceLaunchObservation({
            correlationId: "launch-abc",
            requestedCapabilities: ["KITTY_REMOTE", "DEVTOOLS"],
            appliedCapabilities: ["KITTY_REMOTE", "DEVTOOLS"],
            bootstrap: {
                correlationId: "launch-abc",
                kittyListenOn: "unix:@appcontrol-kitty-123",
                debugAddress: "127.0.0.1",
                debugPort: 9222
            }
        }, 12);

        compare(observation.provider, "SURFACE_LAUNCH");
        compare(
            observation.providerKey,
            "surface-launch:launch-abc"
        );
        compare(
            observation.lifetimeClass,
            identity.lifetimeApplicationInstance
        );
        compare(
            observation.raw.kittyListenOn,
            "unix:@appcontrol-kitty-123"
        );
        compare(observation.raw.debugPort, 9222);
        compare(observation.raw.appliedCapabilities.length, 2);

        verify(observation.semanticKey === undefined);
        verify(observation.canonicalId === undefined);
    }

    function test_resolutionEnvelopeCanRemainAmbiguous() {
        const resolution = identity.resolutionEnvelope(
            identity.resolutionAmbiguous,
            ["desktop-entry:a.desktop", "desktop-entry:b.desktop"],
            [{ kind: "TOKEN_SUFFIX_HEURISTIC" }],
            "two candidates share the same normalized token"
        );

        compare(resolution.status, identity.resolutionAmbiguous);
        compare(resolution.candidates.length, 2);
        compare(resolution.evidence.length, 1);
    }

    function test_invalidResolutionNeverPretendsResolved() {
        const resolution = identity.resolutionEnvelope(
            "first-match-wins",
            ["desktop-entry:a.desktop"],
            [],
            "invalid status"
        );

        compare(resolution.status, identity.resolutionUnresolved);
    }
}
