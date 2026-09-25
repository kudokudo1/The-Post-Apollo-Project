import QtQuick
import QtTest
import "../../services/surface"

TestCase {
    name: "Team5SurfaceLaunchContracts"

    readonly property var requirements: SurfaceLaunchRequirements
    readonly property var coordinator: SurfaceLaunchCoordinator
    readonly property var recovery: SurfaceInstrumentationRecovery

    function cleanup() {
        const ids = Object.keys(coordinator.correlationState);

        for (let i = 0; i < ids.length; i++)
            coordinator.releaseCorrelation(ids[i]);

        coordinator.reconcileObservedInstrumentation(
            [],
            { complete: true }
        );

        recovery.applySnapshot({
            observations: [],
            completeKinds: [],
            errors: []
        });
    }

    function braveEvidence() {
        return {
            displayName: "Brave",
            localId: "brave-browser.desktop",
            startupClass: "Brave-browser",
            executable: "brave-browser",
            argv: ["brave-browser"],
            stableHint: "brave-browser.desktop"
        };
    }

    function kittyEvidence() {
        return {
            displayName: "Kitty",
            localId: "kitty.desktop",
            executable: "kitty",
            argv: ["kitty"],
            stableHint: "kitty.desktop"
        };
    }

    function test_familyRecognitionIgnoresTrailingArgumentText() {
        const fakeKitty = {
            displayName: "Shell Wrapper",
            executable: "bash",
            argv: ["bash", "-lc", "echo kitty"]
        };

        const fakeElectron = {
            displayName: "Script Runner",
            executable: "python3",
            argv: ["python3", "tool.py", "--label=electron"]
        };

        verify(!requirements.looksLikeKitty(fakeKitty));
        verify(!requirements.looksLikeChromiumElectron(fakeElectron));
        compare(
            requirements.suggestedCapabilities(fakeKitty).length,
            0
        );
        compare(
            requirements.suggestedCapabilities(fakeElectron).length,
            0
        );
    }

    function test_launcherExecutableIdentityStillClassifies() {
        verify(requirements.looksLikeKitty({
            executable: "/usr/bin/kitty",
            argv: ["/usr/bin/kitty", "bash", "-lc", "echo hello"]
        }));

        verify(requirements.looksLikeChromiumElectron({
            executable: "/usr/bin/electron",
            argv: ["/usr/bin/electron", "app.js"]
        }));
    }

    function test_capabilitiesAreExplicitOptIn() {
        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            []
        );

        compare(augmentation.appliedCapabilities.length, 0);
        verify(augmentation.ready);
        compare(augmentation.correlationId, "");
        compare(
            Object.keys(coordinator.correlationState).length,
            0
        );
        compare(Object.keys(coordinator.leases).length, 0);
        compare(Object.keys(augmentation.env).length, 0);
        compare(augmentation.argvAppend.length, 0);
        compare(augmentation.argvAfterExecutable.length, 0);
    }

    function test_t5SuggestsButDoesNotAutoApplyCapabilities() {
        const suggested =
            requirements.suggestedCapabilities(braveEvidence());

        compare(suggested.length, 2);
        verify(
            suggested.indexOf(
                requirements.capabilityAccessibility
            ) !== -1
        );
        verify(
            suggested.indexOf(
                requirements.capabilityDevTools
            ) !== -1
        );

        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            []
        );

        compare(augmentation.appliedCapabilities.length, 0);
    }

    function test_unknownCapabilityFailsVisible() {
        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            ["DEVTOOL"]
        );

        verify(!augmentation.ready);
        compare(augmentation.correlationId, "");
        compare(augmentation.appliedCapabilities.length, 0);
        compare(augmentation.unsupportedCapabilities.length, 1);
        compare(augmentation.unsupportedCapabilities[0], "DEVTOOL");
        compare(Object.keys(coordinator.leases).length, 0);
        compare(
            Object.keys(coordinator.correlationState).length,
            0
        );
    }

    function test_unsupportedKnownCapabilityFailsBeforeLeasing() {
        const augmentation = coordinator.buildAugmentation(
            {
                displayName: "Calculator",
                executable: "gnome-calculator",
                argv: ["gnome-calculator"]
            },
            [requirements.capabilityDevTools]
        );

        verify(!augmentation.ready);
        compare(augmentation.correlationId, "");
        compare(augmentation.appliedCapabilities.length, 0);
        compare(augmentation.unsupportedCapabilities.length, 1);
        compare(
            augmentation.unsupportedCapabilities[0],
            requirements.capabilityDevTools
        );
        compare(Object.keys(coordinator.leases).length, 0);
    }

    function test_generatedKittyEndpointIsBoundedAndDistinct() {
        const first = coordinator.buildAugmentation(
            {
                displayName:
                    "Kitty with an intentionally extremely long human-readable launch hint",
                executable: "kitty",
                argv: ["kitty"],
                stableHint:
                    "this-is-an-extremely-long-stable-hint-that-should-not-expand-the-socket-name-indefinitely"
            },
            [requirements.capabilityKittyRemote]
        );

        const second = coordinator.buildAugmentation(
            kittyEvidence(),
            [requirements.capabilityKittyRemote]
        );

        verify(first.ready);
        verify(second.ready);
        verify(first.bootstrap.kittyListenOn.length <= 83);
        verify(second.bootstrap.kittyListenOn.length <= 83);
        verify(
            first.bootstrap.kittyListenOn
            !== second.bootstrap.kittyListenOn
        );
        verify(
            first.bootstrap.kittyListenOn.indexOf(
                "unix:@appcontrol-kitty-"
            ) === 0
        );
    }

    function test_kittyRemoteAugmentation() {
        const augmentation = coordinator.buildAugmentation(
            kittyEvidence(),
            [requirements.capabilityKittyRemote]
        );

        compare(augmentation.appliedCapabilities.length, 1);
        compare(
            augmentation.appliedCapabilities[0],
            requirements.capabilityKittyRemote
        );

        compare(
            augmentation.argvAfterExecutable[0],
            "-o"
        );
        compare(
            augmentation.argvAfterExecutable[1],
            "allow_remote_control=socket-only"
        );
        compare(
            augmentation.argvAfterExecutable[2],
            "--listen-on"
        );
        verify(
            String(augmentation.bootstrap.kittyListenOn)
                .indexOf("unix:@appcontrol-kitty-") === 0
        );
        compare(augmentation.leases.length, 1);
    }

    function test_existingKittyEndpointIsPreserved() {
        const evidence = kittyEvidence();
        evidence.argv = [
            "kitty",
            "-o",
            "allow_remote_control=socket-only",
            "--listen-on",
            "unix:@caller-owned"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityKittyRemote]
        );

        compare(
            augmentation.bootstrap.kittyListenOn,
            "unix:@caller-owned"
        );
        compare(augmentation.argvAfterExecutable.length, 0);
        compare(augmentation.leases.length, 1);
        compare(augmentation.leases[0].source, "caller-supplied");
    }

    function test_existingKittyEndpointGetsRemoteControlIfMissing() {
        const evidence = kittyEvidence();
        evidence.argv = [
            "kitty",
            "--listen-on",
            "unix:@caller-owned-no-remote"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityKittyRemote]
        );

        compare(augmentation.argvAfterExecutable.length, 2);
        compare(augmentation.argvAfterExecutable[0], "-o");
        compare(
            augmentation.argvAfterExecutable[1],
            "allow_remote_control=socket-only"
        );
        compare(augmentation.leases.length, 1);
        compare(augmentation.leases[0].source, "caller-supplied");
        verify(augmentation.ready);
    }

    function test_nonSocketOnlyKittyRemoteModeIsRejected() {
        const evidence = kittyEvidence();
        evidence.argv = [
            "kitty",
            "-o",
            "allow_remote_control=yes",
            "--listen-on",
            "unix:@broad-remote"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityKittyRemote]
        );

        verify(!augmentation.ready);
        compare(augmentation.appliedCapabilities.length, 0);
        compare(augmentation.leases.length, 0);
        compare(augmentation.conflicts.length, 1);
        compare(
            augmentation.conflicts[0].kind,
            "kitty-remote-control-mode"
        );
        compare(
            augmentation.conflicts[0].reason,
            "requires-socket-only"
        );
        compare(Object.keys(coordinator.leases).length, 0);
    }

    function test_accessibilityAugmentationPreservesDonorFlags() {
        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityAccessibility]
        );

        compare(augmentation.env.NO_AT_BRIDGE, "0");
        compare(augmentation.env.ACCESSIBILITY_ENABLED, "1");
        compare(augmentation.env.QT_ACCESSIBILITY, "1");
        compare(
            augmentation.env.QT_LINUX_ACCESSIBILITY_ALWAYS_ON,
            "1"
        );
        verify(
            augmentation.argvAppend.indexOf(
                "--force-renderer-accessibility=complete"
            ) !== -1
        );
    }

    function test_devtoolsPreferredPortsMatchDonorPolicy() {
        compare(
            requirements.preferredDebugPort(braveEvidence()),
            9222
        );

        compare(
            requirements.preferredDebugPort({
                displayName: "Google Chrome",
                argv: ["google-chrome"]
            }),
            9223
        );

        compare(
            requirements.preferredDebugPort({
                displayName: "Chromium",
                argv: ["chromium"]
            }),
            9224
        );

        compare(
            requirements.preferredDebugPort({
                displayName: "Visual Studio Code",
                argv: ["code"]
            }),
            9225
        );

        compare(
            requirements.preferredDebugPort({
                displayName: "VSCodium",
                argv: ["codium"]
            }),
            9226
        );
    }

    function test_devtoolsLeaseAvoidsCoordinatorCollision() {
        const first = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );
        const second = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        compare(first.bootstrap.debugPort, 9222);
        verify(second.bootstrap.debugPort !== 9222);
        verify(second.bootstrap.debugPort >= 9300);
        verify(second.bootstrap.debugPort <= 9499);
    }

    function test_appsAndRunShareOneLeaseUniverse() {
        // Simulate two independent launch domains using the same shared
        // SurfaceLaunchCoordinator singleton. Both Brave-shaped launches
        // prefer 9222; the second request must observe the first lease.
        const appsLaunch = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        const runLaunch = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        verify(appsLaunch.ready);
        verify(runLaunch.ready);
        compare(appsLaunch.bootstrap.debugPort, 9222);
        verify(runLaunch.bootstrap.debugPort !== 9222);
        verify(runLaunch.bootstrap.debugPort >= 9300);
        verify(runLaunch.bootstrap.debugPort <= 9499);

        const leaseKeys = Object.keys(coordinator.leases);
        compare(leaseKeys.length, 2);
        verify(
            coordinator.leases["devtools-port:9222"] !== undefined
        );
        verify(
            coordinator.leases[
                "devtools-port:" + String(runLaunch.bootstrap.debugPort)
            ] !== undefined
        );
    }

    function test_publicAuthoritySnapshotsAreDefensiveCopies() {
        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            [
                requirements.capabilityAccessibility,
                requirements.capabilityDevTools
            ]
        );

        verify(augmentation.ready);

        const leaseSnapshot = coordinator.leases;
        const stateSnapshot = coordinator.correlationState;

        const leaseKey =
            "devtools-port:"
            + String(augmentation.bootstrap.debugPort);

        leaseSnapshot[leaseKey].value = 1;
        stateSnapshot[augmentation.correlationId]
            .metadata.debugPort = 1;
        stateSnapshot[augmentation.correlationId]
            .appliedCapabilities.push("BROKEN");

        const freshLeases = coordinator.leases;
        const freshState = coordinator.correlationState;

        compare(
            freshLeases[leaseKey].value,
            augmentation.bootstrap.debugPort
        );
        compare(
            freshState[augmentation.correlationId]
                .metadata.debugPort,
            augmentation.bootstrap.debugPort
        );
        verify(
            freshState[augmentation.correlationId]
                .appliedCapabilities
                .indexOf("BROKEN") === -1
        );
    }

    function test_recoverySnapshotRehydratesSharedAuthorityWithoutTabs() {
        const snapshot = recovery.applySnapshot({
            observations: [
                {
                    kind: "devtools-port",
                    value: 9444,
                    providerKey: ""
                },
                {
                    kind: "kitty-listen-on",
                    value: "unix:@recovered-kitty",
                    providerKey: ""
                }
            ],
            completeKinds: [
                "devtools-port",
                "kitty-listen-on"
            ],
            errors: []
        });

        compare(snapshot.observations.length, 2);
        compare(snapshot.completeKinds.length, 2);

        const result = recovery.reconcileSharedAuthority();

        compare(result.adopted, 2);
        verify(
            coordinator.leases["devtools-port:9444"] !== undefined
        );
        verify(
            coordinator.leases[
                "kitty-listen-on:unix:@recovered-kitty"
            ] !== undefined
        );
        compare(
            coordinator.leases["devtools-port:9444"].source,
            "observed"
        );
    }

    function test_recoverySnapshotFiltersUnknownKinds() {
        const snapshot = recovery.applySnapshot({
            observations: [
                {
                    kind: "unknown-kind",
                    value: "ignored"
                },
                {
                    kind: "devtools-port",
                    value: 9555
                }
            ],
            completeKinds: [
                "unknown-kind",
                "devtools-port"
            ],
            errors: []
        });

        compare(snapshot.observations.length, 1);
        compare(snapshot.observations[0].kind, "devtools-port");
        compare(snapshot.completeKinds.length, 1);
        compare(snapshot.completeKinds[0], "devtools-port");
    }

    function test_observedDevToolsLeaseSurvivesCoordinatorRestartRecovery() {
        const recovery = coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:LIVE"
            }
        ]);

        compare(recovery.adopted, 1);
        compare(recovery.shadowed, 0);
        compare(
            coordinator.leases["devtools-port:9222"].source,
            "observed"
        );

        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        verify(augmentation.ready);
        verify(augmentation.bootstrap.debugPort !== 9222);
        verify(augmentation.bootstrap.debugPort >= 9300);
        verify(augmentation.bootstrap.debugPort <= 9499);
    }

    function test_partialObservationDoesNotPruneRecoveredLease() {
        coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:LIVE"
            }
        ]);

        coordinator.reconcileObservedInstrumentation([]);

        verify(
            coordinator.leases["devtools-port:9222"] !== undefined
        );
        compare(
            coordinator.leases["devtools-port:9222"].source,
            "observed"
        );
    }

    function test_completeDevToolsSnapshotDoesNotPruneKittyObservation() {
        coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:LIVE"
            },
            {
                kind: "kitty-listen-on",
                value: "unix:@live-kitty",
                providerKey: "kitty:7"
            }
        ]);

        const result = coordinator.reconcileObservedInstrumentation(
            [],
            { completeKinds: ["devtools-port"] }
        );

        compare(result.completeKinds.length, 1);
        compare(result.completeKinds[0], "devtools-port");

        verify(
            coordinator.leases["devtools-port:9222"] === undefined
        );
        verify(
            coordinator.leases[
                "kitty-listen-on:unix:@live-kitty"
            ] !== undefined
        );
    }

    function test_completeKittySnapshotDoesNotPruneDevToolsObservation() {
        coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:LIVE"
            },
            {
                kind: "kitty-listen-on",
                value: "unix:@live-kitty",
                providerKey: "kitty:7"
            }
        ]);

        coordinator.reconcileObservedInstrumentation(
            [],
            { completeKinds: ["kitty-listen-on"] }
        );

        verify(
            coordinator.leases["devtools-port:9222"] !== undefined
        );
        verify(
            coordinator.leases[
                "kitty-listen-on:unix:@live-kitty"
            ] === undefined
        );
    }

    function test_unknownCompleteKindsDoNotPruneObservedState() {
        coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:LIVE"
            }
        ]);

        const result = coordinator.reconcileObservedInstrumentation(
            [],
            { completeKinds: ["unknown-kind"] }
        );

        compare(result.completeKinds.length, 0);
        verify(
            coordinator.leases["devtools-port:9222"] !== undefined
        );
    }

    function test_observedLeaseReconciliationCanPruneStaleRecoveryState() {
        coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:LIVE"
            }
        ]);

        verify(
            coordinator.leases["devtools-port:9222"] !== undefined
        );

        coordinator.reconcileObservedInstrumentation(
            [],
            { complete: true }
        );

        verify(
            coordinator.leases["devtools-port:9222"] === undefined
        );

        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        compare(augmentation.bootstrap.debugPort, 9222);
    }

    function test_observationDoesNotOverwriteKnownTransactionLease() {
        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        compare(augmentation.bootstrap.debugPort, 9222);

        const recovery = coordinator.reconcileObservedInstrumentation([
            {
                kind: "devtools-port",
                value: 9222,
                providerKey: "devtools:9222:ABC"
            }
        ]);

        compare(recovery.adopted, 0);
        compare(recovery.shadowed, 1);
        compare(
            coordinator.leases["devtools-port:9222"].source,
            "generated"
        );
        compare(
            coordinator.leases["devtools-port:9222"].correlationId,
            augmentation.correlationId
        );
    }

    function test_observedKittyEndpointBlocksCallerReuse() {
        coordinator.reconcileObservedInstrumentation([
            {
                kind: "kitty-listen-on",
                value: "unix:@live-kitty",
                providerKey: "kitty:11"
            }
        ]);

        const evidence = kittyEvidence();
        evidence.argv = [
            "kitty",
            "-o",
            "allow_remote_control=socket-only",
            "--listen-on",
            "unix:@live-kitty"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityKittyRemote]
        );

        verify(!augmentation.ready);
        compare(augmentation.leases.length, 0);
        compare(augmentation.conflicts.length, 1);
        compare(
            augmentation.conflicts[0].value,
            "unix:@live-kitty"
        );
    }

    function test_releaseAllowsPreferredPortReuse() {
        const first = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        compare(first.bootstrap.debugPort, 9222);
        verify(
            coordinator.releaseCorrelation(
                first.correlationId
            )
        );

        const second = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        compare(second.bootstrap.debugPort, 9222);
    }

    function test_launchSuccessDoesNotReleaseInstrumentationLease() {
        const augmentation = coordinator.buildAugmentation(
            kittyEvidence(),
            [requirements.capabilityKittyRemote]
        );

        const before = Object.keys(coordinator.leases).length;
        compare(before, 1);

        verify(
            coordinator.markLaunchSucceeded(
                augmentation.correlationId
            )
        );

        compare(
            Object.keys(coordinator.leases).length,
            before
        );
        compare(
            coordinator.correlationState[
                augmentation.correlationId
            ].state,
            "launched"
        );
    }

    function test_accessibilityOnlyCorrelationCanReleaseWithoutLease() {
        const augmentation = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityAccessibility]
        );

        verify(augmentation.ready);
        compare(augmentation.leases.length, 0);
        verify(
            coordinator.correlationState[
                augmentation.correlationId
            ] !== undefined
        );

        verify(
            coordinator.releaseCorrelation(
                augmentation.correlationId
            )
        );
        verify(
            coordinator.correlationState[
                augmentation.correlationId
            ] === undefined
        );
    }

    function test_unknownCorrelationCannotBecomeLaunchedState() {
        verify(
            !coordinator.markLaunchSucceeded(
                "surface-not-prepared"
            )
        );
        verify(
            coordinator.correlationState[
                "surface-not-prepared"
            ] === undefined
        );
    }

    function test_launchFailureReleasesInstrumentationLease() {
        const augmentation = coordinator.buildAugmentation(
            kittyEvidence(),
            [requirements.capabilityKittyRemote]
        );

        compare(Object.keys(coordinator.leases).length, 1);

        verify(
            coordinator.markLaunchFailed(
                augmentation.correlationId
            )
        );

        compare(Object.keys(coordinator.leases).length, 0);
        verify(
            coordinator.correlationState[
                augmentation.correlationId
            ] === undefined
        );
    }

    function test_unsupportedCapabilityDoesNotMutateLaunch() {
        const augmentation = coordinator.buildAugmentation(
            {
                displayName: "Calculator",
                executable: "gnome-calculator",
                argv: ["gnome-calculator"]
            },
            [
                requirements.capabilityAccessibility,
                requirements.capabilityDevTools
            ]
        );

        compare(augmentation.appliedCapabilities.length, 0);
        compare(augmentation.unsupportedCapabilities.length, 2);
        verify(!augmentation.ready);
        compare(Object.keys(augmentation.env).length, 0);
        compare(augmentation.argvAppend.length, 0);
    }

    function test_nonLoopbackDebugAddressIsRejected() {
        const evidence = braveEvidence();
        evidence.argv = [
            "brave-browser",
            "--remote-debugging-address=0.0.0.0",
            "--remote-debugging-port=9444"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityDevTools]
        );

        verify(!augmentation.ready);
        compare(augmentation.appliedCapabilities.length, 0);
        compare(augmentation.leases.length, 0);
        compare(augmentation.conflicts.length, 1);
        compare(
            augmentation.conflicts[0].kind,
            "devtools-debug-address"
        );
        compare(
            augmentation.conflicts[0].reason,
            "requires-loopback"
        );
        compare(Object.keys(coordinator.leases).length, 0);
    }

    function test_loopbackDebugAddressIsAccepted() {
        const evidence = braveEvidence();
        evidence.argv = [
            "brave-browser",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=9444"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityDevTools]
        );

        verify(augmentation.ready);
        compare(augmentation.bootstrap.debugAddress, "127.0.0.1");
        compare(augmentation.bootstrap.debugPort, 9444);
        compare(augmentation.leases.length, 1);
        compare(augmentation.conflicts.length, 0);
    }

    function test_shellMechanismCanSupplyPreparsedDevToolsEvidence() {
        const evidence = {
            displayName: "Brave",
            executable: "brave-browser",
            argv: [
                "__APPCONTROL_SHELL__",
                "brave-browser --remote-debugging-port=9444"
            ],
            existingDebugPort: 9444,
            existingDebugAddress: "127.0.0.1"
        };

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityDevTools]
        );

        verify(augmentation.ready);
        compare(augmentation.bootstrap.debugPort, 9444);
        compare(
            augmentation.bootstrap.debugAddress,
            "127.0.0.1"
        );
        compare(augmentation.argvAppend.length, 0);
        compare(augmentation.leases.length, 1);
        compare(augmentation.leases[0].source, "caller-supplied");
    }

    function test_shellMechanismCanSupplyPreparsedKittyEvidence() {
        const evidence = {
            displayName: "Kitty",
            executable: "kitty",
            argv: [
                "__APPCONTROL_SHELL__",
                "kitty --listen-on unix:@shell-owned"
            ],
            existingKittyListenOn: "unix:@shell-owned",
            existingKittyRemoteControlMode: "socket-only"
        };

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityKittyRemote]
        );

        verify(augmentation.ready);
        compare(
            augmentation.bootstrap.kittyListenOn,
            "unix:@shell-owned"
        );
        compare(augmentation.argvAfterExecutable.length, 0);
        compare(augmentation.leases.length, 1);
        compare(augmentation.leases[0].source, "caller-supplied");
    }

    function test_preparsedBroadDebugAddressStillRejected() {
        const evidence = {
            displayName: "Brave",
            executable: "brave-browser",
            argv: [
                "__APPCONTROL_SHELL__",
                "opaque-launcher-text"
            ],
            existingDebugPort: 9444,
            existingDebugAddress: "0.0.0.0"
        };

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityDevTools]
        );

        verify(!augmentation.ready);
        compare(augmentation.leases.length, 0);
        compare(augmentation.conflicts.length, 1);
        compare(
            augmentation.conflicts[0].reason,
            "requires-loopback"
        );
    }

    function test_existingDebugAddressIsPreserved() {
        const evidence = braveEvidence();
        evidence.argv = [
            "brave-browser",
            "--remote-debugging-address=127.0.0.2",
            "--remote-debugging-port=9444"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityDevTools]
        );

        compare(
            augmentation.bootstrap.debugAddress,
            "127.0.0.2"
        );
        compare(augmentation.bootstrap.debugPort, 9444);
        compare(augmentation.leases.length, 1);
        compare(augmentation.leases[0].source, "caller-supplied");
        compare(augmentation.argvAppend.length, 0);
    }

    function test_existingDebugPortIsPreservedAndRegistered() {
        const evidence = braveEvidence();
        evidence.argv = [
            "brave-browser",
            "--remote-debugging-port=9444"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [requirements.capabilityDevTools]
        );

        compare(augmentation.bootstrap.debugPort, 9444);
        compare(augmentation.leases.length, 1);
        compare(augmentation.leases[0].source, "caller-supplied");
        verify(
            augmentation.argvAppend.indexOf(
                "--remote-debugging-port=9444"
            ) === -1
        );
    }

    function test_callerSuppliedEndpointCollisionIsReported() {
        const firstEvidence = braveEvidence();
        firstEvidence.argv = [
            "brave-browser",
            "--remote-debugging-port=9444"
        ];

        const secondEvidence = braveEvidence();
        secondEvidence.argv = [
            "brave-browser",
            "--remote-debugging-port=9444"
        ];

        const first = coordinator.buildAugmentation(
            firstEvidence,
            [requirements.capabilityDevTools]
        );
        const second = coordinator.buildAugmentation(
            secondEvidence,
            [requirements.capabilityDevTools]
        );

        compare(first.conflicts.length, 0);
        verify(first.ready);
        compare(first.appliedCapabilities.length, 1);

        compare(second.conflicts.length, 1);
        verify(!second.ready);
        compare(second.appliedCapabilities.length, 0);
        compare(second.conflicts[0].value, 9444);
        compare(
            second.conflicts[0].existingCorrelationId,
            first.correlationId
        );
    }

    function test_rejectedConflictDoesNotStrandLeaseState() {
        const first = coordinator.buildAugmentation(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        const conflictingEvidence = braveEvidence();
        conflictingEvidence.argv = [
            "brave-browser",
            "--remote-debugging-port=9222"
        ];

        const second = coordinator.buildAugmentation(
            conflictingEvidence,
            [requirements.capabilityDevTools]
        );

        verify(first.ready);
        verify(!second.ready);
        compare(second.leases.length, 0);
        compare(second.appliedCapabilities.length, 0);

        const leaseKeys = Object.keys(coordinator.leases);
        compare(leaseKeys.length, 1);
        compare(
            coordinator.leases[leaseKeys[0]].correlationId,
            first.correlationId
        );

        verify(
            coordinator.correlationState[
                second.correlationId
            ] === undefined
        );
    }

    function test_rejectedAugmentationCarriesNoExecutableMutation() {
        const evidence = braveEvidence();
        evidence.argv = [
            "brave-browser",
            "--remote-debugging-address=0.0.0.0",
            "--remote-debugging-port=9444"
        ];

        const augmentation = coordinator.buildAugmentation(
            evidence,
            [
                requirements.capabilityAccessibility,
                requirements.capabilityDevTools
            ]
        );

        verify(!augmentation.ready);
        compare(Object.keys(augmentation.env).length, 0);
        compare(augmentation.argvAfterExecutable.length, 0);
        compare(augmentation.argvAppend.length, 0);
        compare(augmentation.bootstrap.kittyListenOn, "");
        compare(augmentation.bootstrap.debugAddress, "");
        compare(augmentation.bootstrap.debugPort, 0);
        compare(augmentation.leases.length, 0);
        verify(augmentation.conflicts.length > 0);
    }

    function test_requirementsDoNotClaimSemanticIdentity() {
        const description = requirements.describe(
            braveEvidence(),
            [requirements.capabilityDevTools]
        );

        verify(description.canonicalId === undefined);
        verify(description.semanticKey === undefined);
        verify(description.desktopEntryId === undefined);
    }
}
