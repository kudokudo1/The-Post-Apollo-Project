import QtQuick
import "../../components"

// Local structural labels, never verified company scopes or staff permissions.
// Functional units and geographic locations are separate categories.
Column {
    id: editor
    property var directoryStore: null
    property var removalController: null
    property var structureStore: null
    property string searchQuery: ""
    readonly property string normalizedSearch: searchQuery.trim().toLowerCase()
    function matchesUnit(unit) {
        if (normalizedSearch.length === 0) return true;
        const org = organizations.find(function(item) {
            return item.id === unit.orgId;
        });
        return (String(unit.name) + " " + String(unit.kind) + " " + String(unit.id)
                + " " + (org ? String(org.name) : ""))
                .toLowerCase().indexOf(normalizedSearch) !== -1;
    }
    property string selectedOrgId: ""
    property bool useSharedContext: false
    onSelectedOrgIdChanged: confirmationKey = ""
    property string selectedKind: "division"
    property bool showArchivedUnits: false
    property bool useSharedArchiveControl: false
    property bool useSharedRefreshControl: false
    onShowArchivedUnitsChanged: confirmationKey = ""
    property bool showArchivedOrganizations: false
    property string confirmationKey: ""

    readonly property bool ready: structureStore !== null
                                  && structureStore.state === "ready"
    readonly property var organizations:
        directoryStore && directoryStore.state === "ready"
        ? directoryStore.saved.organizations : []
    readonly property var selectedOrganization:
        organizations.find(function(org) {
            return org.id === editor.selectedOrgId;
        }) || null
    readonly property bool activeOrganization:
        selectedOrganization !== null && !selectedOrganization.archived
    readonly property var visibleOrganizations:
        organizations.filter(function(org) {
            return !org.archived || editor.showArchivedOrganizations;
        })
    readonly property var visibleUnits: structureStore && structureStore.saved
        ? structureStore.saved.units.filter(function(unit) {
            return unit.orgId === editor.selectedOrgId
                && (editor.normalizedSearch.length > 0
                    || unit.kind === editor.selectedKind)
                && (!unit.archived || editor.showArchivedUnits)
                && editor.matchesUnit(unit);
        }) : []
    readonly property var allUnits: structureStore && structureStore.saved
        ? structureStore.saved.units : []
    readonly property bool canEdit: ready && activeOrganization
    width: parent ? parent.width : 400
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

    spacing: 9

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.45
    }
    Text {
        width: parent.width
        text: "MY STRUCTURE // LOCAL ORGANIZATION UNITS"
        color: Colors.blue
        font.bold: true
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Create divisions, departments, locations and teams for each " +
              "organization. Functional groups and places remain separate. " +
              "These are labels only, not reporting lines, staffing or permissions."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !editor.ready
        text: !structureStore ? "STRUCTURE STORAGE // UNAVAILABLE"
              : structureStore.state === "error"
              ? "STRUCTURE STORAGE ERROR // " + structureStore.errorCode
              : "STRUCTURE STORAGE // " + structureStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    IdentityCenterLocalActionButton {
        role: "refresh"
        width: 149
        height: 28
        visible: !editor.useSharedRefreshControl
        label: "RELOAD STRUCTURE"
        labelPixelSize: 9
        interactive: structureStore !== null && structureStore.state !== "saving"
        onTriggered: structureStore.refresh()
    }
    Text {
        width: parent.width
        visible: !editor.useSharedContext
        text: "1 // ORGANIZATION"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 10
    }
    Flow {
        width: parent.width
        visible: !editor.useSharedContext
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: editor.visibleOrganizations
            delegate: IdentityCenterLocalActionButton {
                role: "navigate"
                required property var modelData
                width: Math.min(190, Math.max(110, editor.width - 12))
                height: 29
                label: modelData.name + (modelData.archived ? " [ARCHIVED]" : "")
                labelPixelSize: 9
                selected: editor.selectedOrgId === modelData.id
                onTriggered: {
                    editor.selectedOrgId = modelData.id;
                    editor.confirmationKey = "";
                }
            }
        }
    }
    IdentityCenterLocalActionButton {
        role: "manage"
        width: 170
        height: 27
        visible: !editor.useSharedContext
        label: editor.showArchivedOrganizations
               ? "HIDE ARCHIVED ORGS" : "SHOW ARCHIVED ORGS"
        labelPixelSize: 9
        onTriggered: editor.showArchivedOrganizations = !editor.showArchivedOrganizations
    }
    Text {
        width: parent.width
        visible: editor.organizations.length === 0
        text: "Add an organization in MY ORGANIZATIONS above first."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: editor.selectedOrganization !== null
                 && editor.selectedOrganization.archived
        text: "This organization is archived. Its units remain visible, " +
              "but editing and restoration require restoring the organization first."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }

    Text {
        width: parent.width
        text: "2 // UNIT CATEGORY"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 10
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: [
                {id:"division", label:"DIVISIONS"},
                {id:"department", label:"DEPARTMENTS"},
                {id:"location", label:"LOCATIONS"},
                {id:"team", label:"TEAMS"}
            ]
            delegate: IdentityCenterLocalActionButton {
                role: "navigate"
                required property var modelData
                width: 113
                height: 29
                label: modelData.label
                labelPixelSize: 9
                selected: editor.selectedKind === modelData.id
                onTriggered: {
                    editor.selectedKind = modelData.id;
                    editor.confirmationKey = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        text: editor.selectedKind === "location"
              ? "Locations are geographic labels. Existing branches remain " +
                "separate records; no branch is automatically moved or copied."
              : "Functional units can operate across different locations. " +
                "No automatic parent, manager or staffing relationship is created."
        font.pixelSize: 10
        color: Colors.white
        wrapMode: Text.WordWrap
    }
    Row {
        width: parent.width
        spacing: 6
        Rectangle {
            width: Math.max(100, parent.width - 148)
            height: 30
            color: newUnitName.activeFocus && newUnitName.enabled && !newUnitName.readOnly
                ? Qt.rgba(Colors.magenta.r, Colors.magenta.g, Colors.magenta.b, 0.12)
                : Colors.black
            border.color: newUnitName.activeFocus && newUnitName.enabled && !newUnitName.readOnly
                ? Colors.magenta : Colors.blue
            TextInput {
                id: newUnitName
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
                enabled: editor.canEdit
                verticalAlignment: TextInput.AlignVCenter
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 6
                text: "New " + editor.selectedKind
                color: Colors.cyan
                opacity: 0.65
                font.pixelSize: 10
                visible: newUnitName.text.length === 0
            }
        }
        IdentityCenterLocalActionButton {
            role: "add"
            width: 136
            height: 30
            label: "+ ADD UNIT"
            labelPixelSize: 9
            interactive: editor.canEdit && newUnitName.text.trim().length > 0
            onTriggered: {
                if (structureStore.createUnit(editor.selectedOrgId,
                                              editor.selectedKind, newUnitName.text))
                    newUnitName.text = "";
            }
        }
    }
    Row {
        spacing: 6
        visible: !editor.useSharedArchiveControl
        IdentityCenterLocalActionButton {
            role: "manage"
            width: 174
            height: 28
            label: editor.showArchivedUnits ? "HIDE ARCHIVED UNITS"
                                           : "SHOW ARCHIVED UNITS"
            labelPixelSize: 9
            onTriggered: {
                editor.showArchivedUnits = !editor.showArchivedUnits;
                editor.confirmationKey = "";
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedOrganization === null
        text: "Select an organization to view its structure."
        color: Colors.white
        font.pixelSize: 10
    }
    Text {
        width: parent.width
        visible: editor.selectedOrganization !== null
                 && editor.ready && editor.visibleUnits.length === 0
        text: "No " + editor.selectedKind + " records in this view."
        color: Colors.white
        font.pixelSize: 10
    }
    Text {
        width: parent.width
        visible: editor.removalController && (editor.removalController.lastTargetKind === "unit")
            && editor.removalController.resultText !== ""
        text: editor.removalController ? editor.removalController.resultText : ""
        color: editor.removalController && editor.removalController.resultKind === "error"
            ? Colors.red : Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: editor.visibleUnits
        delegate: Column {
            id: unitRow
            required property var modelData
            width: editor.width
            spacing: 5
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.28
            }
            Text {
                width: parent.width
                text: modelData.kind.toUpperCase() + " // " + modelData.id
                      + (modelData.archived ? " // ARCHIVED" : " // LOCAL ONLY")
                color: modelData.archived ? Colors.orange : Colors.cyan
                font.pixelSize: 10
                font.bold: true
                wrapMode: Text.WordWrap
            }
            Row {
                width: parent.width
                spacing: 6
                Rectangle {
                    width: Math.max(100, parent.width - 240)
                    height: 30
                    color: unitName.activeFocus && unitName.enabled && !unitName.readOnly
                        ? Qt.rgba(Colors.magenta.r, Colors.magenta.g, Colors.magenta.b, 0.12)
                        : Colors.black
                    border.color: unitName.activeFocus && unitName.enabled && !unitName.readOnly
                        ? Colors.magenta : Colors.blue
                    TextInput {
                        id: unitName
                        cursorDelegate: Rectangle {
                            width: 2
                            color: Colors.orange
                        }
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        anchors.fill: parent
                        anchors.margins: 6
                        text: unitRow.modelData.name
                        color: Colors.magenta
                        font.pixelSize: 10
                        maximumLength: 80
                        clip: true
                        readOnly: !editor.canEdit || unitRow.modelData.archived
                        verticalAlignment: TextInput.AlignVCenter
                    }
                }
                IdentityCenterLocalActionButton {
                    role: "manage"
                    width: 62
                    height: 30
                    label: "SAVE"
                    labelPixelSize: 9
                    interactive: editor.canEdit && !unitRow.modelData.archived
                    onTriggered: structureStore.renameUnit(
                        unitRow.modelData.id, unitName.text)
                }
                IdentityCenterLocalActionButton {
                    role: "manage"
                    width: 128
                    height: 30
                    label: unitRow.modelData.archived ? "RESTORE"
                           : editor.confirmationKey === "unit:" + unitRow.modelData.id
                           ? "CONFIRM ARCHIVE" : "ARCHIVE"
                    labelPixelSize: 8
                    interactive: editor.canEdit
                    onTriggered: {
                        if (unitRow.modelData.archived)
                            structureStore.restoreUnit(unitRow.modelData.id);
                        else if (editor.confirmationKey ===
                                 "unit:" + unitRow.modelData.id) {
                            structureStore.archiveUnit(unitRow.modelData.id);
                            editor.confirmationKey = "";
                        } else
                            editor.confirmationKey = "unit:" + unitRow.modelData.id;
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
                    onTriggered: editor.requestDirectDelete("unit", unitRow.modelData.id, unitRow.modelData.orgId, unitRow.modelData.name, structureStore.saved.revision, "UNIT // " + unitRow.modelData.name)
                }
            }
            Flow {
                width: parent.width
                height: childrenRect.height
                spacing: 6
                visible: editor.deletePending("unit", unitRow.modelData.id, unitRow.modelData.orgId, unitRow.modelData.name, structureStore.saved.revision, "UNIT // " + unitRow.modelData.name)
                IdentityCenterLocalActionButton {
                    role: "danger"
                    width: 163
                    height: 28
                    label: "CONFIRM DELETE"
                    labelPixelSize: 9
                    interactive: editor.removalController
                        && !editor.removalController.busy
                    onTriggered: editor.requestDirectDelete("unit", unitRow.modelData.id, unitRow.modelData.orgId, unitRow.modelData.name, structureStore.saved.revision, "UNIT // " + unitRow.modelData.name)
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
}
