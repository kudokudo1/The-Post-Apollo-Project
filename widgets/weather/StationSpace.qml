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

    color: Colors.black

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 26

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

        Row {
            spacing: 30

            Column {
                width: 150
                spacing: 6

                SecondaryText {
                    text: "KP INDEX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: spaceService ? spaceService.kpText : "--"
                    font.pixelSize: 28
                    color: space.kpColor
                }

                GohuText {
                    text: spaceService ? spaceService.kpLabel : "OFFLINE"
                    font.pixelSize: 11
                    color: space.kpColor
                }

                Rectangle {
                    width: 135
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.kpMeter
                        height: parent.height - 4
                        color: Colors.magenta
                    }
                }
            }

            Column {
                width: 165
                spacing: 6

                SecondaryText {
                    text: "SOLAR WIND"
                    font.pixelSize: 11
                }

                GohuText {
                    text: spaceService
                          ? spaceService.solarWindText : "-- KM/S"
                    font.pixelSize: 19
                    color: space.solarWindColor
                }

                Rectangle {
                    width: 135
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.solarWindMeter
                        height: parent.height - 4
                        color: Colors.magenta
                    }
                }
            }

            Column {
                width: 170
                spacing: 6

                SecondaryText {
                    text: "IMF BZ"
                    font.pixelSize: 11
                }

                GohuText {
                    text: spaceService ? spaceService.bzText : "-- nT"
                    font.pixelSize: 19
                    color: space.bzColor
                }

                GohuText {
                    text: spaceService ? spaceService.bzLabel : "OFFLINE"
                    font.pixelSize: 10
                    color: space.bzColor
                }

                Rectangle {
                    width: 145
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.bzMeter
                        height: parent.height - 4
                        color: Colors.magenta
                    }
                }
            }

            Column {
                width: 170
                spacing: 6

                SecondaryText {
                    text: "F10.7 FLUX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: spaceService
                          ? spaceService.solarFluxText : "-- SFU"
                    font.pixelSize: 19
                    color: Colors.white
                }

                Rectangle {
                    width: 135
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.solarFluxMeter
                        height: parent.height - 4
                        color: Colors.magenta
                    }
                }
            }
        }

        QuietText {
            text: "solar / geomagnetic / astronomy / orbital"
            font.pixelSize: 13
        }
    }
}
