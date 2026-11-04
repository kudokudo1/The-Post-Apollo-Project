import QtQuick
import "../../components"

// Manual names, not Identity Center grants or an authenticated company selector.
Column {
    id: editor
    property var directoryStore: null
    property var removalController: null
    // Optional focus supplied by the one-page editing selector.
    // Empty focus retains the accepted all-organizations editor.
    property string focusedOrganizationId: ""
    property string searchQuery: ""
    readonly property string normalizedSearch: searchQuery.trim().toLowerCase()
    function matchesOrganization(org) {
        if (normalizedSearch.length === 0) return true;
        if ((String(org.name) + " " + String(org.kind) + " " + String(org.id))
                .toLowerCase().indexOf(normalizedSearch) !== -1) return true;
        return Array.isArray(org.branches) && org.branches.some(function(branch) {
            return (String(branch.name) + " " + String(branch.id))
                .toLowerCase().indexOf(editor.normalizedSearch) !== -1;
        });
    }
    function matchesBranch(org, branch) {
        if (normalizedSearch.length === 0) return true;
        return (String(org.name) + " " + String(org.kind) + " "
                + String(branch.name) + " " + String(branch.id))
                .toLowerCase().indexOf(normalizedSearch) !== -1;
    }
    property string newKind: "llc"
    property bool showArchived: false
    property bool useSharedArchiveControl: false
    property bool useSharedRefreshControl: false
    onShowArchivedChanged: confirmationKey = ""
    property string confirmationKey: ""
    readonly property bool editable: directoryStore !== null && directoryStore.state === "ready"
    readonly property var organizations: directoryStore && directoryStore.saved
        ? directoryStore.saved.organizations : []
    // Both active and archived Delete buttons use the same guarded writer.
    function deleteTarget(kind, id, orgId, name, revision, label) {
        return {kind:kind, id:id, orgId:orgId, name:name,
                revision:revision, label:label};
    }
    function requestDirectDelete(kind, id, orgId, name, revision, label) {
        return removalController && removalController.requestRemove(
            deleteTarget(kind, id, orgId, name, revision, label));
    }
    function deletePending(kind, id, orgId, name, revision, label) {
        return removalController && removalController.isConfirmed(
            deleteTarget(kind, id, orgId, name, revision, label));
    }
    function cancelDirectDelete() {
        if (removalController) removalController.cancelDelete();
    }

    spacing: 10

    Text {
        width: parent.width
        text: "MY ORGANIZATIONS // LOCAL DIRECTORY"
        color: Colors.orange
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
    IdentityCenterLocalActionButton {
        role: "refresh"
        width: 140
        height: 28
        visible: !editor.useSharedRefreshControl
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
            color: newOrgName.activeFocus && newOrgName.enabled && !newOrgName.readOnly
                ? Qt.rgba(Colors.magenta.r, Colors.magenta.g, Colors.magenta.b, 0.12)
                : Colors.black
            border.color: newOrgName.activeFocus && newOrgName.enabled && !newOrgName.readOnly
                ? Colors.magenta : Colors.blue
            TextInput {
                id: newOrgName
                cursorDelegate: Rectangle {
                    width: 2
                    color: Colors.orange
                }
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                anchors.fill: parent
                anchors.margins: 6
                color: Colors.magenta
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
        IdentityCenterLocalActionButton {
            role: "add"
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
            delegate: IdentityCenterLocalActionButton {
                role: "navigate"
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
    IdentityCenterLocalActionButton {
        role: "manage"
        width: 175
        height: 28
        visible: !editor.useSharedArchiveControl
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
    Text {
        width: parent.width
        visible: editor.removalController && (editor.removalController.lastTargetKind === "organization"
            || editor.removalController.lastTargetKind === "branch")
            && editor.removalController.resultText !== ""
        text: editor.removalController ? editor.removalController.resultText : ""
        color: editor.removalController && editor.removalController.resultKind === "error"
            ? Colors.red : Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: editor.organizations
        delegate: Column {
            id: orgRow
            required property var modelData
            width: editor.width
            spacing: 6
            visible: (!modelData.archived || editor.showArchived)
                     && (editor.focusedOrganizationId === ""
                         || editor.focusedOrganizationId === modelData.id)
                     && editor.matchesOrganization(modelData)
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
                    width: Math.max(100, parent.width - 240)
                    height: 30
                    color: orgName.activeFocus && orgName.enabled && !orgName.readOnly
                        ? Qt.rgba(Colors.magenta.r, Colors.magenta.g, Colors.magenta.b, 0.12)
                        : Colors.black
                    border.color: orgName.activeFocus && orgName.enabled && !orgName.readOnly
                        ? Colors.magenta : Colors.blue
                    TextInput {
                        id: orgName
                        cursorDelegate: Rectangle {
                            width: 2
                            color: Colors.orange
                        }
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        anchors.fill: parent
                        anchors.margins: 6
                        text: orgRow.modelData.name
                        color: Colors.magenta
                        font.pixelSize: 10
                        maximumLength: 80
                        clip: true
                        readOnly: !editor.editable || orgRow.modelData.archived
                        verticalAlignment: TextInput.AlignVCenter
                    }
                }
                IdentityCenterLocalActionButton {
                    role: "manage"
                    width: 62
                    height: 30
                    label: "SAVE"
                    labelPixelSize: 9
                    interactive: editor.editable && !orgRow.modelData.archived
                    onTriggered: directoryStore.renameOrganization(orgRow.modelData.id, orgName.text)
                }
                IdentityCenterLocalActionButton {
                    role: "manage"
                    width: 128
                    height: 30
                    label: orgRow.modelData.archived ? "RESTORE"
                           : editor.confirmationKey === "org:" + orgRow.modelData.id
                           ? "CONFIRM ARCHIVE" : "ARCHIVE"
                    labelPixelSize: 8
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
                IdentityCenterLocalActionButton {
                    role: "danger"
                    objectName: "orgDirectDeleteX"
                    width: 32
                    height: 30
                    label: "X"
                    labelPixelSize: 10
                    interactive: editor.removalController
                        && editor.removalController.storesReady
                        && !editor.removalController.busy
                    onTriggered: editor.requestDirectDelete("organization", orgRow.modelData.id, orgRow.modelData.id, orgRow.modelData.name, directoryStore.saved.revision, "COMPANY // " + orgRow.modelData.name)
                }
            }
            Flow {
                width: parent.width
                height: childrenRect.height
                spacing: 6
                visible: editor.deletePending("organization", orgRow.modelData.id, orgRow.modelData.id, orgRow.modelData.name, directoryStore.saved.revision, "COMPANY // " + orgRow.modelData.name)
                IdentityCenterLocalActionButton {
                    role: "danger"
                    width: 163
                    height: 28
                    label: "CONFIRM DELETE"
                    labelPixelSize: 9
                    interactive: editor.removalController
                        && !editor.removalController.busy
                    onTriggered: editor.requestDirectDelete("organization", orgRow.modelData.id, orgRow.modelData.id, orgRow.modelData.name, directoryStore.saved.revision, "COMPANY // " + orgRow.modelData.name)
                }
                IdentityCenterLocalActionButton {
                    role: "navigate"
                    width: 88
                    height: 28
                    label: "CANCEL"
                    labelPixelSize: 9
                    onTriggered: editor.cancelDirectDelete()
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
                    delegate: Column {
                        id: branchRow
                        required property var modelData
                        width: parent.width
                        spacing: 6
                        visible: (!modelData.archived || editor.showArchived)
                                 && editor.matchesBranch(orgRow.modelData, modelData)
                        height: visible ? implicitHeight : 0
                        Row {
                            width: parent.width
                            height: 28
                            spacing: 6
                            Rectangle {
                            width: Math.max(90, parent.width - 232)
                            height: 28
                            color: branchName.activeFocus && branchName.enabled && !branchName.readOnly
                                ? Qt.rgba(Colors.magenta.r, Colors.magenta.g, Colors.magenta.b, 0.12)
                                : Colors.black
                            border.color: branchName.activeFocus && branchName.enabled && !branchName.readOnly
                                ? Colors.magenta : Colors.blue
                            TextInput {
                                id: branchName
                                cursorDelegate: Rectangle {
                                    width: 2
                                    color: Colors.orange
                                }
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black
                                anchors.fill: parent
                                anchors.margins: 6
                                text: branchRow.modelData.name
                                color: Colors.magenta
                                font.pixelSize: 10
                                maximumLength: 80
                                clip: true
                                readOnly: !editor.editable || branchRow.modelData.archived
                                verticalAlignment: TextInput.AlignVCenter
                            }
                        }
                        IdentityCenterLocalActionButton {
                            role: "manage"
                            width: 58
                            height: 28
                            label: "SAVE"
                            labelPixelSize: 9
                            interactive: editor.editable && !branchRow.modelData.archived
                            onTriggered: directoryStore.renameBranch(
                                orgRow.modelData.id, branchRow.modelData.id, branchName.text)
                        }
                        IdentityCenterLocalActionButton {
                            role: "manage"
                            width: 124
                            height: 28
                            label: branchRow.modelData.archived ? "RESTORE"
                                   : editor.confirmationKey === "branch:" + branchRow.modelData.id
                                   ? "CONFIRM ARCHIVE" : "ARCHIVE"
                            labelPixelSize: 8
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
                            IdentityCenterLocalActionButton {
                                role: "danger"
                                objectName: "orgDirectDeleteX"
                                width: 32
                                height: 28
                                label: "X"
                                labelPixelSize: 10
                                interactive: editor.removalController
                                    && editor.removalController.storesReady
                                    && !editor.removalController.busy
                                onTriggered: editor.requestDirectDelete("branch", branchRow.modelData.id, orgRow.modelData.id, branchRow.modelData.name, directoryStore.saved.revision, "BRANCH // " + branchRow.modelData.name)
                            }
                        }
                        Flow {
                            width: parent.width
                            height: childrenRect.height
                            spacing: 6
                            visible: editor.deletePending("branch", branchRow.modelData.id, orgRow.modelData.id, branchRow.modelData.name, directoryStore.saved.revision, "BRANCH // " + branchRow.modelData.name)
                            IdentityCenterLocalActionButton {
                                role: "danger"
                                width: 163
                                height: 28
                                label: "CONFIRM DELETE"
                                labelPixelSize: 9
                                interactive: editor.removalController
                                    && !editor.removalController.busy
                                onTriggered: editor.requestDirectDelete("branch", branchRow.modelData.id, orgRow.modelData.id, branchRow.modelData.name, directoryStore.saved.revision, "BRANCH // " + branchRow.modelData.name)
                            }
                            IdentityCenterLocalActionButton {
                                role: "navigate"
                                width: 88
                                height: 28
                                label: "CANCEL"
                                labelPixelSize: 9
                                onTriggered: editor.cancelDirectDelete()
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
                        color: newBranchName.activeFocus && newBranchName.enabled && !newBranchName.readOnly
                            ? Qt.rgba(Colors.magenta.r, Colors.magenta.g, Colors.magenta.b, 0.12)
                            : Colors.black
                        border.color: newBranchName.activeFocus && newBranchName.enabled && !newBranchName.readOnly
                            ? Colors.magenta : Colors.blue
                        TextInput {
                            id: newBranchName
                            cursorDelegate: Rectangle {
                                width: 2
                                color: Colors.orange
                            }
                            selectionColor: Colors.magenta
                            selectedTextColor: Colors.black
                            anchors.fill: parent
                            anchors.margins: 6
                            color: Colors.magenta
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
                    IdentityCenterLocalActionButton {
                        role: "add"
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
