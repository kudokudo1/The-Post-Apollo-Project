import QtQuick
import QtTest
import "../../services/surface"

TestCase {
    name: "Team5SurfaceLaunchContracts"

    SurfaceLaunchRequirements {
        id: requirements
    }

    SurfaceLaunchCoordinator {
        id: coordinator
        requirements: requirements
    }

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
        compare(augmentation.leases.length, 0);
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

        coordinator.markLaunchSucceeded(
            augmentation.correlationId
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

    function test_launchFailureReleasesInstrumentationLease() {
        const augmentation = coordinator.buildAugmentation(
            kittyEvidence(),
            [requirements.capabilityKittyRemote]
        );

        compare(Object.keys(coordinator.leases).length, 1);

        coordinator.markLaunchFailed(
            augmentation.correlationId
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
        compare(Object.keys(augmentation.env).length, 0);
        compare(augmentation.argvAppend.length, 0);
    }

    function test_existingDebugPortIsPreservedWithoutLease() {
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
        compare(augmentation.leases.length, 0);
        verify(
            augmentation.argvAppend.indexOf(
                "--remote-debugging-port=9444"
            ) === -1
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
