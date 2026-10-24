import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "StationTerminalGeometry.js" as SwayGeometry

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
    // Identity is pinned when launched. Changing the menu mode cannot make
    // CLOSE accidentally kill a different domain's console.
    property string terminalMode: "terminal"
    property string sessionMode: "terminal"
    property bool pendingClose: false
    readonly property string terminalAppId:
        sessionMode === "terminal" ? "weather-screen"
        : "weather-screen-" + sessionMode
    readonly property string sessionTitle:
        sessionMode === "terminal" ? "STAR MAP"
        : sessionMode.toUpperCase() + " CONSOLE"

    function supportedMode(mode) {
        return ["home", "ground", "sky", "space", "map",
                "news", "radio", "terminal"].indexOf(mode) !== -1;
    }

    function launchCommand() {
        // Both the app ID and title derive only from the closed mode list.
        // Other domains get a plain Bash terminal, not a fictitious TUI.
        const executable = sessionMode === "terminal"
            ? "/var/home/mapple/.local/bin/weatherstation-starmap"
            : "/usr/bin/bash -l";
        return "kitty --config /var/home/mapple/.config/kitty/weatherstation.conf "
            + "--override confirm_os_window_close=0 "
            + "--app-id " + terminalAppId
            + " --title '" + sessionTitle + "' " + executable
            + " >/dev/null 2>&1 &";
    }

    // Coordinates and cut-out are LOCAL to the panel. These properties
    // were referenced by WeatherStationW's mask but previously absent.
    readonly property real bayX: terminalBay.x
    readonly property real bayY: terminalBay.y
    readonly property real bayWidth: terminalBay.width
    readonly property real bayHeight: terminalBay.height

    readonly property string outputName:
        targetScreen ? String(targetScreen.name || "") : ""
    property var swayOutputs: []

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

        command: ["bash", "-lc", terminalView.launchCommand()]

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

        command: ["bash", "-lc",
                  "for i in $(seq 1 100); do "
                  + "if swaymsg -t get_tree | grep -Fq '\\"app_id\\": \\""
                  + terminalView.terminalAppId
                  + "\\"'; then exit 0; fi; sleep 0.05; done; exit 1"]

        onExited: function (exitCode, exitStatus) {
            if (exitCode === 0) {
                if (terminalView.pendingClose) {
                    terminalView.closeTerminal();
                    return;
                }
                terminalView.revealAfterSync = true;
                terminalView.syncGeometry(true);
            } else {
                terminalView.pendingClose = false;
                terminalView.terminalState = "START ERROR";
            }
        }
    }

    // ─────────────────────────────────────────────
    // SWAY OUTPUT GEOMETRY
    //
    // Wayland layer-shell mapToGlobal() can be surface-local and is NOT
    // reliable for swaymsg move absolute. Query the target output's logical
    // global rect from the compositor and anchor the bay inside that rect.
    // ─────────────────────────────────────────────

    Process {
        id: outputProcess
        command: ["swaymsg", "-t", "get_outputs"]

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const parsed = JSON.parse(String(text || ""));
                    if (!Array.isArray(parsed))
                        throw new Error("Missing Sway output list");
                    terminalView.swayOutputs = parsed;
                    if (terminalView.revealAfterSync)
                        terminalView.syncGeometry(true);
                    else if (terminalView.terminalState === "VISIBLE")
                        terminalView.syncGeometry(false);
                } catch (error) {
                    terminalView.terminalState = "OUTPUT ERROR";
                    console.log("Weather terminal output geometry:", error);
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0)
                terminalView.terminalState = "OUTPUT ERROR";
        }
    }

    Timer {
        // A low-frequency output refresh handles hotplug/scale/move. The
        // existing fast geometry timer emits no Sway command if unchanged.
        interval: 2000
        repeat: true
        running: terminalView.terminalState === "VISIBLE"
        onTriggered: {
            if (!outputProcess.running)
                outputProcess.running = true;
        }
    }

    onOutputNameChanged: {
        if (terminalState !== "IDLE" && !outputProcess.running)
            outputProcess.running = true;
    }

    // ─────────────────────────────────────────────
    // GEOMETRY SYNC
    // ─────────────────────────────────────────────

    Process {
        id: geometryProcess

        property int targetX: 0
        property int targetY: 0
        property int targetWidth: 0
        property int targetHeight: 0

        // Do NOT run "scratchpad show" after placing: it can move/hide
        // an already-visible scratchpad window or fail for normal Kitty.
        command: ["swaymsg", "[app_id=\"^" + terminalView.terminalAppId
                  + "$\"] floating enable, border none, resize set "
                  + targetWidth + " " + targetHeight
                  + ", move absolute position " + targetX + " " + targetY]

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

        const box = SwayGeometry.position(
            swayOutputs, outputName,
            stationWidth, stationRightMargin, stationHeaderHeight,
            stationRailWidth, terminalBay.x, terminalBay.y,
            terminalBay.width, terminalBay.height
        );
        if (!box)
            return;

        const gx = box.x;
        const gy = box.y;
        const gw = box.width;
        const gh = box.height;

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

        command: ["swaymsg", "[app_id=\"^" + terminalView.terminalAppId
                  + "$\"] kill"]

        onExited: function (exitCode, exitStatus) {
            terminalView.terminalState = "IDLE";
            terminalView.pendingClose = false;
            terminalView.revealAfterSync = false;

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
        if (terminalState === "VISIBLE" || terminalState === "STARTING"
                || closeProcess.running || pendingClose)
            return false;
        if (!supportedMode(terminalMode))
            return false;
        if (!outputName) {
            terminalState = "OUTPUT ERROR";
            return false;
        }
        sessionMode = terminalMode;
        terminalState = "STARTING";
        swayOutputs = [];
        if (!outputProcess.running)
            outputProcess.running = true;
        if (!launchProcess.running)
            launchProcess.running = true;
        return true;
    }

    function closeTerminal() {
        if (terminalState === "IDLE" || closeProcess.running)
            return;
        if (terminalState === "STARTING" && waitForKitty.running) {
            pendingClose = true;
            return;
        }
        pendingClose = false;
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

        // Transparent children alone cannot punch through a painted parent.
        // The Weather Station chassis paints four strips around this bay.
        color: terminalView.terminalState === "VISIBLE"
               ? "transparent" : Colors.black
    }

    // ─────────────────────────────────────────────
    // TITLE
    // ─────────────────────────────────────────────

    Text {
        anchors.top: parent.top
        anchors.left: parent.left

        anchors.topMargin: 22
        anchors.leftMargin: 30

        text: terminalView.sessionTitle

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

        // Lower top edge, substantially larger reading area after moving
        // launch/close controls to the Weather Station header.
        x: 14
        y: 90

        width: Math.max(0, parent.width - 28)
        height: Math.max(0, parent.height - 108)

        color: terminalView.terminalState === "VISIBLE" ? "transparent" : Colors.black

        border.width: 2
        border.color: Colors.cyan

        z: 4

        Text {
            anchors.centerIn: parent

            visible: terminalView.terminalState !== "VISIBLE"

            text: terminalView.sessionTitle + " // "
                  + (terminalView.terminalState === "STARTING" ? "INITIALIZING"
                     : terminalView.terminalState === "START ERROR" ? "ERROR"
                       : "STANDBY")

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

}
