import QtQuick
import "../../components"

// CPU++ LOCATION // Middle bay: permanently pinned FIND PLACE search,
// scrollable results inside the search, then independently scrollable
// saved Home and bookmarks. All original writers remain in PlaceRegistry.
Item {
    id: locationSelection
    property var registry: null
    property string durationKey: "2H"
    signal homeCandidateRequested(var candidate)
    signal exploreCandidateRequested(var candidate)
    readonly property bool editingText: placeSearchPanel.editingText

    readonly property var savedHome:
        registry ? registry.homePlace : null
    readonly property var currentPlace:
        registry ? registry.effectivePlace : null

    // Top search controls never scroll away. The component itself scrolls
    // only its match list; bookmarks scroll separately below the search.
    CpuPlusPlaceSearchPanel {
        id: placeSearchPanel
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 5
        anchors.rightMargin: 10
        anchors.topMargin: 5
        compactPinned: true
        resultsViewportLimit: Math.max(50,Math.min(108,
            locationSelection.height*0.22))
        height: implicitHeight
        onUseForHome: function(candidate) {
            locationSelection.homeCandidateRequested(candidate);
        }
        onUseForExplore: function(candidate) {
            locationSelection.exploreCandidateRequested(candidate);
        }
    }

    Flickable {
        id: selectedPlacesScroll
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: placeSearchPanel.bottom
        anchors.topMargin: 8
        anchors.bottom: parent.bottom
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height,locationBody.y+locationBody.implicitHeight+13)

        Column {
            id: locationBody
            x: 3
            y: 8
            width: Math.max(0,selectedPlacesScroll.width-13)
            spacing: 10

            GohuText {
                width: parent.width
                text: "LOCATION // SELECT"
                color: Colors.cyan
                font.pixelSize: 11
            }

            Rectangle {
                id: savedHomeCard
                width: parent.width
                height: 103
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    GohuText {
                        text: "⌂  SAVED HOME"
                        font.pixelSize: 11
                        color: Colors.orange
                    }
                    GohuText {
                        width: parent.width
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        color: Colors.white
                        text: locationSelection.savedHome
                              ? locationSelection.savedHome.label : "NOT SET"
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: locationSelection.savedHome
                              ? Number(locationSelection.savedHome.latitude).toFixed(4)
                                +"°, "
                                +Number(locationSelection.savedHome.longitude).toFixed(4)+"°"
                              : "SET THE DEFAULT PLACE ON THE RIGHT"
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: "STORE // "+(locationSelection.registry
                               ? String(locationSelection.registry.storageState).toUpperCase()
                               : "NOT CONNECTED")
                    }
                }
            }

            // Uses the left EXPLORE pane's currently selected duration.
            // Bookmark/recall/remove remain existing one-writer methods.
            CpuPlusSavedPlacesPanel {
                id: savedPlacesPanel
                width: parent.width
                registry: locationSelection.registry
                durationKey: locationSelection.durationKey
            }
        }
    }

    NeonScrollBar {
        flickable: selectedPlacesScroll
        x: parent.width-width
        // The saved-places rail begins beneath the pinned query;
        // it never overlays or scrolls the FIND PLACE header.
        y: selectedPlacesScroll.y
        height: selectedPlacesScroll.height
        visible: scrollable
    }
}
