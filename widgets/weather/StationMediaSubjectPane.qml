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
    signal newsMapRequested(var payload)

    readonly property string kind:
        MediaPanelPolicy.kindForRoute(subjectRoute)

    // Only the actually loaded NEWS player may publish host-local geometry.
    // A RADIO route and an unloaded/hidden pane return an empty rectangle.
    // On MEDIA overview the NEWS hub is NESTED inside the overview Item.
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

    Loader {
        id: mediaLoader
        anchors.fill: parent
        active: mediaPane.visible && mediaPane.kind !== ""
        sourceComponent: mediaPane.kind === "overview"
                         ? overviewComponent
                         : mediaPane.kind === "radio"
                           ? radioComponent : newsComponent
    }

    Component {
        id: newsComponent
        StationNewsHub {
            stationOpen: mediaPane.visible
            subjectRoute: mediaPane.subjectRoute
            runtimeNowMs: mediaPane.runtimeNowMs
            onNewsMapRequested: function(payload) {
                mediaPane.newsMapRequested(payload);
            }
        }
    }

    Component {
        id: radioComponent
        StationRadio {
            stationOpen: mediaPane.visible
            subjectRoute: mediaPane.subjectRoute
        }
    }

    // The MEDIA overview offers NEWS and RADIO simultaneously. WATCH and
    // creator catalogues remain available in the sibling route rail.
    // Full-width stacked viewports preserve independent star scrollbars.
    Component {
        id: overviewComponent
        Item {
            id: mediaOverview

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

            Rectangle {
                id: reportsBay
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.max(0,(mediaOverview.height - 8) / 2)
                clip: true
                color: Colors.black

                StationNewsHub {
                    id: overviewNewsHub
                    anchors.fill: parent
                    stationOpen: mediaPane.visible
                    subjectRoute: "media/news/reports"
                    runtimeNowMs: mediaPane.runtimeNowMs
                    onNewsMapRequested: function(payload) {
                        mediaPane.newsMapRequested(payload);
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: reportsBay.bottom
                anchors.topMargin: 8
                anchors.bottom: parent.bottom
                clip: true
                color: Colors.black

                StationRadio {
                    anchors.fill: parent
                    stationOpen: mediaPane.visible
                    subjectRoute: "media/overview"
                }
            }
        }
    }
}
