import QtQuick
import "../../components"
import "../../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy

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
    readonly property string currentCelestialMode:
        weatherReady
        ? WeatherCyclePolicy.artworkFor(conditionState, skyCycle) : "weather"

    function numericText(value, digits, suffix) {
        return isFinite(value) && value >= 0
               ? Number(value).toFixed(digits) + suffix
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
                            solar: sky.skyCycle.solar
                            moonPhase: sky.skyCycle.moonPhase
                            ink: sky.iconColor(sky.conditionState.color)
                            visible: sky.currentCelestialMode !== "weather"
                        }

                        SafeDropShadow {
                            anchors.fill: currentCelestialIcon
                            safeSource: currentCelestialIcon
                            requestedVisible: currentCelestialIcon.visible
                            radius: 12
                            samples: 25
                            horizontalOffset: 0
                            verticalOffset: 0
                            transparentBorder: true
                            opacity: 0.95
                            color: sky.iconColor(sky.conditionState.color)
                            z: -1
                        }

                        // Keep a separate moon phase even when the main
                        // condition is rain, fog, wind or other weather.
                        WeatherCelestialGlyph {
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            width: 24
                            height: 24
                            mode: "moon"
                            moonPhase: sky.skyCycle.moonPhase
                            ink: sky.iconColor(sky.conditionState.color)
                            visible: sky.skyCycle.moonPhase !== "unknown"
                                     && sky.currentCelestialMode !== "moon"
                                     && sky.currentCelestialMode !== "moon-cloud"
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

        Column {
            spacing: 4

            StationSectionDivider {
                width: skyContent.width
                title: "FORECAST // NEXT HOURS"
            }

            Row {
                spacing: 10

                Repeater {
                    model: sky.hourlyForecast

                    delegate: Column {
                        required property var modelData

                        width: 112
                        spacing: 2

                        Row {
                            spacing: 6

                            GohuText {
                                text: modelData.timeLabel
                                font.pixelSize: 12
                                color: Colors.cyan
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

                            SafeDropShadow {
                                anchors.fill: hourlyIconGlyph
                                safeSource: hourlyIconGlyph
                                requestedVisible: true
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
                                requestedVisible: true
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
