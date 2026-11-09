import QtQuick
import "../../components"

// CPU++ LOCATION // Middle SELECT bay. Saved Home, active point and
// bookmarks stay together as selectable data. The existing SavedPlacesPanel
// remains the ONLY saved-place control surface and uses PlaceRegistry.
Item {
    id: locationSelection
    property var registry: null
    property string durationKey: "2H"

    readonly property var savedHome:
        registry ? registry.homePlace : null
    readonly property var currentPlace:
        registry ? registry.effectivePlace : null

    Flickable {
        id: selectedPlacesScroll
        anchors.fill: parent
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

            Rectangle {
                width: parent.width
                height: 76
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta
                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    GohuText {
                        text: "⌖  CURRENT // ACTIVE"
                        font.pixelSize: 10
                        color: Colors.magenta
                    }
                    GohuText {
                        width: parent.width
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        color: Colors.white
                        text: locationSelection.currentPlace
                              ? locationSelection.currentPlace.label
                              : "HOME NOT YET CONFIGURED"
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: locationSelection.registry
                              ? "CONTEXT // "+String(locationSelection.registry.contextKind || "UNKNOWN")
                              : "CONTEXT // UNAVAILABLE"
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
        y: 0
        height: parent.height
        visible: scrollable
    }
}
