import QtQuick
import QtQuick.Window
import Quickshell
import "widgets"

// Unmounted CI-only native root. No production TimeW or Sway commands.
ShellRoot {
    id: smoke
    readonly property bool armed:
        Quickshell.env("POST_APOLLO_TIMEW_M11C") === "CI_DISPOSABLE_ONLY"
    readonly property bool missingExecutable: Quickshell.env("TIMEW_M11D_MISSING_EXEC") === "1"
    property bool activeContext: true
    property bool blockedContext: false
    property int stage: 0
    property int ticks: 0
    property string oldToken: ""

    Window {
        id: view
        visible: smoke.armed
        width: 432
        height: 720
        color: "#1B0623"
        MachineSaveRecoveryPanel {
            id: recovery
            width: view.width - 24
            x: 12
            y: 12
            contextActive: smoke.activeContext
            blocked: smoke.blockedContext
        }
    }

    function require(ok, name) {
        if (!ok) {
            console.error("M11C_NATIVE_FAIL " + name + " stage=" + stage
                          + " status=" + recovery.statusText);
            Qt.quit();
            return false;
        }
        return true;
    }

    function advance() {
        stage += 1;
        ticks = 0;
    }

    Timer {
        interval: 100
        repeat: true
        running: smoke.armed
        onTriggered: {
            smoke.ticks += 1;
            if (smoke.missingExecutable) {
                if (smoke.stage === 0) {
                    recovery.toggle();
                    recovery.begin("list");
                    smoke.advance();
                    return;
                }
                if (recovery.busy)
                    return;
                if (!smoke.require(recovery.timedOut && recovery.activeRead === null
                        && recovery.displayResult === null && recovery.requestSequence === 1
                        && recovery.statusText === "RECOVERY READ TIMED OUT // HOLD",
                        "failed exec retired without false success"))
                    return;
                console.log("M11D_NATIVE_MISSING_EXEC_PASS");
                Qt.quit();
                return;
            }
            switch (smoke.stage) {
            case 0:
                if (!smoke.require(!recovery.busy && !recovery.expanded
                        && recovery.requestSequence === 0, "no auto launch"))
                    return;
                recovery.toggle();
                if (!smoke.require(recovery.expanded && !recovery.busy,
                                   "open is not read"))
                    return;
                recovery.begin("list");
                smoke.advance();
                return;
            case 1:
                if (recovery.busy) return;
                if (!smoke.require(recovery.intentIds.length === 2
                        && recovery.statusText === "LOCAL ATTEMPTS // READ ONLY"
                        && recovery.selectedIdentity === "11111111-1111-4111-8111-111111111111",
                        "real list / prepared id"))
                    return;
                console.log("M11C_NATIVE_LIST_PASS");
                recovery.begin("inspect");
                smoke.advance();
                return;
            case 2:
                if (recovery.busy) return;
                if (!smoke.require(recovery.displayResult
                        && recovery.displayResult.ordinary === "PREPARED // NO PAIR OBSERVED"
                        && recovery.statusText === "ORDINARY SAVE // HOLD", "prepared no checkpoint"))
                    return;
                smoke.oldToken = recovery.requestToken;
                recovery.step(1);
                if (!smoke.require(recovery.displayResult === null
                        && recovery.selectedIdentity === "22222222-2222-4222-8222-222222222222"
                        && recovery.requestSequence === 2, "selection clears without launch"))
                    return;
                view.width = 560;
                recovery.begin("inspect");
                smoke.advance();
                return;
            case 3:
                if (recovery.busy) return;
                if (!smoke.require(recovery.displayResult
                        && recovery.statusText === "LOCAL RECORDS OBSERVED // HOLD"
                        && recovery.displayResult.fractional === "LOCAL ROWS OBSERVED"
                        && recovery.width === 536 && recovery.height > 0,
                        "real complete result / resized component"))
                    return;
                console.log("M11C_NATIVE_INSPECT_RESIZE_PASS");
                recovery.begin("list"); // delayed fixture wrapper #4
                smoke.advance();
                return;
            case 4:
                if (!smoke.require(recovery.busy, "delayed child running"))
                    return;
                smoke.activeContext = false;
                if (!smoke.require(!recovery.expanded && recovery.requestToken === ""
                        && recovery.busy, "context departure invalidation"))
                    return;
                smoke.activeContext = true;
                recovery.toggle();
                recovery.begin("list"); // must be refused until old process ends
                if (!smoke.require(recovery.requestSequence === 4, "no overlapping read"))
                    return;
                smoke.advance();
                return;
            case 5:
                if (recovery.busy) return;
                if (!smoke.require(recovery.intentIds.length === 0 && recovery.displayResult === null,
                                   "old response discarded"))
                    return;
                console.log("M11C_NATIVE_CONTEXT_PASS");
                recovery.begin("list");
                smoke.advance();
                return;
            case 6:
                if (recovery.busy) return;
                if (!smoke.require(recovery.intentIds.length === 2, "fresh list"))
                    return;
                recovery.begin("inspect"); // actual 45s deadline, permanently hung fixture child
                smoke.advance();
                return;
            case 7:
                if (!recovery.timedOut) {
                    if (!smoke.require(recovery.busy, "timeout must precede completion"))
                        return;
                    return;
                }
                if (!smoke.require(recovery.requestToken === ""
                        && recovery.displayResult === null
                        && recovery.statusText === "RECOVERY READ TIMED OUT // HOLD",
                        "real timer fail closed"))
                    return;
                if (recovery.busy) {
                    recovery.begin("inspect");
                    if (!smoke.require(recovery.requestSequence === 6, "timeout no overlapping read"))
                        return;
                }
                console.log("M11C_NATIVE_DEADLINE_PASS");
                smoke.advance();
                return;
            case 8:
                if (recovery.busy) return;
                if (!smoke.require(recovery.displayResult === null && recovery.activeRead === null,
                                   "timeout retired child and discarded data"))
                    return;
                recovery.begin("list"); // wrapper #7 exits nonzero
                smoke.advance();
                return;
            case 9:
                if (recovery.busy) return;
                if (!smoke.require(recovery.statusText === "RECOVERY UNAVAILABLE // HOLD"
                        && recovery.displayResult && !recovery.displayResult.valid,
                        "real failed exit"))
                    return;
                console.log("M11C_NATIVE_NONZERO_PASS");
                recovery.begin("list");
                smoke.advance();
                return;
            case 10:
                if (recovery.busy) return;
                if (!smoke.require(recovery.intentIds.length === 2
                        && recovery.requestSequence === 8,
                        "fresh explicit read after completion"))
                    return;
                smoke.blockedContext = true;
                if (!smoke.require(recovery.intentIds.length === 0
                        && recovery.displayResult === null, "competing operation invalidates"))
                    return;
                console.log("M11C_NATIVE_PASS");
                Qt.quit();
                return;
            }
        }
    }
    Timer {
        interval: 75000
        running: smoke.armed
        repeat: false
        onTriggered: {
            console.error("M11C_NATIVE_FAIL watchdog stage=" + smoke.stage
                          + " status=" + recovery.statusText
                          + " busy=" + recovery.busy + " stream=" + recovery.streamDone
                          + " exit=" + recovery.exitDone);
            Qt.quit();
        }
    }
    Component.onCompleted: {
        Quickshell.watchFiles = false;
        if (!smoke.armed)
            Qt.quit();
    }
}
