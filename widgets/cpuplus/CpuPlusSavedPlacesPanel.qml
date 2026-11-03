import QtQuick
import "../../components"

// CPU++ M3 bookmarks. All persistence and validation belong to PlaceRegistry.
// Saving or exploring a bookmark never changes the persistent Home point.
Item {
    id: savedPanel
    property var registry: null
    property string durationKey: "2H"
    property string pendingAction: ""
    property string feedback: ""
    property int confirmRemoveId: 0

    readonly property var bookmarks:
        registry && Array.isArray(registry.savedPlaces)
        ? registry.savedPlaces : []
    readonly property var selectedPlace:
        registry ? registry.effectivePlace : null
    readonly property bool canSave:
        registry && registry.canSaveCurrentPlace === true
    readonly property bool canUse:
        registry && registry.canChangeExplore === true
    readonly property bool canRemove:
        registry && registry.canSaveHome === true

    implicitHeight: bookmarkContent.implicitHeight

    function describeError(code) {
        switch (String(code || "")) {
        case "SAVED_PLACE_DUPLICATE": return "THIS PLACE IS ALREADY SAVED";
        case "SAVED_PLACES_FULL": return "SAVED PLACES FULL // LIMIT 32";
        case "SAVED_PLACE_NOT_FOUND": return "SAVED PLACE NO LONGER EXISTS";
        case "SAVED_PLACE_INVALID": return "INVALID PLACE // NOT SAVED";
        case "NO_PLACE_TO_SAVE": return "SET HOME BEFORE SAVING A PLACE";
        case "STORAGE_NOT_READY": return "PLACE STORAGE NOT READY";
        case "FILE_SAVE_FAILED": return "SAVE FAILED // OLD DATA PRESERVED";
        case "HOME_NOT_SET": return "SET HOME BEFORE EXPLORING";
        case "EXPLORE_DURATION_INVALID": return "INVALID EXPLORATION DURATION";
        default: return code || "SAVED PLACE OPERATION FAILED";
        }
    }

    function submit(action, methodResult) {
        if (!methodResult) {
            pendingAction = "";
            feedback = describeError(registry ? registry.errorCode : "");
            return;
        }
        // onSaved is the only confirmation that data reached storage.
        feedback = action + " // SAVING";
    }

    Connections {
        target: savedPanel.registry
        function onStorageStateChanged() {
            if (!savedPanel.pendingAction)
                return;
            const state = String(savedPanel.registry.storageState || "");
            if (state === "ready") {
                savedPanel.feedback = savedPanel.pendingAction + " // SAVED";
                savedPanel.pendingAction = "";
                savedPanel.confirmRemoveId = 0;
            } else if (state === "error" || state === "unsupported") {
                savedPanel.feedback = savedPanel.describeError(
                    savedPanel.registry.errorCode
                );
                savedPanel.pendingAction = "";
            }
        }
    }

    Column {
        id: bookmarkContent
        width: parent.width
        spacing: 9

        GohuText {
            text: "★  SAVED PLACES // " + savedPanel.bookmarks.length + " / 32"
            color: Colors.magenta
            font.pixelSize: 11
        }

        QuietText {
            width: parent.width
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            text: "BOOKMARK THE CURRENT HOME OR EXPLORE POINT. RECALL USING THE EXPLORE DURATION SELECTED ABOVE."
        }

        Rectangle {
            id: bookmarkCurrentButton
            width: parent.width
            height: 37
            readonly property bool hovered: bookmarkCurrentMouse.containsMouse
            readonly property bool pressed: bookmarkCurrentMouse.pressed
            color: pressed ? Colors.magenta
                   : hovered ? Colors.yellow : Colors.dark
            border.width: 1
            border.color: Colors.magenta
            opacity: savedPanel.canSave ? 1.0 : 0.50

            GohuText {
                anchors.centerIn: parent
                text: savedPanel.pendingAction === "BOOKMARK"
                      ? "SAVING..." : "SAVE CURRENT PLACE ★"
                color: bookmarkCurrentButton.pressed
                       ? Colors.black : Colors.magenta
                font.pixelSize: 11
            }

            MouseArea {
                id: bookmarkCurrentMouse
                anchors.fill: parent
                hoverEnabled: enabled
                enabled: savedPanel.canSave
                onClicked: {
                    savedPanel.confirmRemoveId = 0;
                    savedPanel.pendingAction = "BOOKMARK";
                    savedPanel.feedback = "BOOKMARK // SAVING";
                    const ok = savedPanel.registry.saveCurrentPlace();
                    if (!ok) {
                        savedPanel.pendingAction = "";
                        savedPanel.feedback = savedPanel.describeError(
                            savedPanel.registry.errorCode
                        );
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: savedPanel.selectedPlace
                  ? "CURRENT // " + savedPanel.selectedPlace.label
                  : "CURRENT // HOME NOT SET"
        }

        GohuText {
            width: parent.width
            font.pixelSize: 10
            color: Colors.cyan
            text: savedPanel.bookmarks.length
                  ? "RECALL // EXPLORE" : "NO SAVED PLACES YET"
        }

        Repeater {
            model: savedPanel.bookmarks

            delegate: Rectangle {
                id: bookmarkRow
                required property var modelData
                width: bookmarkContent.width
                height: 99
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        elide: Text.ElideRight
                        text: bookmarkRow.modelData.place.label
                        color: Colors.white
                        font.pixelSize: 11
                    }

                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: Number(bookmarkRow.modelData.place.latitude).toFixed(4)
                              + "°, "
                              + Number(bookmarkRow.modelData.place.longitude).toFixed(4)
                              + "°"
                    }

                    Row {
                        width: parent.width
                        height: 31
                        spacing: 6

                        Rectangle {
                            id: recallButton
                            width: (parent.width - 6) / 2
                            height: 30
                            color: recallMouse.pressed ? Colors.magenta
                                   : recallMouse.containsMouse
                                   ? Colors.yellow : Colors.dark
                            border.width: 1
                            border.color: Colors.cyan
                            opacity: savedPanel.canUse ? 1.0 : 0.50

                            GohuText {
                                anchors.centerIn: parent
                                font.pixelSize: 10
                                color: recallMouse.pressed
                                       ? Colors.black : Colors.cyan
                                text: "EXPLORE"
                            }
                            MouseArea {
                                id: recallMouse
                                anchors.fill: parent
                                enabled: savedPanel.canUse
                                hoverEnabled: enabled
                                onClicked: {
                                    savedPanel.confirmRemoveId = 0;
                                    savedPanel.pendingAction = "EXPLORE";
                                    savedPanel.feedback = "EXPLORE // SAVING";
                                    const ok = savedPanel.registry.exploreSavedPlace(
                                        bookmarkRow.modelData.id, savedPanel.durationKey
                                    );
                                    if (!ok) {
                                        savedPanel.pendingAction = "";
                                        savedPanel.feedback = savedPanel.describeError(
                                            savedPanel.registry.errorCode
                                        );
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: removeButton
                            width: (parent.width - 6) / 2
                            height: 30
                            color: removeMouse.pressed ? Colors.magenta
                                   : removeMouse.containsMouse
                                   ? Colors.yellow : Colors.dark
                            border.width: 1
                            border.color: savedPanel.confirmRemoveId
                                          === bookmarkRow.modelData.id
                                          ? Colors.magenta : Colors.orange
                            opacity: savedPanel.canRemove ? 1.0 : 0.50

                            GohuText {
                                anchors.centerIn: parent
                                font.pixelSize: 9
                                color: removeMouse.pressed
                                       ? Colors.black : Colors.orange
                                text: savedPanel.confirmRemoveId
                                      === bookmarkRow.modelData.id
                                      ? "CONFIRM REMOVE" : "REMOVE"
                            }
                            MouseArea {
                                id: removeMouse
                                anchors.fill: parent
                                enabled: savedPanel.canRemove
                                hoverEnabled: enabled
                                onClicked: {
                                    const id = bookmarkRow.modelData.id;
                                    if (savedPanel.confirmRemoveId !== id) {
                                        savedPanel.confirmRemoveId = id;
                                        savedPanel.feedback = "CLICK CONFIRM REMOVE AGAIN";
                                        return;
                                    }
                                    savedPanel.pendingAction = "REMOVE";
                                    savedPanel.feedback = "REMOVE // SAVING";
                                    const ok = savedPanel.registry.removeSavedPlace(id);
                                    if (!ok) {
                                        savedPanel.pendingAction = "";
                                        savedPanel.feedback = savedPanel.describeError(
                                            savedPanel.registry.errorCode
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: savedPanel.feedback
                  || (savedPanel.registry && savedPanel.registry.errorCode
                      ? savedPanel.describeError(savedPanel.registry.errorCode)
                      : "REMOVING A BOOKMARK DOES NOT CHANGE HOME OR AN ACTIVE EXPLORE LOCATION.")
        }
    }
}
