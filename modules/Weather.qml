import QtQuick
import Quickshell
import "../components"
import "../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy

DockButton {
    id: weatherDock

    property var weatherStationWindow: null
    property var weatherService: null
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

    readonly property string temperatureLabel: {
        if (!weatherFresh)
            return "--°";
        const value = Number(weatherService.tempF);
        if (!isFinite(value) || value < -150 || value > 150)
            return "--°";
        return Math.round(value) + "°";
    }

    implicitHeight: 50
    // Dynamic text must remain inside the dock footprint at every temperature.
    implicitWidth: Math.max(90, Math.ceil(weatherText.implicitWidth) + 18)

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

    contentGlowSource: weatherText
    trackArtworkGlowLocally: true

    Timer {
        interval: 60000
        repeat: true
        running: true
        // Invalid cached readings age out even if the network is down.
        onTriggered: weatherDock.observationClockMs = Date.now()
    }

    Text {
        id: weatherText
        anchors.centerIn: parent
        text: weatherDock.weatherState.icon + " " + weatherDock.temperatureLabel
        font.family: "GohuFont 11 Nerd Font Mono"
        font.pixelSize: 20
        color: weatherDock.foregroundColor
    }

    onLeftClicked: {
        if (weatherStationWindow)
            weatherStationWindow.toggle();
    }
}
