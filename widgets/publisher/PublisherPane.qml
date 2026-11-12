import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services.publisher
import "../../components"

// P1 local-only Publisher. No network, identity grant, upload or scheduler.
// This lives in SocialW's existing content bay and creates no window.
Rectangle {
    id: publisher
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    clip: true

    property string activeSection: "compose"
    property string selectedDraftId: ""
    property string feedback: "LOCAL DRAFTS ONLY // NO PUBLICATION"
    readonly property var storeSnapshot: PublisherDraftStore.snapshot
    readonly property var sections: [
        {id:"compose", label:"COMPOSE"},
        {id:"library", label:"LIBRARY"},
        {id:"calendar", label:"CALENDAR"},
        {id:"queue", label:"QUEUE"},
        {id:"history", label:"HISTORY"}
    ]

    function newDraft() {
        selectedDraftId = "";
        draftTitle.text = "";
        draftBody.text = "";
        activeSection = "compose";
        feedback = "NEW LOCAL DRAFT // NOT YET SAVED";
    }
    function openDraft(item) {
        if (!item || typeof item.id !== "string") return;
        selectedDraftId = item.id;
        draftTitle.text = item.title;
        draftBody.text = item.body;
        activeSection = "compose";
        feedback = "EDIT LOCAL " + item.id + " // SAVE TO CONFIRM";
    }
    function saveEditor() {
        if (PublisherDraftStore.saveDraft(selectedDraftId,
                                         draftTitle.text, draftBody.text))
            feedback = "SAVE REQUESTED // WAIT FOR LOCAL CONFIRMATION";
        else
            feedback = "SAVE REFUSED // " + PublisherDraftStore.actionError;
    }

    Connections {
        target: PublisherDraftStore
        function onSavedSuccessfully(draftId) {
            // A FileView onSaved event, NOT an external publication receipt.
            publisher.selectedDraftId = String(draftId);
            publisher.feedback = "LOCAL SAVE ACKNOWLEDGED // " + draftId;
        }
        function onStorageStateChanged() {
            if (PublisherDraftStore.storageState === "error"
                    || PublisherDraftStore.storageState === "unsupported")
                publisher.feedback = "LOCAL STORAGE BLOCKED // "
                    + PublisherDraftStore.errorCode;
        }
    }

    Column {
        id: body
        anchors.fill: parent
        anchors.margins: 12
        spacing: 9

        Text {
            width: parent.width
            height: 25
            text: "SOCIAL // PUBLISHER"
            color: Colors.white
            font.pixelSize: 17
            font.bold: true
            verticalAlignment: Text.AlignVCenter
        }
        Row {
            id: sectionRail
            width: parent.width
            height: 38
            spacing: 5
            Repeater {
                model: publisher.sections
                ActionButton {
                    required property var modelData
                    width: (sectionRail.width - 4 * sectionRail.spacing) / 5
                    height: 36
                    label: modelData.label
                    labelPixelSize: 11
                    accentColor: Colors.cyan
                    selected: publisher.activeSection === modelData.id
                    onTriggered: publisher.activeSection = modelData.id
                }
            }
        }
        Rectangle {
            id: workspace
            width: parent.width
            height: Math.max(50, parent.height - 126)
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Item {
                id: compose
                anchors.fill: parent
                anchors.margins: 10
                visible: publisher.activeSection === "compose"

                Column {
                    anchors.fill: parent
                    spacing: 8
                    Text {
                        width: parent.width
                        height: 20
                        color: Colors.cyan
                        text: publisher.selectedDraftId !== ""
                              ? "EDIT // " + publisher.selectedDraftId
                              : "NEW TEXT DRAFT"
                        font.pixelSize: 12
                    }
                    TextField {
                        id: draftTitle
                        width: parent.width
                        height: 36
                        placeholderText: "TITLE (REQUIRED)"
                        placeholderTextColor: Colors.cyan
                        color: Colors.white
                        selectByMouse: true
                        background: Rectangle {
                            color: Colors.black
                            border.width: 1
                            border.color: draftTitle.activeFocus
                                          ? Colors.magenta : Colors.cyan
                        }
                    }
                    ScrollView {
                        id: draftScroll
                        width: parent.width
                        height: Math.max(80, compose.height - 20 - 36 - 80)
                        clip: true
                        TextArea {
                            id: draftBody
                            placeholderText: "WRITE YOUR POST HERE. NO PLATFORM IS CONNECTED."
                            placeholderTextColor: Colors.cyan
                            wrapMode: TextEdit.Wrap
                            color: Colors.white
                            selectByMouse: true
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: draftBody.activeFocus
                                              ? Colors.magenta : Colors.cyan
                            }
                        }
                    }
                    Row {
                        width: parent.width
                        height: 36
                        spacing: 8
                        ActionButton {
                            width: (parent.width - parent.spacing) / 2
                            height: 36
                            label: "NEW"
                            accentColor: Colors.cyan
                            onTriggered: publisher.newDraft()
                        }
                        ActionButton {
                            width: (parent.width - parent.spacing) / 2
                            height: 36
                            label: PublisherDraftStore.storageState === "saving"
                                   ? "SAVING" : "SAVE DRAFT"
                            accentColor: Colors.magenta
                            available: publisher.storeSnapshot.writable
                            onTriggered: publisher.saveEditor()
                        }
                    }
                }
            }

            Item {
                id: library
                anchors.fill: parent
                anchors.margins: 10
                visible: publisher.activeSection === "library"
                Column {
                    anchors.fill: parent
                    spacing: 7
                    Text {
                        width: parent.width
                        height: 22
                        text: "LOCAL DRAFTS // "
                              + publisher.storeSnapshot.drafts.length
                        color: Colors.cyan
                        font.pixelSize: 12
                    }
                    Flickable {
                        id: draftList
                        width: parent.width
                        height: Math.max(1, parent.height - 70)
                        clip: true
                        contentWidth: width
                        contentHeight: draftColumn.height
                        boundsBehavior: Flickable.StopAtBounds
                        Column {
                            id: draftColumn
                            width: draftList.width
                            spacing: 6
                            Repeater {
                                model: publisher.storeSnapshot.drafts
                                ActionButton {
                                    required property var modelData
                                    width: draftColumn.width
                                    height: 40
                                    label: modelData.id + " // " + modelData.title
                                    labelPixelSize: 12
                                    accentColor: Colors.cyan
                                    onTriggered: publisher.openDraft(modelData)
                                }
                            }
                        }
                    }
                    ActionButton {
                        width: parent.width
                        height: 34
                        label: "RELOAD LOCAL FILE"
                        accentColor: Colors.cyan
                        available: PublisherDraftStore.storageState !== "saving"
                        onTriggered: {
                            if (!PublisherDraftStore.reloadFromDisk())
                                publisher.feedback = "RELOAD REFUSED // SAVE IN PROGRESS";
                            else
                                publisher.feedback = "RELOADING LOCAL DRAFTS";
                        }
                    }
                }
            }

            Column {
                anchors.centerIn: parent
                width: parent.width - 50
                spacing: 12
                visible: publisher.activeSection === "calendar"
                         || publisher.activeSection === "queue"
                         || publisher.activeSection === "history"
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    color: Colors.yellow
                    font.pixelSize: 18
                    text: publisher.activeSection.toUpperCase()
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: Colors.white
                    font.pixelSize: 12
                    text: "P1 FUTURE STEP // NOT ENABLED.\n"
                          + "NO SCHEDULE, QUEUE, UPLOAD OR POSTING AUTHORITY."
                }
            }
        }
        Text {
            width: parent.width
            height: 22
            verticalAlignment: Text.AlignVCenter
            color: publisher.storeSnapshot.state === "error"
                   || publisher.storeSnapshot.state === "unsupported"
                   ? Colors.orange : Colors.cyan
            font.pixelSize: 10
            elide: Text.ElideRight
            text: publisher.feedback + " // " + publisher.storeSnapshot.state.toUpperCase()
        }
    }
}
