import QtQuick
import Quickshell
import Quickshell.Io
import "SolarCyclePolicy.js" as SolarCyclePolicy

// SPACE-only monthly solar-cycle prediction context.
// This does not duplicate the live F10.7 observation already owned by
// SpaceService, and it deliberately has no repeating timer.
Scope {
    id: cycle

    property bool active: true

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var summary: SolarCyclePolicy.emptySummary()
    property date lastUpdated
    property string loadedMonth: ""

    readonly property bool loading: predictionFetch.running
    readonly property string currentMonth:
        SolarCyclePolicy.monthKeyFromMs(Date.now())
    readonly property string endpoint:
        "https://services.swpc.noaa.gov/json/solar-cycle/predicted-solar-cycle.json"

    function refresh(force) {
        const month = SolarCyclePolicy.monthKeyFromMs(Date.now());
        if (!active || predictionFetch.running || month === "")
            return false;
        if (!force && ready && loadedMonth === month)
            return false;

        predictionFetch.running = true;
        return true;
    }

    function accept(raw) {
        try {
            const parsed = SolarCyclePolicy.summarize(
                JSON.parse(String(raw || "")),
                Date.now()
            );
            summary = parsed;
            loadedMonth = parsed.targetMonth;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "NOAA SOLAR-CYCLE PREDICTION UNAVAILABLE";
            console.log("SolarCycleService parse error:", error);
        }
    }

    Process {
        id: predictionFetch
        command: [
            "curl", "-fsSL", "--max-time", "12",
            "--proto", "=https", "--proto-redir", "=https",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.6",
            cycle.endpoint
        ]

        stdout: StdioCollector {
            onStreamFinished: cycle.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                cycle.failed = true;
                cycle.errorText = "NOAA SOLAR-CYCLE REQUEST FAILED";
            }
        }
    }

    onActiveChanged: {
        if (active)
            Qt.callLater(function() { cycle.refresh(false); });
    }

    Component.onCompleted: {
        if (active)
            Qt.callLater(function() { cycle.refresh(false); });
    }
}
