import QtQuick
import Quickshell
import Quickshell.Io

// SKY-only date-scoped rise/transit/set data for Mercury, Venus, Mars,
// Jupiter and Saturn from USNO's official MRST calculated service.
// The helper parses provider HTML because MRST is not exposed by the JSON API.
Scope {
    id: planets

    property bool active: true
    property string date: ""
    property var latitude: ""
    property var longitude: ""
    property var offsetMinutes: null

    property bool ready: false
    property bool failed: false
    property bool partial: false
    property string errorText: ""
    property var rows: []
    property var failedPlanets: []
    property string precision: ""
    property string azimuthReference: ""
    property date lastUpdated

    property string loadedKey: ""
    property string inflightKey: ""

    readonly property bool dateValid:
        /^\d{4}-\d{2}-\d{2}$/.test(String(date || ""))
    readonly property real latitudeNumber: Number(latitude)
    readonly property real longitudeNumber: Number(longitude)
    readonly property real offsetNumber: Number(offsetMinutes)
    readonly property bool coordinatesValid:
        isFinite(latitudeNumber) && isFinite(longitudeNumber)
        && latitude !== "" && longitude !== ""
        && latitudeNumber >= -90 && latitudeNumber <= 90
        && longitudeNumber >= -180 && longitudeNumber <= 180
    readonly property bool offsetValid:
        offsetMinutes !== null && offsetMinutes !== undefined
        && isFinite(offsetNumber)
        && offsetNumber >= -720 && offsetNumber <= 840
    readonly property bool configured:
        dateValid && coordinatesValid && offsetValid
    readonly property string currentKey:
        configured
        ? String(date) + "|"
          + latitudeNumber.toFixed(4) + "|"
          + longitudeNumber.toFixed(4) + "|"
          + Math.round(offsetNumber)
        : ""
    readonly property bool loading: fetchProcess.running

    function clearForInput() {
        ready = false;
        failed = false;
        partial = false;
        errorText = "";
        rows = [];
        failedPlanets = [];
        precision = "";
        azimuthReference = "";
        loadedKey = "";
    }

    function scheduleRefresh() {
        if (!active || !configured) {
            refreshDelay.stop();
            if (!configured)
                clearForInput();
            return;
        }
        if (currentKey !== loadedKey) {
            ready = false;
            failed = false;
            partial = false;
            errorText = "";
            rows = [];
            failedPlanets = [];
            refreshDelay.restart();
        }
    }

    function refresh() {
        if (!active || !configured || fetchProcess.running
                || currentKey === loadedKey)
            return false;

        inflightKey = currentKey;
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir
                + "/scripts/weather/usno_planet_rise_set.py",
            String(date),
            String(latitude),
            String(longitude),
            String(offsetMinutes)
        ];
        fetchProcess.running = true;
        return true;
    }

    function accept(raw) {
        if (!configured || currentKey !== inflightKey)
            return;
        try {
            const parsed = JSON.parse(String(raw || ""));
            if (!parsed || parsed.error
                    || String(parsed.source || "") !== "USNO MRST"
                    || !Array.isArray(parsed.planets)
                    || parsed.planets.length === 0)
                throw new Error("invalid USNO planet response");

            rows = parsed.planets;
            failedPlanets = Array.isArray(parsed.failedPlanets)
                ? parsed.failedPlanets : [];
            precision = String(parsed.precision || "");
            azimuthReference = String(parsed.azimuthReference || "");
            partial = failedPlanets.length > 0;
            loadedKey = inflightKey;
            lastUpdated = new Date();
            ready = true;
            failed = partial;
            errorText = partial
                ? "USNO PLANET EPHEMERIS PARTIAL // "
                  + failedPlanets.join(" / ")
                : "";
        } catch (error) {
            ready = false;
            failed = true;
            partial = false;
            errorText = "USNO PLANET RISE / SET UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []

        stdout: StdioCollector {
            onStreamFinished: planets.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            const current = planets.configured ? planets.currentKey : "";
            if (exitCode !== 0 && current === planets.inflightKey
                    && !planets.ready) {
                planets.failed = true;
                planets.errorText = "USNO PLANET REQUEST FAILED";
            }
            if (planets.active && planets.configured
                    && current !== planets.inflightKey
                    && current !== planets.loadedKey)
                Qt.callLater(function() { planets.refresh(); });
        }
    }

    Timer {
        id: refreshDelay
        interval: 250
        repeat: false
        onTriggered: planets.refresh()
    }

    onActiveChanged: scheduleRefresh()
    onDateChanged: scheduleRefresh()
    onLatitudeChanged: scheduleRefresh()
    onLongitudeChanged: scheduleRefresh()
    onOffsetMinutesChanged: scheduleRefresh()

    Component.onCompleted: scheduleRefresh()
}
