import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

// Fixed argv; separate terminal lifetime. Installed helper validates and confirms.
Column {
    id: control
    required property int stagedGiB
    required property var sample
    property var host: null
    property var pendingHost: null
    property bool gotOutput: false
    property bool gotExit: false
    property bool exitOk: false
    property bool armed: false
    property string feedback: ""
    readonly property string helperPath: "/usr/local/sbin/post-apollo-memory-add-swap"
    readonly property bool observedActive: sample !== null && sample.rows.some(
        row => row.name === "/var/lib/post-apollo-memory-swap/swapfile")
    readonly property bool eligible: host !== null && host.candidate === true
        && host.filesystem === "btrfs" && Number.isInteger(host.maximumGiB)
        && stagedGiB >= 4 && stagedGiB <= host.maximumGiB && stagedGiB % 4 === 0
        && sample !== null && !observedActive && !check.running

    spacing: 8
    onStagedGiBChanged: armed = false
    onObservedActiveChanged: if (observedActive) armed = false
    function finishCheck() {
        if (!gotOutput || !gotExit) return;
        host = exitOk ? pendingHost : null;
    }
    function checkHost() {
        if (check.running) return;
        armed = false;
        host = null;
        pendingHost = null;
        gotOutput = false;
        gotExit = false;
        exitOk = false;
        check.running = true;
    }
    Component.onCompleted: checkHost()
    Process {
        id: check
        command: ["/usr/bin/python3", "-I", "-B", control.helperPath, "status"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { control.pendingHost = JSON.parse(this.text); }
                catch (e) { control.pendingHost = null; }
                control.gotOutput = true;
                control.finishCheck();
            }
        }
        onExited: function(code, exitStatus) {
            control.gotExit = true;
            control.exitOk = code === 0 && exitStatus === 0;
            control.finishCheck();
        }
    }
    GohuText {
        width: parent.width
        text: "TARGET // BTRFS /var/lib"
        color: Colors.cyan
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: control.observedActive ? "VERIFIED ACTIVE // SEE LIVE SWAP ROW ABOVE"
            : control.host ? (control.host.existing ? "EXISTING ALLOCATION // NO OVERWRITE"
                  : "FREE // " + control.host.availableGiB + " GiB   RESERVE // "
                    + control.host.reserveGiB + " GiB   MAX // " + control.host.maximumGiB + " GiB")
            : check.running ? "CHECKING HOST..." : "HELPER UNAVAILABLE // INSTALL OR CHECK HOST"
        color: control.observedActive ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: parent.width
        height: 30
        label: "CHECK HOST"
        available: !check.running
        onLeftClicked: control.checkHost()
    }
    ActionButton {
        width: parent.width
        height: 34
        label: control.armed ? "CONFIRM // OPEN AUTH TERMINAL" : "PREPARE ADD " + control.stagedGiB + " GiB"
        labelPixelSize: 10
        available: control.eligible
        onLeftClicked: {
            if (!control.eligible) return;
            if (!control.armed) { control.armed = true; return; }
            control.armed = false;
            control.feedback = "TERMINAL REQUESTED // AUTHENTICATE, THEN TYPE ADD "
                + control.stagedGiB + ". CHECK HOST AND LIVE SWAP AFTERWARD."
            Quickshell.execDetached(["/usr/bin/kitty", "--hold", "/usr/bin/sudo", "--",
                control.helperPath, "add", String(control.stagedGiB)]);
            control.host = null;
        }
    }
    ActionButton {
        visible: control.armed
        width: parent.width
        height: 30
        label: "CANCEL"
        onLeftClicked: control.armed = false
    }
    GohuText {
        width: parent.width
        text: control.feedback || "ONE-TIME ADD ONLY // NO PERSISTENCE OR RESIZE"
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
