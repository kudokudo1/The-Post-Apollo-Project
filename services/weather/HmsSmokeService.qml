import QtQuick
import Quickshell
import Quickshell.Io
import "HmsSmokePolicy.js" as SmokePolicy

// Manual, view-scoped NOAA HMS analyst smoke product. Daily KML is fetched
// only on explicit operator request; no timer or pan/zoom network behavior.
Scope {
    id: smoke

    readonly property string sourceName: "NOAA HMS // SMOKE PLUMES"
    readonly property bool loading: fetchProcess.running

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var polygons: []
    property string analysisDate: ""
    property int ageDays: -1
    property int vertexCount: 0
    property bool truncated: false
    property date lastUpdated
    property double lastRequestMs: 0

    readonly property var summary: SmokePolicy.summary(polygons)

    function request() {
        if (fetchProcess.running)
            return false;

        const now = Date.now();
        if (lastRequestMs > 0 && now - lastRequestMs < 30000) {
            failed = true;
            errorText = "HMS REQUEST COOLDOWN";
            return false;
        }

        lastRequestMs = now;
        failed = false;
        errorText = "";
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/hms_smoke_fetch.py"
        ];
        fetchProcess.running = true;
        return true;
    }

    function clear() {
        polygons = [];
        ready = false;
        failed = false;
        errorText = "";
        analysisDate = "";
        ageDays = -1;
        vertexCount = 0;
        truncated = false;
    }

    function acceptResponse(raw) {
        try {
            const parsed = JSON.parse(String(raw || ""));
            if (!parsed || parsed.error || !Array.isArray(parsed.polygons))
                throw new Error("invalid HMS response");
            polygons = parsed.polygons;
            analysisDate = String(parsed.analysisDate || "");
            ageDays = Number(parsed.ageDays);
            vertexCount = Number(parsed.vertexCount || 0);
            truncated = !!parsed.truncated;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "HMS SMOKE UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: smoke.acceptResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && !smoke.failed) {
                smoke.failed = true;
                smoke.errorText = "HMS REQUEST FAILED";
            }
        }
    }
}
