import QtQuick
import Quickshell
import Quickshell.Io
import "UsnoMoonPolicy.js" as MoonPolicy

// SKY-only one-day Moon ephemeris. This uses the provider-local civil offset
// already calibrated from Weather sunrise; it never substitutes desktop TZ.
Scope {
    id: moon

    property bool active: true
    property string date: ""
    property var latitude: ""
    property var longitude: ""
    property var offsetMinutes: null

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var ephemeris: MoonPolicy.emptyResult()
    property date lastUpdated

    property string loadedKey: ""
    property string inflightKey: ""

    readonly property var request:
        MoonPolicy.requestInfo(date, latitude, longitude, offsetMinutes)
    readonly property bool configured: request.valid
    readonly property bool loading: moonFetch.running
    readonly property string endpoint:
        configured ? request.endpoint : ""

    function clearForInput() {
        ready = false;
        failed = false;
        errorText = "";
        ephemeris = MoonPolicy.emptyResult();
        loadedKey = "";
    }

    function scheduleRefresh() {
        if (!active || !configured) {
            refreshDelay.stop();
            if (!configured)
                clearForInput();
            return;
        }

        if (request.key !== loadedKey) {
            ready = false;
            failed = false;
            errorText = "";
            ephemeris = MoonPolicy.emptyResult();
            refreshDelay.restart();
        }
    }

    function refresh() {
        if (!active || !configured || moonFetch.running
                || request.key === loadedKey)
            return false;

        inflightKey = request.key;
        moonFetch.command = [
            "curl", "-fsSL", "--max-time", "12",
            "--proto", "=https", "--proto-redir", "=https",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.5",
            request.endpoint
        ];
        moonFetch.running = true;
        return true;
    }

    function accept(raw) {
        if (!configured || request.key !== inflightKey)
            return;
        try {
            ephemeris = MoonPolicy.parse(JSON.parse(String(raw || "")));
            loadedKey = inflightKey;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            ready = false;
            failed = true;
            errorText = "USNO MOON EPHEMERIS UNAVAILABLE";
            console.log("UsnoMoonService parse error:", error);
        }
    }

    Process {
        id: moonFetch
        command: []

        stdout: StdioCollector {
            onStreamFinished: moon.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            const currentKey = moon.configured ? moon.request.key : "";
            if (exitCode !== 0 && currentKey === moon.inflightKey) {
                moon.ready = false;
                moon.failed = true;
                moon.errorText = "USNO MOON REQUEST FAILED";
            }
            if (moon.active && moon.configured
                    && currentKey !== moon.inflightKey
                    && currentKey !== moon.loadedKey)
                Qt.callLater(function() { moon.refresh(); });
        }
    }

    Timer {
        id: refreshDelay
        interval: 250
        repeat: false
        onTriggered: moon.refresh()
    }

    onActiveChanged: scheduleRefresh()
    onDateChanged: scheduleRefresh()
    onLatitudeChanged: scheduleRefresh()
    onLongitudeChanged: scheduleRefresh()
    onOffsetMinutesChanged: scheduleRefresh()

    Component.onCompleted: scheduleRefresh()
}
