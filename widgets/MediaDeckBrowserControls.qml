import QtQuick
import "../components"

// Physical-style browser controls. Search entry and media actions live
// here, not as clickable overlays on the display or cassette bay.
Item {
    id: bay
    required property var deckHost
    required property var controller
    property alias queryText: searchInput.text
    readonly property bool searchEditing: searchInput.activeFocus

    Item {
        id: searchRow
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: 30

        ActionButton {
            id: sourceKey
            anchors { left: parent.left; top: parent.top }
            width: 84
            height: parent.height
            label: bay.deckHost.catalogSource === "youtube" ? "YOUTUBE"
                : bay.deckHost.catalogSource === "direct-stream" ? "RADIO" : "LIBRARY"
            labelPixelSize: 10
            selected: bay.deckHost.navigationZone === 0
            onClicked: bay.deckHost.toggleCatalogSource()
        }

        Rectangle {
            id: queryBezel
            anchors {
                left: sourceKey.right; right: searchKey.left
                top: parent.top; bottom: parent.bottom
                leftMargin: 7; rightMargin: 7
            }
            color: Colors.black
            radius: 2
            border.width: 1
            border.color: searchInput.activeFocus ? Colors.magenta : Colors.cyan

            TextInput {
                id: searchInput
                anchors { fill: parent; leftMargin: 7; rightMargin: 7; topMargin: 6; bottomMargin: 5 }
                color: Colors.white
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.pixelSize: 12
                clip: true
                activeFocusOnTab: true
                readOnly: bay.deckHost.catalogSource === "direct-stream"
                onAccepted: bay.deckHost.searchLibrary()
            }
            GohuText {
                anchors { left: parent.left; leftMargin: 7; verticalCenter: parent.verticalCenter }
                visible: !searchInput.text.length && !searchInput.activeFocus
                text: bay.deckHost.catalogSource === "direct-stream"
                    ? "GROOVE SALAD / RADIO" : "ARTIST / SONG / ALBUM"
                font.pixelSize: 10
                opacity: 0.55
                color: Colors.cyan
            }
        }

        ActionButton {
            id: searchKey
            anchors { right: parent.right; top: parent.top }
            width: 79
            height: parent.height
            label: "SEARCH"
            labelPixelSize: 10
            available: !bay.controller.busy
                       && bay.deckHost.catalogSource !== "direct-stream"
            onClicked: bay.deckHost.searchLibrary()
        }
    }

    Row {
        id: navigationRig
        anchors { top: searchRow.bottom; topMargin: 2; left: parent.left }
        height: 160
        spacing: 6

        // Small left encoder navigates SOURCE / RESULTS / NOW.
        Item {
            width: 110
            height: navigationRig.height
            SelectorDial {
                id: navigationDial
                anchors.centerIn: parent
                scale: 0.77
                labelText: "HORIZONTAL"
                options: ["SOURCE", "RESULTS", "NOW"]
                currentIndex: bay.deckHost.navigationZone
                accentColor: Colors.cyan
                markerColor: Colors.orange
                onSelectionRequested: function(index, value) {
                    bay.deckHost.navigationZone = index;
                }
            }
        }

        SelectorSlider {
            id: resultSlider
            width: 40
            height: 151
            anchors.verticalCenter: parent.verticalCenter
            count: bay.deckHost.browseItems.length
            currentIndex: bay.deckHost.browseIndex
            sideLabel: "TRACK"
            indexInteraction: "legacy"
            enabledSlider: bay.deckHost.transportMode === "mpd" && count > 1
            onIndexRequested: function(index) {
                bay.deckHost.highlightRow(index);
            }
        }

        // Large encoder jumps between five-item groups without playback.
        Item {
            width: 150
            height: navigationRig.height
            SelectorDial {
                id: tuningDial
                anchors.centerIn: parent
                scale: 1.0
                labelText: "TUNE"
                options: bay.deckHost.tuningGroups
                currentIndex: bay.deckHost.tuningGroup
                accentColor: Colors.cyan
                markerColor: Colors.orange
                onSelectionRequested: function(index, value) {
                    bay.deckHost.tuneToGroup(index);
                }
            }
        }

        Column {
            width: Math.max(90, bay.width - 110 - 40 - 150 - 3 * navigationRig.spacing)
            height: navigationRig.height
            spacing: 6

            ActionButton {
                width: parent.width; height: 42
                label: "SELECT"
                labelPixelSize: 12
                available: !!bay.deckHost.highlightedItem && !bay.controller.busy
                           && bay.deckHost.transportMode === "mpd"
                onClicked: bay.deckHost.selectHighlighted()
            }
            ActionButton {
                width: parent.width; height: 42
                label: "ENTER"
                labelPixelSize: 12
                available: !bay.controller.busy && bay.deckHost.transportMode === "mpd"
                onClicked: bay.deckHost.enterHighlighted()
            }
            ActionButton {
                width: parent.width; height: 42
                label: "LOAD"
                labelPixelSize: 12
                available: !!bay.controller.selection
                           && (bay.controller.selection.source === "local-mpd"
                               || bay.controller.selection.source === "direct-stream")
                           && !bay.controller.busy
                           && bay.deckHost.transportMode === "mpd"
                onClicked: bay.deckHost.loadStaged()
            }
            GohuText {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "SHIFT / SELECT"
                color: Colors.orange
                font.pixelSize: 9
            }
        }
    }
}
