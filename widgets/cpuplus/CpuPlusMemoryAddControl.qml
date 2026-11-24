import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.memory
import "../../components"

// Native system authorization; installed helper validates all privileged operations.
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
    property bool persistArmed: false
    property string feedback: ""
    readonly property string helperPath: "/usr/local/sbin/post-apollo-memory-add-swap"
    readonly property bool observedActive: sample !== null && sample.rows.some(
        row => row.name === "/var/lib/post-apollo-memory-swap/swapfile")
    readonly property bool nativeReady: host !== null && host.nativeAuthVersion === 1
    readonly property bool eligible: nativeReady && host.candidate === true
        && host.filesystem === "btrfs" && Number.isInteger(host.maximumGiB)
        && stagedGiB >= 4 && stagedGiB <= host.maximumGiB && stagedGiB % 4 === 0
        && sample !== null && !observedActive && !check.running
        && !MemoryOperation.busy

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
        persistArmed = false;
        host = null;
        pendingHost = null;
        gotOutput = false;
        gotExit = false;
        exitOk = false;
        check.running = true;
    }
    Component.onCompleted: checkHost()
    Connections {
        target: MemoryOperation
        function onRevisionChanged() { control.checkHost(); }
    }
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
        text: control.host && !control.nativeReady ? "HELPER UPDATE REQUIRED // EXISTING SWAP UNCHANGED"
            : control.observedActive ? "VERIFIED ACTIVE // SEE LIVE SWAP ROW ABOVE"
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
        visible: !control.observedActive
        label: control.armed ? "CONFIRM // AUTHORIZE" : "PREPARE ADD " + control.stagedGiB + " GiB"
        labelPixelSize: 10
        available: control.eligible
        onLeftClicked: {
            if (!control.eligible) return;
            if (!control.armed) { control.armed = true; return; }
            control.armed = false;
            MemoryOperation.request("add", control.stagedGiB);
        }
    }
    ActionButton {
        visible: control.armed
        width: parent.width
        height: 30
        label: "CANCEL"
        onLeftClicked: control.armed = false
    }
    ActionButton {
        width: parent.width
        height: 34
        visible: control.observedActive
        label: "TEST AUTHORIZATION // VERIFY ACTIVE"
        available: !MemoryOperation.busy && control.nativeReady
        onLeftClicked: MemoryOperation.request("verify", 0)
    }
    GohuText {
        visible: control.observedActive
        width: parent.width
        text: "BOOT POLICY // " + (!control.host || control.host.persistenceVersion !== 1
            ? "HELPER UPDATE REQUIRED"
            : control.host.persistence === "enabled" ? "ENABLED // REBOOT VERIFICATION PENDING"
            : control.host.persistence === "off" ? "TEMPORARY // NOT ENABLED"
            : "CHECK CONFIGURATION // " + String(control.host.persistence))
        color: control.host && control.host.persistence === "enabled" ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        visible: control.observedActive
        width: parent.width
        height: 34
        label: control.persistArmed ? "CONFIRM // ENABLE ON BOOT" : "KEEP AFTER REBOOT"
        available: control.observedActive && control.nativeReady && control.host.persistenceVersion === 1
            && control.host.persistence === "off" && !MemoryOperation.busy
        onLeftClicked: {
            if (!control.persistArmed) { control.persistArmed = true; return; }
            control.persistArmed = false;
            MemoryOperation.request("persist", 0);
        }
    }
    ActionButton {
        visible: control.persistArmed
        width: parent.width
        height: 30
        label: "CANCEL BOOT CHANGE"
        onLeftClicked: control.persistArmed = false
    }
    GohuText {
        width: parent.width
        text: MemoryOperation.feedback + "\nNO SWAP REMOVAL OR RESIZE"
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
