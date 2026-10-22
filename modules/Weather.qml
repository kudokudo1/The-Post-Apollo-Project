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

            // Native scene-graph thermometer. Canvas proved unreliable in
            // this dock path at runtime, so draw the same connected tube+bulb
            // silhouette with Qt Quick Shapes instead.
            Item {
                id: weatherThermometer
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 20
                implicitHeight: 42
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

                // Black vessel body. The narrow tube flares directly into the
                // wider bulb, so the silhouette is one connected unit.
                Shape {
                    anchors.fill: parent

                    ShapePath {
                        strokeWidth: 0
                        strokeColor: "transparent"
                        fillColor: Colors.black

                        startX: 10
                        startY: 1

                        PathQuad {
                            x: 15
                            y: 6
                            controlX: 15
                            controlY: 1
                        }
                        PathLine { x: 15; y: 24 }
                        PathQuad {
                            x: 18
                            y: 28
                            controlX: 15
                            controlY: 27
                        }
                        PathCubic {
                            x: 10
                            y: 41
                            control1X: 18
                            control1Y: 33
                            control2X: 17
                            control2Y: 39
                        }
                        PathCubic {
                            x: 2
                            y: 28
                            control1X: 3
                            control1Y: 39
                            control2X: 2
                            control2Y: 33
                        }
                        PathQuad {
                            x: 5
                            y: 24
                            controlX: 5
                            controlY: 27
                        }
                        PathLine { x: 5; y: 6 }
                        PathQuad {
                            x: 10
                            y: 1
                            controlX: 5
                            controlY: 1
                        }
                    }
                }

                // Real temperature liquid. This uses the same connected inner
                // tube+bulb path and a hard vertical fill boundary, so the bulb
                // fills first and the same body continues upward through the stem.
                Shape {
                    anchors.fill: parent
                    visible: weatherThermometer.animatedLevel > 0

                    ShapePath {
                        strokeWidth: 0
                        strokeColor: "transparent"

                        fillGradient: LinearGradient {
                            x1: 0
                            y1: 3
                            x2: 0
                            y2: 39

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

                        startX: 10
                        startY: 3

                        PathQuad {
                            x: 13
                            y: 6
                            controlX: 13
                            controlY: 3
                        }
                        PathLine { x: 13; y: 25 }
                        PathQuad {
                            x: 15.5
                            y: 28
                            controlX: 13
                            controlY: 27
                        }
                        PathCubic {
                            x: 10
                            y: 39
                            control1X: 15.5
                            control1Y: 32
                            control2X: 15
                            control2Y: 37
                        }
                        PathCubic {
                            x: 4.5
                            y: 28
                            control1X: 5
                            control1Y: 37
                            control2X: 4.5
                            control2Y: 32
                        }
                        PathQuad {
                            x: 7
                            y: 25
                            controlX: 7
                            controlY: 27
                        }
                        PathLine { x: 7; y: 6 }
                        PathQuad {
                            x: 10
                            y: 3
                            controlX: 7
                            controlY: 3
                        }
                    }
                }

                // White glass outline, drawn last so the liquid never obscures it.
                Shape {
                    anchors.fill: parent
                    opacity: weatherThermometer.glassOpacity

                    ShapePath {
                        strokeWidth: 2
                        strokeColor: weatherThermometer.glassColor
                        fillColor: "transparent"

                        startX: 10
                        startY: 1

                        PathQuad {
                            x: 15
                            y: 6
                            controlX: 15
                            controlY: 1
                        }
                        PathLine { x: 15; y: 24 }
                        PathQuad {
                            x: 18
                            y: 28
                            controlX: 15
                            controlY: 27
                        }
                        PathCubic {
                            x: 10
                            y: 41
                            control1X: 18
                            control1Y: 33
                            control2X: 17
                            control2Y: 39
                        }
                        PathCubic {
                            x: 2
                            y: 28
                            control1X: 3
                            control1Y: 39
                            control2X: 2
                            control2Y: 33
                        }
                        PathQuad {
                            x: 5
                            y: 24
                            controlX: 5
                            controlY: 27
                        }
                        PathLine { x: 5; y: 6 }
                        PathQuad {
                            x: 10
                            y: 1
                            controlX: 5
                            controlY: 1
                        }
                    }
                }

                // Indicator marks are ordinary QML rectangles now, so their
                // visibility is independent of the shape renderer. They share
                // exactly the same glass color and opacity.
                Repeater {
                    model: 4

                    delegate: Rectangle {
                        x: index % 2 === 0 ? 9 : 10
                        y: 7 + index * 6
                        width: index % 2 === 0 ? 3.5 : 2.5
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
