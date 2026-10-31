import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "../../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy
import "StationSkyHourlyPolicy.js" as HourlyDetails
import "StationSkyTwilightPolicy.js" as TwilightPolicy

Rectangle {
    id: sky

    property var weatherService: null

    readonly property bool weatherReady: weatherService && weatherService.ready
    readonly property bool weatherLoading: weatherService && weatherService.loading
    readonly property bool aqiReady: weatherService && weatherService.aqiReady

    readonly property real temperatureValue:
        weatherReady ? Number(weatherService.tempF) : 0
    readonly property real humidityValue:
        weatherReady ? Number(weatherService.humidity) : 0
    readonly property real windValue:
        weatherReady ? Number(weatherService.windMph) : 0
    readonly property real aqiValue:
        aqiReady ? Number(weatherService.aqi) : 0

    readonly property real pressureValue:
        weatherReady ? Number(weatherService.pressureHpa) : -1
    readonly property real visibilityValue:
        weatherReady ? Number(weatherService.visibilityMiles) : -1
    readonly property real cloudCoverValue:
        weatherReady ? Number(weatherService.cloudCover) : -1
    readonly property real precipValue:
        weatherReady ? Number(weatherService.precipMm) : -1
    readonly property real uvValue:
        weatherReady ? Number(weatherService.uvIndex) : -1

    readonly property var hourlyForecast:
        weatherService ? weatherService.hourlyForecast : []
    // Selection only affects the UI. The same six parsed forecast samples
    // back both the icons and the detail readout; no second collector.
    // Default to the familiar icon forecast. The detail view appears
    // only after a deliberate hour selection and can be dismissed.
    property int inspectedHourIndex: -1
    onHourlyForecastChanged: inspectedHourIndex = -1
    readonly property var inspectedHour: inspectedHourIndex >= 0
        ? HourlyDetails.selectedHour(hourlyForecast, inspectedHourIndex) : null
    readonly property var inspectedHourMetrics:
        HourlyDetails.hourlyMetrics(inspectedHour)
    readonly property var dailyForecast:
        weatherService ? weatherService.dailyForecast : []
    property real cycleClockMs: Date.now()
    Timer {
        interval: 60000
        running: true
        repeat: true
        onTriggered: sky.cycleClockMs = Date.now()
    }
    readonly property var skyCycle: WeatherCyclePolicy.atObservation(
        cycleClockMs,
        weatherService ? weatherService.localObservationDateTime : "",
        weatherService ? weatherService.localObservationAnchorMs : 0,
        dailyForecast
    )
    readonly property var astronomySummary:
        WeatherCyclePolicy.astronomySummary(skyCycle.date, dailyForecast)
    readonly property var twilightSummary:
        TwilightPolicy.summary(
            astronomySummary.date,
            weatherService ? weatherService.latitude : "",
            weatherService ? weatherService.longitude : "",
            astronomySummary.sunrise
        )
    readonly property int providerLocalMinute:
        TwilightPolicy.providerObservationMinute(
            cycleClockMs,
            weatherService ? weatherService.localObservationDateTime : "",
            weatherService ? weatherService.localObservationAnchorMs : 0
        )
    readonly property var currentSolarPosition:
        TwilightPolicy.solarPosition(
            skyCycle.date,
            providerLocalMinute,
            weatherService ? weatherService.latitude : "",
            weatherService ? weatherService.longitude : "",
            twilightSummary.calibrationOffsetMinutes
        )
    readonly property bool openMeteoCivilOffsetAvailable: {
        if (!weatherService
                || weatherService.airQualityUtcOffsetMinutes === undefined
                || weatherService.airQualityUtcOffsetMinutes === null)
            return false;
        const value = Number(weatherService.airQualityUtcOffsetMinutes);
        return isFinite(value) && value >= -720 && value <= 840;
    }
    readonly property var moonCivilOffsetMinutes:
        openMeteoCivilOffsetAvailable
        ? Number(weatherService.airQualityUtcOffsetMinutes)
        : twilightSummary.calibrationOffsetMinutes
    readonly property string moonCivilOffsetSource:
        openMeteoCivilOffsetAvailable
        ? "OPEN-METEO TIMEZONE"
        : "SUNRISE CALIBRATION"
    WeatherServices.UsnoMoonService {
        id: moonService
        active: sky.visible
        // Use the same provider forecast date shown by ASTRONOMY.
        // skyCycle.date intentionally clears when the observation anchor is
        // stale, while astronomySummary safely falls back to dailyForecast[0].
        date: sky.astronomySummary.date
        latitude: sky.weatherService ? sky.weatherService.latitude : ""
        longitude: sky.weatherService ? sky.weatherService.longitude : ""
        offsetMinutes: sky.moonCivilOffsetMinutes
    }

    WeatherServices.UsnoCelnavService {
        id: celnavService
        active: sky.visible
        latitude: sky.weatherService ? sky.weatherService.latitude : ""
        longitude: sky.weatherService ? sky.weatherService.longitude : ""
    }

    WeatherServices.UsnoPlanetRiseSetService {
        id: planetRiseSetService
        active: sky.visible
        date: sky.astronomySummary.date
        latitude: sky.weatherService ? sky.weatherService.latitude : ""
        longitude: sky.weatherService ? sky.weatherService.longitude : ""
        offsetMinutes: sky.moonCivilOffsetMinutes
    }

    readonly property string currentCelestialMode:
        weatherReady
        ? WeatherCyclePolicy.artworkFor(conditionState, skyCycle) : "weather"

    function numericText(value, digits, suffix) {
        return isFinite(value) && value >= 0
               ? Number(value).toFixed(digits) + suffix
               : "--";
    }

    function utcOffsetLabel(value) {
        const text = String(value === undefined || value === null ? "" : value);
        if (text === "")
            return "UTC --";
        const number = Number(text);
        return "UTC" + (isFinite(number) && number >= 0 ? "+" : "") + text;
    }

    function skyAngleText(value) {
        const number = Number(value);
        return isFinite(number) ? number.toFixed(1) + "°" : "--";
    }

    function moonInputIssue() {
        const request = moonService.request || {};
        const missing = [];
        if (!request.dateValid)
            missing.push("DATE");
        if (!request.coordinatesValid)
            missing.push("COORDINATES");
        if (!request.offsetValid)
            missing.push("CIVIL OFFSET");
        return missing.length > 0
            ? "INVALID/MISSING " + missing.join(" + ")
            : "INPUTS WAITING";
    }

    function planetStatusColor(status) {
        switch (String(status || "")) {
        case "NORMAL": return Colors.cyan;
        case "CONTINUOUSLY ABOVE HORIZON": return Colors.green;
        case "CONTINUOUSLY BELOW HORIZON": return Colors.blue;
        case "INDETERMINATE": return Colors.yellow;
        default: return Colors.orange;
        }
    }

    function planetAngleLabel(value, suffix) {
        const number = Number(value);
        return isFinite(number)
            ? Math.round(number) + String(suffix || "°")
            : "--";
    }

    // Normalized live telemetry scales preserved from the original page.
    readonly property real temperatureMeter:
        Math.max(0, Math.min(1, temperatureValue / 120))
    readonly property real aqiMeter:
        Math.max(0, Math.min(1, aqiValue / 500))
    readonly property real humidityMeter:
        Math.max(0, Math.min(1, humidityValue / 100))
    readonly property real windMeter:
        Math.max(0, Math.min(1, windValue / 50))
    readonly property real cloudCoverMeter:
        Math.max(0, Math.min(1, cloudCoverValue / 100))
    // UV 11+ is the standard "extreme" top category, so cap the compact
    // instrument there instead of inventing a weather-specific ceiling.
    readonly property real uvMeter:
        Math.max(0, Math.min(1, uvValue / 11))

    function chanceMeter(value) {
        const number = Number(value);
        if (!isFinite(number) || number < 0)
            return 0;
        return Math.max(0, Math.min(1, number / 100));
    }

    readonly property string conditionText:
        weatherReady && weatherService.condition
        ? weatherService.condition.toUpperCase()
        : weatherLoading ? "RECEIVING..." : "DATA OFFLINE"
    // SKY shares the dock's condition glyphs and semantic colors.
    function iconState(condition, weatherCode, current) {
        const now = sky.cycleClockMs;
        return WeatherDockPolicy.classify({
            ready: true, errorText: "", weatherTimeMs: now, nowMs: now,
            weatherCode: weatherCode || "", condition: condition || "",
            windMph: current && weatherReady ? weatherService.windMph : 0,
            uvIndex: current && weatherReady ? weatherService.uvIndex : -1,
            aqiReady: Boolean(current && aqiReady), aqiErrorText: "",
            aqiTimeMs: now, aqi: current && aqiReady ? weatherService.aqi : -1
        });
    }

    function iconColor(name) {
        switch (name) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "green": return Colors.green;
        case "omnitrix": return Colors.omnitrix;
        case "cyan": return Colors.cyan;
        case "blue": return Colors.blue;
        case "magenta": return Colors.magenta;
        default: return Colors.white;
        }
    }

    readonly property var conditionState: weatherReady
        ? iconState(weatherService.condition, weatherService.weatherCode, true)
        : { icon: "?", color: "white" }

    function windAngle(direction) {
        const directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ];
        const at = directions.indexOf(String(direction || "").toUpperCase());
        return at < 0 ? 0 : at * 22.5;
    }

    readonly property color meterBorderColor: Colors.cyan
    readonly property color meterFillColor: Colors.orange

    color: Colors.black

    // SKY extends beyond the fixed-height station when forecast artwork is
    // enlarged. Measure its real content and scroll rather than clipping rows.
    Flickable {
        id: skyScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, skyContent.y + skyContent.implicitHeight + 12)

        Column {
            id: skyContent
            x: 20
            y: 12
            width: Math.max(0, skyScroll.width - 40)
            spacing: 6

            Row {
            width: parent.width

            GohuText {
                text: "☁  SKY"
                font.pixelSize: 24
                color: Colors.cyan
            }

            Item {
                width: parent.width - 240
                height: 1
            }

            GohuText {
                text: sky.weatherReady
                      ? "WEATHER ONLINE"
                      : sky.weatherLoading
                        ? "RECEIVING"
                        : "OFFLINE"
                font.pixelSize: 12
                color: sky.weatherReady ? Colors.cyan : Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "CURRENT // CONDITIONS"
        }

        Row {
            spacing: 13

            Column {
                width: 135
                spacing: 6

                SecondaryText {
                    text: "TEMPERATURE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.weatherReady
                          ? weatherService.tempF + "°F" : "--°F"
                    font.pixelSize: 30
                    color: Colors.orange
                }

                GohuText {
                    text: sky.weatherReady
                          ? "FEELS " + weatherService.feelsLikeF + "°F"
                          : "FEELS --°F"
                    font.pixelSize: 11
                    color: Colors.white
                }

                Rectangle {
                    width: 115
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: sky.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.temperatureMeter
                        height: parent.height - 4
                        color: sky.meterFillColor
                    }
                }
            }

            // Center the enlarged sun in the fixed-height condition bay.
            // Neither the bay height nor the divider below it moves.
            Column {
                width: 190
                spacing: 2

                SecondaryText {
                    text: "CONDITION"
                    font.pixelSize: 11
                }

                Item {
                    width: parent.width
                    height: 88

                    GohuText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        width: 98
                        text: sky.conditionText
                        font.pixelSize: 14
                        wrapMode: Text.WordWrap
                        color: Colors.orange
                    }

                    Item {
                        width: 110
                        height: parent.height
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.horizontalCenterOffset: -24

                        SafeDropShadow {
                            anchors.fill: conditionIconGlyph
                            safeSource: conditionIconGlyph
                            requestedVisible: sky.currentCelestialMode === "weather"
                            radius: 12
                            samples: 25
                            horizontalOffset: 0
                            verticalOffset: 0
                            transparentBorder: true
                            opacity: 0.95
                            color: sky.iconColor(sky.conditionState.color)
                        }

                        Text {
                            id: conditionIconGlyph
                            anchors.centerIn: parent
                            text: sky.conditionState.icon
                            font.pixelSize: 104
                            color: sky.iconColor(sky.conditionState.color)
                            visible: sky.currentCelestialMode === "weather"
                        }

                        WeatherCelestialGlyph {
                            id: currentCelestialIcon
                            anchors.centerIn: parent
                            width: 86
                            height: 86
                            mode: sky.currentCelestialMode
                            weatherKind: WeatherCyclePolicy.nightKind(sky.conditionState)
                            solar: sky.skyCycle.solar
                            moonPhase: sky.skyCycle.moonPhase
                            ink: sky.iconColor(sky.conditionState.color)
                            visible: sky.currentCelestialMode !== "weather"
                        }

                        SafeDropShadow {
                            anchors.fill: currentCelestialIcon
                            safeSource: currentCelestialIcon
                            requestedVisible: currentCelestialIcon.visible
                                             && sky.skyCycle.solar !== "night"
                            radius: 12
                            samples: 25
                            horizontalOffset: 0
                            verticalOffset: 0
                            transparentBorder: true
                            opacity: 0.95
                            color: sky.iconColor(sky.conditionState.color)
                            z: -1
                        }

                    }
                }
            }

            Column {
                width: 125
                spacing: 6

                SecondaryText {
                    text: "AIR QUALITY"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.aqiReady ? String(weatherService.aqi) : "--"
                    font.pixelSize: 20
                    color: Colors.white
                }

                GohuText {
                    text: sky.aqiReady ? weatherService.aqiLabel : "OFFLINE"
                    font.pixelSize: 10
                    color: Colors.white
                }

                Rectangle {
                    width: 88
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: sky.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.aqiMeter
                        height: parent.height - 4
                        color: sky.meterFillColor
                    }
                }
            }

            Column {
                width: 110
                spacing: 6

                SecondaryText {
                    text: "HUMIDITY"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.weatherReady
                          ? weatherService.humidity + "%" : "--%"
                    font.pixelSize: 20
                    color: Colors.white
                }

                Rectangle {
                    width: 86
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: sky.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.humidityMeter
                        height: parent.height - 4
                        color: sky.meterFillColor
                    }
                }
            }

            Row {
                width: 175
                spacing: 8

                GohuText {
                    text: "↑"
                    font.pixelSize: 28
                    color: Colors.orange
                    rotation: sky.windAngle(
                        sky.weatherReady ? weatherService.windDirection : ""
                    )
                }

                Column {
                    spacing: 6

                    SecondaryText {
                        text: "WIND"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: sky.weatherReady
                              ? weatherService.windDirection
                                + "  " + weatherService.windMph + " MPH"
                              : "--  -- MPH"
                        font.pixelSize: 14
                        color: Colors.white
                    }

                    Rectangle {
                        width: 110
                        height: 8
                        color: Colors.black
                        border.width: 1
                        border.color: sky.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * sky.windMeter
                            height: parent.height - 4
                            color: sky.meterFillColor
                        }
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "ATMOSPHERE // OBSERVATION"
        }

        Row {
            spacing: 18

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "PRESSURE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.numericText(
                        sky.pressureValue, 0, " hPa"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "VISIBILITY"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.numericText(
                        sky.visibilityValue, 1, " mi"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "CLOUD COVER"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.numericText(
                        sky.cloudCoverValue, 0, "%"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 115
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: sky.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.cloudCoverMeter
                        height: parent.height - 4
                        color: sky.meterFillColor
                    }
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "PRECIP"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.numericText(
                        sky.precipValue, 1, " mm"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }
            }

            Column {
                width: 125
                spacing: 5

                SecondaryText {
                    text: "UV INDEX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.numericText(
                        sky.uvValue, 0, ""
                    )
                    font.pixelSize: 16
                    color: sky.uvValue >= 8
                           ? Colors.red
                           : sky.uvValue >= 6
                             ? Colors.orange
                             : sky.uvValue >= 3
                               ? Colors.yellow : Colors.cyan
                }

                Rectangle {
                    width: 105
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: sky.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.uvMeter
                        height: parent.height - 4
                        color: sky.meterFillColor
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "ASTRONOMY // SUN + MOON"
        }

        Row {
            spacing: 12
            visible: sky.astronomySummary.available

            Column {
                width: 118
                spacing: 4

                SecondaryText {
                    text: "DATE"
                    font.pixelSize: 10
                }

                GohuText {
                    text: sky.astronomySummary.date
                    font.pixelSize: 13
                    color: Colors.white
                }
            }

            Column {
                width: 126
                spacing: 4

                SecondaryText {
                    text: "SUNRISE"
                    font.pixelSize: 10
                }

                GohuText {
                    text: sky.astronomySummary.sunrise
                    font.pixelSize: 14
                    color: Colors.white
                }
            }

            Column {
                width: 126
                spacing: 4

                SecondaryText {
                    text: "SUNSET"
                    font.pixelSize: 10
                }

                GohuText {
                    text: sky.astronomySummary.sunset
                    font.pixelSize: 14
                    color: Colors.white
                }
            }

            Column {
                width: 126
                spacing: 4

                SecondaryText {
                    text: "DAYLIGHT"
                    font.pixelSize: 10
                }

                GohuText {
                    text: sky.astronomySummary.daylightLabel
                    font.pixelSize: 14
                    color: Colors.white
                }
            }

            Column {
                width: 238
                spacing: 4

                SecondaryText {
                    text: "MOON"
                    font.pixelSize: 10
                }

                GohuText {
                    text: sky.astronomySummary.moonPhaseLabel
                    font.pixelSize: 12
                    color: Colors.white
                }

                QuietText {
                    text: sky.astronomySummary.moonIllumination >= 0
                          ? "ILLUMINATION "
                            + Math.round(sky.astronomySummary.moonIllumination)
                            + "%"
                          : "ILLUMINATION --"
                    font.pixelSize: 9
                }
            }
        }

        QuietText {
            visible: !sky.astronomySummary.available
            text: "ASTRONOMY DATA UNAVAILABLE IN CURRENT DAILY PROVIDER PAYLOAD"
            font.pixelSize: 9
        }

        QuietText {
            visible: sky.astronomySummary.available
            text: "WTTR.IN DAILY ASTRONOMY // DAYLIGHT DERIVED FROM PROVIDER SUNRISE + SUNSET"
            font.pixelSize: 9
        }

        StationSectionDivider {
            width: parent.width
            title: "MOON // USNO EPHEMERIS"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 12

                GohuText {
                    text: !moonService.configured
                          ? "UNAVAILABLE"
                          : moonService.loading
                            ? "RECEIVING"
                            : moonService.failed
                              ? "OFFLINE"
                              : moonService.ready
                                ? "RECEIVED"
                                : "WAITING"
                    font.pixelSize: 10
                    color: moonService.failed
                           ? Colors.orange
                           : moonService.ready
                             ? Colors.cyan : Colors.white
                }

                QuietText {
                    width: Math.max(0, parent.width - 110)
                    text: moonService.configured
                          ? "U.S. NAVAL OBSERVATORY // "
                            + sky.utcOffsetLabel(
                                  moonService.request.tzHours
                              )
                            + " // " + sky.moonCivilOffsetSource
                            + " // " + moonService.request.date
                          : sky.moonInputIssue()
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Row {
                width: parent.width
                spacing: 12
                visible: moonService.ready

                Column {
                    width: 126
                    spacing: 4
                    SecondaryText {
                        text: "MOONRISE"
                        font.pixelSize: 9
                    }
                    GohuText {
                        text: moonService.ephemeris.rise
                        font.pixelSize: 14
                        color: Colors.cyan
                    }
                }

                Column {
                    width: 126
                    spacing: 4
                    SecondaryText {
                        text: "UPPER TRANSIT"
                        font.pixelSize: 9
                    }
                    GohuText {
                        text: moonService.ephemeris.transit
                        font.pixelSize: 14
                        color: Colors.white
                    }
                }

                Column {
                    width: 126
                    spacing: 4
                    SecondaryText {
                        text: "MOONSET"
                        font.pixelSize: 9
                    }
                    GohuText {
                        text: moonService.ephemeris.set
                        font.pixelSize: 14
                        color: Colors.magenta
                    }
                }

                Column {
                    width: 220
                    spacing: 4
                    SecondaryText {
                        text: "USNO PHASE"
                        font.pixelSize: 9
                    }
                    GohuText {
                        width: parent.width
                        text: moonService.ephemeris.phase
                        elide: Text.ElideRight
                        font.pixelSize: 12
                        color: Colors.white
                    }
                }

                Column {
                    width: 126
                    spacing: 4
                    SecondaryText {
                        text: "ILLUMINATION"
                        font.pixelSize: 9
                    }
                    GohuText {
                        text: moonService.ephemeris.illumination >= 0
                              ? Math.round(
                                    moonService.ephemeris.illumination
                                ) + "%"
                              : "--"
                        font.pixelSize: 14
                        color: Colors.yellow
                    }
                }
            }

            QuietText {
                visible: moonService.ready
                         && moonService.ephemeris.noRiseSet
                width: parent.width
                text: "USNO RETURNED NO MOONRISE OR MOONSET FOR THIS LOCAL DATE // NO EVENT IS INVENTED"
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                visible: moonService.failed
                width: parent.width
                text: moonService.errorText
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                text: "USNO ONE-DAY RISE/SET/TRANSIT // OPEN-METEO RESOLVED CIVIL OFFSET // SUNRISE CALIBRATION FALLBACK // DATE-SCOPED REQUEST"
                font.pixelSize: 9
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SKY NOW // USNO CELESTIAL FIX"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 12

                GohuText {
                    text: !celnavService.configured
                          ? "LOCATION UNAVAILABLE"
                          : celnavService.loading
                            ? "RECEIVING"
                            : celnavService.failed
                              ? (celnavService.ready
                                 ? "DEGRADED" : "OFFLINE")
                              : celnavService.ready
                                ? "RECEIVED"
                                : "WAITING"
                    font.pixelSize: 10
                    color: celnavService.failed
                           ? Colors.yellow
                           : celnavService.ready
                             ? Colors.cyan : Colors.orange
                }

                QuietText {
                    width: Math.max(0, parent.width - 150)
                    text: celnavService.ready
                          ? "U.S. NAVAL OBSERVATORY // "
                            + celnavService.snapshot.date
                            + " " + celnavService.snapshot.time
                            + " UTC"
                          : "USNO CELESTIAL NAVIGATION // CURRENT POSITION"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: celnavService.failed
                width: parent.width
                text: celnavService.errorText
                      + (celnavService.ready
                         ? " // LAST-GOOD SKY FIX RETAINED" : "")
                font.pixelSize: 9
                color: Colors.yellow
            }

            Rectangle {
                visible: celnavService.ready
                width: parent.width
                height: 66
                color: Colors.dark
                border.width: 1
                border.color: celnavService.snapshot.moon
                              ? Colors.magenta : Colors.white

                Row {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 14

                    Column {
                        width: 210
                        spacing: 4

                        SecondaryText {
                            text: "MOON // CURRENT POSITION"
                            font.pixelSize: 9
                        }

                        GohuText {
                            text: celnavService.snapshot.moon
                                  ? "ABOVE USNO DISPLAY LIMIT"
                                  : "NOT IN CURRENT USNO LIST"
                            font.pixelSize: 11
                            color: celnavService.snapshot.moon
                                   ? Colors.magenta : Colors.white
                        }
                    }

                    Column {
                        width: 150
                        spacing: 4

                        SecondaryText {
                            text: "ALTITUDE // HC"
                            font.pixelSize: 9
                        }

                        GohuText {
                            text: celnavService.snapshot.moon
                                  ? sky.skyAngleText(
                                        celnavService.snapshot.moon.altitude
                                    )
                                  : "--"
                            font.pixelSize: 16
                            color: Colors.white
                        }
                    }

                    Column {
                        width: 190
                        spacing: 4

                        SecondaryText {
                            text: "AZIMUTH // ZN"
                            font.pixelSize: 9
                        }

                        GohuText {
                            text: celnavService.snapshot.moon
                                  ? sky.skyAngleText(
                                        celnavService.snapshot.moon.azimuth
                                    )
                                    + " // "
                                    + celnavService.snapshot.moon.direction
                                  : "--"
                            font.pixelSize: 16
                            color: Colors.cyan
                        }
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 590)
                        text: celnavService.snapshot.moon
                              ? "GEOCENTRIC ALTITUDE + COMPUTED AZIMUTH"
                              : "USNO ONLY LISTS MOON WHEN HC > -3°"
                        wrapMode: Text.WordWrap
                        font.pixelSize: 9
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 5
                visible: celnavService.ready

                Row {
                    width: parent.width
                    spacing: 12

                    GohuText {
                        width: 220
                        text: "PLANETS ABOVE HORIZON // "
                              + celnavService.snapshot.planets.length
                        font.pixelSize: 10
                        color: Colors.orange
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 232)
                        text: "USNO CATALOG DISPLAY THRESHOLD // PRACTICAL VISIBILITY NOT GUARANTEED"
                        font.pixelSize: 9
                    }
                }

                Repeater {
                    model: celnavService.snapshot.planets

                    delegate: Row {
                        required property var modelData
                        width: parent.width
                        spacing: 12

                        GohuText {
                            width: 160
                            text: modelData.name
                            font.pixelSize: 11
                            color: Colors.orange
                        }

                        QuietText {
                            width: 170
                            text: "ALT "
                                  + sky.skyAngleText(modelData.altitude)
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: 210
                            text: "AZ "
                                  + sky.skyAngleText(modelData.azimuth)
                                  + " // " + modelData.direction
                            font.pixelSize: 9
                        }
                    }
                }

                QuietText {
                    visible: celnavService.snapshot.planets.length === 0
                    text: "NO NAVIGATIONAL PLANETS RETURNED ABOVE THE USNO DISPLAY THRESHOLD"
                    font.pixelSize: 9
                }
            }

            Column {
                width: parent.width
                spacing: 5
                visible: celnavService.ready

                GohuText {
                    text: "NAVIGATION STARS // CONSTELLATION CONTEXT // "
                          + celnavService.snapshot.stars.length
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                Repeater {
                    model: celnavService.snapshot.stars.slice(0, 6)

                    delegate: Row {
                        required property var modelData
                        width: parent.width
                        spacing: 12

                        GohuText {
                            width: 160
                            text: modelData.name
                            font.pixelSize: 10
                            color: Colors.white
                        }

                        QuietText {
                            width: 190
                            text: modelData.constellation !== ""
                                  ? modelData.constellation
                                  : "CONSTELLATION --"
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: 170
                            text: "ALT "
                                  + sky.skyAngleText(modelData.altitude)
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: 180
                            text: "AZ "
                                  + sky.skyAngleText(modelData.azimuth)
                                  + " // " + modelData.direction
                            font.pixelSize: 9
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 12
                    visible: celnavService.snapshot.constellations
                             && celnavService.snapshot.constellations.length > 0

                    GohuText {
                        width: 240
                        text: "CONSTELLATION ANCHORS // "
                              + celnavService.snapshot.constellations.length
                        font.pixelSize: 10
                        color: Colors.magenta
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 252)
                        text: "GROUPED FROM THE SAME CURRENT USNO NAVIGATION-STAR SNAPSHOT"
                        font.pixelSize: 9
                    }
                }

                Row {
                    id: constellationAnchorRow
                    width: parent.width
                    spacing: 7
                    visible: celnavService.snapshot.constellations
                             && celnavService.snapshot.constellations.length > 0

                    Repeater {
                        model: celnavService.snapshot.constellations
                               ? celnavService.snapshot.constellations.slice(0, 4)
                               : []

                        delegate: Rectangle {
                            required property var modelData
                            width: Math.max(
                                0,
                                (constellationAnchorRow.width
                                 - 3 * constellationAnchorRow.spacing) / 4
                            )
                            height: 98
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta

                            Column {
                                anchors.fill: parent
                                anchors.margins: 7
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text: modelData.name
                                    elide: Text.ElideRight
                                    font.pixelSize: 10
                                    color: Colors.magenta
                                }

                                QuietText {
                                    width: parent.width
                                    text: modelData.count
                                          + (modelData.count === 1
                                             ? " NAV STAR" : " NAV STARS")
                                    font.pixelSize: 8
                                }

                                QuietText {
                                    width: parent.width
                                    text: "ANCHOR // "
                                          + modelData.anchorStar
                                    elide: Text.ElideRight
                                    font.pixelSize: 8
                                    color: Colors.white
                                }

                                QuietText {
                                    width: parent.width
                                    text: "ALT "
                                          + sky.skyAngleText(
                                                modelData.anchorAltitude
                                            )
                                          + " // "
                                          + modelData.anchorDirection
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                }

                                QuietText {
                                    width: parent.width
                                    text: modelData.starNames.join(" / ")
                                    elide: Text.ElideRight
                                    font.pixelSize: 8
                                }
                            }
                        }
                    }
                }

                QuietText {
                    width: parent.width
                    text: "CONSTELLATION ANCHORS GROUP RETURNED NAVIGATION STARS ONLY // NOT FULL IAU CONSTELLATION BOUNDARIES OR ALL VISIBLE STARS"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            QuietText {
                width: parent.width
                text: "ABOVE-HORIZON CATALOG ≠ NAKED-EYE VISIBILITY // DAYLIGHT, SUN GLARE, CLOUDS + TERRAIN ARE NOT MODELED // UTC MINUTE USED FOR USNO UT1 INPUT"
                font.pixelSize: 9
                color: Colors.orange
            }
        }


        StationSectionDivider {
            width: parent.width
            title: "PLANET CLOCK // USNO RISE + TRANSIT + SET"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 12

                GohuText {
                    text: !planetRiseSetService.configured
                          ? "INPUTS UNAVAILABLE"
                          : planetRiseSetService.loading
                            ? "CALCULATING"
                            : planetRiseSetService.failed
                              ? (planetRiseSetService.ready
                                 ? "DEGRADED" : "OFFLINE")
                              : planetRiseSetService.ready
                                ? "RECEIVED" : "WAITING"
                    font.pixelSize: 10
                    color: planetRiseSetService.failed
                           ? Colors.yellow
                           : planetRiseSetService.ready
                             ? Colors.cyan : Colors.orange
                }

                QuietText {
                    width: Math.max(0, parent.width - 150)
                    text: planetRiseSetService.ready
                          ? "LOCAL CIVIL DATE "
                            + sky.astronomySummary.date
                            + " // "
                            + planetRiseSetService.rows.length
                            + " PLANETS // "
                            + planetRiseSetService.precision
                          : "USNO MAJOR SOLAR SYSTEM BODIES // DATE-SCOPED CALCULATOR"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: planetRiseSetService.failed
                width: parent.width
                text: planetRiseSetService.errorText
                font.pixelSize: 9
                color: Colors.yellow
            }

            Row {
                id: planetClockRow
                width: parent.width
                spacing: 7
                visible: planetRiseSetService.ready

                Repeater {
                    model: planetRiseSetService.rows

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(
                            0,
                            (planetClockRow.width
                             - 4 * planetClockRow.spacing) / 5
                        )
                        height: 126
                        color: Colors.dark
                        border.width: 1
                        border.color:
                            sky.planetStatusColor(modelData.status)

                        Column {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 4

                            GohuText {
                                width: parent.width
                                text: modelData.name
                                elide: Text.ElideRight
                                font.pixelSize: 11
                                color:
                                    sky.planetStatusColor(modelData.status)
                            }

                            QuietText {
                                visible: modelData.status === "NORMAL"
                                width: parent.width
                                text: "RISE // "
                                      + modelData.riseLabel
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }

                            QuietText {
                                visible: modelData.status === "NORMAL"
                                width: parent.width
                                text: "AZ // "
                                      + sky.planetAngleLabel(
                                            modelData.riseAzimuth, "°T"
                                        )
                                font.pixelSize: 8
                                color: Colors.cyan
                            }

                            QuietText {
                                visible: modelData.status === "NORMAL"
                                width: parent.width
                                text: "TRANSIT // "
                                      + modelData.transitLabel
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }

                            QuietText {
                                visible: modelData.status === "NORMAL"
                                width: parent.width
                                text: "ALT // "
                                      + sky.planetAngleLabel(
                                            modelData.transitAltitude, "°"
                                        )
                                      + String(
                                            modelData.transitHemisphere || ""
                                        )
                                font.pixelSize: 8
                                color: Colors.orange
                            }

                            QuietText {
                                visible: modelData.status === "NORMAL"
                                width: parent.width
                                text: "SET // "
                                      + modelData.setLabel
                                      + " // "
                                      + sky.planetAngleLabel(
                                            modelData.setAzimuth, "°T"
                                        )
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }

                            GohuText {
                                visible: modelData.status !== "NORMAL"
                                width: parent.width
                                text: modelData.status
                                wrapMode: Text.WordWrap
                                font.pixelSize: 9
                                color:
                                    sky.planetStatusColor(modelData.status)
                            }
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "MERCURY + VENUS + MARS + JUPITER + SATURN // RISE/SET TO ONE-MINUTE PROVIDER PRECISION // AZIMUTH TRUE NORTH"
                font.pixelSize: 9
            }

            QuietText {
                width: parent.width
                text: "USNO MODELS ATMOSPHERIC REFRACTION WITH A FLAT UNOBSTRUCTED HORIZON // TERRAIN, BUILDINGS, CLOUDS + DAYLIGHT ARE NOT VISIBILITY CLAIMS"
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                text: "CURRENT POSITION ABOVE USES CELNAV // THIS TABLE IS THE LOCAL-DATE EVENT CLOCK // BOTH USE THE SAME WEATHER COORDINATE FIX"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "TWILIGHT // SOLAR WINDOWS"
        }

        Column {
            width: parent.width
            spacing: 7
            visible: sky.twilightSummary.available

            Row {
                width: parent.width
                spacing: 12

                SecondaryText {
                    width: 92
                    text: "MORNING"
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                Column {
                    width: 136
                    spacing: 3
                    SecondaryText { text: "ASTRONOMICAL"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.astronomicalDawn
                        font.pixelSize: 13
                        color: Colors.white
                    }
                }

                Column {
                    width: 126
                    spacing: 3
                    SecondaryText { text: "NAUTICAL"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.nauticalDawn
                        font.pixelSize: 13
                        color: Colors.white
                    }
                }

                Column {
                    width: 116
                    spacing: 3
                    SecondaryText { text: "CIVIL"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.civilDawn
                        font.pixelSize: 13
                        color: Colors.white
                    }
                }

                Column {
                    width: 122
                    spacing: 3
                    SecondaryText { text: "SUNRISE"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.astronomySummary.sunrise
                        font.pixelSize: 13
                        color: Colors.orange
                    }
                }

                Column {
                    width: 126
                    spacing: 3
                    SecondaryText { text: "SOLAR NOON"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.solarNoon
                        font.pixelSize: 13
                        color: Colors.yellow
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 12

                SecondaryText {
                    width: 92
                    text: "EVENING"
                    font.pixelSize: 10
                    color: Colors.magenta
                }

                Column {
                    width: 136
                    spacing: 3
                    SecondaryText { text: "SUNSET"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.astronomySummary.sunset
                        font.pixelSize: 13
                        color: Colors.orange
                    }
                }

                Column {
                    width: 126
                    spacing: 3
                    SecondaryText { text: "CIVIL"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.civilDusk
                        font.pixelSize: 13
                        color: Colors.white
                    }
                }

                Column {
                    width: 116
                    spacing: 3
                    SecondaryText { text: "NAUTICAL"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.nauticalDusk
                        font.pixelSize: 13
                        color: Colors.white
                    }
                }

                Column {
                    width: 176
                    spacing: 3
                    SecondaryText { text: "ASTRONOMICAL"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.astronomicalDusk
                        font.pixelSize: 13
                        color: Colors.white
                    }
                }
            }

            StationSectionDivider {
                width: parent.width
                title: "PHOTO LIGHT // STATION CONVENTION"
            }

            Row {
                width: parent.width
                spacing: 12

                SecondaryText {
                    width: 92
                    text: "MORNING"
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                Column {
                    width: 220
                    spacing: 3
                    SecondaryText { text: "BLUE // -6° → -4°"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.blueMorningStart
                              + " → "
                              + sky.twilightSummary.blueMorningEnd
                        font.pixelSize: 12
                        color: Colors.blue
                    }
                }

                Column {
                    width: 250
                    spacing: 3
                    SecondaryText { text: "GOLDEN // -4° → +6°"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.goldenMorningStart
                              + " → "
                              + sky.twilightSummary.goldenMorningEnd
                        font.pixelSize: 12
                        color: Colors.orange
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 12

                SecondaryText {
                    width: 92
                    text: "EVENING"
                    font.pixelSize: 10
                    color: Colors.magenta
                }

                Column {
                    width: 220
                    spacing: 3
                    SecondaryText { text: "GOLDEN // +6° → -4°"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.goldenEveningStart
                              + " → "
                              + sky.twilightSummary.goldenEveningEnd
                        font.pixelSize: 12
                        color: Colors.orange
                    }
                }

                Column {
                    width: 250
                    spacing: 3
                    SecondaryText { text: "BLUE // -4° → -6°"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.twilightSummary.blueEveningStart
                              + " → "
                              + sky.twilightSummary.blueEveningEnd
                        font.pixelSize: 12
                        color: Colors.blue
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "POST-APOLLO PHOTO CONVENTION // SOLAR CENTER ALTITUDE // BLUE -6°..-4° // GOLDEN -4°..+6° // CALCULATED, NOT OBSERVED"
                font.pixelSize: 9
                color: Colors.orange
            }

            Row {
                width: parent.width
                spacing: 12
                visible: sky.currentSolarPosition.available

                SecondaryText {
                    width: 92
                    text: "SUN NOW"
                    font.pixelSize: 10
                    color: Colors.yellow
                }

                Column {
                    width: 150
                    spacing: 3
                    SecondaryText { text: "ALTITUDE"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.currentSolarPosition.available
                              ? sky.currentSolarPosition.altitudeDegrees.toFixed(1)
                                + "°"
                              : "--"
                        font.pixelSize: 14
                        color: Colors.white
                    }
                }

                Column {
                    width: 190
                    spacing: 3
                    SecondaryText { text: "AZIMUTH"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.currentSolarPosition.available
                              ? sky.currentSolarPosition.azimuthDegrees.toFixed(1)
                                + "° "
                                + sky.currentSolarPosition.azimuthLabel
                              : "--"
                        font.pixelSize: 14
                        color: Colors.white
                    }
                }

                Column {
                    width: 190
                    spacing: 3
                    SecondaryText { text: "HORIZON"; font.pixelSize: 9 }
                    GohuText {
                        text: sky.currentSolarPosition.available
                              ? (sky.currentSolarPosition.aboveHorizon
                                 ? "ABOVE HORIZON" : "BELOW HORIZON")
                              : "--"
                        font.pixelSize: 12
                        color: sky.currentSolarPosition.aboveHorizon
                               ? Colors.yellow : Colors.magenta
                    }
                }
            }

            QuietText {
                visible: sky.twilightSummary.available
                         && !sky.currentSolarPosition.available
                width: parent.width
                text: "CURRENT SUN POSITION UNAVAILABLE // PROVIDER OBSERVATION CLOCK IS MISSING OR STALE"
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                text: "CALCULATED SOLAR GEOMETRY // DATE + WEATHER COORDINATES // CLOCK CALIBRATED TO PROVIDER SUNRISE // NOT OBSERVED"
                font.pixelSize: 9
            }

            QuietText {
                visible: sky.currentSolarPosition.available
                width: parent.width
                text: "GEOMETRIC SUN POSITION // ALTITUDE ABOVE HORIZON // AZIMUTH CLOCKWISE FROM NORTH"
                font.pixelSize: 9
            }
        }

        QuietText {
            visible: sky.astronomySummary.available
                     && !sky.twilightSummary.available
            width: parent.width
            text: "TWILIGHT WINDOWS UNAVAILABLE // REQUIRES VALID DATE, COORDINATES, PROVIDER SUNRISE, AND A DAILY SUNRISE SOLUTION"
            font.pixelSize: 9
            color: Colors.orange
        }

        Column {
            spacing: 4

            StationSectionDivider {
                width: skyContent.width
                title: "FORECAST // NEXT HOURS"
            }

            QuietText {
                text: "SELECT A FORECAST HOUR TO INSPECT"
                font.pixelSize: 9
                visible: sky.hourlyForecast.length > 0
            }

            Row {
                spacing: 10

                Repeater {
                    model: sky.hourlyForecast

                    delegate: Column {
                        required property var modelData
                        required property int index

                        width: 112
                        spacing: 2

                        Row {
                            spacing: 6

                            GohuText {
                                text: modelData.timeLabel
                                font.pixelSize: 12
                                color: sky.inspectedHourIndex === index
                                       ? Colors.magenta : Colors.cyan
                            }

                            GohuText {
                                text: modelData.tempF > -900
                                      ? Math.round(modelData.tempF) + "°F"
                                      : "--°F"
                                font.pixelSize: 17
                                color: Colors.orange
                            }
                        }

                        Item {
                            width: parent.width
                            // Keep the slot and its rain meter stationary.
                            // Raise only the icon toward its time/temperature.
                            height: 74

                            readonly property var forecastState:
                                sky.iconState(modelData.condition, modelData.weatherCode, false)
                            readonly property var forecastCycle:
                                WeatherCyclePolicy.forecast(
                                    modelData.date, modelData.time, sky.dailyForecast)
                            readonly property string forecastArt:
                                WeatherCyclePolicy.artworkFor(forecastState, forecastCycle)

                            SafeDropShadow {
                                anchors.fill: hourlyIconGlyph
                                safeSource: hourlyIconGlyph
                                requestedVisible: parent.forecastArt === "weather"
                                radius: 12
                                samples: 25
                                horizontalOffset: 0
                                verticalOffset: 0
                                transparentBorder: true
                                opacity: 0.95
                                color: sky.iconColor(parent.forecastState.color)
                            }

                            Text {
                                id: hourlyIconGlyph
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset: -8
                                text: parent.forecastState.icon
                                font.pixelSize: 80
                                color: sky.iconColor(parent.forecastState.color)
                                visible: parent.forecastArt === "weather"
                            }

                            WeatherCelestialGlyph {
                                id: hourlyCelestial
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset: -8
                                width: 70
                                height: 70
                                mode: parent.forecastArt
                                weatherKind: WeatherCyclePolicy.nightKind(parent.forecastState)
                                solar: parent.forecastCycle.solar
                                moonPhase: parent.forecastCycle.moonPhase
                                ink: sky.iconColor(parent.forecastState.color)
                                visible: parent.forecastArt !== "weather"
                            }

                            SafeDropShadow {
                                anchors.fill: hourlyCelestial
                                safeSource: hourlyCelestial
                                requestedVisible: hourlyCelestial.visible
                                                 && parent.forecastCycle.solar !== "night"
                                radius: 12
                                samples: 25
                                horizontalOffset: 0
                                verticalOffset: 0
                                transparentBorder: true
                                opacity: 0.95
                                color: sky.iconColor(parent.forecastState.color)
                                z: -1
                            }

                        }

                        Row {
                            width: parent.width
                            spacing: 5

                            QuietText {
                                id: hourlyRainLabel
                                text: modelData.chanceRain >= 0
                                      ? "RAIN " + Math.round(
                                            modelData.chanceRain
                                        ) + "%"
                                      : "RAIN --"
                                font.pixelSize: 9
                            }

                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.max(20, parent.width
                                               - hourlyRainLabel.implicitWidth
                                               - parent.spacing)
                                height: 6
                                color: Colors.black
                                border.width: 1
                                border.color: sky.meterBorderColor

                                Rectangle {
                                    x: 2
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: (parent.width - 4)
                                           * sky.chanceMeter(
                                               modelData.chanceRain
                                           )
                                    height: parent.height - 4
                                    color: sky.meterFillColor
                                }
                            }
                        }

                        // Pointer handlers do NOT participate in Column
                        // positioner sizing. An anchors.fill MouseArea inside
                        // this implicit-height Column collapsed all 6 icons.
                        TapHandler {
                            onTapped: sky.inspectedHourIndex = index
                        }

                        HoverHandler {
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }

            StationSectionDivider {
                width: skyContent.width
                title: "HOURLY // INSPECT SELECTED FORECAST"
                visible: sky.inspectedHour !== null
            }

            Rectangle {
                width: skyContent.width
                height: inspectorContents.implicitHeight + 20
                visible: sky.inspectedHour !== null
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Column {
                    id: inspectorContents
                    x: 10
                    y: 10
                    width: parent.width - 20
                    spacing: 9

                    // Close returns to the original icon forecast. Keep
                    // the dismiss control inside this detail section, not
                    // in the global Weather Station header.
                    Item {
                        width: parent.width
                        height: 39

                        GohuText {
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: inspectorClose.left
                            anchors.rightMargin: 8
                            text: HourlyDetails.hourCaption(sky.inspectedHour)
                            font.pixelSize: 11
                            color: Colors.magenta
                            elide: Text.ElideRight
                        }

                        QuietText {
                            anchors.left: parent.left
                            anchors.bottom: parent.bottom
                            text: "WTTR.IN // FORECAST, NOT OBSERVED"
                            font.pixelSize: 9
                        }

                        ActionButton {
                            id: inspectorClose
                            anchors.top: parent.top
                            anchors.right: parent.right
                            width: 30
                            height: 27
                            label: "X"
                            accentColor: Colors.magenta
                            onClicked: sky.inspectedHourIndex = -1
                        }
                    }

                    Grid {
                        width: parent.width
                        columns: 4
                        columnSpacing: 12
                        rowSpacing: 9

                        Repeater {
                            model: sky.inspectedHourMetrics

                            delegate: Column {
                                required property var modelData
                                width: (inspectorContents.width - 36) / 4
                                spacing: 4

                                SecondaryText {
                                    text: modelData.title
                                    font.pixelSize: 10
                                }

                                GohuText {
                                    text: modelData.value
                                    font.pixelSize: 14
                                    color: Colors.white
                                }
                            }
                        }
                    }
                }
            }
        }

        Column {
            spacing: 4

            StationSectionDivider {
                width: skyContent.width
                title: "FORECAST // DAILY"
            }

            Row {
                spacing: 18

                Repeater {
                    model: sky.dailyForecast

                    delegate: Column {
                        required property var modelData

                        width: 220
                        spacing: 3

                        // Date and temperature form one centered header row.
                        Row {
                            anchors.horizontalCenter: parent.horizontalCenter
                            spacing: 12

                            GohuText {
                                text: modelData.date
                                font.pixelSize: 12
                                color: Colors.cyan
                            }

                            GohuText {
                                text: (
                                    modelData.maxTempF > -900
                                    ? Math.round(modelData.maxTempF) : "--"
                                ) + "° / " + (
                                    modelData.minTempF > -900
                                    ? Math.round(modelData.minTempF) : "--"
                                ) + "°F"
                                font.pixelSize: 16
                                color: Colors.white
                            }
                        }

                        // Keep the original 116px slot and icon position.
                        // Sunrise stays under the date; the rain meter goes
                        // below the large weather icon without growing the row.
                        Item {
                            id: dailyForecastArtwork
                            width: parent.width
                            height: 116

                            readonly property var forecastState:
                                sky.iconState(modelData.condition, modelData.weatherCode, false)
                            readonly property var forecastCycle:
                                WeatherCyclePolicy.atLocal(
                                    modelData.date, 12 * 60, sky.dailyForecast)
                            readonly property string forecastArt:
                                WeatherCyclePolicy.artworkFor(forecastState, forecastCycle)

                            Column {
                                id: dailyWeatherDetails
                                anchors.top: parent.top
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: parent.width
                                z: 2

                                QuietText {
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter
                                    text: "SUN "
                                          + modelData.sunrise
                                          + " → "
                                          + modelData.sunset
                                    font.pixelSize: 9
                                }
                            }

                            Row {
                                id: dailyRainMeter
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 2
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 8
                                z: 2

                                QuietText {
                                    text: modelData.chanceRain >= 0
                                          ? "RAIN "
                                            + Math.round(modelData.chanceRain)
                                            + "%"
                                          : "RAIN --"
                                    font.pixelSize: 10
                                }

                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 120
                                    height: 6
                                    color: Colors.black
                                    border.width: 1
                                    border.color: sky.meterBorderColor

                                    Rectangle {
                                        x: 2
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: (parent.width - 4)
                                               * sky.chanceMeter(
                                                   modelData.chanceRain
                                               )
                                        height: parent.height - 4
                                        color: sky.meterFillColor
                                    }
                                }
                            }

                            SafeDropShadow {
                                anchors.fill: dailyIconGlyph
                                safeSource: dailyIconGlyph
                                requestedVisible: parent.forecastArt === "weather"
                                radius: 12
                                samples: 25
                                horizontalOffset: 0
                                verticalOffset: 0
                                transparentBorder: true
                                opacity: 0.95
                                color: sky.iconColor(parent.forecastState.color)
                            }

                            Text {
                                id: dailyIconGlyph
                                anchors.centerIn: parent
                                text: parent.forecastState.icon
                                font.pixelSize: 100
                                color: sky.iconColor(parent.forecastState.color)
                                visible: parent.forecastArt === "weather"
                            }

                            WeatherCelestialGlyph {
                                id: dailyCelestial
                                anchors.centerIn: parent
                                width: 94
                                height: 94
                                mode: parent.forecastArt
                                solar: parent.forecastCycle.solar
                                moonPhase: parent.forecastCycle.moonPhase
                                ink: sky.iconColor(parent.forecastState.color)
                                visible: parent.forecastArt !== "weather"
                            }

                            SafeDropShadow {
                                anchors.fill: dailyCelestial
                                safeSource: dailyCelestial
                                requestedVisible: dailyCelestial.visible
                                                 && parent.forecastCycle.solar !== "night"
                                radius: 12
                                samples: 25
                                horizontalOffset: 0
                                verticalOffset: 0
                                transparentBorder: true
                                opacity: 0.95
                                color: sky.iconColor(parent.forecastState.color)
                                z: -1
                            }
                        }

                        Row {
                            anchors.horizontalCenter: parent.horizontalCenter
                            spacing: 4

                            WeatherCelestialGlyph {
                                width: 20
                                height: 20
                                mode: "moon"
                                moonPhase: WeatherCyclePolicy.normalizedPhase(
                                    modelData.moonPhase)
                                ink: sky.iconColor(dailyForecastArtwork.forecastState.color)
                            }

                            QuietText {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "MOON " + (
                                    WeatherCyclePolicy.normalizedPhase(modelData.moonPhase) !== "unknown"
                                    ? modelData.moonPhase.toUpperCase() : "--")
                                    + (modelData.moonIllumination >= 0
                                        ? " // " + Math.round(modelData.moonIllumination) + "%"
                                        : "")
                                font.pixelSize: 9
                            }
                        }
                    }
                }
            }
        }

        }
    }

    // Use the established scroll control; the rail remains outside content.
    NeonScrollBar {
        flickable: skyScroll
        handleStyle: "star"
        geometryHost: sky
        visible: scrollable
    }
}
