import QtQuick
import Quickshell
import Quickshell.Io
import "KpForecastPolicy.js" as KpForecastPolicy

// SPACE-only near-term NOAA planetary K forecast.
// Rows tagged observed/estimated are deliberately excluded from the
// presentation; NOAA's provider noaa_scale is never reconstructed locally.
Scope {
    id: forecast

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var summary: KpForecastPolicy.emptySummary()
    property date lastUpdated

    readonly property bool loading: forecastFetch.running
    readonly property string endpoint:
        "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"

    function refresh() {
        if (!active || forecastFetch.running)
            return false;
        forecastFetch.running = true;
        return true;
    }

    function accept(raw) {
        try {
            summary = KpForecastPolicy.summarize(
                JSON.parse(String(raw || "")),
                8
            );
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "NOAA PLANETARY K FORECAST UNAVAILABLE";
            console.log("KpForecastService parse error:", error);
        }
    }

    Process {
        id: forecastFetch
        command: [
            "curl", "-fsSL", "--max-time", "10",
            "--proto", "=https", "--proto-redir", "=https",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.8",
            forecast.endpoint
        ]

        stdout: StdioCollector {
            onStreamFinished: forecast.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                forecast.failed = true;
                forecast.errorText = "NOAA PLANETARY K FORECAST REQUEST FAILED";
            }
        }
    }

    Timer {
        interval: 900000
        repeat: true
        running: forecast.active
        onTriggered: forecast.refresh()
    }

    onActiveChanged: {
        if (active)
            Qt.callLater(function() { forecast.refresh(); });
    }

    Component.onCompleted: {
        if (active)
            Qt.callLater(function() { forecast.refresh(); });
    }
}
