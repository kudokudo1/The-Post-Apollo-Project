import QtQuick
import "../../components"

// Manual local functional reporting/coordination map, not a workforce graph,
// legal authority, manager assignment, Identity Center membership or grant.
Column {
    id: editor
    property var directoryStore: null
    property var structureStore: null
    property var reportingStore: null
    property string selectedOrgId: ""
    property bool useSharedContext: false
    onSelectedOrgIdChanged: {
        selectedParentId = "";
        selectedChildId = "";
        confirmRemovalId = "";
    }
    property string selectedParentId: ""
    property string selectedChildId: ""
    property string confirmRemovalId: ""
    property bool showAllLinks: false
    spacing: 9

    readonly property bool inputsReady:
        directoryStore !== null && directoryStore.state === "ready"
        && structureStore !== null && structureStore.state === "ready"
    readonly property bool ready:
        inputsReady && reportingStore !== null && reportingStore.state === "ready"
    readonly property var allOrganizations:
        inputsReady ? directoryStore.saved.organizations : []
    readonly property var organizations:
        allOrganizations.filter(function(o) { return !o.archived; })
    readonly property var allUnits:
        inputsReady ? structureStore.saved.units : []
    readonly property var functions:
        allUnits.filter(function(unit) {
            return !unit.archived && unit.orgId === editor.selectedOrgId
                   && unit.kind !== "location";
        })
    readonly property var links:
        reportingStore && reportingStore.saved ? reportingStore.saved.links : []
    readonly property bool parentValid:
        functions.some(function(unit) { return unit.id === editor.selectedParentId; })
    readonly property bool childValid:
        functions.some(function(unit) { return unit.id === editor.selectedChildId; })
    readonly property bool selectionValid:
        ready && organizations.some(function(org) { return org.id === selectedOrgId; })
        && parentValid && childValid && selectedParentId !== selectedChildId
    readonly property bool duplicateSelected:
        links.some(function(link) {
            return link.orgId === editor.selectedOrgId
                   && link.parentId === editor.selectedParentId
                   && link.childId === editor.selectedChildId;
        })

    function resolveOrg(orgId) {
        return allOrganizations.find(function(o) { return o.id === orgId; }) || null;
    }
    function resolveUnit(unitId) {
        return allUnits.find(function(unit) { return unit.id === unitId; }) || null;
    }
    function showOrg(orgId) {
        const org = resolveOrg(orgId);
        return org ? org.name + (org.archived ? " [ARCHIVED]" : "")
                   : "MISSING ORG // " + orgId;
    }
    function showUnit(unitId) {
        const unit = resolveUnit(unitId);
        return unit ? unit.kind.toUpperCase() + " // " + unit.name
                    + (unit.archived ? " [ARCHIVED]" : "")
                    : "MISSING UNIT // " + unitId;
    }
    function validLink(link) {
        if (!inputsReady) return false;
        const org = resolveOrg(link.orgId);
        const parentUnit = resolveUnit(link.parentId);
        const childUnit = resolveUnit(link.childId);
        return !!(org && !org.archived
            && parentUnit && !parentUnit.archived
            && parentUnit.orgId === link.orgId
            && parentUnit.kind !== "location"
            && childUnit && !childUnit.archived
            && childUnit.orgId === link.orgId
            && childUnit.kind !== "location");
    }
    function wouldCycle() {
        if (!selectionValid)
            return false;
        // Follow child→descendant links from selected child. Creating
        // parent→child would cycle if the child reaches the chosen parent.
        const visited = {};
        const pending = [selectedChildId];
        while (pending.length > 0) {
            const current = pending.pop();
            if (current === selectedParentId)
                return true;
            if (visited[current])
                continue;
            visited[current] = true;
            for (let i = 0; i < links.length; ++i) {
                const link = links[i];
                if (link.orgId === selectedOrgId && link.parentId === current)
                    pending.push(link.childId);
            }
        }
        return false;
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "FUNCTIONAL REPORTING // LOCAL MAP"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Describe which division, department or team sits below another " +
              "within one organization. No fixed division → department → team " +
              "sequence is imposed. Multiple relationships are permitted, but " +
              "loops are blocked. This is not a manager, employee or access grant."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !ready
        text: !reportingStore ? "REPORTING MAP // UNAVAILABLE"
              : reportingStore.state === "error"
              ? "REPORTING MAP ERROR // " + reportingStore.errorCode
              : "REPORTING MAP // " + reportingStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 155
        height: 28
        label: "RELOAD MAP"
        labelPixelSize: 9
        interactive: reportingStore !== null
                     && reportingStore.state !== "saving"
        onTriggered: reportingStore.refresh()
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
                    editor.selectedParentId = "";
                    editor.selectedChildId = "";
                    editor.confirmRemovalId = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        text: "2 // PARENT FUNCTION"
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
                selected: editor.selectedParentId === modelData.id
                onTriggered: editor.selectedParentId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        text: "3 // CHILD FUNCTION"
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
                selected: editor.selectedChildId === modelData.id
                onTriggered: editor.selectedChildId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedOrgId !== "" && editor.functions.length < 2
        text: "Create at least two active functional units in MY STRUCTURE above."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: editor.selectionValid &&
                 (editor.duplicateSelected || editor.wouldCycle())
        text: editor.duplicateSelected ? "This link already exists."
              : "This link would create a reporting loop and is blocked."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 195
        height: 30
        label: "+ LINK FUNCTIONS"
        labelPixelSize: 9
        interactive: editor.selectionValid && !editor.duplicateSelected
                     && !editor.wouldCycle()
        onTriggered: reportingStore.addRelationship(
            editor.selectedOrgId, editor.selectedParentId, editor.selectedChildId)
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.35
    }
    Text {
        width: parent.width
        text: "SAVED FUNCTION RELATIONSHIPS // " + editor.links.length
        color: Colors.cyan
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 169
        height: 28
        label: editor.showAllLinks ? "SHOW SELECTED ONLY" : "SHOW ALL LINKS"
        labelPixelSize: 9
        onTriggered: {
            editor.showAllLinks = !editor.showAllLinks;
            editor.confirmRemovalId = "";
        }
    }
    Text {
        width: parent.width
        visible: editor.links.length === 0
        text: "No functional reporting links saved yet."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: editor.links
        delegate: Column {
            id: row
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
                opacity: 0.25
            }
            Text {
                width: parent.width
                text: editor.showOrg(row.modelData.orgId) + " // "
                      + editor.showUnit(row.modelData.parentId) + " → "
                      + editor.showUnit(row.modelData.childId)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: editor.validLink(row.modelData)
                      ? "LOCAL REPORTING LABEL // NOT AN ACCESS GRANT"
                      : "STALE OR UNAVAILABLE // NOT AN ACCESS GRANT"
                color: editor.validLink(row.modelData)
                       ? Colors.cyan : Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: 169
                height: 28
                label: editor.confirmRemovalId === row.modelData.id
                       ? "CONFIRM UNLINK" : "UNLINK FUNCTIONS"
                labelPixelSize: 9
                accentColor: Colors.orange
                interactive: reportingStore !== null
                             && reportingStore.state === "ready"
                onTriggered: {
                    if (editor.confirmRemovalId === row.modelData.id) {
                        reportingStore.removeRelationship(row.modelData.id);
                        editor.confirmRemovalId = "";
                    } else {
                        editor.confirmRemovalId = row.modelData.id;
                    }
                }
            }
        }
    }
}
