import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "../../services/windowassembly"

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

    // Global panel origin is owned by WeatherStationW, the actual PanelWindow.
    property int stationGlobalX: 0
    property int stationGlobalY: 0
    property bool stationGeometryReady: false

    // Public bay geometry expected by WeatherStationW's input mask.
    readonly property int bayX: terminalBay.x
    readonly property int bayY: terminalBay.y
    readonly property int bayWidth: terminalBay.width
    readonly property int bayHeight: terminalBay.height

    property string terminalState: "IDLE"
    property string terminalAppId: "weather-screen"

    // Last geometry sent to Sway.
    property int lastX: -99999
    property int lastY: -99999
    property int lastWidth: -1
    property int lastHeight: -1

    property bool revealAfterSync: false

    // The Weather Station is the first live consumer of the reusable
    // window-assembly tracker. The QML instrument bay owns the canonical
    // scene rectangle; Kitty is a follower.
    property string assemblySceneId: "weather-station-terminal"
    property bool assemblyDefined: false

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
    // The QML bay remains the structural truth, but movement is now delegated
    // to the persistent WindowAssemblyBridge instead of spawning swaymsg for
    // every geometry change.
    // ─────────────────────────────────────────────

    WindowAssemblyTracker {
        id: assemblyTracker

        intervalMs: 8

        onSnapshot: function (payload) {
            terminalView.handleAssemblySnapshot(payload);
        }

        onBridgeError: function (message) {
            console.log("StationTerminal assembly:", message);

            if (terminalView.terminalState === "STARTING")
                terminalView.terminalState = "SYNC ERROR";
        }
    }

    Process {
        id: revealProcess

        command: ["swaymsg", "[app_id=\"^weather-screen$\"] scratchpad show"]

        onExited: function (exitCode, exitStatus) {
            if (exitCode === 0) {
                terminalView.revealAfterSync = false;
                terminalView.terminalState = "VISIBLE";
                terminalView.syncGeometry(true);
            } else {
                terminalView.terminalState = "SYNC ERROR";
            }
        }
    }

    function currentBayRect() {
        if (!stationGeometryReady)
            return null;

        // terminalView fills mainView. Its origin inside the station is:
        //   X = mode rail width
        //   Y = header height
        //
        // terminalBay then contributes bayX/bayY inside terminalView.
        // No mapToGlobal(), QsWindow lookup, or guessed window size is needed.
        return assemblyTracker.rect(
            stationGlobalX + stationRailWidth + bayX,
            stationGlobalY + stationHeaderHeight + bayY,
            bayWidth,
            bayHeight
        );
    }
    function rectMatchesBay(rect) {
        if (!rect)
            return false;

        const bay = currentBayRect();

        if (!bay)
            return false;

        return Math.round(Number(rect.x)) === bay.x
            && Math.round(Number(rect.y)) === bay.y
            && Math.round(Number(rect.width)) === bay.width
            && Math.round(Number(rect.height)) === bay.height;
    }

    function defineAssembly(sceneRect) {
        assemblyDefined = assemblyTracker.defineScene(
            assemblySceneId,
            sceneRect,
            [
                assemblyTracker.member(
                    "screen",
                    { appId: terminalAppId },
                    assemblyTracker.transform(
                        0, 0,
                        0, 0,
                        1, 0,
                        1, 0
                    ),
                    {
                        // Weather Station is a layer-shell instrument, so its
                        // QML bay is authoritative for this first test.
                        canLead: false,
                        setup: true,
                        tolerance: 0
                    }
                )
            ],
            {
                minimumWidth: 1,
                minimumHeight: 1,
                watch: true,
                sync: true
            }
        );

        if (!assemblyDefined) {
            terminalState = "SYNC ERROR";
            console.log("StationTerminal assembly: bridge is not running");
        }
    }

    function syncGeometry(force) {
        if (terminalState !== "VISIBLE" && !revealAfterSync)
            return;

        const bay = currentBayRect();

        if (!bay)
            return;

        if (!force
                && bay.x === lastX
                && bay.y === lastY
                && bay.width === lastWidth
                && bay.height === lastHeight) {
            return;
        }

        lastX = bay.x;
        lastY = bay.y;
        lastWidth = bay.width;
        lastHeight = bay.height;

        if (!assemblyDefined) {
            defineAssembly(bay);
            return;
        }

        assemblyTracker.setSceneRect(
            assemblySceneId,
            bay,
            true
        );
    }

    function handleAssemblySnapshot(payload) {
        if (!payload || payload.scene !== assemblySceneId)
            return;

        if (!revealAfterSync || revealProcess.running)
            return;

        const members = payload.members || {};
        const screen = members.screen;

        // Reveal only after the hidden Kitty surface has actually reached the
        // QML bay. This preserves the old "place first, show second" behavior.
        if (screen && rectMatchesBay(screen.rect))
            revealProcess.running = true;
    }

    // mapToGlobal() has no change signal. Sample the source bay cheaply while
    // the terminal is alive; actual Sway mutations stay on the persistent
    // bridge and are only sent when the geometry changed.
    Timer {
        interval: 16
        repeat: true
        running: terminalView.terminalState === "VISIBLE"
            || terminalView.revealAfterSync

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
            terminalView.revealAfterSync = false;

            if (terminalView.assemblyDefined) {
                assemblyTracker.removeScene(terminalView.assemblySceneId);
                terminalView.assemblyDefined = false;
            }

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
