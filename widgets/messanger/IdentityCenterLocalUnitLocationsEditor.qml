import QtQuick
import "../../components"

// Local planning labels only: never tenant grants, employer relationships,
// manager reporting lines, location proof, or actual branch migrations.
Column {
    id: editor
    property var directoryStore: null
    property var structureStore: null
    property var linkStore: null
    property string selectedOrgId: ""
    property bool useSharedContext: false
    onSelectedOrgIdChanged: {
        selectedFunctionId = "";
        selectedLocationId = "";
        pendingRemovalId = "";
    }
    property string selectedFunctionId: ""
    property string selectedLocationId: ""
    property string pendingRemovalId: ""
    property bool showAllLinks: false
    spacing: 9

    readonly property bool sourcesReady:
        directoryStore !== null && directoryStore.state === "ready"
        && structureStore !== null && structureStore.state === "ready"
    readonly property bool readyToSave:
        sourcesReady && linkStore !== null && linkStore.state === "ready"
    readonly property var organizations:
        sourcesReady
        ? directoryStore.saved.organizations.filter(function(org) {
            return !org.archived;
        }) : []
    readonly property var allOrganizations:
        sourcesReady ? directoryStore.saved.organizations : []
    readonly property var units:
        sourcesReady ? structureStore.saved.units : []
    readonly property var functions:
        units.filter(function(unit) {
            return unit.orgId === editor.selectedOrgId && !unit.archived
                   && unit.kind !== "location";
        })
    readonly property var locations:
        units.filter(function(unit) {
            return unit.orgId === editor.selectedOrgId && !unit.archived
                   && unit.kind === "location";
        })
    readonly property bool selectedFunctionValid:
        functions.some(function(unit) {
            return unit.id === editor.selectedFunctionId;
        })
    readonly property bool selectedLocationValid:
        locations.some(function(unit) {
            return unit.id === editor.selectedLocationId;
        })
    readonly property var savedLinks:
        linkStore && linkStore.saved ? linkStore.saved.links : []
    readonly property bool canCreate:
        readyToSave && organizations.some(function(org) {
            return org.id === editor.selectedOrgId;
        }) && selectedFunctionValid && selectedLocationValid

    function resolveUnit(unitId) {
        return units.find(function(unit) { return unit.id === unitId; }) || null;
    }
    function resolveOrg(orgId) {
        return allOrganizations.find(function(org) {
            return org.id === orgId;
        }) || null;
    }
    function describeUnit(unitId) {
        const unit = resolveUnit(unitId);
        if (!unit)
            return "MISSING UNIT // " + unitId;
        return unit.kind.toUpperCase() + " // " + unit.name +
               (unit.archived ? " [ARCHIVED]" : "");
    }
    function describeOrg(orgId) {
        const org = resolveOrg(orgId);
        if (!org)
            return "MISSING ORGANIZATION // " + orgId;
        return org.name + (org.archived ? " [ARCHIVED]" : "");
    }
    function isCurrent(link) {
        const org = resolveOrg(link.orgId);
        const fn = resolveUnit(link.functionId);
        const location = resolveUnit(link.locationId);
        return !!(sourcesReady && org && !org.archived
            && fn && !fn.archived && fn.orgId === link.orgId
            && fn.kind !== "location"
            && location && !location.archived
            && location.orgId === link.orgId && location.kind === "location");
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.45
    }
    Text {
        width: parent.width
        text: "STRUCTURE LINKS // FUNCTIONS & LOCATIONS"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Show where a division, department or team operates. One " +
              "function can span locations, and one location can serve " +
              "multiple functions. These are local planning links only, " +
              "not reporting lines, branches, staff or access grants."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !editor.readyToSave
        text: !linkStore ? "UNIT LOCATION LINKS // NOT LOADED"
              : linkStore.state === "error"
              ? "UNIT LOCATION LINKS ERROR // " + linkStore.errorCode
              : "UNIT LOCATION LINKS // " + linkStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 135
        height: 28
        label: "RELOAD LINKS"
        labelPixelSize: 9
        interactive: linkStore !== null && linkStore.state !== "saving"
        onTriggered: linkStore.refresh()
    }

    Text {
        width: parent.width
        visible: !editor.useSharedContext
        text: "1 // SELECT ORGANIZATION"
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
            model: editor.organizations
            delegate: ActionButton {
                required property var modelData
                width: Math.min(190, Math.max(110, editor.width - 12))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedOrgId === modelData.id
                onTriggered: {
                    editor.selectedOrgId = modelData.id;
                    editor.selectedFunctionId = "";
                    editor.selectedLocationId = "";
                    editor.pendingRemovalId = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.organizations.length === 0
        text: "Create or restore an organization before adding links."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }

    Text {
        width: parent.width
        text: "2 // FUNCTIONAL UNIT"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 10
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: editor.functions
            delegate: ActionButton {
                required property var modelData
                width: Math.min(190, Math.max(110, editor.width - 12))
                height: 29
                label: modelData.kind.toUpperCase() + " // " + modelData.name
                labelPixelSize: 8
                selected: editor.selectedFunctionId === modelData.id
                onTriggered: editor.selectedFunctionId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedOrgId !== "" && editor.functions.length === 0
        text: "Add a division, department or team in MY STRUCTURE above."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "3 // LOCATION"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 10
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: editor.locations
            delegate: ActionButton {
                required property var modelData
                width: Math.min(190, Math.max(110, editor.width - 12))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedLocationId === modelData.id
                onTriggered: editor.selectedLocationId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedOrgId !== "" && editor.locations.length === 0
        text: "Add a location in MY STRUCTURE above. Existing branches " +
              "remain separate and are not automatically imported."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 189
        height: 30
        label: "+ LINK TO LOCATION"
        labelPixelSize: 9
        interactive: editor.canCreate
        onTriggered: {
            linkStore.linkToLocation(
                editor.selectedOrgId,
                editor.selectedFunctionId,
                editor.selectedLocationId);
        }
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.35
    }
    Text {
        width: parent.width
        text: "SAVED FUNCTION-LOCATION LINKS // " + editor.savedLinks.length
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 166
        height: 28
        label: editor.showAllLinks ? "SHOW SELECTED ONLY" : "SHOW ALL LINKS"
        labelPixelSize: 9
        onTriggered: {
            editor.showAllLinks = !editor.showAllLinks;
            editor.pendingRemovalId = "";
        }
    }
    Text {
        width: parent.width
        visible: editor.savedLinks.length === 0
        text: "No local function-location links saved yet."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: editor.savedLinks
        delegate: Column {
            id: linkRow
            required property var modelData
            width: editor.width
            spacing: 5
            visible: editor.showAllLinks ||
                     (editor.selectedOrgId !== ""
                      && editor.selectedOrgId === modelData.orgId)
            height: visible ? implicitHeight : 0
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.3
            }
            Text {
                width: parent.width
                text: editor.describeOrg(linkRow.modelData.orgId) + " // " +
                      editor.describeUnit(linkRow.modelData.functionId) +
                      " → " + editor.describeUnit(linkRow.modelData.locationId)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: editor.isCurrent(linkRow.modelData)
                      ? "LOCAL PLANNING LINK // NOT AN ACCESS GRANT"
                      : "STALE OR UNAVAILABLE // NOT AN ACCESS GRANT"
                color: editor.isCurrent(linkRow.modelData)
                       ? Colors.cyan : Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: 160
                height: 28
                label: editor.pendingRemovalId === linkRow.modelData.id
                       ? "CONFIRM UNLINK" : "UNLINK LOCATION"
                labelPixelSize: 9
                accentColor: Colors.orange
                interactive: linkStore !== null && linkStore.state === "ready"
                onTriggered: {
                    if (editor.pendingRemovalId === linkRow.modelData.id) {
                        linkStore.unlinkFromLocation(linkRow.modelData.id);
                        editor.pendingRemovalId = "";
                    } else {
                        editor.pendingRemovalId = linkRow.modelData.id;
                    }
                }
            }
        }
    }
}
