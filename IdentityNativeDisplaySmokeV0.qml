//@ pragma DataDir $BASE/post-apollo-identity-native-smoke-v0
//@ pragma StateDir $BASE/post-apollo-identity-native-smoke-v0
//@ pragma CacheDir $BASE/post-apollo-identity-native-smoke-v0
import Quickshell
import QtQuick
import "widgets/messanger"

// UNMOUNTED NATIVE SMOKE ROOT: NEVER imported by production shell.qml.
// The only host is a disposable, synthetic, token-free Unix socket fixture.
// Quickshell itself owns the genuine Process, StdioCollector and QML engine.
// Requires exact CI_DISPOSABLE_ONLY gate; without it, nothing is activated.
ShellRoot {
    id: smoke

    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_IDENTITY_NATIVE_SMOKE") || "")
        === "CI_DISPOSABLE_ONLY"
    readonly property string scenario:
        String(Quickshell.env("POST_APOLLO_IDENTITY_NATIVE_SCENARIO") || "")
    property bool observedReady: false
    property int tabStep: 0
    property bool testSettingsOpen: smoke.armed
    property string testSection: smoke.armed ? "ORGANIZATIONS" : "SOCIAL LAYOUT"

    IdentityCenterSettingsSections {
        id: sections
        width: 820
        height: 560
        settingsOpen: smoke.testSettingsOpen
        activeSection: smoke.testSection
    }

    Timer {
        interval: 100
        repeat: true
        running: smoke.armed
        onTriggered: {
            const view = sections.organizationDisplaySnapshot;
            // Exercise the real settings-reader active binding, rather than
            // injecting data directly into any QML display property.
            if (smoke.scenario === "tab-change") {
                if (smoke.tabStep === 0 && view
                    && view.status === "READY"
                    && sections.organizationDisplayReady
                    && view.organizations.length === 2) {
                    smoke.tabStep = 1;
                    smoke.testSection = "SECURITY";
                    return;
                }
                if (smoke.tabStep === 1
                    && sections.activeSection === "SECURITY"
                    && sections.organizationDisplaySnapshot === null
                    && !sections.organizationDisplayReady) {
                    smoke.tabStep = 2;
                    smoke.testSection = "ORGANIZATIONS";
                    return;
                }
                if (smoke.tabStep === 2 && view
                    && view.status === "READY"
                    && sections.organizationDisplayReady
                    && view.organizations.length === 2
                    && view.portfolios.length === 1
                    && view.canSwitchOrganization === false) {
                    console.log("IDENTITY_NATIVE_SMOKE_PASS_TAB_CHANGE");
                    Qt.quit();
                }
                return;
            }
            if (view === null || !view)
                return;
            if (view.schema !== "post-apollo.identity.desktop-context-display.v0"
                || view.canSwitchOrganization !== false)
                return;
            if (smoke.scenario === "ready" && view.status === "READY") {
                if (!sections.organizationDisplayReady
                    || view.organizations.length !== 2
                    || view.organizations[0].organizationId !== "synthetic_llc_a"
                    || view.organizations[1].organizationId !== "synthetic_nonprofit"
                    || view.portfolios.length !== 1
                    || view.portfolios[0].organizationIds.length !== 2)
                    return;
                console.log("IDENTITY_NATIVE_SMOKE_PASS_READY");
                Qt.quit();
            }
            if (smoke.scenario === "signed-out" && view.status === "SIGNED_OUT"
                && !sections.organizationDisplayReady
                && view.organizations.length === 0
                && view.portfolios.length === 0) {
                console.log("IDENTITY_NATIVE_SMOKE_PASS_SIGNED_OUT");
                Qt.quit();
            }
            if (smoke.scenario === "missing" && view.status === "UNAVAILABLE"
                && !sections.organizationDisplayReady
                && view.organizations.length === 0) {
                console.log("IDENTITY_NATIVE_SMOKE_PASS_MISSING");
                Qt.quit();
            }
            if (smoke.scenario === "host-stop") {
                if (view.status === "READY" && view.organizations.length === 2
                    && sections.organizationDisplayReady)
                    smoke.observedReady = true;
                else if (smoke.observedReady && view.status === "UNAVAILABLE"
                         && view.organizations.length === 0
                         && view.portfolios.length === 0
                         && !sections.organizationDisplayReady) {
                    console.log("IDENTITY_NATIVE_SMOKE_PASS_HOST_STOP");
                    Qt.quit();
                }
            }
            if (smoke.scenario === "revoke") {
                if (view.status === "READY" && view.organizations.length === 2)
                    smoke.observedReady = true;
                else if (smoke.observedReady && view.status === "SIGNED_OUT"
                         && view.organizations.length === 0
                         && !sections.organizationDisplayReady) {
                    console.log("IDENTITY_NATIVE_SMOKE_PASS_REVOKE");
                    Qt.quit();
                }
            }
        }
    }

    Timer {
        interval: 16000
        running: smoke.armed
        repeat: false
        onTriggered: {
            console.error("IDENTITY_NATIVE_SMOKE_TIMEOUT");
            Qt.quit();
        }
    }

    Component.onCompleted: {
        Quickshell.watchFiles = false;
        if (!armed)
            Qt.quit();
    }
}
