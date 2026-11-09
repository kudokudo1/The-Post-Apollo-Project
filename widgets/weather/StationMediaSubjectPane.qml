import QtQuick
import "../../components"
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy
import "StationMediaViewportPolicy.js" as ViewportPolicy

// MEDIA D1 mounts original NEWS, WATCH and shared Hi-Fi RADIO controls.
// One loaded NEWS hub for NEWS/WATCH/CREATORS subroutes, and one RADIO
// controller for RADIO subroutes. There is no second feed or MPD server.
Rectangle {
    id: mediaPane
    color: Colors.black
    property string subjectRoute: ""
    property real runtimeNowMs: Date.now()
    // Disposable native fixtures can inspect layout without activating
    // RadioBrowser, MPD, GDELT or creator-feed requests. True by default.
    property bool providerActivationAllowed: true
    signal newsMapRequested(var payload)
    signal routeRequested(string path)

    readonly property string kind:
        MediaPanelPolicy.kindForRoute(subjectRoute)

    // M2 // The contextual rail delegates actions to the currently mounted
    // NEWS, RADIO or SERVICES owner. No controller or provider is duplicated.
    readonly property var loadedRadio: kind==="radio" && mediaLoader.item
        ? mediaLoader.item : null
    readonly property var loadedNews: mediaLoader.item
        ? (kind==="news" ? mediaLoader.item
           : kind==="overview" ? mediaLoader.item.overviewNews : null)
        : null
    readonly property var loadedServices: kind==="services" && mediaLoader.item
        ? mediaLoader.item : null
    function selectRadioPreset(index) {
        if (loadedRadio && loadedRadio.canOperate)
            loadedRadio.searchPreset(index);
    }
    function selectNewsChannel(section) {
        if (!loadedNews) return;
        loadedNews.selectSection(section);
        // OVERVIEW's NEWS is already the selected top bay. Filter it in
        // place; focused NEWS deep routes still return to full NEWS mode.
        if (kind==="news" && subjectRoute!=="media/news/full")
            mediaPane.routeRequested("media/news/full");
    }
    function selectServiceMode(mode) {
        if (loadedServices && (mode==="runtime" || mode==="sources"))
            loadedServices.viewMode=mode;
    }

    // Optional read-only window onto whichever Radio component is actually
    // loaded. A different MEDIA route exposes nothing, not a stale snapshot.
    readonly property var radioFavoritesSnapshot:
        mediaLoader.active && mediaLoader.item
        && (mediaPane.kind==="radio" || mediaPane.kind==="overview")
        ? mediaLoader.item.favoritesBridgeSnapshot || null : null

    // Only the actually loaded NEWS player may publish host-local geometry.
    // A RADIO route and an unloaded/hidden pane return an empty rectangle.
    // On MEDIA overview the NEWS hub is NESTED inside the overview Item.
    readonly property string activeWatchSourceId: {
        if (activePlayerViewportRect.width <= 0 || !mediaLoader.item
                || mediaPane.kind === "radio")
            return "";
        const sourceId = mediaLoader.item.activeWatchSourceId;
        return sourceId === "bbc" || sourceId === "cspan" ? sourceId : "";
    }
    readonly property rect activePlayerViewportRect: {
        if (!mediaPane.visible || !mediaLoader.active || !mediaLoader.item
                || mediaPane.kind === "" || mediaPane.kind === "radio")
            return Qt.rect(0, 0, 0, 0);
        const item = mediaLoader.item;
        const bay = mediaPane.kind === "overview"
                  ? item.activePlayerViewportRect : item.playerViewportRect;
        if (!ViewportPolicy.within(bay, item.width, item.height))
            return Qt.rect(0, 0, 0, 0);
        const origin = item.mapToItem(mediaPane, bay.x, bay.y);
        const mapped = Qt.rect(origin.x, origin.y, bay.width, bay.height);
        return ViewportPolicy.within(mapped, mediaPane.width, mediaPane.height)
               ? mapped : Qt.rect(0, 0, 0, 0);
    }

    // M1 // One fixed COSMOS/EARTH C44 title/tab/divider for every MEDIA
    // screen. NEWS, RADIO and overview own only the content below it.
    StationMediaHeader {
        id: mediaHeader
        objectName: "media-m1-global-fixed-header"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        subjectRoute: mediaPane.subjectRoute
        radioPresets: mediaPane.loadedRadio ? mediaPane.loadedRadio.presets : []
        radioPresetIndex: mediaPane.loadedRadio
            ? mediaPane.loadedRadio.presetIndex : 0
        radioCanOperate: mediaPane.loadedRadio
            ? mediaPane.loadedRadio.canOperate : false
        radioStatus: mediaPane.loadedRadio
            ? mediaPane.loadedRadio.headerStatus : ""
        radioStatusColor: mediaPane.loadedRadio
            ? mediaPane.loadedRadio.headerStatusColor : Colors.white
        newsSection: mediaPane.loadedNews
            ? mediaPane.loadedNews.effectiveSection : "REPORTS"
        servicesMode: mediaPane.loadedServices
            ? mediaPane.loadedServices.viewMode : "runtime"
        onRouteRequested: function(path) {
            mediaPane.routeRequested(path);
        }
        onRadioPresetRequested: function(index) {
            mediaPane.selectRadioPreset(index);
        }
        onNewsSectionRequested: function(section) {
            mediaPane.selectNewsChannel(section);
        }
        onServicesModeRequested: function(mode) {
            mediaPane.selectServiceMode(mode);
        }
    }

    Loader {
        id: mediaLoader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: mediaHeader.bottom
        anchors.bottom: parent.bottom
        active: mediaPane.visible && mediaPane.kind !== ""
        sourceComponent: mediaPane.kind === "overview"
                         ? overviewComponent
                         : mediaPane.kind === "radio"
                           ? radioComponent
                           : mediaPane.kind === "services"
                           ? servicesComponent : newsComponent
    }

    Component {
        id: servicesComponent
        StationMediaServicesPane { embeddedHeader: true }
    }

    Component {
        id: newsComponent
        StationNewsHub {
            stationOpen: mediaPane.visible && mediaPane.providerActivationAllowed
            subjectRoute: mediaPane.subjectRoute
            embeddedHeader: true
            runtimeNowMs: mediaPane.runtimeNowMs
            onNewsMapRequested: function(payload) {
                mediaPane.newsMapRequested(payload);
            }
        }
    }

    Component {
        id: radioComponent
        StationRadio {
            stationOpen: mediaPane.visible && mediaPane.providerActivationAllowed
            subjectRoute: mediaPane.subjectRoute
            embeddedHeader: true
        }
    }

    // The MEDIA overview offers NEWS and RADIO simultaneously. WATCH and
    // creator catalogues remain available in the sibling route rail.
    // Full-width stacked viewports preserve independent star scrollbars.
    Component {
        id: overviewComponent
        Item {
            id: mediaOverview

            objectName: "media-m3-overview"
            readonly property var favoritesBridgeSnapshot:
                overviewRadio.favoritesBridgeSnapshot
            readonly property var overviewNews: overviewNewsHub
            readonly property string activeWatchSourceId:
                activePlayerViewportRect.width > 0
                ? overviewNewsHub.activeWatchSourceId : ""

            // MEDIA overview wraps its NEWS hub; do not pretend Loader.item
            // is itself a StationNewsHub or add a second player instance.
            readonly property rect activePlayerViewportRect: {
                const bay = overviewNewsHub.playerViewportRect;
                if (!ViewportPolicy.within(
                            bay, overviewNewsHub.width, overviewNewsHub.height))
                    return Qt.rect(0, 0, 0, 0);
                const origin = overviewNewsHub.mapToItem(
                                   mediaOverview, bay.x, bay.y);
                const mapped = Qt.rect(origin.x, origin.y,
                                       bay.width, bay.height);
                return ViewportPolicy.within(
                           mapped, mediaOverview.width, mediaOverview.height)
                       ? mapped : Qt.rect(0, 0, 0, 0);
            }

            // M4 // NEWS and RADIO are two stationary instruments. There is
            // deliberately NO parent Flickable; only the existing NEWS
            // feed and RADIO station directory may scroll independently.
            // Reserve real height for the docked full-radio controller.
            Rectangle {
                id: reportsBay
                objectName: "media-m3-news-top-bay"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                // NEWS stays above RADIO, and its existing feed is intact.
                // At the 520x300 shell, the RADIO dock reserves 160px.
                height: Math.max(52,Math.min(110,mediaOverview.height - 166))
                clip: true
                color: Colors.black

                StationNewsHub {
                    id: overviewNewsHub
                    anchors.fill: parent
                    stationOpen: mediaPane.visible && mediaPane.providerActivationAllowed
                    // REPORTS is still the initial visible NEWS feed.
                    // The contextual C44 header now selects all six
                    // original NEWS categories on this same mounted hub.
                    subjectRoute: "media/news/reports"
                    // Preserve the existing focused REPORTS data route
                    // while allowing NEWS filters in the overview C44 rail.
                    overviewChannelFilters: true
                    section: "REPORTS"
                    embeddedHeader: true
                    runtimeNowMs: mediaPane.runtimeNowMs
                    onNewsMapRequested: function(payload) {
                        mediaPane.newsMapRequested(payload);
                    }
                }
            }

            Rectangle {
                id: overviewRadioBay
                objectName: "media-m3-full-radio-bottom-bay"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: reportsBay.bottom
                anchors.topMargin: 6
                anchors.bottom: parent.bottom
                clip: true
                color: Colors.black

                StationRadio {
                    id: overviewRadio
                    objectName: "media-m3-overview-full-radio"
                    anchors.fill: parent
                    stationOpen: mediaPane.visible && mediaPane.providerActivationAllowed
                    // Use the identical RADIO mode/preset/saved/transport
                    // contract as MEDIA → RADIO // ALL. No compact bypass.
                    subjectRoute: "media/radio/full"
                    embeddedHeader: true
                    overviewDocked: true
                }
            }
        }
    }
}
