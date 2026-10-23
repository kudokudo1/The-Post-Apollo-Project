import QtQuick
import Quickshell
import Quickshell.Io
import "StationDiscoveryPolicy.js" as DiscoveryPolicy

// Mounted only by the selected MAP / NEWS / RADIO page.
// No polling while the other domains are selected or the menu is closed.
Scope {
    id: discovery

    property string domain: "map"
    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var rows: []
    property date lastUpdated

    readonly property bool loading: fetchProcess.running
    readonly property string endpoint: {
        if (domain === "map")
            return "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=30";
        if (domain === "news")
            return "https://api.gdeltproject.org/api/v2/doc/doc"
                   + "?query=(weather%20OR%20earthquake%20OR%20wildfire%20OR%20aurora)"
                   + "&mode=artlist&maxrecords=30&timespan=24h&format=json";
        if (domain === "radio")
            return "https://de1.api.radio-browser.info/json/stations/topvote/30"
                   + "?hidebroken=true";
        return "";
    }
    function refresh() {
        if (active && endpoint !== "" && !fetchProcess.running)
            fetchProcess.running = true;
    }
    function parseResponse(rawText) {
        try {
            const parsed = DiscoveryPolicy.parse(domain, JSON.parse(rawText));
            rows = parsed;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "SOURCE RESPONSE UNAVAILABLE";
            console.log("StationDiscoveryService", domain, error);
        }
    }
    Process {
        id: fetchProcess
        command: ["curl", "-fsSL", "--compressed", "--max-time", "14",
                  "-A", "Post-Apollo-WeatherStation/0.1", discovery.endpoint]
        stdout: StdioCollector {
            onStreamFinished: discovery.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                discovery.failed = true;
                discovery.errorText = "SOURCE REQUEST FAILED";
            }
        }
    }
    Timer {
        interval: 900000
        repeat: true
        running: discovery.active
        onTriggered: discovery.refresh()
    }
    onActiveChanged: { if (active) refresh(); }
    Component.onCompleted: { if (active) refresh(); }
}
