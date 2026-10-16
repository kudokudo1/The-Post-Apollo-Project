import QtQuick
import Quickshell
import qs.services.notifications
import "WeatherAqiPolicy.js" as AqiPolicy

// Display-only observer of the existing session-wide WeatherService.
// Never starts a fetch, modifies weather readings, or takes system actions.
Scope {
    id: producer

    required property var weatherService
    property int announcedBand: 0

    function observeAqi() {
        if (!weatherService || !weatherService.aqiReady)
            return;

        const value = Number(weatherService.aqi);
        const decision = AqiPolicy.nextTransition(announcedBand, value);
        announcedBand = decision.nextBand;

        if (!decision.shouldNotify)
            return;

        const band = AqiPolicy.bandForAqi(value);
        const label = AqiPolicy.labelForBand(band);
        const rounded = Math.round(value);
        NotificationsService.pushRich({
            "source": "WEATHER STATION",
            "sourceId": "weather-station",
            "category": "internal",
            "severity": AqiPolicy.severityForBand(band),
            "title": "AIR QUALITY // " + label,
            "message": "US AQI " + rounded
                       + " // " + label
                       + ". Review Weather Station for details.",
            "tags": ["weather", "air-quality", "aqi"],
            "context": {
                "eventType": "aqi-unhealthy-transition",
                "aqi": rounded,
                "band": band
            }
        });
    }

    Connections {
        target: producer.weatherService

        function onAqiChanged() { producer.observeAqi(); }
        function onAqiReadyChanged() { producer.observeAqi(); }
    }

    Component.onCompleted: observeAqi()
}
