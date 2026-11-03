import QtQuick
import qs.services.location
import "../../components"

// Search only previews coordinates. Home/Explore writes happen separately.
Item {
    id: searchPanel
    signal useForHome(var candidate)
    signal useForExplore(var candidate)
    readonly property bool editingText: queryInput.activeFocus
    implicitHeight: searchContent.implicitHeight

    function search() {
        searchService.search(queryInput.text);
    }

    function statusText() {
        switch (searchService.status) {
        case "idle": return "TYPE A PLACE NAME AND PRESS SEARCH";
        case "loading": return "SEARCHING // WAITING FOR RESULTS";
        case "empty": return "NO MATCHING PLACES";
        case "ready": return searchService.rows.length + " MATCHES // SELECT ONE";
        case "error":
            switch (searchService.errorCode) {
            case "QUERY_INVALID": return "ENTER 2-80 CHARACTERS";
            case "RATE_GUARD": return "RETRY IN A MOMENT";
            case "REQUEST_FAILED": return "GEOCODING CONNECTION FAILED";
            case "JSON_INVALID":
            case "RESPONSE_INVALID": return "GEOCODING RESPONSE INVALID";
            default: return "GEOCODING SOURCE UNAVAILABLE";
            }
        default: return "LOCATION SEARCH UNAVAILABLE";
        }
    }

    PlaceLookupService {
        id: searchService
    }

    Column {
        id: searchContent
        width: parent.width
        spacing: 9

        GohuText {
            width: parent.width
            text: "⌕  FIND A PLACE"
            font.pixelSize: 12
            color: Colors.cyan
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: "CITY, REGION, OR POSTAL CODE // NO STREET ADDRESS SEARCH"
        }

        Rectangle {
            width: parent.width
            height: 36
            color: Colors.black
            border.width: 1
            border.color: queryInput.activeFocus ? Colors.magenta : Colors.cyan

            TextInput {
                id: queryInput
                anchors.fill: parent
                anchors.margins: 8
                font.family: GohuFont.family
                font.pixelSize: 11
                color: Colors.white
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                selectByMouse: true
                maximumLength: 80
                clip: true
                onAccepted: searchPanel.search()
                Keys.onEscapePressed: function(event) {
                    event.accepted = true;
                    queryInput.focus = false;
                }
            }
        }

        Rectangle {
            id: runSearchButton
            width: parent.width
            height: 35
            readonly property bool hovered: runSearchMouse.containsMouse
            readonly property bool pressed: runSearchMouse.pressed
            color: pressed ? Colors.magenta
                   : hovered ? Colors.yellow : Colors.dark
            border.width: 1
            border.color: Colors.orange
            opacity: searchService.loading ? 0.5 : 1.0

            GohuText {
                anchors.centerIn: parent
                text: searchService.loading ? "SEARCHING..." : "SEARCH PLACES"
                font.pixelSize: 11
                color: runSearchButton.pressed ? Colors.black : Colors.cyan
            }
            MouseArea {
                id: runSearchMouse
                anchors.fill: parent
                enabled: !searchService.loading
                hoverEnabled: enabled
                onClicked: searchPanel.search()
            }
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: searchPanel.statusText()
        }

        Repeater {
            model: searchService.rows

            delegate: Rectangle {
                id: resultCard
                required property var modelData
                width: searchContent.width
                height: 112
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        textFormat: Text.PlainText
                        text: resultCard.modelData.label
                        color: Colors.white
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }

                    QuietText {
                        width: parent.width
                        textFormat: Text.PlainText
                        text: Number(resultCard.modelData.latitude).toFixed(4)
                              + "°, "
                              + Number(resultCard.modelData.longitude).toFixed(4)
                              + "°"
                              + (resultCard.modelData.timezone
                                 ? " // " + resultCard.modelData.timezone : "")
                        color: Colors.cyan
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }

                    Row {
                        width: parent.width
                        height: 31
                        spacing: 6

                        Rectangle {
                            id: useHomeButton
                            width: (parent.width - 6) / 2
                            height: 30
                            color: homeMouse.pressed ? Colors.magenta
                                   : homeMouse.containsMouse
                                   ? Colors.yellow : Colors.dark
                            border.width: 1
                            border.color: Colors.orange

                            GohuText {
                                anchors.centerIn: parent
                                text: "USE FOR HOME"
                                font.pixelSize: 9
                                color: homeMouse.pressed ? Colors.black : Colors.orange
                            }
                            MouseArea {
                                id: homeMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: searchPanel.useForHome(resultCard.modelData)
                            }
                        }

                        Rectangle {
                            id: useExploreButton
                            width: (parent.width - 6) / 2
                            height: 30
                            color: exploreMouse.pressed ? Colors.magenta
                                   : exploreMouse.containsMouse
                                   ? Colors.yellow : Colors.dark
                            border.width: 1
                            border.color: Colors.cyan

                            GohuText {
                                anchors.centerIn: parent
                                text: "USE FOR EXPLORE"
                                font.pixelSize: 9
                                color: exploreMouse.pressed ? Colors.black : Colors.cyan
                            }
                            MouseArea {
                                id: exploreMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: searchPanel.useForExplore(resultCard.modelData)
                            }
                        }
                    }
                }
            }
        }

        SecondaryText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: "LOCATION DATA // GEONAMES VIA OPEN-METEO. "
                  + "EXPLICIT ONLINE SEARCH // NON-COMMERCIAL API. "
                  + "RESULTS ARE PREVIEWS UNTIL YOU SAVE HOME OR EXPLORE."
        }
    }
}
