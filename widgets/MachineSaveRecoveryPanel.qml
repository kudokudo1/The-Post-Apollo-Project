import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../services/time/MachineV3LocalSaveRecoveryPolicy.js" as RecoveryPolicy

// Explicit ordinary local recovery, independent of current Save/Restore.
Column {
    id: panel
    property bool contextActive: false
    property bool blocked: false
    property bool expanded: false
    property bool busy: false
    property double requestSequence: 0
    property string requestToken: ""
    property string requestMode: ""
    property string requestIdentity: ""
    property var intentIds: []
    property int selectedIndex: 0
    property var displayResult: null
    property string statusText: "NOT INSPECTED // READ ONLY"
    property bool streamDone: false
    property bool exitDone: false
    property bool exitOk: false
    property bool timedOut: false
    property string responseText: ""
    readonly property string selectedIdentity: selectedIndex >= 0
        && selectedIndex < intentIds.length ? intentIds[selectedIndex] : ""
    spacing: 6

    onContextActiveChanged: {
        if (!contextActive) {
            expanded = false;
            invalidate(true);
        }
    }
    onExpandedChanged: {
        if (!expanded)
            invalidate(true);
    }
    onBlockedChanged: {
        if (blocked)
            invalidate(true);
    }
    onSelectedIdentityChanged: {
        // A list response may itself establish a selection. No inspect starts
        // from that change, and no old inspect remains displayed.
        if (requestMode === "inspect" || !busy) {
            requestToken = "";
            displayResult = null;
            statusText = "NOT INSPECTED // READ ONLY";
        }
    }

    function invalidate(clearList) {
        requestToken = "";
        displayResult = null;
        statusText = busy && timedOut ? "RECOVERY READ TIMED OUT // HOLD"
            : "NOT INSPECTED // READ ONLY";
        if (clearList) {
            intentIds = [];
            selectedIndex = 0;
        }
        // Busy belongs to actual process/stream completion, not visibility.
    }

    function toggle() {
        if (!contextActive || blocked)
            return;
        expanded = !expanded;
    }

    function step(delta) {
        if (!contextActive || !expanded || blocked || busy
                || (delta !== -1 && delta !== 1) || intentIds.length < 2)
            return;
        invalidate(false);
        selectedIndex = (selectedIndex + delta + intentIds.length) % intentIds.length;
    }

    function nextToken() {
        // Unique within this component lifetime. Correlation only, not a
        // cryptographic nonce. A new component has no surviving child replies.
        if (requestSequence >= 281474976710655)
            return "";
        requestSequence += 1;
        const suffix = ("000000000000" + requestSequence.toString(16)).slice(-12);
        return "00000000-0000-4000-8000-" + suffix;
    }

    function begin(mode) {
        if (!contextActive || !expanded || blocked || busy
                || (mode !== "list" && mode !== "inspect")
                || (mode === "inspect" && !selectedIdentity))
            return;
        invalidate(mode === "list");
        const token = nextToken();
        if (!token) {
            statusText = "RECOVERY UNAVAILABLE // HOLD";
            return;
        }
        requestToken = token;
        requestMode = mode;
        requestIdentity = mode === "inspect" ? selectedIdentity : "";
        streamDone = false;
        exitDone = false;
        exitOk = false;
        timedOut = false;
        responseText = "";
        busy = true;
        statusText = "READING LOCAL RECORDS // NO ACTION";
        const args = ["python3", "-B", "-I",
            Quickshell.shellPath("services/time/MachineV3LocalSaveRecoveryUiRead.py"),
            mode, token];
        if (mode === "inspect")
            args.push(requestIdentity);
        recoveryDeadline.restart();
        recoveryProcess.exec(args);
    }

    function deadlineReached() {
        if (!busy)
            return;
        timedOut = true;
        invalidate(false);
        statusText = "RECOVERY READ TIMED OUT // HOLD";
        // Do not reuse the Process until both original completion signals.
    }

    function streamFinished(text) {
        if (!busy)
            return;
        responseText = typeof text === "string" && text.length <= 8193 ? text : "";
        streamDone = true;
        finishIfReady();
    }

    function processExited(exitCode, exitStatus) {
        if (!busy)
            return;
        exitOk = exitCode === 0 && exitStatus === 0;
        exitDone = true;
        finishIfReady();
    }

    function finishIfReady() {
        if (!busy || !streamDone || !exitDone)
            return;
        recoveryDeadline.stop();
        const token = requestToken;
        const mode = requestMode;
        const identity = requestIdentity;
        const raw = responseText;
        const ok = exitOk;
        const current = contextActive && expanded && !blocked && token !== ""
            && (mode === "list" || (mode === "inspect" && identity === selectedIdentity));
        requestToken = "";
        responseText = "";
        if (current) {
            let result = RecoveryPolicy.unavailable();
            if (ok && raw.length > 0) {
                try {
                    result = RecoveryPolicy.accept(JSON.parse(raw), token, mode,
                        mode === "list" ? null : identity);
                } catch (error) {
                    result = RecoveryPolicy.unavailable();
                }
            }
            if (mode === "list") {
                intentIds = result.valid ? result.intentIds : [];
                selectedIndex = 0;
            }
            displayResult = result;
            statusText = result.status;
        }
        requestMode = "";
        requestIdentity = "";
        streamDone = false;
        exitDone = false;
        exitOk = false;
        timedOut = false;
        busy = false;
    }

    Timer {
        id: recoveryDeadline
        interval: 45000
        repeat: false
        running: false
        onTriggered: panel.deadlineReached()
    }

    Process {
        id: recoveryProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: panel.streamFinished(this.text)
        }
        onExited: function(exitCode, exitStatus) {
            panel.processExited(exitCode, exitStatus);
        }
    }

    ActionButton {
        width: panel.width
        height: 32
        label: panel.expanded ? "SAVE RECOVERY // CLOSE" : "SAVE RECOVERY // READ ONLY"
        labelPixelSize: 10
        accentColor: panel.expanded ? Colors.magenta : Colors.white
        available: panel.contextActive && !panel.blocked
        onLeftClicked: panel.toggle()
    }

    Column {
        visible: panel.expanded
        width: panel.width
        spacing: 6

        ActionButton {
            width: parent.width
            height: 32
            label: panel.busy ? (panel.timedOut ? "READ TIMED OUT // HOLD" : "READING...")
                : "REFRESH LOCAL ATTEMPTS"
            labelPixelSize: 10
            accentColor: Colors.cyan
            available: panel.contextActive && !panel.blocked && !panel.busy
            onLeftClicked: panel.begin("list")
        }

        Row {
            width: parent.width
            height: 32
            spacing: 5
            ActionButton {
                width: 40
                height: parent.height
                label: "<"
                accentColor: Colors.white
                available: !panel.blocked && !panel.busy && panel.intentIds.length > 1
                onLeftClicked: panel.step(-1)
            }
            GohuText {
                width: Math.max(0, parent.width - 90)
                anchors.verticalCenter: parent.verticalCenter
                text: panel.intentIds.length ? "ATTEMPT " + (panel.selectedIndex + 1)
                    + " / " + panel.intentIds.length : "NO ATTEMPT SELECTED"
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            ActionButton {
                width: 40
                height: parent.height
                label: ">"
                accentColor: Colors.white
                available: !panel.blocked && !panel.busy && panel.intentIds.length > 1
                onLeftClicked: panel.step(1)
            }
        }

        GohuText {
            visible: panel.selectedIdentity !== ""
            width: parent.width
            text: panel.selectedIdentity
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WrapAnywhere
        }

        ActionButton {
            width: parent.width
            height: 32
            label: "INSPECT ORIGINAL ATTEMPT"
            labelPixelSize: 10
            accentColor: Colors.cyan
            available: panel.contextActive && !panel.blocked && !panel.busy
                       && panel.selectedIdentity !== ""
            onLeftClicked: panel.begin("inspect")
        }

        GohuText {
            width: parent.width
            text: panel.statusText
            color: Colors.orange
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }
        GohuText {
            visible: !!panel.displayResult
            width: parent.width
            text: "ORDINARY // " + (panel.displayResult ? panel.displayResult.ordinary : "UNKNOWN")
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            visible: !!panel.displayResult
            width: parent.width
            text: "FRACTIONAL // " + (panel.displayResult ? panel.displayResult.fractional : "UNKNOWN")
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            visible: !!panel.displayResult
            width: parent.width
            text: panel.displayResult ? panel.displayResult.detail : ""
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "LOCAL DATA ONLY // NO RETRY OR RESTORE AUTHORITY"
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
    }
}
