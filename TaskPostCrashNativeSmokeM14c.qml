//@ pragma DataDir $BASE/post-apollo-tasks-m14c-native-smoke
//@ pragma StateDir $BASE/post-apollo-tasks-m14c-native-smoke
//@ pragma CacheDir $BASE/post-apollo-tasks-m14c-native-smoke
import QtQuick
import Quickshell
import "./tests/tasks/fixtures"

// TASKS M14c // REAL native Quickshell CI root, NEVER imported by shell.qml.
// This is separate from M14b's MANUAL standalone test panel. Only here
// may a disposable CI marker trigger automatic inspection. All real TASKS,
// credentials, task writers and the operator's desktop remain inaccessible.
ShellRoot {
    id: smoke

    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_TASKS_M14C_NATIVE") || "")
        === "CI_DISPOSABLE_ONLY"
    readonly property string scenario:
        String(Quickshell.env("POST_APOLLO_TASKS_M14C_SCENARIO") || "")
    readonly property string fixture:
        String(Quickshell.env("POST_APOLLO_TASKS_M14C_FIXTURE") || "")
    property bool started: false

    TaskPostCrashReviewLabM14b {
        id: reviewLab
    }

    function success() {
        var report=reviewLab.resultProjection;
        var powerDenied=report && report.canReplay===false &&
            report.canRestore===false && report.canClearDraft===false &&
            report.canWriteTasks===false &&
            report.nativeSaveAcknowledged===false &&
            report.keyReleaseAuthorized===false;
        if(!powerDenied)
            return false;
        if(scenario==="baseline" || scenario==="expected" ||
                scenario==="settled") {
            var titles={
                baseline:"SOURCE STILL UNCHANGED",
                expected:"NEW BYTES // UNSETTLED RECEIPT",
                settled:"RECEIPT SETTLED / UI NOT ACKNOWLEDGED"
            };
            return reviewLab.status===
                "SYNTHETIC SOURCE OBSERVATION // REVIEW ONLY" &&
                report.origin==="SYNTHETIC FIXTURE ONLY // NOT LIVE" &&
                report.title===titles[scenario] &&
                report.draftStatus==="KEEP UNSAVED DRAFT";
        }
        if(scenario==="unsafe" || scenario==="missing" ||
                scenario==="locked") {
            return reviewLab.status===
                "REFUSED // SOURCE EVIDENCE UNVERIFIED" &&
                report.origin==="SYNTHETIC FIXTURE // UNVERIFIED" &&
                report.title==="SAVE STATE NOT VERIFIED";
        }
        return false;
    }

    Timer {
        interval: 75
        repeat: true
        running: smoke.armed
        onTriggered: {
            if(!smoke.started) {
                smoke.started=true;
                reviewLab.fixtureDbPath=smoke.fixture;
                if(!reviewLab.inspectOnce()) {
                    console.error("M14C_NATIVE_REFUSED_TO_START");
                    Qt.quit();
                }
                return;
            }
            if(reviewLab.inFlight)
                return;
            if(smoke.success()) {
                console.log("M14C_NATIVE_PASS_"+smoke.scenario.toUpperCase());
                Qt.quit();
            } else {
                console.error("M14C_NATIVE_REFUSED_OR_BAD_CLASSIFICATION");
                Qt.quit();
            }
        }
    }

    Timer {
        interval: 18000
        repeat: false
        running: smoke.armed
        onTriggered: {
            console.error("M14C_NATIVE_TIMEOUT");
            Qt.quit();
        }
    }

    Component.onCompleted: {
        Quickshell.watchFiles=false;
        if(!smoke.armed ||
            ["baseline","expected","settled","unsafe","missing","locked"]
            .indexOf(smoke.scenario)<0 ||
            !reviewLab.fixtureOnlyPath(smoke.fixture)) {
            console.error("M14C_NATIVE_NOT_ARMED");
            Qt.quit();
        }
    }
}
