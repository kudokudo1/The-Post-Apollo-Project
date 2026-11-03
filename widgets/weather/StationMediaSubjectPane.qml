import QtQuick
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy

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

            Rectangle {
                id: reportsBay
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.max(0,(mediaOverview.height - 8) / 2)
                clip: true
                color: Colors.black

                StationNewsHub {
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
