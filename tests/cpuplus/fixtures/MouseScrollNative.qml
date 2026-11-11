import QtQuick
import Quickshell
import qs.services.input
import "widgets/cpuplus"

ShellRoot {
    id: root
    property bool done: false
    property int tick: 0
    property int phase: 0
    FloatingWindow {
        id: window
        visible: true
        title: "CPU-MOUSE-SCROLL-NATIVE"
        implicitWidth: 1120
        implicitHeight: 710
        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            CpuPlusSettingsMouseScrollPane {
                id: devicesPane
                x: 8
                y: 10
                width: 365
                height: parent.height - 20
                area: "devices"
            }
            CpuPlusSettingsMouseScrollPane {
                id: factorPane
                x: 380
                y: 10
                width: 350
                height: parent.height - 20
                area: "factor"
            }
            CpuPlusSettingsMouseScrollPane {
                id: applyPane
                x: 737
                y: 10
                width: parent.width - 745
                height: parent.height - 20
                area: "apply"
            }
        }
    }
    function fail(reason) {
        if (done) return;
        done = true;
        console.error("MOUSE_NATIVE_FAIL // " + reason);
    }
    Timer {
        interval: 100
        repeat: true
        running: !root.done
        onTriggered: {
            root.tick++;
            if (root.tick > 160) {
                root.fail("TIMEOUT");return;
            }
            if (SwayScrollSettings.storeState === "error") {
                root.fail("STORE_ERROR");return;
            }
            if (!SwayScrollSettings.canStore || SwayScrollSettings.busy)
                return;
            if (!devicesPane.visible || !factorPane.visible || !applyPane.visible) {
                root.fail("PANE_MISSING");return;
            }
            if (SwayScrollSettings.applying || SwayScrollSettings.confirmationRequired) {
                root.fail("UNAUTHORIZED_APPLY");return;
            }
            if (root.phase === 2) {
                if (ZellijScrollSettings.busy)
                    return;
                if (!ZellijScrollSettings.active
                        || !ZellijScrollSettings.stage("mouse", "false")
                        || !ZellijScrollSettings.stage("resize", "false")
                        || !ZellijScrollSettings.stage("sync", "false")
                        || !ZellijScrollSettings.stage("buffer", 20000)
                        || ZellijScrollSettings.confirmRequired) {
                    root.fail("ZELLIJ_STAGE_OR_PERMISSION"); return;
                }
                root.done = true;
                console.log("ZELLIJ_NATIVE_PASS // STAGED_NO_CONFIG_WRITE");
                return;
            }
            if (root.phase === 1) {
                if (KittyScrollSettings.busy)
                    return;
                if (!KittyScrollSettings.terminalMode
                        || !KittyScrollSettings.stage("wheel", 8.0)
                        || !KittyScrollSettings.stage("touch", 2.0)
                        || KittyScrollSettings.confirmAction !== "") {
                    root.fail("KITTY_STAGING_OR_APPROVAL"); return;
                }
                console.log("KITTY_NATIVE_PASS // TWO_FACTORS_STAGED_NO_CONFIG_WRITE");
                root.phase = 2;
                if (!ZellijScrollSettings.open()) {
                    root.fail("ZELLIJ_ROUTE_REFUSED"); return;
                }
                return;
            }
            // Test only: inject synthetic Sway discovery into the in-memory
            // QML view. No Sway IPC or config file is touched.
            SwayScrollSettings.devices = [
                {identifier:"111:222:Test_Mouse",name:"Test Mouse",
                 kind:"pointer",factor:1.0}
            ];
            if (!SwayScrollSettings.selectDevice("111:222:Test_Mouse")
                    || !SwayScrollSettings.stageFactor(2.0)
                    || !SwayScrollSettings.prepareApply()) {
                root.fail("STAGE_REFUSED");return;
            }
            if (!SwayScrollSettings.confirmationRequired) {
                root.fail("MISSING_EXPLICIT_CONFIRMATION");return;
            }
            SwayScrollSettings.cancelApply();
            if (SwayScrollSettings.applying || SwayScrollSettings.confirmationRequired) {
                root.fail("CANCEL_REFUSED");return;
            }
            console.log("MOUSE_NATIVE_PASS // THREE_BAYS_STAGED_NO_HOST_MUTATION");
            root.phase = 1;
            if (!KittyScrollSettings.chooseMode(true)) {
                root.fail("KITTY_MODE_UNAVAILABLE"); return;
            }
        }
    }
    Timer {
        interval: 300
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
}
