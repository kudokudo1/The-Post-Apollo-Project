import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationViewerPolicy.js" as ViewerPolicy
import "StationMapProjectionPolicy.js" as MapProjection

// Source-first stage. All records shown come from a backend, never examples.
// MAP now owns a source-driven geographic point canvas plus its event list.
// No basemap or polygon renderer is implied; RADIO remains a stream directory
// before MediaDeck's persistent transport is connected.
Rectangle {
    id: stationDiscovery

    property string domain: "map"
    property bool stationOpen: true
    property bool viewerOpen: false
    property var selectedNews: null
    property string mapFilter: "all"
    property var selectedMapEvent: null
    property real mapZoom: 1
    property real mapCenterLon: 0
    property real mapCenterLat: 0

    readonly property var mapPointRows:
        MapProjection.plottable(source ? source.rows : [])

    readonly property var mapFilterOptions: [
        { "id": "all", "label": "ALL EVENTS", "category": "" },
        { "id": "wildfires", "label": "WILDFIRE", "category": "wildfires" },
        { "id": "severeStorms", "label": "SEVERE STORM", "category": "severeStorms" }
    ]
    readonly property bool mapInspectorOpen:
        domain === "map" && selectedMapEvent !== null

    function mapCategoryForFilter(id) {
        for (let i = 0; i < mapFilterOptions.length; i++) {
            if (mapFilterOptions[i].id === id)
                return mapFilterOptions[i].category;
        }
        return "";
    }

    function mapFilterLabel(id) {
        for (let i = 0; i < mapFilterOptions.length; i++) {
            if (mapFilterOptions[i].id === id)
                return mapFilterOptions[i].label;
        }
        return "ALL EVENTS";
    }

    function selectMapFilter(id) {
        if (domain !== "map" || source.loading || mapFilter === id)
            return;
        selectedMapEvent = null;
        mapFilter = id;
        resetMapView();
        discoveryScroll.contentY = 0;
    }

    function closeMapInspector() {
        selectedMapEvent = null;
    }

    function applyMapView(view) {
        if (!view)
            return;
        mapZoom = view.zoom;
        mapCenterLon = view.centerLon;
        mapCenterLat = view.centerLat;
    }

    function resetMapView() {
        applyMapView(MapProjection.clampView(1, 0, 0));
    }

    function mapPointColor(categoryId) {
        switch (String(categoryId || "")) {
        case "wildfires": return Colors.orange;
        case "severeStorms": return Colors.magenta;
        default: return Colors.cyan;
        }
    }

    // Live MM:SS display, keeping even long provider cooldowns readable.
    function retryClock(value) {
        const seconds = Math.max(0, Math.ceil(Number(value) || 0));
        const mm = Math.floor(seconds / 60);
        const ss = seconds % 60;
        return (mm < 10 ? "0" : "") + mm + ":"
               + (ss < 10 ? "0" : "") + ss;
    }

    // Expose the child provider's actual NEWS state to the Station header.
    // Configured is not the same thing as received articles.
    readonly property string feedBadge: {
        if (source.failed)
            return source.errorText
                   + (source.retryWaitSeconds > 0
                      ? " // RETRY " + stationDiscovery.retryClock(source.retryWaitSeconds) : "");
        if (source.loading)
            return "READING // NEWS";
        if (source.ready)
            return (source.usingCache ? "NEWS CACHED // " : "NEWS RECEIVED // ")
                   + source.rows.length;
        if (source.retryWaitSeconds > 0)
            return "WAIT // RETRY " + stationDiscovery.retryClock(source.retryWaitSeconds);
        return "CONNECTING // NEWS";
    }
    readonly property color feedBadgeColor:
        source.failed ? Colors.orange
        : source.loading ? Colors.orange
        : source.ready ? Colors.magenta : Colors.orange


    // NEWS selection stays in the Station. GDELT supplies a headline record,
    // not verified article body text. MAP uses an internal EONET inspector
    // instead of yanking the operator into an external browser.
    function openRow(row) {
        if (domain === "news") {
            const next = ViewerPolicy.normalizeNews(row);
            if (!next) return;
            selectedNews = next;
            viewerOpen = true;
            return;
        }
        if (domain === "map") {
            if (row)
                selectedMapEvent = row;
            return;
        }
        if (row && row.url)
            Qt.openUrlExternally(row.url);
    }

    function closeViewer() {
        viewerOpen = false;
        selectedNews = null;
    }

    onDomainChanged: {
        closeViewer();
        selectedMapEvent = null;
    }
    onStationOpenChanged: { if (!stationOpen) closeViewer(); }

    readonly property string modeTitle:
        domain === "map" ? "⌖  MAP // EVENT SOURCES"
        : domain === "news" ? "▤  NEWS // HEADLINES"
        : "◉  RADIO // STATIONS"
    readonly property string providerTitle:
        domain === "map" ? "NASA EONET // " + mapFilterLabel(mapFilter)
        : domain === "news" ? "GDELT DOC // WORLD EVENT HEADLINES"
        : "RADIO BROWSER // TOP VOTED STREAMS"
    readonly property string sourceCaution:
        domain === "map" ? "EONET FILTER + INSPECTOR + POINT PLOT CONNECTED // BASEMAP + POLYGON RENDERING NOT YET WIRED"
        : domain === "news" ? "ARTICLE DISCOVERY // NOT YET LIVE VIDEO OR STORY CLUSTERS"
        : "STATION DIRECTORY // PERSISTENT PLAYBACK NOT YET WIRED"
    readonly property var plannedSources: {
        if (domain === "map")
            return [
                {name:"NASA EONET // FILTERED EVENTS + INSPECTOR", state:"SOURCE CONNECTED"},
                {name:"EONET POINT CANVAS // PAN + ZOOM", state:"CONNECTED"},
                {name:"USGS // EARTHQUAKES", state:"GROUND FEED EXISTS"},
                {name:"RAINVIEWER // RADAR TILES", state:"NOT WIRED"},
                {name:"NASA FIRMS // FIRE HOTSPOTS", state:"NOT WIRED"},
                {name:"BASEMAP / POLYGON LAYERS", state:"NOT WIRED"}
            ];
        if (domain === "news")
            return [
                {name:"GDELT DOC // ARTICLE LIST", state:"ENDPOINT CONFIGURED"},
                {name:"TOPICS / SOURCES / REGIONS", state:"NOT WIRED"},
                {name:"LIVE NEWS / VIDEO", state:"NOT WIRED"},
                {name:"STORY CLUSTERS / DOSSIERS", state:"NOT WIRED"}
            ];
        return [
            {name:"RADIO BROWSER // STATION LIST", state:"SOURCE CONNECTED"},
            {name:"COUNTRY / LANGUAGE / TAGS", state:"NOT WIRED"},
            {name:"MEDIA DECK // PERSISTENT PLAYBACK", state:"NOT WIRED"},
            {name:"STATION FAVORITES", state:"NOT WIRED"},
            {name:"RF / SDR / NOAA WEATHER RADIO", state:"HARDWARE LATER"}
        ];
    }

    WeatherServices.StationDiscoveryService {
        id: source
        domain: stationDiscovery.domain
        mapCategory: stationDiscovery.mapCategoryForFilter(
            stationDiscovery.mapFilter
        )
        active: stationDiscovery.stationOpen && stationDiscovery.visible
    }

    color: Colors.black

    Flickable {
        id: discoveryScroll
        anchors.fill: parent
        visible: !stationDiscovery.viewerOpen
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, content.y + content.implicitHeight + 12)

        Column {
            id: content
            x: 20
            y: 12
            width: Math.max(0, discoveryScroll.width - 40)
            spacing: 12

            Row {
                width: parent.width
                spacing: 20

                GohuText {
                    text: stationDiscovery.modeTitle
                    color: Colors.cyan
                    font.pixelSize: 23
                }

                GohuText {
                    text: source.failed ? source.errorText
                          : source.loading ? "RECEIVING"
                          : source.ready
                            ? (source.usingCache ? "CACHED " : "RECEIVED ")
                              + source.rows.length
                            : source.retryWaitSeconds > 0 ? "WAITING" : "OFFLINE"
                    font.pixelSize: 12
                    color: source.failed ? Colors.orange
                           : source.ready ? Colors.cyan : Colors.white
                }
            }

            StationSectionDivider {
                width: parent.width
                title: "SOURCE RACK // WHAT IS CONNECTED"
            }

            Column {
                width: parent.width
                spacing: 5

                Repeater {
                    model: stationDiscovery.plannedSources

                    delegate: Row {
                        required property var modelData
                        width: content.width
                        spacing: 16

                        GohuText {
                            width: Math.max(150, content.width - 250)
                            text: modelData.name
                            color: Colors.white
                            font.pixelSize: 12
                        }

                        GohuText {
                            text: modelData.state
                            color: modelData.state === "SOURCE CONNECTED"
                                   || modelData.state === "CONNECTED"
                                   || modelData.state === "GROUND FEED EXISTS"
                                   ? Colors.cyan : Colors.orange
                            font.pixelSize: 11
                        }
                    }
                }
            }

            StationSectionDivider {
                width: parent.width
                title: stationDiscovery.providerTitle
            }

            Row {
                id: mapFilterRail
                width: parent.width
                height: stationDiscovery.domain === "map" ? 34 : 0
                visible: stationDiscovery.domain === "map"
                spacing: 8

                Repeater {
                    model: stationDiscovery.mapFilterOptions

                    delegate: ModeButton {
                        required property var modelData
                        width: modelData.id === "severeStorms" ? 156 : 136
                        height: 32
                        textOnly: true
                        horizontalContent: true
                        bordered: false
                        selected: stationDiscovery.mapFilter === modelData.id
                        interactive: !source.loading
                        labelText: modelData.label
                        labelFontSize: 10
                        idlePrimaryColor: Colors.cyan
                        selectedPrimaryColor: Colors.magenta
                        perimeterGlowColor: Colors.orange
                        onTriggered:
                            stationDiscovery.selectMapFilter(modelData.id)
                    }
                }

                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: source.usingCache
                          ? "SESSION CACHE // 15m"
                          : source.loading ? "QUERYING EONET"
                            : "ONE ACTIVE EONET QUERY"
                    font.pixelSize: 9
                }
            }

            Column {
                id: mapCanvasSection
                width: parent.width
                spacing: 7
                visible: stationDiscovery.domain === "map"

                StationSectionDivider {
                    width: parent.width
                    title: "SPATIAL PLOT // EONET POINT GEOMETRIES"
                }

                Row {
                    width: parent.width
                    height: 28
                    spacing: 10

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 120)
                        text: "PLOTTABLE "
                              + stationDiscovery.mapPointRows.length
                              + " / " + source.rows.length
                              + " // WHEEL ZOOM // DRAG PAN"
                        font.pixelSize: 9
                    }

                    ActionButton {
                        width: 110
                        height: 26
                        label: "RESET VIEW"
                        labelPixelSize: 10
                        available: stationDiscovery.mapZoom > 1.001
                                   || Math.abs(stationDiscovery.mapCenterLon) > 0.001
                                   || Math.abs(stationDiscovery.mapCenterLat) > 0.001
                        onClicked: stationDiscovery.resetMapView()
                    }
                }

                Rectangle {
                    id: mapPlot
                    width: parent.width
                    height: 270
                    clip: true
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    readonly property var longitudeGrid:
                        [-180, -120, -60, 0, 60, 120, 180]
                    readonly property var latitudeGrid:
                        [-90, -60, -30, 0, 30, 60, 90]

                    Repeater {
                        model: mapPlot.longitudeGrid

                        delegate: Rectangle {
                            required property var modelData
                            readonly property var projected:
                                MapProjection.project(
                                    modelData,
                                    stationDiscovery.mapCenterLat,
                                    mapPlot.width,
                                    mapPlot.height,
                                    stationDiscovery.mapZoom,
                                    stationDiscovery.mapCenterLon,
                                    stationDiscovery.mapCenterLat
                                )
                            width: Number(modelData) === 0 ? 2 : 1
                            height: mapPlot.height
                            x: projected.x - width / 2
                            visible: projected.valid
                                     && projected.x >= 0
                                     && projected.x <= mapPlot.width
                            color: Number(modelData) === 0
                                   ? Colors.cyan : Colors.white
                            opacity: Number(modelData) === 0 ? 0.42 : 0.14
                            z: 0
                        }
                    }

                    Repeater {
                        model: mapPlot.latitudeGrid

                        delegate: Rectangle {
                            required property var modelData
                            readonly property var projected:
                                MapProjection.project(
                                    stationDiscovery.mapCenterLon,
                                    modelData,
                                    mapPlot.width,
                                    mapPlot.height,
                                    stationDiscovery.mapZoom,
                                    stationDiscovery.mapCenterLon,
                                    stationDiscovery.mapCenterLat
                                )
                            width: mapPlot.width
                            height: Number(modelData) === 0 ? 2 : 1
                            y: projected.y - height / 2
                            visible: projected.valid
                                     && projected.y >= 0
                                     && projected.y <= mapPlot.height
                            color: Number(modelData) === 0
                                   ? Colors.cyan : Colors.white
                            opacity: Number(modelData) === 0 ? 0.42 : 0.14
                            z: 0
                        }
                    }

                    MouseArea {
                        id: mapPanArea
                        anchors.fill: parent
                        z: 1
                        acceptedButtons: Qt.LeftButton
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: pressed
                                     ? Qt.ClosedHandCursor
                                     : Qt.OpenHandCursor

                        property real previousX: 0
                        property real previousY: 0

                        onPressed: function(mouse) {
                            previousX = mouse.x;
                            previousY = mouse.y;
                        }

                        onPositionChanged: function(mouse) {
                            if (!pressed)
                                return;
                            const view = MapProjection.pan(
                                stationDiscovery.mapZoom,
                                stationDiscovery.mapCenterLon,
                                stationDiscovery.mapCenterLat,
                                mouse.x - previousX,
                                mouse.y - previousY,
                                mapPlot.width,
                                mapPlot.height
                            );
                            stationDiscovery.applyMapView(view);
                            previousX = mouse.x;
                            previousY = mouse.y;
                        }

                        onWheel: function(wheel) {
                            const direction = wheel.angleDelta.y > 0 ? 1
                                            : wheel.angleDelta.y < 0 ? -1 : 0;
                            const view = MapProjection.zoomAt(
                                stationDiscovery.mapZoom,
                                stationDiscovery.mapCenterLon,
                                stationDiscovery.mapCenterLat,
                                wheel.x,
                                wheel.y,
                                mapPlot.width,
                                mapPlot.height,
                                direction
                            );
                            stationDiscovery.applyMapView(view);
                            wheel.accepted = true;
                        }

                        onDoubleClicked:
                            stationDiscovery.resetMapView()
                    }

                    Repeater {
                        model: stationDiscovery.mapPointRows

                        delegate: Item {
                            required property var modelData
                            readonly property var projected:
                                MapProjection.project(
                                    modelData.longitude,
                                    modelData.latitude,
                                    mapPlot.width,
                                    mapPlot.height,
                                    stationDiscovery.mapZoom,
                                    stationDiscovery.mapCenterLon,
                                    stationDiscovery.mapCenterLat
                                )

                            width: 16
                            height: 16
                            x: projected.x - width / 2
                            y: projected.y - height / 2
                            visible: projected.visible
                            z: 2

                            Rectangle {
                                anchors.centerIn: parent
                                width: 9
                                height: 9
                                rotation: 45
                                color: Colors.black
                                border.width: 2
                                border.color:
                                    stationDiscovery.selectedMapEvent
                                    && stationDiscovery.selectedMapEvent.id
                                       === modelData.id
                                    ? Colors.yellow
                                    : stationDiscovery.mapPointColor(
                                          modelData.categoryId
                                      )
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked:
                                    stationDiscovery.selectedMapEvent = modelData
                            }
                        }
                    }

                    QuietText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 7
                        z: 3
                        text: "LAT/LON GRID // NO BASEMAP"
                        color: Colors.orange
                        font.pixelSize: 9
                    }

                    QuietText {
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.margins: 7
                        z: 3
                        text: "ZOOM "
                              + stationDiscovery.mapZoom.toFixed(2)
                              + "x // CENTER "
                              + stationDiscovery.mapCenterLat.toFixed(1)
                              + "°, "
                              + stationDiscovery.mapCenterLon.toFixed(1)
                              + "°"
                        font.pixelSize: 9
                    }

                    QuietText {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 7
                        z: 3
                        text: "POINTS ONLY // POLYGONS LISTED BELOW"
                        font.pixelSize: 9
                    }
                }
            }

            Row {
                width: parent.width
                height: stationDiscovery.domain === "news" ? 34 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 12
                ActionButton {
                    width: 102
                    height: 30
                    label: "RETRY NEWS"
                    labelPixelSize: 11
                    available: source.canRetry
                    onClicked: source.refresh(true)
                }
                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: source.retryWaitSeconds > 0
                          ? "EARLIEST RETRY IN " + stationDiscovery.retryClock(source.retryWaitSeconds)
                          : source.failed && source.errorText === "RATE LIMITED"
                            ? "RETRY MAY STILL BE THROTTLED"
                          : source.failed ? "REQUEST FAILED // RETRY AVAILABLE"
                          : source.loading ? "REQUEST IN PROGRESS"
                          : "ON DEMAND // 15-MIN REFRESH"
                    font.pixelSize: 11
                }
            }

            QuietText {
                width: parent.width
                text: stationDiscovery.sourceCaution
                font.pixelSize: 11
            }

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.mapInspectorOpen

                StationSectionDivider {
                    width: parent.width
                    title: "EVENT INSPECTOR // NASA EONET"
                }

                Rectangle {
                    width: parent.width
                    height: stationDiscovery.selectedMapEvent
                            && stationDiscovery.selectedMapEvent.description
                            ? 172 : 142
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 5

                        Row {
                            width: parent.width
                            spacing: 10

                            GohuText {
                                width: Math.max(0, parent.width - 96)
                                text: stationDiscovery.selectedMapEvent
                                      ? stationDiscovery.selectedMapEvent.title
                                      : ""
                                color: Colors.white
                                elide: Text.ElideRight
                                font.pixelSize: 15
                            }

                            ActionButton {
                                width: 86
                                height: 26
                                label: "CLOSE"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                destructive: true
                                onClicked:
                                    stationDiscovery.closeMapInspector()
                            }
                        }

                        SecondaryText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEvent
                                  ? stationDiscovery.selectedMapEvent.category
                                    + " // "
                                    + stationDiscovery.selectedMapEvent.coordinates
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 11
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEvent
                                  ? "OBSERVED // "
                                    + stationDiscovery.selectedMapEvent.time
                                    + " // GEOMETRY // "
                                    + stationDiscovery.selectedMapEvent.geometryType
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEvent
                                  ? "MAGNITUDE // "
                                    + stationDiscovery.selectedMapEvent.magnitude
                                    + " // SOURCES // "
                                    + stationDiscovery.selectedMapEvent.sourceNames
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            visible: stationDiscovery.selectedMapEvent
                                     && stationDiscovery.selectedMapEvent.description
                                     !== ""
                            width: parent.width
                            text: stationDiscovery.selectedMapEvent
                                  ? stationDiscovery.selectedMapEvent.description
                                  : ""
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }
                    }
                }
            }

            QuietText {
                visible: source.failed || !source.ready || source.rows.length === 0
                width: parent.width
                text: source.failed
                      ? source.errorText + " // PRIOR DATA MAY BE STALE"
                      : source.loading ? "RECEIVING REMOTE RECORDS"
                      : source.retryWaitSeconds > 0
                        ? "REQUEST HELD // PROVIDER COOLDOWN"
                      : source.ready ? "NO RECORDS RETURNED"
                        : "BACKEND NOT YET AVAILABLE"
                font.pixelSize: 12
            }

            Repeater {
                model: source.ready ? source.rows : []

                delegate: Rectangle {
                    required property var modelData
                    width: content.width
                    height: 88
                    color: Colors.dark
                    border.width: 1
                    border.color: entryMouse.containsMouse ? Colors.yellow
                                  : Colors.cyan

                    Column {
                        anchors.left: parent.left
                        anchors.right: openLabel.left
                        anchors.top: parent.top
                        anchors.leftMargin: 12
                        anchors.topMargin: 8
                        anchors.rightMargin: 12
                        spacing: 6

                        GohuText {
                            width: parent.width
                            text: modelData.title
                            color: Colors.white
                            elide: Text.ElideRight
                            font.pixelSize: 15
                        }

                        SecondaryText {
                            width: parent.width
                            text: modelData.detail
                            elide: Text.ElideRight
                            font.pixelSize: 12
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.time
                            elide: Text.ElideRight
                            font.pixelSize: 10
                        }
                    }

                    GohuText {
                        id: openLabel
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: 12
                        text: stationDiscovery.domain === "news" ? "VIEW HERE"
                              : stationDiscovery.domain === "map" ? "INSPECT HERE"
                              : modelData.url !== "" ? modelData.action : "NO LINK"
                        color: entryMouse.containsMouse ? Colors.yellow : Colors.cyan
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: entryMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: stationDiscovery.domain === "news"
                                     || stationDiscovery.domain === "map"
                                     || modelData.url !== ""
                                     ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: stationDiscovery.openRow(modelData)
                    }
                }
            }

            QuietText {
                width: parent.width
                text: source.ready
                      ? "LAST RECEIVED // "
                        + Qt.formatDateTime(source.lastUpdated, "hh:mm") + " LOCAL"
                      : "LAST RECEIVED // --"
                font.pixelSize: 11
            }
        }
    }

    // Destroy the optional webpage when backing out, retaining the discovery
    // list position and its existing provider connection.
    Component {
        id: newsViewerComponent
        StationViewerHost {
            selectedRecord: stationDiscovery.selectedNews
            onBackRequested: stationDiscovery.closeViewer()
        }
    }
    Loader {
        anchors.fill: parent
        active: stationDiscovery.viewerOpen
        sourceComponent: newsViewerComponent
        z: 3
    }

    NeonScrollBar {
        flickable: discoveryScroll
        handleStyle: "star"
        geometryHost: stationDiscovery
        visible: !stationDiscovery.viewerOpen && scrollable
    }
}
