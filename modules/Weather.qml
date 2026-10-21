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

    // Condition -> measured temperature with isolated degree glow -> thermometer.
    // Preserve the original overall module glow and 50px dock height.
    Row {
        id: weatherContent
        anchors.centerIn: parent
        // Font bearings put the visible 🌡 slightly farther from the right
        // edge. Compensate optically while keeping measured width + 6px.
        anchors.horizontalCenterOffset: 2
        spacing: 6

        Text {
            id: weatherCondition
            anchors.verticalCenter: parent.verticalCenter
            text: weatherDock.weatherState.icon
            font.pixelSize: 32
            color: weatherDock.foregroundColor
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

            Text {
                id: weatherThermometer
                anchors.verticalCenter: parent.verticalCenter
                text: "🌡"
                font.pixelSize: 24
                color: weatherDock.open ? Colors.magenta : Colors.orange
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
