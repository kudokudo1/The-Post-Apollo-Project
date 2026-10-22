import QtQuick
import QtQuick.Shapes
import Quickshell
import "../components"
import "../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy

DockButton {
    id: weatherDock

    property var weatherStationWindow: null
    property var weatherService: null
    // Right-click toggles the displayed unit while this Quickshell session runs.
    property bool useCelsius: false
    property real observationClockMs: Date.now()

    readonly property bool menuOpen:
        weatherStationWindow && weatherStationWindow.menuOpen

    readonly property real weatherTimeMs:
        weatherService && weatherService.lastUpdated
        ? weatherService.lastUpdated.getTime() : 0
    readonly property real aqiTimeMs:
        weatherService && weatherService.aqiLastUpdated
        ? weatherService.aqiLastUpdated.getTime() : 0

    readonly property bool weatherFresh:
        weatherService && weatherService.ready && !weatherService.errorText
        && WeatherDockPolicy.fresh(weatherTimeMs, observationClockMs)

    readonly property var weatherState: WeatherDockPolicy.classify({
        "nowMs": observationClockMs,
        "ready": weatherService ? weatherService.ready : false,
        "errorText": weatherService ? weatherService.errorText : "",
        "weatherTimeMs": weatherTimeMs,
        "weatherCode": weatherService ? weatherService.weatherCode : "",
        "condition": weatherService ? weatherService.condition : "",
        "windMph": weatherService ? weatherService.windMph : "",
        "uvIndex": weatherService ? weatherService.uvIndex : -1,
        "aqiReady": weatherService ? weatherService.aqiReady : false,
        "aqiErrorText": weatherService ? weatherService.aqiErrorText : "",
        "aqiTimeMs": aqiTimeMs,
        "aqi": weatherService ? weatherService.aqi : -1
    })

    readonly property color weatherColor: {
        switch (weatherState.color) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "green": return Colors.green;
        case "omnitrix": return Colors.omnitrix;
        case "cyan": return Colors.cyan;
        case "blue": return Colors.blue;
        case "magenta": return Colors.magenta;
        default: return Colors.white;
        }
    }

    readonly property string temperatureLabel:
        WeatherDockPolicy.formatTemperature(
            weatherService ? weatherService.tempF : "",
            weatherFresh,
            useCelsius
        )

    // Temperature-state colors are distinct from weather-condition colors.
    // Use the shared Fahrenheit reading regardless of the unit shown on screen.
    readonly property var thermometerState: WeatherDockPolicy.temperatureState(
        weatherService ? weatherService.tempF : "",
        weatherFresh
    )

    readonly property color thermometerLiquidColor: {
        if (!thermometerState.valid)
            return "transparent";
        if (weatherDock.open)
            return Colors.magenta;
        switch (thermometerState.color) {
        case "white": return Colors.white;
        case "cyan": return Colors.cyan;
        case "blue": return Colors.blue;
        case "magenta": return Colors.magenta;
        case "yellow": return Colors.yellow;
        case "orange": return Colors.orange;
        case "red": return Colors.red;
        default: return Colors.white;
        }
    }

    implicitHeight: 50
    // Precisely fit the visible content with 3px left and right padding.
    // This width follows temperature digits, units, and condition glyph changes.
    implicitWidth: Math.ceil(weatherContent.implicitWidth) + 6

    open: menuOpen
    // Follow the shared dock recipe: yellow open fill, magenta opened mark/glow.
    openFillColor: Colors.yellow

    normalForegroundColor: weatherColor
    hoverForegroundColor: Colors.orange
    // Pressing keeps each icon's semantic foreground; only the glow pulses magenta.
    pressedForegroundColor: weatherColor
    openForegroundColor: Colors.magenta

    normalContentGlowColor: weatherColor
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta
    openGlowColor: Colors.magenta

    normalDockGlowColor: weatherColor
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    contentGlowSource: weatherContent
    trackArtworkGlowLocally: true

    Timer {
        interval: 60000
        repeat: true
        running: true
        // Invalid cached readings age out even if the network is down.
        onTriggered: weatherDock.observationClockMs = Date.now()
    }

    // Condition -> measured temperature -> active thermometer.
    // The former +2px correction compensated for an emoji's font bearings.
    // The drawn gauge has explicit geometry; center the whole group evenly.
    Row {
        id: weatherContent
        anchors.centerIn: parent
        spacing: 6

        Item {
            id: weatherConditionSlot
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: Math.ceil(weatherCondition.implicitWidth)
            implicitHeight: 46

            Text {
                id: weatherCondition
                anchors.centerIn: parent
                text: weatherDock.weatherState.icon
                font.pixelSize: 42
                color: weatherDock.foregroundColor
            }
        }

        // Keep the icon-to-data gap at 6px; close only the readout-to-🌡 gap.
        Row {
            id: weatherReadout
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            Row {
                id: weatherTemperature
                anchors.verticalCenter: parent.verticalCenter
                spacing: 0

                GohuText {
                    id: weatherTemperatureValue
                    anchors.verticalCenter: parent.verticalCenter
                    text: weatherDock.temperatureLabel.slice(0, -2)
                    font.pixelSize: 20
                    color: weatherDock.foregroundColor
                }

                Item {
                    id: degreeSlot
                    anchors.verticalCenter: parent.verticalCenter
                    implicitWidth: weatherDegree.implicitWidth
                    implicitHeight: weatherDegree.implicitHeight

                    SafeDropShadow {
                        anchors.fill: weatherDegree
                        safeSource: weatherDegree
                        requestedVisible: true
                        z: -1
                        radius: 8
                        samples: 15
                        horizontalOffset: 0
                        verticalOffset: 0
                        transparentBorder: true
                        opacity: weatherDock.contentGlowOpacity
                        color: weatherDock.open || weatherDock.pressed
                               ? Colors.magenta : Colors.orange
                    }

                    GohuText {
                        id: weatherDegree
                        text: "°"
                        font.pixelSize: 20
                        color: weatherDock.open ? Colors.magenta
                               : weatherDock.pressed ? Colors.white
                               : weatherDock.hovered ? Colors.orange : Colors.white
                    }
                }

                GohuText {
                    id: weatherTemperatureUnit
                    anchors.verticalCenter: parent.verticalCenter
                    text: weatherDock.temperatureLabel.slice(-1)
                    font.pixelSize: 20
                    color: weatherDock.foregroundColor
                }
            }

            // Compact native scene-graph thermometer: one smooth connected
            // tube and circular bulb. Original 20×42 scaled to 17×35.
            Item {
                id: weatherThermometer
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 17
                implicitHeight: 35
                width: implicitWidth
                height: implicitHeight

                property color liquidColor: weatherDock.thermometerLiquidColor
                property real animatedLevel:
                    weatherDock.thermometerState.valid
                    ? weatherDock.thermometerState.level : 0

                readonly property color glassColor: Colors.white
                readonly property real glassOpacity: 1.0
                readonly property real fillStart:
                    Math.max(0, Math.min(1, 1 - animatedLevel))

                Behavior on animatedLevel {
                    NumberAnimation {
                        duration: 300
                        easing.type: Easing.InOutQuad
                    }
                }

                Behavior on liquidColor {
                    ColorAnimation { duration: 300 }
                }

                // Single connected vessel silhouette. The matching outline
                // below uses identical geometry and rounded stroke joins.
                Shape {
                    anchors.fill: parent

                    ShapePath {
                        strokeWidth: 0
                        strokeColor: "transparent"
                        fillColor: Colors.black

                        startX: 8.5
                        startY: 1.2

                        PathQuad {
                            x: 12.2
                            y: 5.2
                            controlX: 12.2
                            controlY: 1.2
                        }
                        PathLine { x: 12.2; y: 21.5 }
                        // Shoulders meet the round bulb tangentially rather
                        // than forming a sharp corner at the tube junction.
                        PathCubic {
                            x: 14.2
                            y: 24.3
                            control1X: 12.2
                            control1Y: 23.0
                            control2X: 13.5
                            control2Y: 23.0
                        }
                        PathCubic {
                            x: 8.5
                            y: 33.8
                            control1X: 18.0
                            control1Y: 28.2
                            control2X: 14.8
                            control2Y: 33.8
                        }
                        PathCubic {
                            x: 2.8
                            y: 24.3
                            control1X: 2.2
                            control1Y: 33.8
                            control2X: -1.0
                            control2Y: 28.2
                        }
                        PathCubic {
                            x: 4.8
                            y: 21.5
                            control1X: 3.5
                            control1Y: 23.0
                            control2X: 4.8
                            control2Y: 23.0
                        }
                        PathLine { x: 4.8; y: 5.2 }
                        PathQuad {
                            x: 8.5
                            y: 1.2
                            controlX: 4.8
                            controlY: 1.2
                        }
                    }
                }

                // Same joined fluid silhouette, inset inside the glass.
                // A moving gradient stop drains through bulb and tube.
                Shape {
                    anchors.fill: parent
                    visible: weatherThermometer.animatedLevel > 0

                    ShapePath {
                        strokeWidth: 0
                        strokeColor: "transparent"

                        fillGradient: LinearGradient {
                            x1: 0
                            y1: 3.2
                            x2: 0
                            y2: 31.8

                            GradientStop {
                                position: 0
                                color: "transparent"
                            }
                            GradientStop {
                                position: Math.max(
                                    0,
                                    weatherThermometer.fillStart - 0.002
                                )
                                color: "transparent"
                            }
                            GradientStop {
                                position: weatherThermometer.fillStart
                                color: weatherThermometer.liquidColor
                            }
                            GradientStop {
                                position: 1
                                color: weatherThermometer.liquidColor
                            }
                        }

                        startX: 8.5
                        startY: 3.2

                        PathQuad {
                            x: 10.4
                            y: 5.2
                            controlX: 10.4
                            controlY: 3.2
                        }
                        PathLine { x: 10.4; y: 22.3 }
                        PathCubic {
                            x: 12.5
                            y: 25.0
                            control1X: 10.4
                            control1Y: 23.6
                            control2X: 11.9
                            control2Y: 23.8
                        }
                        PathCubic {
                            x: 8.5
                            y: 31.8
                            control1X: 15.9
                            control1Y: 27.8
                            control2X: 12.9
                            control2Y: 31.8
                        }
                        PathCubic {
                            x: 4.5
                            y: 25.0
                            control1X: 4.1
                            control1Y: 31.8
                            control2X: 1.1
                            control2Y: 27.8
                        }
                        PathCubic {
                            x: 6.6
                            y: 22.3
                            control1X: 5.1
                            control1Y: 23.8
                            control2X: 6.6
                            control2Y: 23.6
                        }
                        PathLine { x: 6.6; y: 5.2 }
                        PathQuad {
                            x: 8.5
                            y: 3.2
                            controlX: 6.6
                            controlY: 3.2
                        }
                    }
                }

                // The white glass stays on top of the animated liquid.
                Shape {
                    anchors.fill: parent
                    opacity: weatherThermometer.glassOpacity

                    ShapePath {
                        strokeWidth: 1.5
                        strokeColor: weatherThermometer.glassColor
                        joinStyle: ShapePath.RoundJoin
                        capStyle: ShapePath.RoundCap
                        fillColor: "transparent"

                        startX: 8.5
                        startY: 1.2

                        PathQuad {
                            x: 12.2
                            y: 5.2
                            controlX: 12.2
                            controlY: 1.2
                        }
                        PathLine { x: 12.2; y: 21.5 }
                        // Shoulders meet the round bulb tangentially rather
                        // than forming a sharp corner at the tube junction.
                        PathCubic {
                            x: 14.2
                            y: 24.3
                            control1X: 12.2
                            control1Y: 23.0
                            control2X: 13.5
                            control2Y: 23.0
                        }
                        PathCubic {
                            x: 8.5
                            y: 33.8
                            control1X: 18.0
                            control1Y: 28.2
                            control2X: 14.8
                            control2Y: 33.8
                        }
                        PathCubic {
                            x: 2.8
                            y: 24.3
                            control1X: 2.2
                            control1Y: 33.8
                            control2X: -1.0
                            control2Y: 28.2
                        }
                        PathCubic {
                            x: 4.8
                            y: 21.5
                            control1X: 3.5
                            control1Y: 23.0
                            control2X: 4.8
                            control2Y: 23.0
                        }
                        PathLine { x: 4.8; y: 5.2 }
                        PathQuad {
                            x: 8.5
                            y: 1.2
                            controlX: 4.8
                            controlY: 1.2
                        }
                    }
                }

                // Compact white scale ticks share the glass opacity.
                Repeater {
                    model: 4

                    delegate: Rectangle {
                        x: index % 2 === 0 ? 7.5 : 8
                        y: 6 + index * 5.2
                        width: index % 2 === 0 ? 3 : 2
                        height: 1
                        color: weatherThermometer.glassColor
                        opacity: weatherThermometer.glassOpacity
                    }
                }
            }
        }
    }

    onRightClicked: {
        useCelsius = !useCelsius;
    }

    onLeftClicked: {
        if (weatherStationWindow)
            weatherStationWindow.toggle();
    }
}
