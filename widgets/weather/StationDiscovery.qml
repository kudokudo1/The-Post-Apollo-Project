import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationViewerPolicy.js" as ViewerPolicy
import "../../services/weather/StationDiscoveryPolicy.js" as DiscoveryPolicy
import "StationMapProjectionPolicy.js" as MapProjection
import "StationMapCompanionPolicy.js" as MapCompanion
import "StationNaturalEarthLand110.js" as NaturalEarthLand
import "StationNaturalEarthContext110.js" as NaturalEarthContext
import "../../services/weather/FirmsHotspotPolicy.js" as FirmsAreaPolicy
import "StationRadarPolicy.js" as RadarPolicy
import "../../services/weather/HmsSmokePolicy.js" as SmokePolicy
import "../../services/weather/SeismicPolicy.js" as SeismicPolicy
import "../../services/weather/GdacsPolicy.js" as GdacsPolicy
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy
import "StationEventContextPolicy.js" as EventContextPolicy
import "StationDossierPreviewPolicy.js" as DossierPreviewPolicy
import "StationDossierCapturePolicy.js" as DossierCapturePolicy
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy

// Source-first stage. All records shown come from a backend, never examples.
// MAP owns a local Natural Earth geographic basemap plus source-driven data
// overlays and its event list. RADIO remains a stream directory
// before MediaDeck's persistent transport is connected.
Rectangle {
    id: stationDiscovery

    property string domain: "map"
    // Existing GDELT, source cooldown and in-pane article inspector reused.
    property string newsSubjectRoute: ""
    function newsGroupVisible(group) {
        return MediaPanelPolicy.newsGroupVisible(newsSubjectRoute,group);
    }
    onNewsSubjectRouteChanged: {
        if (discoveryScroll)
            discoveryScroll.contentY = 0;
    }
    // M2b weather-only view of the existing CLASSIC map renderer.
    property bool weatherMapOnly: false
    property string weatherMapRoute: ""

    // EARTH shares the real CLASSIC MAP and its manual dossier controls.
    // Never clear selected event or geographic viewport during EARTH routing.
    property bool earthMapOnly: false
    property string earthMapRoute: ""
    function earthLayerEnabled(layer) {
        return !earthMapOnly
            || EarthPanelPolicy.showsLayer(earthMapRoute,layer);
    }
    readonly property bool earthInvestigationRoute:
        earthMapOnly && EarthPanelPolicy.investigationRoute(earthMapRoute)
    onEarthMapRouteChanged: {
        if (!earthMapOnly)
            return;
        // A dedicated source route must not be blanked by an earlier toggle.
        if (earthMapRoute === "earth/geology/earthquakes")
            mapShowEarthquakes = true;
        else if (earthMapRoute === "earth/events/gdacs")
            mapShowGdacs = true;
        if (discoveryScroll)
            discoveryScroll.contentY = 0;
    }

    function weatherLayerEnabled(layer) {
        if (!weatherMapOnly || weatherMapRoute === "weather/maps")
            return true;
        return weatherMapRoute === "weather/maps/" + layer;
    }

    onWeatherMapRouteChanged: {
        if (!weatherMapOnly)
            return;
        if (weatherMapRoute === "weather/maps/radar")
            radarDisplaySource = "noaa";
        else if (weatherMapRoute === "weather/maps/radar-fallback")
            radarDisplaySource = "rainviewer";
        if (discoveryScroll)
            discoveryScroll.contentY = 0;
    }
    property bool stationOpen: true
    property bool viewerOpen: false
    property var selectedNews: null
    property var newsMentionOverlay: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var weatherService: null
    property var persistentCacheStore: null
    property var eventArchiveStore: null
    property var dossierArchiveStore: null
    property real runtimeNowMs: Date.now()
    signal newsMapRequested(var payload)
    signal newsMapClearRequested()
    readonly property bool newsLocationMatchesSelection:
        selectedNews
        && articleLocationService.requestedUrl !== ""
        && articleLocationService.requestedUrl === selectedNews.url

    readonly property var runtimeRows: {
        const base = [
            RuntimePolicy.displayRow(
                "discovery",
                {
                    "active": source.active,
                    "ready": source.ready,
                    "loading": source.loading,
                    "errorText": source.errorText,
                    "receivedAt": source.lastUpdated,
                    "usingCache": source.usingCache,
                    "detail": domain === "map" ? "EONET" : "GDELT DOC"
                },
                runtimeNowMs
            )
        ];

        if (domain === "news") {
            base.push(RuntimePolicy.displayRow(
                "gdelt-article-location",
                {
                    "active": stationOpen,
                    "ready": articleLocationService.ready,
                    "loading": articleLocationService.loading,
                    "errorText": articleLocationService.errorText,
                    "detail": "ARTICLE LOCATION LOOKUP"
                },
                runtimeNowMs
            ));
            return base;
        }

        if (domain !== "map")
            return base;

        base.push(
            RuntimePolicy.displayRow(
                "gdacs",
                {
                    "active": gdacsService.active,
                    "ready": gdacsService.ready,
                    "loading": gdacsService.loading,
                    "errorText": gdacsService.errorText,
                    "receivedAt": gdacsService.lastUpdated,
                    "usingCache": gdacsService.usingPersistentCache
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "seismic",
                {
                    "active": !!seismicSource && seismicSource.active !== false,
                    "ready": !!seismicSource && seismicSource.ready,
                    "loading": !!seismicSource && seismicSource.loading,
                    "errorText": seismicSource ? seismicSource.errorText : "",
                    "receivedAt": seismicSource
                                  ? seismicSource.lastUpdated : null,
                    "usingCache": seismicSource
                                  ? seismicSource.usingPersistentCache : false
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "firms",
                {
                    "active": stationOpen,
                    "ready": firmsService.ready,
                    "loading": firmsService.loading,
                    "errorText": firmsService.errorText,
                    "receivedAt": firmsService.lastUpdated,
                    "detail": "VIEWPORT REQUEST"
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "mrms-radar",
                {
                    "active": stationOpen,
                    "ready": mrmsRadarService.ready,
                    "loading": mrmsRadarService.loading,
                    "errorText": mrmsRadarService.errorText,
                    "receivedAt": mrmsRadarService.lastUpdated,
                    "observedAt": mrmsRadarService.requestedTimeMs,
                    "usingCache": mrmsRadarService.usingFrameCache,
                    "detail": "VIEWPORT IMAGE"
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "lightning",
                {
                    "active": !!lightningSource
                              && lightningSource.active !== false,
                    "ready": !!lightningSource
                             && lightningSource.ready,
                    "loading": !!lightningSource
                               && lightningSource.loading,
                    "errorText": lightningSource
                                 ? lightningSource.errorText : "",
                    "receivedAt": lightningSource
                                  ? lightningSource.lastUpdated : null,
                    "observedAt": lightningSource
                                  ? lightningSource.latestTime : null,
                    "usingCache": lightningSource
                                  ? lightningSource.usingFrameCache : false,
                    "detail": "WEATHER-FIX 15M DENSITY"
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "river",
                {
                    "active": !!riverSource
                              && riverSource.active !== false,
                    "ready": !!riverSource && riverSource.ready,
                    "loading": !!riverSource && riverSource.loading,
                    "errorText": riverSource
                                 ? riverSource.errorText : "",
                    "receivedAt": riverSource
                                  ? riverSource.lastUpdated : null,
                    "usingCache": riverSource
                                  ? riverSource.usingPersistentCache : false,
                    "detail": "WEATHER-FIX NEAREST GAUGE"
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "rainviewer",
                {
                    "active": stationOpen,
                    "ready": rainViewerRadarService.ready,
                    "loading": rainViewerRadarService.loading,
                    "errorText": rainViewerRadarService.errorText,
                    "receivedAt": rainViewerRadarService.lastUpdated,
                    "observedAt":
                        rainViewerRadarService.selectedFrameTime > 0
                        ? rainViewerRadarService.selectedFrameTime * 1000 : 0,
                    "usingCache": rainViewerRadarService.usingFrameCache,
                    "detail": "FALLBACK FRAME"
                },
                runtimeNowMs
            ),
            RuntimePolicy.displayRow(
                "hms-smoke",
                {
                    "active": stationOpen,
                    "ready": hmsSmokeService.ready,
                    "loading": hmsSmokeService.loading,
                    "errorText": hmsSmokeService.errorText,
                    "receivedAt": hmsSmokeService.lastUpdated,
                    "detail": "ANALYST POLYGONS"
                },
                runtimeNowMs
            )
        );
        return base;
    }
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
    property var selectedMapGdacsEvent: null
    property bool mapShowEarthquakes: true
    property bool mapShowGdacs: true
    property bool mapShowCountryBorders: true
    property bool mapShowAdmin1: false
    property bool mapShowPlaces: true
    property real mapZoom: 1
    property real mapCenterLon: 0
    property real mapCenterLat: 0

    readonly property var mapPointRows:
        weatherMapOnly ? [] : MapProjection.plottable(source ? source.rows : [])
            .filter(function() {
                return stationDiscovery.earthLayerEnabled("eonet");
            })
    // MEDIA owns article extraction. Both CLASSIC (during migration) and
    // EARTH may plot the explicitly handed-off mentioned locations. These
    // are NOT provider-native event records and never enter dossier capture.
    readonly property var mapNewsMentionRows:
        weatherMapOnly ? [] : MapProjection.plottable(
            newsMentionOverlay
            && Array.isArray(newsMentionOverlay.locations)
            ? newsMentionOverlay.locations : []
        )
    readonly property var mapEarthquakeRows:
        !weatherMapOnly && mapShowEarthquakes
        && earthLayerEnabled("quakes")
        && seismicSource
        && seismicSource.ready
        ? MapProjection.plottable(seismicSource.events)
        : []
    readonly property var mapGdacsRows:
        !weatherMapOnly && mapShowGdacs && gdacsService.ready
        && earthLayerEnabled("gdacs")
        ? MapProjection.plottable(gdacsService.events)
        : []
    readonly property var gdacsSummary:
        GdacsPolicy.summary(gdacsService.events)
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
    // A small spatial companion, not a duplicated MEDIA news feed.
    // EARTH → EVENTS → EONET keeps the complete original event list.
    readonly property var mapCompanionEonetRows:
        !earthMapOnly || earthMapRoute === "earth/events/eonet"
        ? visibleRows
        : MapCompanion.previewEonet(
              mapPointRows, selectedMapEvent, mapVisibleBounds, 4
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
    readonly property string radarImageUrl: mrmsRadarService.imageUrl
    readonly property var radarSnapshotBounds: mrmsRadarService.snapshotBounds
    property int radarHistoryMinutes: 0
    readonly property int radarLoadedHistoryMinutes:
        mrmsRadarService.loadedHistoryMinutes
    readonly property double radarRequestedTimeMs:
        mrmsRadarService.requestedTimeMs
    readonly property date radarRequestedAt: mrmsRadarService.lastUpdated
    property string radarDisplaySource: "noaa"
    property bool pendingRainViewerDisplay: false
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
    readonly property bool gdacsInspectorOpen:
        domain === "map" && selectedMapGdacsEvent !== null

    readonly property string selectedContextSourceId:
        selectedMapGdacsEvent !== null ? "gdacs"
        : selectedMapEarthquake !== null ? "usgs"
        : selectedMapEvent !== null ? "eonet"
        : selectedMapHotspot !== null ? "firms"
        : ""

    readonly property var selectedContextRow:
        selectedContextSourceId === "gdacs" ? selectedMapGdacsEvent
        : selectedContextSourceId === "usgs" ? selectedMapEarthquake
        : selectedContextSourceId === "eonet" ? selectedMapEvent
        : selectedContextSourceId === "firms" ? selectedMapHotspot
        : null

    readonly property var selectedEventContext:
        EventContextPolicy.normalizeSelected(
            selectedContextSourceId,
            selectedContextRow
        )

    readonly property real selectedWeatherFixDistanceKm:
        EventContextPolicy.weatherFixDistance(
            selectedEventContext,
            weatherService ? weatherService.latitude : null,
            weatherService ? weatherService.longitude : null
        )

    readonly property var selectedRadarContext:
        EventContextPolicy.radarCoverage(
            selectedEventContext,
            radarSnapshotBounds,
            radarLoadedHistoryMinutes,
            radarRequestedTimeMs,
            mrmsRadarService.usingFrameCache,
            mrmsRadarService.lastUpdated
        )

    readonly property var selectedLightningContext:
        EventContextPolicy.lightningCoverage(
            selectedEventContext,
            lightningSource ? lightningSource.bbox : null,
            lightningSource ? lightningSource.ready : false,
            lightningSource ? lightningSource.latestTime : "",
            lightningSource ? lightningSource.windowMinutes : 0,
            lightningSource ? lightningSource.resolutionKm : 0,
            lightningSource ? lightningSource.radiusKm : 0,
            lightningSource ? lightningSource.usingFrameCache : false,
            lightningSource ? lightningSource.lastUpdated : null
        )

    readonly property var selectedContextCompanions:
        EventContextPolicy.nearbyEvidence(
            selectedEventContext,
            [
                {
                    "sourceId": "gdacs",
                    "rows": mapShowGdacs && gdacsService.ready
                        ? gdacsService.events : []
                },
                {
                    "sourceId": "usgs",
                    "rows": mapShowEarthquakes
                        && seismicSource
                        && seismicSource.ready
                        ? seismicSource.events : []
                },
                {
                    "sourceId": "eonet",
                    "rows": source && Array.isArray(source.rows)
                        ? source.rows : []
                },
                {
                    "sourceId": "firms",
                    "rows": firmsService.ready
                        ? firmsService.hotspots : []
                }
            ],
            250,
            6
        )

    readonly property var selectedFloodContext:
        EventContextPolicy.floodGaugeContext(
            selectedEventContext,
            riverSource && riverSource.ready
                ? riverSource.gauge : null,
            riverSource && riverSource.contextReady
                ? riverSource.gaugeContext : null,
            riverSource && riverSource.stageflowReady
                ? riverSource.stageflow : null,
            100,
            riverSource && riverSource.stageflowReady
                ? riverSource.stageflowLastUpdated : null
        )

    readonly property var selectedEvidenceTimeline:
        EventContextPolicy.evidenceTimeline(
            selectedEventContext,
            selectedContextCompanions,
            selectedRadarContext,
            selectedLightningContext,
            selectedFloodContext,
            8
        )

    readonly property var selectedEvidenceRelationships:
        EventContextPolicy.evidenceRelationships(
            selectedEventContext,
            selectedContextCompanions,
            selectedRadarContext,
            selectedLightningContext,
            selectedFloodContext,
            8
        )

    // M22-A read-only, volatile preview over already-derived event context.
    // Not an archive writer, and never a merged incident identity.
    readonly property var selectedDossierPreview:
        DossierPreviewPolicy.preview(
            selectedEventContext,
            selectedContextCompanions,
            selectedRadarContext,
            selectedLightningContext,
            selectedFloodContext,
            selectedEvidenceTimeline,
            selectedEvidenceRelationships,
            runtimeNowMs
        )

    // Admission review is volatile. It never stages or saves a dossier.
    readonly property var selectedDossierCaptureReview:
        DossierCapturePolicy.review(
            selectedDossierPreview,
            runtimeNowMs
        )

    readonly property int selectedArchiveRevision: {
        return eventArchiveStore
            ? Number(eventArchiveStore.revision || 0) : 0;
    }

    // Pair selections belong to the currently inspected provider-native event.
    // Clear positional choices after event switches or archive retention changes.
    property int archiveEarlierPosition: 0
    property int archiveLaterPosition: 0
    readonly property string archivePairIdentity:
        selectedContextSourceId + "|" + (selectedEventContext
            ? String(selectedEventContext.id || "") : "")
    onArchivePairIdentityChanged: {
        archiveEarlierPosition = 0;
        archiveLaterPosition = 0;
    }
    onSelectedArchiveRevisionChanged: {
        archiveEarlierPosition = 0;
        archiveLaterPosition = 0;
    }

    readonly property int selectedArchiveCount: {
        const revision = selectedArchiveRevision;
        if (!eventArchiveStore || !selectedEventContext)
            return 0;
        return eventArchiveStore.snapshotCount(
            selectedContextSourceId,
            selectedEventContext.id,
            runtimeNowMs
        );
    }

    readonly property var selectedArchiveRows: {
        const revision = selectedArchiveRevision;
        if (!eventArchiveStore || !selectedEventContext)
            return [];
        return eventArchiveStore.revisionRows(
            selectedContextSourceId,
            selectedEventContext.id,
            runtimeNowMs,
            5
        );
    }

    readonly property var selectedArchiveDiff: {
        const revision = selectedArchiveRevision;
        if (!eventArchiveStore || !selectedEventContext)
            return null;
        return eventArchiveStore.latestDiff(
            selectedContextSourceId,
            selectedEventContext.id,
            runtimeNowMs
        );
    }

    readonly property int resolvedArchiveEarlierPosition:
        archiveEarlierPosition > 0 ? archiveEarlierPosition
            : Math.max(1, selectedArchiveCount - 1)
    readonly property int resolvedArchiveLaterPosition:
        archiveLaterPosition > 0 ? archiveLaterPosition
            : selectedArchiveCount
    readonly property bool archivePairCustom:
        archiveEarlierPosition > 0 && archiveLaterPosition > 0

    readonly property var selectedArchivePairDiff: {
        const revision = selectedArchiveRevision;
        if (!eventArchiveStore || !selectedEventContext
                || selectedArchiveCount < 2)
            return null;
        return eventArchiveStore.pairDiff(
            selectedContextSourceId,
            selectedEventContext.id,
            runtimeNowMs,
            resolvedArchiveEarlierPosition,
            resolvedArchiveLaterPosition
        );
    }

    function selectArchivePair(earlierPosition, laterPosition) {
        const earlier = Number(earlierPosition);
        const later = Number(laterPosition);
        if (selectedArchiveCount < 2
                || !Number.isInteger(earlier) || !Number.isInteger(later)
                || earlier < 1 || later > selectedArchiveCount
                || earlier >= later)
            return false;
        archiveEarlierPosition = earlier;
        archiveLaterPosition = later;
        return true;
    }

    readonly property bool selectedArchiveAvailable:
        !!eventArchiveStore
        && selectedEventContext !== null
        && eventArchiveStore.storageState !== "error"
        && eventArchiveStore.storageState !== "unsupported"

    readonly property string selectedArchiveStatus: {
        if (!eventArchiveStore)
            return "ARCHIVE STORE UNAVAILABLE";
        if (eventArchiveStore.storageState === "error")
            return "ARCHIVE ERROR // " + eventArchiveStore.errorCode;
        if (eventArchiveStore.storageState === "unsupported")
            return "ARCHIVE SCHEMA UNSUPPORTED";
        if (eventArchiveStore.storageState === "loading")
            return "ARCHIVE LOADING";
        if (eventArchiveStore.storageState === "saving")
            return "ARCHIVE SAVING";
        if (selectedArchiveCount > 0)
            return "ARCHIVED // " + selectedArchiveCount + " SNAPSHOT"
                + (selectedArchiveCount === 1 ? "" : "S");
        return "NOT ARCHIVED";
    }

    function archiveSelectedEvent() {
        if (!selectedArchiveAvailable
                || !selectedContextSourceId
                || !selectedContextRow)
            return false;
        return eventArchiveStore.archiveEvent(
            selectedContextSourceId,
            selectedContextRow
        );
    }

    // M25 is an independent store. No write on selection or data refresh.
    readonly property bool dossierSaveAvailable:
        !!dossierArchiveStore
        && !!selectedDossierCaptureReview
        && selectedDossierCaptureReview.ready === true
        && (dossierArchiveStore.storageState === "ready"
            || dossierArchiveStore.storageState === "empty")

    readonly property int selectedDossierCount:
        dossierArchiveStore && selectedEventContext
        ? dossierArchiveStore.eventCount(
            selectedContextSourceId, selectedEventContext.id
        ) : 0

    readonly property string selectedDossierSaveStatus: {
        if (!dossierArchiveStore)
            return "DOSSIER STORE UNAVAILABLE";
        const state = dossierArchiveStore.storageState;
        if (state === "error")
            return "DOSSIER ERROR // " + dossierArchiveStore.errorCode;
        if (state === "unsupported")
            return "DOSSIER SCHEMA UNSUPPORTED";
        if (state === "loading")
            return "DOSSIER LOADING";
        if (state === "saving")
            return "DOSSIER SAVING";
        if (dossierArchiveStore.lastResultCode
                && dossierArchiveStore.lastResultCode !== "SAVED")
            return "DOSSIER // " + dossierArchiveStore.lastResultCode;
        return selectedDossierCount > 0
            ? "SAVED // " + selectedDossierCount + " DOSSIER"
                + (selectedDossierCount === 1 ? "" : "S")
            : "NOT SAVED";
    }

    function saveSelectedDossier() {
        if (!dossierSaveAvailable)
            return false;
        const now = Date.now();
        const staged = DossierCapturePolicy.stage(
            selectedDossierPreview, now, true
        );
        if (!staged.ok)
            return false;
        return dossierArchiveStore.capture(staged, now);
    }

    readonly property bool eventContextInspectorOpen:
        domain === "map"
        && selectedContextSourceId !== ""
        && selectedEventContext !== null

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
        selectedMapGdacsEvent = null;
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

    function inspectNewsMention(row) {
        if (domain !== "map" || !row) return false;
        selectedMapEvent = null;
        selectedMapHotspot = null;
        selectedMapEarthquake = null;
        selectedMapGdacsEvent = null;
        selectedMapNewsMention = row;
        return true;
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

    function radarUtcLabel(timeMs) {
        const value = Number(timeMs);
        if (!isFinite(value) || value <= 0)
            return "-- UTC";
        const date = new Date(value);
        if (isNaN(date.getTime()))
            return "-- UTC";
        const hh = date.getUTCHours();
        const mm = date.getUTCMinutes();
        return (hh < 10 ? "0" : "") + hh + ":"
               + (mm < 10 ? "0" : "") + mm + " UTC";
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

        return mrmsRadarService.request(
            nextUrl,
            snapshot,
            radarHistoryMinutes,
            historicalTime
        );
    }

    function clearRadarSnapshot() {
        mrmsRadarService.clear();
        if (radarDisplaySource === "noaa"
                && rainViewerRadarService.ready)
            radarDisplaySource = "rainviewer";
    }

    function loadRainViewerFallback() {
        if (domain !== "map" || !stationOpen)
            return false;
        const accepted = rainViewerRadarService.request(
            radarHistoryMinutes,
            mapVisibleBounds
        );
        if (accepted)
            pendingRainViewerDisplay = true;
        return accepted;
    }

    function clearRainViewerFallback() {
        rainViewerRadarService.clear();
        if (radarDisplaySource === "rainviewer")
            radarDisplaySource = "noaa";
    }

    function showRadarSource(sourceId) {
        const next = String(sourceId || "");
        if (next === "noaa" && radarImageUrl !== "") {
            radarDisplaySource = "noaa";
            return true;
        }
        if (next === "rainviewer" && rainViewerRadarService.ready) {
            radarDisplaySource = "rainviewer";
            return true;
        }
        return false;
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

    function eventContextAccentColor() {
        switch (selectedContextSourceId) {
        case "gdacs":
            return selectedMapGdacsEvent
                ? gdacsAlertColor(selectedMapGdacsEvent.alertLevel)
                : Colors.magenta;
        case "usgs":
            return selectedMapEarthquake
                ? earthquakeDepthColor(selectedMapEarthquake.depthKm)
                : Colors.cyan;
        case "eonet":
            return selectedMapEvent
                ? mapPointColor(selectedMapEvent.categoryId)
                : Colors.cyan;
        case "firms":
            return Colors.orange;
        default:
            return Colors.white;
        }
    }

    function closeEarthquakeInspector() {
        selectedMapEarthquake = null;
    }

    function closeGdacsInspector() {
        selectedMapGdacsEvent = null;
    }

    function gdacsAlertColor(level) {
        switch (GdacsPolicy.alertToken(level)) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
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
                selectedMapGdacsEvent = null;
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
        selectedMapGdacsEvent = null;
    }
    onNewsMentionOverlayChanged: {
        selectedMapNewsMention = null;
        if (domain === "map" && mapNewsMentionRows.length > 0)
            focusNewsMentions();
    }
    onStationOpenChanged: { if (!stationOpen) closeViewer(); }

    readonly property string modeTitle:
        earthMapOnly ? "⌖  EARTH // MAP" :
        weatherMapOnly ? "☁  WEATHER // MAP" :
        domain === "map" ? "⌖  MAP // EVENT SOURCES"
        : domain === "news" ? "▤  NEWS // HEADLINES"
        : "◉  RADIO // STATIONS"
    readonly property string providerTitle:
        earthMapOnly ? EarthPanelPolicy.routeLabel(earthMapRoute) :
        weatherMapOnly ? "WEATHER OVERLAYS // MANUAL LOAD" :
        domain === "map" ? "WORLD EVENTS // NASA EONET + GDACS"
        : domain === "news" ? "GDELT DOC // WORLD EVENT HEADLINES"
        : "RADIO BROWSER // TOP VOTED STREAMS"
    readonly property string sourceCaution:
        earthMapOnly ? "NATURAL EARTH + USGS + NASA EONET + GDACS + NASA FIRMS // MANUAL HOTSPOT & SMOKE LOAD // PROVIDER-NATIVE EVENTS" :
        weatherMapOnly ? "NOAA MRMS + RAINVIEWER + NOAA HMS // NOT A DISASTER FEED" :
        domain === "map" ? "NATURAL EARTH + EONET + GDACS + USGS EARTHQUAKES + FIRMS + MRMS + RAINVIEWER FALLBACK + HMS SMOKE"
        : domain === "news" ? "ARTICLE DISCOVERY // LOCAL FILTERS // EXACT-HEADLINE SOURCE GROUPS // NOT FUZZY STORY CLUSTERING"
        : "STATION DIRECTORY // PERSISTENT PLAYBACK NOT YET WIRED"
    readonly property var plannedSources: {
        if (earthMapOnly)
            return [
                {name:"NATURAL EARTH // SHARED LOCAL CARTOGRAPHY",
                 state:"CONNECTED"},
                {name:"USGS // OBSERVED EARTHQUAKES M2.5+",
                 state: seismicSource && seismicSource.ready
                      ? "EVENTS " + seismicSource.events.length
                      : seismicSource && seismicSource.loading
                        ? "RECEIVING" : "INACTIVE / WAITING"},
                {name:"NASA EONET // NATURAL EVENTS",
                 state: source.ready ? "EVENTS " + source.rows.length
                       : source.loading ? "RECEIVING" : "INACTIVE / WAITING"},
                {name:"GDACS // DISASTER EARLY WARNING",
                 state: gdacsService.ready
                        ? "EVENTS " + gdacsService.events.length
                        : gdacsService.loading ? "RECEIVING"
                          : "INACTIVE / WAITING"},
                {name:"NASA FIRMS // VIIRS HOTSPOTS",
                 state: !firmsService.configured ? "KEY REQUIRED"
                      : firmsService.ready
                        ? "HOTSPOTS " + firmsService.hotspots.length
                        : "MANUAL READY"},
                {name:"NOAA HMS // SMOKE PLUMES",
                 state: hmsSmokeService.ready
                      ? "PLUMES " + hmsSmokeService.polygons.length
                      : "MANUAL READY"}
            ];
        if (weatherMapOnly)
            return [
                {name:"NATURAL EARTH // LOCAL BASEMAP", state:"CONNECTED"},
                {name:"NOAA MRMS // MANUAL RADAR", state:mrmsRadarService.ready
                      ? "FRAME READY" : mrmsRadarService.loading
                        ? "RECEIVING" : "MANUAL READY"},
                {name:"RAINVIEWER // PAST RADAR FALLBACK", state:rainViewerRadarService.ready
                      ? "FRAME READY" : rainViewerRadarService.loading
                        ? "RECEIVING" : "MANUAL READY"},
                {name:"NOAA HMS // SMOKE PLUMES", state:hmsSmokeService.ready
                      ? "PLUMES " + hmsSmokeService.polygons.length
                      : hmsSmokeService.loading ? "RECEIVING" : "MANUAL READY"}
            ];
        if (domain === "map")
            return [
                {name:"NASA EONET // FILTERED EVENTS + INSPECTOR", state:"SOURCE CONNECTED"},
                {
                    name:"GDACS // GLOBAL MULTI-HAZARD EARLY WARNING",
                    state: gdacsService.ready
                           ? "LOADED " + gdacsService.events.length
                           : gdacsService.loading
                             ? "RECEIVING"
                             : gdacsService.failed
                               ? "ERROR" : "WAITING"
                },
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
                    state: mrmsRadarService.ready
                           ? (mrmsRadarService.usingFrameCache
                              ? "CACHE " : "FRAME ")
                             + radarHistoryLabel(radarLoadedHistoryMinutes)
                           : mrmsRadarService.loading
                             ? "RECEIVING"
                             : mrmsRadarService.failed
                               ? "ERROR" : "MANUAL READY"
                },
                {
                    name:"RAINVIEWER // PAST RADAR FALLBACK // 2H",
                    state: rainViewerRadarService.ready
                           ? (rainViewerRadarService.usingFrameCache
                              ? "CACHE " : "READY ")
                             + rainViewerRadarService.tileCount
                             + " TILES"
                           : rainViewerRadarService.loading
                             ? "RECEIVING"
                             : rainViewerRadarService.failed
                               ? "ERROR" : "MANUAL READY"
                },
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
                && !stationDiscovery.weatherMapOnly
                && (!stationDiscovery.earthMapOnly
                    || EarthPanelPolicy.needsSource(
                           stationDiscovery.earthMapRoute,"eonet"))
    }

    WeatherServices.GdacsService {
        id: gdacsService
        cacheStore: stationDiscovery.persistentCacheStore
        active: stationDiscovery.domain === "map"
                && !stationDiscovery.weatherMapOnly
                && (!stationDiscovery.earthMapOnly
                    || EarthPanelPolicy.needsSource(
                           stationDiscovery.earthMapRoute,"gdacs"))
                && stationDiscovery.stationOpen
                && stationDiscovery.visible
    }

    WeatherServices.FirmsHotspotService {
        id: firmsService
    }

    WeatherServices.HmsSmokeService {
        id: hmsSmokeService
    }

    WeatherServices.MrmsRadarService {
        id: mrmsRadarService
        active: stationDiscovery.domain === "map"
                && stationDiscovery.stationOpen
                && !stationDiscovery.earthMapOnly
        onFrameReady: {
            if (!stationDiscovery.pendingRainViewerDisplay)
                stationDiscovery.radarDisplaySource = "noaa";
        }
    }

    WeatherServices.RainViewerRadarService {
        id: rainViewerRadarService
        onOverlayReady: {
            if (stationDiscovery.pendingRainViewerDisplay
                    || !mrmsRadarService.ready)
                stationDiscovery.radarDisplaySource = "rainviewer";
            stationDiscovery.pendingRainViewerDisplay = false;
        }
    }

    WeatherServices.GdeltArticleLocationService {
        id: articleLocationService
    }

    color: Colors.black

    // The original SOURCE ROW card is shared by the MEDIA feed and the
    // EARTH event companion. Reuse the same click/inspector behavior.
    Component {
        id: discoveryRecordCard
        Rectangle {
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
                    text: stationDiscovery.earthMapOnly
                          ? "EARTH // SOURCE-SCOPED MAP" :
                          stationDiscovery.weatherMapOnly ? "RADAR + SMOKE // MANUAL" :
                          source.failed ? source.errorText
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

            StationRuntimeRack {
                // Both native map families expose their original providers.
                visible: stationDiscovery.domain === "map"
                width: parent.width
                rows: stationDiscovery.runtimeRows
            }

            StationSectionDivider {
                visible: stationDiscovery.domain === "map"
                width: parent.width
                title: "SOURCE RACK // WHAT IS CONNECTED"
            }

            Column {
                visible: stationDiscovery.domain === "map"
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
                                   || String(modelData.state).indexOf("READY ") === 0
                                   ? Colors.cyan : Colors.orange
                            font.pixelSize: 11
                        }
                    }
                }
            }

            StationSectionDivider {
                visible: !stationDiscovery.weatherMapOnly
                width: parent.width
                title: stationDiscovery.providerTitle
            }

            Row {
                id: mapFilterRail
                width: parent.width
                height: stationDiscovery.domain === "map" && !stationDiscovery.weatherMapOnly
                        && stationDiscovery.earthLayerEnabled("eonet") ? 34 : 0
                visible: stationDiscovery.domain === "map" && !stationDiscovery.weatherMapOnly
                         && stationDiscovery.earthLayerEnabled("eonet")
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
                    visible: stationDiscovery.weatherMapOnly
                    width: parent.width
                    title: "WEATHER // RADAR + SMOKE GEOGRAPHY"
                }

                StationSectionDivider {
                    visible: stationDiscovery.earthMapOnly
                    width: parent.width
                    title: EarthPanelPolicy.routeLabel(
                        stationDiscovery.earthMapRoute)
                }

                QuietText {
                    visible: stationDiscovery.earthInvestigationRoute
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.yellow
                    text: EarthPanelPolicy.selectionHint(
                        stationDiscovery.earthMapRoute)
                          + " // SELECT A MAP MARKER, THEN SCROLL TO EVENT CONTEXT BELOW."
                }

                StationSectionDivider {
                    visible: (!stationDiscovery.weatherMapOnly) && !stationDiscovery.earthMapOnly
                    width: parent.width
                    title: "SPATIAL PLOT // GDACS + USGS QUAKES + EONET + FIRMS + NEWS"
                }

                QuietText {
                    visible: stationDiscovery.earthMapOnly
                             && stationDiscovery.mapNewsMentionRows.length > 0
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "MEDIA → EARTH // GDELT ARTICLE MENTIONS // NOT VERIFIED EVENT LOCATIONS"
                    color: Colors.magenta
                    font.pixelSize: 10
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
                    visible: (!stationDiscovery.weatherMapOnly)
                             && stationDiscovery.earthLayerEnabled("quakes")
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
                    visible: (!stationDiscovery.weatherMapOnly)
                             && stationDiscovery.earthLayerEnabled("gdacs")
                    width: parent.width
                    height: 30
                    spacing: 10

                    ActionButton {
                        width: 152
                        height: 28
                        label: "GDACS: "
                               + (stationDiscovery.mapShowGdacs
                                  ? "ON" : "OFF")
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        selected: stationDiscovery.mapShowGdacs
                        onClicked:
                            stationDiscovery.mapShowGdacs =
                                !stationDiscovery.mapShowGdacs
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 162)
                        text: gdacsService.ready
                              ? "GDACS // " + stationDiscovery.mapGdacsRows.length
                                + " PLOTTABLE // CURRENT "
                                + stationDiscovery.gdacsSummary.current
                                + " // RED " + stationDiscovery.gdacsSummary.red
                                + " // ORANGE " + stationDiscovery.gdacsSummary.orange
                              : gdacsService.loading
                                ? "GDACS // RECEIVING"
                                : gdacsService.failed
                                  ? gdacsService.errorText
                                  : "GDACS // WAITING"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: Colors.magenta
                    }
                }

                Row {
                    width: parent.width
                    height: 28
                    spacing: 10

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 120)
                        text: stationDiscovery.earthMapOnly
                              ? "WHEEL ZOOM // DRAG PAN // EVENT SELECTION PRESERVED"
                              : stationDiscovery.weatherMapOnly
                                ? "WHEEL ZOOM // DRAG PAN // MANUAL RADAR + SMOKE"
                              : "PLOTTABLE "
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
                    visible: (!stationDiscovery.weatherMapOnly)
                             && (stationDiscovery.mapNewsMentionRows.length > 0)
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
                    visible: (!stationDiscovery.weatherMapOnly) && stationDiscovery.earthLayerEnabled("firms")
                    width: parent.width
                    title: "FIRE HOTSPOTS // NASA FIRMS"
                }

                Row {
                    visible: (!stationDiscovery.weatherMapOnly)
                             && stationDiscovery.earthLayerEnabled("firms")
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
                    visible: (!stationDiscovery.weatherMapOnly)
                             && stationDiscovery.earthLayerEnabled("firms")
                    width: parent.width
                    text: "POST_APOLLO_FIRMS_MAP_KEY // OPTIONAL // KEY NEVER SHOWN OR PASSED IN PROCESS ARGV"
                    font.pixelSize: 9
                    color: Colors.orange
                }

                StationSectionDivider {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar")) && !stationDiscovery.earthMapOnly
                    width: parent.width
                    title: "RADAR // NOAA/NWS MRMS BASE REFLECTIVITY + 4H HISTORY"
                }

                Row {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar") || stationDiscovery.weatherLayerEnabled("radar-fallback"))
                             && !stationDiscovery.earthMapOnly
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
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar"))
                             && !stationDiscovery.earthMapOnly
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
                                   && !mrmsRadarService.loading
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
                              : mrmsRadarService.loading
                                ? "CACHING FRAME"
                                : mrmsRadarService.failed
                                  ? mrmsRadarService.errorText
                                  : radarImage.status === Image.Error
                                    ? "IMAGE ERROR"
                                    : radarImage.status === Image.Ready
                                      ? (mrmsRadarService.usingFrameCache
                                         ? "FRAME CACHE" : "RADAR LOADED")
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
                                     + stationDiscovery.radarUtcLabel(
                                           stationDiscovery
                                           .radarRequestedTimeMs
                                       )
                                     + " TARGET"
                                   : " // LATEST AVAILABLE")
                                + (mrmsRadarService.usingFrameCache
                                   ? " // FRAME CACHE"
                                   : " // SNAPSHOT TRACKS MAP")
                              : "MAX 90° × 50° VIEW // MANUAL LOAD // NO PAN AUTO-FETCH"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                QuietText {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar"))
                             && !stationDiscovery.earthMapOnly
                    width: parent.width
                    text: "NOAA / NWS / MRMS // OFFICIAL BASE REFLECTIVITY // 4H MOVING HISTORY // COVERAGE IS NOT GLOBAL"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                StationSectionDivider {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar-fallback")) && !stationDiscovery.earthMapOnly
                    width: parent.width
                    title: "RADAR FALLBACK // RAINVIEWER PAST RADAR"
                }

                Row {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar-fallback"))
                             && !stationDiscovery.earthMapOnly
                    width: parent.width
                    height: 32
                    spacing: 10

                    ActionButton {
                        width: 142
                        height: 30
                        label: rainViewerRadarService.ready
                               ? "REFRESH FALLBACK"
                               : "LOAD FALLBACK"
                        labelPixelSize: 9
                        accentColor: Colors.blue
                        available: !rainViewerRadarService.loading
                                   && stationDiscovery.radarHistoryMinutes <= 120
                        onClicked:
                            stationDiscovery.loadRainViewerFallback()
                    }

                    ActionButton {
                        width: 92
                        height: 30
                        label: "CLEAR RV"
                        labelPixelSize: 9
                        available: rainViewerRadarService.ready
                                   || rainViewerRadarService.strips.length > 0
                        onClicked:
                            stationDiscovery.clearRainViewerFallback()
                    }

                    GohuText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 180
                        text: stationDiscovery.radarHistoryMinutes > 120
                              ? "MAX HISTORY // 2H"
                              : rainViewerRadarService.loading
                                ? "READING METADATA"
                                : rainViewerRadarService.failed
                                  ? rainViewerRadarService.errorText
                                  : rainViewerRadarService.ready
                                    ? (rainViewerRadarService.usingFrameCache
                                       ? "FRAME CACHE"
                                       : rainViewerRadarService.frameCacheMode === "fetch"
                                         ? "CACHING TILES"
                                         : "FALLBACK PLANNED")
                                    : "MANUAL READY"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: rainViewerRadarService.failed
                               ? Colors.yellow
                               : rainViewerRadarService.ready
                                 ? Colors.blue : Colors.white
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 434)
                        text: rainViewerRadarService.ready
                              ? "FRAME "
                                + stationDiscovery.radarUtcLabel(
                                      rainViewerRadarService
                                      .selectedFrameTime * 1000
                                  )
                                + " // "
                                + rainViewerRadarService.tileCount
                                + " TILES // Z"
                                + rainViewerRadarService.tileZoom
                                + (rainViewerRadarService.usingFrameCache
                                   ? " // CACHE" : "")
                              : "PAST 2H // 10-MIN FRAMES // MANUAL // NO AUTO-FETCH"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                Row {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar-fallback"))
                             && !stationDiscovery.earthMapOnly
                    width: parent.width
                    height: 30
                    spacing: 10

                    ActionButton {
                        width: 108
                        height: 28
                        label: "SHOW NOAA"
                        labelPixelSize: 9
                        selected: stationDiscovery.radarDisplaySource === "noaa"
                        available: stationDiscovery.radarImageUrl !== ""
                        accentColor: Colors.cyan
                        onClicked:
                            stationDiscovery.showRadarSource("noaa")
                    }

                    ActionButton {
                        width: 132
                        height: 28
                        label: "SHOW FALLBACK"
                        labelPixelSize: 9
                        selected:
                            stationDiscovery.radarDisplaySource === "rainviewer"
                        available: rainViewerRadarService.ready
                        accentColor: Colors.blue
                        onClicked:
                            stationDiscovery.showRadarSource("rainviewer")
                    }

                    QuietText {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 250)
                        text: "DISPLAY // "
                              + (stationDiscovery.radarDisplaySource
                                 === "rainviewer"
                                 ? "RAINVIEWER" : "NOAA MRMS")
                              + " // WEATHER DATA BY RAINVIEWER WHEN FALLBACK IS SHOWN"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: stationDiscovery.radarDisplaySource
                               === "rainviewer"
                               ? Colors.blue : Colors.cyan
                    }
                }

                QuietText {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("radar-fallback"))
                             && !stationDiscovery.earthMapOnly
                    width: parent.width
                    text: "RAINVIEWER API // SOURCE CREDIT REQUIRED // GLOBAL COVERAGE VARIES // PUBLIC FALLBACK HAS PAST RADAR ONLY"
                    font.pixelSize: 9
                    color: Colors.orange
                }

                StationSectionDivider {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("smoke")) && stationDiscovery.earthLayerEnabled("smoke")
                    width: parent.width
                    title: "SMOKE PLUMES // NOAA HMS"
                }

                Row {
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("smoke"))
                             && stationDiscovery.earthLayerEnabled("smoke")
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
                    visible: (!stationDiscovery.weatherMapOnly || stationDiscovery.weatherLayerEnabled("smoke"))
                             && stationDiscovery.earthLayerEnabled("smoke")
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
                        visible: stationDiscovery.radarDisplaySource === "noaa"
                                 && !stationDiscovery.earthMapOnly
                                 && stationDiscovery.weatherLayerEnabled("radar")
                                 && source !== ""
                                 && northWest.valid && southEast.valid
                                 && width > 0 && height > 0
                    }

                    Repeater {
                        model: stationDiscovery.radarDisplaySource
                               === "rainviewer"
                               && rainViewerRadarService.ready
                               && stationDiscovery.weatherLayerEnabled("radar-fallback")
                               && !stationDiscovery.earthMapOnly
                               ? rainViewerRadarService.strips : []

                        delegate: Image {
                            required property var modelData
                            readonly property var northWest:
                                MapProjection.project(
                                    modelData.west,
                                    modelData.north,
                                    mapPlot.width,
                                    mapPlot.height,
                                    stationDiscovery.mapZoom,
                                    stationDiscovery.mapCenterLon,
                                    stationDiscovery.mapCenterLat
                                )
                            readonly property var southEast:
                                MapProjection.project(
                                    modelData.east,
                                    modelData.south,
                                    mapPlot.width,
                                    mapPlot.height,
                                    stationDiscovery.mapZoom,
                                    stationDiscovery.mapCenterLon,
                                    stationDiscovery.mapCenterLat
                                )

                            source: modelData.url
                            sourceSize.width: modelData.sourceSize
                            sourceSize.height: modelData.sourceSize
                            sourceClipRect: Qt.rect(
                                0,
                                modelData.sourceY,
                                modelData.sourceSize,
                                modelData.sourceHeight
                            )
                            cache: true
                            asynchronous: true
                            fillMode: Image.Stretch
                            smooth: true
                            opacity: 0.68
                            z: 0.12

                            x: northWest.valid ? northWest.x : 0
                            y: northWest.valid ? northWest.y : 0
                            width: northWest.valid && southEast.valid
                                   ? Math.max(
                                         0,
                                         southEast.x - northWest.x
                                     ) : 0
                            height: northWest.valid && southEast.valid
                                    ? Math.max(
                                          0,
                                          southEast.y - northWest.y
                                      ) : 0
                            visible: northWest.valid && southEast.valid
                                     && width > 0 && height > 0
                        }
                    }

                    Canvas {
                        id: smokeCanvas
                        anchors.fill: parent
                        z: 0.2

                        property var smokeRows: stationDiscovery.weatherLayerEnabled("smoke")
                                                && stationDiscovery.earthLayerEnabled("smoke")
                                                ? hmsSmokeService.polygons : []
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
                                    stationDiscovery.selectedMapGdacsEvent = null;
                                    stationDiscovery.selectedMapEarthquake = modelData;
                                }
                            }
                        }
                    }

                    Repeater {
                        model: stationDiscovery.mapGdacsRows

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
                            readonly property real alertRadius:
                                GdacsPolicy.alertRadius(modelData.alertLevel)

                            width: alertRadius * 2 + 8
                            height: alertRadius * 2 + 8
                            x: projected.x - width / 2
                            y: projected.y - height / 2
                            visible: projected.visible
                            z: 2.12

                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.alertRadius * 2
                                height: parent.alertRadius * 2
                                color: stationDiscovery.gdacsAlertColor(
                                    modelData.alertLevel
                                )
                                opacity: 0.88
                                border.width:
                                    stationDiscovery.selectedMapGdacsEvent
                                       === modelData ? 2 : 1
                                border.color:
                                    stationDiscovery.selectedMapGdacsEvent
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
                                    stationDiscovery.selectedMapEarthquake = null;
                                    stationDiscovery.selectedMapGdacsEvent = modelData;
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
                                    stationDiscovery.selectedMapGdacsEvent = null;
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
                                onClicked:
                                    stationDiscovery.inspectNewsMention(modelData)
                            }
                        }
                    }

                    Repeater {
                        model: firmsService.ready ? firmsService.hotspots : []
                        visible: !stationDiscovery.weatherMapOnly
                                 && stationDiscovery.earthLayerEnabled("firms")

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
                                    stationDiscovery.selectedMapGdacsEvent = null;
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
                        text: stationDiscovery.weatherMapOnly
                              ? "NOAA RADAR + HMS SMOKE // MANUAL REQUESTS"
                              : "GDACS ALERT SQUARES // QUAKES CIRCLES // EONET DIAMONDS // FIRMS ORANGE // NEWS MAGENTA"
                        font.pixelSize: 9
                    }
                }
            }

            // The map's companion is adjacent to the canvas. It is not
            // a second full MEDIA article feed or provider owner.
            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.domain === "map"
                         && stationDiscovery.earthMapOnly

                // No second news feed is created in EARTH. These are the
                // mentioned locations already extracted for the selected MEDIA
                // article. Each remains independently selectable on the map.
                Column {
                    width: parent.width
                    spacing: 6
                    visible: stationDiscovery.domain === "map"
                             && stationDiscovery.earthMapOnly
                             && stationDiscovery.mapNewsMentionRows.length > 0
    
                    StationSectionDivider {
                        width: parent.width
                        title: "MAP COMPANION // ARTICLE MENTIONED PLACES"
                    }
                    QuietText {
                        width: parent.width
                        text: stationDiscovery.newsMentionOverlay
                              ? stationDiscovery.newsMentionOverlay.articleTitle
                              : ""
                        elide: Text.ElideRight
                        color: Colors.magenta
                        font.pixelSize: 10
                    }
                    Repeater {
                        model: stationDiscovery.mapNewsMentionRows.slice(0, 5)
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.min(parent.width, 360)
                            height: 28
                            label: "◉ " + modelData.name
                            labelPixelSize: 10
                            accentColor: Colors.magenta
                            selected: stationDiscovery.selectedMapNewsMention
                                      === modelData
                            onClicked: {
                                stationDiscovery.inspectNewsMention(modelData);
                                stationDiscovery.applyMapView(
                                    MapProjection.fitRows([modelData], 1.35)
                                );
                            }
                        }
                    }
                    QuietText {
                        width: parent.width
                        text: "ARTICLE MENTIONS ONLY // NOT VERIFIED EVENT LOCATIONS"
                        font.pixelSize: 9
                        color: Colors.orange
                    }
                }

                StationSectionDivider {
                    width: parent.width
                    visible: stationDiscovery.earthLayerEnabled("eonet")
                    title: stationDiscovery.earthMapRoute === "earth/events/eonet"
                        ? "NASA EONET // FULL EVENT LIST"
                        : "EARTH MAP CONTEXT // EONET EVENTS IN VIEW"
                }
                QuietText {
                    width: parent.width
                    visible: stationDiscovery.earthLayerEnabled("eonet")
                    text: stationDiscovery.earthMapRoute === "earth/events/eonet"
                        ? "ALL SOURCE EVENTS // SELECT TO INSPECT"
                        : "SHOWING " + stationDiscovery.mapCompanionEonetRows.length
                          + " CONTEXT EVENTS // COMPLETE LIST UNDER EARTH → EVENTS → EONET"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                QuietText {
                    width: parent.width
                    visible: stationDiscovery.earthLayerEnabled("eonet")
                             && !source.ready
                    text: source.failed ? source.errorText
                          : source.retryWaitSeconds > 0
                            ? "EONET REQUEST HELD // PROVIDER COOLDOWN"
                          : source.loading ? "RECEIVING EONET EVENTS"
                          : "EONET SOURCE WAITING"
                    color: Colors.orange
                    font.pixelSize: 9
                }
                Repeater {
                    model: stationDiscovery.domain === "map"
                            && stationDiscovery.earthMapOnly
                            && stationDiscovery.earthLayerEnabled("eonet")
                            && source.ready
                        ? stationDiscovery.mapCompanionEonetRows : []
                    delegate: discoveryRecordCard
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
                         && stationDiscovery.newsGroupVisible("filters")
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
                         && stationDiscovery.newsGroupVisible("filters")
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
                         && stationDiscovery.newsGroupVisible("filters")
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
                         && stationDiscovery.newsGroupVisible("filters")
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
                         && stationDiscovery.newsGroupVisible("filters")
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

            // M28-B: MEDIA owns the full article feed. Keep its working
            // filters together, then show headlines before optional analytics.
            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.domain === "news"
                         && stationDiscovery.newsGroupVisible("list")

                StationSectionDivider {
                    width: parent.width
                    title: "NEWS HEADLINES // CURRENT FILTERED BATCH // "
                         + stationDiscovery.visibleRows.length
                }

                QuietText {
                    width: parent.width
                    visible: !source.ready || stationDiscovery.visibleRows.length === 0
                    wrapMode: Text.WordWrap
                    text: source.failed ? source.errorText
                          : source.retryWaitSeconds > 0
                            ? "REQUEST HELD // PROVIDER COOLDOWN // ARTICLES NOT LOADED"
                          : source.loading ? "RECEIVING NEWS HEADLINES"
                          : source.ready
                            ? "NO HEADLINES MATCH THE ACTIVE FILTERS"
                            : "NEWS SOURCE WAITING // REQUEST A FRESH BATCH"
                    color: Colors.orange
                    font.pixelSize: 10
                }

                Repeater {
                    // NEWS reports/filters/locations/viewer only. Analytic
                    // routes must not instantiate a hidden headline feed.
                    model: stationDiscovery.newsGroupVisible("list")
                           && source.ready
                        ? stationDiscovery.visibleRows : []
                    delegate: discoveryRecordCard
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.domain === "news"
                         && (stationDiscovery.newsGroupVisible("trend")
                             || stationDiscovery.newsGroupVisible("stories"))

                StationSectionDivider {
                    visible: stationDiscovery.newsGroupVisible("trend")
                    width: parent.width
                    title: "REPORTING TREND // CURRENT FILTERED BATCH"
                }

                Row {
                    visible: stationDiscovery.newsGroupVisible("trend")
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
                    visible: stationDiscovery.newsGroupVisible("trend")
                    width: parent.width
                    text: "ORANGE = ARTICLES // CYAN = UNIQUE PUBLISHERS // LOCAL HISTOGRAM FROM GDELT SEENDATE // FILTER CHANGES RECOMPUTE WITHOUT REFETCH"
                    font.pixelSize: 9
                    color: Colors.orange
                }

                StationSectionDivider {
                    visible: stationDiscovery.newsGroupVisible("stories")
                    width: parent.width
                    title: "STORY FAMILIES // CONSERVATIVE TITLE TOKENS"
                }

                Column {
                    width: parent.width
                    spacing: 5
                    visible: stationDiscovery.newsGroupVisible("stories")
                             && stationDiscovery.newsStoryFamilies.length > 0

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
                    visible: stationDiscovery.newsGroupVisible("stories")
                             && stationDiscovery.newsStoryFamilies.length === 0
                    width: parent.width
                    text: "NO MULTI-HEADLINE FAMILY CLEARS THE STRICT LOCAL TOKEN THRESHOLD IN THIS FILTERED BATCH"
                    font.pixelSize: 9
                }

                QuietText {
                    visible: stationDiscovery.newsGroupVisible("stories")
                    width: parent.width
                    text: "LOCAL TITLE-TOKEN CLUSTERS // ≥3 SHARED TOKENS + ≥75% SHORTER-TITLE OVERLAP + ≥62% JACCARD // NOT EMBEDDING SEMANTICS OR VERIFIED EVENT IDENTITY"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            QuietText {
                visible: stationDiscovery.domain === "news"
                         && stationDiscovery.newsGroupVisible("inspector-hint")
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.yellow
                text: MediaPanelPolicy.hintFor(stationDiscovery.newsSubjectRoute)
                font.pixelSize: 10
            }

            QuietText {
                width: parent.width
                text: stationDiscovery.sourceCaution
                font.pixelSize: 11
            }

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.eventContextInspectorOpen

                StationSectionDivider {
                    width: parent.width
                    title: "EVENT CONTEXT // CROSS-DOMAIN"
                }

                StationEventContextCard {
                    width: parent.width
                    eventContext: stationDiscovery.selectedEventContext
                    weatherFixDistanceKm:
                        stationDiscovery.selectedWeatherFixDistanceKm
                    radarContext:
                        stationDiscovery.selectedRadarContext
                    lightningContext:
                        stationDiscovery.selectedLightningContext
                    floodContext:
                        stationDiscovery.selectedFloodContext
                    timelineRows:
                        stationDiscovery.selectedEvidenceTimeline
                    relationshipRows:
                        stationDiscovery.selectedEvidenceRelationships
                    runtimeNowMs:
                        stationDiscovery.runtimeNowMs
                    companions:
                        stationDiscovery.selectedContextCompanions
                    archiveAvailable:
                        stationDiscovery.selectedArchiveAvailable
                    archiveSnapshotCount:
                        stationDiscovery.selectedArchiveCount
                    archiveStatusText:
                        stationDiscovery.selectedArchiveStatus
                    dossierPreview:
                        stationDiscovery.selectedDossierPreview
                    dossierCaptureReview:
                        stationDiscovery.selectedDossierCaptureReview
                    dossierSaveAvailable:
                        stationDiscovery.dossierSaveAvailable
                    dossierSaveStatus:
                        stationDiscovery.selectedDossierSaveStatus
                    dossierSavedCount:
                        stationDiscovery.selectedDossierCount
                    onDossierSaveRequested:
                        stationDiscovery.saveSelectedDossier()
                    archiveRows:
                        stationDiscovery.selectedArchiveRows
                    archiveDiff:
                        stationDiscovery.selectedArchiveDiff
                    archivePairDiff:
                        stationDiscovery.selectedArchivePairDiff
                    archivePairCustom:
                        stationDiscovery.archivePairCustom
                    archiveEarlierPosition:
                        stationDiscovery.resolvedArchiveEarlierPosition
                    archiveLaterPosition:
                        stationDiscovery.resolvedArchiveLaterPosition
                    accentColor:
                        stationDiscovery.eventContextAccentColor()
                    onArchiveRequested:
                        stationDiscovery.archiveSelectedEvent()
                    onArchivePairRequested: (earlier, later) =>
                        stationDiscovery.selectArchivePair(earlier, later)
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: stationDiscovery.gdacsInspectorOpen

                StationSectionDivider {
                    width: parent.width
                    title: "DISASTER INSPECTOR // GDACS"
                }

                Rectangle {
                    width: parent.width
                    height: 188
                    color: Colors.dark
                    border.width: 1
                    border.color: stationDiscovery.selectedMapGdacsEvent
                                  ? stationDiscovery.gdacsAlertColor(
                                        stationDiscovery.selectedMapGdacsEvent.alertLevel
                                    )
                                  : Colors.magenta

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 5

                        Row {
                            width: parent.width
                            spacing: 10

                            GohuText {
                                width: Math.max(0, parent.width - 96)
                                text: stationDiscovery.selectedMapGdacsEvent
                                      ? stationDiscovery.selectedMapGdacsEvent.name
                                      : ""
                                color: stationDiscovery.selectedMapGdacsEvent
                                       ? stationDiscovery.gdacsAlertColor(
                                             stationDiscovery.selectedMapGdacsEvent.alertLevel
                                         )
                                       : Colors.white
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
                                    stationDiscovery.closeGdacsInspector()
                            }
                        }

                        SecondaryText {
                            width: parent.width
                            text: stationDiscovery.selectedMapGdacsEvent
                                  ? stationDiscovery.selectedMapGdacsEvent.eventTypeLabel
                                    + " // ALERT "
                                    + stationDiscovery.selectedMapGdacsEvent.alertLevel
                                    + " // "
                                    + (stationDiscovery.selectedMapGdacsEvent.country !== ""
                                       ? stationDiscovery.selectedMapGdacsEvent.country
                                       : "COUNTRY --")
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 11
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapGdacsEvent
                                  ? stationDiscovery.selectedMapGdacsEvent.coordinates
                                    + " // "
                                    + (stationDiscovery.selectedMapGdacsEvent.isCurrent
                                       ? "CURRENT EVENT" : "RECENT EVENT")
                                    + " // ID "
                                    + stationDiscovery.selectedMapGdacsEvent.eventId
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapGdacsEvent
                                  ? "SEVERITY // "
                                    + stationDiscovery.selectedMapGdacsEvent.severityText
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: stationDiscovery.selectedMapGdacsEvent
                                  ? "WINDOW // "
                                    + stationDiscovery.selectedMapGdacsEvent.fromUtc
                                    + " → "
                                    + stationDiscovery.selectedMapGdacsEvent.toUtc
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: "GLOBAL DISASTER AWARENESS AND COORDINATION SYSTEM, GDACS // EARLY-WARNING CONTEXT // VERIFY LOCAL/NATIONAL WARNINGS"
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
                visible: stationDiscovery.domain === "map"
                         && !stationDiscovery.weatherMapOnly
                         && stationDiscovery.earthLayerEnabled("eonet")
                         && (source.failed || !source.ready || source.rows.length === 0)
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
                // Preserve the original complete CLASSIC MAP event list until
                // all legacy capabilities pass the final SUBJECTS cutover.
                model: stationDiscovery.domain === "map"
                       && !stationDiscovery.earthMapOnly && source.ready
                    ? stationDiscovery.visibleRows : []
                visible: !stationDiscovery.weatherMapOnly
                         && stationDiscovery.earthLayerEnabled("eonet")
                delegate: discoveryRecordCard
            }

            QuietText {
                width: parent.width
                text: stationDiscovery.earthMapOnly
                      ? EarthPanelPolicy.routeLabel(stationDiscovery.earthMapRoute)
                        + " // NATIVE SOURCE RECORDS // SELECT TO INSPECT"
                      : stationDiscovery.weatherMapOnly
                        ? "RADAR + SMOKE // MANUAL SOURCE REQUESTS"
                      : source.ready
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
