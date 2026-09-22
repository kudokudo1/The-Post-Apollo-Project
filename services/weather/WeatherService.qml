import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: weatherService

    // ─────────────────────────────────────────────
    // WEATHER DATA
    // ─────────────────────────────────────────────

    property bool ready: false

    property string tempF: "--"
    property string feelsLikeF: "--"
    property string condition: "UNKNOWN"
    property string weatherCode: ""

    property string humidity: "--"

    property string windMph: "--"
    property string windDirection: "--"

    property string latitude: ""
    property string longitude: ""

    property string errorText: ""

    property date lastUpdated

    readonly property bool loading: weatherFetch.running

    // ─────────────────────────────────────────────
    // AIR QUALITY DATA
    // ─────────────────────────────────────────────

    property bool aqiReady: false

    property int aqi: -1
    property string aqiLabel: "UNKNOWN"

    property real pm25: -1
    property real pm10: -1

    property string aqiErrorText: ""

    readonly property bool aqiLoading: airQualityFetch.running

    // ─────────────────────────────────────────────
    // LOCATION
    // ─────────────────────────────────────────────

    // Leave blank to allow wttr.in to resolve
    // the location from the request.
    property string location: ""

    readonly property string endpoint: {
        if (location.trim().length > 0) {
            return "https://wttr.in/" + encodeURIComponent(location.trim()) + "?format=j1";
        }

        return "https://wttr.in/?format=j1";
    }

    readonly property string airQualityEndpoint: {
        if (latitude === "" || longitude === "")
            return "";

        return "https://air-quality-api.open-meteo.com/v1/air-quality" + "?latitude=" + latitude + "&longitude=" + longitude + "&current=us_aqi,pm2_5,pm10" + "&timezone=auto";
    }

    // ─────────────────────────────────────────────
    // WEATHER FETCH
    // ─────────────────────────────────────────────

    Process {
        id: weatherFetch

        command: ["curl", "-fsSL", "--max-time", "10", weatherService.endpoint]

        stdout: StdioCollector {
            onStreamFinished: {
                weatherService.parseWeather(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                weatherService.errorText = "wttr.in request failed";
            }
        }
    }

    // ─────────────────────────────────────────────
    // AIR QUALITY FETCH
    // ─────────────────────────────────────────────

    Process {
        id: airQualityFetch

        command: ["curl", "-fsSL", "--max-time", "10", weatherService.airQualityEndpoint]

        stdout: StdioCollector {
            onStreamFinished: {
                weatherService.parseAirQuality(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                weatherService.aqiErrorText = "air quality request failed";
            }
        }
    }

    // ─────────────────────────────────────────────
    // REFRESH TIMER
    // ─────────────────────────────────────────────

    Timer {
        interval: 900000
        repeat: true
        running: true

        onTriggered: {
            weatherService.refresh();
        }
    }

    // ─────────────────────────────────────────────
    // REFRESH
    // ─────────────────────────────────────────────

    function refresh() {
        if (!weatherFetch.running)
            weatherFetch.running = true;
    }

    function refreshAirQuality() {
        if (airQualityEndpoint === "")
            return;
        if (!airQualityFetch.running)
            airQualityFetch.running = true;
    }

    // ─────────────────────────────────────────────
    // WEATHER PARSER
    // ─────────────────────────────────────────────

    function parseWeather(rawText) {
        try {
            const root = JSON.parse(rawText);

            // wttr.in has existed both with and
            // without this wrapper.
            const data = root.data ? root.data : root;

            if (!data.current_condition || data.current_condition.length === 0) {
                throw new Error("No current conditions");
            }

            const current = data.current_condition[0];

            tempF = current.temp_F || "--";

            feelsLikeF = current.FeelsLikeF || "--";

            humidity = current.humidity || "--";

            windMph = current.windspeedMiles || "--";

            windDirection = current.winddir16Point || "--";

            weatherCode = current.weatherCode || "";

            if (current.weatherDesc && current.weatherDesc.length > 0 && current.weatherDesc[0].value) {
                condition = current.weatherDesc[0].value;
            } else {
                condition = "UNKNOWN";
            }

            // ─────────────────────────────────────
            // LOCATION FROM WTTR
            // ─────────────────────────────────────

            if (data.nearest_area && data.nearest_area.length > 0) {
                const nearest = data.nearest_area[0];

                if (nearest.latitude)
                    latitude = String(nearest.latitude);

                if (nearest.longitude)
                    longitude = String(nearest.longitude);
            }

            // Fallback for responses where the
            // request itself contains Lat/Lon.
            if ((latitude === "" || longitude === "") && data.request && data.request.length > 0 && data.request[0].query) {
                const query = String(data.request[0].query);

                const match = query.match(/Lat\s+(-?\d+(?:\.\d+)?)\s+and\s+Lon\s+(-?\d+(?:\.\d+)?)/i);

                if (match) {
                    latitude = match[1];
                    longitude = match[2];
                }
            }

            lastUpdated = new Date();

            errorText = "";
            ready = true;

            // Once weather gives us coordinates,
            // fetch matching AQI.
            refreshAirQuality();
        } catch (error) {
            console.log("WeatherService weather parse error:", error);

            errorText = "weather data parse failed";
        }
    }

    // ─────────────────────────────────────────────
    // AIR QUALITY PARSER
    // ─────────────────────────────────────────────

    function parseAirQuality(rawText) {
        try {
            const root = JSON.parse(rawText);

            if (!root.current)
                throw new Error("No current AQI data");

            const current = root.current;

            if (current.us_aqi === undefined || current.us_aqi === null) {
                throw new Error("No US AQI value");
            }

            aqi = Math.round(Number(current.us_aqi));

            if (current.pm2_5 !== undefined && current.pm2_5 !== null) {
                pm25 = Number(current.pm2_5);
            }

            if (current.pm10 !== undefined && current.pm10 !== null) {
                pm10 = Number(current.pm10);
            }

            aqiLabel = describeAqi(aqi);

            aqiErrorText = "";
            aqiReady = true;
        } catch (error) {
            console.log("WeatherService AQI parse error:", error);

            aqiErrorText = "AQI data parse failed";
        }
    }

    // ─────────────────────────────────────────────
    // AQI LABEL
    // ─────────────────────────────────────────────

    function describeAqi(value) {
        if (value < 0)
            return "UNKNOWN";

        if (value <= 50)
            return "GOOD";

        if (value <= 100)
            return "MODERATE";

        if (value <= 150)
            return "SENSITIVE";

        if (value <= 200)
            return "UNHEALTHY";

        if (value <= 300)
            return "VERY UNHEALTHY";

        return "HAZARDOUS";
    }

    // ─────────────────────────────────────────────
    // INITIAL FETCH
    // ─────────────────────────────────────────────

    Component.onCompleted: {
        refresh();
    }
}
