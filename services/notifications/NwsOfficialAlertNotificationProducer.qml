import QtQuick
import Quickshell
import Quickshell.Io
import qs.services.notifications
import "NwsOfficialAlertPolicy.js" as NwsPolicy

// Opt-in official NWS active point alerts. Required launch environment:
// POST_APOLLO_NWS_ALERT_POINT="latitude,longitude" (up to 4 decimal places).
// No IP-derived location, geolocation permission, or silent location guessing.
Scope {
    id: producer

    readonly property string alertPoint:
        NwsPolicy.configuredPoint(Quickshell.env("POST_APOLLO_NWS_ALERT_POINT"))
    readonly property string endpoint: alertPoint === "" ? ""
        : "https://api.weather.gov/alerts/active?point=" + alertPoint

    property var activeAlerts: ({})
    property bool fetchSucceeded: false
    property date lastUpdated
    property string errorText: ""

    // Public read-only seam for Weather Station. The notification producer
    // remains the ONE owner of the NWS request and pinned-point lifecycle.
    readonly property bool configured: alertPoint !== ""
    readonly property bool loading: nwsFetch.running
    readonly property bool ready: fetchSucceeded
    readonly property var alertList: NwsPolicy.visibleAlerts(activeAlerts)
    readonly property int activeCount: alertList.length

    function historyContains(alertId, revision, kind) {
        const model = NotificationsService.notifications;
        for (let i = model.count - 1; i >= 0; --i) {
            const row = model.get(i);
            const context = row.context || {};
            if (String(context.alertId || "") === alertId
                    && String(context.revision || "") === revision
                    && String(context.eventType || "") === "nws-" + kind)
                return true;
        }
        return false;
    }

    function publish(change) {
        const alert = change.alert;
        const kind = change.kind;
        if (!alert || producer.historyContains(alert.id, alert.revision, kind))
            return;

        const vanished = kind === "not-listed";
        const sourceLabel = "NWS // " + alert.event;
        const status = vanished ? "NO LONGER LISTED AS ACTIVE"
                     : kind === "updated" ? "UPDATED" : "ACTIVE";
        const narrative = vanished
            ? "This alert was absent from two successful NWS active-feed checks. "
              + "That does not establish cancellation or all-clear."
            : "Official NWS alert " + status.toLowerCase() + ".";
        const message = (alert.headline || alert.event)
                      + " // " + (alert.area || "AREA NOT PROVIDED")
                      + " // " + narrative
                      + " Expires " + alert.expires
                      + ". Review the National Weather Service bulletin.";
        NotificationsService.pushRich({
            "source": "WEATHER STATION",
            "sourceId": "weather-station-nws",
            "category": "internal",
            "severity": vanished ? "normal" : alert.displaySeverity,
            "title": sourceLabel + " // " + status,
            "message": message.slice(0, 1000),
            "tags": ["weather", "nws", "official-alert"],
            "context": {
                "eventType": "nws-" + kind,
                "origin": "apollo",
                "domain": "weather",
                "issuer": alert.issuer,
                "alertId": alert.id,
                "revision": alert.revision,
                "area": alert.area,
                "expiresUtc": alert.expires,
                "source": "NWS active alerts API"
            }
        });
    }

    function acceptResponse(text) {
        if (!NotificationsService.historyReady)
            return;
        const alerts = NwsPolicy.parseActive(text, Date.now());
        if (!alerts) {
            producer.errorText = "NWS RESPONSE INVALID";
            return; // malformed/failed request is NOT an all-clear
        }
        const outcome = NwsPolicy.advance(producer.activeAlerts, alerts);
        producer.activeAlerts = outcome.state;
        producer.fetchSucceeded = true;
        producer.lastUpdated = new Date();
        producer.errorText = "";
        for (const change of outcome.changes)
            producer.publish(change);
    }

    Process {
        id: nwsFetch
        command: [
            "curl", "-fsSL", "--max-time", "12",
            "-H", "Accept: application/geo+json",
            "-A", "Post-Apollo-WeatherStation (https://github.com/kudokudo1/The-Post-Apollo-Project)",
            producer.endpoint
        ]
        stdout: StdioCollector {
            onStreamFinished: producer.acceptResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0)
                producer.errorText = "NWS REQUEST FAILED";
        }
    }

    function refresh() {
        if (producer.alertPoint !== "" && NotificationsService.historyReady
                && !nwsFetch.running)
            nwsFetch.running = true;
    }

    Timer {
        interval: 900000
        repeat: true
        running: producer.alertPoint !== ""
        onTriggered: producer.refresh()
    }
    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.refresh(); }
    }
    Component.onCompleted: producer.refresh()
}
