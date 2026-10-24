import QtQuick
import "../../components"

// Stage 8C: read-only Level 2 projection of the Hub's one weather snapshot.
// This component must never start WeatherStation's view-scoped collectors.
Item {
    id: weatherExplore
    property var weatherSnapshot: null
    property string selectedDomain: "weather"
    readonly property int densityLevel: height >= 300 ? 3 : 2
    readonly property string weatherState:
        weatherSnapshot && weatherSnapshot.state
        ? String(weatherSnapshot.state) : "disconnected"
    readonly property bool weatherReady:
        weatherSnapshot !== null && weatherState === "ready"
        && weatherSnapshot.fresh === true
    readonly property var airQuality:
        weatherSnapshot && weatherSnapshot.airQuality
        ? weatherSnapshot.airQuality : null
    readonly property bool airQualityReady:
        airQuality !== null && airQuality.state === "ready"
        && airQuality.fresh === true
        && typeof airQuality.index === "number"
        && isFinite(airQuality.index) && airQuality.index >= 0
    readonly property real uvIndex:
        weatherReady && typeof weatherSnapshot.uvIndex === "number"
        && isFinite(weatherSnapshot.uvIndex) && weatherSnapshot.uvIndex >= 0
        ? weatherSnapshot.uvIndex : -1
    readonly property string weatherStatus:
        weatherState === "ready" && !weatherReady
        ? "STALE" : weatherState.toUpperCase()
    readonly property string airQualityStatus:
        airQualityReady ? "READY" : airQuality && airQuality.state
        ? String(airQuality.state).toUpperCase() : "UNAVAILABLE"
    readonly property string statusLine:
        selectedDomain === "space" ? "SPACE // PROVIDER NOT CONNECTED"
        : selectedDomain === "ground"
        ? (airQualityReady ? "GROUND // AQI ONLY // FRESH"
           : "GROUND // AQI " + airQualityStatus)
        : selectedDomain === "sky"
        ? (weatherReady ? "SKY // CURRENT ATMOSPHERE // FRESH"
           : "SKY // " + weatherStatus)
        : weatherReady ? "WEATHER // FRESH" : "WEATHER // " + weatherStatus

    // Weather, air quality, and UV must retain their *independent* states.
    // Solar and seismic feeds are not available from this shared bridge.
    readonly property string heading:
        selectedDomain === "ground" ? "GROUND // AIR"
        : selectedDomain === "sky" ? "SKY // ATMOSPHERE"
        : selectedDomain === "space" ? "SPACE // SOLAR"
        : "WEATHER // CURRENT"
    readonly property string primary:
        selectedDomain === "ground"
        ? (airQualityReady ? "AQI " + String(airQuality.index) : "AQI --")
        : selectedDomain === "sky"
        ? (uvIndex >= 0 ? "UV " + String(uvIndex) : "UV --")
        : selectedDomain === "space" ? "NO LIVE FEED"
        : weatherReady ? String(weatherSnapshot.temperatureF || "--°F") : "--°F"
    readonly property string detail:
        selectedDomain === "ground"
        ? (airQualityReady ? String(airQuality.label || "UNKNOWN")
           : "AQI // " + airQualityStatus)
        : selectedDomain === "sky"
        ? (weatherReady ? "WIND " + String(weatherSnapshot.windMph || "--")
                          + " MPH" : "WIND --")
        : selectedDomain === "space" ? "NOAA SOLAR // NOT CONNECTED"
        : weatherReady ? String(weatherSnapshot.condition || "UNKNOWN")
                       : weatherStatus
    readonly property string secondDetail:
        selectedDomain === "ground" ? "POLLEN / SEISMIC // NOT CONNECTED"
        : selectedDomain === "sky"
        ? (weatherReady ? "HUMIDITY " + String(weatherSnapshot.humidity || "--")
                         : "HUMIDITY --")
        : selectedDomain === "space" ? "AURORA / FLARES // NOT CONNECTED"
        : weatherReady ? "FEELS " + String(weatherSnapshot.feelsLikeF || "--")
                       : "FEELS --"
    readonly property string thirdDetail:
        selectedDomain === "ground" ? "OTHER GROUND DATA // NOT CONNECTED"
        : selectedDomain === "sky"
        ? (weatherReady ? "WIND DIRECTION " + String(
              weatherSnapshot.windDirection || "--") : "WIND DIRECTION --")
        : selectedDomain === "space" ? "AWAITING SHARED BRIDGE"
        : weatherReady ? "WIND " + String(weatherSnapshot.windMph || "--")
                          + " MPH" : "WIND --"

    Row {
        id: domainSelector
        width: parent.width
        height: weatherExplore.densityLevel === 3 ? 32 : 27
        spacing: 4
        Repeater {
            model: ["WEATHER", "GROUND", "SKY", "SPACE"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(1, (domainSelector.width
                                    - 3 * domainSelector.spacing) / 4)
                height: domainSelector.height
                label: modelData
                labelPixelSize: 10
                selected: modelData.toLowerCase() === weatherExplore.selectedDomain
                trackLabelGlowLocally: true
                softGlowEnabled: false
                // SPACE is inspectable, but intentionally has no live feed.
                onLeftClicked: weatherExplore.selectedDomain = modelData.toLowerCase()
            }
        }
    }
    Item {
        anchors.top: domainSelector.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        Column {
            width: parent.width
            height: childrenRect.height
            anchors.centerIn: parent
            spacing: weatherExplore.densityLevel === 3 ? 12 : 7
            GohuText {
                width: parent.width
                height: weatherExplore.densityLevel === 3 ? 28 : 23
                font.pixelSize: weatherExplore.densityLevel === 3 ? 17 : 13
                color: Colors.magenta
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: weatherExplore.heading
            }
            GohuText {
                width: parent.width
                height: weatherExplore.densityLevel === 3 ? 62 : 49
                font.pixelSize: weatherExplore.densityLevel === 3 ? 39 : 30
                color: weatherExplore.selectedDomain === "space"
                       || (weatherExplore.selectedDomain === "ground"
                           && !weatherExplore.airQualityReady)
                       || (weatherExplore.selectedDomain !== "ground"
                           && !weatherExplore.weatherReady)
                       ? Colors.orange : Colors.white
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: weatherExplore.primary
            }
            GohuText {
                width: parent.width
                height: weatherExplore.densityLevel === 3 ? 31 : 24
                font.pixelSize: weatherExplore.densityLevel === 3 ? 18 : 15
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: weatherExplore.detail
            }
            GohuText {
                width: parent.width
                height: weatherExplore.densityLevel === 3 ? 23 : 19
                font.pixelSize: weatherExplore.densityLevel === 3 ? 13 : 11
                color: weatherExplore.selectedDomain === "weather"
                       || weatherExplore.selectedDomain === "sky"
                       ? Colors.cyan : Colors.orange
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: weatherExplore.secondDetail
            }
            GohuText {
                width: parent.width
                height: weatherExplore.densityLevel === 3 ? 22 : 18
                font.pixelSize: weatherExplore.densityLevel === 3 ? 12 : 10
                color: Colors.orange
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: weatherExplore.thirdDetail
            }
        }
    }
}
