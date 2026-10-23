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

    // Only gas component AQI scores are available. This is NOT a claim
    // about the primary pollutant driving overall AQI.
    readonly property var gasLeader: {
        if (!aqiReady)
            return { "name": "UNAVAILABLE", "value": -1 };
        const indices = [
            ["OZONE", ozoneAqiValue],
            ["NO₂", nitrogenDioxideAqiValue],
            ["CO", carbonMonoxideAqiValue]
        ];
        let peak = { "name": "UNAVAILABLE", "value": -1 };
        for (let i = 0; i < indices.length; i++) {
            const index = Number(indices[i][1]);
            if (isFinite(index) && index >= 0 && index > peak.value)
                peak = { "name": indices[i][0], "value": index };
        }
        return peak;
    }

    function particulateText(value) {
        return aqiReady && isFinite(value) && value >= 0
               ? Number(value).toFixed(1) + " µg/m³" : "-- µg/m³";
    }

    readonly property color meterBorderColor: Colors.cyan
    readonly property color meterFillColor: Colors.green

    color: Colors.black

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

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

        // One large instrument, two particulate measurements and the
        // highest available gas AQI component. No invented measurement.
        Row {
            width: parent.width
            spacing: 14

            Rectangle {
                id: airQualityInstrument
                width: 248
                height: 166
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                SecondaryText {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.margins: 12
                    text: "U.S. AIR QUALITY INDEX"
                    font.pixelSize: 11
                }

                GohuText {
                    id: aqiReadingText
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 29
                    text: ground.aqiReady ? String(weatherService.aqi) : "--"
                    font.pixelSize: 68
                    color: ground.aqiColor
                }

                SafeDropShadow {
                    anchors.fill: aqiReadingText
                    safeSource: aqiReadingText
                    requestedVisible: ground.aqiReady
                    radius: 10
                    samples: 19
                    horizontalOffset: 0
                    verticalOffset: 0
                    transparentBorder: true
                    opacity: 0.68
                    color: ground.aqiColor
                }

                GohuText {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: aqiTrack.top
                    anchors.bottomMargin: 9
                    text: ground.aqiReady ? weatherService.aqiLabel : "OFFLINE"
                    font.pixelSize: 12
                    color: ground.aqiColor
                }

                Rectangle {
                    id: aqiTrack
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    height: 9
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
                width: 158
                spacing: 10

                SecondaryText {
                    text: "PM2.5 // FINE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.particulateText(ground.pm25Value)
                    font.pixelSize: 19
                    color: Colors.white
                }

                Rectangle {
                    width: 144
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

                QuietText {
                    text: "FINE PARTICLES"
                    font.pixelSize: 10
                }
            }

            Column {
                width: 158
                spacing: 10

                SecondaryText {
                    text: "PM10 // COARSE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.particulateText(ground.pm10Value)
                    font.pixelSize: 19
                    color: Colors.white
                }

                Rectangle {
                    width: 144
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

                QuietText {
                    text: "COARSE PARTICLES"
                    font.pixelSize: 10
                }
            }

            Column {
                width: Math.max(0, parent.width - 248 - 158 - 158 - 3 * parent.spacing)
                spacing: 8

                SecondaryText {
                    text: "TOP GAS SUBINDEX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.gasLeader.name
                    font.pixelSize: 18
                    color: Colors.green
                }

                GohuText {
                    text: ground.gasLeader.value >= 0
                          ? Math.round(ground.gasLeader.value) + " AQI" : "-- AQI"
                    font.pixelSize: 19
                    color: Colors.white
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "OF OZONE / NO₂ / CO"
                    font.pixelSize: 9
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "GASES // POLLEN"
        }

        Row {
            spacing: 14

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

        StationSectionDivider {
            width: parent.width
            title: "ENVIRONMENT // SOURCE"
        }

        Row {
            width: parent.width
            spacing: 22

            Column {
                width: 248
                spacing: 5

                SecondaryText {
                    text: "POSITION // WEATHER FIX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: "LAT " + (weatherService && weatherService.latitude !== ""
                                   ? weatherService.latitude : "--")
                          + "   LON " + (weatherService && weatherService.longitude !== ""
                                      ? weatherService.longitude : "--")
                    font.pixelSize: 12
                    color: Colors.white
                }
            }

            Column {
                width: Math.max(0, parent.width - 270)
                spacing: 5

                SecondaryText {
                    text: "AIR QUALITY // SAMPLE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.aqiReady && weatherService.airQualitySourceTime !== ""
                          ? weatherService.airQualitySourceTime : "--"
                    font.pixelSize: 12
                    color: Colors.white
                }
            }
        }
    }
}
