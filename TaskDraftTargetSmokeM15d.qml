//@ pragma DataDir $BASE/post-apollo-tasks-m15d-native-smoke
//@ pragma StateDir $BASE/post-apollo-tasks-m15d-native-smoke
//@ pragma CacheDir $BASE/post-apollo-tasks-m15d-native-smoke
import QtQuick
import Quickshell
import "./widgets/tasks"

// TASKS M15d // true Quickshell UI evaluation in disposable Xvfb CI only.
// Not mounted in shell.qml; all editor signals are invented booleans.
// No task data, keyring, network, source writer or credential provider.
ShellRoot {
    id: smoke

    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_TASKS_M15D_NATIVE") || "")
            === "CI_DISPOSABLE_ONLY"
    property int step: 0
    property var signals: ({
        entryDirty:true,detailsDirty:true,
        entrySavePending:false,detailsSavePending:false,
        sourceState:"ready"
    })

    PanelWindow {
        visible: smoke.armed
        implicitWidth: 640
        implicitHeight: 590
        color: "#1B0623"
        focusable: true
        exclusiveZone: 0
        anchors {left:true;top:true}

        TaskEncryptedDraftAccessPaneM15c {
            id: access
            x: 10
            y: 10
            width: parent.width - 20
            editorSignals: smoke.signals
            selectedOperation: "capture"
            editorStatus: "UNSAVED EDITOR CHANGE // OBSERVED"
            credentialActionsEnabled: false
            brokerKnown: false
            brokerGrantEnabled: false
            recoveryEnabled: false
            storageAuthorized: false
            unlockAuthorized: false
            draftHostEnabled: false
            draftHostWriteAuthorized: false
        }
    }

    function denied(report) {
        return report && report.captureAuthorized===false &&
            report.taskTextRead===false &&
            report.taskTextTransferred===false &&
            report.keyReleaseAuthorized===false &&
            report.checkpointCreated===false &&
            report.sourceWriteAuthorized===false &&
            access.canCaptureDraft===false &&
            access.statusReport.operationAvailable===false;
    }

    Timer {
        interval: 180
        repeat: true
        running: smoke.armed
        onTriggered: {
            var report=access.draftSelection;
            if(!smoke.denied(report)) {
                console.error("M15D_NATIVE_AUTHORITY_BYPASS");
                Qt.quit();
                return;
            }
            if(smoke.step===0) {
                if(report.state!=="BOTH_DIRTY_CHOOSE_ONE" ||
                        report.selectedTarget!=="none") {
                    console.error("M15D_NATIVE_AMBIGUOUS_SELECTION_FAILED");
                    Qt.quit();return;
                }
                access.selectedDraftTarget="entry";
            } else if(smoke.step===1) {
                if(report.state!=="ENTRY_SELECTED") {
                    console.error("M15D_NATIVE_ENTRY_FAILED");
                    Qt.quit();return;
                }
                access.selectedDraftTarget="details";
            } else if(smoke.step===2) {
                if(report.state!=="DETAILS_SELECTED") {
                    console.error("M15D_NATIVE_DETAILS_FAILED");
                    Qt.quit();return;
                }
                smoke.signals={
                    entryDirty:true,detailsDirty:true,
                    entrySavePending:true,detailsSavePending:false,
                    sourceState:"saving"
                };
            } else if(smoke.step===3) {
                if(report.state!=="SAVE_IN_PROGRESS") {
                    console.error("M15D_NATIVE_PENDING_SAVE_NOT_REFUSED");
                    Qt.quit();return;
                }
                smoke.signals={
                    entryDirty:true,detailsDirty:false,
                    entrySavePending:false,detailsSavePending:false,
                    sourceState:"ready"
                };
            } else if(smoke.step===4) {
                if(report.state!=="SELECTED_EDITOR_CLEAN") {
                    console.error("M15D_NATIVE_STALE_SELECTION_NOT_REFUSED");
                    Qt.quit();return;
                }
                console.log("M15D_NATIVE_EXPLICIT_EDITOR_SELECTION_NO_CAPTURE_PASS");
                Qt.quit();
                return;
            }
            smoke.step++;
        }
    }

    Timer {
        interval: 12000
        running: smoke.armed
        repeat: false
        onTriggered: {
            console.error("M15D_NATIVE_TIMEOUT");
            Qt.quit();
        }
    }

    Component.onCompleted: {
        Quickshell.watchFiles=false;
        if(!smoke.armed) {
            console.error("M15D_NATIVE_NOT_ARMED");
            Qt.quit();
        }
    }
}
