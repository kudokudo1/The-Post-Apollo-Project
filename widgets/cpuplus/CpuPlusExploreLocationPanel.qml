import QtQuick
import "../../components"

// CPU++ Explore editor. All state and disk operations belong to PlaceRegistry.
// Exploration is scoped data only: no weather/alerts/system-clock changes.
Item {
    id: explorePanel
    property var registry: null
    property string durationKey: "2H"
    property string pendingAction: ""
    property string feedback: ""
    implicitHeight: exploreContents.implicitHeight

    readonly property bool editingText:
        exploreNameInput.activeFocus
        || exploreLatitudeInput.activeFocus
        || exploreLongitudeInput.activeFocus
    readonly property bool canExplore:
        registry && registry.canChangeExplore === true
    readonly property bool canReturnHome:
        registry && registry.canSaveHome === true
        && registry.hasStoredExplore === true
    readonly property var activeExplore:
        registry ? registry.activeExplore : null
    readonly property bool hadExpiredExplore:
        registry && registry.hasStoredExplore && activeExplore === null

    // Search selection only fills inputs; EXPLORE HERE remains explicit.
    function fillDestination(candidate) {
        if (!candidate)
            return;
        exploreNameInput.text = String(candidate.label || "");
        exploreLatitudeInput.text = String(candidate.latitude);
        exploreLongitudeInput.text = String(candidate.longitude);
        feedback = "SEARCH RESULT LOADED // REVIEW THEN EXPLORE HERE";
    }

    function explainError(code) {
        switch (String(code || "")) {
        case "HOME_NOT_SET": return "SET HOME BEFORE EXPLORING";
        case "HOME_LABEL_INVALID": return "ENTER A DESTINATION NAME (1-64 CHARACTERS)";
        case "LATITUDE_INVALID": return "DESTINATION LATITUDE MUST BE -90 TO 90";
        case "LONGITUDE_INVALID": return "DESTINATION LONGITUDE MUST BE -180 TO 180";
        case "EXPLORE_DURATION_INVALID": return "SELECT A VALID DURATION";
        case "EXPLORE_TIME_INVALID": return "SYSTEM TIME IS NOT VALID";
        case "FILE_SAVE_FAILED": return "SAVE FAILED // CONTEXT UNCHANGED";
        case "STORAGE_NOT_READY": return "PLACE STORAGE NOT READY";
        default: return code || "LOCATION CHANGE UNAVAILABLE";
        }
    }

    Connections {
        target: explorePanel.registry
        function onStorageStateChanged() {
            if (!explorePanel.pendingAction)
                return;
            const state = String(explorePanel.registry.storageState || "");
            if (state === "ready") {
                explorePanel.feedback = explorePanel.pendingAction === "EXPLORE"
                                      ? "EXPLORE SAVED // ACTIVE"
                                      : "RETURNED HOME // SAVED";
                explorePanel.pendingAction = "";
            } else if (state === "error" || state === "unsupported") {
                explorePanel.feedback = explorePanel.explainError(
                    explorePanel.registry.errorCode
                );
                explorePanel.pendingAction = "";
            }
        }
    }

    Column {
        id: exploreContents
        width: parent.width
        spacing: 10

        GohuText {
            text: "⌖  EXPLORE LOCATION"
            font.pixelSize: 12
            color: Colors.cyan
        }

        Rectangle {
            width: parent.width
            height: 104
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Column {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 6

                GohuText {
                    width: parent.width
                    elide: Text.ElideRight
                    font.pixelSize: 11
                    color: explorePanel.activeExplore ? Colors.magenta : Colors.white
                    text: explorePanel.activeExplore
                          ? "ACTIVE // " + explorePanel.activeExplore.place.label
                          : explorePanel.hadExpiredExplore
                          ? "EXPIRED // HOME" : "NOT ACTIVE"
                }

                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    text: explorePanel.activeExplore
                          ? Number(explorePanel.activeExplore.place.latitude).toFixed(4)
                            + "°, " + Number(explorePanel.activeExplore.place.longitude).toFixed(4) + "°"
                          : "HOME REMAINS THE DEFAULT"
                }

                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    text: explorePanel.activeExplore
                          ? explorePanel.activeExplore.expiresAtMs === null
                            ? "UNTIL RETURN HOME"
                            : "ENDS IN "
                              + Math.ceil(explorePanel.registry.remainingMs / 60000)
                              + " MIN"
                          : explorePanel.hadExpiredExplore
                          ? "EXPIRY ENFORCED // PERSISTED RECORD CAN BE CLEARED"
                          : "SELECT DESTINATION + DURATION BELOW"
                }
            }
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: "TEMPORARY CONTEXT // DOES NOT REPLACE HOME"
        }

        Column {
            width: parent.width
            spacing: 5
            GohuText {
                text: "DESTINATION NAME"
                color: Colors.white
                font.pixelSize: 9
            }
            Rectangle {
                width: parent.width
                height: 35
                color: Colors.black
                border.width: 1
                border.color: exploreNameInput.activeFocus
                              ? Colors.magenta : Colors.cyan
                TextInput {
                    id: exploreNameInput
                    anchors.fill: parent
                    anchors.margins: 8
                    font.family: GohuFont.family
                    font.pixelSize: 11
                    color: Colors.white
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    maximumLength: 64
                    selectByMouse: true
                    clip: true
                    Keys.onEscapePressed: function(event) {
                        event.accepted = true;
                        exploreNameInput.focus = false;
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
                    border.color: exploreLatitudeInput.activeFocus
                                  ? Colors.magenta : Colors.cyan
                    TextInput {
                        id: exploreLatitudeInput
                        anchors.fill: parent
                        anchors.margins: 8
                        font.family: GohuFont.family
                        font.pixelSize: 11
                        color: Colors.white
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        maximumLength: 16
                        selectByMouse: true
                        clip: true
                        Keys.onEscapePressed: function(event) {
                            event.accepted = true;
                            exploreLatitudeInput.focus = false;
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
                    border.color: exploreLongitudeInput.activeFocus
                                  ? Colors.magenta : Colors.cyan
                    TextInput {
                        id: exploreLongitudeInput
                        anchors.fill: parent
                        anchors.margins: 8
                        font.family: GohuFont.family
                        font.pixelSize: 11
                        color: Colors.white
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        maximumLength: 16
                        selectByMouse: true
                        clip: true
                        Keys.onEscapePressed: function(event) {
                            event.accepted = true;
                            exploreLongitudeInput.focus = false;
                        }
                    }
                }
            }
        }

        GohuText {
            text: "EXPLORATION DURATION"
            color: Colors.white
            font.pixelSize: 9
        }

        Row {
            width: parent.width
            spacing: 4

            Repeater {
                model: [
                    { key: "30M", label: "30 MIN" },
                    { key: "2H", label: "2 HRS" },
                    { key: "1D", label: "1 DAY" },
                    { key: "MANUAL", label: "HOLD" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool chosen:
                        explorePanel.durationKey === modelData.key
                    width: (exploreContents.width - 12) / 4
                    height: 32
                    color: chosen ? Colors.yellow : Colors.dark
                    border.width: 1
                    border.color: chosen ? Colors.magenta : Colors.orange

                    GohuText {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: parent.chosen ? Colors.black : Colors.white
                        font.pixelSize: 9
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: explorePanel.durationKey = modelData.key
                    }
                }
            }
        }

        Rectangle {
            id: startExploreButton
            width: parent.width
            height: 38
            readonly property bool hovered: startExploreMouse.containsMouse
            readonly property bool pressed: startExploreMouse.pressed
            color: pressed ? Colors.magenta
                   : hovered ? Colors.yellow : Colors.dark
            border.width: 1
            border.color: Colors.cyan
            opacity: explorePanel.canExplore ? 1.0 : 0.50
            GohuText {
                anchors.centerIn: parent
                text: explorePanel.pendingAction === "EXPLORE"
                      ? "SAVING..." : "EXPLORE HERE"
                font.pixelSize: 12
                color: startExploreButton.pressed ? Colors.black : Colors.cyan
            }
            MouseArea {
                id: startExploreMouse
                anchors.fill: parent
                enabled: explorePanel.canExplore
                hoverEnabled: enabled
                onClicked: {
                    explorePanel.pendingAction = "EXPLORE";
                    explorePanel.feedback = "SAVING // WAIT FOR CONFIRMATION";
                    const ok = explorePanel.registry.exploreHere(
                        exploreNameInput.text,
                        exploreLatitudeInput.text,
                        exploreLongitudeInput.text,
                        explorePanel.durationKey
                    );
                    if (!ok) {
                        explorePanel.pendingAction = "";
                        explorePanel.feedback = explorePanel.explainError(
                            explorePanel.registry.errorCode
                        );
                    }
                }
            }
        }

        Rectangle {
            id: returnHomeButton
            width: parent.width
            height: 36
            readonly property bool hovered: returnHomeMouse.containsMouse
            readonly property bool pressed: returnHomeMouse.pressed
            color: pressed ? Colors.magenta
                   : hovered ? Colors.yellow : Colors.dark
            border.width: 1
            border.color: Colors.orange
            opacity: explorePanel.canReturnHome ? 1.0 : 0.50
            GohuText {
                anchors.centerIn: parent
                text: explorePanel.pendingAction === "HOME"
                      ? "SAVING..." : "RETURN HOME"
                font.pixelSize: 11
                color: returnHomeButton.pressed ? Colors.black : Colors.orange
            }
            MouseArea {
                id: returnHomeMouse
                anchors.fill: parent
                enabled: explorePanel.canReturnHome
                hoverEnabled: enabled
                onClicked: {
                    explorePanel.pendingAction = "HOME";
                    explorePanel.feedback = "SAVING // WAIT FOR CONFIRMATION";
                    if (!explorePanel.registry.returnHome()) {
                        explorePanel.pendingAction = "";
                        explorePanel.feedback = explorePanel.explainError(
                            explorePanel.registry.errorCode
                        );
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: explorePanel.feedback ||
                  (explorePanel.registry && explorePanel.registry.errorCode
                   ? explorePanel.explainError(explorePanel.registry.errorCode)
                   : "EXPLORE AFFECTS SHARED CONTEXT ONLY // WIDGET ROUTING PENDING")
        }
    }
}
