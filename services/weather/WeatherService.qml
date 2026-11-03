import QtQuick
import Quickshell
import Quickshell.Io
import "WeatherDataPolicy.js" as WeatherDataPolicy
import "OpenMeteoFallbackPolicy.js" as FallbackPolicy
import "../location/WeatherLocationPolicy.js" as LocationPolicy

Scope {
    id: weatherService

    property var cacheStore: null
    property var historyStore: null
    // Optional shared user-selected place. Existing standalone consumers
    // keep wttr.in's legacy location lookup when no manual Home is set.
    property var placeRegistry: null
    readonly property var selectedPlace:
        placeRegistry ? placeRegistry.effectivePlace : null
    property bool locationBooted: false
    property string weatherRequestContextKey: ""
    property string aqiRequestContextKey: ""
    property bool usingPersistentCurrentCache: false
    property bool usingPersistentForecastCache: false
    property bool usingPersistentAqiCache: false

    // Both sources feed the same WeatherService data contract. The primary
    // gets a bounded attempt at every scheduled refresh, so recovery does
    // not require a manual reset. Fallback never owns a place selection.
    property string activeWeatherProvider: "NONE"
    property string primaryWeatherStatus: "IDLE"
    property string fallbackWeatherStatus: "IDLE"
    property string fallbackWeatherError: ""
    property int weatherGeneration: 0
    property bool primaryParseSucceeded: false
    property bool fallbackParseSucceeded: false
    property int fallbackGeneration: 0
    property string fallbackRequestContextKey: ""
    property date fallbackLastUpdated

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

    // Provider values are retained separately. The public latitude/longitude
    // always prefer a validated user-selected Home/Explore coordinate.
    property string providerLatitude: ""
    property string providerLongitude: ""
    readonly property var resolvedCoordinates:
        LocationPolicy.coordinates(
            selectedPlace, providerLatitude, providerLongitude
        )
    readonly property string latitude: resolvedCoordinates.latitude
    readonly property string longitude: resolvedCoordinates.longitude
    readonly property string requestContextKey:
        LocationPolicy.requestContextKey(selectedPlace, location)
    readonly property bool hasManualPlace:
        LocationPolicy.manualPoint(selectedPlace) !== null

    readonly property string historyScopeKey: {
        if (latitude === "" || longitude === "")
            return "";
        const lat = Number(latitude);
        const lon = Number(longitude);
        if (!isFinite(lat) || !isFinite(lon)
                || lat < -90 || lat > 90 || lon < -180 || lon > 180)
            return "";
        return lat.toFixed(3) + "|" + lon.toFixed(3);
    }

    property string errorText: ""

    property date lastUpdated

    readonly property bool loading:
        weatherFetch.running || fallbackWeatherFetch.running

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
    // timezone=auto metadata from the SAME Open-Meteo AQ response.
    // Used by SKY for civil-time astronomy; no extra request.
    property var airQualityUtcOffsetMinutes: null
    property string airQualityTimezone: ""
    property string airQualityTimezoneAbbreviation: ""

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
        const query = LocationPolicy.locationQuery(selectedPlace, location);
        return query.length > 0
            ? "https://wttr.in/" + encodeURIComponent(query) + "?format=j1"
            : "https://wttr.in/?format=j1";
    }

    readonly property string fallbackWeatherEndpoint:
        hasManualPlace ? FallbackPolicy.endpoint(latitude, longitude) : ""

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
                if (weatherService.weatherRequestContextKey
                        === weatherService.requestContextKey)
                    weatherService.parseWeather(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            // Give StdioCollector a chance to settle before deciding whether
            // the completed request needs a fallback.
            Qt.callLater(function() {
                if (weatherService.weatherRequestContextKey
                        !== weatherService.requestContextKey) {
                    weatherService.refresh();
                    return;
                }
                if (exitCode === 0 && weatherService.primaryParseSucceeded) {
                    weatherService.primaryWeatherStatus = "READY";
                    return;
                }
                weatherService.primaryWeatherStatus = exitCode === 0
                    ? "PARSE_FAILED" : "REQUEST_FAILED";
                if (!weatherService.startFallbackWeather() && !weatherService.ready)
                    weatherService.errorText = "wttr.in request failed";
            });
        }
    }

    // Separate process only runs after primary failure, for manual Home or
    // Explore coordinates. It is never a duplicate continuous poller.
    Process {
        id: fallbackWeatherFetch
        command: [
            "curl", "-fsSL", "--max-time", "10", "--connect-timeout", "5",
            weatherService.fallbackWeatherEndpoint
        ]
        stdout: StdioCollector {
            onStreamFinished: {
                if (weatherService.fallbackRequestContextKey
                        === weatherService.requestContextKey
                        && weatherService.fallbackGeneration
                           === weatherService.weatherGeneration)
                    weatherService.parseFallbackWeather(text);
            }
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (weatherService.fallbackRequestContextKey
                        !== weatherService.requestContextKey
                        || weatherService.fallbackGeneration
                           !== weatherService.weatherGeneration) {
                    // A new primary may have failed while the previous
                    // fallback was still exiting. Try the pending context.
                    if (weatherService.primaryWeatherStatus !== "READY"
                            && !weatherService.ready)
                        weatherService.startFallbackWeather();
                    return;
                }
                if (exitCode === 0 && weatherService.fallbackParseSucceeded) {
                    weatherService.fallbackWeatherStatus = "READY";
                    return;
                }
                weatherService.fallbackWeatherStatus = exitCode === 0
                    ? "PARSE_FAILED" : "REQUEST_FAILED";
                weatherService.fallbackWeatherError =
                    "Open-Meteo forecast unavailable";
                if (!weatherService.ready)
                    weatherService.errorText = "weather providers unavailable";
            });
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
                if (weatherService.aqiRequestContextKey
                        === weatherService.requestContextKey)
                    weatherService.parseAirQuality(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (weatherService.aqiRequestContextKey
                    !== weatherService.requestContextKey) {
                Qt.callLater(weatherService.refreshAirQuality);
                return;
            }
            if (exitCode !== 0)
                weatherService.aqiErrorText = "air quality request failed";
        }
    }

    function hydratePersistentCache() {
        // The legacy weather cache is global, not keyed by user coordinates.
        // Never label its payload as the selected Home or Explore destination.
        if (!cacheStore || hasManualPlace)
            return false;

        const now = Date.now();
        let hydrated = false;

        if (!ready) {
            const saved = cacheStore.record("weather-current", now);
            if (saved && saved.payload) {
                const p = saved.payload;
                tempF = String(p.tempF || "--");
                feelsLikeF = String(p.feelsLikeF || "--");
                condition = String(p.condition || "UNKNOWN");
                weatherCode = String(p.weatherCode || "");
                uvIndex = Number(p.uvIndex);
                humidity = String(p.humidity || "--");
                windMph = String(p.windMph || "--");
                windDirection = String(p.windDirection || "--");
                pressureHpa = Number(p.pressureHpa);
                visibilityMiles = Number(p.visibilityMiles);
                cloudCover = Number(p.cloudCover);
                precipMm = Number(p.precipMm);
                observationTime = String(p.observationTime || "");
                localObservationDateTime =
                    String(p.localObservationDateTime || "");
                localObservationAnchorMs = Number(saved.receivedAtMs);
                providerLatitude = String(p.latitude || "");
                providerLongitude = String(p.longitude || "");
                lastUpdated = new Date(saved.receivedAtMs);
                errorText = "";
                ready = true;
                usingPersistentCurrentCache = true;
                activeWeatherProvider = "CACHE";
                hydrated = true;
            }
        }

        if (!forecastReady) {
            const saved = cacheStore.record("weather-forecast", now);
            if (saved && saved.payload) {
                hourlyForecast =
                    Array.isArray(saved.payload.hourlyForecast)
                    ? saved.payload.hourlyForecast.slice() : [];
                dailyForecast =
                    Array.isArray(saved.payload.dailyForecast)
                    ? saved.payload.dailyForecast.slice() : [];
                if (hourlyForecast.length > 0 || dailyForecast.length > 0) {
                    forecastLastUpdated =
                        new Date(saved.receivedAtMs);
                    usingPersistentForecastCache = true;
                    hydrated = true;
                }
            }
        }

        if (!aqiReady) {
            const saved = cacheStore.record("air-quality", now);
            if (saved && saved.payload) {
                const p = saved.payload;
                aqi = Number(p.aqi);
                aqiLabel = String(p.aqiLabel || describeAqi(aqi));
                ozoneAqi = Number(p.ozoneAqi);
                nitrogenDioxideAqi = Number(p.nitrogenDioxideAqi);
                carbonMonoxideAqi = Number(p.carbonMonoxideAqi);
                pm25 = Number(p.pm25);
                pm10 = Number(p.pm10);
                carbonMonoxide = Number(p.carbonMonoxide);
                nitrogenDioxide = Number(p.nitrogenDioxide);
                ozone = Number(p.ozone);
                dust = Number(p.dust);
                alderPollen = Number(p.alderPollen);
                birchPollen = Number(p.birchPollen);
                grassPollen = Number(p.grassPollen);
                mugwortPollen = Number(p.mugwortPollen);
                olivePollen = Number(p.olivePollen);
                ragweedPollen = Number(p.ragweedPollen);
                pollenAvailable = p.pollenAvailable === true;
                airQualitySourceTime =
                    String(p.airQualitySourceTime || "");
                airQualityUtcOffsetMinutes =
                    p.airQualityUtcOffsetMinutes === null
                    || p.airQualityUtcOffsetMinutes === undefined
                    ? null : Number(p.airQualityUtcOffsetMinutes);
                airQualityTimezone =
                    String(p.airQualityTimezone || "");
                airQualityTimezoneAbbreviation =
                    String(p.airQualityTimezoneAbbreviation || "");
                airQualityForecast =
                    Array.isArray(p.airQualityForecast)
                    ? p.airQualityForecast.slice() : [];
                aqiLastUpdated = new Date(saved.receivedAtMs);
                aqiErrorText = "";
                aqiReady = true;
                usingPersistentAqiCache = true;
                hydrated = true;
            }
        }

        return hydrated;
    }

    function persistCurrentWeather(receivedAtMs) {
        // Keep user-scoped observations out of legacy unscoped cache records.
        if (!cacheStore || hasManualPlace)
            return false;
        return cacheStore.put("weather-current", receivedAtMs, {
            "tempF": tempF,
            "feelsLikeF": feelsLikeF,
            "condition": condition,
            "weatherCode": weatherCode,
            "uvIndex": uvIndex,
            "humidity": humidity,
            "windMph": windMph,
            "windDirection": windDirection,
            "pressureHpa": pressureHpa,
            "visibilityMiles": visibilityMiles,
            "cloudCover": cloudCover,
            "precipMm": precipMm,
            "observationTime": observationTime,
            "localObservationDateTime": localObservationDateTime,
            "latitude": latitude,
            "longitude": longitude
        });
    }

    function captureCurrentHistory(receivedAtMs) {
        if (!historyStore || historyScopeKey === "" || !ready)
            return false;
        return historyStore.append(
            "weather-current",
            historyScopeKey,
            receivedAtMs,
            receivedAtMs,
            {
                "tempF": tempF,
                "feelsLikeF": feelsLikeF,
                "humidity": humidity,
                "windMph": windMph,
                "pressureHpa": pressureHpa,
                "visibilityMiles": visibilityMiles,
                "cloudCover": cloudCover,
                "precipMm": precipMm,
                "uvIndex": uvIndex,
                "condition": condition
            }
        );
    }

    function captureAirQualityHistory(receivedAtMs) {
        if (!historyStore || historyScopeKey === "" || !aqiReady)
            return false;
        return historyStore.append(
            "air-quality",
            historyScopeKey,
            receivedAtMs,
            receivedAtMs,
            {
                "aqi": aqi,
                "pm25": pm25,
                "pm10": pm10,
                "ozoneAqi": ozoneAqi,
                "nitrogenDioxideAqi": nitrogenDioxideAqi,
                "carbonMonoxideAqi": carbonMonoxideAqi,
                "ozone": ozone,
                "nitrogenDioxide": nitrogenDioxide,
                "carbonMonoxide": carbonMonoxide,
                "dust": dust
            }
        );
    }

    function persistForecast(receivedAtMs) {
        if (!cacheStore || hasManualPlace || !forecastReady)
            return false;
        return cacheStore.put("weather-forecast", receivedAtMs, {
            "hourlyForecast": hourlyForecast,
            "dailyForecast": dailyForecast
        });
    }

    function persistAirQuality(receivedAtMs) {
        if (!cacheStore || hasManualPlace || !aqiReady)
            return false;
        return cacheStore.put("air-quality", receivedAtMs, {
            "aqi": aqi,
            "aqiLabel": aqiLabel,
            "ozoneAqi": ozoneAqi,
            "nitrogenDioxideAqi": nitrogenDioxideAqi,
            "carbonMonoxideAqi": carbonMonoxideAqi,
            "pm25": pm25,
            "pm10": pm10,
            "carbonMonoxide": carbonMonoxide,
            "nitrogenDioxide": nitrogenDioxide,
            "ozone": ozone,
            "dust": dust,
            "alderPollen": alderPollen,
            "birchPollen": birchPollen,
            "grassPollen": grassPollen,
            "mugwortPollen": mugwortPollen,
            "olivePollen": olivePollen,
            "ragweedPollen": ragweedPollen,
            "pollenAvailable": pollenAvailable,
            "airQualitySourceTime": airQualitySourceTime,
            "airQualityUtcOffsetMinutes": airQualityUtcOffsetMinutes,
            "airQualityTimezone": airQualityTimezone,
            "airQualityTimezoneAbbreviation":
                airQualityTimezoneAbbreviation,
            "airQualityForecast": airQualityForecast
        });
    }

    Connections {
        target: weatherService.cacheStore
        enabled: !!weatherService.cacheStore
        function onStorageStateChanged() {
            if (!weatherService.cacheStore)
                return;
            const state = String(weatherService.cacheStore.storageState || "");
            if (state === "ready" || state === "empty")
                weatherService.hydratePersistentCache();
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
        if (!weatherFetch.running) {
            weatherGeneration += 1;
            weatherRequestContextKey = requestContextKey;
            primaryParseSucceeded = false;
            primaryWeatherStatus = "FETCHING";
            weatherFetch.running = true;
        }
    }

    function startFallbackWeather() {
        if (fallbackWeatherFetch.running)
            return true;
        if (fallbackWeatherEndpoint === "") {
            fallbackWeatherStatus = "NO_MANUAL_PLACE";
            return false;
        }
        fallbackGeneration = weatherGeneration;
        fallbackRequestContextKey = requestContextKey;
        fallbackParseSucceeded = false;
        fallbackWeatherStatus = "FETCHING";
        fallbackWeatherError = "";
        fallbackWeatherFetch.running = true;
        return true;
    }

    function refreshAirQuality() {
        if (airQualityEndpoint === "")
            return;
        if (!airQualityFetch.running) {
            aqiRequestContextKey = requestContextKey;
            airQualityFetch.running = true;
        }
    }

    function clearLocationData() {
        ready = false;
        aqiReady = false;
        tempF = "--";
        feelsLikeF = "--";
        condition = "UNKNOWN";
        weatherCode = "";
        uvIndex = -1;
        humidity = "--";
        windMph = "--";
        windDirection = "--";
        pressureHpa = -1;
        visibilityMiles = -1;
        cloudCover = -1;
        precipMm = -1;
        observationTime = "";
        localObservationDateTime = "";
        localObservationAnchorMs = 0;
        hourlyForecast = [];
        dailyForecast = [];
        providerLatitude = "";
        providerLongitude = "";
        airQualityForecast = [];
        aqi = -1;
        aqiLabel = "UNKNOWN";
        ozoneAqi = -1;
        nitrogenDioxideAqi = -1;
        carbonMonoxideAqi = -1;
        pm25 = -1;
        pm10 = -1;
        carbonMonoxide = -1;
        nitrogenDioxide = -1;
        ozone = -1;
        dust = -1;
        alderPollen = -1;
        birchPollen = -1;
        grassPollen = -1;
        mugwortPollen = -1;
        olivePollen = -1;
        ragweedPollen = -1;
        pollenAvailable = false;
        airQualitySourceTime = "";
        airQualityUtcOffsetMinutes = null;
        airQualityTimezone = "";
        airQualityTimezoneAbbreviation = "";
        errorText = "";
        aqiErrorText = "";
        usingPersistentCurrentCache = false;
        usingPersistentForecastCache = false;
        usingPersistentAqiCache = false;
        activeWeatherProvider = "NONE";
        primaryWeatherStatus = "IDLE";
        fallbackWeatherStatus = "IDLE";
        fallbackWeatherError = "";
    }

    onRequestContextKeyChanged: {
        if (!locationBooted)
            return;
        // Keep in-flight requests bounded by their existing 10s timeout.
        // Their parsers refuse old-context replies; onExited restarts the
        // fetch for the new context. Avoid overlapping process restarts.
        clearLocationData();
        Qt.callLater(function() {
            weatherService.refresh();
            // AQI can load from the saved point even when wttr.in times out.
            weatherService.refreshAirQuality();
        });
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
            const receivedAt = new Date();
            forecastLastUpdated = receivedAt;

            // ─────────────────────────────────────
            // LOCATION FROM WTTR
            // ─────────────────────────────────────

            if (data.nearest_area && data.nearest_area.length > 0) {
                const nearest = data.nearest_area[0];

                if (nearest.latitude)
                    providerLatitude = String(nearest.latitude);

                if (nearest.longitude)
                    providerLongitude = String(nearest.longitude);
            }

            // Fallback for responses where the
            // request itself contains Lat/Lon.
            if ((latitude === "" || longitude === "") && data.request && data.request.length > 0 && data.request[0].query) {
                const query = String(data.request[0].query);

                const match = query.match(/Lat\s+(-?\d+(?:\.\d+)?)\s+and\s+Lon\s+(-?\d+(?:\.\d+)?)/i);

                if (match) {
                    providerLatitude = match[1];
                    providerLongitude = match[2];
                }
            }

            lastUpdated = receivedAt;

            errorText = "";
            ready = true;
            primaryParseSucceeded = true;
            activeWeatherProvider = "WTTR";
            usingPersistentCurrentCache = false;
            usingPersistentForecastCache = false;

            persistCurrentWeather(receivedAt.getTime());
            persistForecast(receivedAt.getTime());
            captureCurrentHistory(receivedAt.getTime());

            // Once weather gives us coordinates,
            // fetch matching AQI.
            refreshAirQuality();
        } catch (error) {
            console.log("WeatherService weather parse error:", error);

            errorText = "weather data parse failed";
        }
    }

    // Parse fallback into a complete temporary object before mutating the
    // shared UI fields. A bad provider response leaves prior data intact.
    function parseFallbackWeather(rawText) {
        const parsed = FallbackPolicy.parse(rawText);
        if (!parsed.ok) {
            fallbackWeatherError = parsed.reason;
            return false;
        }
        const current = parsed.current;
        tempF = current.tempF;
        feelsLikeF = current.feelsLikeF;
        condition = current.condition;
        weatherCode = current.weatherCode;
        uvIndex = current.uvIndex;
        humidity = current.humidity;
        windMph = current.windMph;
        windDirection = current.windDirection;
        pressureHpa = current.pressureHpa;
        visibilityMiles = current.visibilityMiles;
        cloudCover = current.cloudCover;
        precipMm = current.precipMm;
        observationTime = current.observationTime;
        localObservationDateTime = current.localObservationDateTime;
        localObservationAnchorMs = Date.now();
        hourlyForecast = parsed.hourly;
        dailyForecast = parsed.daily;
        const receivedAt = new Date();
        lastUpdated = receivedAt;
        forecastLastUpdated = receivedAt;
        fallbackLastUpdated = receivedAt;
        ready = true;
        fallbackParseSucceeded = true;
        activeWeatherProvider = "OPEN_METEO";
        errorText = "";
        usingPersistentCurrentCache = false;
        usingPersistentForecastCache = false;
        persistCurrentWeather(receivedAt.getTime());
        persistForecast(receivedAt.getTime());
        captureCurrentHistory(receivedAt.getTime());
        refreshAirQuality();
        return true;
    }

    // ─────────────────────────────────────────────
    // AIR QUALITY PARSER
    // ─────────────────────────────────────────────

    function parseAirQuality(rawText) {
        try {
            const root = JSON.parse(rawText);
            const context =
                WeatherDataPolicy.parseAirQualityContext(root);
            airQualityUtcOffsetMinutes = context.utcOffsetMinutes;
            airQualityTimezone = context.timezone;
            airQualityTimezoneAbbreviation =
                context.timezoneAbbreviation;

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
            usingPersistentAqiCache = false;
            persistAirQuality(aqiLastUpdated.getTime());
            captureAirQualityHistory(aqiLastUpdated.getTime());
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
        hydratePersistentCache();
        locationBooted = true;
        // AQI source now has a location from the Place Registry independently
        // of the success/failure of the weather provider.
        refreshAirQuality();
        refresh();
    }
}
