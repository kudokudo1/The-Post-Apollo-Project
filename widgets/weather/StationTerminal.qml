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
        // Supply Kitty with the final bay size at WINDOW CREATION, not
        // just a later Sway resize. Do not mutate the user's kitty config.
        const w = Math.round(terminalBay.width);
        const h = Math.round(terminalBay.height);
        return "kitty --config /var/home/mapple/.config/kitty/weatherstation.conf "
            + "--override remember_window_size=no "
            + "--override initial_window_width=" + w + " "
            + "--override initial_window_height=" + h + " "
            + "--override resize_in_steps=no "
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

    // The observed Sway window may differ from requested resize dimensions.
    // Feed only the actual intersecting region to the overlay alpha cutout.
    property real verifiedOffsetX: 0
    property real verifiedOffsetY: 0
    property real verifiedWidth: 0
    property real verifiedHeight: 0
    property string fitStatus: "UNVERIFIED"
    readonly property real visibleBayX: bayX + verifiedOffsetX
    readonly property real visibleBayY: bayY + verifiedOffsetY
    readonly property real visibleBayWidth: verifiedWidth
    readonly property real visibleBayHeight: verifiedHeight

    readonly property string outputName:
        targetScreen ? String(targetScreen.name || "") : ""
    property var swayOutputs: []

    // Last geometry sent to Sway.
    property int lastX: -99999
    property int lastY: -99999
    property int lastWidth: -1
    property int lastHeight: -1

    property bool revealAfterSync: false
    // At most one post-map corrective resize and one center fallback.
    // Never spin resizing Kitty every 75 ms.
    property int fitResizeRetries: 0
    property bool fitCenterAttempted: false

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
                  + "if swaymsg -t get_tree | grep -Fq '\"app_id\": \""
                  + terminalView.terminalAppId
                  + "\"'; then exit 0; fi; sleep 0.05; done; exit 1"]

        onExited: function (exitCode, exitStatus) {
            if (exitCode === 0) {
                if (terminalView.pendingClose) {
                    if (!closeProcess.running)
                        closeProcess.running = true;
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

        // Explicit px units, then verify compositor-applied geometry.
        // A successful Sway IPC exit does NOT prove Kitty accepted resize.
        command: ["swaymsg", "[app_id=\"^" + terminalView.terminalAppId
                  + "$\"] floating enable, border none, resize set width "
                  + targetWidth + " px height " + targetHeight
                  + " px, move absolute position " + targetX + " " + targetY]

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                terminalView.terminalState = "SYNC ERROR";
                return;
            }
            terminalView.lastX = targetX;
            terminalView.lastY = targetY;
            terminalView.lastWidth = targetWidth;
            terminalView.lastHeight = targetHeight;

            if (terminalView.pendingClose || closeProcess.running) {
                // During STARTING, closeTerminal() would only re-arm the
                // pending flag; kill the now-mapped actor directly instead.
                if (!closeProcess.running)
                    closeProcess.running = true;
                return;
            }
            // Wayland applies configure asynchronously; reading get_tree
            // immediately can observe the old Kitty rect. Wait briefly.
            verifyDelay.restart();
        }


    }

    Timer {
        id: verifyDelay
        interval: 250
        repeat: false
        onTriggered: {
            if (!terminalView.pendingClose && !closeProcess.running
                    && !verifyProcess.running)
                verifyProcess.running = true;
        }
    }

    Process {
        id: centerProcess
        property int targetX: 0
        property int targetY: 0
        // Only the exact Weather terminal identity can be moved. Do not
        // target the currently focused window or every Kitty application.
        command: ["swaymsg", "[app_id=\"^" + terminalView.terminalAppId
                  + "$\"] move absolute position " + targetX + " " + targetY]
        onExited: function(exitCode, exitStatus) {
            if (terminalView.pendingClose || closeProcess.running)
                return;
            if (exitCode !== 0) {
                terminalView.fitStatus = "CENTER ERROR";
                terminalView.terminalState = "VERIFY ERROR";
                return;
            }
            verifyDelay.restart();
        }
    }

    // Sway's JSON tree reports the ACTUAL Kitty size. Never reveal the
    // whole bay merely because the resize command returned exit code zero.
    Process {
        id: verifyProcess
        command: ["swaymsg", "-t", "get_tree"]
        stdout: StdioCollector {
            onStreamFinished: {
                if (terminalView.pendingClose || closeProcess.running)
                    return;
                try {
                    const tree = JSON.parse(String(text || ""));
                    const actual = SwayGeometry.observedWindow(
                        tree, terminalView.terminalAppId);
                    const requested = {
                        x: geometryProcess.targetX,
                        y: geometryProcess.targetY,
                        width: geometryProcess.targetWidth,
                        height: geometryProcess.targetHeight
                    };
                    if (!actual)
                        throw new Error("Kitty actor not visible in Sway tree");
                    const overlap = SwayGeometry.visibleIntersection(requested, actual);
                    if (!overlap || !overlap.exact) {
                        if (terminalView.fitResizeRetries < 1) {
                            // Initial Kitty dimensions/configure may still
                            // be stale. Try the SAME requested size once.
                            terminalView.fitResizeRetries += 1;
                            if (!geometryProcess.running)
                                geometryProcess.running = true;
                            return;
                        }
                        if (!terminalView.fitCenterAttempted) {
                            const centered = SwayGeometry.centeredPosition(requested, actual);
                            terminalView.fitCenterAttempted = true;
                            if (centered && (actual.x !== centered.x
                                             || actual.y !== centered.y)) {
                                centerProcess.targetX = centered.x;
                                centerProcess.targetY = centered.y;
                                centerProcess.running = true;
                                return;
                            }
                        }
                    }
                    if (!overlap)
                        throw new Error("Kitty absent or outside intended bay");
                    terminalView.verifiedOffsetX = overlap.x;
                    terminalView.verifiedOffsetY = overlap.y;
                    terminalView.verifiedWidth = overlap.width;
                    terminalView.verifiedHeight = overlap.height;
                    terminalView.fitStatus = overlap.exact ? "ALIGNED" : "PARTIAL";
                    terminalView.revealAfterSync = false;
                    terminalView.terminalState = "VISIBLE";
                } catch (error) {
                    terminalView.fitStatus = "NO VERIFIED RECT";
                    terminalView.terminalState = "VERIFY ERROR";
                    console.log("Weather terminal size verification:", error);
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && !terminalView.pendingClose) {
                terminalView.fitStatus = "Sway tree unavailable";
                terminalView.terminalState = "VERIFY ERROR";
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
        // A *new* requested bay/screen geometry gets its own bounded
        // verification cycle. A retry for identical geometry does not.
        if (gx !== lastX || gy !== lastY || gw !== lastWidth || gh !== lastHeight) {
            fitResizeRetries = 0;
            fitCenterAttempted = false;
        }
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
            verifyDelay.stop();
            terminalView.fitResizeRetries = 0;
            terminalView.fitCenterAttempted = false;
            terminalView.verifiedWidth = 0;
            terminalView.verifiedHeight = 0;
            terminalView.verifiedOffsetX = 0;
            terminalView.verifiedOffsetY = 0;
            terminalView.fitStatus = "UNVERIFIED";

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
        fitResizeRetries = 0;
        fitCenterAttempted = false;
        verifiedWidth = 0;
        verifiedHeight = 0;
        fitStatus = "UNVERIFIED";
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
        if (terminalState === "STARTING") {
            // Launch may still be racing compositor registration.
            // Let waitForKitty finish, then kill the exact session actor.
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

        text: terminalView.terminalState === "VISIBLE"
              && terminalView.fitStatus === "PARTIAL"
              ? "PARTIAL FIT" : terminalView.terminalState

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 14

        color: terminalView.terminalState === "VISIBLE" ? Colors.cyan : Colors.orange

        z: 5
    }

    // The shared title/status row serves STAR MAP and every domain
    // console (MAP, NEWS, RADIO, SKY, etc.). Keep one cyan inset
    // divider here rather than duplicating it in each mode.
    Rectangle {
        id: terminalTitleDivider
        x: 14
        y: 64
        width: Math.max(0, parent.width - 28)
        height: 2
        color: Colors.cyan
        z: 5
    }

    // ─────────────────────────────────────────────
    // ACTUAL INSTRUMENT BAY
    //
    // Kitty is locked to THIS rectangle.
    // ─────────────────────────────────────────────

    Rectangle {
        id: terminalBay

        // Center the viewport vertically between the shared title rule
        // and Station footer, with the SAME 8px clearance on each side.
        // Keep height unchanged at the current Station size; Sway positioning,
        // observed-geometry alpha cutout and input mask all follow this bay.
        readonly property real verticalClearance: 8
        x: 8
        y: terminalTitleDivider.y + terminalTitleDivider.height + verticalClearance

        width: Math.max(0, parent.width - 16)
        height: Math.max(0, parent.height - y - verticalClearance)

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
