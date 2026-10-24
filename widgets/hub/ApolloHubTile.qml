import QtQuick
import "../../components"
import "../../services/hub/ApolloHubLayout.js" as Layout
import "../../services/hub/ApolloHubTimePolicy.js" as TimePolicy

// Hub mini presentations consume shared snapshots. The B7 To-do UI uses
// the single user-private store only for intentional task actions.
SectionFrame {
    id: tile

    property string moduleId: "time"
    property var weatherSnapshot: null
    property var networkSnapshot: null
    property var mediaSnapshot: null
    property var systemSnapshot: null
    property var uptimeSnapshot: null
    property var appsSnapshot: null
    property var todoStore: null
    property var todoSnapshot: null
    property var notesStore: null
    property var notesSnapshot: null
    property var calendarSnapshot: null
    property var calendarBridge: null
    signal todoTextFocusChanged(bool focused)
    signal notesTextFocusChanged(bool focused)
    // B3 deliberately distinguishes local link status from verified internet.
    // Connected Wi-Fi/Ethernet is NOT proof that the internet is reachable.
    readonly property string networkState:
        networkSnapshot && networkSnapshot.state
        ? String(networkSnapshot.state) : "unavailable"
    readonly property bool networkConnected:
        networkState === "connected" && networkSnapshot !== null
        && networkSnapshot.connected === true
    readonly property string networkTransport:
        networkConnected ? String(networkSnapshot.transport || "none") : "none"
    readonly property var networkWifi:
        networkSnapshot && networkSnapshot.wifi ? networkSnapshot.wifi : null
    readonly property var networkEthernet:
        networkSnapshot && networkSnapshot.ethernet ? networkSnapshot.ethernet : null
    readonly property string networkHeading:
        networkState === "unavailable" ? "UNAVAILABLE"
        : networkState === "disconnected" ? "NO LOCAL LINK"
        : networkTransport === "ethernet" ? "ETHERNET"
        : networkTransport === "wifi" ? "WI-FI" : "NO LOCAL LINK"
    readonly property string networkDetail: {
        if (!networkConnected)
            return networkState === "disconnected" ? "DISCONNECTED" : "NO DEVICE DATA";
        if (networkTransport === "wifi" && networkWifi)
            return String(networkWifi.networkName || networkWifi.interfaceName || "WI-FI LINK");
        if (networkTransport === "ethernet" && networkEthernet)
            return String(networkEthernet.interfaceName || "WIRED LINK");
        return "LOCAL LINK";
    }
    readonly property string wifiLinkText:
        !networkWifi || networkState === "unavailable" ? "UNKNOWN"
        : !networkWifi.present ? "NOT PRESENT"
        : networkWifi.connected === true ? "CONNECTED" : "DISCONNECTED"
    readonly property string ethernetLinkText:
        !networkEthernet || networkState === "unavailable" ? "UNKNOWN"
        : !networkEthernet.present ? "NOT PRESENT"
        : networkEthernet.connected === true ? "CONNECTED" : "DISCONNECTED"
    readonly property string wifiSignalText: {
        if (!networkWifi || networkWifi.connected !== true)
            return "--";
        const value = networkWifi.signalPercent;
        return typeof value === "number" && isFinite(value)
               && value >= 0 && value <= 100 ? String(value) + "%" : "--";
    }
    readonly property string networkSpeedText: {
        const value = networkSnapshot ? networkSnapshot.linkSpeedMbps : -1;
        return typeof value === "number" && isFinite(value) && value >= 0
               ? String(value) + " Mb/s" : "--";
    }
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
    // Width is 1/2 columns and height is 1/2/3 base tile rows.
    // Defaults reproduce the original half-width, 140px tile.
    property int tileColumnSpan: 1
    property int tileRowSpan: 1
    property date now: new Date()
    // B10 reuses the single existing one-second tile timer. The format
    // choice is view-local, not a persisted setting or system-clock change.
    property bool use24Hour: true
    readonly property var timeSnapshot:
        TimePolicy.snapshot(tile.now.getTime(), tile.use24Hour)

    // Refresh immediately when a previously hidden Time tile reappears.
    // The existing timer handles all subsequent one-second ticks.
    onVisibleChanged: {
        if (visible && moduleId === "time")
            now = new Date();
    }

    signal moveLeft(int index)
    signal moveRight(int index)
    signal changeModule(int index, var sourceItem)
    signal transferTile(int index, var sourceItem)
    signal removeTile(int index)
    signal toggleTileWidth(int index)
    signal cycleTileHeight(int index)
    readonly property Item swapAnchor: swapAction
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
            id: swapAction
            width: 57
            height: 25
            label: "SWAP"
            onLeftClicked: tile.changeModule(tile.tileIndex, swapAction)
        }
        ActionButton {
            trackLabelGlowLocally: true
            id: moveAction
            width: 57
            height: 25
            label: "MOVE"
            onLeftClicked: tile.transferTile(tile.tileIndex, moveAction)
        }
        ActionButton {
            // One/two grid columns; metadata lives in the v2 layout.
            trackLabelGlowLocally: true
            width: 42
            height: 25
            label: "W:" + tile.tileColumnSpan
            selected: tile.tileColumnSpan === 2
            onLeftClicked: tile.toggleTileWidth(tile.tileIndex)
        }
        ActionButton {
            // Cycle normal/double/triple height, then return to normal.
            trackLabelGlowLocally: true
            width: 42
            height: 25
            label: "H:" + tile.tileRowSpan
            selected: tile.tileRowSpan > 1
            onLeftClicked: tile.cycleTileHeight(tile.tileIndex)
        }
        ActionButton {
            // Delete this tile placement ONLY. Never delete stored widget data.
            trackLabelGlowLocally: true
            width: 28
            height: 25
            label: "×"
            labelPixelSize: 18
            contentPadding: 3
            accentColor: Colors.red
            destructive: true
            hoverFillColor: Colors.red
            hoverForegroundColor: Colors.black
            hoverBorderColor: Colors.red
            onLeftClicked: tile.removeTile(tile.tileIndex)
        }
    }

    // 140px mini Weather card: temperature/status left, detailed readings
    // right. Leave the 25px edit controls and footer in their own lanes.
    Row {
        id: weatherInfo
        visible: tile.moduleId === "weather" && tile.tileRowSpan === 1
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

    // Stage 8C uses only the established Hub bridge snapshot.
    ApolloHubWeatherExplore {
        id: weatherExplore
        visible: tile.moduleId === "weather" && tile.tileRowSpan > 1
        weatherSnapshot: tile.weatherSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // Read-only B3 mini network view, using the established square tile.
    // Both transports remain visible even when Ethernet takes priority.
    Row {
        id: networkInfo
        visible: tile.moduleId === "network" && tile.tileRowSpan === 1
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
        spacing: 9

        Column {
            id: networkPrimary
            width: Math.round(networkInfo.width * 0.43)
            spacing: 3

            GohuText {
                width: parent.width
                height: 26
                font.pixelSize: 18
                color: tile.networkConnected ? Colors.white : Colors.orange
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: tile.networkHeading
            }
            GohuText {
                width: parent.width
                height: 16
                font.pixelSize: 11
                color: Colors.cyan
                elide: Text.ElideRight
                text: tile.networkDetail
            }
        }

        Column {
            width: Math.max(0, networkInfo.width - networkPrimary.width
                            - networkInfo.spacing)
            spacing: 2

            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "WI-FI LINK  " + tile.wifiLinkText
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "ETHERNET   " + tile.ethernetLinkText
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "SIGNAL     " + tile.wifiSignalText
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "SPEED      " + tile.networkSpeedText
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.orange
                elide: Text.ElideRight
                text: "INTERNET   UNVERIFIED"
            }
        }
    }

    // Stage 8D passive network views on the SAME source as the H:1 card.
    ApolloHubNetworkExplore {
        id: networkExplore
        visible: tile.moduleId === "network" && tile.tileRowSpan > 1
        networkSnapshot: tile.networkSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B2 CPU++ shows fresh CPU/RAM and optional SWAP/rootfs gauges.
    // All four percentages remain unknown while a sample is stale,
    // unavailable, disconnected, or being refreshed.
    ApolloHubSystemMini {
        id: systemMini
        visible: tile.moduleId === "cpu"
        systemSnapshot: tile.systemSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B5 Linux boot uptime, not this widget or Quickshell's session age.
    ApolloHubUptimeMini {
        id: uptimeMini
        visible: tile.moduleId === "uptime"
        uptimeSnapshot: tile.uptimeSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B6 native desktop-entry index: scrollable metadata, no launch path.
    ApolloHubAppsMini {
        id: appsMini
        visible: tile.moduleId === "apps"
        appsSnapshot: tile.appsSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B10 formatted local clock, supplied by the same tile.now timer.
    ApolloHubTimeMini {
        id: timeMini
        visible: tile.moduleId === "time"
        timeSnapshot: tile.timeSnapshot
        use24Hour: tile.use24Hour
        onToggleHourFormat: tile.use24Hour = !tile.use24Hour
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B9 civil-date calendar: cells are provided by the same live bridge
    // that already tracks local time. Navigation adjusts only view inputs.
    ApolloHubCalendarMini {
        id: calendarMini
        visible: tile.moduleId === "calendar"
        calendarSnapshot: tile.calendarSnapshot
        calendarBridge: tile.calendarBridge
        todoSnapshot: tile.todoSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B8 local Notes editor: the backend singleton owns revisions, file
    // safety, and atomic writes. The tile only passes user-initiated actions.
    ApolloHubNotesMini {
        id: notesMini
        visible: tile.moduleId === "notes"
        notesStore: tile.notesStore
        notesSnapshot: tile.notesSnapshot
        onTextFocusChanged: function(focused) {
            tile.notesTextFocusChanged(focused);
        }
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // B7 personal checklist, independent from Hospital and Hub layout data.
    ApolloHubTodoMini {
        id: todoMini
        visible: tile.moduleId === "todo"
        todoStore: tile.todoStore
        todoSnapshot: tile.todoSnapshot
        onTextFocusChanged: function(focused) {
            tile.todoTextFocusChanged(focused);
        }
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // MPD and MPRIS remain separate; neither gets selected automatically.
    ApolloHubMediaMini {
        visible: tile.moduleId === "media" && tile.tileRowSpan === 1
        mediaSnapshot: tile.mediaSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    // Stage 8E expands only the passive display of the one Media snapshot.
    ApolloHubMediaExplore {
        id: mediaExplore
        visible: tile.moduleId === "media" && tile.tileRowSpan > 1
        mediaSnapshot: tile.mediaSnapshot
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            topMargin: tile.editing ? 32 : 22
            bottomMargin: 23
        }
    }

    GohuText {
        visible: tile.moduleId !== "weather" && tile.moduleId !== "network"
                 && tile.moduleId !== "media"
                 && tile.moduleId !== "cpu"
                 && tile.moduleId !== "uptime"
                 && tile.moduleId !== "apps"
                 && tile.moduleId !== "todo"
                 && tile.moduleId !== "notes"
                 && tile.moduleId !== "calendar"
                 && tile.moduleId !== "time"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 3
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        color: tile.moduleId === "time" ? Colors.white : Colors.orange
        font.pixelSize: tile.moduleId === "time" ? 23 : 14
        text: "MODULE PREVIEW"
    }

    GohuText {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        color: Colors.cyan
        opacity: 0.7
        font.pixelSize: 10
        text: tile.moduleId === "time"
              ? timeMini.statusLine
              : tile.moduleId === "calendar"
              ? calendarMini.statusLine
              : tile.moduleId === "weather" && tile.tileRowSpan > 1
              ? weatherExplore.statusLine
              : tile.moduleId === "weather"
              ? (tile.weatherReady
                 ? (Number(tile.weatherSnapshot.ageMinutes) >= 0
                    ? "WEATHER // FRESH // "
                      + String(tile.weatherSnapshot.ageMinutes) + " MIN OLD"
                    : "WEATHER // FRESH")
                 : "WEATHER // " + tile.weatherStatus)
              : tile.moduleId === "network" && tile.tileRowSpan > 1
              ? networkExplore.statusLine
              : tile.moduleId === "network"
              ? ("NETWORK // " + (tile.networkConnected
                                  ? "LOCAL LINK CONNECTED" : tile.networkState.toUpperCase())
                 + " // INTERNET UNVERIFIED")
              : tile.moduleId === "media" && tile.tileRowSpan > 1
              ? mediaExplore.statusLine
              : tile.moduleId === "media"
              ? "MEDIA // READ ONLY // AUDIO OUTPUT NOT VERIFIED"
              : tile.moduleId === "cpu"
              ? systemMini.statusLine
              : tile.moduleId === "uptime"
              ? uptimeMini.statusLine
              : tile.moduleId === "apps"
              ? appsMini.statusLine
              : tile.moduleId === "todo"
              ? todoMini.statusLine
              : tile.moduleId === "notes"
              ? notesMini.statusLine
              : "DATA ADAPTER NOT CONNECTED"
    }
}
