import QtQuick
import "../../components"

Rectangle {
    id: space

    property var spaceService: null

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
    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

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

        QuietText {
            text: "NOAA SWPC // FOUR LIVE PRODUCTS // INDEPENDENT SAMPLE TIMES"
            font.pixelSize: 11
        }
    }
}
