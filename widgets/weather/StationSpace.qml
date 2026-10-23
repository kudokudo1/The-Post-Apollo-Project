import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices

Rectangle {
    id: space

    property var spaceService: null

    // OVATION's gridded model fetch exists only while SPACE is instantiated.
    WeatherServices.AuroraService {
        id: auroraService
        active: space.visible
    }

    WeatherServices.SolarFlareService {
        id: flareService
        active: space.visible
    }

    // Event classes are measured GOES X-ray peaks, not alert severity.
    function flareClassColor(letter) {
        if (letter === "X")
            return Colors.magenta;
        if (letter === "M")
            return Colors.orange;
        if (letter === "C")
            return Colors.yellow;
        if (letter === "B")
            return Colors.cyan;
        return Colors.white;
    }

    readonly property bool spaceReady: spaceService && spaceService.ready
    readonly property bool spaceLoading: spaceService && spaceService.loading

    readonly property real kpValue:
        spaceService && spaceService.kp >= 0 ? Number(spaceService.kp) : 0
    readonly property real solarWindValue:
        spaceService && spaceService.solarWindSpeed >= 0
        ? Number(spaceService.solarWindSpeed) : 0
    readonly property real bzValue:
        spaceService && spaceService.magneticFieldReady
        ? Number(spaceService.magneticFieldBz) : 0
    readonly property real btValue:
        spaceService && spaceService.magneticFieldReady
        ? Number(spaceService.magneticFieldBt) : -1
    readonly property real solarFluxValue:
        spaceService && spaceService.solarFlux >= 0
        ? Number(spaceService.solarFlux) : 0

    // Normalized live NOAA telemetry scales preserved from the original page.
    readonly property real kpMeter:
        Math.max(0, Math.min(1, kpValue / 9))
    readonly property real solarWindMeter:
        Math.max(0, Math.min(1, solarWindValue / 1000))
    readonly property real bzMeter:
        Math.max(0, Math.min(1, Math.abs(bzValue) / 20))
    readonly property real btMeter:
        Math.max(0, Math.min(1, btValue / 20))
    readonly property real solarFluxMeter:
        Math.max(0, Math.min(1, solarFluxValue / 300))

    readonly property color kpColor: {
        if (!spaceService || !spaceService.kpReady)
            return Colors.white;
        if (kpValue < 4)
            return Colors.cyan;
        if (kpValue < 5)
            return Colors.yellow;
        if (kpValue < 6)
            return Colors.orange;
        return Colors.red;
    }

    readonly property color solarWindColor: {
        if (!spaceService || !spaceService.solarWindReady)
            return Colors.white;
        if (solarWindValue < 500)
            return Colors.cyan;
        if (solarWindValue < 650)
            return Colors.yellow;
        if (solarWindValue < 800)
            return Colors.orange;
        return Colors.red;
    }

    readonly property color bzColor: {
        if (!spaceService || !spaceService.magneticFieldReady)
            return Colors.white;
        if (bzValue <= -10)
            return Colors.red;
        if (bzValue <= -5)
            return Colors.orange;
        if (bzValue < 0)
            return Colors.yellow;
        return Colors.cyan;
    }

    function shortSampleTime(value) {
        const text = String(value || "");
        if (text.length === 0)
            return "--";

        return text.replace("T", " ").replace("Z", "").slice(5, 16);
    }

    readonly property color meterBorderColor: Colors.cyan
    readonly property color meterFillColor: Colors.magenta

    color: Colors.black

    // Compact observatory view: promote the existing NOAA readings without
    // introducing another refresh, provider, or invented severity scale.
    // The original instruments stay in place. Scroll SPACE itself if the
    // new model forecast extends beyond the station's fixed-height viewport.
    Flickable {
        id: spaceScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, spaceContent.y + spaceContent.implicitHeight + 12)

        Column {
            id: spaceContent
            x: 20
            y: 12
            width: Math.max(0, spaceScroll.width - 40)
            spacing: 10

            Row {
            width: parent.width

            GohuText {
                text: "✦  SPACE"
                font.pixelSize: 24
                color: Colors.magenta
            }

            Item {
                width: parent.width - 315
                height: 1
            }

            GohuText {
                text: space.spaceReady
                      ? "SPACE WEATHER ONLINE"
                      : space.spaceLoading
                        ? "RECEIVING"
                        : "OFFLINE"
                font.pixelSize: 12
                color: space.spaceReady ? Colors.cyan : Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR // GEOMAGNETIC"
        }

        Row {
            width: parent.width
            spacing: 14

            Rectangle {
                id: kpInstrument
                width: 236
                height: 184
                color: Colors.dark
                border.width: 1
                border.color: space.meterBorderColor

                SecondaryText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: 12
                    text: "PLANETARY // KP INDEX"
                    font.pixelSize: 11
                }

                // Glow behind the live Kp value, respecting the established
                // warning palette and the SafeDropShadow teardown behavior.
                SafeDropShadow {
                    anchors.fill: kpHeroReading
                    safeSource: kpHeroReading
                    requestedVisible: spaceService && spaceService.kpReady
                    radius: 11
                    samples: 21
                    horizontalOffset: 0
                    verticalOffset: 0
                    transparentBorder: true
                    opacity: 0.72
                    color: space.kpColor
                }

                GohuText {
                    id: kpHeroReading
                    anchors.top: parent.top
                    anchors.topMargin: 29
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: spaceService ? spaceService.kpText : "--"
                    font.pixelSize: 74
                    color: space.kpColor
                }

                GohuText {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: kpTrack.top
                    anchors.bottomMargin: 11
                    text: spaceService ? spaceService.kpLabel : "OFFLINE"
                    font.pixelSize: 12
                    color: space.kpColor
                }

                Rectangle {
                    id: kpTrack
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    height: 9
                    color: Colors.black
                    border.width: 1
                    border.color: space.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.kpMeter
                        height: parent.height - 4
                        color: space.meterFillColor
                    }
                }
            }

            Row {
                width: Math.max(0, parent.width - kpInstrument.width - parent.spacing)
                spacing: 14

                Column {
                    width: Math.max(0, (parent.width - 2 * parent.spacing) / 3)
                    spacing: 9

                    SecondaryText {
                        text: "SOLAR WIND"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? spaceService.solarWindText : "-- KM/S"
                        font.pixelSize: 28
                        color: space.solarWindColor
                    }

                    Rectangle {
                        width: parent.width - 10
                        height: 9
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * space.solarWindMeter
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }

                    QuietText {
                        text: "STREAM SPEED"
                        font.pixelSize: 10
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 2 * parent.spacing) / 3)
                    spacing: 9

                    SecondaryText {
                        text: "IMF BZ"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService ? spaceService.bzText : "-- nT"
                        font.pixelSize: 28
                        color: space.bzColor
                    }

                    Rectangle {
                        width: parent.width - 10
                        height: 9
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * space.bzMeter
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }

                    GohuText {
                        width: parent.width
                        text: spaceService ? spaceService.bzLabel : "OFFLINE"
                        font.pixelSize: 11
                        color: space.bzColor
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 2 * parent.spacing) / 3)
                    spacing: 9

                    SecondaryText {
                        text: "F10.7 FLUX"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? spaceService.solarFluxText : "-- SFU"
                        font.pixelSize: 28
                        color: Colors.white
                    }

                    Rectangle {
                        width: parent.width - 10
                        height: 9
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * space.solarFluxMeter
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }

                    QuietText {
                        text: "10.7 CM RADIO FLUX"
                        font.pixelSize: 10
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "FIELD // SOURCE TIMES"
        }

        Row {
            width: parent.width
            spacing: 14

            Column {
                width: 180
                spacing: 6

                SecondaryText {
                    text: "IMF BT"
                    font.pixelSize: 11
                }

                GohuText {
                    text: space.btValue >= 0
                          ? space.btValue.toFixed(1) + " nT"
                          : "-- nT"
                    font.pixelSize: 30
                    color: Colors.white
                }

                Rectangle {
                    width: 158
                    height: 9
                    color: Colors.black
                    border.width: 1
                    border.color: space.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.btMeter
                        height: parent.height - 4
                        color: space.meterFillColor
                    }
                }

                QuietText {
                    text: "TOTAL FIELD"
                    font.pixelSize: 10
                }
            }

            Row {
                width: Math.max(0, parent.width - 180 - parent.spacing)
                spacing: 10

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "KP SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(spaceService.kpTime)
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "WIND SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(spaceService.solarWindTime)
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "IMF SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(
                                    spaceService.magneticFieldTime
                                )
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "FLUX SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(spaceService.solarFluxTime)
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "AURORA // 30-90 MIN FORECAST"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 14

                Rectangle {
                    width: 228
                    height: 122
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "BOREALIS // NORTH PEAK"
                        font.pixelSize: 11
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 28
                        text: auroraService.ready
                              ? Math.round(auroraService.northPeak) + "%" : "--%"
                        font.pixelSize: 39
                        color: auroraService.forecastFresh
                               ? Colors.magenta : Colors.white
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 10
                        height: 8
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4)
                                   * (auroraService.ready
                                      ? auroraService.northPeak / 100 : 0)
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }
                }

                Rectangle {
                    width: 228
                    height: 122
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "AUSTRALIS // SOUTH PEAK"
                        font.pixelSize: 11
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 28
                        text: auroraService.ready
                              ? Math.round(auroraService.southPeak) + "%" : "--%"
                        font.pixelSize: 39
                        color: auroraService.forecastFresh
                               ? Colors.magenta : Colors.white
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 10
                        height: 8
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4)
                                   * (auroraService.ready
                                      ? auroraService.southPeak / 100 : 0)
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }
                }

                Column {
                    width: Math.max(0, parent.width - 456 - 2 * parent.spacing)
                    spacing: 8

                    SecondaryText {
                        text: "MODEL VALID // UTC"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: auroraService.ready
                              ? auroraService.forecastLabel : "-- UTC"
                        font.pixelSize: 17
                        color: Colors.white
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: auroraService.failed
                              ? "FETCH ERROR // LAST DATA"
                              : auroraService.loading && !auroraService.ready
                                ? "RECEIVING"
                                : auroraService.forecastFresh
                                  ? "MODEL CURRENT"
                                  : auroraService.ready ? "MODEL STALE"
                                    : "UNAVAILABLE"
                        font.pixelSize: 11
                        color: auroraService.forecastFresh
                               ? Colors.cyan : Colors.orange
                    }

                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: "OBS " + (auroraService.ready
                                       ? auroraService.observationLabel : "-- UTC")
                        font.pixelSize: 10
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "NOAA OVATION GRID // HIGHEST CELL PER HEMISPHERE // NOT LOCAL VISIBILITY"
                font.pixelSize: 10
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR // GOES X-RAY FLARES"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 14

                Rectangle {
                    width: 235
                    height: 125
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "LATEST DETECTED // PEAK"
                        font.pixelSize: 11
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 30
                        text: flareService.ready && flareService.latest
                              ? flareService.latest.classLabel : "--"
                        font.pixelSize: 36
                        color: flareService.ready && flareService.latest
                               ? space.flareClassColor(flareService.latest.classLetter)
                               : Colors.white
                    }

                    QuietText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 10
                        text: flareService.ready && flareService.latest
                              ? flareService.latest.peakUtc : "PEAK TIME --"
                        font.pixelSize: 10
                    }
                }

                Rectangle {
                    width: 235
                    height: 125
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "OBSERVED // LAST 24H"
                        font.pixelSize: 11
                    }

                    Row {
                        anchors.top: parent.top
                        anchors.topMargin: 36
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 14

                        Column {
                            spacing: 6

                            GohuText {
                                text: flareService.ready
                                      ? String(flareService.count24h) : "--"
                                font.pixelSize: 30
                                color: Colors.cyan
                            }

                            QuietText {
                                text: "ALL"
                                font.pixelSize: 10
                            }
                        }

                        Column {
                            spacing: 6

                            GohuText {
                                text: flareService.ready
                                      ? String(flareService.cPlus24h) : "--"
                                font.pixelSize: 30
                                color: Colors.yellow
                            }

                            QuietText {
                                text: "C / M / X"
                                font.pixelSize: 10
                            }
                        }
                    }
                }

                Column {
                    width: Math.max(0, parent.width - 470 - 2 * parent.spacing)
                    spacing: 8

                    SecondaryText {
                        text: "EVENT FEED // NOAA GOES"
                        font.pixelSize: 11
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: flareService.failed
                              ? (flareService.ready
                                 ? "REQUEST FAILED // SAVED EVENTS"
                                 : "REQUEST FAILED // NO DATA")
                              : flareService.loading && !flareService.ready
                                ? "RECEIVING"
                                : flareService.ready ? "EVENTS RECEIVED"
                                  : "UNAVAILABLE"
                        font.pixelSize: 12
                        color: flareService.failed ? Colors.orange
                               : flareService.ready ? Colors.cyan : Colors.white
                    }

                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: flareService.ready
                              ? "FETCHED "
                                + Qt.formatDateTime(flareService.lastUpdated, "hh:mm")
                                + " LOCAL"
                              : "--"
                        font.pixelSize: 10
                    }

                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: "EVENT PEAKS // NOT LIVE X-RAY FLUX"
                        font.pixelSize: 10
                    }
                }
            }

            Row {
                id: flareEventRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: flareService.ready ? flareService.events : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (flareEventRow.width
                                            - 2 * flareEventRow.spacing) / 3)
                        height: 102
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 5

                            Row {
                                spacing: 10

                                GohuText {
                                    text: modelData.classLabel
                                    font.pixelSize: 21
                                    color: space.flareClassColor(modelData.classLetter)
                                }

                                QuietText {
                                    text: modelData.satellite
                                    font.pixelSize: 10
                                }
                            }

                            GohuText {
                                text: "PEAK " + modelData.peakUtc
                                font.pixelSize: 11
                                color: Colors.white
                            }

                            QuietText {
                                text: modelData.ended ? "END REPORTED" : "END NOT REPORTED"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !flareService.ready || flareService.events.length === 0
                text: flareService.failed ? flareService.errorText
                      : flareService.loading ? "LOADING GOES EVENTS"
                      : flareService.ready ? "NO VALID FLARE PEAKS IN 7-DAY FEED"
                        : "GOES DATA UNAVAILABLE"
                font.pixelSize: 11
            }

            QuietText {
                width: parent.width
                text: "GOES XRS // LAST 7D EVENTS // OBSERVATIONS, NOT ALERTS OR PREDICTIONS"
                font.pixelSize: 10
            }
        }

        QuietText {
            text: "NOAA SWPC // FOUR LIVE PRODUCTS // INDEPENDENT SAMPLE TIMES"
            font.pixelSize: 11
        }
        }
    }

    NeonScrollBar {
        flickable: spaceScroll
        handleStyle: "star"
        geometryHost: space
        visible: scrollable
    }
}
