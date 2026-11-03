import QtQuick
import "../../components"

// Explicit local branch-to-location labels. This does not migrate branches,
// change ownership, grant access, or establish verified physical addresses.
Column {
    id: editor
    property var directoryStore: null
    property var structureStore: null
    property var linkStore: null
    property string selectedOrgId: ""
    property string selectedBranchId: ""
    property string selectedLocationId: ""
    property string confirmationId: ""
    property bool showAllLinks: false
    spacing: 9

    readonly property bool inputsReady:
        directoryStore !== null && directoryStore.state === "ready"
        && structureStore !== null && structureStore.state === "ready"
    readonly property bool storeReady:
        linkStore !== null && linkStore.state === "ready"
    readonly property var allOrganizations:
        inputsReady ? directoryStore.saved.organizations : []
    readonly property var activeOrganizations:
        allOrganizations.filter(function(org) { return !org.archived; })
    readonly property var selectedOrganization:
        allOrganizations.find(function(org) {
            return org.id === editor.selectedOrgId && !org.archived;
        }) || null
    readonly property var branches:
        selectedOrganization
        ? selectedOrganization.branches.filter(function(branch) {
            return !branch.archived;
        }) : []
    readonly property var locations:
        inputsReady ? structureStore.saved.units.filter(function(unit) {
            return unit.orgId === editor.selectedOrgId
                   && unit.kind === "location" && !unit.archived;
        }) : []
    readonly property var savedLinks:
        linkStore && linkStore.saved ? linkStore.saved.links : []
    readonly property bool readyToAdd:
        inputsReady && storeReady && selectedOrganization !== null
        && branches.some(function(branch) {
            return branch.id === editor.selectedBranchId;
        })
        && locations.some(function(location) {
            return location.id === editor.selectedLocationId;
        })

    function resolveOrganization(orgId) {
        return allOrganizations.find(function(org) {
            return org.id === orgId;
        }) || null;
    }
    function resolveBranch(link) {
        const org = resolveOrganization(link.orgId);
        return org ? org.branches.find(function(branch) {
            return branch.id === link.branchId;
        }) || null : null;
    }
    function resolveLocation(locationId) {
        return inputsReady ? structureStore.saved.units.find(function(unit) {
            return unit.id === locationId;
        }) || null : null;
    }
    function describeOrg(orgId) {
        const org = resolveOrganization(orgId);
        return org ? org.name + (org.archived ? " [ARCHIVED]" : "")
                   : "MISSING ORGANIZATION // " + orgId;
    }
    function describeBranch(link) {
        const branch = resolveBranch(link);
        return branch ? branch.name + (branch.archived ? " [ARCHIVED]" : "")
                      : "MISSING BRANCH // " + link.branchId;
    }
    function describeLocation(link) {
        const unit = resolveLocation(link.locationId);
        return unit ? unit.name + (unit.archived ? " [ARCHIVED]" : "")
                    : "MISSING LOCATION // " + link.locationId;
    }
    function currentLink(link) {
        if (!inputsReady) return false;
        const org = resolveOrganization(link.orgId);
        const branch = resolveBranch(link);
        const location = resolveLocation(link.locationId);
        return !!(org && !org.archived && branch && !branch.archived
            && location && !location.archived
            && location.kind === "location" && location.orgId === link.orgId);
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "BRANCH LINKS // LOCATIONS"
        font.pixelSize: 12
        font.bold: true
        color: Colors.cyan
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Associate an existing branch with one or more locations from " +
              "the SAME organization. Branches and locations remain separate " +
              "records. A link is not proof of an address or an access grant."
        font.pixelSize: 10
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !editor.inputsReady || !editor.storeReady
        text: !editor.linkStore ? "BRANCH LINKS // UNAVAILABLE"
              : editor.linkStore.state === "error"
              ? "BRANCH LINKS ERROR // " + editor.linkStore.errorCode
              : "BRANCH LINKS // " + editor.linkStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 134
        height: 28
        label: "RELOAD LINKS"
        labelPixelSize: 9
        interactive: linkStore !== null && linkStore.state !== "saving"
        onTriggered: linkStore.refresh()
    }
    Text {
        width: parent.width
        text: "1 // ORGANIZATION"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: editor.activeOrganizations
            delegate: ActionButton {
                required property var modelData
                width: Math.min(190, Math.max(110, editor.width - 12))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedOrgId === modelData.id
                onTriggered: {
                    editor.selectedOrgId = modelData.id;
                    editor.selectedBranchId = "";
                    editor.selectedLocationId = "";
                    editor.confirmationId = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        text: "2 // EXISTING BRANCH"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: editor.branches
            delegate: ActionButton {
                required property var modelData
                width: Math.min(190, Math.max(110, editor.width - 12))
                height: 29
                label: modelData.name
                labelPixelSize: 9
                selected: editor.selectedBranchId === modelData.id
                onTriggered: editor.selectedBranchId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: editor.selectedOrganization !== null
                 && editor.branches.length === 0
        text: "Create an active branch in MY ORGANIZATIONS above first."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "3 // STRUCTURE LOCATION"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
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
        visible: editor.selectedOrganization !== null
                 && editor.locations.length === 0
        text: "Create a LOCATION for this organization in MY STRUCTURE."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 188
        height: 30
        label: "+ LINK BRANCH TO LOCATION"
        labelPixelSize: 9
        interactive: editor.readyToAdd
        onTriggered: linkStore.linkBranch(
            editor.selectedOrgId, editor.selectedBranchId,
            editor.selectedLocationId)
    }
    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "SAVED BRANCH-LOCATION LINKS // " + editor.savedLinks.length
        color: Colors.cyan
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 166
        height: 28
        label: editor.showAllLinks ? "SHOW SELECTED ONLY" : "SHOW ALL LINKS"
        labelPixelSize: 9
        onTriggered: {
            editor.showAllLinks = !editor.showAllLinks;
            editor.confirmationId = "";
        }
    }
    Text {
        width: parent.width
        visible: editor.savedLinks.length === 0
        text: "No local branch-location links saved yet."
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
                opacity: 0.25
            }
            Text {
                width: parent.width
                text: editor.describeOrg(linkRow.modelData.orgId)
                      + " // BRANCH: " + editor.describeBranch(linkRow.modelData)
                      + " → LOCATION: " + editor.describeLocation(linkRow.modelData)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: editor.currentLink(linkRow.modelData)
                      ? "LOCAL ASSOCIATION ONLY // NOT AN ACCESS GRANT"
                      : "STALE OR UNAVAILABLE // NOT AN ACCESS GRANT"
                color: editor.currentLink(linkRow.modelData)
                       ? Colors.cyan : Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: 170
                height: 28
                label: editor.confirmationId === linkRow.modelData.id
                       ? "CONFIRM UNLINK" : "UNLINK BRANCH LOCATION"
                labelPixelSize: 9
                accentColor: Colors.orange
                interactive: linkStore !== null && linkStore.state === "ready"
                onTriggered: {
                    if (editor.confirmationId === linkRow.modelData.id) {
                        linkStore.unlinkBranch(linkRow.modelData.id);
                        editor.confirmationId = "";
                    } else {
                        editor.confirmationId = linkRow.modelData.id;
                    }
                }
            }
        }
    }
}
