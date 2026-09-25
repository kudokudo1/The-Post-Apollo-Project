import QtQuick
import QtTest
import qs.services.surface

TestCase {
    name: "Team5SurfaceLaunchContracts"

    readonly property var requirements: SurfaceLaunchRequirements
    readonly property var coordinator: SurfaceLaunchCoordinator

    function cleanup() {
        const ids = Object.keys(coordinator.correlationState);

        for (let i = 0; i < ids.length; i++)
            coordinator.releaseCorrelation(ids[i]);
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
