//@ pragma DataDir $BASE/local-unit-location-native-v1
//@ pragma StateDir $BASE/local-unit-location-native-v1
//@ pragma CacheDir $BASE/local-unit-location-native-v1
import QtQuick
import Quickshell
import qs.services.social
import "widgets/messanger"

// Genuine Quickshell, unmounted, CI-disposable-only synthetic fixture.
ShellRoot {
    id: smoke
    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_LOCAL_UNIT_LOCATION_SMOKE") || "")
            === "CI_DISPOSABLE_ONLY"
    readonly property string phase:
        String(Quickshell.env("POST_APOLLO_LOCAL_UNIT_LOCATION_PHASE") || "")
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
        localLinksStore: SocialOrganizationLinksStore
        socialIdentitiesSnapshot: null
        socialAccountDetailsStore: null
    }

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("UNIT_LOCATION_NATIVE_FAIL|" + reason);
        Qt.quit();
    }
    function pass() {
        if (done) return;
        done = true;
        console.log("UNIT_LOCATION_NATIVE_PASS_" + phase.toUpperCase());
        Qt.quit();
    }
    function next(ok) {
        if (!ok) {
            fail("ACTION_REFUSED_" + stage);
            return;
        }
        stage++;
    }
    function expected(doc) {
        return doc.schema === "post-apollo.social-local-unit-location-links.v1"
            && doc.revision === 7
            && doc.nextId === 7
            && doc.links.length === 5
            && doc.links[0].id === "placement-2"
            && doc.links[0].orgId === "org-1"
            && doc.links[0].functionId === "unit-1"
            && doc.links[0].locationId === "unit-4"
            && doc.links[1].id === "placement-3"
            && doc.links[1].orgId === "org-1"
            && doc.links[1].functionId === "unit-2"
            && doc.links[1].locationId === "unit-3"
            && doc.links[2].id === "placement-4"
            && doc.links[2].orgId === "org-2"
            && doc.links[2].functionId === "unit-5"
            && doc.links[2].locationId === "unit-6"
            && doc.links[3].id === "placement-5"
            && doc.links[3].orgId === "org-3"
            && doc.links[3].functionId === "unit-7"
            && doc.links[3].locationId === "unit-8"
            && doc.links[4].id === "placement-6"
            && doc.links[4].orgId === "org-1"
            && doc.links[4].functionId === "unit-2"
            && doc.links[4].locationId === "unit-4";
    }
    function advance() {
        if (!armed || done) return;
        if (phase !== "create" && phase !== "reload") {
            fail("INVALID_PHASE");
            return;
        }
        const store = SocialLocalUnitLocationLinksStore;
        const directory = SocialOrganizationDirectoryStore;
        const structure = SocialLocalOrganizationStructureStore;
        if (store.state === "error" || directory.state === "error"
                || structure.state === "error") {
            fail("STORE_ERROR_" + store.errorCode + "_" + directory.errorCode);
            return;
        }
        if (store.state !== "ready" || directory.state !== "ready"
                || structure.state !== "ready")
            return;
        if (directory.saved.organizations.length !== 3
                || structure.saved.units.length !== 8
                || settings.organizationDisplayReady) {
            fail("INPUT_FIXTURE_OR_VERIFIED_MEMBERSHIP");
            return;
        }
        const doc = store.saved;
        if (phase === "reload") {
            if (stage !== 0 || !expected(doc)) {
                fail("RELOAD_MISMATCH");
                return;
            }
            pass();
            return;
        }
        if (doc.revision !== stage) {
            fail("REVISION_MISMATCH_" + stage + "_GOT_" + doc.revision);
            return;
        }
        if (stage === 0) {
            if (doc.links.length !== 0) { fail("EXPECTED_EMPTY"); return; }
            next(store.linkToLocation("org-1", "unit-1", "unit-3"));
        } else if (stage === 1) {
            next(store.linkToLocation("org-1", "unit-1", "unit-4"));
        } else if (stage === 2) {
            next(store.linkToLocation("org-1", "unit-2", "unit-3"));
        } else if (stage === 3) {
            next(store.linkToLocation("org-2", "unit-5", "unit-6"));
        } else if (stage === 4) {
            next(store.linkToLocation("org-3", "unit-7", "unit-8"));
        } else if (stage === 5) {
            next(store.unlinkFromLocation("placement-1"));
        } else if (stage === 6) {
            next(store.linkToLocation("org-1", "unit-2", "unit-4"));
        } else if (stage === 7) {
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
