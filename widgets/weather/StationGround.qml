import QtQuick
import "../../components"

Rectangle {
    id: ground

    property var weatherService: null

    readonly property bool aqiReady: weatherService && weatherService.aqiReady
    readonly property bool aqiLoading: weatherService && weatherService.aqiLoading
    readonly property real aqiValue: aqiReady ? Number(weatherService.aqi) : 0
    readonly property real pm25Value:
        aqiReady ? Number(weatherService.pm25) : 0
    readonly property real pm10Value:
        aqiReady ? Number(weatherService.pm10) : 0

    readonly property real ozoneValue:
        weatherService ? Number(weatherService.ozone) : -1
    readonly property real nitrogenDioxideValue:
        weatherService ? Number(weatherService.nitrogenDioxide) : -1
    readonly property real carbonMonoxideValue:
        weatherService ? Number(weatherService.carbonMonoxide) : -1
    readonly property real dustValue:
        weatherService ? Number(weatherService.dust) : -1

    readonly property real ozoneAqiValue:
        weatherService ? Number(weatherService.ozoneAqi) : -1
    readonly property real nitrogenDioxideAqiValue:
        weatherService ? Number(weatherService.nitrogenDioxideAqi) : -1
    readonly property real carbonMonoxideAqiValue:
        weatherService ? Number(weatherService.carbonMonoxideAqi) : -1

    readonly property var pollenPeak: {
        if (!weatherService || !weatherService.pollenAvailable)
            return { "name": "UNAVAILABLE", "value": -1 };

        const entries = [
            ["ALDER", Number(weatherService.alderPollen)],
            ["BIRCH", Number(weatherService.birchPollen)],
            ["GRASS", Number(weatherService.grassPollen)],
            ["MUGWORT", Number(weatherService.mugwortPollen)],
            ["OLIVE", Number(weatherService.olivePollen)],
            ["RAGWEED", Number(weatherService.ragweedPollen)]
        ];

        let best = { "name": "UNAVAILABLE", "value": -1 };
        for (let i = 0; i < entries.length; i++) {
            if (isFinite(entries[i][1]) && entries[i][1] >= 0
                    && entries[i][1] > best.value) {
                best = { "name": entries[i][0], "value": entries[i][1] };
            }
        }
        return best;
    }

    function concentrationText(value, suffix) {
        return isFinite(value) && value >= 0
               ? value.toFixed(1) + suffix
               : "--";
    }

    // These are normalized views of real telemetry, preserved from the
    // original combined HOME implementation.
    readonly property real aqiMeter:
        Math.max(0, Math.min(1, aqiValue / 500))
    readonly property real pm25Meter:
        Math.max(0, Math.min(1, pm25Value / 100))
    readonly property real pm10Meter:
        Math.max(0, Math.min(1, pm10Value / 150))

    // Gas bars use Open-Meteo's provider-computed U.S. AQI component
    // indices rather than inventing arbitrary concentration ceilings.
    readonly property real ozoneMeter:
        Math.max(0, Math.min(1, ozoneAqiValue / 500))
    readonly property real nitrogenDioxideMeter:
        Math.max(0, Math.min(1, nitrogenDioxideAqiValue / 500))
    readonly property real carbonMonoxideMeter:
        Math.max(0, Math.min(1, carbonMonoxideAqiValue / 500))

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

    readonly property color meterBorderColor: Colors.cyan
    readonly property color meterFillColor: Colors.green

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

        StationSectionDivider {
            width: parent.width
            title: "AIR // PARTICULATES"
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

                Rectangle {
                    width: 130
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.aqiMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
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

                Rectangle {
                    width: 120
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.pm25Meter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
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

                Rectangle {
                    width: 120
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.pm10Meter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
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

        StationSectionDivider {
            width: parent.width
            title: "GASES // POLLEN"
        }

        Row {
            spacing: 18

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "OZONE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.ozoneValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 115
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.ozoneMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "NO₂"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.nitrogenDioxideValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 115
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.nitrogenDioxideMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 150
                spacing: 5

                SecondaryText {
                    text: "CO"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.carbonMonoxideValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 125
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.carbonMonoxideMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "DUST"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.dustValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }
            }

            Column {
                width: 170
                spacing: 5

                SecondaryText {
                    text: "POLLEN // PEAK"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.pollenPeak.value >= 0
                          ? ground.pollenPeak.value.toFixed(1) + " gr/m³"
                          : "N/A"
                    font.pixelSize: 16
                    color: ground.pollenPeak.value >= 0
                           ? Colors.green : Colors.white
                }

                QuietText {
                    text: ground.pollenPeak.name
                    font.pixelSize: 10
                }
            }
        }

        QuietText {
            text: "surface / environment / events / infrastructure"
            font.pixelSize: 13
        }
    }
}
