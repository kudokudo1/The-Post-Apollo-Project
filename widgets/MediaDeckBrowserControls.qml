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
            anchors { right: parent.right; top: parent.top }
            width: 84
            height: parent.height
            label: bay.deckHost.catalogSource === "youtube" ? "YOUTUBE"
                : bay.deckHost.catalogSource === "radio-browser" ? "RADIO"
                : bay.deckHost.catalogSource === "direct-stream" ? "PRESET" : "LIBRARY"
            labelPixelSize: 10
            // Ordinary ActionButton: no specialized/latched selection face.
            onClicked: bay.deckHost.toggleCatalogSource()
        }

        Rectangle {
            id: queryBezel
            anchors {
                left: searchKey.right; right: sourceKey.left
                top: parent.top; bottom: parent.bottom
                leftMargin: 7; rightMargin: 7
            }
            color: Colors.black
            radius: 2
            border.width: searchInput.activeFocus ? 2 : 1
            border.color: Colors.magenta

            TextInput {
                id: searchInput
                anchors { fill: parent; leftMargin: 7; rightMargin: 7; topMargin: 6; bottomMargin: 5 }
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                cursorDelegate: Rectangle {
                    width: 2
                    height: Math.max(12, searchInput.cursorRectangle.height)
                    color: Colors.orange
                }
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
                    ? "GROOVE SALAD / PRESET"
                    : bay.deckHost.catalogSource === "radio-browser"
                      ? "NAME / TAG:JAZZ / COUNTRY:US"
                      : "ARTIST / SONG / ALBUM"
                font.pixelSize: 10
                opacity: 0.55
                color: Colors.magenta
            }
        }

        ActionButton {
            id: searchKey
            anchors { left: parent.left; top: parent.top }
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
        anchors {
            top: searchRow.bottom
            topMargin: 2
            left: parent.left
            right: parent.right
        }
        height: 160
        spacing: 6

        // Leftmost vertical slider: precise result-by-result movement.
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

        // Smaller horizontal encoder: SOURCE / RESULTS / NOW.
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

        // Ordinary action buttons between the small encoder and the tuner.
        Column {
            id: mediaActionColumn
            width: Math.max(90, navigationRig.width - 40 - 110 - 150
                                - 3 * navigationRig.spacing)
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
                               || bay.controller.selection.source === "direct-stream"
                               || bay.controller.selection.source === "radio-browser")
                           && !bay.controller.busy
                           && bay.deckHost.transportMode === "mpd"
                onClicked: bay.deckHost.loadStaged()
            }
            ActionButton {
                width: parent.width
                height: 16
                visible: bay.deckHost.catalogSource === "radio-browser"
                label: "NEXT 50"
                labelPixelSize: 9
                available: !!bay.deckHost.nextBrowseCursor && !bay.controller.busy
                onClicked: bay.deckHost.nextRadioPage()
            }
            GohuText {
                width: parent.width
                visible: bay.deckHost.catalogSource !== "radio-browser"
                horizontalAlignment: Text.AlignHCenter
                text: "SHIFT / SELECT"
                color: Colors.orange
                font.pixelSize: 9
            }
        }

        // Larger tuning encoder at the right end of the control bay.
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
    }
}
