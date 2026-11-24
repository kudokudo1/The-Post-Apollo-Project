pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.time

// A transient operation request, not a saved privilege or a password store.
// Shared native Polkit agent is owned by the existing shell loader.
Scope {
    id: owner
    property bool busy: false
    property bool waiting: false
    property string kind: ""
    property int requestedGiB: 0
    property string feedback: "NO NATIVE REQUEST"
    property bool gotOutput: false
    property bool gotExit: false
    property bool exitOk: false
    property string output: ""
    property int revision: 0
    readonly property string helperPath: "/usr/local/sbin/post-apollo-memory-add-swap"

    function request(action, size) {
        if (busy || TimeSettings.authSessionActive || TimeSettings.resyncAuthPending
                || TimeSettings.timezoneAuthPending) {
            feedback = "AN AUTHORIZATION REQUEST IS ALREADY ACTIVE";
            return;
        }
        if (action !== "verify" && (action !== "add" || !Number.isInteger(size)
                || size < 4 || size > 64 || size % 4 !== 0))
            return;
        kind = action;
        requestedGiB = action === "add" ? size : 0;
        gotOutput = false;
        gotExit = false;
        exitOk = false;
        output = "";
        waiting = true;
        busy = true;
        feedback = "WAITING FOR SYSTEM AUTHORIZATION AGENT";
        agentTimeout.restart();
    }
    function agentReady() {
        if (!busy || !waiting || operation.running) return;
        if (TimeSettings.authSessionActive || TimeSettings.resyncAuthPending
                || TimeSettings.timezoneAuthPending) {
            cancelWaiting("CLOCK AUTHORIZATION ACTIVE // TRY AGAIN");
            return;
        }
        agentTimeout.stop();
        waiting = false;
        feedback = "AUTHENTICATE // WAIT FOR SYSTEM RESULT";
        const args = ["/usr/bin/pkexec", "--disable-internal-agent", helperPath];
        if (kind === "add") args.push("add-authorized", String(requestedGiB));
        else args.push("verify-authorized");
        operation.exec(args);
    }
    function cancelWaiting(message) {
        if (!waiting) return;
        agentTimeout.stop();
        waiting = false;
        busy = false;
        feedback = message;
    }
    function finish() {
        if (!gotOutput || !gotExit) return;
        let verified = false;
        try {
            const line = output.trim().split("\n").pop();
            const result = JSON.parse(line.replace(/^VERIFIED ACTIVE: /, ""));
            verified = line.indexOf("VERIFIED ACTIVE: ") === 0
                && Number.isSafeInteger(result.sizeKiB) && result.sizeKiB > 0
                && result.priority === 10
                && (kind !== "add" || (result.sizeKiB <= requestedGiB * 1048576
                    && result.sizeKiB >= requestedGiB * 1048576 - 1024));
        } catch (e) {}
        feedback = exitOk && verified
            ? "VERIFIED ACTIVE // REFRESHING KERNEL SWAP"
            : "NOT VERIFIED // CHECK HOST AND KERNEL SWAP; NO AUTO RETRY";
        busy = false;
        revision++;
    }
    Timer {
        id: agentTimeout
        interval: 6000
        repeat: false
        onTriggered: owner.cancelWaiting("NATIVE AUTHORIZATION AGENT UNAVAILABLE")
    }
    Process {
        id: operation
        stdout: StdioCollector {
            onStreamFinished: {
                owner.output = this.text.slice(-4096);
                owner.gotOutput = true;
                owner.finish();
            }
        }
        onExited: function(code, exitStatus) {
            owner.exitOk = code === 0 && exitStatus === 0;
            owner.gotExit = true;
            owner.finish();
        }
    }
}
