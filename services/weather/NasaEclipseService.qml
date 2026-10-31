import QtQuick
import Quickshell
import Quickshell.Io

// SKY-only global eclipse calendar from NASA GSFC annual eclipse pages.
// This slice is intentionally event-date context only. It does not claim
// local visibility, contact times, magnitude, obscuration, or maximum time.
Scope {
    id: eclipses

    property bool active: true

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string sourceName: "NASA GSFC ECLIPSE WEB SITE"
    property var events: []
    property var nextSolar: null
    property var nextLunar: null
    property int eventCount: 0
    property string dateScope: ""
    property bool localVisibility: false
    property bool exactMaximumTime: false
    property date lastUpdated

    readonly property bool loading: fetchProcess.running

    function refresh() {
        if (!active || fetchProcess.running)
            return false;
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/nasa_eclipse_calendar.py"
        ];
        fetchProcess.running = true;
        return true;
    }

    function accept(raw) {
        try {
            const parsed = JSON.parse(String(raw || ""));
            if (!parsed || parsed.error
                    || String(parsed.source || "") === ""
                    || !Array.isArray(parsed.events))
                throw new Error("invalid NASA eclipse response");

            sourceName = String(parsed.source || "NASA GSFC ECLIPSE WEB SITE");
            events = parsed.events;
            nextSolar = parsed.nextSolar || null;
            nextLunar = parsed.nextLunar || null;
            eventCount = Number(parsed.eventCount || events.length);
            dateScope = String(parsed.dateScope || "");
            localVisibility = parsed.localVisibility === true;
            exactMaximumTime = parsed.exactMaximumTime === true;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "NASA ECLIPSE CALENDAR UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []

        stdout: StdioCollector {
            onStreamFinished: eclipses.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                eclipses.failed = true;
                eclipses.errorText = "NASA ECLIPSE REQUEST FAILED";
            }
        }
    }

    Timer {
        interval: 43200000
        repeat: true
        running: eclipses.active
        onTriggered: eclipses.refresh()
    }

    Timer {
        id: initialDelay
        interval: 250
        repeat: false
        onTriggered: eclipses.refresh()
    }

    onActiveChanged: {
        if (active)
            initialDelay.restart();
    }

    Component.onCompleted: {
        if (active)
            initialDelay.restart();
    }
}
