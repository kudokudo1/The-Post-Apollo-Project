import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

// Private local backups of organization LABEL stores only. The restore
// replacement action is intentionally DISABLED pending safe transaction work.
Column {
    id: backupPanel
    property var directoryStore: null
    property var portfolioStore: null
    property var structureStore: null
    property var functionLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null

    property bool busy: false
    property string operation: ""
    property string readText: ""
    property string selectedBackup: ""
    property var backups: []
    property string resultKind: "neutral"
    property string resultText: "No backup operation has been run."
    signal activityObserved(string kind, string detail)
    readonly property bool sourcesReady: [
        directoryStore, portfolioStore, structureStore,
        functionLocationStore, branchLocationStore, reportingStore,
        socialLinksStore
    ].every(function(store) {
        return store !== null && store.state === "ready";
    })
    spacing: 6

    function runAction(action) {
        if (busy || !["list", "create", "verify"].includes(action))
            return false;
        if (action === "create" && !sourcesReady) {
            resultKind = "error";
            resultText = "BACKUP BLOCKED // Wait for all seven stores to be ready.";
            return false;
        }
        if (action === "verify" && (selectedBackup === ""
            || backups.indexOf(selectedBackup) === -1)) {
            resultKind = "error";
            resultText = "VALIDATION BLOCKED // Select a listed backup.";
            return false;
        }
        operation = action;
        readText = "";
        busy = true;
        resultKind = "busy";
        resultText = action === "create" ? "BACKUP WORKING // Snapshot not yet confirmed."
            : action === "verify" ? "VALIDATING // Restore not enabled."
            : "LISTING // Private local backups.";
        backupProcess.running = true;
        return true;
    }
    function acceptResponse(exitCode) {
        let response = null;
        try { response = JSON.parse(readText); } catch (error) {}
        const success = exitCode === 0 && response && response.ok === true;
        busy = false;
        if (!success) {
            resultKind = "error";
            resultText = "BACKUP ERROR // " +
                (response && response.error ? String(response.error) : "UNAVAILABLE");
            backupPanel.activityObserved("failure", resultText);
            return;
        }
        if (operation === "list") {
            backups = Array.isArray(response.backups) ? response.backups : [];
            if (!backups.includes(selectedBackup))
                selectedBackup = "";
            resultKind = "loaded";
            resultText = "BACKUPS LISTED // " + String(response.total)
                + " private snapshot(s).";
            backupPanel.activityObserved("listing", resultText);
        } else if (operation === "create") {
            const name = String(response.backup || "");
            if (name === "") {
                resultKind = "error";
                resultText = "BACKUP ERROR // MISSING_FILENAME";
                backupPanel.activityObserved("failure", resultText);
                return;
            }
            backups = [name].concat(backups.filter(function(item) {
                return item !== name;
            })).sort().reverse();
            selectedBackup = name;
            resultKind = "saved";
            resultText = "BACKUP CREATED // " + name +
                " // All seven local organization record groups snapshotted.";
            backupPanel.activityObserved("backup", resultText);
        } else if (operation === "verify") {
            resultKind = "verified";
            resultText = "VALID BACKUP // " + String(response.backup) +
                " // Schema and checksums verified. RESTORE NOT ENABLED.";
            backupPanel.activityObserved("validation", resultText);
        }
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "LOCAL ORGANIZATION BACKUP // PRIVATE RECORDS"
        color: Colors.yellow
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Seven local organization label files only. Saved privately under " +
              "post-apollo/social/organization-backups-v1. No provider logins " +
              "or account contact details are included."
        color: Colors.white
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 6
        IdentityCenterLocalActionButton {
            role: "manage"
            objectName: "orgBackupCreateButton"
            width: 155
            height: 28
            label: "BACK UP NOW"
            labelPixelSize: 9
            interactive: !backupPanel.busy && backupPanel.sourcesReady
            onTriggered: backupPanel.runAction("create")
        }
        IdentityCenterLocalActionButton {
            role: "navigate"
            objectName: "orgBackupListButton"
            width: 155
            height: 28
            label: "LIST BACKUPS"
            labelPixelSize: 9
            interactive: !backupPanel.busy
            onTriggered: backupPanel.runAction("list")
        }
    }
    Text {
        width: parent.width
        visible: !backupPanel.sourcesReady
        text: "BACKUP NOT READY // Wait for all seven local stores to finish " +
              "loading or saving before creating a consistent snapshot."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "SAVED BACKUPS // " + backupPanel.backups.length
        color: Colors.cyan
        font.pixelSize: 10
        font.bold: true
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: backupPanel.backups
        delegate: IdentityCenterLocalActionButton {
            role: "neutral"
            required property string modelData
            width: Math.min(275, backupPanel.width - 8)
            height: 28
            label: modelData
            labelPixelSize: 9
            selected: backupPanel.selectedBackup === modelData
            interactive: !backupPanel.busy
            onTriggered: backupPanel.selectedBackup = modelData
        }
    }
    Flow {
        width: parent.width
        height: childrenRect.height
        spacing: 6
        IdentityCenterLocalActionButton {
            role: "refresh"
            objectName: "orgBackupValidateButton"
            width: 171
            height: 28
            label: "VALIDATE FOR RESTORE"
            labelPixelSize: 9
            interactive: !backupPanel.busy && backupPanel.selectedBackup !== ""
            onTriggered: backupPanel.runAction("verify")
        }
        IdentityCenterLocalActionButton {
            role: "danger"
            objectName: "orgBackupRestoreLockedButton"
            width: 172
            height: 28
            label: "RESTORE // LOCKED"
            labelPixelSize: 9
            interactive: false
        }
    }
    Text {
        objectName: "orgBackupResult"
        width: parent.width
        text: backupPanel.resultText
        color: backupPanel.resultKind === "error" ? Colors.red
             : backupPanel.resultKind === "verified" ? Colors.green
             : backupPanel.resultKind === "saved" ? Colors.yellow
             : backupPanel.resultKind === "busy" ? Colors.orange
             : Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Restoring seven files needs reviewed concurrency and rollback. " +
              "Validation never replaces records. This is local planning data, " +
              "not verified company access."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }

    Process {
        id: backupProcess
        objectName: "orgBackupProcess"
        running: false
        command: ["/usr/bin/python3",
            Quickshell.shellPath("services/social/SocialLocalOrgBackup.py"),
            backupPanel.operation].concat(backupPanel.operation === "verify"
            ? [backupPanel.selectedBackup] : [])
        stdout: StdioCollector {
            onStreamFinished: backupPanel.readText = String(text || "")
        }
        onExited: function(exitCode) {
            backupPanel.acceptResponse(exitCode)
        }
    }
}
