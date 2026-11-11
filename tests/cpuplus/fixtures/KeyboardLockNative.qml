import QtQuick
import Quickshell
import qs.services.input
import "widgets/cpuplus"

ShellRoot {
    id: root
    property bool started: false
    property bool done: false
    property int ticks: 0

    FloatingWindow {
        id: window
        visible: true
        title: "CPU-KEYBOARD-LOCK-SMOKE"
        implicitWidth: 1100
        implicitHeight: 680

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"

            CpuPlusSettingsKeyboardPane {
                id: controls
                x: 10
                y: 10
                width: 400
                height: parent.height - 20
                area: "controls"
            }
            CpuPlusSettingsKeyboardPane {
                id: status
                x: 420
                y: 10
                width: 280
                height: parent.height - 20
                area: "status"
            }
            CpuPlusSettingsKeyboardPane {
                id: apply
                x: 710
                y: 10
                width: parent.width - 720
                height: parent.height - 20
                area: "apply"
            }
        }
    }

    function fail(reason) {
        if (done) return;
        done = true;
        console.error("KB_NATIVE_FAIL // " + reason);
    }
    Timer {
        interval: 100
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks > 160) {
                root.fail("TIMEOUT");return;
            }
            if (!root.started) {
                if (!KeyboardLockSettings.canEdit)
                    return;
                if (!controls.visible || !status.visible || !apply.visible) {
                    root.fail("PANE_MISSING");return;
                }
                if (!KeyboardLockSettings.choose("num", "on")
                        || !KeyboardLockSettings.choose("caps", "off")) {
                    root.fail("SELECT_REFUSED");return;
                }
                root.started = true;
                return;
            }
            if (KeyboardLockSettings.storageState === "error") {
                root.fail("STORE_ERROR_" + KeyboardLockSettings.storageError);
                return;
            }
            if (KeyboardLockSettings.storageState !== "ready")
                return;
            if (KeyboardLockSettings.numMode !== "on"
                    || KeyboardLockSettings.capsMode !== "off") {
                root.fail("STATE_MISMATCH");return;
            }
            if (KeyboardLockSettings.confirmRequired
                    || KeyboardLockSettings.profileInstalled) {
                root.fail("UNAUTHORIZED_HOST_APPLY");return;
            }
            root.done = true;
            console.log("KB_NATIVE_PASS // TWO_LOCKS_SAVED_NO_HOST_INSTALL");
        }
    }
    Timer {
        interval: 350
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
}
