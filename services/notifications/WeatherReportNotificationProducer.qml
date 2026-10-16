import QtQuick
import Quickshell
import qs.services.notifications
import "WeatherReportPolicy.js" as WeatherReportPolicy

// Current-conditions report observed from the existing WeatherService.
// No new network calls, external commands, forecasts, or system mutations.
Scope {
    id: producer
    required property var weatherService
    property string deliveredDay: ""
    property double firstWeatherReadyMs: 0

    function historyContains(id) {
        const history = NotificationsService.notifications;
        for (let i = 0; i < history.count; ++i) {
            if (String(history.get(i).id || "") === id)
                return true;
        }
        return false;
    }

    function maybePublish() {
        if (!NotificationsService.historyReady || !weatherService)
            return;

        const now = new Date();
        const day = WeatherReportPolicy.localDayKey(now);
        const id = "apollo-weather-report-" + day;

        if (deliveredDay === day)
            return;
        if (historyContains(id)) {
            deliveredDay = day;
            return;
        }

        const record = WeatherReportPolicy.snapshot(
            weatherService, now.getTime());
        if (!record)
            return;

        // Give the existing follow-up AQI request time to finish, but do not
        // suppress a weather report indefinitely when that API is unavailable.
        if (!weatherService.aqiReady) {
            if (firstWeatherReadyMs <= 0)
                firstWeatherReadyMs = now.getTime();
            if (now.getTime() - firstWeatherReadyMs < 90000)
                return;
        }

        NotificationsService.pushRich({
            "id": id,
            "source": "WEATHER REPORT",
            "sourceId": "weather-brief",
            "category": "internal",
            "severity": "normal",
            "title": "WEATHER REPORT // CURRENT CONDITIONS",
            "message": WeatherReportPolicy.summary(record),
            "tags": ["weather", "current-conditions", "daily-report"],
            "metrics": {
                "temperatureF": record.temperatureF,
                "feelsLikeF": record.feelsLikeF,
                "condition": record.condition,
                "humidityPercent": record.humidityPercent,
                "windMph": record.windMph,
                "windDirection": record.windDirection,
                "aqi": record.aqi,
                "aqiLabel": record.aqiLabel,
                "pm25": record.pm25,
                "pm10": record.pm10
            },
            "context": {
                "eventType": "weather-daily-report",
                "localDay": day,
                "observedAtUtc": record.observedAtUtc,
                "weatherSource": "wttr.in",
                "airQualitySource": record.aqi === null
                                   ? "" : "Open-Meteo",
                "airQualityTiming": "last available AQI; separate observation"
            }
        });
        deliveredDay = day;
    }

    Connections {
        target: producer.weatherService
        function onReadyChanged() { producer.maybePublish(); }
        function onLastUpdatedChanged() { producer.maybePublish(); }
        function onAqiReadyChanged() { producer.maybePublish(); }
        function onAqiChanged() { producer.maybePublish(); }
    }

    Connections {
        target: NotificationsService
        function onHistoryReadyChanged() { producer.maybePublish(); }
    }

    // Used only for the new day and the bounded wait for optional AQI.
    Timer {
        interval: 30000
        repeat: true
        running: true
        onTriggered: producer.maybePublish()
    }
    Component.onCompleted: maybePublish()
}
