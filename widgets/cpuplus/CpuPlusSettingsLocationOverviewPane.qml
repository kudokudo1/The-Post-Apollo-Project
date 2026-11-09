import QtQuick
import "../../components"

// CPU++ LOCATION // Wide left side. Search, active context and temporary
// exploration are displayed here; PlaceRegistry remains their sole writer.
// The Home search action only sends an edit-field fill request to the
// existing right-side Home editor.
Item {
    id: locationOverview
    property var registry: null
    signal homeCandidateRequested(var candidate)

    property alias durationKey: explorePanel.durationKey
    readonly property bool editingText:
        placeSearchPanel.editingText || explorePanel.editingText
    readonly property var currentPlace:
        registry ? registry.effectivePlace : null
    readonly property var activeExplore:
        registry ? registry.activeExplore : null

    function revealExploreEditor() {
        Qt.callLater(function() {
            const y=explorePanel.mapToItem(locationBody,0,0).y-20;
            overviewScroll.contentY=Math.max(0,Math.min(
                Math.max(0,overviewScroll.contentHeight-overviewScroll.height),y));
        });
    }

    Flickable {
        id: overviewScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height,locationBody.y+locationBody.implicitHeight+14)

        Column {
            id: locationBody
            x: 4
            y: 7
            width: Math.max(0,overviewScroll.width-14)
            spacing: 12

            GohuText {
                text: "LOCATION // LIVE CONTEXT"
                color: Colors.cyan
                font.pixelSize: 12
            }

            Rectangle {
                width: parent.width
                height: 109
                color: Colors.black
                border.width: 1
                border.color: locationOverview.activeExplore
                              ? Colors.magenta : Colors.orange
                Column {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 7
                    GohuText {
                        width: parent.width
                        font.pixelSize: 11
                        color: Colors.magenta
                        elide: Text.ElideRight
                        text: "SHARED CONTEXT // "
                              +(locationOverview.registry
                                ? String(locationOverview.registry.contextKind || "UNKNOWN")
                                : "NOT CONNECTED")
                    }
                    GohuText {
                        width: parent.width
                        font.pixelSize: 12
                        color: Colors.white
                        elide: Text.ElideRight
                        text: locationOverview.currentPlace
                              ? locationOverview.currentPlace.label
                              : "NO HOME CONFIGURED"
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: locationOverview.currentPlace
                              ? Number(locationOverview.currentPlace.latitude).toFixed(4)
                                +"°, "
                                +Number(locationOverview.currentPlace.longitude).toFixed(4)+"°"
                              : "SELECT OR SET A HOME LOCATION"
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        text: "WEATHER, SKY, GROUND AND MAP ROUTING NOT YET WIRED. ALERT TARGETS STAY PINNED."
                    }
                }
            }

            GohuText {
                text: "FIND // LOCATION"
                color: Colors.cyan
                font.pixelSize: 11
            }
            CpuPlusPlaceSearchPanel {
                id: placeSearchPanel
                width: parent.width
                onUseForHome: function(candidate) {
                    locationOverview.homeCandidateRequested(candidate);
                }
                onUseForExplore: function(candidate) {
                    explorePanel.fillDestination(candidate);
                    locationOverview.revealExploreEditor();
                }
            }

            // Wide interaction area for Explore duration and destination.
            // Selecting a result does NOT start exploration automatically.
            CpuPlusExploreLocationPanel {
                id: explorePanel
                width: parent.width
                registry: locationOverview.registry
            }
        }
    }

    NeonScrollBar {
        flickable: overviewScroll
        x: parent.width-width
        y: 0
        height: parent.height
        visible: scrollable
    }
}
