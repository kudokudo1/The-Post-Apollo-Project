import QtQuick
import Quickshell
import Quickshell.Io

// SKY-only ISS geometric pass predictions. Pass geometry comes from
// iss-in.space; orbital element epoch/provenance comes directly from CelesTrak.
// This service does not claim optical visibility.
Scope {
    id: iss

    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string sourceName: "ISS-IN.SPACE"
    property string orbitalSource: "CELESTRAK"
    property string predictionModel: ""
    property bool geometricPassOnly: true
    property bool visibilityEvaluated: false
    property var orbit: null
    property var passes: []
    property int passCount: 0
    property date lastUpdated

    property string inflightKey: ""

    readonly property real latitudeNumber: Number(latitude)
    readonly property real longitudeNumber: Number(longitude)
    readonly property bool configured:
        latitude !== "" && longitude !== ""
        && isFinite(latitudeNumber) && isFinite(longitudeNumber)
        && latitudeNumber >= -90 && latitudeNumber <= 90
        && longitudeNumber >= -180 && longitudeNumber <= 180
    readonly property string currentKey:
        configured
        ? latitudeNumber.toFixed(3) + "|" + longitudeNumber.toFixed(3)
        : ""
    readonly property bool loading: fetchProcess.running

    function refresh() {
        if (!active || !configured || fetchProcess.running)
            return false;
        inflightKey = currentKey;
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/iss_passes.py",
            String(latitude), String(longitude)
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
                    || !Array.isArray(parsed.passes)
                    || parsed.passes.length === 0
                    || !parsed.orbit)
                throw new Error("invalid ISS pass response");

            sourceName = String(parsed.source || "ISS-IN.SPACE");
            orbitalSource = String(parsed.orbitalSource || "CELESTRAK");
            predictionModel = String(parsed.predictionModel || "");
            geometricPassOnly = parsed.geometricPassOnly !== false;
            visibilityEvaluated = parsed.visibilityEvaluated === true;
            orbit = parsed.orbit;
            passes = parsed.passes;
            passCount = Number(parsed.passCount || passes.length);
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "ISS PASS DATA UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []

        stdout: StdioCollector {
            onStreamFinished: iss.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && iss.currentKey === iss.inflightKey) {
                iss.failed = true;
                iss.errorText = "ISS PASS REQUEST FAILED";
            }
            if (iss.active && iss.configured
                    && iss.currentKey !== iss.inflightKey)
                Qt.callLater(function() { iss.refresh(); });
        }
    }

    // CelesTrak GP data updates on roughly a two-hour cadence. Match that
    // provider freshness instead of repeatedly downloading unchanged elements.
    Timer {
        interval: 7200000
        repeat: true
        running: iss.active && iss.configured
        onTriggered: iss.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: iss.refresh()
    }

    onActiveChanged: {
        if (active && configured)
            locationDebounce.restart();
    }
    onLatitudeChanged: {
        if (active && configured)
            locationDebounce.restart();
    }
    onLongitudeChanged: {
        if (active && configured)
            locationDebounce.restart();
    }
    Component.onCompleted: {
        if (active && configured)
            locationDebounce.restart();
    }
}
