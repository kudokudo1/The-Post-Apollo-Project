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

            // One continuous glass chamber: the rounded lower reservoir
            // stays inside the tube walls and fills/drains with the same live
            // temperature level as the stem. Scale ticks live inside the glass.
            Item {
                id: weatherThermometer
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 20
                implicitHeight: 42

                property color liquidColor: weatherDock.thermometerLiquidColor
                property real animatedLevel:
                    weatherDock.thermometerState.valid
                    ? weatherDock.thermometerState.level : 0

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
                onWidthChanged: thermometerCanvas.requestPaint()
                onHeightChanged: thermometerCanvas.requestPaint()

                // Rounded glass body without a separate circular bulb.
                // The bottom curve terminates at the same side walls as the
                // stem, so the chamber is one continuous vessel.
                function traceGlass(ctx, x, y, width, height, topRadius, bottomRadius) {
                    const left = x;
                    const right = x + width;
                    const top = y;
                    const bottom = y + height;

                    ctx.beginPath();
                    ctx.moveTo(left + topRadius, top);
                    ctx.lineTo(right - topRadius, top);
                    ctx.quadraticCurveTo(right, top, right, top + topRadius);
                    ctx.lineTo(right, bottom - bottomRadius);
                    ctx.quadraticCurveTo(
                        right, bottom,
                        right - bottomRadius, bottom
                    );
                    ctx.lineTo(left + bottomRadius, bottom);
                    ctx.quadraticCurveTo(
                        left, bottom,
                        left, bottom - bottomRadius
                    );
                    ctx.lineTo(left, top + topRadius);
                    ctx.quadraticCurveTo(left, top, left + topRadius, top);
                    ctx.closePath();
                }

                Canvas {
                    id: thermometerCanvas
                    anchors.fill: parent
                    antialiasing: true

                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);

                        const outerX = 2;
                        const outerY = 1;
                        const outerWidth = width - 4;
                        const outerHeight = height - 2;
                        const wall = 2;

                        const innerX = outerX + wall;
                        const innerY = outerY + wall;
                        const innerWidth = outerWidth - wall * 2;
                        const innerHeight = outerHeight - wall * 2;
                        const innerBottom = innerY + innerHeight;

                        // Black glass interior first.
                        weatherThermometer.traceGlass(
                            ctx,
                            outerX, outerY,
                            outerWidth, outerHeight,
                            5, outerWidth / 2
                        );
                        ctx.fillStyle = Colors.black;
                        ctx.fill();

                        // The fluid is clipped to the entire inner chamber.
                        // At low readings only the lower reservoir fills; as
                        // temperature rises the same body continues up the stem.
                        ctx.save();
                        weatherThermometer.traceGlass(
                            ctx,
                            innerX, innerY,
                            innerWidth, innerHeight,
                            3, innerWidth / 2
                        );
                        ctx.clip();

                        const fillHeight =
                            innerHeight * weatherThermometer.animatedLevel;
                        ctx.fillStyle = weatherThermometer.liquidColor;
                        ctx.fillRect(
                            innerX,
                            innerBottom - fillHeight,
                            innerWidth,
                            fillHeight
                        );
                        ctx.restore();

                        // White glass outline.
                        weatherThermometer.traceGlass(
                            ctx,
                            outerX, outerY,
                            outerWidth, outerHeight,
                            5, outerWidth / 2
                        );
                        ctx.lineWidth = wall;
                        ctx.strokeStyle = Colors.white;
                        ctx.stroke();

                        // Four scale marks, all inside the right side of glass.
                        const tickStartX = innerX + innerWidth * 0.52;
                        const longTickEndX = innerX + innerWidth - 1;
                        const shortTickEndX = innerX + innerWidth - 3;
                        const tickTop = innerY + 5;
                        const tickStep = 7;

                        ctx.lineWidth = 1;
                        ctx.strokeStyle = Colors.white;

                        for (let i = 0; i < 4; i++) {
                            const tickY = tickTop + i * tickStep;
                            ctx.beginPath();
                            ctx.moveTo(tickStartX, tickY);
                            ctx.lineTo(
                                i % 2 === 0
                                ? longTickEndX : shortTickEndX,
                                tickY
                            );
                            ctx.stroke();
                        }
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
