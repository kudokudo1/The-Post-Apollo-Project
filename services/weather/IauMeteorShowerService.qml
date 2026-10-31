import QtQuick
import Quickshell
import Quickshell.Io

// SKY-only established meteor-shower catalog from the IAU Meteor Data Center.
// The helper converts the provider's solar-longitude activity model into a
// current active list, approximate upcoming UTC peak times, and local radiant
// altitude for the Weather Station coordinate fix.
Scope {
    id: meteors

    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string sourceName: "IAU METEOR DATA CENTER"
    property string sourceVersion: ""
    property int catalogCount: 0
    property real solarLongitude: -1
    property int activeCount: 0
    property var activeShowers: []
    property var upcomingShowers: []
    property string note: ""
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
            Quickshell.configDir + "/scripts/weather/iau_meteor_showers.py",
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
                    || String(parsed.source || "") === ""
                    || !Array.isArray(parsed.active)
                    || !Array.isArray(parsed.upcoming))
                throw new Error("invalid IAU meteor response");

            sourceName = String(parsed.source || "IAU Meteor Data Center")
                .toUpperCase();
            sourceVersion = String(parsed.version || "");
            catalogCount = Number(parsed.catalogCount || 0);
            solarLongitude = Number(parsed.solarLongitude);
            activeCount = Number(parsed.activeCount || 0);
            activeShowers = parsed.active;
            upcomingShowers = parsed.upcoming;
            note = String(parsed.note || "");
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "IAU METEOR SHOWER CATALOG UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []

        stdout: StdioCollector {
            onStreamFinished: meteors.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && meteors.currentKey === meteors.inflightKey) {
                meteors.failed = true;
                meteors.errorText = "IAU METEOR REQUEST FAILED";
            }
            if (meteors.active && meteors.configured
                    && meteors.currentKey !== meteors.inflightKey)
                Qt.callLater(function() { meteors.refresh(); });
        }
    }

    Timer {
        interval: 21600000
        repeat: true
        running: meteors.active && meteors.configured
        onTriggered: meteors.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: meteors.refresh()
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
