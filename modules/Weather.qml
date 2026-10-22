import QtQuick
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

            // Classic thermometer silhouette again: a narrow tube feeding a
            // wider bulb. Tube and bulb are traced as one continuous glass
            // chamber, so there is no seam and the live fluid fills/drains
            // through both as a single temperature reading.
            Item {
                id: weatherThermometer
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 20
                implicitHeight: 42

                property color liquidColor: weatherDock.thermometerLiquidColor
                property real animatedLevel:
                    weatherDock.thermometerState.valid
                    ? weatherDock.thermometerState.level : 0

                // Glass and scale marks deliberately share one opacity.
                readonly property color glassColor: Colors.white
                readonly property real glassOpacity: 1.0

                Behavior on animatedLevel {
                    NumberAnimation {
                        duration: 300
                        easing.type: Easing.InOutQuad
                    }
                }

                Behavior on liquidColor {
                    ColorAnimation { duration: 300 }
                }

                onAnimatedLevelChanged: thermometerCanvas.requestPaint()
                onLiquidColorChanged: thermometerCanvas.requestPaint()
                onGlassColorChanged: thermometerCanvas.requestPaint()
                onWidthChanged: thermometerCanvas.requestPaint()
                onHeightChanged: thermometerCanvas.requestPaint()

                // One path, shaped like the original tube + bulb instrument.
                // The shoulder curves flare from the tube directly into the
                // bulb, so neither glass nor liquid has a dividing line.
                function traceThermometer(
                    ctx, centerX, topY, bottomY,
                    tubeHalfWidth, shoulderY, bulbHalfWidth
                ) {
                    const left = centerX - tubeHalfWidth;
                    const right = centerX + tubeHalfWidth;
                    const topRadius = tubeHalfWidth;
                    const bulbTopY = shoulderY + 1;
                    const bulbMidY = (bulbTopY + bottomY) / 2;

                    ctx.beginPath();
                    ctx.moveTo(centerX, topY);
                    ctx.quadraticCurveTo(
                        right, topY,
                        right, topY + topRadius
                    );
                    ctx.lineTo(right, shoulderY - 2);
                    ctx.quadraticCurveTo(
                        right, shoulderY,
                        centerX + bulbHalfWidth, bulbTopY
                    );
                    ctx.cubicCurveTo(
                        centerX + bulbHalfWidth, bulbMidY,
                        centerX + bulbHalfWidth, bottomY - 2,
                        centerX, bottomY
                    );
                    ctx.cubicCurveTo(
                        centerX - bulbHalfWidth, bottomY - 2,
                        centerX - bulbHalfWidth, bulbMidY,
                        centerX - bulbHalfWidth, bulbTopY
                    );
                    ctx.quadraticCurveTo(
                        left, shoulderY,
                        left, shoulderY - 2
                    );
                    ctx.lineTo(left, topY + topRadius);
                    ctx.quadraticCurveTo(
                        left, topY,
                        centerX, topY
                    );
                    ctx.closePath();
                }

                Canvas {
                    id: thermometerCanvas
                    anchors.fill: parent
                    antialiasing: true

                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);

                        const centerX = width / 2;
                        const outerTop = 1;
                        const outerBottom = height - 1;
                        const outerTubeHalf = 5;
                        const outerShoulderY = 26;
                        const outerBulbHalf = 8;

                        const innerTop = 3;
                        const innerBottom = height - 3;
                        const innerTubeHalf = 3;
                        const innerShoulderY = 27;
                        const innerBulbHalf = 5.5;

                        // Black glass interior.
                        weatherThermometer.traceThermometer(
                            ctx,
                            centerX,
                            outerTop,
                            outerBottom,
                            outerTubeHalf,
                            outerShoulderY,
                            outerBulbHalf
                        );
                        ctx.fillStyle = Colors.black;
                        ctx.fill();

                        // Continuous live fluid, clipped to the entire inner
                        // tube + bulb chamber. The bulb therefore fills and
                        // drains with the same normalized reading as the stem.
                        ctx.save();
                        weatherThermometer.traceThermometer(
                            ctx,
                            centerX,
                            innerTop,
                            innerBottom,
                            innerTubeHalf,
                            innerShoulderY,
                            innerBulbHalf
                        );
                        ctx.clip();

                        const innerHeight = innerBottom - innerTop;
                        const fillHeight =
                            innerHeight * weatherThermometer.animatedLevel;
                        ctx.globalAlpha = 1.0;
                        ctx.fillStyle = weatherThermometer.liquidColor;
                        ctx.fillRect(
                            centerX - innerBulbHalf,
                            innerBottom - fillHeight,
                            innerBulbHalf * 2,
                            fillHeight
                        );
                        ctx.restore();

                        // Glass outline.
                        ctx.save();
                        ctx.globalAlpha = weatherThermometer.glassOpacity;
                        weatherThermometer.traceThermometer(
                            ctx,
                            centerX,
                            outerTop,
                            outerBottom,
                            outerTubeHalf,
                            outerShoulderY,
                            outerBulbHalf
                        );
                        ctx.lineWidth = 2;
                        ctx.strokeStyle = weatherThermometer.glassColor;
                        ctx.stroke();

                        // Four indicator marks inside the tube. They use the
                        // exact same color and opacity as the glass outline.
                        const innerTubeRight = centerX + innerTubeHalf;
                        const tickLongStartX = centerX - 0.5;
                        const tickShortStartX = centerX + 0.5;
                        const tickEndX = innerTubeRight - 0.5;
                        const tickTop = 7;
                        const tickStep = 6;

                        ctx.lineWidth = 1;
                        ctx.strokeStyle = weatherThermometer.glassColor;

                        for (let i = 0; i < 4; i++) {
                            const tickY = tickTop + i * tickStep;
                            ctx.beginPath();
                            ctx.moveTo(
                                i % 2 === 0
                                ? tickLongStartX : tickShortStartX,
                                tickY
                            );
                            ctx.lineTo(tickEndX, tickY);
                            ctx.stroke();
                        }
                        ctx.restore();
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
