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
    property var activeRead: null
    property var activeWatchdog: null
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
        // Each read has its own Process, collector and watchdog. A retired
        // callback cannot become a response to a later explicit read.
        let process = null;
        let watchdog = null;
        try {
            process = recoveryProcessFactory.createObject(panel, { generation: requestSequence });
            if (!process)
                throw new Error("reader allocation");
            activeRead = process;
            watchdog = recoveryWatchdogFactory.createObject(panel,
                { ownerProcess: process, generation: requestSequence });
            if (!watchdog)
                throw new Error("watchdog allocation");
            activeWatchdog = watchdog;
            watchdog.start();
            process.exec(args);
        } catch (error) {
            // Creation/exec failure is never a completed read. Retire only
            // when the owned Process has no running child.
            if (process && activeRead === process) {
                deadlineReached(process, process.generation);
            } else {
                requestToken = "";
                displayResult = RecoveryPolicy.unavailable();
                statusText = displayResult.status;
                busy = false;
            }
        }
    }

    function isCurrent(process, generation) {
        return busy && !!process && activeRead === process
            && generation === requestSequence;
    }

    function deadlineReached(process, generation) {
        if (!isCurrent(process, generation))
            return;
        timedOut = true;
        invalidate(false);
        statusText = "RECOVERY READ TIMED OUT // HOLD";
        // Cancel only our own read-only child. No PID from a response, no
        // external kill command, no Save/Restore process is ever targeted.
        if (process.running) {
            process.signal(9);
        }
        // A failed start may emit neither streamFinished nor exited.
        // Never release on a timer alone while the owned child is running.
        finishIfReady(process, generation);
    }

    function streamFinished(process, generation, text) {
        if (!isCurrent(process, generation))
            return;
        responseText = typeof text === "string" && text.length <= 8193 ? text : "";
        streamDone = true;
        finishIfReady(process, generation);
    }

    function processExited(process, generation, exitCode, exitStatus) {
        if (!isCurrent(process, generation))
            return;
        exitOk = exitCode === 0 && exitStatus === 0;
        exitDone = true;
        finishIfReady(process, generation);
    }

    function processStateChanged(process, generation) {
        if (!isCurrent(process, generation))
            return;
        finishIfReady(process, generation);
    }

    function finishIfReady(process, generation) {
        if (!isCurrent(process, generation))
            return;
        if (timedOut) {
            if (process.running || (process.processId !== null && process.processId !== undefined))
                return; // unconfirmed termination stays HOLD; no overlap.
        } else if (!streamDone || !exitDone) {
            return;
        }
        const token = requestToken;
        const mode = requestMode;
        const identity = requestIdentity;
        const raw = responseText;
        const ok = exitOk;
        const current = !timedOut && contextActive && expanded && !blocked && token !== ""
            && (mode === "list" || (mode === "inspect" && identity === selectedIdentity));

        // Revoke old ownership before retiring Qt objects; their queued
        // signals carry the original object and generation.
        const watchdog = activeWatchdog;
        activeRead = null;
        activeWatchdog = null;
        requestToken = "";
        responseText = "";
        if (watchdog)
            watchdog.stop();
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
        busy = false;
        Qt.callLater(function() {
            if (watchdog)
                watchdog.destroy();
            process.destroy();
        });
    }

    Component {
        id: recoveryWatchdogFactory
        Timer {
            id: deadline
            property var ownerProcess: null
            property double generation: 0
            interval: 45000
            repeat: false
            running: false
            onTriggered: {
                if (panel.activeWatchdog === deadline)
                    panel.deadlineReached(ownerProcess, generation);
            }
        }
    }

    Component {
        id: recoveryProcessFactory
        Process {
            id: reader
            property double generation: 0
            running: false
            stdout: StdioCollector {
                onStreamFinished: panel.streamFinished(reader, reader.generation, this.text)
            }
            onExited: function(exitCode, exitStatus) {
                panel.processExited(reader, reader.generation, exitCode, exitStatus);
            }
            onRunningChanged: panel.processStateChanged(reader, reader.generation)
            onProcessIdChanged: panel.processStateChanged(reader, reader.generation)
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
