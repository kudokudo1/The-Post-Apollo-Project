import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "../../services/weather/SeismicPolicy.js" as SeismicPolicy
import "StationGroundPollenPolicy.js" as PollenDetails

Rectangle {
    id: ground

    property var weatherService: null

    // View-scoped service: no USGS polling while GROUND is unmounted.
    WeatherServices.SeismicService {
        id: quakeService
        active: ground.visible
    }

    function distanceLabel(latitude, longitude) {
        const km = SeismicPolicy.distanceKm(
            weatherService ? weatherService.latitude : "",
            weatherService ? weatherService.longitude : "",
            latitude, longitude
        );
        return km >= 0 ? Math.round(km) + " KM FROM FIX" : "DISTANCE --";
    }

    readonly property bool aqiReady: weatherService && weatherService.aqiReady
    readonly property bool aqiLoading: weatherService && weatherService.aqiLoading
    readonly property var airQualityForecast:
        weatherService ? weatherService.airQualityForecast : []
    readonly property bool airQualityForecastReady:
        weatherService && weatherService.airQualityForecastReady
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

    readonly property var pollenSpecies: PollenDetails.species(
        !!(aqiReady && weatherService.pollenAvailable), {
            alderPollen: weatherService ? weatherService.alderPollen : -1,
            birchPollen: weatherService ? weatherService.birchPollen : -1,
            grassPollen: weatherService ? weatherService.grassPollen : -1,
            mugwortPollen: weatherService ? weatherService.mugwortPollen : -1,
            olivePollen: weatherService ? weatherService.olivePollen : -1,
            ragweedPollen: weatherService ? weatherService.ragweedPollen : -1
        }
    )

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

    function aqiSeverityColor(value) {
        const reading = Number(value);
        if (!isFinite(reading) || reading < 0 || reading > 500)
            return Colors.white;
        if (reading <= 50)
            return Colors.cyan;
        if (reading <= 100)
            return Colors.yellow;
        if (reading <= 150)
            return Colors.orange;
        return Colors.red;
    }

    readonly property color aqiColor: aqiReady
                                      ? aqiSeverityColor(aqiValue) : Colors.white

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

    // Leave the existing forecast intact; expose new rows with a scrollbar
    // if the fixed-height window cannot contain everything at once.
    Flickable {
        id: groundScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, groundContent.y + groundContent.implicitHeight + 12)

        Column {
            id: groundContent
            x: 20
            y: 12
            width: Math.max(0, groundScroll.width - 40)
            spacing: 10

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

                // Draw the halo behind its AQI glyph, not over the number.
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
                    id: aqiReadingText
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 29
                    text: ground.aqiReady ? String(weatherService.aqi) : "--"
                    font.pixelSize: 68
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

        // The peak is only a summary. Show the six already-received
        // per-species readings without requesting a second pollen source.
        StationSectionDivider {
            width: parent.width
            title: "POLLEN // SPECIES"
        }

        Row {
            width: parent.width
            spacing: 8
            visible: ground.pollenSpecies.length > 0

            Repeater {
                model: ground.pollenSpecies

                delegate: Column {
                    required property var modelData
                    width: (groundContent.width - 5 * 8) / 6
                    spacing: 5

                    SecondaryText {
                        text: modelData.name
                        font.pixelSize: 10
                    }

                    GohuText {
                        width: parent.width
                        text: modelData.label
                        font.pixelSize: 13
                        color: modelData.available ? Colors.green : Colors.white
                        elide: Text.ElideRight
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 10
            text: ground.pollenSpecies.length > 0
                  ? "OPEN-METEO // CURRENT CONCENTRATION IN GRAINS/M³ // -- = NO READING, NOT ZERO"
                  : "POLLEN SPECIES UNAVAILABLE FOR THIS PROVIDER / LOCATION"
        }

        StationSectionDivider {
            width: parent.width
            title: "AIR // NEXT 12 HOURS"
        }

        Column {
            width: parent.width
            spacing: 4

            Row {
                width: parent.width
                spacing: 8

                Repeater {
                    model: ground.airQualityForecastReady
                           ? ground.airQualityForecast : []

                    delegate: Column {
                        required property var modelData
                        width: 116
                        spacing: 4

                        SecondaryText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.label
                            font.pixelSize: 11
                        }

                        GohuText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.aqi >= 0
                                  ? Math.round(modelData.aqi) + " AQI" : "-- AQI"
                            font.pixelSize: 22
                            color: ground.aqiSeverityColor(modelData.aqi)
                        }

                        Rectangle {
                            width: parent.width - 12
                            anchors.horizontalCenter: parent.horizontalCenter
                            height: 7
                            color: Colors.black
                            border.width: 1
                            border.color: ground.meterBorderColor

                            Rectangle {
                                x: 2
                                anchors.verticalCenter: parent.verticalCenter
                                width: (parent.width - 4)
                                       * (modelData.aqi >= 0
                                          ? Math.max(0, Math.min(1, modelData.aqi / 500))
                                          : 0)
                                height: parent.height - 4
                                color: ground.aqiSeverityColor(modelData.aqi)
                            }
                        }

                        QuietText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.pm25 >= 0
                                  ? "PM2.5 " + modelData.pm25.toFixed(1)
                                  : "PM2.5 --"
                            font.pixelSize: 10
                        }
                    }
                }
            }

            QuietText {
                visible: !ground.airQualityForecastReady
                text: "FORECAST UNAVAILABLE // CURRENT AIR QUALITY REMAINS ABOVE"
                font.pixelSize: 11
            }

            QuietText {
                text: "OPEN-METEO MODEL // LOCAL HOURS // 2H STEPS // PM2.5 IN µg/m³"
                font.pixelSize: 9
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SEISMIC // WORLDWIDE 24H"
        }

        Column {
            width: parent.width
            spacing: 5

            Row {
                spacing: 12

                SecondaryText {
                    text: "USGS // M2.5+"
                    font.pixelSize: 11
                    color: Colors.green
                }

                QuietText {
                    text: quakeService.failed
                          ? "FEED ERROR // PREVIOUS EVENTS MAY BE STALE"
                          : quakeService.loading && !quakeService.ready
                            ? "RECEIVING"
                            : quakeService.ready ? "LATEST PUBLISHED EVENTS"
                              : "OFFLINE"
                    font.pixelSize: 10
                }
            }

            Row {
                id: seismicEventRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: quakeService.ready ? quakeService.events : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (seismicEventRow.width
                                            - 2 * seismicEventRow.spacing) / 3)
                        height: 112
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            Row {
                                width: parent.width
                                spacing: 8

                                GohuText {
                                    text: "M " + modelData.magnitude.toFixed(1)
                                    font.pixelSize: 23
                                    color: Colors.green
                                }

                                QuietText {
                                    text: modelData.utc
                                    font.pixelSize: 10
                                }
                            }

                            GohuText {
                                width: parent.width
                                elide: Text.ElideRight
                                text: modelData.place
                                font.pixelSize: 12
                                color: Colors.white
                            }

                            QuietText {
                                text: modelData.depthKm >= 0
                                      ? "DEPTH " + modelData.depthKm.toFixed(1) + " KM"
                                      : "DEPTH --"
                                font.pixelSize: 10
                            }

                            QuietText {
                                text: ground.distanceLabel(
                                    modelData.latitude, modelData.longitude
                                )
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !quakeService.ready || quakeService.events.length === 0
                text: quakeService.failed ? quakeService.errorText
                      : quakeService.loading ? "LOADING USGS EVENTS"
                      : quakeService.ready ? "NO M2.5+ EVENTS IN FEED"
                        : "USGS DATA UNAVAILABLE"
                font.pixelSize: 11
            }

            QuietText {
                text: "USGS GEOJSON // MOST RECENT GLOBAL EVENTS // NOT AN EARTHQUAKE WARNING"
                font.pixelSize: 9
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

    NeonScrollBar {
        flickable: groundScroll
        handleStyle: "star"
        geometryHost: ground
        visible: scrollable
    }
}
