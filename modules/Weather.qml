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

                // Both bulb contours share one center. Native circular
                // arcs avoid the flattened bottom and uneven liquid-to-glass
                // gap from separately approximated Bezier bulbs.
                readonly property real bulbCenterX: width / 2
                readonly property real bulbCenterY: 26.6
                readonly property real outerBulbRadius: 6.75
                readonly property real innerBulbRadius: 4.4
                readonly property real joinDiagonal: Math.SQRT1_2
                readonly property real outerRightJoinX:
                    bulbCenterX + outerBulbRadius * joinDiagonal
                readonly property real outerLeftJoinX:
                    bulbCenterX - outerBulbRadius * joinDiagonal
                readonly property real outerJoinY:
                    bulbCenterY - outerBulbRadius * joinDiagonal
                readonly property real innerRightJoinX:
                    bulbCenterX + innerBulbRadius * joinDiagonal
                readonly property real innerLeftJoinX:
                    bulbCenterX - innerBulbRadius * joinDiagonal
                readonly property real innerJoinY:
                    bulbCenterY - innerBulbRadius * joinDiagonal

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

                // Glass vessel: the bulb's lower 270 degrees use exact
                // circular arcs shared by the black body and outline.
                Shape {
                    anchors.fill: parent

                    ShapePath {
                        strokeWidth: 0
                        strokeColor: "transparent"
                        fillColor: Colors.black

                        startX: weatherThermometer.bulbCenterX
                        startY: 1.2

                        PathQuad {
                            x: 12.2
                            y: 5.2
                            controlX: 12.2
                            controlY: 1.2
                        }
                        PathLine { x: 12.2; y: 19.8 }
                        // Smoothly enter the circular bulb at 45 degrees.
                        PathCubic {
                            x: weatherThermometer.outerRightJoinX
                            y: weatherThermometer.outerJoinY
                            control1X: 12.2
                            control1Y: 20.7
                            control2X: weatherThermometer.outerRightJoinX - 0.75
                            control2Y: weatherThermometer.outerJoinY - 0.75
                        }
                        PathArc {
                            x: weatherThermometer.bulbCenterX
                            y: weatherThermometer.bulbCenterY
                               + weatherThermometer.outerBulbRadius
                            radiusX: weatherThermometer.outerBulbRadius
                            radiusY: weatherThermometer.outerBulbRadius
                            direction: PathArc.Clockwise
                        }
                        PathArc {
                            x: weatherThermometer.outerLeftJoinX
                            y: weatherThermometer.outerJoinY
                            radiusX: weatherThermometer.outerBulbRadius
                            radiusY: weatherThermometer.outerBulbRadius
                            direction: PathArc.Clockwise
                        }
                        PathCubic {
                            x: 4.8
                            y: 19.8
                            control1X: weatherThermometer.outerLeftJoinX + 0.75
                            control1Y: weatherThermometer.outerJoinY - 0.75
                            control2X: 4.8
                            control2Y: 20.7
                        }
                        PathLine { x: 4.8; y: 5.2 }
                        PathQuad {
                            x: weatherThermometer.bulbCenterX
                            y: 1.2
                            controlX: 4.8
                            controlY: 1.2
                        }
                    }
                }

                // Inset fluid bulb uses a concentric circle, providing a
                // constant radial glass-to-liquid clearance all around.
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
                            y2: weatherThermometer.bulbCenterY
                                + weatherThermometer.innerBulbRadius

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

                        startX: weatherThermometer.bulbCenterX
                        startY: 3.2

                        PathQuad {
                            x: 10.1
                            y: 5.2
                            controlX: 10.1
                            controlY: 3.2
                        }
                        PathLine { x: 10.1; y: 21.3 }
                        PathCubic {
                            x: weatherThermometer.innerRightJoinX
                            y: weatherThermometer.innerJoinY
                            control1X: 10.1
                            control1Y: 22.2
                            control2X: weatherThermometer.innerRightJoinX - 0.6
                            control2Y: weatherThermometer.innerJoinY - 0.6
                        }
                        PathArc {
                            x: weatherThermometer.bulbCenterX
                            y: weatherThermometer.bulbCenterY
                               + weatherThermometer.innerBulbRadius
                            radiusX: weatherThermometer.innerBulbRadius
                            radiusY: weatherThermometer.innerBulbRadius
                            direction: PathArc.Clockwise
                        }
                        PathArc {
                            x: weatherThermometer.innerLeftJoinX
                            y: weatherThermometer.innerJoinY
                            radiusX: weatherThermometer.innerBulbRadius
                            radiusY: weatherThermometer.innerBulbRadius
                            direction: PathArc.Clockwise
                        }
                        PathCubic {
                            x: 6.9
                            y: 21.3
                            control1X: weatherThermometer.innerLeftJoinX + 0.6
                            control1Y: weatherThermometer.innerJoinY - 0.6
                            control2X: 6.9
                            control2Y: 22.2
                        }
                        PathLine { x: 6.9; y: 5.2 }
                        PathQuad {
                            x: weatherThermometer.bulbCenterX
                            y: 3.2
                            controlX: 6.9
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

                        startX: weatherThermometer.bulbCenterX
                        startY: 1.2

                        PathQuad {
                            x: 12.2
                            y: 5.2
                            controlX: 12.2
                            controlY: 1.2
                        }
                        PathLine { x: 12.2; y: 19.8 }
                        // Smoothly enter the circular bulb at 45 degrees.
                        PathCubic {
                            x: weatherThermometer.outerRightJoinX
                            y: weatherThermometer.outerJoinY
                            control1X: 12.2
                            control1Y: 20.7
                            control2X: weatherThermometer.outerRightJoinX - 0.75
                            control2Y: weatherThermometer.outerJoinY - 0.75
                        }
                        PathArc {
                            x: weatherThermometer.bulbCenterX
                            y: weatherThermometer.bulbCenterY
                               + weatherThermometer.outerBulbRadius
                            radiusX: weatherThermometer.outerBulbRadius
                            radiusY: weatherThermometer.outerBulbRadius
                            direction: PathArc.Clockwise
                        }
                        PathArc {
                            x: weatherThermometer.outerLeftJoinX
                            y: weatherThermometer.outerJoinY
                            radiusX: weatherThermometer.outerBulbRadius
                            radiusY: weatherThermometer.outerBulbRadius
                            direction: PathArc.Clockwise
                        }
                        PathCubic {
                            x: 4.8
                            y: 19.8
                            control1X: weatherThermometer.outerLeftJoinX + 0.75
                            control1Y: weatherThermometer.outerJoinY - 0.75
                            control2X: 4.8
                            control2Y: 20.7
                        }
                        PathLine { x: 4.8; y: 5.2 }
                        PathQuad {
                            x: weatherThermometer.bulbCenterX
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
