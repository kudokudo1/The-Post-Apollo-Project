import QtQuick
import "../../components"
import "../../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy

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
        const now = Date.now();
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

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

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

            Column {
                width: 190
                spacing: 4

                SecondaryText {
                    text: "CONDITION"
                    font.pixelSize: 11
                }

                GohuText {
                    text: sky.conditionText
                    font.pixelSize: 16
                    color: Colors.orange
                }

                Text {
                    text: sky.conditionState.icon
                    font.pixelSize: 44
                    color: sky.iconColor(sky.conditionState.color)
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
            spacing: 8

            StationSectionDivider {
                width: sky.width - 48
                title: "FORECAST // NEXT HOURS"
            }

            Row {
                spacing: 10

                Repeater {
                    model: sky.hourlyForecast

                    delegate: Column {
                        required property var modelData

                        width: 112
                        spacing: 3

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

                        Text {
                            readonly property var forecastState:
                                sky.iconState(modelData.condition, modelData.weatherCode, false)
                            text: forecastState.icon
                            font.pixelSize: 32
                            color: sky.iconColor(forecastState.color)
                        }

                        QuietText {
                            text: modelData.chanceRain >= 0
                                  ? "RAIN " + Math.round(
                                        modelData.chanceRain
                                    ) + "%"
                                  : "RAIN --"
                            font.pixelSize: 9
                        }

                        Rectangle {
                            width: 92
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

        Column {
            spacing: 8

            StationSectionDivider {
                width: sky.width - 48
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

                        Text {
                            readonly property var forecastState:
                                sky.iconState(modelData.condition, modelData.weatherCode, false)
                            text: forecastState.icon
                            font.pixelSize: 32
                            color: sky.iconColor(forecastState.color)
                        }

                        QuietText {
                            text: modelData.chanceRain >= 0
                                  ? "RAIN "
                                    + Math.round(modelData.chanceRain)
                                    + "%"
                                  : "RAIN --"
                            font.pixelSize: 10
                        }

                        Rectangle {
                            width: 180
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

                        QuietText {
                            text: "SUN "
                                  + modelData.sunrise
                                  + " → "
                                  + modelData.sunset
                            font.pixelSize: 9
                        }
                    }
                }
            }
        }

        QuietText {
            text: "weather / atmosphere / radar / aviation"
            font.pixelSize: 13
        }
    }
}
