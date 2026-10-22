import QtQuick
import "../../components"

Rectangle {
    id: ground

    property var weatherService: null

    readonly property bool aqiReady: weatherService && weatherService.aqiReady
    readonly property bool aqiLoading: weatherService && weatherService.aqiLoading
    readonly property real aqiValue: aqiReady ? Number(weatherService.aqi) : 0

    readonly property color aqiColor: {
        if (!aqiReady)
            return Colors.white;
        if (aqiValue <= 50)
            return Colors.cyan;
        if (aqiValue <= 100)
            return Colors.yellow;
        if (aqiValue <= 150)
            return Colors.orange;
        return Colors.red;
    }

    color: Colors.black

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 26

        Row {
            width: parent.width

            GohuText {
                text: "⌁  GROUND"
                font.pixelSize: 24
                color: Colors.green
            }

            Item {
                width: parent.width - 330
                height: 1
            }

            GohuText {
                text: ground.aqiReady
                      ? "ENVIRONMENT ONLINE"
                      : ground.aqiLoading
                        ? "RECEIVING"
                        : "OFFLINE"
                font.pixelSize: 12
                color: ground.aqiReady ? Colors.cyan : Colors.orange
            }
        }

        Row {
            spacing: 35

            Column {
                width: 145
                spacing: 6

                SecondaryText {
                    text: "AIR QUALITY"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.aqiReady ? String(weatherService.aqi) : "--"
                    font.pixelSize: 28
                    color: ground.aqiColor
                }

                GohuText {
                    text: ground.aqiReady ? weatherService.aqiLabel : "OFFLINE"
                    font.pixelSize: 11
                    color: ground.aqiColor
                }
            }

            Column {
                width: 150
                spacing: 6

                SecondaryText {
                    text: "PM2.5"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.aqiReady
                          ? Number(weatherService.pm25).toFixed(1) + " µg/m³"
                          : "-- µg/m³"
                    font.pixelSize: 18
                    color: Colors.white
                }
            }

            Column {
                width: 150
                spacing: 6

                SecondaryText {
                    text: "PM10"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.aqiReady
                          ? Number(weatherService.pm10).toFixed(1) + " µg/m³"
                          : "-- µg/m³"
                    font.pixelSize: 18
                    color: Colors.white
                }
            }

            Column {
                width: 210
                spacing: 6

                SecondaryText {
                    text: "POSITION"
                    font.pixelSize: 11
                }

                GohuText {
                    text: "LAT  " + (
                        weatherService && weatherService.latitude !== ""
                        ? weatherService.latitude : "--"
                    )
                    font.pixelSize: 14
                    color: Colors.white
                }

                GohuText {
                    text: "LON  " + (
                        weatherService && weatherService.longitude !== ""
                        ? weatherService.longitude : "--"
                    )
                    font.pixelSize: 14
                    color: Colors.white
                }
            }
        }

        QuietText {
            text: "surface / environment / events / infrastructure"
            font.pixelSize: 13
        }
    }
}
