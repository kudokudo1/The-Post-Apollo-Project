import QtQuick
import "../../components"

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

    // Normalized live telemetry scales preserved from the original page.
    readonly property real temperatureMeter:
        Math.max(0, Math.min(1, temperatureValue / 120))
    readonly property real aqiMeter:
        Math.max(0, Math.min(1, aqiValue / 500))
    readonly property real humidityMeter:
        Math.max(0, Math.min(1, humidityValue / 100))
    readonly property real windMeter:
        Math.max(0, Math.min(1, windValue / 50))

    readonly property string conditionText:
        weatherReady && weatherService.condition
        ? weatherService.condition.toUpperCase()
        : weatherLoading ? "RECEIVING..." : "DATA OFFLINE"
    readonly property string conditionIcon: iconForCondition(conditionText)

    function iconForCondition(condition) {
        const value = String(condition).toLowerCase();

        if (value.includes("thunder"))
            return "⛈";
        if (value.includes("snow") || value.includes("blizzard")
                || value.includes("sleet") || value.includes("ice"))
            return "❄";
        if (value.includes("rain") || value.includes("drizzle")
                || value.includes("shower"))
            return "🌧";
        if (value.includes("fog") || value.includes("mist"))
            return "≋";
        if (value.includes("cloud") || value.includes("overcast"))
            return "☁";
        if (value.includes("sun") || value.includes("clear"))
            return "☀";
        return "◌";
    }

    function windAngle(direction) {
        const directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ];
        const at = directions.indexOf(String(direction || "").toUpperCase());
        return at < 0 ? 0 : at * 22.5;
    }

    color: Colors.black

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 26

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
                    border.color: Colors.cyan

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.temperatureMeter
                        height: parent.height - 4
                        color: Colors.cyan
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

                GohuText {
                    text: sky.conditionIcon
                    font.pixelSize: 28
                    color: Colors.cyan
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
                    border.color: Colors.cyan

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.aqiMeter
                        height: parent.height - 4
                        color: Colors.cyan
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
                    border.color: Colors.cyan

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * sky.humidityMeter
                        height: parent.height - 4
                        color: Colors.cyan
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
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * sky.windMeter
                            height: parent.height - 4
                            color: Colors.cyan
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
