//@ pragma DataDir $BASE/local-branch-location-native-v1
//@ pragma StateDir $BASE/local-branch-location-native-v1
//@ pragma CacheDir $BASE/local-branch-location-native-v1
import QtQuick
import Quickshell
import qs.services.social
import "widgets/messanger"

// Unmounted synthetic-only Quickshell process fixture. No desktop identity.
ShellRoot {
    id: smoke
    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_LOCAL_BRANCH_LOCATION_SMOKE") || "")
            === "CI_DISPOSABLE_ONLY"
    readonly property string phase:
        String(Quickshell.env("POST_APOLLO_LOCAL_BRANCH_LOCATION_PHASE") || "")
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
        localLinksStore: SocialOrganizationLinksStore
        socialIdentitiesSnapshot: null
        socialAccountDetailsStore: null
    }

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("BRANCH_LOCATION_NATIVE_FAIL|" + reason);
        Qt.quit();
    }
    function pass() {
        if (done) return;
        done = true;
        console.log("BRANCH_LOCATION_NATIVE_PASS_" + phase.toUpperCase());
        Qt.quit();
    }
    function next(ok) {
        if (!ok) { fail("ACTION_REFUSED_" + stage); return; }
        stage++;
    }
    function expected(doc) {
        return doc.schema === "post-apollo.social-local-branch-location-links.v1"
            && doc.revision === 7
            && doc.nextId === 7
            && doc.links.length === 5
            && doc.links[0].id === "branch-placement-2"
            && doc.links[0].orgId === "org-1"
            && doc.links[0].branchId === "branch-4"
            && doc.links[0].locationId === "unit-2"
            && doc.links[1].id === "branch-placement-3"
            && doc.links[1].orgId === "org-1"
            && doc.links[1].branchId === "branch-7"
            && doc.links[1].locationId === "unit-1"
            && doc.links[2].id === "branch-placement-4"
            && doc.links[2].orgId === "org-2"
            && doc.links[2].branchId === "branch-5"
            && doc.links[2].locationId === "unit-3"
            && doc.links[3].id === "branch-placement-5"
            && doc.links[3].orgId === "org-3"
            && doc.links[3].branchId === "branch-6"
            && doc.links[3].locationId === "unit-4"
            && doc.links[4].id === "branch-placement-6"
            && doc.links[4].orgId === "org-1"
            && doc.links[4].branchId === "branch-7"
            && doc.links[4].locationId === "unit-2";
    }
    function advance() {
        if (!armed || done) return;
        if (phase !== "create" && phase !== "reload") {
            fail("INVALID_PHASE"); return;
        }
        const store = SocialLocalBranchLocationLinksStore;
        const d = SocialOrganizationDirectoryStore;
        const s = SocialLocalOrganizationStructureStore;
        if (store.state === "error" || d.state === "error" || s.state === "error") {
            fail("STORAGE_" + store.errorCode); return;
        }
        if (store.state !== "ready" || d.state !== "ready" || s.state !== "ready")
            return;
        if (d.saved.organizations.length !== 3
                || s.saved.units.length !== 5
                || settings.organizationDisplayReady) {
            fail("FIXTURE_OR_VERIFIED_MEMBERSHIP");
            return;
        }
        const doc = store.saved;
        if (phase === "reload") {
            if (stage !== 0 || !expected(doc))
                fail("RELOAD_MISMATCH");
            else pass();
            return;
        }
        if (doc.revision !== stage) {
            fail("REVISION_MISMATCH_" + stage + "_GOT_" + doc.revision);
            return;
        }
        if (stage === 0) {
            if (doc.links.length !== 0) { fail("NOT_EMPTY"); return; }
            next(store.linkBranch("org-1", "branch-4", "unit-1"));
        } else if (stage === 1) {
            next(store.linkBranch("org-1", "branch-4", "unit-2"));
        } else if (stage === 2) {
            next(store.linkBranch("org-1", "branch-7", "unit-1"));
        } else if (stage === 3) {
            next(store.linkBranch("org-2", "branch-5", "unit-3"));
        } else if (stage === 4) {
            next(store.linkBranch("org-3", "branch-6", "unit-4"));
        } else if (stage === 5) {
            next(store.unlinkBranch("branch-placement-1"));
        } else if (stage === 6) {
            next(store.linkBranch("org-1", "branch-7", "unit-2"));
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
