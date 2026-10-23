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
    property string terminalAppId: "weather-screen"

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
        command: ["swaymsg", "[app_id=\"^weather-screen$\"] " + "floating enable, " + "border none, " + "resize set " + targetWidth + " " + targetHeight + ", " + "move absolute position " + targetX + " " + targetY]

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

        if (!outputName) {
            terminalState = "OUTPUT ERROR";
            return;
        }
        terminalState = "STARTING";
        swayOutputs = [];
        if (!outputProcess.running)
            outputProcess.running = true;
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


    // Two Weather actions share the universal ActionButton shell.
    // Weather owns only compact content and the available-width budget.
    // These are ordinary actions; closing the Star Map is not destructive.
    component StationActionButton: ActionButton {
        id: stationAction

        property string fullLabel: ""
        property string compactIcon: ""
        property string miniIcon: ""
        property string actionDescription: fullLabel

        readonly property real labelSpace: Math.max(0, width - 20)
        readonly property bool labelFits:
            minimumLabelMeasure.implicitWidth <= labelSpace
        readonly property bool compactIconFits:
            compactIconMeasure.implicitWidth <= labelSpace
        readonly property string renderedContent:
            labelFits ? fullLabel
            : compactIconFits ? compactIcon
            : miniIcon

        implicitHeight: 35
        height: 35
        label: fullLabel
        showLabel: false
        contentItem.clip: true

        Accessible.role: Accessible.Button
        Accessible.name: actionDescription

        acceptedButtons: Qt.LeftButton
        idleFillColor: Colors.black
        hoverFillColor: Colors.yellow
        selectedFillColor: Colors.yellow
        keyboardSelectedFillColor: Colors.yellow
        pressedFillColor: Colors.magenta

        idleForegroundColor: Colors.cyan
        hoverForegroundColor: Colors.orange
        selectedForegroundColor: Colors.orange
        keyboardSelectedForegroundColor: Colors.orange
        pressedForegroundColor: Colors.black

        idleBorderColor: Colors.cyan
        hoverBorderColor: Colors.orange
        selectedBorderColor: Colors.orange
        keyboardSelectedBorderColor: Colors.orange
        pressedBorderColor: Colors.orange
        // Border widths remain unchanged until the separate border audit.
        idleBorderWidth: 1
        hoverBorderWidth: 1
        selectedBorderWidth: 1
        keyboardSelectedBorderWidth: 1
        pressedBorderWidth: 1

        contentGlowSource: actionText
        contentGlowEnabled: true
        idleContentGlowColor: Colors.cyan
        hoverContentGlowColor: Colors.orange
        selectedContentGlowColor: Colors.orange
        keyboardSelectedContentGlowColor: Colors.orange
        pressedContentGlowColor: Colors.orange
        contentGlowIdleOpacity: 0.35
        contentGlowHoverOpacity: 0.75
        contentGlowSelectedOpacity: 0.75
        contentGlowKeyboardSelectedOpacity: 0.75
        contentGlowPressedOpacity: 1.0

        softGlowEnabled: true
        softGlowSpread: 3
        idleSoftGlowColor: Colors.cyan
        hoverSoftGlowColor: Colors.orange
        selectedSoftGlowColor: Colors.orange
        keyboardSelectedSoftGlowColor: Colors.orange
        pressedSoftGlowColor: Colors.orange
        softGlowIdleOpacity: 0.25
        softGlowHoverOpacity: 0.55
        softGlowSelectedOpacity: 0.55
        softGlowKeyboardSelectedOpacity: 0.55
        softGlowPressedOpacity: 0.60

        // Optional halo stays off so the two actions never visually collide.
        wideGlowEnabled: false
        wideGlowIdleOpacity: 0.015
        wideGlowHoverOpacity: 0.075
        wideGlowSelectedOpacity: 0.075
        wideGlowKeyboardSelectedOpacity: 0.075
        wideGlowPressedOpacity: 0.10

        // Measure text at the minimum readable size before switching to
        // an icon, then a smaller version if even that would not fit.
        GohuText {
            id: minimumLabelMeasure
            visible: false
            text: stationAction.fullLabel
            font.pixelSize: 10
        }
        GohuText {
            id: compactIconMeasure
            visible: false
            text: stationAction.compactIcon
            font.pixelSize: 16
        }
        GohuText {
            id: actionText
            anchors.centerIn: parent
            width: stationAction.labelSpace
            height: Math.max(0, stationAction.height - 8)
            visible: width > 0
            text: stationAction.renderedContent
            font.pixelSize: stationAction.labelFits ? 16
                            : stationAction.compactIconFits ? 16 : 10
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: stationAction.labelFits ? 10 : 8
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideNone
            color: stationAction.foregroundColor
        }
    }

    Row {
        id: stationActionRow
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 28

        // Width of both actions + gap <= panel width - edge clearances.
        readonly property real edgeClearance: 24
        readonly property real availableWidth:
            Math.max(0, terminalView.width - 2 * edgeClearance)
        readonly property real actionWidthBudget:
            Math.max(0, availableWidth - spacing)
        readonly property real widthRatio:
            Math.min(1, actionWidthBudget / (180 + 130))

        spacing: Math.min(18, availableWidth * 0.05)
        z: 5

        StationActionButton {
            width: 180 * stationActionRow.widthRatio
            fullLabel: "[ STAR MAP ]"
            compactIcon: "⌖"
            miniIcon: "⌖"
            actionDescription: "Open Star Map"
            onTriggered: terminalView.openTerminal()
        }

        StationActionButton {
            width: 130 * stationActionRow.widthRatio
            fullLabel: "[ CLOSE ]"
            compactIcon: "×"
            miniIcon: "×"
            actionDescription: "Close Star Map"
            onTriggered: terminalView.closeTerminal()
        }
    }
}
