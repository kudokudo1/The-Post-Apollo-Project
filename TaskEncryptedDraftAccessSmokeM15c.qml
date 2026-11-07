//@ pragma DataDir $BASE/post-apollo-tasks-m15c-native-smoke
//@ pragma StateDir $BASE/post-apollo-tasks-m15c-native-smoke
//@ pragma CacheDir $BASE/post-apollo-tasks-m15c-native-smoke
import QtQuick
import Quickshell
import "./widgets/tasks"

// TASKS M15c // disposable CI-only REAL QML control layout and state.
// This root is never imported by shell.qml or live TASKS.
// No OS credentials, editors, test-only hosts, source files or key material.
ShellRoot {
    id: smoke

    readonly property bool armed:
        String(Quickshell.env("POST_APOLLO_TASKS_M15C_NATIVE") || "")
        === "CI_DISPOSABLE_ONLY"
    property int phase: 0

    PanelWindow {
        visible: smoke.armed
        implicitWidth: 600
        implicitHeight: 530
        color: "#1B0623"
        focusable: true
        exclusiveZone: 0
        anchors { left: true; top: true }

        TaskEncryptedDraftAccessPaneM15c {
            id: accessPane
            x: 10
            y: 10
            width: parent.width - 20
            providerStatus: "SERVICE_ACQUIRED"
            providerChecking: false
            credentialActionsEnabled: false
            brokerKnown: false
            brokerGrantEnabled: false
            recoveryEnabled: false
            storageAuthorized: false
            unlockAuthorized: false
            draftHostEnabled: false
            draftHostWriteAuthorized: false
            editorStatus: "UNSAVED EDITOR CHANGE // OBSERVED"
        }
    }

    Timer {
        interval: 140
        repeat: true
        running: smoke.armed
        onTriggered: {
            var ids = ["capture","preview","clear"];
            var scopes = [
                "tasks.draft.capture.encrypted",
                "tasks.draft.preview.unlocked",
                "tasks.draft.clear.encrypted"
            ];
            if(smoke.phase < 3) {
                accessPane.selectedOperation = ids[smoke.phase];
                accessPane.requirementsChecked = true;
                var report = accessPane.statusReport;
                if(!report || report.scope!==scopes[smoke.phase] ||
                        report.status!=="TASKS CREDENTIAL PROVIDER // NOT REGISTERED" ||
                        report.operationAvailable!==false ||
                        report.draftTextRead!==false ||
                        report.draftTextTransferred!==false ||
                        report.hostAuthenticated!==false ||
                        report.keyReleaseAuthorized!==false ||
                        report.encryptedCaptureAuthorized!==false ||
                        report.encryptedPreviewAuthorized!==false ||
                        report.encryptedClearAuthorized!==false ||
                        report.sourceWriteAuthorized!==false ||
                        report.automaticReplayAuthorized!==false ||
                        report.draftClearAuthorized!==false ||
                        accessPane.canCaptureDraft!==false ||
                        accessPane.canUnlockPreview!==false ||
                        accessPane.canDeleteCheckpoint!==false) {
                    console.error("M15C_NATIVE_DEFAULT_DENY_FAILURE");
                    Qt.quit();
                    return;
                }
                smoke.phase++;
                return;
            }
            accessPane.brokerKnown = true;
            accessPane.credentialActionsEnabled = true;
            accessPane.selectedOperation = "capture";
            accessPane.requirementsChecked = true;
            if(accessPane.statusReport.status !==
                    "UNEXPECTED AUTHORITY STATE // REVIEW REQUIRED" ||
                    accessPane.statusReport.operationAvailable!==false) {
                console.error("M15C_NATIVE_UNEXPECTED_AUTHORITY_NOT_REFUSED");
            } else {
                console.log("M15C_NATIVE_THREE_SCOPES_DEFAULT_DENY_PASS");
            }
            Qt.quit();
        }
    }

    Timer {
        interval: 10000
        repeat: false
        running: smoke.armed
        onTriggered: {
            console.error("M15C_NATIVE_TIMEOUT");
            Qt.quit();
        }
    }

    Component.onCompleted: {
        Quickshell.watchFiles=false;
        if(!smoke.armed) {
            console.error("M15C_NATIVE_NOT_ARMED");
            Qt.quit();
        }
    }
}
