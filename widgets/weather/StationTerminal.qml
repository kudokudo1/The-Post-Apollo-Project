import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

Rectangle {
    id: terminalView

    color: "transparent"

    property var targetScreen: null
    property bool stationOpen: false

    // Keep these so WeatherStationW does not need
    // to change yet.
    property int stationWidth: 1000
    property int stationHeight: 700
    property int stationRightMargin: 20
    property int stationBottomMargin: 90
    property int stationHeaderHeight: 62
    property int stationRailWidth: 160

    property string terminalState: "IDLE"
    property string terminalAppId: "weather-screen"

    // Last geometry sent to Sway.
    property int lastX: -99999
    property int lastY: -99999
    property int lastWidth: -1
    property int lastHeight: -1

    property bool revealAfterSync: false

    // ─────────────────────────────────────────────
    // LAUNCH
    // ─────────────────────────────────────────────

    Process {
        id: launchProcess

        command: ["bash", "-lc", "kitty " + "--config /var/home/mapple/.config/kitty/weatherstation.conf " + "--override confirm_os_window_close=0 " + "--app-id weather-screen " + "--title 'STAR MAP' " + "/var/home/mapple/.local/bin/weatherstation-starmap " + ">/dev/null 2>&1 &"]

        onExited: function (exitCode, exitStatus) {
            if (exitCode === 0)
                waitForKitty.running = true;
            else
                terminalView.terminalState = "LAUNCH ERROR";
        }
    }

    // ─────────────────────────────────────────────
    // WAIT UNTIL SWAY ACTUALLY SEES KITTY
    // ─────────────────────────────────────────────

    Process {
        id: waitForKitty

        command: ["bash", "-lc", "for i in $(seq 1 100); do " + "if swaymsg -t get_tree | " + "grep -Fq '\"app_id\": \"weather-screen\"'; then " + "exit 0; " + "fi; " + "sleep 0.05; " + "done; " + "exit 1"]

        onExited: function (exitCode, exitStatus) {
            if (exitCode === 0) {
                terminalView.revealAfterSync = true;
                terminalView.syncGeometry(true);
            } else {
                terminalView.terminalState = "START ERROR";
            }
        }
    }

    // ─────────────────────────────────────────────
    // GEOMETRY SYNC
    //
    // Kitty follows the ACTUAL QML bay position.
    // ─────────────────────────────────────────────

    Process {
        id: geometryProcess

        property int targetX: 0
        property int targetY: 0
        property int targetWidth: 0
        property int targetHeight: 0

        command: ["swaymsg", "[app_id=\"^weather-screen$\"] " + "floating enable, " + "border none, " + "resize set " + targetWidth + " " + targetHeight + ", " + "move absolute position " + targetX + " " + targetY + (terminalView.revealAfterSync ? ", scratchpad show" : "")]

        onExited: function (exitCode, exitStatus) {
            if (exitCode === 0) {
                terminalView.lastX = geometryProcess.targetX;

                terminalView.lastY = geometryProcess.targetY;

                terminalView.lastWidth = geometryProcess.targetWidth;

                terminalView.lastHeight = geometryProcess.targetHeight;

                if (terminalView.revealAfterSync) {
                    terminalView.revealAfterSync = false;
                    terminalView.terminalState = "VISIBLE";
                }
            } else {
                terminalView.terminalState = "SYNC ERROR";
            }
        }
    }

    function syncGeometry(force) {
        if (terminalState !== "VISIBLE" && !revealAfterSync) {
            return;
        }

        // THIS is the important part:
        // ask Qt where the bay actually is globally.
        const point = terminalBay.mapToGlobal(0, 0);

        const gx = Math.round(point.x);

        const gy = Math.round(point.y);

        const gw = Math.round(terminalBay.width);

        const gh = Math.round(terminalBay.height);

        if (!force && gx === lastX && gy === lastY && gw === lastWidth && gh === lastHeight) {
            return;
        }

        if (geometryProcess.running)
            return;
        geometryProcess.targetX = gx;
        geometryProcess.targetY = gy;
        geometryProcess.targetWidth = gw;
        geometryProcess.targetHeight = gh;

        geometryProcess.running = true;
    }

    // Check geometry while the instrument is open.
    // It only sends swaymsg when something actually
    // changed.
    Timer {
        interval: 75

        repeat: true

        running: terminalView.terminalState === "VISIBLE"

        onTriggered: {
            terminalView.syncGeometry(false);
        }
    }

    // ─────────────────────────────────────────────
    // CLOSE
    // ─────────────────────────────────────────────

    Process {
        id: closeProcess

        command: ["swaymsg", "[app_id=\"^weather-screen$\"] kill"]

        onExited: function (exitCode, exitStatus) {
            terminalView.terminalState = "IDLE";

            terminalView.lastX = -99999;
            terminalView.lastY = -99999;
            terminalView.lastWidth = -1;
            terminalView.lastHeight = -1;
        }
    }

    // ─────────────────────────────────────────────
    // FUNCTIONS
    // ─────────────────────────────────────────────

    function openTerminal() {
        if (terminalState === "VISIBLE" || terminalState === "STARTING") {
            return;
        }

        terminalState = "STARTING";

        if (!launchProcess.running)
            launchProcess.running = true;
    }

    function closeTerminal() {
        if (terminalState === "IDLE")
            return;
        if (!closeProcess.running)
            closeProcess.running = true;
    }

    onStationOpenChanged: {
        if (!stationOpen)
            closeTerminal();
    }

    onVisibleChanged: {
        if (!visible)
            closeTerminal();
    }

    // ─────────────────────────────────────────────
    // BACKGROUND
    // ─────────────────────────────────────────────

    Rectangle {
        anchors.fill: parent

        color: Colors.black
    }

    // ─────────────────────────────────────────────
    // TITLE
    // ─────────────────────────────────────────────

    Text {
        anchors.top: parent.top
        anchors.left: parent.left

        anchors.topMargin: 22
        anchors.leftMargin: 30

        text: "✦ STAR MAP"

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 22

        color: Colors.orange

        z: 5
    }

    Text {
        anchors.top: parent.top
        anchors.right: parent.right

        anchors.topMargin: 26
        anchors.rightMargin: 30

        text: terminalView.terminalState

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 14

        color: terminalView.terminalState === "VISIBLE" ? Colors.cyan : Colors.orange

        z: 5
    }

    // ─────────────────────────────────────────────
    // ACTUAL INSTRUMENT BAY
    //
    // Kitty is locked to THIS rectangle.
    // ─────────────────────────────────────────────

    Rectangle {
        id: terminalBay

        x: 30
        y: 70

        width: parent.width - 60

        height: parent.height - 160

        color: terminalView.terminalState === "VISIBLE" ? "transparent" : Colors.black

        border.width: 2
        border.color: Colors.cyan

        z: 4

        Text {
            anchors.centerIn: parent

            visible: terminalView.terminalState !== "VISIBLE"

            text: terminalView.terminalState === "STARTING" ? "STAR MAP // INITIALIZING" : terminalView.terminalState === "START ERROR" ? "STAR MAP // ERROR" : "STAR MAP // STANDBY"

            font.family: "GohuFont 11 Nerd Font Mono"

            font.pixelSize: 22

            color: Colors.cyan
        }

        onWidthChanged: {
            terminalView.syncGeometry(false);
        }

        onHeightChanged: {
            terminalView.syncGeometry(false);
        }

        onXChanged: {
            terminalView.syncGeometry(false);
        }

        onYChanged: {
            terminalView.syncGeometry(false);
        }
    }

    // ─────────────────────────────────────────────
    // CONTROLS
    // ─────────────────────────────────────────────

    Row {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter

        anchors.bottomMargin: 28

        spacing: 18

        z: 5

        Rectangle {
            width: 180
            height: 38

            color: openMouse.pressed ? Colors.magenta : openMouse.containsMouse ? Colors.yellow : Colors.black

            border.width: 1
            border.color: Colors.cyan

            Text {
                anchors.centerIn: parent

                text: "[ STAR MAP ]"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: openMouse.pressed ? Colors.black : openMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            MouseArea {
                id: openMouse

                anchors.fill: parent
                hoverEnabled: true

                onClicked: {
                    terminalView.openTerminal();
                }
            }
        }

        Rectangle {
            width: 130
            height: 38

            color: closeMouse.pressed ? Colors.magenta : closeMouse.containsMouse ? Colors.yellow : Colors.black

            border.width: 1
            border.color: Colors.cyan

            Text {
                anchors.centerIn: parent

                text: "[ CLOSE ]"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: closeMouse.pressed ? Colors.black : closeMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            MouseArea {
                id: closeMouse

                anchors.fill: parent
                hoverEnabled: true

                onClicked: {
                    terminalView.closeTerminal();
                }
            }
        }
    }
}
