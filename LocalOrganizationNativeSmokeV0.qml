//@ pragma DataDir $BASE/local-org-native-smoke-v0
//@ pragma StateDir $BASE/local-org-native-smoke-v0
//@ pragma CacheDir $BASE/local-org-native-smoke-v0
import QtQuick
import Quickshell
import qs.services.social
import "widgets/messanger"

// Unmounted real-Quickshell smoke. CI-only. No real organization authority.
ShellRoot {
    id: smoke
    readonly property bool armed: String(Quickshell.env("POST_APOLLO_LOCAL_ORG_SMOKE") || "") === "CI_DISPOSABLE_ONLY"
    readonly property string phase: String(Quickshell.env("POST_APOLLO_LOCAL_ORG_PHASE") || "")
    property int stageNumber: 0
    property bool finished: false

    IdentityCenterSettingsSections {
        id: settings
        width: 820
        height: 560
        settingsOpen: smoke.armed
        activeSection: "ORGANIZATIONS"
        localDirectoryStore: SocialOrganizationDirectoryStore
    }

    function failure(reason) {
        if (finished) return;
        finished = true;
        console.error("LOCAL_ORG_NATIVE_FAIL|" + reason);
        Qt.quit();
    }
    function success() {
        if (finished) return;
        finished = true;
        console.log("LOCAL_ORG_NATIVE_PASS_" + phase.toUpperCase());
        Qt.quit();
    }
    function next(accepted) {
        if (!accepted) {
            failure("EDIT_REFUSED_" + stageNumber);
            return;
        }
        stageNumber += 1;
    }
    function finalDocument(doc) {
        return doc.revision === 9 && doc.nextId === 4
            && doc.organizations.length === 2
            && doc.organizations[0].id === "org-1"
            && doc.organizations[0].name === "SYNTHETIC LLC RENAMED"
            && doc.organizations[0].kind === "llc"
            && doc.organizations[0].archived === false
            && doc.organizations[0].branches.length === 1
            && doc.organizations[0].branches[0].id === "branch-3"
            && doc.organizations[0].branches[0].name === "SYNTHETIC PROGRAM"
            && doc.organizations[0].branches[0].archived === false
            && doc.organizations[1].id === "org-2"
            && doc.organizations[1].name === "SYNTHETIC NONPROFIT"
            && doc.organizations[1].kind === "nonprofit"
            && doc.organizations[1].archived === false;
    }
    function advance() {
        if (!armed || finished) return;
        if (phase !== "create" && phase !== "reload") {
            failure("INVALID_PHASE"); return;
        }
        const store = SocialOrganizationDirectoryStore;
        if (store.state === "error" || store.state === "unsupported") {
            failure("STORAGE_" + store.errorCode); return;
        }
        if (store.state !== "ready") return;
        if (settings.organizationDisplayReady) {
            failure("UNVERIFIED_MEMBERSHIP"); return;
        }
        const doc = store.saved;
        if (phase === "reload") {
            if (finalDocument(doc)) success();
            else failure("RELOAD_MISMATCH");
            return;
        }
        // Every command is followed by a distinct saved revision. No optimistic
        // completion is accepted, and no second writer starts while saving.
        if (doc.revision !== stageNumber) {
            failure("REVISION_MISMATCH_" + stageNumber); return;
        }
        if (stageNumber === 0) {
            if (doc.organizations.length !== 0) { failure("NOT_INITIAL_EMPTY"); return; }
            next(store.addOrganization("SYNTHETIC LLC", "llc"));
        } else if (stageNumber === 1) {
            next(store.addOrganization("SYNTHETIC NONPROFIT", "nonprofit"));
        } else if (stageNumber === 2) {
            next(store.addBranch("org-1", "SYNTHETIC BRANCH"));
        } else if (stageNumber === 3) {
            next(store.renameBranch("org-1", "branch-3", "SYNTHETIC PROGRAM"));
        } else if (stageNumber === 4) {
            next(store.archiveBranch("org-1", "branch-3"));
        } else if (stageNumber === 5) {
            if (!doc.organizations[0].branches[0].archived) { failure("BRANCH_NOT_ARCHIVED"); return; }
            next(store.restoreBranch("org-1", "branch-3"));
        } else if (stageNumber === 6) {
            next(store.renameOrganization("org-1", "SYNTHETIC LLC RENAMED"));
        } else if (stageNumber === 7) {
            next(store.archiveOrganization("org-1"));
        } else if (stageNumber === 8) {
            if (!doc.organizations[0].archived) { failure("ORG_NOT_ARCHIVED"); return; }
            next(store.restoreOrganization("org-1"));
        } else if (stageNumber === 9) {
            if (finalDocument(doc)) success();
            else failure("FINAL_MISMATCH");
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
        onTriggered: smoke.failure("TIMEOUT_" + smoke.stageNumber)
    }
    Component.onCompleted: {
        Quickshell.watchFiles = false;
        if (!armed) Qt.quit();
    }
}
