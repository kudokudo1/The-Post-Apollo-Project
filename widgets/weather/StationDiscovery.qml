import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationViewerPolicy.js" as ViewerPolicy
import "../../services/weather/StationDiscoveryPolicy.js" as DiscoveryPolicy
import "StationMapProjectionPolicy.js" as MapProjection
import "StationNaturalEarthLand110.js" as NaturalEarthLand
import "StationNaturalEarthContext110.js" as NaturalEarthContext
import "../../services/weather/FirmsHotspotPolicy.js" as FirmsAreaPolicy
import "StationRadarPolicy.js" as RadarPolicy
import "../../services/weather/HmsSmokePolicy.js" as SmokePolicy
import "../../services/weather/SeismicPolicy.js" as SeismicPolicy

// Source-first stage. All records shown come from a backend, never examples.
// MAP owns a local Natural Earth geographic basemap plus source-driven data
// overlays and its event list. RADIO remains a stream directory
// before MediaDeck's persistent transport is connected.
Rectangle {
    id: stationDiscovery

    property string domain: "map"
    property bool stationOpen: true
    property bool viewerOpen: false
    property var selectedNews: null
    property var newsMentionOverlay: null
    property var seismicSource: null
    signal newsMapRequested(var payload)
    signal newsMapClearRequested()
    readonly property bool newsLocationMatchesSelection:
        selectedNews
        && articleLocationService.requestedUrl !== ""
        && articleLocationService.requestedUrl === selectedNews.url
    property string newsTopic: "all"
    property string newsSourceQuery: ""
    property string newsLanguageQuery: ""
    property string newsSourceRegion: ""
    property int newsMaxAgeHours: 0
    readonly property var newsTopicOptions: [
        { "id": "all", "label": "ALL" },
        { "id": "weather", "label": "WEATHER" },
        { "id": "earth", "label": "EARTH" },
        { "id": "fire", "label": "FIRE" },
        { "id": "space", "label": "SPACE" }
    ]
    readonly property var newsTimeOptions: [
        { "hours": 0, "label": "ALL 24H" },
        { "hours": 1, "label": "1H" },
        { "hours": 3, "label": "3H" },
        { "hours": 6, "label": "6H" },
        { "hours": 12, "label": "12H" },
        { "hours": 24, "label": "24H" }
    ]
    readonly property var newsRegionBaseRows:
        domain === "news"
        ? DiscoveryPolicy.filterNewsRows(
              source && Array.isArray(source.rows) ? source.rows : [],
              newsTopic,
              newsSourceQuery,
              newsLanguageQuery,
              newsMaxAgeHours,
              source ? source.sourceClockMs : 0,
              ""
          ) : []
    readonly property var newsSourceRegionGroups:
        DiscoveryPolicy.newsSourceRegionGroups(newsRegionBaseRows)
    readonly property var newsRegionOptions: {
        const options = [{
            "id": "",
            "label": "ALL SOURCES",
            "articles": newsRegionBaseRows.length,
            "publishers": 0
        }];
        const groups = newsSourceRegionGroups.slice(0, 5);
        for (let i = 0; i < groups.length; i++) {
            options.push({
                "id": groups[i].country,
                "label": groups[i].country.toUpperCase(),
                "articles": groups[i].articles,
                "publishers": groups[i].publishers
            });
        }
        return options;
    }
    readonly property var visibleRows:
        domain === "news"
        ? DiscoveryPolicy.filterNewsRows(
              source && Array.isArray(source.rows) ? source.rows : [],
              newsTopic,
              newsSourceQuery,
              newsLanguageQuery,
              newsMaxAgeHours,
              source ? source.sourceClockMs : 0,
              newsSourceRegion
          )
        : (source && Array.isArray(source.rows) ? source.rows : [])
    readonly property var newsVisibleSummary:
        DiscoveryPolicy.newsBatchSummary(visibleRows)
    readonly property var newsReportingTrend:
        DiscoveryPolicy.newsReportingTrend(
            visibleRows,
            source ? source.sourceClockMs : 0,
            4,
            6
        )
    readonly property var newsStoryFamilies:
        DiscoveryPolicy.newsStoryFamilies(visibleRows)

    property string mapFilter: "all"
    property var selectedMapEvent: null
    property var selectedMapHotspot: null
    property var selectedMapNewsMention: null
    property var selectedMapEarthquake: null
    property bool mapShowEarthquakes: true
    property bool mapShowCountryBorders: true
    property bool mapShowAdmin1: false
    property bool mapShowPlaces: true
    property real mapZoom: 1
    property real mapCenterLon: 0
    property real mapCenterLat: 0

    readonly property var mapPointRows:
        MapProjection.plottable(source ? source.rows : [])
    readonly property var mapNewsMentionRows:
        MapProjection.plottable(
            newsMentionOverlay
            && Array.isArray(newsMentionOverlay.locations)
            ? newsMentionOverlay.locations : []
        )
    readonly property var mapEarthquakeRows:
        mapShowEarthquakes
        && seismicSource
        && seismicSource.ready
        ? MapProjection.plottable(seismicSource.events)
        : []
    readonly property var mapPlaceRows:
        mapShowPlaces
        ? NaturalEarthContext.placesForZoom(mapZoom)
        : []
    readonly property var mapVisibleBounds:
        MapProjection.visibleBounds(
            mapPlot ? mapPlot.width : 0,
            mapPlot ? mapPlot.height : 0,
            mapZoom, mapCenterLon, mapCenterLat
        )
    readonly property var firmsArea:
        firmsService
        ? FirmsAreaPolicy.boundedArea(mapVisibleBounds, 60, 40)
        : { "valid": false, "reason": "FIRMS SERVICE UNAVAILABLE" }
    readonly property var radarArea:
        RadarPolicy.boundedArea(mapVisibleBounds, 90, 50)
    readonly property bool firmsAreaReady:
        firmsArea && firmsArea.valid
    readonly property bool radarAreaReady:
        radarArea && radarArea.valid
    property string radarImageUrl: ""
    property var radarSnapshotBounds: null
    property int radarHistoryMinutes: 0
    property int radarLoadedHistoryMinutes: 0
    property double radarRequestedTimeMs: 0
    property date radarRequestedAt
    readonly property var radarHistoryOptions:
        RadarPolicy.historyOptions()
    readonly property var smokeSummary:
        hmsSmokeService ? hmsSmokeService.summary
                        : { "count": 0, "light": 0, "medium": 0, "heavy": 0 }
    readonly property bool hotspotInspectorOpen:
        domain === "map" && selectedMapHotspot !== null
    readonly property bool newsMentionInspectorOpen:
        domain === "map" && selectedMapNewsMention !== null
    readonly property bool earthquakeInspectorOpen:
        domain === "map" && selectedMapEarthquake !== null

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

    function newsTopicLabel(id) {
        for (let i = 0; i < newsTopicOptions.length; i++) {
            if (newsTopicOptions[i].id === id)
                return newsTopicOptions[i].label;
        }
        return "ALL";
    }

    function selectNewsTopic(id) {
        if (domain !== "news" || newsTopic === id)
            return;
        newsTopic = id;
        discoveryScroll.contentY = 0;
    }

    function selectNewsTime(hours) {
        const next = Number(hours);
        if (domain !== "news" || newsMaxAgeHours === next)
            return;
        newsMaxAgeHours = next;
        discoveryScroll.contentY = 0;
    }

    function selectNewsRegion(id) {
        const next = String(id || "");
        if (domain !== "news" || newsSourceRegion === next)
            return;
        newsSourceRegion = next;
        discoveryScroll.contentY = 0;
    }

    function newsTrendColor(direction) {
        switch (String(direction || "")) {
        case "RISING": return Colors.magenta;
        case "FALLING": return Colors.blue;
        case "SPARSE": return Colors.yellow;
        case "NO TIME DATA": return Colors.orange;
        default: return Colors.cyan;
        }
    }

    function newsAgeLabel(millis) {
        const seen = Number(millis);
        const now = source ? Number(source.sourceClockMs) : NaN;
        if (!isFinite(seen) || seen <= 0 || !isFinite(now) || now <= seen)
            return seen > 0 ? "<1m" : "--";
        const minutes = Math.floor((now - seen) / 60000);
        if (minutes < 60)
            return minutes + "m";
        const hours = Math.floor(minutes / 60);
        return hours + "h";
    }

    function selectMapFilter(id) {
        if (domain !== "map" || source.loading || mapFilter === id)
            return;
        selectedMapEvent = null;
        selectedMapHotspot = null;
        selectedMapNewsMention = null;
        selectedMapEarthquake = null;
        mapFilter = id;
        resetMapView();
        discoveryScroll.contentY = 0;
    }

    function closeMapInspector() {
        selectedMapEvent = null;
    }

    function closeHotspotInspector() {
        selectedMapHotspot = null;
    }

    function closeNewsMentionInspector() {
        selectedMapNewsMention = null;
    }

    function requestNewsMapHandoff() {
        if (domain !== "news"
                || !selectedNews
                || !articleLocationService.ready
                || articleLocationService.rows.length === 0)
            return false;

        const copiedRows = JSON.parse(
            JSON.stringify(articleLocationService.rows)
        );
        newsMapRequested({
            "articleTitle": String(selectedNews.title || ""),
            "articleUrl": String(selectedNews.url || ""),
            "articleSource": String(selectedNews.source || ""),
            "articleTime": String(selectedNews.time || ""),
            "gkgSliceUtc": String(articleLocationService.sliceUtc || ""),
            "matchMethod": String(articleLocationService.matchMethod || ""),
            "semantics": String(
                articleLocationService.semantics
                || "MENTIONED LOCATIONS, NOT VERIFIED EVENT LOCATIONS"
            ),
            "locations": copiedRows
        });
        return true;
    }

    function focusNewsMentions() {
        if (domain !== "map" || mapNewsMentionRows.length === 0)
            return false;
        applyMapView(MapProjection.fitRows(mapNewsMentionRows, 1.35));
        return true;
    }

    function fetchVisibleHotspots() {
        if (!firmsService || !firmsAreaReady)
            return false;
        selectedMapHotspot = null;
        return firmsService.request(mapVisibleBounds);
    }

    function selectRadarHistory(minutes) {
        radarHistoryMinutes =
            RadarPolicy.normalizeHistoryMinutes(minutes);
    }

    function radarHistoryLabel(minutes) {
        const value = Number(minutes);
        if (!isFinite(value) || value <= 0)
            return "NOW";
        if (value < 60)
            return "-" + Math.round(value) + "M";
        return "-" + Math.round(value / 60) + "H";
    }

    function loadRadarSnapshot() {
        if (!radarAreaReady || radarImage.status === Image.Loading)
            return false;
        const snapshot = RadarPolicy.snapshot(radarArea);
        const requestNow = Date.now();
        const historicalTime = RadarPolicy.historyTimeMillis(
            requestNow,
            radarHistoryMinutes
        );
        const nextUrl = RadarPolicy.exportImageUrl(
            radarArea,
            Math.round(mapPlot.width),
            Math.round(mapPlot.height),
            historicalTime
        );
        if (!snapshot || nextUrl === "")
            return false;

        radarSnapshotBounds = snapshot;
        radarRequestedAt = new Date(requestNow);
        radarLoadedHistoryMinutes = radarHistoryMinutes;
        radarRequestedTimeMs = historicalTime;
        // Explicit empty -> next URL guarantees a manual same-viewport refresh
        // even with the Image cache disabled.
        radarImageUrl = "";
        Qt.callLater(function() {
            stationDiscovery.radarImageUrl = nextUrl;
        });
        return true;
    }

    function clearRadarSnapshot() {
        radarImageUrl = "";
        radarSnapshotBounds = null;
        radarLoadedHistoryMinutes = 0;
        radarRequestedTimeMs = 0;
    }

    function loadSmokePolygons() {
        if (!hmsSmokeService || hmsSmokeService.loading)
            return false;
        return hmsSmokeService.request();
    }

    function clearSmokePolygons() {
        if (hmsSmokeService)
            hmsSmokeService.clear();
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

    function earthquakeDepthColor(depthKm) {
        const band = SeismicPolicy.depthBand(depthKm);
        switch (String(band.token || "")) {
        case "orange": return Colors.orange;
        case "cyan": return Colors.cyan;
        case "blue": return Colors.blue;
        default: return Colors.white;
        }
    }

    function closeEarthquakeInspector() {
        selectedMapEarthquake = null;
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
            if (!articleLocationService.loading)
                articleLocationService.clear();
            selectedNews = next;
            viewerOpen = true;
            return;
        }
        if (domain === "map") {
            if (row) {
                selectedMapHotspot = null;
                selectedMapNewsMention = null;
                selectedMapEarthquake = null;
                selectedMapEvent = row;
            }
            return;
        }
        if (row && row.url)
            Qt.openUrlExternally(row.url);
    }

    function closeViewer() {
        viewerOpen = false;
        selectedNews = null;
        if (!articleLocationService.loading)
            articleLocationService.clear();
    }

    onDomainChanged: {
        closeViewer();
        selectedMapEvent = null;
        selectedMapHotspot = null;
        selectedMapNewsMention = null;
        selectedMapEarthquake = null;
    }
    onNewsMentionOverlayChanged: {
        selectedMapNewsMention = null;
        if (domain === "map" && mapNewsMentionRows.length > 0)
            focusNewsMentions();
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
        domain === "map" ? "NATURAL EARTH + EONET + USGS EARTHQUAKES + FIRMS + MRMS + HMS SMOKE"
        : domain === "news" ? "ARTICLE DISCOVERY // LOCAL FILTERS // EXACT-HEADLINE SOURCE GROUPS // NOT FUZZY STORY CLUSTERING"
        : "STATION DIRECTORY // PERSISTENT PLAYBACK NOT YET WIRED"
    readonly property var plannedSources: {
        if (domain === "map")
            return [
                {name:"NASA EONET // FILTERED EVENTS + INSPECTOR", state:"SOURCE CONNECTED"},
                {name:"NATURAL EARTH 1:110m LAND BASEMAP", state:"CONNECTED"},
                {
                    name:"NATURAL EARTH ADMIN-0 REFERENCE BOUNDARIES",
                    state: mapShowCountryBorders ? "VISIBLE" : "HIDDEN"
                },
                {
                    name:"NATURAL EARTH ADMIN-1 STATE/PROVINCE LINES",
                    state: mapShowAdmin1 ? "VISIBLE" : "HIDDEN"
                },
                {
                    name:"NATURAL EARTH POPULATED PLACES",
                    state: mapShowPlaces ? "VISIBLE" : "HIDDEN"
                },
                {name:"EONET POINT CANVAS // PAN + ZOOM", state:"CONNECTED"},
                {
                    name:"GDELT NEWS MENTION POINTS",
                    state: mapNewsMentionRows.length > 0
                           ? "LOADED " + mapNewsMentionRows.length
                           : "READY FROM NEWS"
                },
                {
                    name:"USGS // M2.5+ EARTHQUAKES // 24H",
                    state: seismicSource
                           ? (seismicSource.ready
                              ? "LOADED " + seismicSource.events.length
                              : seismicSource.loading
                                ? "RECEIVING"
                                : seismicSource.failed
                                  ? "ERROR" : "WAITING")
                           : "UNAVAILABLE"
                },
                {
                    name:"NOAA/NWS MRMS // BASE REFLECTIVITY + 4H HISTORY",
                    state: radarImage.status === Image.Ready
                           ? "FRAME "
                             + radarHistoryLabel(radarLoadedHistoryMinutes)
                           : "MANUAL READY"
                },
                {name:"RAINVIEWER // RADAR FALLBACK", state:"NOT WIRED"},
                {
                    name:"NOAA HMS // SMOKE PLUME POLYGONS",
                    state: hmsSmokeService.ready
                           ? "LOADED " + hmsSmokeService.polygons.length
                           : "MANUAL READY"
                },
                {
                    name:"NASA FIRMS // VIIRS NOAA-21 HOTSPOTS",
                    state: firmsService.configured
                           ? (firmsService.ready
                              ? "FETCHED " + firmsService.hotspots.length
                              : "MANUAL READY")
                           : "KEY REQUIRED"
                },
                {name:"OTHER POLYGON LAYERS", state:"NOT WIRED"}
            ];
        if (domain === "news")
            return [
                {name:"GDELT DOC // ARTICLE LIST", state:"ENDPOINT CONFIGURED"},
                {name:"LOCAL TOPIC FILTER + URL/TITLE DEDUPE", state:"CONNECTED"},
                {name:"PUBLISHER / SOURCE COUNTRY FILTER", state:"CONNECTED"},
                {name:"LANGUAGE + TIME WINDOW FILTERS", state:"CONNECTED"},
                {name:"EXACT-HEADLINE SOURCE GROUPS", state:"CONNECTED"},
                {name:"SOURCE-COUNTRY REGION GROUPS", state:"CONNECTED"},
                {name:"REPORTING TREND / SOURCE COUNT", state:"CONNECTED"},
                {name:"CONSERVATIVE STORY FAMILIES", state:"CONNECTED"},
                {name:"ARTICLE → GKG MENTIONED LOCATIONS", state:"CONNECTED"},
                {name:"NEWS → MAP LOCATION HANDOFF", state:"CONNECTED"},
                {name:"LIVE NEWS / VIDEO", state:"NOT WIRED"},
                {name:"SEMANTIC / EMBEDDING DOSSIERS", state:"NOT WIRED"}
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

    WeatherServices.FirmsHotspotService {
        id: firmsService
    }

    WeatherServices.HmsSmokeService {
        id: hmsSmokeService
    }

    WeatherServices.GdeltArticleLocationService {
        id: articleLocationService
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
                                   || modelData.state === "MANUAL READY"
                                   || modelData.state === "SNAPSHOT LOADED"
                                   || modelData.state === "VISIBLE"
                                   || String(modelData.state).indexOf("FETCHED ") === 0
                                   || String(modelData.state).indexOf("LOADED ") === 0
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
                    title: "SPATIAL PLOT // USGS QUAKES + EONET + FIRMS + NEWS"
                }

                QuietText {
                    width: parent.width
                    text: "BASEMAP // NATURAL EARTH 1:110m LAND // PUBLIC DOMAIN // LOCAL ASSET // NO TILE NETWORK"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 8

                    ActionButton {
                        width: 126
                        height: 28
                        label: "BORDERS: "
                               + (stationDiscovery.mapShowCountryBorders
                                  ? "ON" : "OFF")
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        selected: stationDiscovery.mapShowCountryBorders
                        onClicked:
                            stationDiscovery.mapShowCountryBorders =
                                !stationDiscovery.mapShowCountryBorders
                    }

                    ActionButton {
                        width: 116
                        height: 28
                        label: "STATES: "
                               + (stationDiscovery.mapShowAdmin1
                                  ? "ON" : "OFF")
                        labelPixelSize: 9
                        accentColor: Colors.blue
                        selected: stationDiscovery.mapShowAdmin1
                        onClicked:
                            stationDiscovery.mapShowAdmin1 =
                                !stationDiscovery.mapShowAdmin1
                    }

                    ActionButton {
                        width: 116
                        height: 28
                        label: "PLACES: "
                               + (stationDiscovery.mapShowPlaces
                                  ? "ON" : "OFF")
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        selected: stationDiscovery.mapShowPlaces
                        onClicked:
                            stationDiscovery.mapShowPlaces =
                                !stationDiscovery.mapShowPlaces
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 382)
                        text: "REFERENCE CARTOGRAPHY // DISPUTED / CLAIM LINES ARE DISTINCT // NOT A LEGAL POSITION"
                        elide: Text.ElideRight
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 10

                    ActionButton {
                        width: 152
                        height: 28
                        label: "EARTHQUAKES: "
                               + (stationDiscovery.mapShowEarthquakes
                                  ? "ON" : "OFF")
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        selected: stationDiscovery.mapShowEarthquakes
                        onClicked:
                            stationDiscovery.mapShowEarthquakes =
                                !stationDiscovery.mapShowEarthquakes
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 162)
                        text: stationDiscovery.seismicSource
                              ? (stationDiscovery.seismicSource.ready
                                 ? "USGS M2.5+ // "
                                   + stationDiscovery.mapEarthquakeRows.length
                                   + " PLOTTABLE // SIZE=MAGNITUDE // COLOR=DEPTH"
                                 : stationDiscovery.seismicSource.loading
                                   ? "USGS // RECEIVING"
                                   : stationDiscovery.seismicSource.failed
                                     ? stationDiscovery.seismicSource.errorText
                                     : "USGS // WAITING")
                              : "USGS // SHARED SOURCE UNAVAILABLE"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: Colors.orange
                    }
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

                Row {
                    width: parent.width
                    height: stationDiscovery.mapNewsMentionRows.length > 0 ? 30 : 0
                    visible: stationDiscovery.mapNewsMentionRows.length > 0
                    spacing: 10

                    ActionButton {
                        width: 132
                        height: 28
                        label: "FOCUS NEWS"
                        labelPixelSize: 10
                        accentColor: Colors.magenta
                        onClicked: stationDiscovery.focusNewsMentions()
                    }

                    ActionButton {
                        width: 118
                        height: 28
                        label: "CLEAR NEWS"
                        labelPixelSize: 10
                        accentColor: Colors.orange
                        onClicked: stationDiscovery.newsMapClearRequested()
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 270)
                        text: "NEWS MENTIONS // "
                              + stationDiscovery.mapNewsMentionRows.length
                              + " // "
                              + (stationDiscovery.newsMentionOverlay
                                 ? stationDiscovery.newsMentionOverlay.articleTitle
                                 : "")
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: Colors.magenta
                    }
                }

                StationSectionDivider {
                    width: parent.width
                    title: "FIRE HOTSPOTS // NASA FIRMS"
                }

                Row {
                    width: parent.width
                    height: 32
                    spacing: 10

                    ActionButton {
                        width: 142
                        height: 30
                        label: "FETCH HOTSPOTS"
                        labelPixelSize: 10
                        available: firmsService.configured
                                   && stationDiscovery.firmsAreaReady
                                   && !firmsService.loading
                        accentColor: Colors.orange
                        onClicked:
                            stationDiscovery.fetchVisibleHotspots()
                    }

                    GohuText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 190
                        text: !firmsService.configured
                              ? "KEY REQUIRED"
                              : firmsService.loading
                                ? "FETCHING"
                                : firmsService.failed
                                  ? firmsService.errorText
                                  : firmsService.ready
                                    ? "HOTSPOTS " + firmsService.hotspots.length
                                    : stationDiscovery.firmsAreaReady
                                      ? "MANUAL READY"
                                      : stationDiscovery.firmsArea.reason
                        elide: Text.ElideRight
                        font.pixelSize: 10
                        color: !firmsService.configured ? Colors.orange
                               : firmsService.failed ? Colors.yellow
                               : firmsService.ready ? Colors.orange
                               : Colors.cyan
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 352)
                        text: firmsService.ready
                              ? "LAST BBOX // " + firmsService.lastBounds
                              : "ONE DAY // MAX 60° × 40° VIEW // NO AUTO-FETCH"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                QuietText {
                    width: parent.width
                    text: "POST_APOLLO_FIRMS_MAP_KEY // OPTIONAL // KEY NEVER SHOWN OR PASSED IN PROCESS ARGV"
                    font.pixelSize: 9
                    color: Colors.orange
                }

                StationSectionDivider {
                    width: parent.width
                    title: "RADAR // NOAA/NWS MRMS BASE REFLECTIVITY + 4H HISTORY"
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 7

                    Repeater {
                        model: stationDiscovery.radarHistoryOptions

                        delegate: ModeButton {
                            required property var modelData
                            width: 74
                            height: 28
                            textOnly: true
                            horizontalContent: true
                            bordered: false
                            selected:
                                stationDiscovery.radarHistoryMinutes
                                === modelData.minutes
                            labelText: modelData.label
                            labelFontSize: 9
                            idlePrimaryColor: Colors.cyan
                            selectedPrimaryColor: Colors.magenta
                            perimeterGlowColor: Colors.orange
                            onTriggered:
                                stationDiscovery.selectRadarHistory(
                                    modelData.minutes
                                )
                        }
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 390)
                        text: "SELECT FRAME // THEN LOAD // NOAA TIME WINDOW // NO AUTO-FETCH"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                Row {
                    width: parent.width
                    height: 32
                    spacing: 10

                    ActionButton {
                        width: 142
                        height: 30
                        label: stationDiscovery.radarImageUrl !== ""
                               ? "REFRESH RADAR" : "LOAD RADAR"
                        labelPixelSize: 10
                        available: stationDiscovery.radarAreaReady
                                   && radarImage.status !== Image.Loading
                        accentColor: Colors.cyan
                        onClicked:
                            stationDiscovery.loadRadarSnapshot()
                    }

                    ActionButton {
                        width: 90
                        height: 30
                        label: "CLEAR"
                        labelPixelSize: 10
                        available: stationDiscovery.radarImageUrl !== ""
                                   || stationDiscovery.radarSnapshotBounds !== null
                        onClicked:
                            stationDiscovery.clearRadarSnapshot()
                    }

                    GohuText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 170
                        text: !stationDiscovery.radarAreaReady
                              ? stationDiscovery.radarArea.reason
                              : radarImage.status === Image.Loading
                                ? "LOADING"
                                : radarImage.status === Image.Error
                                  ? "IMAGE ERROR"
                                  : radarImage.status === Image.Ready
                                    ? "RADAR LOADED"
                                    : "MANUAL READY"
                        elide: Text.ElideRight
                        font.pixelSize: 10
                        color: radarImage.status === Image.Error ? Colors.yellow
                               : radarImage.status === Image.Ready ? Colors.cyan
                               : Colors.white
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 432)
                        text: radarImage.status === Image.Ready
                              ? "LOADED "
                                + stationDiscovery.radarHistoryLabel(
                                      stationDiscovery
                                      .radarLoadedHistoryMinutes
                                  )
                                + (stationDiscovery
                                   .radarRequestedTimeMs > 0
                                   ? " // "
                                     + Qt.formatDateTime(
                                           new Date(
                                               stationDiscovery
                                               .radarRequestedTimeMs
                                           ),
                                           "hh:mm"
                                       )
                                     + " UTC TARGET"
                                   : " // LATEST AVAILABLE")
                                + " // SNAPSHOT TRACKS MAP"
                              : "MAX 90° × 50° VIEW // MANUAL LOAD // NO PAN AUTO-FETCH"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                QuietText {
                    width: parent.width
                    text: "NOAA / NWS / MRMS // OFFICIAL BASE REFLECTIVITY // 4H MOVING HISTORY // COVERAGE IS NOT GLOBAL"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                StationSectionDivider {
                    width: parent.width
                    title: "SMOKE PLUMES // NOAA HMS"
                }

                Row {
                    width: parent.width
                    height: 32
                    spacing: 10

                    ActionButton {
                        width: 142
                        height: 30
                        label: hmsSmokeService.ready
                               ? "REFRESH SMOKE" : "LOAD SMOKE"
                        labelPixelSize: 10
                        available: !hmsSmokeService.loading
                        accentColor: Colors.yellow
                        onClicked:
                            stationDiscovery.loadSmokePolygons()
                    }

                    ActionButton {
                        width: 90
                        height: 30
                        label: "CLEAR"
                        labelPixelSize: 10
                        available: hmsSmokeService.ready
                        onClicked:
                            stationDiscovery.clearSmokePolygons()
                    }

                    GohuText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 180
                        text: hmsSmokeService.loading ? "LOADING"
                              : hmsSmokeService.failed
                                ? hmsSmokeService.errorText
                                : hmsSmokeService.ready
                                  ? "PLUMES " + hmsSmokeService.polygons.length
                                  : "MANUAL READY"
                        elide: Text.ElideRight
                        font.pixelSize: 10
                        color: hmsSmokeService.failed ? Colors.yellow
                               : hmsSmokeService.ready ? Colors.yellow
                               : Colors.white
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 442)
                        text: hmsSmokeService.ready
                              ? "PRODUCT " + hmsSmokeService.analysisDate
                                + " // AGE " + hmsSmokeService.ageDays + "d"
                              : "LATEST AVAILABLE DAILY ANALYSIS // NO AUTO-FETCH"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                Row {
                    width: parent.width
                    spacing: 16

                    QuietText {
                        text: "LIGHT " + stationDiscovery.smokeSummary.light
                              + " // MEDIUM " + stationDiscovery.smokeSummary.medium
                              + " // HEAVY " + stationDiscovery.smokeSummary.heavy
                        font.pixelSize: 9
                        color: Colors.white
                    }

                    QuietText {
                        text: hmsSmokeService.truncated
                              ? "SOURCE CLIPPED BY SAFETY LIMIT"
                              : "QUALITATIVE PLUME DENSITY // NOT GROUND-LEVEL PM2.5"
                        font.pixelSize: 9
                        color: hmsSmokeService.truncated ? Colors.orange
                                                       : Colors.cyan
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

                    Canvas {
                        id: basemapCanvas
                        anchors.fill: parent
                        z: 0.05

                        property var landPolygons: NaturalEarthLand.polygons
                        property real viewZoom: stationDiscovery.mapZoom
                        property real viewCenterLon: stationDiscovery.mapCenterLon
                        property real viewCenterLat: stationDiscovery.mapCenterLat

                        onLandPolygonsChanged: requestPaint()
                        onViewZoomChanged: requestPaint()
                        onViewCenterLonChanged: requestPaint()
                        onViewCenterLatChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()

                        function projectedRing(rawRing, offset) {
                            const ring = SmokePolicy.unwrapRing(rawRing);
                            if (ring.length < 4)
                                return [];

                            const points = [];
                            let minX = Infinity;
                            let maxX = -Infinity;
                            let minY = Infinity;
                            let maxY = -Infinity;

                            for (let i = 0; i < ring.length; i++) {
                                const point = MapProjection.projectUnwrapped(
                                    ring[i][0] + offset,
                                    ring[i][1],
                                    width,
                                    height,
                                    viewZoom,
                                    viewCenterLon,
                                    viewCenterLat
                                );
                                if (!point.valid)
                                    return [];
                                points.push(point);
                                minX = Math.min(minX, point.x);
                                maxX = Math.max(maxX, point.x);
                                minY = Math.min(minY, point.y);
                                maxY = Math.max(maxY, point.y);
                            }

                            if (maxX < 0 || minX > width
                                    || maxY < 0 || minY > height)
                                return [];
                            return points;
                        }

                        function drawRing(ctx, points) {
                            if (!points || points.length < 4)
                                return false;
                            ctx.beginPath();
                            ctx.moveTo(points[0].x, points[0].y);
                            for (let i = 1; i < points.length; i++)
                                ctx.lineTo(points[i].x, points[i].y);
                            ctx.closePath();
                            return true;
                        }

                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            const offsets = [-360, 0, 360];

                            for (let polygonIndex = 0;
                                 polygonIndex < landPolygons.length;
                                 polygonIndex++) {
                                const polygon = landPolygons[polygonIndex];
                                if (!Array.isArray(polygon)
                                        || polygon.length === 0)
                                    continue;

                                for (let copy = 0;
                                     copy < offsets.length;
                                     copy++) {
                                    const offset = offsets[copy];
                                    const outer = projectedRing(
                                        polygon[0], offset
                                    );
                                    if (!drawRing(ctx, outer))
                                        continue;

                                    ctx.fillStyle = "rgba(22,5,31,0.96)";
                                    ctx.strokeStyle = "rgba(85,207,202,0.58)";
                                    ctx.lineWidth = 1;
                                    ctx.fill();
                                    ctx.stroke();

                                    // Natural Earth land contains rare interior
                                    // holes. Paint those back to Station ocean
                                    // rather than claiming they are land.
                                    for (let ringIndex = 1;
                                         ringIndex < polygon.length;
                                         ringIndex++) {
                                        const hole = projectedRing(
                                            polygon[ringIndex], offset
                                        );
                                        if (!drawRing(ctx, hole))
                                            continue;
                                        ctx.fillStyle = "#1B0623";
                                        ctx.fill();
                                    }
                                }
                            }
                        }
                    }

                    Canvas {
                        id: mapContextLineCanvas
                        anchors.fill: parent
                        z: 0.08
                        visible: stationDiscovery.mapShowCountryBorders
                                 || stationDiscovery.mapShowAdmin1

                        property var countryLines:
                            NaturalEarthContext.admin0Lines
                        property var admin1Lines:
                            NaturalEarthContext.admin1Lines
                        property bool showCountry:
                            stationDiscovery.mapShowCountryBorders
                        property bool showAdmin1:
                            stationDiscovery.mapShowAdmin1
                        property real viewZoom: stationDiscovery.mapZoom
                        property real viewCenterLon: stationDiscovery.mapCenterLon
                        property real viewCenterLat: stationDiscovery.mapCenterLat

                        onCountryLinesChanged: requestPaint()
                        onAdmin1LinesChanged: requestPaint()
                        onShowCountryChanged: requestPaint()
                        onShowAdmin1Changed: requestPaint()
                        onViewZoomChanged: requestPaint()
                        onViewCenterLonChanged: requestPaint()
                        onViewCenterLatChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()

                        function projectedLine(rawLine, offset) {
                            if (!Array.isArray(rawLine)
                                    || rawLine.length < 2)
                                return [];
                            const points = [];
                            let minX = Infinity;
                            let maxX = -Infinity;
                            let minY = Infinity;
                            let maxY = -Infinity;

                            for (let i = 0; i < rawLine.length; i++) {
                                const point = rawLine[i];
                                if (!Array.isArray(point)
                                        || point.length < 2)
                                    return [];
                                const projected =
                                    MapProjection.projectUnwrapped(
                                        Number(point[0]) + offset,
                                        Number(point[1]),
                                        width,
                                        height,
                                        viewZoom,
                                        viewCenterLon,
                                        viewCenterLat
                                    );
                                if (!projected.valid)
                                    return [];
                                points.push(projected);
                                minX = Math.min(minX, projected.x);
                                maxX = Math.max(maxX, projected.x);
                                minY = Math.min(minY, projected.y);
                                maxY = Math.max(maxY, projected.y);
                            }

                            if (maxX < 0 || minX > width
                                    || maxY < 0 || minY > height)
                                return [];
                            return points;
                        }

                        function strokeLine(ctx, points, color, lineWidth) {
                            if (!points || points.length < 2)
                                return;
                            ctx.beginPath();
                            ctx.moveTo(points[0].x, points[0].y);
                            for (let i = 1; i < points.length; i++)
                                ctx.lineTo(points[i].x, points[i].y);
                            ctx.strokeStyle = color;
                            ctx.lineWidth = lineWidth;
                            ctx.stroke();
                        }

                        function disputedClass(value) {
                            const text = String(value || "").toLowerCase();
                            return text.indexOf("disputed") >= 0
                                || text.indexOf("claim") >= 0
                                || text.indexOf("line of control") >= 0
                                || text.indexOf("indefinite") >= 0
                                || text.indexOf("indeterminant") >= 0;
                        }

                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            const offsets = [-360, 0, 360];

                            if (showCountry) {
                                for (let rowIndex = 0;
                                     rowIndex < countryLines.length;
                                     rowIndex++) {
                                    const row = countryLines[rowIndex];
                                    const disputed = disputedClass(
                                        row.className
                                    );
                                    for (let copy = 0;
                                         copy < offsets.length;
                                         copy++) {
                                        strokeLine(
                                            ctx,
                                            projectedLine(
                                                row.line,
                                                offsets[copy]
                                            ),
                                            disputed
                                            ? "rgba(242,190,78,0.74)"
                                            : "rgba(220,243,250,0.34)",
                                            disputed ? 1.25 : 0.8
                                        );
                                    }
                                }
                            }

                            if (showAdmin1 && viewZoom >= 1.6) {
                                for (let rowIndex = 0;
                                     rowIndex < admin1Lines.length;
                                     rowIndex++) {
                                    const row = admin1Lines[rowIndex];
                                    for (let copy = 0;
                                         copy < offsets.length;
                                         copy++) {
                                        strokeLine(
                                            ctx,
                                            projectedLine(
                                                row.line,
                                                offsets[copy]
                                            ),
                                            "rgba(91,95,212,0.30)",
                                            0.7
                                        );
                                    }
                                }
                            }
                        }
                    }

                    Image {
                        id: radarImage
                        readonly property var northWest:
                            stationDiscovery.radarSnapshotBounds
                            ? MapProjection.project(
                                stationDiscovery.radarSnapshotBounds.west,
                                stationDiscovery.radarSnapshotBounds.north,
                                mapPlot.width,
                                mapPlot.height,
                                stationDiscovery.mapZoom,
                                stationDiscovery.mapCenterLon,
                                stationDiscovery.mapCenterLat
                              )
                            : { "valid": false, "x": 0, "y": 0 }
                        readonly property var southEast:
                            stationDiscovery.radarSnapshotBounds
                            ? MapProjection.project(
                                stationDiscovery.radarSnapshotBounds.east,
                                stationDiscovery.radarSnapshotBounds.south,
                                mapPlot.width,
                                mapPlot.height,
                                stationDiscovery.mapZoom,
                                stationDiscovery.mapCenterLon,
                                stationDiscovery.mapCenterLat
                              )
                            : { "valid": false, "x": 0, "y": 0 }

                        source: stationDiscovery.radarImageUrl
                        cache: false
                        asynchronous: true
                        fillMode: Image.Stretch
                        smooth: true
                        opacity: 0.68
                        z: 0.1

                        x: northWest.valid ? northWest.x : 0
                        y: northWest.valid ? northWest.y : 0
                        width: northWest.valid && southEast.valid
                               ? Math.max(0, southEast.x - northWest.x) : 0
                        height: northWest.valid && southEast.valid
                                ? Math.max(0, southEast.y - northWest.y) : 0
                        visible: source !== ""
                                 && northWest.valid && southEast.valid
                                 && width > 0 && height > 0
                    }

                    Canvas {
                        id: smokeCanvas
                        anchors.fill: parent
                        z: 0.2

                        property var smokeRows: hmsSmokeService.polygons
                        property real viewZoom: stationDiscovery.mapZoom
                        property real viewCenterLon: stationDiscovery.mapCenterLon
                        property real viewCenterLat: stationDiscovery.mapCenterLat

                        onSmokeRowsChanged: requestPaint()
                        onViewZoomChanged: requestPaint()
                        onViewCenterLonChanged: requestPaint()
                        onViewCenterLatChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()

                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            const offsets = [-360, 0, 360];

                            for (let rowIndex = 0;
                                 rowIndex < smokeRows.length;
                                 rowIndex++) {
                                const row = smokeRows[rowIndex];
                                const ring = SmokePolicy.unwrapRing(row.ring);
                                if (ring.length < 4)
                                    continue;

                                for (let copy = 0; copy < offsets.length; copy++) {
                                    const offset = offsets[copy];
                                    const projected = [];
                                    let minX = Infinity;
                                    let maxX = -Infinity;
                                    let minY = Infinity;
                                    let maxY = -Infinity;

                                    for (let i = 0; i < ring.length; i++) {
                                        const point = MapProjection.projectUnwrapped(
                                            ring[i][0] + offset,
                                            ring[i][1],
                                            width,
                                            height,
                                            viewZoom,
                                            viewCenterLon,
                                            viewCenterLat
                                        );
                                        if (!point.valid) {
                                            projected.length = 0;
                                            break;
                                        }
                                        projected.push(point);
                                        minX = Math.min(minX, point.x);
                                        maxX = Math.max(maxX, point.x);
                                        minY = Math.min(minY, point.y);
                                        maxY = Math.max(maxY, point.y);
                                    }

                                    if (projected.length < 4
                                            || maxX < 0 || minX > width
                                            || maxY < 0 || minY > height)
                                        continue;

                                    ctx.beginPath();
                                    ctx.moveTo(projected[0].x, projected[0].y);
                                    for (let i = 1; i < projected.length; i++)
                                        ctx.lineTo(projected[i].x, projected[i].y);
                                    ctx.closePath();
                                    ctx.fillStyle = SmokePolicy.fillStyle(row.density);
                                    ctx.strokeStyle = SmokePolicy.strokeStyle(row.density);
                                    ctx.lineWidth = 1;
                                    ctx.fill();
                                    ctx.stroke();
                                }
                            }
                        }
                    }

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
                            z: 0.3
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
                            z: 0.3
                        }
                    }

                    Canvas {
                        id: mapPlaceLabelCanvas
                        anchors.fill: parent
                        z: 0.45
                        visible: stationDiscovery.mapShowPlaces

                        property var placeRows:
                            stationDiscovery.mapPlaceRows
                        property real viewZoom: stationDiscovery.mapZoom
                        property real viewCenterLon: stationDiscovery.mapCenterLon
                        property real viewCenterLat: stationDiscovery.mapCenterLat

                        onPlaceRowsChanged: requestPaint()
                        onViewZoomChanged: requestPaint()
                        onViewCenterLonChanged: requestPaint()
                        onViewCenterLatChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()

                        function collides(box, used) {
                            for (let i = 0; i < used.length; i++) {
                                const other = used[i];
                                if (box.x < other.x + other.w + 3
                                        && box.x + box.w + 3 > other.x
                                        && box.y < other.y + other.h + 2
                                        && box.y + box.h + 2 > other.y)
                                    return true;
                            }
                            return false;
                        }

                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            const used = [];
                            ctx.font =
                                "9px 'GohuFont 11 Nerd Font Mono'";
                            ctx.textBaseline = "alphabetic";

                            for (let i = 0; i < placeRows.length; i++) {
                                const row = placeRows[i];
                                const point = MapProjection.project(
                                    row.longitude,
                                    row.latitude,
                                    width,
                                    height,
                                    viewZoom,
                                    viewCenterLon,
                                    viewCenterLat
                                );
                                if (!point.visible)
                                    continue;

                                const labelWidth = Math.min(
                                    118,
                                    Math.max(24, row.name.length * 5.4)
                                );
                                let labelX = point.x + 5;
                                let labelY = point.y - 3;
                                if (labelX + labelWidth + 3 > width)
                                    labelX = point.x - labelWidth - 5;
                                if (labelY - 9 < 0)
                                    labelY = point.y + 11;

                                const box = {
                                    "x": labelX - 2,
                                    "y": labelY - 9,
                                    "w": labelWidth + 4,
                                    "h": 12
                                };
                                if (collides(box, used))
                                    continue;
                                used.push(box);

                                const accent =
                                    row.adm0cap ? "#C74EC7"
                                    : (row.worldcity || row.megacity)
                                      ? "#55CFCA" : "#DCF3FA";
                                ctx.fillStyle = "rgba(27,6,35,0.82)";
                                ctx.fillRect(
                                    box.x, box.y, box.w, box.h
                                );
                                ctx.fillStyle = accent;
                                ctx.fillRect(
                                    point.x - 1.5,
                                    point.y - 1.5,
                                    3,
                                    3
                                );
                                ctx.fillText(
                                    row.name,
                                    labelX,
                                    labelY
                                );
                            }
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
                        model: stationDiscovery.mapEarthquakeRows

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
                            readonly property real quakeRadius:
                                SeismicPolicy.magnitudeRadius(
                                    modelData.magnitude
                                )

                            width: quakeRadius * 2 + 8
                            height: quakeRadius * 2 + 8
                            x: projected.x - width / 2
                            y: projected.y - height / 2
                            visible: projected.visible
                            z: 2.15

                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.quakeRadius * 2
                                height: parent.quakeRadius * 2
                                radius: width / 2
                                color: stationDiscovery.earthquakeDepthColor(
                                    modelData.depthKm
                                )
                                opacity: 0.82
                                border.width:
                                    stationDiscovery.selectedMapEarthquake
                                       === modelData ? 2 : 1
                                border.color:
                                    stationDiscovery.selectedMapEarthquake
                                       === modelData
                                    ? Colors.yellow : Colors.white
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    stationDiscovery.selectedMapEvent = null;
                                    stationDiscovery.selectedMapHotspot = null;
                                    stationDiscovery.selectedMapNewsMention = null;
                                    stationDiscovery.selectedMapEarthquake = modelData;
                                }
                            }
                        }
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
                                onClicked: {
                                    stationDiscovery.selectedMapHotspot = null;
                                    stationDiscovery.selectedMapNewsMention = null;
                                    stationDiscovery.selectedMapEarthquake = null;
                                    stationDiscovery.selectedMapEvent = modelData;
                                }
                            }
                        }
                    }

                    Repeater {
                        model: stationDiscovery.mapNewsMentionRows

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

                            width: 18
                            height: 18
                            x: projected.x - width / 2
                            y: projected.y - height / 2
                            visible: projected.visible
                            z: 2.2

                            Rectangle {
                                anchors.centerIn: parent
                                width: 10
                                height: 10
                                radius: 5
                                color: Colors.magenta
                                border.width: 2
                                border.color:
                                    stationDiscovery.selectedMapNewsMention
                                       === modelData
                                    ? Colors.yellow : Colors.white
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    stationDiscovery.selectedMapEvent = null;
                                    stationDiscovery.selectedMapHotspot = null;
                                    stationDiscovery.selectedMapEarthquake = null;
                                    stationDiscovery.selectedMapNewsMention = modelData;
                                }
                            }
                        }
                    }

                    Repeater {
                        model: firmsService.ready ? firmsService.hotspots : []

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

                            width: 14
                            height: 14
                            x: projected.x - width / 2
                            y: projected.y - height / 2
                            visible: projected.visible
                            z: 2

                            Rectangle {
                                anchors.centerIn: parent
                                width: 7
                                height: 7
                                radius: 3.5
                                color: Colors.orange
                                border.width: 1
                                border.color:
                                    stationDiscovery.selectedMapHotspot
                                    && stationDiscovery.selectedMapHotspot.id
                                       === modelData.id
                                    ? Colors.yellow : Colors.white
                                opacity:
                                    modelData.confidenceLabel === "HIGH" ? 1.0
                                    : modelData.confidenceLabel === "NOMINAL"
                                      ? 0.82 : 0.62
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    stationDiscovery.selectedMapEvent = null;
                                    stationDiscovery.selectedMapNewsMention = null;
                                    stationDiscovery.selectedMapEarthquake = null;
                                    stationDiscovery.selectedMapHotspot = modelData;
                                }
                            }
                        }
                    }

                    QuietText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 7
                        z: 3
                        text: "NATURAL EARTH LAND + CONTEXT // LAT/LON GRID // RADAR + SMOKE OVERLAYS"
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
                        text: "QUAKES CIRCLES // EONET DIAMONDS // FIRMS ORANGE // NEWS MAGENTA"
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

            Row {
                id: newsTopicRail
                width: parent.width
                height: stationDiscovery.domain === "news" ? 34 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 7

                Repeater {
                    model: stationDiscovery.newsTopicOptions

                    delegate: ModeButton {
                        required property var modelData
                        width: modelData.id === "weather" ? 122 : 102
                        height: 32
                        textOnly: true
                        horizontalContent: true
                        bordered: false
                        selected: stationDiscovery.newsTopic === modelData.id
                        labelText: modelData.label
                        labelFontSize: 10
                        idlePrimaryColor: Colors.cyan
                        selectedPrimaryColor: Colors.magenta
                        perimeterGlowColor: Colors.orange
                        onTriggered:
                            stationDiscovery.selectNewsTopic(modelData.id)
                    }
                }

                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(0, parent.width - 550)
                    text: source.ready
                          ? "SHOWING "
                            + stationDiscovery.visibleRows.length
                            + " / " + source.rows.length
                            + " // LOCAL FILTER"
                            + (stationDiscovery.newsSourceQuery !== ""
                               ? " // SOURCE MATCH" : "")
                            + (stationDiscovery.newsSourceRegion !== ""
                               ? " // REGION "
                                 + stationDiscovery.newsSourceRegion.toUpperCase()
                               : "")
                          : "LOCAL FILTER // WAITING FOR HEADLINES"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Row {
                id: newsSourceFilter
                width: parent.width
                height: stationDiscovery.domain === "news" ? 34 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 8

                Rectangle {
                    width: 320
                    height: 30
                    color: Colors.dark
                    border.width: 1
                    border.color: newsSourceInput.activeFocus
                                  ? Colors.magenta : Colors.cyan

                    QuietText {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 10
                        visible: newsSourceInput.text.length === 0
                                 && !newsSourceInput.activeFocus
                        text: "PUBLISHER DOMAIN / SOURCE COUNTRY"
                        font.pixelSize: 10
                    }

                    TextInput {
                        id: newsSourceInput
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: Colors.white
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        font.family: "GohuFont 11 Nerd Font Mono"
                        font.pixelSize: 11
                        clip: true
                        text: stationDiscovery.newsSourceQuery
                        onTextEdited:
                            stationDiscovery.newsSourceQuery = text
                        Keys.onEscapePressed: {
                            stationDiscovery.newsSourceQuery = "";
                            text = "";
                            event.accepted = true;
                        }
                    }
                }

                ActionButton {
                    width: 72
                    height: 30
                    label: "CLEAR"
                    labelPixelSize: 10
                    available: stationDiscovery.newsSourceQuery !== ""
                    onClicked: {
                        stationDiscovery.newsSourceQuery = "";
                        newsSourceInput.text = "";
                    }
                }

                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(0, parent.width - 408)
                    text: stationDiscovery.newsSourceQuery === ""
                          ? "LOCAL // MATCHES GDELT DOMAIN OR SOURCE COUNTRY"
                          : "MATCH // "
                            + stationDiscovery.newsSourceQuery.toUpperCase()
                            + " // "
                            + stationDiscovery.visibleRows.length
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Row {
                id: newsTimeRail
                width: parent.width
                height: stationDiscovery.domain === "news" ? 34 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 7

                Repeater {
                    model: stationDiscovery.newsTimeOptions

                    delegate: ModeButton {
                        required property var modelData
                        width: modelData.hours === 0 ? 102 : 68
                        height: 32
                        textOnly: true
                        horizontalContent: true
                        bordered: false
                        selected:
                            stationDiscovery.newsMaxAgeHours
                            === modelData.hours
                        labelText: modelData.label
                        labelFontSize: 10
                        idlePrimaryColor: Colors.cyan
                        selectedPrimaryColor: Colors.magenta
                        perimeterGlowColor: Colors.orange
                        onTriggered:
                            stationDiscovery.selectNewsTime(
                                modelData.hours
                            )
                    }
                }

                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(0, parent.width - 478)
                    text: stationDiscovery.newsMaxAgeHours > 0
                          ? "AGE ≤ "
                            + stationDiscovery.newsMaxAgeHours
                            + "H // LOCAL SEENDATE FILTER"
                          : "FULL GDELT 24H BATCH"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Row {
                id: newsLanguageFilter
                width: parent.width
                height: stationDiscovery.domain === "news" ? 34 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 8

                Rectangle {
                    width: 250
                    height: 30
                    color: Colors.dark
                    border.width: 1
                    border.color: newsLanguageInput.activeFocus
                                  ? Colors.magenta : Colors.cyan

                    QuietText {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 10
                        visible: newsLanguageInput.text.length === 0
                                 && !newsLanguageInput.activeFocus
                        text: "LANGUAGE / CODE"
                        font.pixelSize: 10
                    }

                    TextInput {
                        id: newsLanguageInput
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: Colors.white
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        font.family: "GohuFont 11 Nerd Font Mono"
                        font.pixelSize: 11
                        clip: true
                        text: stationDiscovery.newsLanguageQuery
                        onTextEdited:
                            stationDiscovery.newsLanguageQuery = text
                        Keys.onEscapePressed: {
                            stationDiscovery.newsLanguageQuery = "";
                            text = "";
                            event.accepted = true;
                        }
                    }
                }

                ActionButton {
                    width: 72
                    height: 30
                    label: "CLEAR"
                    labelPixelSize: 10
                    available:
                        stationDiscovery.newsLanguageQuery !== ""
                    onClicked: {
                        stationDiscovery.newsLanguageQuery = "";
                        newsLanguageInput.text = "";
                    }
                }

                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(0, parent.width - 338)
                    text: "BATCH // "
                          + stationDiscovery.newsVisibleSummary.publishers
                          + " PUBLISHERS // "
                          + stationDiscovery.newsVisibleSummary.countries
                          + " COUNTRIES // "
                          + stationDiscovery.newsVisibleSummary.languages
                          + " LANGUAGES"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Row {
                id: newsRegionRail
                width: parent.width
                height: stationDiscovery.domain === "news" ? 42 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 7

                Repeater {
                    model: stationDiscovery.newsRegionOptions

                    delegate: ModeButton {
                        required property var modelData
                        width: modelData.id === "" ? 112 : 124
                        height: 32
                        textOnly: true
                        horizontalContent: true
                        bordered: false
                        selected:
                            stationDiscovery.newsSourceRegion
                            === modelData.id
                        labelText: modelData.label
                        labelFontSize: 9
                        idlePrimaryColor: Colors.cyan
                        selectedPrimaryColor: Colors.magenta
                        perimeterGlowColor: Colors.orange
                        onTriggered:
                            stationDiscovery.selectNewsRegion(
                                modelData.id
                            )
                    }
                }

                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(
                        0,
                        parent.width
                        - stationDiscovery.newsRegionOptions.length * 131
                    )
                    text: stationDiscovery.newsSourceRegion === ""
                          ? "SOURCE COUNTRY GROUPS // TOP BATCH COUNTRIES"
                          : "SOURCE REGION // "
                            + stationDiscovery.newsSourceRegion.toUpperCase()
                            + " // "
                            + stationDiscovery.visibleRows.length
                            + " ARTICLES"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.domain === "news"

                StationSectionDivider {
                    width: parent.width
                    title: "REPORTING TREND // CURRENT FILTERED BATCH"
                }

                Row {
                    width: parent.width
                    spacing: 12

                    Rectangle {
                        width: 174
                        height: 104
                        color: Colors.dark
                        border.width: 1
                        border.color: stationDiscovery.newsTrendColor(
                            stationDiscovery.newsReportingTrend.direction
                        )

                        Column {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 5

                            SecondaryText {
                                text: "LAST 24H // 4H BUCKETS"
                                font.pixelSize: 8
                            }

                            GohuText {
                                text: stationDiscovery.newsReportingTrend.direction
                                font.pixelSize: 14
                                color: stationDiscovery.newsTrendColor(
                                    stationDiscovery.newsReportingTrend.direction
                                )
                            }

                            QuietText {
                                text: "RECENT // "
                                      + stationDiscovery.newsReportingTrend.recentArticles
                                      + " ARTICLES"
                                font.pixelSize: 8
                            }

                            QuietText {
                                text: "PRIOR // "
                                      + stationDiscovery.newsReportingTrend.previousArticles
                                      + " ARTICLES"
                                font.pixelSize: 8
                            }

                            QuietText {
                                text: "TIMED // "
                                      + stationDiscovery.newsReportingTrend.timedRows
                                font.pixelSize: 8
                            }
                        }
                    }

                    Row {
                        id: newsTrendBars
                        width: Math.max(0, parent.width - 186)
                        spacing: 7

                        Repeater {
                            model: stationDiscovery.newsReportingTrend.buckets

                            delegate: Column {
                                required property var modelData
                                width: Math.max(
                                    64,
                                    (newsTrendBars.width
                                     - 5 * newsTrendBars.spacing) / 6
                                )
                                spacing: 3

                                Item {
                                    width: parent.width
                                    height: 72

                                    Rectangle {
                                        anchors.bottom: parent.bottom
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.horizontalCenterOffset: -9
                                        width: 12
                                        height:
                                            stationDiscovery.newsReportingTrend.maxArticles > 0
                                            ? 6 + 58
                                              * modelData.articles
                                              / stationDiscovery.newsReportingTrend.maxArticles
                                            : 6
                                        color: Colors.orange
                                    }

                                    Rectangle {
                                        anchors.bottom: parent.bottom
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.horizontalCenterOffset: 9
                                        width: 12
                                        height:
                                            stationDiscovery.newsReportingTrend.maxSources > 0
                                            ? 6 + 58
                                              * modelData.sources
                                              / stationDiscovery.newsReportingTrend.maxSources
                                            : 6
                                        color: Colors.cyan
                                    }
                                }

                                QuietText {
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter
                                    text: modelData.label
                                    font.pixelSize: 8
                                }

                                QuietText {
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter
                                    text: "A" + modelData.articles
                                          + " // S" + modelData.sources
                                    font.pixelSize: 8
                                }
                            }
                        }
                    }
                }

                QuietText {
                    width: parent.width
                    text: "ORANGE = ARTICLES // CYAN = UNIQUE PUBLISHERS // LOCAL HISTOGRAM FROM GDELT SEENDATE // FILTER CHANGES RECOMPUTE WITHOUT REFETCH"
                    font.pixelSize: 9
                    color: Colors.orange
                }

                StationSectionDivider {
                    width: parent.width
                    title: "STORY FAMILIES // CONSERVATIVE TITLE TOKENS"
                }

                Column {
                    width: parent.width
                    spacing: 5
                    visible: stationDiscovery.newsStoryFamilies.length > 0

                    Repeater {
                        model: stationDiscovery.newsStoryFamilies.slice(0, 4)

                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 82
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta

                            Column {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text: modelData.title
                                    elide: Text.ElideRight
                                    font.pixelSize: 11
                                    color: Colors.white
                                }

                                QuietText {
                                    width: parent.width
                                    text: modelData.variantCount
                                          + " TITLE VARIANTS // "
                                          + modelData.sourceCount
                                          + " SOURCES // "
                                          + modelData.articleRecords
                                          + " SOURCE RECORDS"
                                    elide: Text.ElideRight
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                }

                                QuietText {
                                    width: parent.width
                                    text: "COUNTRIES // "
                                          + (modelData.countries.length
                                             ? modelData.countries.join(" / ")
                                             : "--")
                                          + " // TOPICS // "
                                          + (modelData.topics.length
                                             ? modelData.topics.join(" / ").toUpperCase()
                                             : "OTHER")
                                    elide: Text.ElideRight
                                    font.pixelSize: 8
                                }

                                QuietText {
                                    width: parent.width
                                    text: "STRONGEST TOKEN JACCARD // "
                                          + Math.round(
                                                modelData.strongestJaccard * 100
                                            )
                                          + "% // LATEST "
                                          + stationDiscovery.newsAgeLabel(
                                                modelData.latestSeenMillis
                                            )
                                          + " AGO"
                                    elide: Text.ElideRight
                                    font.pixelSize: 8
                                    color: Colors.magenta
                                }
                            }
                        }
                    }
                }

                QuietText {
                    visible: stationDiscovery.newsStoryFamilies.length === 0
                    width: parent.width
                    text: "NO MULTI-HEADLINE FAMILY CLEARS THE STRICT LOCAL TOKEN THRESHOLD IN THIS FILTERED BATCH"
                    font.pixelSize: 9
                }

                QuietText {
                    width: parent.width
                    text: "LOCAL TITLE-TOKEN CLUSTERS // ≥3 SHARED TOKENS + ≥75% SHORTER-TITLE OVERLAP + ≥62% JACCARD // NOT EMBEDDING SEMANTICS OR VERIFIED EVENT IDENTITY"
                    font.pixelSize: 9
                    color: Colors.orange
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
                visible: stationDiscovery.earthquakeInspectorOpen

                StationSectionDivider {
                    width: parent.width
                    title: "EARTHQUAKE INSPECTOR // USGS"
                }

                Rectangle {
                    width: parent.width
                    height: 170
                    color: Colors.dark
                    border.width: 1
                    border.color: stationDiscovery.selectedMapEarthquake
                                  ? stationDiscovery.earthquakeDepthColor(
                                        stationDiscovery.selectedMapEarthquake
                                            .depthKm
                                    )
                                  : Colors.orange

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 5

                        Row {
                            width: parent.width
                            spacing: 10

                            GohuText {
                                width: Math.max(0, parent.width - 96)
                                text: stationDiscovery.selectedMapEarthquake
                                      ? "M "
                                        + stationDiscovery.selectedMapEarthquake
                                          .magnitude.toFixed(1)
                                        + " // "
                                        + stationDiscovery.selectedMapEarthquake
                                          .place
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
                                    stationDiscovery.closeEarthquakeInspector()
                            }
                        }

                        SecondaryText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEarthquake
                                  ? SeismicPolicy.depthBand(
                                        stationDiscovery.selectedMapEarthquake
                                            .depthKm
                                    ).label
                                    + " // DEPTH "
                                    + (stationDiscovery.selectedMapEarthquake
                                       .depthKm >= 0
                                       ? stationDiscovery.selectedMapEarthquake
                                         .depthKm.toFixed(1) + " KM"
                                       : "--")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 11
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEarthquake
                                  ? stationDiscovery.selectedMapEarthquake.utc
                                    + " // "
                                    + stationDiscovery.selectedMapEarthquake
                                      .latitude.toFixed(3)
                                    + ", "
                                    + stationDiscovery.selectedMapEarthquake
                                      .longitude.toFixed(3)
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEarthquake
                                  ? "SIG "
                                    + stationDiscovery.selectedMapEarthquake
                                      .significance
                                    + " // "
                                    + (stationDiscovery.selectedMapEarthquake
                                       .magType !== ""
                                       ? stationDiscovery.selectedMapEarthquake
                                         .magType.toUpperCase()
                                       : "MAG TYPE --")
                                    + " // STATUS "
                                    + (stationDiscovery.selectedMapEarthquake
                                       .status !== ""
                                       ? stationDiscovery.selectedMapEarthquake
                                         .status.toUpperCase()
                                       : "--")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapEarthquake
                                  ? "TSUNAMI FLAG // "
                                    + (stationDiscovery.selectedMapEarthquake
                                       .tsunami ? "YES" : "NO")
                                    + (stationDiscovery.selectedMapEarthquake
                                       .alert !== ""
                                       ? " // ALERT "
                                         + stationDiscovery
                                           .selectedMapEarthquake.alert
                                           .toUpperCase()
                                       : "")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                            color: stationDiscovery.selectedMapEarthquake
                                   && stationDiscovery.selectedMapEarthquake
                                      .tsunami
                                   ? Colors.orange : Colors.cyan
                        }

                        QuietText {
                            width: parent.width
                            text: "USGS OBSERVED EVENT // M2.5+ PAST DAY FEED // NOT AN EARTHQUAKE PREDICTION"
                            elide: Text.ElideRight
                            font.pixelSize: 9
                            color: Colors.orange
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.newsMentionInspectorOpen

                StationSectionDivider {
                    width: parent.width
                    title: "NEWS MENTION INSPECTOR // GDELT GKG"
                }

                Rectangle {
                    width: parent.width
                    height: 150
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
                                text: stationDiscovery.selectedMapNewsMention
                                      ? stationDiscovery.selectedMapNewsMention.name
                                      : ""
                                color: Colors.magenta
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
                                    stationDiscovery.closeNewsMentionInspector()
                            }
                        }

                        SecondaryText {
                            width: parent.width
                            text: stationDiscovery.selectedMapNewsMention
                                  ? stationDiscovery.selectedMapNewsMention.typeLabel
                                    + " // "
                                    + Number(
                                        stationDiscovery.selectedMapNewsMention.latitude
                                      ).toFixed(3)
                                    + ", "
                                    + Number(
                                        stationDiscovery.selectedMapNewsMention.longitude
                                      ).toFixed(3)
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 11
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapNewsMention
                                  ? "MENTIONS // "
                                    + stationDiscovery.selectedMapNewsMention.mentionCount
                                    + " // FIRST OFFSET // "
                                    + stationDiscovery.selectedMapNewsMention.firstOffset
                                    + " // FEATURE // "
                                    + (stationDiscovery.selectedMapNewsMention.featureId || "--")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.newsMentionOverlay
                                  ? "ARTICLE // "
                                    + stationDiscovery.newsMentionOverlay.articleTitle
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                            color: Colors.white
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.newsMentionOverlay
                                  ? stationDiscovery.newsMentionOverlay.semantics
                                  : "MENTIONED LOCATION // NOT VERIFIED EVENT LOCATION"
                            elide: Text.ElideRight
                            font.pixelSize: 9
                            color: Colors.orange
                        }
                    }
                }
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

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.hotspotInspectorOpen

                StationSectionDivider {
                    width: parent.width
                    title: "HOTSPOT INSPECTOR // NASA FIRMS"
                }

                Rectangle {
                    width: parent.width
                    height: 138
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 5

                        Row {
                            width: parent.width
                            spacing: 10

                            GohuText {
                                width: Math.max(0, parent.width - 96)
                                text: "VIIRS NOAA-21 // SATELLITE HOTSPOT"
                                color: Colors.orange
                                font.pixelSize: 14
                            }

                            ActionButton {
                                width: 86
                                height: 26
                                label: "CLOSE"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                destructive: true
                                onClicked:
                                    stationDiscovery.closeHotspotInspector()
                            }
                        }

                        SecondaryText {
                            width: parent.width
                            text: stationDiscovery.selectedMapHotspot
                                  ? stationDiscovery.selectedMapHotspot.coordinates
                                    + " // "
                                    + stationDiscovery.selectedMapHotspot.acquiredUtc
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 10
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapHotspot
                                  ? "CONFIDENCE "
                                    + stationDiscovery.selectedMapHotspot.confidenceLabel
                                    + " // BRIGHTNESS "
                                    + (stationDiscovery.selectedMapHotspot.brightnessK >= 0
                                       ? stationDiscovery.selectedMapHotspot.brightnessK.toFixed(1)
                                         + " K" : "--")
                                    + " // FRP "
                                    + (stationDiscovery.selectedMapHotspot.frpMw >= 0
                                       ? stationDiscovery.selectedMapHotspot.frpMw.toFixed(1)
                                         + " MW" : "--")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapHotspot
                                  ? stationDiscovery.selectedMapHotspot.satellite
                                    + " // "
                                    + stationDiscovery.selectedMapHotspot.instrument
                                    + " // "
                                    + stationDiscovery.selectedMapHotspot.dayNight
                                    + " // SATELLITE HOTSPOT, NOT FIRE PERIMETER"
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }
                    }
                }
            }

            QuietText {
                visible: stationDiscovery.domain === "news"
                         && source.ready
                         && source.rows.length > 0
                         && stationDiscovery.visibleRows.length === 0
                width: parent.width
                text: "NO HEADLINES MATCH // "
                      + stationDiscovery.newsTopicLabel(
                            stationDiscovery.newsTopic
                        )
                      + (stationDiscovery.newsSourceQuery !== ""
                         ? " // SOURCE "
                           + stationDiscovery.newsSourceQuery.toUpperCase()
                         : "")
                      + (stationDiscovery.newsLanguageQuery !== ""
                         ? " // LANGUAGE "
                           + stationDiscovery.newsLanguageQuery.toUpperCase()
                         : "")
                      + (stationDiscovery.newsMaxAgeHours > 0
                         ? " // " + stationDiscovery.newsMaxAgeHours + "H"
                         : "")
                      + " // FILTER IS LOCAL // SOURCE NOT REFETCHED"
                font.pixelSize: 11
                color: Colors.orange
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
                model: source.ready ? stationDiscovery.visibleRows : []

                delegate: Rectangle {
                    required property var modelData
                    width: content.width
                    height: modelData.sourceGroup
                            && modelData.sourceGroup.multiSource
                            ? 108 : 88
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
                            text: stationDiscovery.domain === "news"
                                  ? modelData.detail
                                    + " // "
                                    + String(
                                          modelData.primaryTopic || "other"
                                      ).toUpperCase()
                                  : modelData.detail
                            elide: Text.ElideRight
                            font.pixelSize: 12
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.time
                            elide: Text.ElideRight
                            font.pixelSize: 10
                        }
                        QuietText {
                            visible: modelData.sourceGroup
                                     && modelData.sourceGroup.multiSource
                            width: parent.width
                            text: modelData.sourceGroup
                                  ? "EXACT HEADLINE GROUP // "
                                    + modelData.sourceGroup.sourceCount
                                    + " PUBLISHERS // "
                                    + modelData.sourceGroup.domains.join(" / ")
                                    + (modelData.sourceGroup.countries.length > 0
                                       ? " // COUNTRIES "
                                         + modelData.sourceGroup.countries.join(" / ")
                                       : "")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                            color: Colors.magenta
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
            locationLoading:
                stationDiscovery.newsLocationMatchesSelection
                && articleLocationService.loading
            locationReady:
                stationDiscovery.newsLocationMatchesSelection
                && articleLocationService.ready
            locationFailed:
                stationDiscovery.newsLocationMatchesSelection
                && articleLocationService.failed
            locationError:
                stationDiscovery.newsLocationMatchesSelection
                ? articleLocationService.errorText : ""
            locationRows:
                stationDiscovery.newsLocationMatchesSelection
                ? articleLocationService.rows : []
            locationFeedName:
                stationDiscovery.newsLocationMatchesSelection
                ? articleLocationService.feedName : ""
            locationSliceUtc:
                stationDiscovery.newsLocationMatchesSelection
                ? articleLocationService.sliceUtc : ""
            locationMatchMethod:
                stationDiscovery.newsLocationMatchesSelection
                ? articleLocationService.matchMethod : ""
            locationSemantics:
                stationDiscovery.newsLocationMatchesSelection
                ? articleLocationService.semantics : ""
            onLocateRequested:
                articleLocationService.request(
                    stationDiscovery.selectedNews
                )
            onShowOnMapRequested:
                stationDiscovery.requestNewsMapHandoff()
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
