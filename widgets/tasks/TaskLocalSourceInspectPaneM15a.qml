import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "TaskLocalSourceInspectPolicyM15a.js" as SourcePolicy

// TASKS M15a // LIVE read-only, manual source structure check.
// It NEVER captures draft text, observes a storage directory automatically,
// reads a key, modifies the JSON source, or grants a save acknowledgment.
Column {
    id: sourceCheck
    width: parent ? parent.width : 400
    spacing: 8

    // Must be bound by the existing RECOVERY parent to the canonical
    // ApolloHubTodoStore.storagePath, not user-entered arbitrary paths.
    property string sourcePath: ""
    property int saveRequestCount: 0
    property bool saveInProgress: false
    property bool busy: false
    property bool replySeen: false
    property bool malformed: false
    property var pendingResult: null
    property int requestAtStart: -1
    property var report: SourcePolicy.notChecked()

    readonly property bool encryptedRecoveryEnabled: false
    readonly property bool trustedSourceOwnerVerified: false
    readonly property bool savedUserEditAcknowledged: false
    readonly property bool canClearDraft: false
    readonly property bool canWriteTaskSource: false
    readonly property bool canReleaseKey: false

    function inspect() {
        if (busy || inspector.running || saveInProgress)
            return false;
        report = SourcePolicy.unverified();
        if (typeof sourcePath !== "string"
                || !/^\/.+\/apollo-hub-todo-v1\.json$/.test(sourcePath)
                || sourcePath.indexOf("/../") >= 0
                || sourcePath.indexOf("/./") >= 0) {
            return false;
        }
        pendingResult = null;
        replySeen = false;
        malformed = false;
        requestAtStart = saveRequestCount;
        busy = true;
        report = SourcePolicy.checking();
        inspector.exec([
            "python3", "-I", "-B",
            Quickshell.shellPath("services/hub/TaskLocalSourceInspectM15a.py"),
            "--source", sourcePath
        ]);
        return true;
    }

    function receive(line) {
        if (!busy || replySeen || malformed
                || typeof line !== "string" || line.length > 1024) {
            malformed = true;
            pendingResult = null;
            return;
        }
        replySeen = true;
        try {
            pendingResult = SourcePolicy.view(JSON.parse(line));
            if (pendingResult.state === "REFUSED")
                malformed = true;
        } catch(error) {
            malformed = true;
            pendingResult = null;
        }
    }

    function finish(code) {
        if (!busy)
            return;
        busy = false;
        if (saveRequestCount !== requestAtStart) {
            report = SourcePolicy.stale();
        } else if (code !== 0 || !replySeen || malformed
                || pendingResult === null) {
            report = SourcePolicy.unverified();
        } else {
            report = pendingResult;
        }
        pendingResult = null;
        replySeen = false;
    }

    onSaveRequestCountChanged: {
        // Invalidate a previous point-in-time check after a local write
        // request. Does NOT imply protection from noncooperating peers.
        if (!busy && report.state !== "NOT_CHECKED")
            report = SourcePolicy.stale();
    }

    Process {
        id: inspector
        stdinEnabled: false
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { sourceCheck.receive(line); }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            sourceCheck.finish(code);
        }
    }

    Timer {
        id: checkTimeout
        interval: 5000
        repeat: false
        running: sourceCheck.busy
        onTriggered: {
            if (!sourceCheck.busy)
                return;
            sourceCheck.busy = false;
            sourceCheck.pendingResult = null;
            sourceCheck.replySeen = false;
            sourceCheck.malformed = true;
            sourceCheck.report = SourcePolicy.unverified();
            if (inspector.running)
                inspector.running = false;
        }
    }

    GohuText {
        width: parent.width
        text: "LOCAL SOURCE // READ-ONLY CHECK"
        color: Colors.magenta
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: "An explicit check of the saved JSON on disk. No automatic scan, "
              + "change, backup, repair, draft capture or source ownership claim."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }

    ActionButton {
        width: Math.min(parent.width, 195)
        height: 30
        label: sourceCheck.busy ? "CHECKING SOURCE..." : "CHECK LOCAL SOURCE"
        labelPixelSize: 10
        accentColor: Colors.cyan
        available: !sourceCheck.busy && !sourceCheck.saveInProgress
                   && sourceCheck.sourcePath !== ""
        onLeftClicked: sourceCheck.inspect()
    }

    GohuText {
        width: parent.width
        text: sourceCheck.report.title
        color: sourceCheck.report.state === "SOURCE_STRUCTURALLY_READABLE"
            ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: sourceCheck.report.countLabel
        color: Colors.yellow
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: sourceCheck.report.explanation
        color: Colors.white
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: sourceCheck.report.proof
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
}
