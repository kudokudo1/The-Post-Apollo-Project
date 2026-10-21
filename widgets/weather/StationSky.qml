import QtQuick
import "../../components"

Rectangle {
    id: sky

    property var weatherService: null

    readonly property bool weatherReady: weatherService && weatherService.ready
    readonly property bool weatherLoading: weatherService && weatherService.loading
    readonly property bool aqiReady: weatherService && weatherService.aqiReady
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
            spacing: 28

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
                }
            }
        }

        QuietText {
            text: "weather / atmosphere / radar / aviation"
            font.pixelSize: 13
        }
    }
}
