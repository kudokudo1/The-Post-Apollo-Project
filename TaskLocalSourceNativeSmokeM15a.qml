//@ pragma DataDir $BASE/post-apollo-tasks-m15a-native-smoke
//@ pragma StateDir $BASE/post-apollo-tasks-m15a-native-smoke
//@ pragma CacheDir $BASE/post-apollo-tasks-m15a-native-smoke
import QtQuick
import Quickshell
import "./widgets/tasks"

// TASKS M15a // CI-ONLY genuine QML/Process test of the actual mounted UI.
// Not imported by shell.qml. No access to production TASKS source or keyring.
ShellRoot {
    id: smoke

    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_TASKS_M15A_NATIVE") || "")
        === "CI_DISPOSABLE_ONLY"
    readonly property string scenario:
        String(Quickshell.env("POST_APOLLO_TASKS_M15A_SCENARIO") || "")
    readonly property string sourceFile:
        String(Quickshell.env("POST_APOLLO_TASKS_M15A_SOURCE") || "")
    property bool attempted: false

    PanelWindow {
        visible: smoke.armed
        implicitWidth: 580
        implicitHeight: 360
        color: "#1B0623"
        focusable: true
        exclusiveZone: 0
        anchors { left: true; top: true }

        TaskLocalSourceInspectPaneM15a {
            id: sourcePane
            width: parent.width - 20
            x: 10
            y: 10
            sourcePath: smoke.sourceFile
            saveRequestCount: 0
            saveInProgress: false
        }
    }

    Timer {
        interval: 90
        repeat: true
        running: smoke.armed
        onTriggered: {
            if (!smoke.attempted) {
                smoke.attempted=true;
                if (!sourcePane.inspect()) {
                    console.error("M15A_NATIVE_START_REFUSED");
                    Qt.quit();
                }
                return;
            }
            if (sourcePane.busy)
                return;
            var expected={
                valid:"SOURCE_STRUCTURALLY_READABLE",
                missing:"SOURCE_MISSING",
                malformed:"SOURCE_INVALID_JSON",
                permissions:"SOURCE_PERMISSION_REVIEW",
                symlink:"SOURCE_UNSAFE"
            };
            var v=sourcePane.report;
            if (v && v.state===expected[smoke.scenario] &&
                    v.writeAuthorized===false &&
                    v.savedAcknowledged===false &&
                    v.canReplay===false &&
                    v.canRestore===false &&
                    v.canClearDraft===false &&
                    v.canReleaseKey===false &&
                    v.sourceRevisionVerified===false &&
                    v.draftDisposition==="KEEP UNSAVED DRAFT" &&
                    (smoke.scenario!=="valid" ||
                     v.countLabel.indexOf("TASKS 1")>=0)) {
                console.log("M15A_NATIVE_PASS_"+smoke.scenario.toUpperCase());
            } else {
                console.error("M15A_NATIVE_BAD_SOURCE_REVIEW");
            }
            Qt.quit();
        }
    }

    Timer {
        interval: 12000
        running: smoke.armed
        repeat: false
        onTriggered: {
            console.error("M15A_NATIVE_TIMEOUT");
            Qt.quit();
        }
    }

    Component.onCompleted: {
        Quickshell.watchFiles=false;
        if (!smoke.armed ||
                ["valid","missing","malformed","permissions","symlink"]
                .indexOf(smoke.scenario)<0 ||
                !/^\/.+\/apollo-hub-todo-v1\.json$/.test(smoke.sourceFile)) {
            console.error("M15A_NATIVE_NOT_ARMED");
            Qt.quit();
        }
    }
}
