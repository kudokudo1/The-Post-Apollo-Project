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

                // Subpixel smoothing matters at a native size of only 17x35.
                // Sample this tiny native Shape instrument independently,
                // without applying another effect to the surrounding dock.
                layer.enabled: true
                layer.samples: 4
                layer.smooth: true

                // Both outlines share a center and matched ellipse contours.
                // Slightly taller bulbs rasterize into more natural side steps
                // at this scale than a mathematically perfect tiny circle.
                readonly property real bulbCenterX: width / 2
                readonly property real bulbCenterY: 26.0
                readonly property real outerBulbRadiusX: 6.2
                readonly property real outerBulbRadiusY: 7.1
                readonly property real innerBulbRadiusX: 3.65
                readonly property real innerBulbRadiusY: 4.6
                readonly property real joinDiagonal: Math.SQRT1_2
                readonly property real outerRightJoinX:
                    bulbCenterX + outerBulbRadiusX * joinDiagonal
                readonly property real outerLeftJoinX:
                    bulbCenterX - outerBulbRadiusX * joinDiagonal
                readonly property real outerJoinY:
                    bulbCenterY - outerBulbRadiusY * joinDiagonal
                readonly property real innerRightJoinX:
                    bulbCenterX + innerBulbRadiusX * joinDiagonal
                readonly property real innerLeftJoinX:
                    bulbCenterX - innerBulbRadiusX * joinDiagonal
                readonly property real innerJoinY:
                    bulbCenterY - innerBulbRadiusY * joinDiagonal

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

                // Glass vessel. Its bottom arcs use a vertically balanced
                // elliptical silhouette at native dock resolution.
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
                        PathLine { x: 12.2; y: 19.3 }
                        // A mirrored, tangent entry into the bulb avoids
                        // the accidental right-angle raster step.
                        PathCubic {
                            x: weatherThermometer.outerRightJoinX
                            y: weatherThermometer.outerJoinY
                            control1X: 12.2
                            control1Y: 20.0
                            control2X: weatherThermometer.outerRightJoinX - 0.58
                            control2Y: weatherThermometer.outerJoinY - 0.66
                        }
                        PathArc {
                            x: weatherThermometer.bulbCenterX
                            y: weatherThermometer.bulbCenterY
                               + weatherThermometer.outerBulbRadiusY
                            radiusX: weatherThermometer.outerBulbRadiusX
                            radiusY: weatherThermometer.outerBulbRadiusY
                            direction: PathArc.Clockwise
                        }
                        PathArc {
                            x: weatherThermometer.outerLeftJoinX
                            y: weatherThermometer.outerJoinY
                            radiusX: weatherThermometer.outerBulbRadiusX
                            radiusY: weatherThermometer.outerBulbRadiusY
                            direction: PathArc.Clockwise
                        }
                        PathCubic {
                            x: 4.8
                            y: 19.3
                            control1X: weatherThermometer.outerLeftJoinX + 0.58
                            control1Y: weatherThermometer.outerJoinY - 0.66
                            control2X: 4.8
                            control2Y: 20.0
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

                // The inner ellipse is centered with the glass and slightly
                // narrower, keeping both side voids and bottom clearance even.
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
                                + weatherThermometer.innerBulbRadiusY

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
                            x: 9.75
                            y: 5.2
                            controlX: 9.75
                            controlY: 3.2
                        }
                        PathLine { x: 9.75; y: 21.6 }
                        PathCubic {
                            x: weatherThermometer.innerRightJoinX
                            y: weatherThermometer.innerJoinY
                            control1X: 9.75
                            control1Y: 22.15
                            control2X: weatherThermometer.innerRightJoinX - 0.55
                            control2Y: weatherThermometer.innerJoinY - 0.62
                        }
                        PathArc {
                            x: weatherThermometer.bulbCenterX
                            y: weatherThermometer.bulbCenterY
                               + weatherThermometer.innerBulbRadiusY
                            radiusX: weatherThermometer.innerBulbRadiusX
                            radiusY: weatherThermometer.innerBulbRadiusY
                            direction: PathArc.Clockwise
                        }
                        PathArc {
                            x: weatherThermometer.innerLeftJoinX
                            y: weatherThermometer.innerJoinY
                            radiusX: weatherThermometer.innerBulbRadiusX
                            radiusY: weatherThermometer.innerBulbRadiusY
                            direction: PathArc.Clockwise
                        }
                        PathCubic {
                            x: 7.25
                            y: 21.6
                            control1X: weatherThermometer.innerLeftJoinX + 0.55
                            control1Y: weatherThermometer.innerJoinY - 0.62
                            control2X: 7.25
                            control2Y: 22.15
                        }
                        PathLine { x: 7.25; y: 5.2 }
                        PathQuad {
                            x: weatherThermometer.bulbCenterX
                            y: 3.2
                            controlX: 7.25
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
                        PathLine { x: 12.2; y: 19.3 }
                        // A mirrored, tangent entry into the bulb avoids
                        // the accidental right-angle raster step.
                        PathCubic {
                            x: weatherThermometer.outerRightJoinX
                            y: weatherThermometer.outerJoinY
                            control1X: 12.2
                            control1Y: 20.0
                            control2X: weatherThermometer.outerRightJoinX - 0.58
                            control2Y: weatherThermometer.outerJoinY - 0.66
                        }
                        PathArc {
                            x: weatherThermometer.bulbCenterX
                            y: weatherThermometer.bulbCenterY
                               + weatherThermometer.outerBulbRadiusY
                            radiusX: weatherThermometer.outerBulbRadiusX
                            radiusY: weatherThermometer.outerBulbRadiusY
                            direction: PathArc.Clockwise
                        }
                        PathArc {
                            x: weatherThermometer.outerLeftJoinX
                            y: weatherThermometer.outerJoinY
                            radiusX: weatherThermometer.outerBulbRadiusX
                            radiusY: weatherThermometer.outerBulbRadiusY
                            direction: PathArc.Clockwise
                        }
                        PathCubic {
                            x: 4.8
                            y: 19.3
                            control1X: weatherThermometer.outerLeftJoinX + 0.58
                            control1Y: weatherThermometer.outerJoinY - 0.66
                            control2X: 4.8
                            control2Y: 20.0
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

                // Major/minor scale marks: both use the EXACT white and
                // opacity of the glass. Snap their edges to whole pixels so
                // 4-sample antialiasing does not fade the tiny strokes.
                // The long marks intentionally cross the right edge of the
                // narrow liquid column, like a graduated thermometer scale.
                readonly property real tickRightX: 12.2 - 1.5 / 2 - 0.45
                Repeater {
                    model: 4

                    delegate: Rectangle {
                        readonly property bool majorTick: index % 2 === 0
                        width: majorTick ? 3 : 2
                        x: Math.round(weatherThermometer.tickRightX) - width
                        y: Math.round(6 + index * 3.8)
                        height: 1.25
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
