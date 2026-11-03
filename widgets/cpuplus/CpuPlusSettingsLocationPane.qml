import QtQuick
import "../../components"

// CPU++ edits Home through the shared PlaceRegistry. It never infers or
// transmits a location and never redirects pinned emergency alerts.
Item {
    id: locationPane
    property var registry: null
    property bool awaitingSave: false
    property string feedback: ""

    // CPU++ window shortcuts are suspended while any Home or Explore
    // field is focused. Escape in a field only releases its text focus.
    readonly property bool editingText:
        homeLabelInput.activeFocus || homeLatitudeInput.activeFocus
        || homeLongitudeInput.activeFocus || explorePanel.editingText
        || placeSearchPanel.editingText
    readonly property var savedHome:
        registry ? registry.homePlace : null
    readonly property bool canWrite:
        registry && registry.canSaveHome === true

    function readableError(code) {
        switch (String(code || "")) {
        case "HOME_LABEL_INVALID": return "ENTER A HOME NAME (1-64 CHARACTERS)";
        case "LATITUDE_INVALID": return "LATITUDE MUST BE -90 TO 90";
        case "LONGITUDE_INVALID": return "LONGITUDE MUST BE -180 TO 180";
        case "STORAGE_NOT_READY": return "PLACE STORAGE NOT READY";
        case "FILE_SAVE_FAILED": return "SAVE FAILED // HOME UNCHANGED";
        case "FILE_LOAD_FAILED": return "HOME STORAGE COULD NOT BE READ";
        case "UNSUPPORTED_VERSION": return "STORAGE VERSION NOT SUPPORTED";
        default: return code || "LOCATION STORAGE UNAVAILABLE";
        }
    }

    Connections {
        target: locationPane.registry
        function onStorageStateChanged() {
            if (!locationPane.awaitingSave)
                return;
            const state = String(locationPane.registry.storageState || "");
            if (state === "ready") {
                locationPane.awaitingSave = false;
                locationPane.feedback = "HOME SAVED // PERSISTENT";
            } else if (state === "error" || state === "unsupported") {
                locationPane.awaitingSave = false;
                locationPane.feedback = locationPane.readableError(
                    locationPane.registry.errorCode
                );
            }
        }
    }

    Flickable {
        id: locationScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.y + body.implicitHeight + 14)

        Column {
            id: body
            x: 4
            y: 7
            width: Math.max(0, locationScroll.width - 13)
            spacing: 12

            GohuText {
                text: "PLACES // LOCATION CONTEXT"
                font.pixelSize: 12
                color: Colors.cyan
            }
            QuietText {
                width: parent.width
                text: "HOME // MANUAL // LOCAL STORAGE"
                font.pixelSize: 9
            }

            CpuPlusPlaceSearchPanel {
                id: placeSearchPanel
                width: parent.width

                onUseForHome: function(candidate) {
                    homeLabelInput.text = candidate.label;
                    homeLatitudeInput.text = String(candidate.latitude);
                    homeLongitudeInput.text = String(candidate.longitude);
                    locationPane.feedback =
                        "SEARCH RESULT LOADED // REVIEW THEN SAVE HOME";
                    Qt.callLater(function() {
                        const y = homeLabelInput.mapToItem(body, 0, 0).y - 45;
                        locationScroll.contentY = Math.max(0, Math.min(
                            Math.max(0, locationScroll.contentHeight
                                       - locationScroll.height), y
                        ));
                    });
                }
                onUseForExplore: function(candidate) {
                    explorePanel.fillDestination(candidate);
                    Qt.callLater(function() {
                        const y = explorePanel.mapToItem(body, 0, 0).y - 20;
                        locationScroll.contentY = Math.max(0, Math.min(
                            Math.max(0, locationScroll.contentHeight
                                       - locationScroll.height), y
                        ));
                    });
                }
            }

            Rectangle {
                id: savedCard
                width: parent.width
                height: 107
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6
                    GohuText {
                        text: "⌂  SAVED HOME"
                        font.pixelSize: 12
                        color: Colors.orange
                    }
                    GohuText {
                        width: parent.width
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: Colors.white
                        text: locationPane.savedHome
                              ? locationPane.savedHome.label
                              : "NOT SET"
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: locationPane.savedHome
                              ? Number(locationPane.savedHome.latitude).toFixed(4)
                                + "°, " + Number(locationPane.savedHome.longitude).toFixed(4) + "°"
                              : "SET YOUR DEFAULT POINT BELOW"
                    }
                    QuietText {
                        font.pixelSize: 9
                        text: "STORE // " + (
                            locationPane.registry
                            ? String(locationPane.registry.storageState).toUpperCase()
                            : "NOT CONNECTED"
                        )
                    }
                }
            }

            GohuText {
                text: "SET // REPLACE HOME"
                font.pixelSize: 11
                color: Colors.cyan
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "NAME + COORDINATES // NO IP GUESSING"
                font.pixelSize: 9
            }

            Column {
                width: parent.width
                spacing: 5
                GohuText {
                    text: "PLACE NAME"
                    font.pixelSize: 9
                    color: Colors.white
                }
                Rectangle {
                    width: parent.width
                    height: 35
                    color: Colors.black
                    border.width: 1
                    border.color: homeLabelInput.activeFocus
                                  ? Colors.magenta : Colors.cyan
                    TextInput {
                        id: homeLabelInput
                        anchors.fill: parent
                        anchors.margins: 8
                        font.family: GohuFont.family
                        font.pixelSize: 11
                        color: Colors.white
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        selectByMouse: true
                        maximumLength: 64
                        clip: true
                        Keys.onEscapePressed: function(event) {
                            event.accepted = true;
                            homeLabelInput.focus = false;
                        }
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 7

                Column {
                    width: (parent.width - 7) / 2
                    spacing: 5
                    GohuText {
                        text: "LATITUDE"
                        font.pixelSize: 9
                        color: Colors.white
                    }
                    Rectangle {
                        width: parent.width
                        height: 35
                        color: Colors.black
                        border.width: 1
                        border.color: homeLatitudeInput.activeFocus
                                      ? Colors.magenta : Colors.cyan
                        TextInput {
                            id: homeLatitudeInput
                            anchors.fill: parent
                            anchors.margins: 8
                            font.family: GohuFont.family
                            font.pixelSize: 11
                            color: Colors.white
                            selectionColor: Colors.magenta
                            selectedTextColor: Colors.black
                            selectByMouse: true
                            maximumLength: 16
                            clip: true
                            Keys.onEscapePressed: function(event) {
                                event.accepted = true;
                                homeLatitudeInput.focus = false;
                            }
                        }
                    }
                }

                Column {
                    width: (parent.width - 7) / 2
                    spacing: 5
                    GohuText {
                        text: "LONGITUDE"
                        font.pixelSize: 9
                        color: Colors.white
                    }
                    Rectangle {
                        width: parent.width
                        height: 35
                        color: Colors.black
                        border.width: 1
                        border.color: homeLongitudeInput.activeFocus
                                      ? Colors.magenta : Colors.cyan
                        TextInput {
                            id: homeLongitudeInput
                            anchors.fill: parent
                            anchors.margins: 8
                            font.family: GohuFont.family
                            font.pixelSize: 11
                            color: Colors.white
                            selectionColor: Colors.magenta
                            selectedTextColor: Colors.black
                            selectByMouse: true
                            maximumLength: 16
                            clip: true
                            Keys.onEscapePressed: function(event) {
                                event.accepted = true;
                                homeLongitudeInput.focus = false;
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: saveHomeButton
                width: parent.width
                height: 38
                readonly property bool hovered: saveHomeMouse.containsMouse
                readonly property bool pressed: saveHomeMouse.pressed
                color: pressed ? Colors.magenta
                      : hovered ? Colors.yellow : Colors.dark
                border.width: 1
                border.color: locationPane.canWrite ? Colors.orange : Colors.white
                opacity: locationPane.canWrite ? 1.0 : 0.50

                GohuText {
                    anchors.centerIn: parent
                    text: locationPane.awaitingSave ? "SAVING..." : "SAVE HOME"
                    color: saveHomeButton.pressed ? Colors.black : Colors.cyan
                    font.pixelSize: 12
                }
                MouseArea {
                    id: saveHomeMouse
                    anchors.fill: parent
                    enabled: locationPane.canWrite
                    hoverEnabled: enabled
                    onClicked: {
                        locationPane.feedback = "";
                        locationPane.awaitingSave = true;
                        locationPane.feedback = "SAVING // WAIT FOR CONFIRMATION";
                        const ok = locationPane.registry.saveHome(
                            homeLabelInput.text,
                            homeLatitudeInput.text,
                            homeLongitudeInput.text
                        );
                        if (!ok) {
                            locationPane.awaitingSave = false;
                            locationPane.feedback = locationPane.readableError(
                                locationPane.registry.errorCode
                            );
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                text: locationPane.feedback ||
                      (locationPane.registry && locationPane.registry.errorCode
                        ? locationPane.readableError(locationPane.registry.errorCode)
                        : "ONLY SAVE HOME CHANGES THE DEFAULT PLACE")
            }

            CpuPlusExploreLocationPanel {
                id: explorePanel
                width: parent.width
                registry: locationPane.registry
            }

            CpuPlusSavedPlacesPanel {
                id: savedPlacesPanel
                width: parent.width
                registry: locationPane.registry
                durationKey: explorePanel.durationKey
            }

            Rectangle {
                width: parent.width
                height: 96
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta

                Column {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 6
                    GohuText {
                        text: "SHARED CONTEXT // "
                              + (locationPane.registry
                                 ? locationPane.registry.contextKind : "UNKNOWN")
                        font.pixelSize: 10
                        color: Colors.magenta
                    }
                    GohuText {
                        width: parent.width
                        elide: Text.ElideRight
                        font.pixelSize: 10
                        color: Colors.white
                        text: locationPane.registry && locationPane.registry.effectivePlace
                              ? locationPane.registry.effectivePlace.label
                              : "NO HOME CONFIGURED"
                    }
                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: 9
                        text: "CONTEXT READY // ROUTING TO WEATHER, SKY, GROUND AND MAP IS NOT WIRED. ALERT TARGETS REMAIN PINNED."
                    }
                }
            }
        }
    }

    NeonScrollBar {
        flickable: locationScroll
        x: parent.width - width
        y: 0
        height: parent.height
        visible: scrollable
    }
}
