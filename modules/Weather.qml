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
    // Dynamic text must remain inside the dock footprint at every temperature.
    implicitWidth: Math.max(90, Math.ceil(weatherContent.implicitWidth) + 18)

    open: menuOpen
    // An informational state has to stay legible when its color is yellow.
    openFillColor: Colors.black

    normalForegroundColor: weatherColor
    hoverForegroundColor: weatherColor
    pressedForegroundColor: weatherColor
    openForegroundColor: weatherColor

    normalContentGlowColor: weatherColor
    hoverContentGlowColor: weatherColor
    pressedContentGlowColor: weatherColor
    openGlowColor: weatherColor

    normalDockGlowColor: weatherColor
    hoverDockGlowColor: weatherColor
    pressedDockGlowColor: weatherColor

    contentGlowSource: weatherContent
    trackArtworkGlowLocally: true

    Timer {
        interval: 60000
        repeat: true
        running: true
        // Invalid cached readings age out even if the network is down.
        onTriggered: weatherDock.observationClockMs = Date.now()
    }

    // Condition -> measured temperature + units -> original thermometer.
    // Keep all three glyphs independently sized within the 50px dock.
    Row {
        id: weatherContent
        anchors.centerIn: parent
        spacing: 6

        Text {
            id: weatherCondition
            anchors.verticalCenter: parent.verticalCenter
            text: weatherDock.weatherState.icon
            font.pixelSize: 32
            color: weatherDock.foregroundColor
        }

        GohuText {
            id: weatherTemperature
            anchors.verticalCenter: parent.verticalCenter
            text: weatherDock.temperatureLabel
            font.pixelSize: 20
            color: weatherDock.foregroundColor
        }

        Text {
            id: weatherThermometer
            anchors.verticalCenter: parent.verticalCenter
            text: "🌡"
            font.pixelSize: 24
            color: Colors.orange
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
