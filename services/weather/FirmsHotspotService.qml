import QtQuick
import Quickshell
import Quickshell.Io
import "FirmsHotspotPolicy.js" as FirmsPolicy

// Optional, operator-triggered NASA FIRMS hotspot intake for the visible MAP
// viewport. No timer, no automatic fetch on pan/zoom, and the MAP_KEY never
// appears in argv or Weather UI.
Scope {
    id: firms

    readonly property string sourceName: "NASA FIRMS // VIIRS NOAA-21 NRT"
    readonly property string mapKey:
        FirmsPolicy.configuredKey(Quickshell.env("POST_APOLLO_FIRMS_MAP_KEY"))
    readonly property bool configured: mapKey !== ""
    readonly property bool loading: fetchProcess.running

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var hotspots: []
    property date lastUpdated
    property string lastBounds: ""
    property double lastRequestMs: 0
    property string inflightBounds: ""

    function request(bounds) {
        if (fetchProcess.running)
            return false;

        if (!configured) {
            failed = true;
            errorText = "FIRMS MAP KEY NOT CONFIGURED";
            return false;
        }

        const area = FirmsPolicy.boundedArea(bounds, 60, 40);
        if (!area.valid) {
            failed = true;
            errorText = area.reason;
            return false;
        }

        const now = Date.now();
        if (lastRequestMs > 0 && now - lastRequestMs < 30000) {
            failed = true;
            errorText = "FIRMS REQUEST COOLDOWN";
            return false;
        }

        inflightBounds = area.bbox;
        lastRequestMs = now;
        failed = false;
        errorText = "";
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/firms_area_fetch.py",
            "VIIRS_NOAA21_NRT",
            inflightBounds,
            "1"
        ];
        fetchProcess.running = true;
        return true;
    }

    function acceptResponse(raw) {
        try {
            const parsed = FirmsPolicy.parseViirsCsv(raw, 800);
            hotspots = parsed;
            ready = true;
            failed = false;
            errorText = "";
            lastBounds = inflightBounds;
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "FIRMS RESPONSE UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: firms.acceptResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                firms.failed = true;
                firms.errorText = "FIRMS REQUEST FAILED";
            }
        }
    }
}
