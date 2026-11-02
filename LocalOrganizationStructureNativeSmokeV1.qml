//@ pragma DataDir $BASE/local-org-structure-native-v1
//@ pragma StateDir $BASE/local-org-structure-native-v1
//@ pragma CacheDir $BASE/local-org-structure-native-v1
import QtQuick
import Quickshell
import qs.services.social
import "widgets/messanger"

// Unmounted CI-only genuine Quickshell fixture. No production UI launch,
// credentials, real company data, verified membership or user session.
ShellRoot {
    id: smoke
    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_STRUCTURE_NATIVE_SMOKE") || "")
        === "CI_DISPOSABLE_ONLY"
    readonly property string phase:
        String(Quickshell.env("POST_APOLLO_STRUCTURE_NATIVE_PHASE") || "")
    property int stageNumber: 0
    property bool finished: false

    IdentityCenterSettingsSections {
        id: settings
        width: 820
        height: 560
        activeSection: "ORGANIZATIONS"
        settingsOpen: smoke.armed
        localDirectoryStore: SocialOrganizationDirectoryStore
        localStructureStore: SocialLocalOrganizationStructureStore
        localPortfoliosStore: SocialLocalPortfoliosStore
        localLinksStore: SocialOrganizationLinksStore
        socialIdentitiesSnapshot: null
        socialAccountDetailsStore: null
    }

    function fail(reason) {
        if (finished) return;
        finished = true;
        console.error("ORG_STRUCTURE_NATIVE_FAIL|" + reason);
        Qt.quit();
    }
    function pass() {
        if (finished) return;
        finished = true;
        console.log("ORG_STRUCTURE_NATIVE_PASS_" + phase.toUpperCase());
        Qt.quit();
    }
    function next(ok) {
        if (!ok) {
            fail("ACTION_REFUSED_" + stageNumber);
            return;
        }
        stageNumber++;
    }
    function expected(doc) {
        return doc.schema === "post-apollo.social-local-org-structure.v1"
            && doc.revision === 8
            && doc.nextId === 6
            && doc.units.length === 5
            && doc.units[0].id === "unit-1"
            && doc.units[0].orgId === "org-1"
            && doc.units[0].kind === "division"
            && doc.units[0].name === "SYNTHETIC EDUCATION"
            && doc.units[0].archived === false
            && doc.units[1].id === "unit-2"
            && doc.units[1].orgId === "org-1"
            && doc.units[1].kind === "department"
            && doc.units[1].name === "SYNTHETIC ENGINEERING"
            && doc.units[1].archived === false
            && doc.units[2].id === "unit-3"
            && doc.units[2].orgId === "org-2"
            && doc.units[2].kind === "location"
            && doc.units[2].name === "SYNTHETIC NORTH"
            && doc.units[2].archived === false
            && doc.units[3].id === "unit-4"
            && doc.units[3].orgId === "org-3"
            && doc.units[3].kind === "team"
            && doc.units[3].name === "SYNTHETIC OPERATIONS"
            && doc.units[3].archived === false
            && doc.units[4].id === "unit-5"
            && doc.units[4].orgId === "org-1"
            && doc.units[4].kind === "location"
            && doc.units[4].name === "SYNTHETIC EAST"
            && doc.units[4].archived === false;
    }
    function advance() {
        if (!armed || finished) return;
        if (phase !== "create" && phase !== "reload") {
            fail("BAD_PHASE"); return;
        }
        const store = SocialLocalOrganizationStructureStore;
        const directory = SocialOrganizationDirectoryStore;
        if (store.state === "error" || store.state === "unsupported") {
            fail("STRUCTURE_STORAGE_" + store.errorCode); return;
        }
        if (directory.state === "error" || directory.state === "unsupported") {
            fail("DIRECTORY_STORAGE_" + directory.errorCode); return;
        }
        if (store.state !== "ready" || directory.state !== "ready")
            return;
        if (directory.saved.organizations.length !== 3) {
            fail("PARENT_ORG_COUNT"); return;
        }
        if (settings.organizationDisplayReady) {
            fail("UNVERIFIED_MEMBERSHIP"); return;
        }
        const doc = store.saved;
        if (phase === "reload") {
            if (stageNumber !== 0 || !expected(doc)) {
                fail("RELOADED_DATA_MISMATCH"); return;
            }
            pass();
            return;
        }
        if (doc.revision !== stageNumber) {
            fail("REVISION_" + stageNumber + "_GOT_" + doc.revision);
            return;
        }
        if (stageNumber === 0) {
            if (doc.units.length !== 0) { fail("EXPECTED_EMPTY"); return; }
            next(store.createUnit("org-1", "division", "SYNTHETIC HEALTH"));
        } else if (stageNumber === 1) {
            next(store.createUnit("org-1", "department", "SYNTHETIC ENGINEERING"));
        } else if (stageNumber === 2) {
            next(store.createUnit("org-2", "location", "SYNTHETIC NORTH"));
        } else if (stageNumber === 3) {
            next(store.createUnit("org-3", "team", "SYNTHETIC OPERATIONS"));
        } else if (stageNumber === 4) {
            next(store.renameUnit("unit-1", "SYNTHETIC EDUCATION"));
        } else if (stageNumber === 5) {
            next(store.archiveUnit("unit-2"));
        } else if (stageNumber === 6) {
            if (!doc.units[1].archived) { fail("ARCHIVE_NOT_SAVED"); return; }
            next(store.restoreUnit("unit-2"));
        } else if (stageNumber === 7) {
            if (doc.units[1].archived) { fail("RESTORE_NOT_SAVED"); return; }
            next(store.createUnit("org-1", "location", "SYNTHETIC EAST"));
        } else if (stageNumber === 8) {
            if (!expected(doc)) { fail("FINAL_MISMATCH"); return; }
            pass();
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed && !smoke.finished
        onTriggered: smoke.advance()
    }
    Timer {
        interval: 18000
        repeat: false
        running: smoke.armed && !smoke.finished
        onTriggered: smoke.fail("TIMEOUT_" + smoke.stageNumber)
    }
    Component.onCompleted: {
        Quickshell.watchFiles = false;
        if (!armed) Qt.quit();
    }
}
