import QtQuick
import "../../components"

// Manual names, not Identity Center grants or an authenticated company selector.
Column {
    id: editor
    property var directoryStore: null
    property string newKind: "llc"
    property bool showArchived: false
    property string confirmationKey: ""
    readonly property bool editable: directoryStore !== null && directoryStore.state === "ready"
    readonly property var organizations: directoryStore && directoryStore.saved
        ? directoryStore.saved.organizations : []
    spacing: 10

    Text {
        width: parent.width
        text: "MY ORGANIZATIONS // LOCAL DIRECTORY"
        color: Colors.cyan
        font.pixelSize: 12
        font.bold: true
    }
    Text {
        width: parent.width
        text: "Manually entered names only. No verified company membership, " +
              "login, record access or switching is granted by this directory."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !editor.editable
        text: directoryStore === null ? "LOCAL DIRECTORY // UNAVAILABLE"
              : directoryStore.state === "error"
              ? "LOCAL DIRECTORY ERROR // " + directoryStore.errorCode
              : "LOCAL DIRECTORY // " + directoryStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 140
        height: 28
        label: "RELOAD DIRECTORY"
        labelPixelSize: 9
        interactive: directoryStore !== null && directoryStore.state !== "saving"
        onTriggered: directoryStore.refresh()
    }

    Row {
        width: parent.width
        spacing: 6
        Rectangle {
            width: Math.max(100, parent.width - 148)
            height: 30
            color: Colors.black
            border.color: Colors.cyan
            TextInput {
                id: newOrgName
                anchors.fill: parent
                anchors.margins: 6
                color: Colors.white
                font.pixelSize: 11
                maximumLength: 80
                clip: true
                enabled: editor.editable
                verticalAlignment: TextInput.AlignVCenter
            }
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: "Organization name"
                color: Colors.cyan
                opacity: 0.65
                font.pixelSize: 10
                visible: newOrgName.text.length === 0
            }
        }
        ActionButton {
            width: 136
            height: 30
            label: "+ ORGANIZATION"
            labelPixelSize: 9
            interactive: editor.editable && newOrgName.text.trim().length > 0
            onTriggered: {
                if (directoryStore.addOrganization(newOrgName.text, editor.newKind))
                    newOrgName.text = "";
            }
        }
    }
    Row {
        spacing: 6
        Repeater {
            model: [{id:"llc",label:"LLC"},
                    {id:"nonprofit",label:"NONPROFIT"},
                    {id:"other",label:"OTHER"}]
            delegate: ActionButton {
                required property var modelData
                width: 108
                height: 28
                label: modelData.label
                labelPixelSize: 9
                selected: editor.newKind === modelData.id
                onTriggered: editor.newKind = modelData.id
            }
        }
    }
    ActionButton {
        width: 175
        height: 28
        label: editor.showArchived ? "HIDE ARCHIVED" : "SHOW ARCHIVED"
        labelPixelSize: 9
        onTriggered: {
            editor.showArchived = !editor.showArchived;
            editor.confirmationKey = "";
        }
    }
    Text {
        width: parent.width
        text: "No local organizations saved yet."
        visible: editor.editable && editor.organizations.length === 0
        color: Colors.white
        font.pixelSize: 10
    }
    Repeater {
        model: editor.organizations
        delegate: Column {
            id: orgRow
            required property var modelData
            width: editor.width
            spacing: 6
            visible: !modelData.archived || editor.showArchived
            height: visible ? implicitHeight : 0

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.35
            }
            Text {
                width: parent.width
                text: modelData.kind.toUpperCase() +
                      (modelData.archived ? " // ARCHIVED" : " // LOCAL ONLY")
                color: modelData.archived ? Colors.orange : Colors.cyan
                font.pixelSize: 10
                font.bold: true
            }
            Row {
                width: parent.width
                spacing: 6
                Rectangle {
                    width: Math.max(100, parent.width - 202)
                    height: 30
                    color: Colors.black
                    border.color: Colors.cyan
                    TextInput {
                        id: orgName
                        anchors.fill: parent
                        anchors.margins: 6
                        text: orgRow.modelData.name
                        color: Colors.white
                        font.pixelSize: 10
                        maximumLength: 80
                        clip: true
                        readOnly: !editor.editable || orgRow.modelData.archived
                        verticalAlignment: TextInput.AlignVCenter
                    }
                }
                ActionButton {
                    width: 62
                    height: 30
                    label: "SAVE"
                    labelPixelSize: 9
                    interactive: editor.editable && !orgRow.modelData.archived
                    onTriggered: directoryStore.renameOrganization(orgRow.modelData.id, orgName.text)
                }
                ActionButton {
                    width: 128
                    height: 30
                    label: orgRow.modelData.archived ? "RESTORE"
                           : editor.confirmationKey === "org:" + orgRow.modelData.id
                           ? "CONFIRM ARCHIVE" : "ARCHIVE"
                    labelPixelSize: 8
                    accentColor: Colors.orange
                    interactive: editor.editable
                    onTriggered: {
                        if (orgRow.modelData.archived)
                            directoryStore.restoreOrganization(orgRow.modelData.id);
                        else if (editor.confirmationKey === "org:" + orgRow.modelData.id) {
                            directoryStore.archiveOrganization(orgRow.modelData.id);
                            editor.confirmationKey = "";
                        } else
                            editor.confirmationKey = "org:" + orgRow.modelData.id;
                    }
                }
            }
            Column {
                width: parent.width - 16
                x: 16
                spacing: 5
                visible: !orgRow.modelData.archived
                height: visible ? implicitHeight : 0
                Repeater {
                    model: orgRow.modelData.branches
                    delegate: Row {
                        id: branchRow
                        required property var modelData
                        width: parent.width
                        spacing: 6
                        visible: !modelData.archived || editor.showArchived
                        height: visible ? 28 : 0
                        Rectangle {
                            width: Math.max(90, parent.width - 194)
                            height: 28
                            color: Colors.black
                            border.color: Colors.cyan
                            TextInput {
                                id: branchName
                                anchors.fill: parent
                                anchors.margins: 6
                                text: branchRow.modelData.name
                                color: Colors.white
                                font.pixelSize: 10
                                maximumLength: 80
                                clip: true
                                readOnly: !editor.editable || branchRow.modelData.archived
                                verticalAlignment: TextInput.AlignVCenter
                            }
                        }
                        ActionButton {
                            width: 58
                            height: 28
                            label: "SAVE"
                            labelPixelSize: 9
                            interactive: editor.editable && !branchRow.modelData.archived
                            onTriggered: directoryStore.renameBranch(
                                orgRow.modelData.id, branchRow.modelData.id, branchName.text)
                        }
                        ActionButton {
                            width: 124
                            height: 28
                            label: branchRow.modelData.archived ? "RESTORE"
                                   : editor.confirmationKey === "branch:" + branchRow.modelData.id
                                   ? "CONFIRM ARCHIVE" : "ARCHIVE"
                            labelPixelSize: 8
                            accentColor: Colors.orange
                            interactive: editor.editable
                            onTriggered: {
                                if (branchRow.modelData.archived)
                                    directoryStore.restoreBranch(orgRow.modelData.id, branchRow.modelData.id);
                                else if (editor.confirmationKey === "branch:" + branchRow.modelData.id) {
                                    directoryStore.archiveBranch(orgRow.modelData.id, branchRow.modelData.id);
                                    editor.confirmationKey = "";
                                } else
                                    editor.confirmationKey = "branch:" + branchRow.modelData.id;
                            }
                        }
                    }
                }
                Row {
                    width: parent.width
                    spacing: 6
                    Rectangle {
                        width: Math.max(100, parent.width - 148)
                        height: 28
                        color: Colors.black
                        border.color: Colors.cyan
                        TextInput {
                            id: newBranchName
                            anchors.fill: parent
                            anchors.margins: 6
                            color: Colors.white
                            font.pixelSize: 10
                            maximumLength: 80
                            clip: true
                            enabled: editor.editable
                            verticalAlignment: TextInput.AlignVCenter
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 6
                            text: "New branch / program"
                            visible: newBranchName.text.length === 0
                            color: Colors.cyan
                            opacity: 0.65
                            font.pixelSize: 9
                        }
                    }
                    ActionButton {
                        width: 136
                        height: 28
                        label: "+ BRANCH"
                        labelPixelSize: 9
                        interactive: editor.editable && newBranchName.text.trim().length > 0
                        onTriggered: {
                            if (directoryStore.addBranch(orgRow.modelData.id, newBranchName.text))
                                newBranchName.text = "";
                        }
                    }
                }
            }
        }
    }
}
