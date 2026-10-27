import QtQuick
import QtQuick.Shapes
import QtQuick.Effects
import Quickshell
import "../components"
import "../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy
import "../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy
import "../widgets/weather/StationOfficialAlertPolicy.js" as OfficialAlertPolicy

DockButton {
    id: weatherDock

    property var weatherStationWindow: null
    property var weatherService: null
    property var nwsAlertSource: null

    readonly property var officialAlertSummary:
        OfficialAlertPolicy.summary(
            nwsAlertSource && Array.isArray(nwsAlertSource.alertList)
            ? nwsAlertSource.alertList : []
        )
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

    // One service clock and one shared astronomy policy. No new weather
    // requests or new day/night colors.
    readonly property var skyCycle: WeatherCyclePolicy.atObservation(
        observationClockMs,
        weatherService ? weatherService.localObservationDateTime : "",
        weatherService ? weatherService.localObservationAnchorMs : 0,
        weatherService ? weatherService.dailyForecast : []
    )
    readonly property string celestialMode:
        weatherFresh ? WeatherCyclePolicy.artworkFor(weatherState, skyCycle) : "weather"

    function officialAlertColor(token) {
        switch (String(token || "")) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }

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
                   + (officialAlertSummary.available ? 18 : 0)

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

    // The dock perimeter belongs to the weather condition; only the
    // thermometer itself gets a temperature-colored halo.
    normalDockGlowColor: weatherColor
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    // This module owns two independent, locally stacked glow planes.
    // Disable DockButton's z=2 overlay, which otherwise spreads orange
    // from the nearby readout across the temperature-colored thermometer.
    contentGlowEnabled: false
    contentGlowSource: weatherGlowArtwork
    trackArtworkGlowLocally: true

    Timer {
        interval: 60000
        repeat: true
        running: true
        // Invalid cached readings age out even if the network is down.
        onTriggered: weatherDock.observationClockMs = Date.now()
    }

    // Optical center: the 2px right shift overcompensated for emoji bearings.
    // Shift the full group 3px left relative to that version while keeping
    // its responsive width, icon/readout gap and independent glow planes.
    Row {
        id: weatherContent
        anchors.centerIn: parent
        anchors.horizontalCenterOffset:
            officialAlertSummary.available ? -9 : -1
        spacing: 0

        // Weather art glow stays behind its icon and readout, not over the
        // separate thermometer. The wrapper preserves identical implicit
        // width/height and the same 6px condition-to-readout gap.
        Item {
            id: weatherArtworkGlowFrame
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: weatherGlowArtwork.implicitWidth
            implicitHeight: weatherGlowArtwork.implicitHeight

            SafeDropShadow {
                id: weatherArtworkGlow
                anchors.fill: weatherGlowArtwork
                safeSource: weatherGlowArtwork
                requestedVisible: true
                z: 0
                radius: weatherDock.contentGlowRadius
                samples: weatherDock.contentGlowSamples
                horizontalOffset: 0
                verticalOffset: 0
                transparentBorder: true
                opacity: weatherDock.contentGlowOpacity
                color: weatherDock.contentGlowColor
            }

            Row {
                id: weatherGlowArtwork
                z: 1
                spacing: 6

                Item {
                    id: weatherConditionSlot
                    anchors.verticalCenter: parent.verticalCenter
                    implicitWidth: Math.max(42, Math.ceil(weatherCondition.implicitWidth))
                    implicitHeight: 46

                    // Preserve the original 42px condition glyph contract
                    // for unknown or warning states; it stays centered.
                    Text {
                        id: weatherCondition
                        anchors.centerIn: parent
                        text: weatherDock.weatherState.icon
                        font.pixelSize: 42
                        color: weatherDock.foregroundColor
                        visible: weatherDock.celestialMode === "weather"
                    }

                    // One 40x40 canonical composition owns moon placement,
                    // foreground cloud/precipitation and occlusion. Neither
                    // the dock Row width nor its thermometer is changed.
                    WeatherCelestialGlyph {
                        id: dockWeatherArt
                        anchors.centerIn: parent
                        width: 42
                        height: 42
                        mode: weatherDock.celestialMode
                        weatherKind: WeatherCyclePolicy.nightKind(weatherDock.weatherState)
                        solar: weatherDock.skyCycle.solar
                        moonPhase: weatherDock.skyCycle.moonPhase
                        ink: weatherDock.foregroundColor
                        visible: weatherDock.celestialMode !== "weather"
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
                }
            }
        }

        // The rear light stays OUTSIDE the thermometer's antialiasing
        // layer. RectangularShadow paints a visible bulb/stem halo directly
        // instead of sampling an animated QtQuick.Shape nested in that layer.
        // Neither halo samples white glass, avoiding doubled outlines.
        Item {
            id: thermometerGlowFrame
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: 17
            implicitHeight: 35
            clip: false

            readonly property bool hasGlow: weatherDock.thermometerState.valid
                                            && weatherThermometer.animatedLevel > 0
            readonly property color rearGlowColor:
                weatherDock.open || weatherDock.pressed
                ? Colors.magenta : weatherThermometer.liquidColor

            // Stronger, broader rear light around the bulb, now matched to
            // the shared dock opacity instead of attenuating it. This effect
            // stays behind the vessel and never recolors its white glass.
            RectangularShadow {
                id: thermometerRearGlow
                x: weatherThermometer.bulbCenterX - width / 2
                y: weatherThermometer.bulbCenterY - height / 2
                width: weatherThermometer.outerBulbRadiusX * 2 - 1
                height: weatherThermometer.outerBulbRadiusY * 2 - 1
                radius: Math.min(width, height) / 2
                blur: 10
                spread: 2.2
                z: 0
                visible: thermometerGlowFrame.hasGlow
                opacity: weatherDock.contentGlowOpacity
                color: thermometerGlowFrame.rearGlowColor
            }

            // A narrower glow rises with the animated liquid, instead of
            // lighting the entire tube when only the bulb is filled.
            RectangularShadow {
                id: thermometerStemRearGlow
                readonly property real topY: 3.2
                readonly property real bottomY: 22.5
                x: weatherThermometer.bulbCenterX - width / 2
                width: 2.5
                height: Math.max(0, Math.min(1, weatherThermometer.animatedLevel))
                        * (bottomY - topY)
                y: bottomY - height
                radius: width / 2
                blur: 7
                spread: 1.2
                z: 0
                visible: thermometerGlowFrame.hasGlow && height >= 1
                opacity: weatherDock.contentGlowOpacity
                color: thermometerGlowFrame.rearGlowColor
            }

            // Compact native scene-graph thermometer: one smooth connected
            // tube and circular bulb. Original 20×42 scaled to 17×35.
            Item {
                id: weatherThermometer
                z: 1
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

                // Glass and its graduated ticks share one state color.
                // Only OPEN turns structural glass magenta; idle, hover,
                // and pressed retain the normal off-white glass.
                readonly property color glassColor:
                    weatherDock.open ? Colors.magenta : Colors.white
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

                // The vessel is transparent: the dock background shows
                // through the glass around the liquid, including when open.
                // Its existing curves remain unchanged for outline alignment.
                Shape {
                    anchors.fill: parent

                    ShapePath {
                        strokeWidth: 0
                        strokeColor: "transparent"
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

                // A small LOCAL liquid-only halo, layered behind colored
                // fluid. The color stays linked to actual
                // air temperature while idle and hovered; the intensity uses
                // the shared DockButton state values. Press/open retain the
                // established magenta glow rule without changing pressed fluid.
                SafeDropShadow {
                    id: thermometerLiquidGlow
                    anchors.fill: thermometerLiquid
                    safeSource: thermometerLiquid
                    requestedVisible: weatherDock.thermometerState.valid
                                      && weatherThermometer.animatedLevel > 0
                    z: 1
                    radius: 8
                    samples: 15
                    horizontalOffset: 0
                    verticalOffset: 0
                    transparentBorder: true
                    opacity: weatherDock.contentGlowOpacity * 0.8
                    color: weatherDock.open || weatherDock.pressed
                           ? Colors.magenta : weatherThermometer.liquidColor
                }

                // The inner ellipse is centered with the glass and slightly
                // narrower, keeping both side voids and bottom clearance even.
                // A moving gradient stop drains through bulb and tube.
                Shape {
                    id: thermometerLiquid
                    anchors.fill: parent
                    z: 2
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

                // The glass follows open mode and stays over the liquid halo.
                Shape {
                    anchors.fill: parent
                    z: 3
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

                // Major/minor scale marks use the SAME color and opacity
                // as the glass, including the magenta-open state. Snap their edges to whole pixels so
                // 4-sample antialiasing does not fade the tiny strokes.
                // The long marks intentionally cross the right edge of the
                // narrow liquid column, like a graduated thermometer scale.
                readonly property real tickRightX: 12.2 - 1.5 / 2 - 0.45
                Repeater {
                    model: 4

                    delegate: Rectangle {
                        z: 4
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

    // Separate official-alert mark. It never changes weatherState,
    // weatherColor, celestial artwork, or thermometer classification.
    Rectangle {
        id: officialAlertDockBadge
        visible: weatherDock.officialAlertSummary.available
        width: 16
        height: 20
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.verticalCenter: parent.verticalCenter
        color: Colors.black
        border.width: 1
        border.color:
            weatherDock.officialAlertColor(
                weatherDock.officialAlertSummary.colorToken
            )

        GohuText {
            anchors.centerIn: parent
            text: weatherDock.officialAlertSummary.dockText
            font.pixelSize: 11
            color:
                weatherDock.officialAlertColor(
                    weatherDock.officialAlertSummary.colorToken
                )
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
