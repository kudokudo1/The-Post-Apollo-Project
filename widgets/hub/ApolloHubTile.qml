import QtQuick
import "../../components"
import "../../services/hub/ApolloHubLayout.js" as Layout

// Presentation only: live weather arrives from ApolloHubW as a read-only
// snapshot. This tile never creates services, polls the network, or refreshes.
SectionFrame {
    id: tile

    property string moduleId: "time"
    property var weatherSnapshot: null
    // Keep weather and air-quality readiness independent. The backend masks
    // unavailable readings; the UI must not resurrect them from stale values.
    readonly property string weatherState:
        weatherSnapshot && weatherSnapshot.state
        ? String(weatherSnapshot.state) : "disconnected"
    readonly property bool weatherReady:
        weatherState === "ready" && weatherSnapshot !== null
        && weatherSnapshot.fresh === true
    readonly property string weatherStatus:
        weatherState === "ready" && !weatherReady
        ? "STALE" : weatherState.toUpperCase()
    readonly property var airQuality:
        weatherSnapshot && weatherSnapshot.airQuality
        ? weatherSnapshot.airQuality : null
    readonly property bool airQualityReady:
        airQuality !== null && airQuality.state === "ready"
        && airQuality.fresh === true && Number(airQuality.index) >= 0
    readonly property string airQualityText: {
        if (!airQuality)
            return "DISCONNECTED";
        if (airQualityReady)
            return String(airQuality.index) + " " + String(airQuality.label || "UNKNOWN");
        return String(airQuality.state || "unavailable").toUpperCase();
    }
    property bool editing: false
    property bool keyboardSelected: false
    property int tileIndex: 0
    property int tileCount: 0
    property date now: new Date()

    signal moveLeft(int index)
    signal moveRight(int index)
    signal changeModule(int index)
    signal pointerEntered(int index)

    HoverHandler {
        onHoveredChanged: {
            if (hovered)
                tile.pointerEntered(tile.tileIndex);
        }
    }

    fillColor: Colors.black
    fillOpacity: 0.92
    borderColor: keyboardSelected ? Colors.orange : Colors.cyan
    borderOpacity: 0.7
    borderWidth: 1
    radius: 0
    inset: 10

    Timer {
        interval: 1000
        repeat: true
        running: tile.visible && (tile.moduleId === "time" || tile.moduleId === "calendar")
        onTriggered: tile.now = new Date()
    }

    GohuText {
        id: titleLabel
        anchors.left: parent.left
        anchors.top: parent.top
        text: Layout.tileTitle(tile.moduleId)
        color: Colors.cyan
        font.pixelSize: 13
    }

    Row {
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 4
        visible: tile.editing

        ActionButton {
            trackLabelGlowLocally: true
            width: 28
            height: 25
            label: "←"
            available: tile.tileIndex > 0
            onLeftClicked: tile.moveLeft(tile.tileIndex)
        }
        ActionButton {
            trackLabelGlowLocally: true
            width: 28
            height: 25
            label: "→"
            available: tile.tileIndex < tile.tileCount - 1
            onLeftClicked: tile.moveRight(tile.tileIndex)
        }
        ActionButton {
            trackLabelGlowLocally: true
            width: 57
            height: 25
            label: "SWAP"
            onLeftClicked: tile.changeModule(tile.tileIndex)
        }
    }

    // 140px mini Weather card: temperature/status left, detailed readings
    // right. Leave the 25px edit controls and footer in their own lanes.
    Row {
        id: weatherInfo
        visible: tile.moduleId === "weather"
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
        spacing: 10

        Column {
            id: weatherPrimary
            width: Math.round(weatherInfo.width * 0.43)
            spacing: 1

            GohuText {
                width: parent.width
                height: 32
                color: tile.weatherReady ? Colors.white : Colors.orange
                font.pixelSize: 25
                verticalAlignment: Text.AlignVCenter
                text: tile.weatherReady
                      ? String(tile.weatherSnapshot.temperatureF || "--°F")
                      : "--°F"
            }
            GohuText {
                width: parent.width
                height: 18
                color: tile.weatherReady ? Colors.cyan : Colors.orange
                font.pixelSize: 11
                elide: Text.ElideRight
                text: tile.weatherReady
                      ? String(tile.weatherSnapshot.condition || "UNKNOWN")
                      : tile.weatherStatus
            }
        }

        Column {
            width: Math.max(0, weatherInfo.width - weatherPrimary.width
                            - weatherInfo.spacing)
            spacing: 3

            GohuText {
                width: parent.width
                height: 15
                color: Colors.cyan
                font.pixelSize: 10
                elide: Text.ElideRight
                text: "HUM  " + (tile.weatherReady
                                 ? String(tile.weatherSnapshot.humidity || "--") : "--")
            }
            GohuText {
                width: parent.width
                height: 15
                color: Colors.cyan
                font.pixelSize: 10
                elide: Text.ElideRight
                text: "WIND " + (tile.weatherReady
                                 ? String(tile.weatherSnapshot.windMph || "--") + " MPH"
                                 : "--")
            }
            GohuText {
                width: parent.width
                height: 15
                color: tile.airQualityReady ? Colors.cyan : Colors.orange
                font.pixelSize: 10
                elide: Text.ElideRight
                text: "AQI  " + tile.airQualityText
            }
        }
    }

    GohuText {
        visible: tile.moduleId !== "weather"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 3
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        color: tile.moduleId === "time" ? Colors.white : Colors.orange
        font.pixelSize: tile.moduleId === "time" ? 23 : 14
        text: tile.moduleId === "time"
              ? Qt.formatTime(tile.now, "HH:mm:ss")
              : tile.moduleId === "calendar"
              ? Qt.formatDate(tile.now, "ddd, d MMM yyyy")
              : "MODULE PREVIEW"
    }

    GohuText {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        color: Colors.cyan
        opacity: 0.7
        font.pixelSize: 10
        text: tile.moduleId === "time" || tile.moduleId === "calendar"
              ? "LOCAL TIME"
              : tile.moduleId === "weather"
              ? (tile.weatherReady
                 ? (Number(tile.weatherSnapshot.ageMinutes) >= 0
                    ? "WEATHER // FRESH // "
                      + String(tile.weatherSnapshot.ageMinutes) + " MIN OLD"
                    : "WEATHER // FRESH")
                 : "WEATHER // " + tile.weatherStatus)
              : "DATA ADAPTER NOT CONNECTED"
    }
}
