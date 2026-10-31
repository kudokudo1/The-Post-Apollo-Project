import QtQuick
import Quickshell
import Quickshell.Io

// GROUND-only local NOAA nowCOAST lightning-density snapshot. The helper
// discovers the public WMS layer at runtime so the UI does not pin an opaque
// provider layer id. No raw Vaisala strike records are requested or stored.
Scope {
    id: lightning

    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string imageUrl: ""
    property string layerName: ""
    property string layerTitle: ""
    property string latestTime: ""
    property int windowMinutes: 15
    property int resolutionKm: 8
    property real radiusKm: 320
    property var bbox: null
    property date lastUpdated
    property string inflightKey: ""

    readonly property string currentKey: {
        const lat = Number(latitude);
        const lon = Number(longitude);
        if (!isFinite(lat) || !isFinite(lon)
                || lat < -90 || lat > 90 || lon < -180 || lon > 180)
            return "";
        return lat.toFixed(3) + "|" + lon.toFixed(3);
    }
    readonly property bool configured: currentKey !== ""
    readonly property bool loading: fetchProcess.running

    function refresh() {
        if (!active || !configured || fetchProcess.running)
            return false;
        inflightKey = currentKey;
        failed = false;
        errorText = "";
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir
                + "/scripts/weather/nowcoast_lightning_snapshot.py",
            String(latitude), String(longitude)
        ];
        fetchProcess.running = true;
        return true;
    }

    function acceptResponse(raw) {
        if (!configured || currentKey !== inflightKey)
            return;
        try {
            const parsed = JSON.parse(String(raw || ""));
            if (!parsed || parsed.error
                    || String(parsed.source || "") !== "NOAA nowCOAST"
                    || String(parsed.product || "")
                       !== "LIGHTNING STRIKE DENSITY"
                    || !String(parsed.imageUrl || "")
                           .startsWith("https://nowcoast.noaa.gov/")
                    || !parsed.bbox)
                throw new Error("invalid nowCOAST lightning response");

            imageUrl = String(parsed.imageUrl);
            layerName = String(parsed.layer || "");
            layerTitle = String(parsed.layerTitle || "");
            latestTime = String(parsed.latestTime || "LATEST");
            windowMinutes = Number(parsed.windowMinutes || 15);
            resolutionKm = Number(parsed.resolutionKm || 8);
            radiusKm = Number(parsed.radiusKm || 320);
            bbox = parsed.bbox;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "NOWCOAST LIGHTNING UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: lightning.acceptResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && lightning.currentKey === lightning.inflightKey) {
                lightning.failed = true;
                lightning.errorText = "NOWCOAST LIGHTNING REQUEST FAILED";
            }
            if (lightning.active && lightning.configured
                    && lightning.currentKey !== lightning.inflightKey)
                Qt.callLater(function() { lightning.refresh(); });
        }
    }

    Timer {
        interval: 900000
        repeat: true
        running: lightning.active && lightning.configured
        onTriggered: lightning.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: lightning.refresh()
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
