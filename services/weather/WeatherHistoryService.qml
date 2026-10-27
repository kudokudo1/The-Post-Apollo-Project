import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherHistoryPolicy.js" as HistoryPolicy

// Recent completed-day model history for HOME. This is not a local database
// and not an observation archive. It uses Open-Meteo's Historical Forecast API
// only while HOME is active, with a long refresh interval.
Scope {
    id: history

    property bool active: false
    property string latitude: ""
    property string longitude: ""
    property string anchorDateTime: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var daily: []
    property var sameHour: null
    property var summary: ({
        days: 0, maxHighF: -999, minLowF: -999,
        avgHighF: -999, avgLowF: -999,
        precipitationIn: 0, wetDays: 0,
        maxPrecipIn: -1, maxPrecipDate: ""
    })
    property string timezone: ""
    property string timezoneAbbreviation: ""
    property date lastUpdated
    property string loadedKey: ""
    property string lastAttemptKey: ""
    property double lastAttemptMs: 0
    property var inflightSpec: null
    property string inflightKey: ""

    readonly property bool loading: fetchProcess.running
    readonly property var requestSpec:
        HistoryPolicy.requestSpec(latitude, longitude, anchorDateTime)
    function endpointFor(spec) {
        if (!spec || !spec.valid)
            return "";
        return "https://historical-forecast-api.open-meteo.com/v1/forecast"
               + "?latitude=" + spec.latitude
               + "&longitude=" + spec.longitude
               + "&start_date=" + spec.startDate
               + "&end_date=" + spec.endDate
               + "&hourly=temperature_2m,relative_humidity_2m,"
               + "apparent_temperature,pressure_msl,wind_speed_10m"
               + "&daily=temperature_2m_max,temperature_2m_min,"
               + "precipitation_sum,wind_speed_10m_max"
               + "&temperature_unit=fahrenheit"
               + "&wind_speed_unit=mph"
               + "&precipitation_unit=inch"
               + "&timezone=auto";
    }

    function refresh(force) {
        if (!active || !requestSpec.valid || fetchProcess.running)
            return false;

        const now = Date.now();
        const sameKey = lastAttemptKey === requestSpec.key;
        if (!force && sameKey && lastAttemptMs > 0
                && now - lastAttemptMs < 300000)
            return false;

        if (!force && ready && loadedKey === requestSpec.key
                && lastUpdated
                && now - lastUpdated.getTime() < 21600000)
            return false;

        const spec = {
            "valid": true,
            "latitude": requestSpec.latitude,
            "longitude": requestSpec.longitude,
            "startDate": requestSpec.startDate,
            "endDate": requestSpec.endDate,
            "localHour": requestSpec.localHour,
            "key": requestSpec.key
        };
        const requestUrl = endpointFor(spec);
        if (requestUrl === "")
            return false;

        lastAttemptKey = spec.key;
        lastAttemptMs = now;
        inflightSpec = spec;
        inflightKey = spec.key;
        fetchProcess.command = [
            "curl", "-fsSL", "--max-time", "15", requestUrl
        ];
        fetchProcess.running = true;
        return true;
    }

    function acceptResponse(raw) {
        try {
            const parsed = HistoryPolicy.parseResponse(
                JSON.parse(String(raw || "")),
                inflightSpec
            );
            daily = parsed.daily;
            sameHour = parsed.sameHour;
            summary = parsed.summary;
            timezone = parsed.timezone;
            timezoneAbbreviation = parsed.timezoneAbbreviation;
            loadedKey = inflightKey;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "HISTORY RESPONSE UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: history.acceptResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                history.failed = true;
                history.errorText = "HISTORY REQUEST FAILED";
            }
        }
    }

    Timer {
        interval: 21600000
        repeat: true
        running: history.active
        onTriggered: history.refresh(false)
    }

    onActiveChanged: {
        if (active)
            Qt.callLater(function() { history.refresh(false); });
    }
    onLatitudeChanged: {
        if (active)
            Qt.callLater(function() { history.refresh(false); });
    }
    onLongitudeChanged: {
        if (active)
            Qt.callLater(function() { history.refresh(false); });
    }
    onAnchorDateTimeChanged: {
        if (active)
            Qt.callLater(function() { history.refresh(false); });
    }

    Component.onCompleted: {
        if (active)
            refresh(false);
    }
}
