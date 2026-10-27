import QtQuick
import "../../components"
import "StationHomePolicy.js" as StationHomePolicy
import "StationSourceHealthPolicy.js" as SourceHealth
import "StationOfficialAlertPolicy.js" as OfficialAlertPolicy
import "../../services/weather/WeatherHistoryPolicy.js" as HistoryPolicy

Rectangle {
    id: home

    property var weatherService: null
    property var spaceService: null
    property var nwsAlertSource: null
    property var historyService: null

    readonly property bool historyReady:
        historyService && historyService.ready
    readonly property var historyDaily:
        historyReady ? historyService.daily : []
    readonly property var historySameHour:
        historyReady ? historyService.sameHour : null
    readonly property var historySummary:
        historyReady ? historyService.summary
                     : ({
                           days: 0, maxHighF: -999, minLowF: -999,
                           avgHighF: -999, avgLowF: -999,
                           precipitationIn: 0, wetDays: 0,
                           maxPrecipIn: -1, maxPrecipDate: ""
                       })


    readonly property var officialAlertSummary:
        OfficialAlertPolicy.summary(
            nwsAlertSource && Array.isArray(nwsAlertSource.alertList)
            ? nwsAlertSource.alertList : []
        )

    readonly property bool weatherReady:
        weatherService && weatherService.ready
    readonly property bool aqiReady:
        weatherService && weatherService.aqiReady
    readonly property bool spaceReady:
        spaceService && spaceService.ready
    readonly property bool spacePartial:
        spaceService
        && !spaceService.ready
        && (
            spaceService.kpReady
            || spaceService.solarWindReady
            || spaceService.magneticFieldReady
            || spaceService.solarFluxReady
        )

    readonly property real temperatureValue:
        weatherReady ? Number(weatherService.tempF) : 0
    readonly property real humidityValue:
        weatherReady ? Number(weatherService.humidity) : 0
    readonly property real windValue:
        weatherReady ? Number(weatherService.windMph) : 0
    readonly property real aqiValue:
        aqiReady ? Number(weatherService.aqi) : 0
    readonly property real uvValue:
        weatherReady ? Number(weatherService.uvIndex) : -1
    readonly property real kpValue:
        spaceService && spaceService.kpReady
        ? Number(spaceService.kp) : 0

    readonly property var nextForecast:
        weatherService
        && Array.isArray(weatherService.hourlyForecast)
        && weatherService.hourlyForecast.length > 0
        ? weatherService.hourlyForecast[0]
        : null

    readonly property real nextRainChance:
        nextForecast && Number(nextForecast.chanceRain) >= 0
        ? Number(nextForecast.chanceRain) : 0

    property double relevanceClockMs: Date.now()

    readonly property int weatherAgeMinutes: {
        relevanceClockMs;

        if (!weatherService || !weatherService.ready)
            return -1;

        const stamp = weatherService.lastUpdated;
        if (!stamp || typeof stamp.getTime !== "function")
            return -1;

        const millis = stamp.getTime();
        if (!isFinite(millis) || millis <= 0)
            return -1;

        return Math.max(
            0,
            Math.floor((relevanceClockMs - millis) / 60000)
        );
    }

    readonly property bool weatherStale:
        weatherReady
        && (
            String(weatherService.errorText || "").length > 0
            || weatherAgeMinutes >= 20
        )

    // Space feeds have different natural cadences. Kp is reported in
    // three-hour bins, solar-wind/IMF summaries are near-real-time, and
    // F10.7 is a daily observation. Use source-specific age windows with
    // slack instead of falsely applying one freshness threshold to all four.
    readonly property int kpStaleAfterMinutes: 360
    readonly property int solarWindStaleAfterMinutes: 45
    readonly property int magneticFieldStaleAfterMinutes: 45
    readonly property int solarFluxStaleAfterMinutes: 2160

    function sourceAgeMinutes(value) {
        relevanceClockMs;

        let raw = String(value || "").trim();
        if (!raw)
            return -1;

        raw = raw.replace(" ", "T");

        if (!/(Z|[+\-]\d{2}:?\d{2})$/i.test(raw))
            raw += "Z";

        const millis = Date.parse(raw);
        if (!isFinite(millis) || millis <= 0)
            return -1;

        return Math.max(
            0,
            Math.floor((relevanceClockMs - millis) / 60000)
        );
    }

    function dateMillis(value) {
        if (!value || typeof value.getTime !== "function")
            return -1;
        const millis = value.getTime();
        return isFinite(millis) && millis > 0 ? millis : -1;
    }

    readonly property int kpAgeMinutes:
        spaceService && spaceService.kpReady
        ? sourceAgeMinutes(spaceService.kpTime) : -1
    readonly property int solarWindAgeMinutes:
        spaceService && spaceService.solarWindReady
        ? sourceAgeMinutes(spaceService.solarWindTime) : -1
    readonly property int magneticFieldAgeMinutes:
        spaceService && spaceService.magneticFieldReady
        ? sourceAgeMinutes(spaceService.magneticFieldTime) : -1
    readonly property int solarFluxAgeMinutes:
        spaceService && spaceService.solarFluxReady
        ? sourceAgeMinutes(spaceService.solarFluxTime) : -1

    readonly property bool spaceStale:
        (kpAgeMinutes >= kpStaleAfterMinutes)
        || (solarWindAgeMinutes >= solarWindStaleAfterMinutes)
        || (magneticFieldAgeMinutes >= magneticFieldStaleAfterMinutes)
        || (solarFluxAgeMinutes >= solarFluxStaleAfterMinutes)

    readonly property string spaceStaleDetail: {
        const parts = [];

        if (kpAgeMinutes >= kpStaleAfterMinutes)
            parts.push("KP " + kpAgeMinutes + "m");
        if (solarWindAgeMinutes >= solarWindStaleAfterMinutes)
            parts.push("WIND " + solarWindAgeMinutes + "m");
        if (magneticFieldAgeMinutes >= magneticFieldStaleAfterMinutes)
            parts.push("IMF " + magneticFieldAgeMinutes + "m");
        if (solarFluxAgeMinutes >= solarFluxStaleAfterMinutes)
            parts.push("F10.7 " + solarFluxAgeMinutes + "m");

        return parts.length > 0
               ? "STALE // " + parts.join(" // ")
               : "";
    }

    // One read-only view over the services already mounted by Weather.
    // It never starts a provider itself. Space freshness uses provider sample
    // age; Weather/AQI use their receive-success clocks.
    readonly property var sourceHealthRows:
        SourceHealth.buildCoreSources({
            "nowMs": relevanceClockMs,
            "weather": {
                "id": "weather",
                "title": "WEATHER",
                "provider": "WTTR.IN",
                "ready": weatherReady,
                "loading": weatherService ? weatherService.loading : false,
                "error": weatherService ? weatherService.errorText : "NO SERVICE",
                "lastSuccessMs":
                    dateMillis(weatherService ? weatherService.lastUpdated : null),
                "sampleAgeMinutes": -1,
                "staleAfterMinutes": 20
            },
            "aqi": {
                "id": "aqi",
                "title": "AIR QUALITY",
                "provider": "OPEN-METEO",
                "ready": aqiReady,
                "loading": weatherService ? weatherService.aqiLoading : false,
                "error": weatherService ? weatherService.aqiErrorText : "NO SERVICE",
                "lastSuccessMs":
                    dateMillis(weatherService ? weatherService.aqiLastUpdated : null),
                "sampleAgeMinutes": -1,
                "staleAfterMinutes": 20
            },
            "kp": {
                "id": "kp",
                "title": "KP INDEX",
                "provider": "NOAA SWPC",
                "ready": spaceService ? spaceService.kpReady : false,
                "loading": spaceService ? spaceService.kpLoading : false,
                "error": spaceService ? spaceService.kpErrorText : "NO SERVICE",
                "lastSuccessMs":
                    dateMillis(spaceService ? spaceService.kpLastUpdated : null),
                "sampleAgeMinutes": kpAgeMinutes,
                "staleAfterMinutes": kpStaleAfterMinutes
            },
            "solarWind": {
                "id": "solar-wind",
                "title": "SOLAR WIND",
                "provider": "NOAA SWPC",
                "ready": spaceService ? spaceService.solarWindReady : false,
                "loading": spaceService ? spaceService.solarWindLoading : false,
                "error": spaceService ? spaceService.solarWindErrorText : "NO SERVICE",
                "lastSuccessMs":
                    dateMillis(spaceService ? spaceService.solarWindLastUpdated : null),
                "sampleAgeMinutes": solarWindAgeMinutes,
                "staleAfterMinutes": solarWindStaleAfterMinutes
            },
            "magneticField": {
                "id": "imf",
                "title": "IMF",
                "provider": "NOAA SWPC",
                "ready": spaceService ? spaceService.magneticFieldReady : false,
                "loading": spaceService ? spaceService.magneticFieldLoading : false,
                "error": spaceService ? spaceService.magneticFieldErrorText : "NO SERVICE",
                "lastSuccessMs":
                    dateMillis(spaceService ? spaceService.magneticFieldLastUpdated : null),
                "sampleAgeMinutes": magneticFieldAgeMinutes,
                "staleAfterMinutes": magneticFieldStaleAfterMinutes
            },
            "solarFlux": {
                "id": "solar-flux",
                "title": "F10.7 FLUX",
                "provider": "NOAA SWPC",
                "ready": spaceService ? spaceService.solarFluxReady : false,
                "loading": spaceService ? spaceService.solarFluxLoading : false,
                "error": spaceService ? spaceService.solarFluxErrorText : "NO SERVICE",
                "lastSuccessMs":
                    dateMillis(spaceService ? spaceService.solarFluxLastUpdated : null),
                "sampleAgeMinutes": solarFluxAgeMinutes,
                "staleAfterMinutes": solarFluxStaleAfterMinutes
            }
        })

    // HOME tracks only session-local deltas between completed provider
    // observations. The services remain the single owners of fetching.
    property bool weatherTrendSeeded: false
    property real previousTemperatureF: 0
    property real previousPressureHpa: 0
    property real previousRainChance: 0
    property real temperatureDelta: 0
    property real pressureDelta: 0
    property real rainChanceDelta: 0

    property bool aqiTrendSeeded: false
    property real previousAqi: 0
    property real aqiDelta: 0

    property bool kpTrendSeeded: false
    property real previousKp: 0
    property real kpDelta: 0

    property bool solarWindTrendSeeded: false
    property real previousSolarWind: 0
    property real solarWindDelta: 0

    property bool bzTrendSeeded: false
    property real previousBz: 0
    property real bzDelta: 0

    property var watchItems: []
    property var activeWatchIds: []

    function finiteNumber(value, fallback) {
        const number = Number(value);
        return isFinite(number) ? number : fallback;
    }

    function historyTemp(value) {
        const number = Number(value);
        return isFinite(number) && number > -900
               ? Math.round(number) + "°F" : "--°F";
    }

    function historyPrecip(value) {
        const number = Number(value);
        return isFinite(number) && number >= 0
               ? number.toFixed(2) + " in" : "-- in";
    }

    function historyDateLabel(value) {
        const text = String(value || "");
        const match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        return match ? match[2] + "/" + match[3] : "--/--";
    }

    function historyDelta(current, past, suffix, digits) {
        const value = HistoryPolicy.signedDelta(current, past, digits);
        return value === "--" ? "--" : value + suffix;
    }

    function clamp01(value) {
        const number = Number(value);
        if (!isFinite(number))
            return 0;
        return Math.max(0, Math.min(1, number));
    }

    function currentNowMinutes() {
        const now = new Date(relevanceClockMs);
        return now.getHours() * 60 + now.getMinutes();
    }

    function buildRelevanceInput() {
        return {
            "weatherReady": weatherReady,
            "weatherStale": weatherStale,
            "weatherAgeMinutes": weatherAgeMinutes,
            "weatherError":
                weatherService ? weatherService.errorText : "",
            "aqiReady": aqiReady,
            "aqiError":
                weatherService ? weatherService.aqiErrorText : "",
            "spaceReady": spaceReady,
            "spacePartial": spacePartial,
            "spaceStale": spaceStale,
            "spaceStaleDetail": spaceStaleDetail,
            "spaceError": spaceService ? spaceService.errorText : "",

            "temperatureF":
                weatherService ? weatherService.tempF : -999,
            "humidity":
                weatherService ? weatherService.humidity : -1,
            "windMph":
                weatherService ? weatherService.windMph : -1,
            "windDirection":
                weatherService ? weatherService.windDirection : "",
            "condition":
                weatherService ? weatherService.condition : "",
            "pressureHpa":
                weatherService ? weatherService.pressureHpa : -1,
            "visibilityMiles":
                weatherService ? weatherService.visibilityMiles : -1,
            "cloudCover":
                weatherService ? weatherService.cloudCover : -1,
            "uvIndex":
                weatherService ? weatherService.uvIndex : -1,

            "aqi": weatherService ? weatherService.aqi : -1,
            "aqiLabel":
                weatherService ? weatherService.aqiLabel : "",
            "pm25":
                weatherService ? weatherService.pm25 : -1,

            "hourlyForecast":
                weatherService ? weatherService.hourlyForecast : [],
            "dailyForecast":
                weatherService ? weatherService.dailyForecast : [],

            "kp": spaceService ? spaceService.kp : -1,
            "kpLabel":
                spaceService ? spaceService.kpLabel : "",
            "solarWindSpeed":
                spaceService ? spaceService.solarWindSpeed : -1,
            "bz":
                spaceService && spaceService.magneticFieldReady
                ? spaceService.magneticFieldBz : 999,
            "bt":
                spaceService && spaceService.magneticFieldReady
                ? spaceService.magneticFieldBt : -1,
            "solarFlux":
                spaceService && spaceService.solarFluxReady
                ? spaceService.solarFlux : -1,

            "temperatureDelta":
                weatherTrendSeeded ? temperatureDelta : 0,
            "pressureDelta":
                weatherTrendSeeded ? pressureDelta : 0,
            "rainChanceDelta":
                weatherTrendSeeded ? rainChanceDelta : 0,
            "aqiDelta":
                aqiTrendSeeded ? aqiDelta : 0,
            "kpDelta":
                kpTrendSeeded ? kpDelta : 0,
            "solarWindDelta":
                solarWindTrendSeeded ? solarWindDelta : 0,
            "bzDelta":
                bzTrendSeeded ? bzDelta : 0,

            "nowMinutes": currentNowMinutes()
        };
    }

    function refreshWatch() {
        const next = StationHomePolicy.rankRelevant(
            buildRelevanceInput(),
            activeWatchIds,
            3
        );

        watchItems = next;

        const ids = [];
        for (let i = 0; i < next.length; i++) {
            if (Number(next[i].rank) > 0)
                ids.push(String(next[i].id || ""));
        }
        activeWatchIds = ids;
    }

    function captureWeatherSnapshot() {
        if (!weatherReady) {
            weatherTrendSeeded = false;
            refreshWatch();
            return;
        }

        const temp = finiteNumber(weatherService.tempF, -999);
        const pressure = finiteNumber(weatherService.pressureHpa, -1);
        const rain = nextForecast
                     ? finiteNumber(nextForecast.chanceRain, -1)
                     : -1;

        if (weatherTrendSeeded) {
            temperatureDelta =
                temp > -900 && previousTemperatureF > -900
                ? temp - previousTemperatureF : 0;
            pressureDelta =
                pressure >= 0 && previousPressureHpa >= 0
                ? pressure - previousPressureHpa : 0;
            rainChanceDelta =
                rain >= 0 && previousRainChance >= 0
                ? rain - previousRainChance : 0;
        }

        previousTemperatureF = temp;
        previousPressureHpa = pressure;
        previousRainChance = rain;
        weatherTrendSeeded = true;
        refreshWatch();
    }

    function captureAqiSnapshot() {
        if (!aqiReady) {
            aqiTrendSeeded = false;
            refreshWatch();
            return;
        }

        const current = finiteNumber(weatherService.aqi, -1);
        if (aqiTrendSeeded && current >= 0 && previousAqi >= 0)
            aqiDelta = current - previousAqi;

        previousAqi = current;
        aqiTrendSeeded = true;
        refreshWatch();
    }

    function captureKpSnapshot() {
        if (!spaceService || !spaceService.kpReady) {
            kpTrendSeeded = false;
            refreshWatch();
            return;
        }

        const current = finiteNumber(spaceService.kp, -1);
        if (kpTrendSeeded && current >= 0 && previousKp >= 0)
            kpDelta = current - previousKp;

        previousKp = current;
        kpTrendSeeded = true;
        refreshWatch();
    }

    function captureSolarWindSnapshot() {
        if (!spaceService || !spaceService.solarWindReady) {
            solarWindTrendSeeded = false;
            refreshWatch();
            return;
        }

        const current = finiteNumber(
            spaceService.solarWindSpeed,
            -1
        );
        if (solarWindTrendSeeded
                && current >= 0
                && previousSolarWind >= 0) {
            solarWindDelta = current - previousSolarWind;
        }

        previousSolarWind = current;
        solarWindTrendSeeded = true;
        refreshWatch();
    }

    function captureBzSnapshot() {
        if (!spaceService || !spaceService.magneticFieldReady) {
            bzTrendSeeded = false;
            refreshWatch();
            return;
        }

        const current = finiteNumber(
            spaceService.magneticFieldBz,
            999
        );
        if (bzTrendSeeded && current < 900 && previousBz < 900)
            bzDelta = current - previousBz;

        previousBz = current;
        bzTrendSeeded = true;
        refreshWatch();
    }

    function uvLabel(value) {
        const number = Number(value);
        if (!isFinite(number) || number < 0)
            return "UNKNOWN";
        if (number >= 8)
            return "VERY HIGH";
        if (number >= 6)
            return "HIGH";
        if (number >= 3)
            return "MODERATE";
        return "LOW";
    }

    function sourceAccent(source) {
        const key = String(source || "");
        if (key === "ground")
            return Colors.green;
        if (key === "space")
            return Colors.magenta;
        if (key === "sky")
            return Colors.cyan;
        return Colors.orange;
    }

    function sourceMeterFill(source) {
        const key = String(source || "");
        if (key === "ground")
            return Colors.green;
        if (key === "space")
            return Colors.magenta;
        return Colors.orange;
    }

    function healthAccent(token) {
        switch (String(token || "")) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "magenta": return Colors.magenta;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }

    function officialAlertColor(token) {
        switch (String(token || "")) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }

    Timer {
        interval: 60000
        repeat: true
        running: true

        onTriggered: {
            home.relevanceClockMs = Date.now();
            home.refreshWatch();
        }
    }

    Connections {
        target: home.weatherService

        function onReadyChanged() {
            if (home.weatherReady)
                home.captureWeatherSnapshot();
            else {
                home.weatherTrendSeeded = false;
                home.refreshWatch();
            }
        }

        function onLastUpdatedChanged() {
            home.captureWeatherSnapshot();
        }

        function onAqiReadyChanged() {
            if (home.aqiReady)
                home.captureAqiSnapshot();
            else {
                home.aqiTrendSeeded = false;
                home.refreshWatch();
            }
        }

        function onAqiLastUpdatedChanged() {
            home.captureAqiSnapshot();
        }

        function onErrorTextChanged() {
            home.refreshWatch();
        }

        function onAqiErrorTextChanged() {
            home.refreshWatch();
        }
    }

    Connections {
        target: home.spaceService

        function onKpTimeChanged() {
            home.captureKpSnapshot();
        }

        function onSolarWindTimeChanged() {
            home.captureSolarWindSnapshot();
        }

        function onMagneticFieldTimeChanged() {
            home.captureBzSnapshot();
        }

        function onReadyChanged() {
            home.refreshWatch();
        }

        function onErrorTextChanged() {
            home.refreshWatch();
        }
    }

    Component.onCompleted: {
        relevanceClockMs = Date.now();

        if (weatherReady)
            captureWeatherSnapshot();
        if (aqiReady)
            captureAqiSnapshot();
        if (spaceService && spaceService.kpReady)
            captureKpSnapshot();
        if (spaceService && spaceService.solarWindReady)
            captureSolarWindSnapshot();
        if (spaceService && spaceService.magneticFieldReady)
            captureBzSnapshot();

        refreshWatch();
    }

    color: Colors.black

    Flickable {
        id: homeScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(
            height,
            homeContent.y + homeContent.implicitHeight + 24
        )

        Column {
            id: homeContent
            x: 24
            y: 24
            width: Math.max(0, homeScroll.width - 48)
            spacing: 14

        Row {
            width: parent.width
            height: 28

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: "⌂  HOME"
                font.pixelSize: 24
                color: Colors.magenta
            }

            Item {
                width: parent.width - 255
                height: 1
            }

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: "AUTO SNAPSHOT"
                font.pixelSize: 12
                color: Colors.orange
            }
        }

        Column {
            width: parent.width
            spacing: 8
            visible: home.officialAlertSummary.available

            StationSectionDivider {
                width: parent.width
                title: "OFFICIAL ALERT // NWS"
            }

            Rectangle {
                width: parent.width
                height: 108
                color: Colors.dark
                border.width: 1
                border.color:
                    home.officialAlertColor(
                        home.officialAlertSummary.colorToken
                    )

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 5
                    color:
                        home.officialAlertColor(
                            home.officialAlertSummary.colorToken
                        )
                }

                Column {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 10
                    anchors.topMargin: 9
                    anchors.bottomMargin: 8
                    spacing: 4

                    Row {
                        width: parent.width
                        spacing: 10

                        GohuText {
                            width: Math.max(0, parent.width - 300)
                            text: home.officialAlertSummary.event
                            elide: Text.ElideRight
                            font.pixelSize: 15
                            color:
                                home.officialAlertColor(
                                    home.officialAlertSummary.colorToken
                                )
                        }

                        GohuText {
                            width: 290
                            horizontalAlignment: Text.AlignRight
                            text:
                                home.officialAlertSummary.listingState
                                + " // "
                                + home.officialAlertSummary.severity
                                + " // "
                                + home.officialAlertSummary.urgency
                            elide: Text.ElideRight
                            font.pixelSize: 10
                            color:
                                home.officialAlertColor(
                                    home.officialAlertSummary.colorToken
                                )
                        }
                    }

                    GohuText {
                        width: parent.width
                        text: home.officialAlertSummary.headline
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    QuietText {
                        width: parent.width
                        text: "AREA // " + home.officialAlertSummary.area
                              + " // CERTAINTY "
                              + home.officialAlertSummary.certainty
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }

                    QuietText {
                        width: parent.width
                        text: "EXPIRES "
                              + home.officialAlertSummary.expiresLabel
                              + " // ISSUER // "
                              + home.officialAlertSummary.issuer
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SNAPSHOT // NOW"
        }

        Row {
            width: parent.width
            height: 118
            spacing: 12

            StationHomeMetricCard {
                width: (parent.width - 24) / 3
                height: parent.height

                title: "CURRENT WEATHER"
                valueText:
                    home.weatherReady
                    ? weatherService.tempF + "°F" : "--°F"
                detailText:
                    home.weatherReady
                    ? String(
                        weatherService.condition || "UNKNOWN"
                      ).toUpperCase()
                    : "WEATHER OFFLINE"
                footerText:
                    home.weatherReady
                    ? "FEELS " + weatherService.feelsLikeF + "°F"
                    : "WAITING FOR SOURCE"
                accentColor: Colors.cyan
                valueColor: Colors.orange
                meterVisible: home.weatherReady
                meterValue:
                    home.clamp01(home.temperatureValue / 120)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 24) / 3
                height: parent.height

                title: "NEXT HOURS"
                valueText:
                    home.nextForecast
                    && Number(home.nextForecast.tempF) > -900
                    ? Math.round(
                        Number(home.nextForecast.tempF)
                      ) + "°F"
                    : "--°F"
                detailText:
                    home.nextForecast
                    ? String(
                        home.nextForecast.timeLabel || "--"
                      )
                      + " // "
                      + String(
                          home.nextForecast.condition || "FORECAST"
                        ).toUpperCase()
                    : "FORECAST UNAVAILABLE"
                footerText:
                    home.nextForecast
                    ? "RAIN "
                      + Math.round(home.nextRainChance)
                      + "%"
                    : "RAIN --"
                accentColor: Colors.cyan
                valueColor: Colors.orange
                meterVisible: home.nextForecast !== null
                meterValue:
                    home.clamp01(home.nextRainChance / 100)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 24) / 3
                height: parent.height

                title: "AIR QUALITY"
                valueText:
                    home.aqiReady
                    ? "AQI " + weatherService.aqi
                    : "AQI --"
                detailText:
                    home.aqiReady
                    ? String(
                        weatherService.aqiLabel || "UNKNOWN"
                      ).toUpperCase()
                    : "AIR QUALITY OFFLINE"
                footerText:
                    home.aqiReady
                    && Number(weatherService.pm25) >= 0
                    ? "PM2.5 "
                      + Number(weatherService.pm25).toFixed(1)
                      + " µg/m³"
                    : "PM2.5 --"
                accentColor: Colors.green
                valueColor: Colors.white
                meterVisible: home.aqiReady
                meterValue:
                    home.clamp01(home.aqiValue / 500)
                meterFillColor: Colors.green
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "RECENT HISTORY // ARCHIVED MODEL"
        }

        Column {
            width: parent.width
            spacing: 9

            Row {
                width: parent.width
                spacing: 12

                SecondaryText {
                    text: "OPEN-METEO // HISTORICAL FORECAST"
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                GohuText {
                    text: !home.historyService
                          ? "NO SERVICE"
                          : home.historyService.loading
                            ? "RECEIVING"
                            : home.historyService.failed
                              ? (home.historyReady ? "DEGRADED" : "OFFLINE")
                              : home.historyReady
                                ? "7 COMPLETED DAYS"
                                : "WAITING"
                    font.pixelSize: 10
                    color: home.historyReady ? Colors.cyan
                           : home.historyService
                             && home.historyService.failed
                             ? Colors.yellow : Colors.orange
                }

                QuietText {
                    width: Math.max(0, parent.width - 430)
                    text: home.historyReady
                          ? "ARCHIVED MODEL // "
                            + (home.historyService.timezoneAbbreviation || "LOCAL")
                            + " // NOT STATION OBSERVATIONS"
                          : "RECENT MODEL HISTORY // NO LOCAL DATABASE"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Row {
                width: parent.width
                height: 104
                spacing: 12

                StationHomeMetricCard {
                    width: (parent.width - 24) / 3
                    height: parent.height
                    title: "YESTERDAY // SAME HOUR"
                    valueText: home.historySameHour
                               ? home.historyTemp(home.historySameHour.tempF)
                               : "--°F"
                    detailText: home.historySameHour && home.weatherReady
                                ? "NOW "
                                  + home.historyTemp(home.temperatureValue)
                                  + " // Δ "
                                  + home.historyDelta(
                                      home.temperatureValue,
                                      home.historySameHour.tempF,
                                      "°F", 0
                                    )
                                : "SAME-HOUR ARCHIVE UNAVAILABLE"
                    footerText: home.historySameHour
                                ? "HUM "
                                  + Math.round(home.historySameHour.humidity)
                                  + "% // WIND "
                                  + Math.round(home.historySameHour.windMph)
                                  + " MPH"
                                : "OPEN-METEO ARCHIVED MODEL"
                    accentColor: Colors.cyan
                    valueColor: Colors.white
                    meterVisible: false
                }

                StationHomeMetricCard {
                    width: (parent.width - 24) / 3
                    height: parent.height
                    title: "7-DAY TEMP RANGE"
                    valueText: home.historyReady
                               ? home.historyTemp(home.historySummary.maxHighF)
                                 + " / "
                                 + home.historyTemp(home.historySummary.minLowF)
                               : "--°F / --°F"
                    detailText: home.historyReady
                                ? "AVG HIGH "
                                  + home.historyTemp(home.historySummary.avgHighF)
                                  + " // AVG LOW "
                                  + home.historyTemp(home.historySummary.avgLowF)
                                : "HISTORY UNAVAILABLE"
                    footerText: "MAX HIGH / MIN LOW"
                    accentColor: Colors.orange
                    valueColor: Colors.white
                    meterVisible: false
                }

                StationHomeMetricCard {
                    width: (parent.width - 24) / 3
                    height: parent.height
                    title: "PRECIP // 7 DAYS"
                    valueText: home.historyReady
                               ? home.historyPrecip(
                                   home.historySummary.precipitationIn
                                 )
                               : "-- in"
                    detailText: home.historyReady
                                ? "WET DAYS "
                                  + home.historySummary.wetDays
                                  + " // MAX "
                                  + home.historyPrecip(
                                      home.historySummary.maxPrecipIn
                                    )
                                : "HISTORY UNAVAILABLE"
                    footerText: home.historyReady
                                && home.historySummary.maxPrecipDate
                                ? "WETTEST "
                                  + home.historyDateLabel(
                                      home.historySummary.maxPrecipDate
                                    )
                                : "COMPLETED LOCAL DAYS"
                    accentColor: Colors.cyan
                    valueColor: Colors.white
                    meterVisible: false
                }
            }

            Row {
                id: historyDailyRow
                width: parent.width
                height: 66
                spacing: 6

                Repeater {
                    model: home.historyDaily

                    delegate: Rectangle {
                        required property var modelData
                        width: (historyDailyRow.width
                                - historyDailyRow.spacing
                                  * Math.max(0, home.historyDaily.length - 1))
                               / Math.max(1, home.historyDaily.length)
                        height: parent.height
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 3

                            SecondaryText {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: home.historyDateLabel(modelData.date)
                                font.pixelSize: 9
                            }

                            GohuText {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: home.historyTemp(modelData.maxTempF)
                                      + " / "
                                      + home.historyTemp(modelData.minTempF)
                                font.pixelSize: 10
                                color: Colors.white
                            }

                            QuietText {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: "P "
                                      + home.historyPrecip(
                                          modelData.precipitationIn
                                        )
                                font.pixelSize: 8
                            }
                        }
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "QUICK // CONDITIONS"
        }

        Row {
            width: parent.width
            height: 106
            spacing: 12

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "HUMIDITY"
                valueText:
                    home.weatherReady
                    ? weatherService.humidity + "%"
                    : "--%"
                detailText: "SKY"
                accentColor: Colors.cyan
                meterVisible: home.weatherReady
                meterValue:
                    home.clamp01(home.humidityValue / 100)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "WIND"
                valueText:
                    home.weatherReady
                    ? weatherService.windMph + " MPH"
                    : "-- MPH"
                detailText:
                    home.weatherReady
                    ? String(
                        weatherService.windDirection || "--"
                      )
                    : "SKY"
                accentColor: Colors.cyan
                meterVisible: home.weatherReady
                meterValue:
                    home.clamp01(home.windValue / 50)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "UV INDEX"
                valueText:
                    home.uvValue >= 0
                    ? String(Math.round(home.uvValue))
                    : "--"
                detailText: home.uvLabel(home.uvValue)
                accentColor: Colors.cyan
                meterVisible: home.uvValue >= 0
                meterValue:
                    home.clamp01(home.uvValue / 11)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "SPACE WEATHER"
                valueText:
                    spaceService && spaceService.kpReady
                    ? "KP " + spaceService.kpText
                    : "KP --"
                detailText:
                    spaceService && spaceService.kpReady
                    ? spaceService.kpLabel
                    : "SPACE FEED PARTIAL"
                accentColor: Colors.magenta
                meterVisible:
                    spaceService && spaceService.kpReady
                meterValue:
                    home.clamp01(home.kpValue / 9)
                meterFillColor: Colors.magenta
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "CORE SOURCE HEALTH // LAST SUCCESS + FRESHNESS"
        }

        Grid {
            id: sourceHealthGrid
            width: parent.width
            columns: 3
            columnSpacing: 12
            rowSpacing: 12

            Repeater {
                model: home.sourceHealthRows

                delegate: StationHomeMetricCard {
                    required property var modelData

                    width: (sourceHealthGrid.width - 24) / 3
                    height: 92
                    title: modelData.title
                    valueText: modelData.state
                    detailText: modelData.detail
                    footerText: modelData.footer
                    accentColor: home.healthAccent(modelData.accent)
                    valueColor: home.healthAccent(modelData.accent)
                    meterVisible: false
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "AUTO // RELEVANT"
        }

        Row {
            width: parent.width
            height: 118
            spacing: 12

            Repeater {
                model: home.watchItems

                delegate: StationHomeMetricCard {
                    required property var modelData

                    width:
                        (
                            parent.width
                            - parent.spacing
                              * Math.max(
                                  0,
                                  home.watchItems.length - 1
                                )
                        )
                        / Math.max(
                            1,
                            home.watchItems.length
                        )
                    height: parent.height

                    title: modelData.title
                    valueText: modelData.value
                    detailText: modelData.detail
                    footerText:
                        modelData.footer.length > 0
                        ? modelData.footer
                        : "AUTO // "
                          + String(
                              modelData.source
                            ).toUpperCase()
                    accentColor:
                        home.sourceAccent(modelData.source)
                    valueColor:
                        Number(modelData.rank) >= 85
                        ? Colors.red
                        : Number(modelData.rank) >= 65
                          ? Colors.orange
                          : Number(modelData.rank) >= 45
                            ? Colors.yellow
                            : Colors.white
                    meterVisible: modelData.meterVisible
                    meterValue: modelData.meterValue
                    meterFillColor:
                        home.sourceMeterFill(modelData.source)
                }
            }
        }
        }
    }

    NeonScrollBar {
        flickable: homeScroll
        handleStyle: "star"
        geometryHost: home
        visible: scrollable
    }
}
