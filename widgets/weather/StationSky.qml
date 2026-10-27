import QtQuick
import "../../components"
import "../../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy
import "StationSkyHourlyPolicy.js" as HourlyDetails

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
