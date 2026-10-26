import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherDataPolicy.js" as WeatherDataPolicy

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
    property real uvIndex: -1

    property string humidity: "--"

    property string windMph: "--"
    property string windDirection: "--"

    // Atmospheric observations from the same wttr.in current-condition payload.
    property real pressureHpa: -1
    property real visibilityMiles: -1
    property real cloudCover: -1
    property real precipMm: -1
    property string observationTime: ""
    // The provider's location-local observation clock; used only for
    // sunrise/sunset presentation, never as a global system time zone.
    property string localObservationDateTime: ""
    property real localObservationAnchorMs: 0

    // Forecasts are parsed from the same wttr.in response, so this does not
    // introduce another weather request or another provider.
    property var hourlyForecast: []
    property var dailyForecast: []
    property date forecastLastUpdated
    readonly property bool forecastReady:
        hourlyForecast.length > 0 || dailyForecast.length > 0

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

    // Provider-computed U.S. AQI component indices. These give the pollutant
    // meters a real 0-500 health-index scale while the labels continue to show
    // the raw concentration values.
    property real ozoneAqi: -1
    property real nitrogenDioxideAqi: -1
    property real carbonMonoxideAqi: -1

    property real pm25: -1
    property real pm10: -1
    property real carbonMonoxide: -1
    property real nitrogenDioxide: -1
    property real ozone: -1
    property real dust: -1

    property real alderPollen: -1
    property real birchPollen: -1
    property real grassPollen: -1
    property real mugwortPollen: -1
    property real olivePollen: -1
    property real ragweedPollen: -1
    property bool pollenAvailable: false
    property string airQualitySourceTime: ""

    // Forecast points ride along with the existing AQI request.
    property var airQualityForecast: []
    readonly property bool airQualityForecastReady:
        airQualityForecast.some(function(entry) { return entry.aqi >= 0; })

    property string aqiErrorText: ""
    property date aqiLastUpdated

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

        return "https://air-quality-api.open-meteo.com/v1/air-quality"
               + "?latitude=" + latitude
               + "&longitude=" + longitude
               + "&current=us_aqi,us_aqi_ozone,"
               + "us_aqi_nitrogen_dioxide,us_aqi_carbon_monoxide,"
               + "pm2_5,pm10,carbon_monoxide,"
               + "nitrogen_dioxide,ozone,dust,alder_pollen,birch_pollen,"
               + "grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen"
               + "&hourly=us_aqi,pm2_5,pm10"
               + "&forecast_hours=12"
               + "&timezone=auto";
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

            const atmosphere =
                WeatherDataPolicy.currentAtmosphere(current);
            pressureHpa = atmosphere.pressureHpa;
            visibilityMiles = atmosphere.visibilityMiles;
            cloudCover = atmosphere.cloudCover;
            precipMm = atmosphere.precipMm;
            observationTime = atmosphere.observationTime;
            localObservationDateTime = String(current.localObsDateTime || "");
            localObservationAnchorMs = Date.now();

            weatherCode = current.weatherCode || "";

            // wttr.in j1 supplies UV alongside the current condition.
            // A missing/invalid value must never look like a safe UV reading.
            const reportedUv = Number(current.uvIndex);
            uvIndex = current.uvIndex !== undefined && current.uvIndex !== null
                      && String(current.uvIndex).trim() !== ""
                      && isFinite(reportedUv) && reportedUv >= 0
                      ? reportedUv : -1;

            if (current.weatherDesc && current.weatherDesc.length > 0 && current.weatherDesc[0].value) {
                condition = current.weatherDesc[0].value;
            } else {
                condition = "UNKNOWN";
            }

            const forecast =
                WeatherDataPolicy.parseForecast(data, current, 6);
            hourlyForecast = forecast.hourly;
            dailyForecast = forecast.daily;
            forecastLastUpdated = new Date();

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
            const parsed = WeatherDataPolicy.parseAirQuality(current);

            if (parsed.usAqi < 0)
                throw new Error("No US AQI value");

            aqi = Math.round(parsed.usAqi);
            ozoneAqi = parsed.ozoneAqi;
            nitrogenDioxideAqi = parsed.nitrogenDioxideAqi;
            carbonMonoxideAqi = parsed.carbonMonoxideAqi;
            pm25 = parsed.pm25;
            pm10 = parsed.pm10;
            carbonMonoxide = parsed.carbonMonoxide;
            nitrogenDioxide = parsed.nitrogenDioxide;
            ozone = parsed.ozone;
            dust = parsed.dust;

            alderPollen = parsed.alderPollen;
            birchPollen = parsed.birchPollen;
            grassPollen = parsed.grassPollen;
            mugwortPollen = parsed.mugwortPollen;
            olivePollen = parsed.olivePollen;
            ragweedPollen = parsed.ragweedPollen;
            pollenAvailable = parsed.pollenAvailable;
            airQualitySourceTime = parsed.time;
            airQualityForecast =
                WeatherDataPolicy.parseAirQualityForecast(root.hourly, 12);

            aqiLabel = describeAqi(aqi);

            aqiErrorText = "";
            aqiLastUpdated = new Date();
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
