//@ pragma DataDir $BASE/local-functional-reporting-native-v1
//@ pragma StateDir $BASE/local-functional-reporting-native-v1
//@ pragma CacheDir $BASE/local-functional-reporting-native-v1
import QtQuick
import Quickshell
import qs.services.social
import "widgets/messanger"

// Real Quickshell only in disposable CI; never mounted by shell.qml.
ShellRoot {
    id: smoke
    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_FUNCTIONAL_REPORTING_SMOKE") || "")
            === "CI_DISPOSABLE_ONLY"
    readonly property string phase:
        String(Quickshell.env("POST_APOLLO_FUNCTIONAL_REPORTING_PHASE") || "")
    property int stage: 0
    property bool done: false

    IdentityCenterSettingsSections {
        id: settings
        width: 820
        height: 560
        settingsOpen: smoke.armed
        activeSection: "ORGANIZATIONS"
        localDirectoryStore: SocialOrganizationDirectoryStore
        localPortfoliosStore: SocialLocalPortfoliosStore
        localStructureStore: SocialLocalOrganizationStructureStore
        localUnitLocationLinksStore: SocialLocalUnitLocationLinksStore
        localBranchLocationLinksStore: SocialLocalBranchLocationLinksStore
        localFunctionalReportingStore: SocialLocalFunctionalReportingStore
        localLinksStore: SocialOrganizationLinksStore
        socialIdentitiesSnapshot: null
        socialAccountDetailsStore: null
    }

    function fail(message) {
        if (done) return;
        done = true;
        console.error("FUNCTION_REPORTING_NATIVE_FAIL|" + message);
        Qt.quit();
    }
    function pass() {
        if (done) return;
        done = true;
        console.log("FUNCTION_REPORTING_NATIVE_PASS_" + phase.toUpperCase());
        Qt.quit();
    }
    function next(result) {
        if (!result) { fail("ACTION_REFUSED_" + stage); return; }
        stage++;
    }
    function expected(doc) {
        return doc.schema === "post-apollo.social-local-functional-reporting.v1"
            && doc.revision === 8
            && doc.nextId === 8
            && doc.links.length === 6
            && doc.links[0].id === "report-link-1"
            && doc.links[0].orgId === "org-1"
            && doc.links[0].parentId === "unit-1"
            && doc.links[0].childId === "unit-2"
            && doc.links[1].id === "report-link-2"
            && doc.links[1].orgId === "org-1"
            && doc.links[1].parentId === "unit-2"
            && doc.links[1].childId === "unit-3"
            && doc.links[2].id === "report-link-3"
            && doc.links[2].orgId === "org-1"
            && doc.links[2].parentId === "unit-4"
            && doc.links[2].childId === "unit-3"
            && doc.links[3].id === "report-link-5"
            && doc.links[3].orgId === "org-2"
            && doc.links[3].parentId === "unit-5"
            && doc.links[3].childId === "unit-6"
            && doc.links[4].id === "report-link-6"
            && doc.links[4].orgId === "org-3"
            && doc.links[4].parentId === "unit-7"
            && doc.links[4].childId === "unit-8"
            && doc.links[5].id === "report-link-7"
            && doc.links[5].orgId === "org-1"
            && doc.links[5].parentId === "unit-4"
            && doc.links[5].childId === "unit-2";
    }
    function advance() {
        if (!armed || done) return;
        if (phase !== "create" && phase !== "reload") {
            fail("INVALID_PHASE"); return;
        }
        const store = SocialLocalFunctionalReportingStore;
        const d = SocialOrganizationDirectoryStore;
        const s = SocialLocalOrganizationStructureStore;
        if (store.state === "error" || d.state === "error" || s.state === "error") {
            fail("STORE_" + store.errorCode); return;
        }
        if (store.state !== "ready" || d.state !== "ready" || s.state !== "ready")
            return;
        if (d.saved.organizations.length !== 3
                || s.saved.units.length !== 9
                || settings.organizationDisplayReady) {
            fail("FIXTURE_OR_VERIFIED_MEMBERSHIP"); return;
        }
        const doc = store.saved;
        if (phase === "reload") {
            if (stage !== 0 || !expected(doc)) fail("RELOAD_MISMATCH");
            else pass();
            return;
        }
        if (doc.revision !== stage) {
            fail("REVISION_" + stage + "_GOT_" + doc.revision); return;
        }
        if (stage === 0) {
            if (doc.links.length !== 0) { fail("NOT_EMPTY"); return; }
            next(store.addRelationship("org-1", "unit-1", "unit-2"));
        } else if (stage === 1) {
            next(store.addRelationship("org-1", "unit-2", "unit-3"));
        } else if (stage === 2) {
            next(store.addRelationship("org-1", "unit-4", "unit-3"));
        } else if (stage === 3) {
            next(store.addRelationship("org-1", "unit-1", "unit-4"));
        } else if (stage === 4) {
            next(store.addRelationship("org-2", "unit-5", "unit-6"));
        } else if (stage === 5) {
            next(store.addRelationship("org-3", "unit-7", "unit-8"));
        } else if (stage === 6) {
            next(store.removeRelationship("report-link-4"));
        } else if (stage === 7) {
            next(store.addRelationship("org-1", "unit-4", "unit-2"));
        } else if (stage === 8) {
            if (!expected(doc)) fail("FINAL_MISMATCH");
            else pass();
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: smoke.advance()
    }
    Timer {
        interval: 18000
        repeat: false
        running: smoke.armed && !smoke.done
        onTriggered: smoke.fail("TIMEOUT_" + smoke.stage)
    }
    Component.onCompleted: {
        Quickshell.watchFiles = false;
        if (!armed) Qt.quit();
    }
}
