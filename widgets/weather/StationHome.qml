import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

Rectangle {
    id: home

    // ─────────────────────────────────────────────
    // EXTERNAL STATE
    // ─────────────────────────────────────────────

    property string activeDomain: "sky"

    property var weatherService: null
    property var spaceService: null

    signal domainRequested(string domain)

    color: Colors.black

    // ─────────────────────────────────────────────
    // SERVICE STATE
    // ─────────────────────────────────────────────

    readonly property bool weatherReady: weatherService && weatherService.ready

    readonly property bool weatherLoading: weatherService && weatherService.loading

    readonly property bool aqiReady: weatherService && weatherService.aqiReady

    readonly property bool aqiLoading: weatherService && weatherService.aqiLoading

    readonly property bool spaceReady: spaceService && spaceService.ready

    readonly property bool spaceLoading: spaceService && spaceService.loading

    // ─────────────────────────────────────────────
    // WEATHER RAW VALUES
    // ─────────────────────────────────────────────

    readonly property real temperatureValue: weatherReady ? Number(weatherService.tempF) : 0

    readonly property real humidityValue: weatherReady ? Number(weatherService.humidity) : 0

    readonly property real windValue: weatherReady ? Number(weatherService.windMph) : 0

    readonly property real aqiValue: aqiReady ? Number(weatherService.aqi) : 0

    readonly property real pm25Value: aqiReady ? Number(weatherService.pm25) : 0

    readonly property real pm10Value: aqiReady ? Number(weatherService.pm10) : 0

    // ─────────────────────────────────────────────
    // SPACE RAW VALUES
    // ─────────────────────────────────────────────

    readonly property real kpValue: spaceService && spaceService.kp >= 0 ? Number(spaceService.kp) : 0

    readonly property real solarWindValue: spaceService && spaceService.solarWindSpeed >= 0 ? Number(spaceService.solarWindSpeed) : 0

    readonly property real bzValue: spaceService && spaceService.magneticFieldReady ? Number(spaceService.magneticFieldBz) : 0

    readonly property real solarFluxValue: spaceService && spaceService.solarFlux >= 0 ? Number(spaceService.solarFlux) : 0

    // ─────────────────────────────────────────────
    // SKY TEXT
    // ─────────────────────────────────────────────

    readonly property string temperatureText: weatherReady ? weatherService.tempF + "°F" : "--°F"

    readonly property string feelsLikeText: weatherReady ? "FEELS " + weatherService.feelsLikeF + "°F" : "FEELS --°F"

    readonly property string conditionText: weatherReady && weatherService.condition ? weatherService.condition.toUpperCase() : weatherLoading ? "RECEIVING..." : "DATA OFFLINE"

    readonly property string humidityText: weatherReady ? weatherService.humidity + "%" : "--%"

    readonly property string windDirectionText: weatherReady && weatherService.windDirection ? weatherService.windDirection : "--"

    readonly property string windText: weatherReady ? weatherService.windDirection + "  " + weatherService.windMph + " MPH" : "--  -- MPH"

    // ─────────────────────────────────────────────
    // GROUND TEXT
    // ─────────────────────────────────────────────

    readonly property string aqiText: aqiReady ? String(weatherService.aqi) : aqiLoading ? "..." : "--"

    readonly property string aqiLabel: aqiReady ? weatherService.aqiLabel : aqiLoading ? "RECEIVING" : "OFFLINE"

    readonly property string pm25Text: aqiReady ? Number(weatherService.pm25).toFixed(1) : "--"

    readonly property string pm10Text: aqiReady ? Number(weatherService.pm10).toFixed(1) : "--"

    readonly property string latitudeText: weatherService && weatherService.latitude !== "" ? weatherService.latitude : "--"

    readonly property string longitudeText: weatherService && weatherService.longitude !== "" ? weatherService.longitude : "--"

    // ─────────────────────────────────────────────
    // SPACE TEXT
    // ─────────────────────────────────────────────

    readonly property string kpText: spaceService ? spaceService.kpText : "--"

    readonly property string kpLabel: spaceService ? spaceService.kpLabel : "OFFLINE"

    readonly property string solarWindText: spaceService ? spaceService.solarWindText : "-- KM/S"

    readonly property string bzText: spaceService ? spaceService.bzText : "-- nT"

    readonly property string bzLabel: spaceService ? spaceService.bzLabel : "OFFLINE"

    readonly property string solarFluxText: spaceService ? spaceService.solarFluxText : "-- SFU"

    // ─────────────────────────────────────────────
    // WEATHER METERS
    // ─────────────────────────────────────────────

    readonly property real temperatureMeter: {
        let value = temperatureValue / 120;
        return Math.max(0, Math.min(1, value));
    }

    readonly property real humidityMeter: Math.max(0, Math.min(1, humidityValue / 100))

    readonly property real windMeter: Math.max(0, Math.min(1, windValue / 50))

    readonly property real aqiMeter: Math.max(0, Math.min(1, aqiValue / 500))

    readonly property real pm25Meter: Math.max(0, Math.min(1, pm25Value / 100))

    readonly property real pm10Meter: Math.max(0, Math.min(1, pm10Value / 150))

    // ─────────────────────────────────────────────
    // SPACE METERS
    // ─────────────────────────────────────────────

    readonly property real kpMeter: Math.max(0, Math.min(1, kpValue / 9))

    readonly property real solarWindMeter: Math.max(0, Math.min(1, solarWindValue / 1000))

    readonly property real bzMeter: Math.max(0, Math.min(1, Math.abs(bzValue) / 20))

    readonly property real solarFluxMeter: Math.max(0, Math.min(1, solarFluxValue / 300))

    // ─────────────────────────────────────────────
    // COLORS
    // ─────────────────────────────────────────────

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

    // ─────────────────────────────────────────────
    // CONDITION ICON
    // ─────────────────────────────────────────────

    readonly property string conditionIcon: iconForCondition(conditionText)

    function iconForCondition(condition) {
        const value = String(condition).toLowerCase();

        if (value.includes("thunder"))
            return "⛈";

        if (value.includes("snow") || value.includes("blizzard") || value.includes("sleet") || value.includes("ice")) {
            return "❄";
        }

        if (value.includes("rain") || value.includes("drizzle") || value.includes("shower")) {
            return "🌧";
        }

        if (value.includes("fog") || value.includes("mist")) {
            return "≋";
        }

        if (value.includes("cloud") || value.includes("overcast")) {
            return "☁";
        }

        if (value.includes("sun") || value.includes("clear")) {
            return "☀";
        }

        return "◌";
    }

    // ─────────────────────────────────────────────
    // WIND ANGLE
    // ─────────────────────────────────────────────

    function windAngle(direction) {
        switch (direction) {
        case "N":
            return 0;
        case "NNE":
            return 22.5;
        case "NE":
            return 45;
        case "ENE":
            return 67.5;
        case "E":
            return 90;
        case "ESE":
            return 112.5;
        case "SE":
            return 135;
        case "SSE":
            return 157.5;
        case "S":
            return 180;
        case "SSW":
            return 202.5;
        case "SW":
            return 225;
        case "WSW":
            return 247.5;
        case "W":
            return 270;
        case "WNW":
            return 292.5;
        case "NW":
            return 315;
        case "NNW":
            return 337.5;
        default:
            return 0;
        }
    }

    // ─────────────────────────────────────────────
    // DOMAIN STACK
    // ─────────────────────────────────────────────

    Column {
        id: domainStack

        anchors.fill: parent

        anchors.topMargin: 20
        anchors.bottomMargin: 20
        anchors.leftMargin: 22
        anchors.rightMargin: 22

        spacing: 12

        // ═════════════════════════════════════════
        // SPACE
        // ═════════════════════════════════════════

        Rectangle {
            id: spaceBand

            width: domainStack.width

            height: (domainStack.height - domainStack.spacing * 2) / 3

            color: Colors.black

            readonly property bool selected: home.activeDomain === "space"

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom

                width: 3

                color: spaceBand.selected ? Colors.orange : spaceMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            Text {
                id: spaceTitle

                anchors.left: parent.left
                anchors.top: parent.top

                anchors.leftMargin: 18
                anchors.topMargin: 8

                text: "✦  SPACE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: spaceBand.selected ? Colors.orange : spaceMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            Text {
                anchors.right: parent.right
                anchors.top: parent.top

                anchors.rightMargin: 18
                anchors.topMargin: 10

                text: home.spaceReady ? "SPACE WEATHER ONLINE" : home.spaceLoading ? "RECEIVING" : "OFFLINE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 12

                color: home.spaceReady ? Colors.cyan : Colors.orange
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: spaceTitle.bottom

                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.topMargin: 6

                spacing: 30

                height: 95

                // ─────────────────────────────────
                // KP INDEX
                // ─────────────────────────────────

                Column {
                    width: 150

                    spacing: 2

                    Text {
                        text: "KP INDEX"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Row {
                        spacing: 7

                        Text {
                            text: home.kpText

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 22

                            color: home.kpColor
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter

                            text: home.kpLabel

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 11

                            color: home.kpColor
                        }
                    }

                    Rectangle {
                        width: 135
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.kpMeter

                            height: parent.height - 4

                            color: home.kpColor
                        }
                    }
                }

                // ─────────────────────────────────
                // SOLAR WIND
                // ─────────────────────────────────

                Column {
                    width: 150

                    spacing: 3

                    Text {
                        text: "SOLAR WIND"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.solarWindText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 16

                        color: home.solarWindColor
                    }

                    Rectangle {
                        width: 135
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.solarWindMeter

                            height: parent.height - 4

                            color: home.solarWindColor
                        }
                    }
                }

                // ─────────────────────────────────
                // IMF BZ
                // ─────────────────────────────────

                Column {
                    width: 170

                    spacing: 2

                    Text {
                        text: "IMF BZ"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.bzText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 16

                        color: home.bzColor
                    }

                    Text {
                        text: home.bzLabel

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 10

                        color: home.bzColor
                    }

                    Rectangle {
                        width: 145
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.bzMeter

                            height: parent.height - 4

                            color: home.bzColor
                        }
                    }
                }

                // ─────────────────────────────────
                // F10.7 SOLAR FLUX
                // ─────────────────────────────────

                Column {
                    width: 155

                    spacing: 3

                    Text {
                        text: "F10.7 FLUX"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.solarFluxText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 16

                        color: Colors.white
                    }

                    Rectangle {
                        width: 135
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.solarFluxMeter

                            height: parent.height - 4

                            color: Colors.cyan
                        }
                    }
                }
            }

            Text {
                anchors.left: parent.left
                anchors.bottom: parent.bottom

                anchors.leftMargin: 18
                anchors.bottomMargin: 8

                text: "solar / geomagnetic / celestial telemetry"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 13

                color: Colors.white
            }

            MouseArea {
                id: spaceMouse

                anchors.fill: parent

                hoverEnabled: true

                onClicked: {
                    home.domainRequested("space");
                }
            }

            SafeDropShadow {
                anchors.fill: spaceBand
                safeSource: spaceBand

                z: -1

                color: Colors.orange

                opacity: spaceBand.selected ? 0.28 : spaceMouse.containsMouse ? 0.18 : 0

                horizontalOffset: 0
                verticalOffset: 0

                radius: 16
                samples: 33

                transparentBorder: true
            }
        }

        // ═════════════════════════════════════════
        // SKY
        // ═════════════════════════════════════════

        Rectangle {
            id: skyBand

            width: domainStack.width

            height: (domainStack.height - domainStack.spacing * 2) / 3

            color: Colors.black

            readonly property bool selected: home.activeDomain === "sky"

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom

                width: 3

                color: skyBand.selected ? Colors.orange : skyMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            Text {
                id: skyTitle

                anchors.left: parent.left
                anchors.top: parent.top

                anchors.leftMargin: 18
                anchors.topMargin: 8

                text: "☁  SKY"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: skyBand.selected ? Colors.orange : skyMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            Text {
                anchors.right: parent.right
                anchors.top: parent.top

                anchors.rightMargin: 18
                anchors.topMargin: 10

                text: home.weatherReady ? "LIVE" : home.weatherLoading ? "RECEIVING" : "OFFLINE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 12

                color: home.weatherReady ? Colors.cyan : Colors.orange
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: skyTitle.bottom

                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.topMargin: 4

                spacing: 14

                height: 105

                // ─────────────────────────────────
                // TEMPERATURE
                // ─────────────────────────────────

                Column {
                    width: 125

                    spacing: 3

                    Text {
                        text: home.temperatureText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 28

                        color: Colors.orange
                    }

                    Text {
                        text: home.feelsLikeText

                        font.family: "GohuFont 11 Nerd Font Mono"

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

                            width: (parent.width - 4) * home.temperatureMeter

                            height: parent.height - 4

                            color: Colors.orange
                        }
                    }
                }

                // ─────────────────────────────────
                // CONDITION
                // ─────────────────────────────────

                Column {
                    width: 190

                    spacing: 2

                    Text {
                        width: parent.width

                        text: "CONDITION"

                        horizontalAlignment: Text.AlignHCenter

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        width: parent.width

                        text: home.conditionText

                        horizontalAlignment: Text.AlignHCenter

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 14

                        color: Colors.orange

                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width

                        text: home.conditionIcon

                        horizontalAlignment: Text.AlignHCenter

                        font.pixelSize: 24

                        color: Colors.cyan
                    }
                }

                // ─────────────────────────────────
                // AIR QUALITY
                // ─────────────────────────────────

                Column {
                    width: 100

                    spacing: 2

                    Text {
                        text: "AIR QUALITY"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.aqiText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 17

                        color: home.aqiColor
                    }

                    Text {
                        text: home.aqiLabel

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 10

                        color: home.aqiColor
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

                            width: (parent.width - 4) * home.aqiMeter

                            height: parent.height - 4

                            color: home.aqiColor
                        }
                    }
                }

                // ─────────────────────────────────
                // HUMIDITY
                // ─────────────────────────────────

                Column {
                    width: 95

                    spacing: 3

                    Text {
                        text: "HUMIDITY"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.humidityText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 17

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

                            width: (parent.width - 4) * home.humidityMeter

                            height: parent.height - 4

                            color: Colors.cyan
                        }
                    }
                }

                // ─────────────────────────────────
                // WIND
                // ─────────────────────────────────

                Row {
                    width: 160

                    spacing: 6

                    Item {
                        width: 36
                        height: 56

                        Text {
                            anchors.centerIn: parent

                            text: "↑"

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 26

                            color: Colors.orange

                            rotation: home.windAngle(home.windDirectionText)
                        }
                    }

                    Column {
                        width: 116

                        spacing: 3

                        Text {
                            text: "WIND"

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 11

                            color: Colors.cyan
                        }

                        Text {
                            text: home.windText

                            font.family: "GohuFont 11 Nerd Font Mono"

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

                                width: (parent.width - 4) * home.windMeter

                                height: parent.height - 4

                                color: Colors.cyan
                            }
                        }
                    }
                }
            }

            Text {
                anchors.left: parent.left
                anchors.bottom: parent.bottom

                anchors.leftMargin: 18
                anchors.bottomMargin: 8

                text: "weather / atmosphere / radar / aviation"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 13

                color: Colors.white
            }

            MouseArea {
                id: skyMouse

                anchors.fill: parent

                hoverEnabled: true

                onClicked: {
                    home.domainRequested("sky");
                }
            }

            SafeDropShadow {
                anchors.fill: skyBand
                safeSource: skyBand

                z: -1

                color: Colors.orange

                opacity: skyBand.selected ? 0.28 : skyMouse.containsMouse ? 0.18 : 0

                horizontalOffset: 0
                verticalOffset: 0

                radius: 16
                samples: 33

                transparentBorder: true
            }
        }

        // ═════════════════════════════════════════
        // GROUND
        // ═════════════════════════════════════════

        Rectangle {
            id: groundBand

            width: domainStack.width

            height: (domainStack.height - domainStack.spacing * 2) / 3

            color: Colors.black

            readonly property bool selected: home.activeDomain === "ground"

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom

                width: 3

                color: groundBand.selected ? Colors.orange : groundMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            Text {
                id: groundTitle

                anchors.left: parent.left
                anchors.top: parent.top

                anchors.leftMargin: 18
                anchors.topMargin: 8

                text: "⌁  GROUND"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: groundBand.selected ? Colors.orange : groundMouse.containsMouse ? Colors.orange : Colors.cyan
            }

            Text {
                anchors.right: parent.right
                anchors.top: parent.top

                anchors.rightMargin: 18
                anchors.topMargin: 10

                text: home.aqiReady ? "ENVIRONMENT ONLINE" : home.aqiLoading ? "RECEIVING" : "OFFLINE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 12

                color: home.aqiReady ? Colors.cyan : Colors.orange
            }

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: groundTitle.bottom

                anchors.leftMargin: 18
                anchors.rightMargin: 18
                anchors.topMargin: 6

                spacing: 28

                height: 95

                // ─────────────────────────────────
                // AIR QUALITY
                // ─────────────────────────────────

                Column {
                    width: 145

                    spacing: 2

                    Text {
                        text: "AIR QUALITY"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Row {
                        spacing: 7

                        Text {
                            text: home.aqiText

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 22

                            color: home.aqiColor
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter

                            text: home.aqiLabel

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: 11

                            color: home.aqiColor
                        }
                    }

                    Rectangle {
                        width: 130
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.aqiMeter

                            height: parent.height - 4

                            color: home.aqiColor
                        }
                    }
                }

                // ─────────────────────────────────
                // PM2.5
                // ─────────────────────────────────

                Column {
                    width: 130

                    spacing: 3

                    Text {
                        text: "PM2.5"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.pm25Text + " µg/m³"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 15

                        color: Colors.white
                    }

                    Rectangle {
                        width: 120
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.pm25Meter

                            height: parent.height - 4

                            color: Colors.cyan
                        }
                    }
                }

                // ─────────────────────────────────
                // PM10
                // ─────────────────────────────────

                Column {
                    width: 130

                    spacing: 3

                    Text {
                        text: "PM10"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: home.pm10Text + " µg/m³"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 15

                        color: Colors.white
                    }

                    Rectangle {
                        width: 120
                        height: 8

                        color: Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            x: 2

                            anchors.verticalCenter: parent.verticalCenter

                            width: (parent.width - 4) * home.pm10Meter

                            height: parent.height - 4

                            color: Colors.cyan
                        }
                    }
                }

                // ─────────────────────────────────
                // POSITION
                // ─────────────────────────────────

                Column {
                    width: 190

                    spacing: 2

                    Text {
                        text: "POSITION"

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 11

                        color: Colors.cyan
                    }

                    Text {
                        text: "LAT  " + home.latitudeText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 13

                        color: Colors.white
                    }

                    Text {
                        text: "LON  " + home.longitudeText

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 13

                        color: Colors.white
                    }
                }
            }

            Text {
                anchors.left: parent.left
                anchors.bottom: parent.bottom

                anchors.leftMargin: 18
                anchors.bottomMargin: 8

                text: "surface / environment / events / infrastructure"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 13

                color: Colors.white
            }

            MouseArea {
                id: groundMouse

                anchors.fill: parent

                hoverEnabled: true

                onClicked: {
                    home.domainRequested("ground");
                }
            }

            SafeDropShadow {
                anchors.fill: groundBand
                safeSource: groundBand

                z: -1

                color: Colors.orange

                opacity: groundBand.selected ? 0.28 : groundMouse.containsMouse ? 0.18 : 0

                horizontalOffset: 0
                verticalOffset: 0

                radius: 16
                samples: 33

                transparentBorder: true
            }
        }
    }
}
