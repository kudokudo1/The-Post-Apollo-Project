import QtQuick
import "../../components"

// LOCAL LABEL LINKS ONLY: never connects a provider, changes a session,
// assigns company roles, or grants permission to another identity/tenant.
Column {
    id: linksEditor
    property var directoryStore: null
    property var linksStore: null
    property var identitiesSnapshot: null
    property var accountDetailsStore: null
    property string selectedOrgId: ""
    property string selectedBranchId: ""
    property string selectedIdentityId: ""
    property string selectedServiceId: ""
    property string selectedAccountId: ""
    property string pendingUnlinkId: ""
    property bool showAllLinks: false
    spacing: 9

    readonly property var availableOrganizations:
        directoryStore && directoryStore.state === "ready"
        ? directoryStore.saved.organizations.filter(function(org) {
            return !org.archived;
        }) : []
    readonly property var selectedOrganization:
        availableOrganizations.find(function(org) {
            return org.id === linksEditor.selectedOrgId;
        }) || null
    readonly property var availableBranches:
        selectedOrganization
        ? selectedOrganization.branches.filter(function(branch) {
            return !branch.archived;
        }) : []
    readonly property var identities:
        identitiesSnapshot && identitiesSnapshot.writable
        ? (identitiesSnapshot.identities || []) : []
    readonly property bool validTarget:
        selectedOrganization !== null
        && (!selectedBranchId || availableBranches.some(function(branch) {
            return branch.id === selectedBranchId;
        }))
    readonly property bool validIdentity:
        identities.some(function(identity) {
            return identity.id === selectedIdentityId;
        })
    readonly property bool readyToLink:
        linksStore !== null && linksStore.state === "ready"
        && validTarget && validIdentity
    readonly property var servicesWithNames:
        accountDetailsStore && accountDetailsStore.state === "ready"
        && validIdentity
        ? Object.keys(accountDetailsStore.recordFor(selectedIdentityId).accounts || {})
            .filter(function(serviceId) {
                return accountDetailsStore.accountNamesFor(
                    linksEditor.selectedIdentityId, serviceId).length > 0;
            }).sort()
        : []
    readonly property var accountNames:
        accountDetailsStore && accountDetailsStore.state === "ready"
        && servicesWithNames.includes(selectedServiceId)
        ? accountDetailsStore.accountNamesFor(selectedIdentityId, selectedServiceId)
        : []
    readonly property var savedLinks:
        linksStore && linksStore.saved ? linksStore.saved.links : []

    function displayIdentity(identityId) {
        const found = identities.find(function(i) { return i.id === identityId; });
        return found ? found.name + " (" + identityId + ")" :
                       "MISSING SOCIAL IDENTITY // " + identityId;
    }
    function displayScope(link) {
        if (!directoryStore || directoryStore.state !== "ready")
            return "DIRECTORY UNAVAILABLE";
        const org = directoryStore.saved.organizations.find(function(o) {
            return o.id === link.orgId;
        });
        if (!org)
            return "MISSING ORGANIZATION";
        const prefix = org.name + (org.archived ? " (ARCHIVED)" : "");
        if (link.branchId === null)
            return prefix + " / ORGANIZATION LABEL";
        const branch = org.branches.find(function(b) {
            return b.id === link.branchId;
        });
        return prefix + " / " + (branch
               ? branch.name + (branch.archived ? " (ARCHIVED)" : "")
               : "MISSING BRANCH");
    }
    function displayAccount(link) {
        if (link.serviceId === null)
            return "SOCIAL IDENTITY LABEL";
        if (!accountDetailsStore || accountDetailsStore.state !== "ready")
            return "ACCOUNT LABEL UNAVAILABLE";
        const names = accountDetailsStore.accountNamesFor(
            link.identityId, link.serviceId);
        const found = names.find(function(a) { return a.id === link.accountId; });
        return found
            ? "ACCOUNT NICKNAME // " + link.serviceId.toUpperCase()
                + " / " + found.label
            : "MISSING ACCOUNT NICKNAME // " + link.serviceId;
    }
    function linkIsCurrent(link) {
        if (!directoryStore || directoryStore.state !== "ready")
            return false;
        const org = availableOrganizations.find(function(o) {
            return o.id === link.orgId;
        });
        if (!org || (link.branchId !== null &&
                !org.branches.some(function(b) {
                    return b.id === link.branchId && !b.archived;
                })))
            return false;
        if (!identities.some(function(i) { return i.id === link.identityId; }))
            return false;
        if (link.serviceId === null)
            return true;
        if (!accountDetailsStore || accountDetailsStore.state !== "ready")
            return false;
        return accountDetailsStore.accountNamesFor(
            link.identityId, link.serviceId).some(function(a) {
                return a.id === link.accountId;
            });
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
    }
    Text {
        width: parent.width
        text: "SOCIAL LINKS // LOCAL LABEL ASSOCIATIONS"
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Associate an organization or branch with an existing Social " +
              "layout identity or saved account nickname. This does NOT " +
              "connect accounts, designate legal ownership, or grant access."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: !linksStore || linksStore.state !== "ready"
        text: !linksStore ? "LOCAL LINKS // NOT LOADED" :
              linksStore.state === "error"
              ? "LOCAL LINKS ERROR // " + linksStore.errorCode
              : "LOCAL LINKS // " + linksStore.state.toUpperCase()
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 118
        height: 28
        label: "RELOAD LINKS"
        labelPixelSize: 9
        interactive: linksStore !== null && linksStore.state !== "saving"
        onTriggered: linksStore.refresh()
    }
    Text {
        width: parent.width
        text: "1 // SELECT LOCAL ORGANIZATION"
        color: Colors.cyan
        font.pixelSize: 10
        font.bold: true
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: linksEditor.availableOrganizations
            delegate: ActionButton {
                required property var modelData
                width: Math.min(180, Math.max(105, linksEditor.width - 5))
                height: 30
                label: modelData.name
                labelPixelSize: 9
                selected: linksEditor.selectedOrgId === modelData.id
                onTriggered: {
                    linksEditor.selectedOrgId = modelData.id;
                    linksEditor.selectedBranchId = "";
                    linksEditor.pendingUnlinkId = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        visible: linksEditor.availableOrganizations.length === 0
        text: "Create an active local organization above before linking labels."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "2 // ORGANIZATION LABEL OR BRANCH LABEL"
        color: Colors.cyan
        font.pixelSize: 10
        font.bold: true
        visible: linksEditor.selectedOrganization !== null
    }
    Flow {
        width: parent.width
        spacing: 5
        height: visible ? childrenRect.height : 0
        visible: linksEditor.selectedOrganization !== null
        ActionButton {
            width: 155
            height: 28
            label: "ORGANIZATION LEVEL"
            labelPixelSize: 9
            selected: linksEditor.selectedBranchId === ""
            onTriggered: linksEditor.selectedBranchId = ""
        }
        Repeater {
            model: linksEditor.availableBranches
            delegate: ActionButton {
                required property var modelData
                width: Math.min(180, Math.max(105, linksEditor.width - 5))
                height: 28
                label: modelData.name
                labelPixelSize: 9
                selected: linksEditor.selectedBranchId === modelData.id
                onTriggered: linksEditor.selectedBranchId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        text: "3 // SELECT SOCIAL LAYOUT IDENTITY"
        color: Colors.cyan
        font.pixelSize: 10
        font.bold: true
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: linksEditor.identities
            delegate: ActionButton {
                required property var modelData
                width: Math.min(180, Math.max(105, linksEditor.width - 5))
                height: 28
                label: modelData.name
                labelPixelSize: 9
                selected: linksEditor.selectedIdentityId === modelData.id
                onTriggered: {
                    linksEditor.selectedIdentityId = modelData.id;
                    linksEditor.selectedServiceId = "";
                    linksEditor.selectedAccountId = "";
                }
            }
        }
    }
    Text {
        width: parent.width
        text: "Social identity list unavailable; local identity storage must be ready."
        visible: linksEditor.identities.length === 0
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 190
        height: 30
        label: "+ LINK IDENTITY LABEL"
        labelPixelSize: 9
        accentColor: Colors.cyan
        interactive: linksEditor.readyToLink
        onTriggered: {
            linksEditor.linksStore.linkIdentity(
                linksEditor.selectedOrgId,
                linksEditor.selectedBranchId || null,
                linksEditor.selectedIdentityId);
        }
    }
    Text {
        width: parent.width
        text: "4 // OPTIONAL ACCOUNT NICKNAME FROM THAT IDENTITY"
        font.pixelSize: 10
        font.bold: true
        color: Colors.cyan
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: linksEditor.servicesWithNames
            delegate: ActionButton {
                required property string modelData
                width: 120
                height: 28
                label: modelData.toUpperCase()
                labelPixelSize: 9
                selected: linksEditor.selectedServiceId === modelData
                onTriggered: {
                    linksEditor.selectedServiceId = modelData;
                    linksEditor.selectedAccountId = "";
                }
            }
        }
    }
    Flow {
        width: parent.width
        spacing: 5
        height: childrenRect.height
        Repeater {
            model: linksEditor.accountNames
            delegate: ActionButton {
                required property var modelData
                width: Math.min(180, Math.max(105, linksEditor.width - 5))
                height: 28
                label: modelData.label
                labelPixelSize: 9
                selected: linksEditor.selectedAccountId === modelData.id
                onTriggered: linksEditor.selectedAccountId = modelData.id
            }
        }
    }
    Text {
        width: parent.width
        visible: linksEditor.validIdentity && linksEditor.servicesWithNames.length === 0
        text: "No saved account nicknames for this identity. " +
              "Add them in SOCIAL LAYOUT → ACCOUNT NAMES first."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    ActionButton {
        width: 205
        height: 30
        label: "+ LINK ACCOUNT NICKNAME"
        labelPixelSize: 9
        interactive: linksEditor.readyToLink
                     && accountDetailsStore !== null
                     && accountDetailsStore.state === "ready"
                     && linksEditor.accountNames.some(function(a) {
                         return a.id === linksEditor.selectedAccountId;
                     })
        onTriggered: {
            linksEditor.linksStore.linkAccountLabel(
                linksEditor.selectedOrgId,
                linksEditor.selectedBranchId || null,
                linksEditor.selectedIdentityId,
                linksEditor.selectedServiceId,
                linksEditor.selectedAccountId);
        }
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.45
    }
    Text {
        width: parent.width
        text: "SAVED LABEL LINKS // " + linksEditor.savedLinks.length
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 11
    }
    ActionButton {
        width: 150
        height: 28
        label: linksEditor.showAllLinks ? "SHOW TARGET ONLY" : "SHOW ALL LINKS"
        labelPixelSize: 9
        onTriggered: {
            linksEditor.showAllLinks = !linksEditor.showAllLinks;
            linksEditor.pendingUnlinkId = "";
        }
    }
    Text {
        width: parent.width
        visible: linksEditor.savedLinks.length === 0
        text: "No local Social label links saved yet."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: linksEditor.savedLinks
        delegate: Column {
            id: linkRow
            required property var modelData
            width: linksEditor.width
            spacing: 4
            visible: linksEditor.showAllLinks ||
                     (linksEditor.selectedOrgId === modelData.orgId
                      && (linksEditor.selectedBranchId || null) === modelData.branchId)
            height: visible ? implicitHeight : 0
            Text {
                width: parent.width
                text: linksEditor.displayScope(linkRow.modelData) + " // " +
                      linksEditor.displayIdentity(linkRow.modelData.identityId)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: linksEditor.displayAccount(linkRow.modelData) +
                      (linksEditor.linkIsCurrent(linkRow.modelData)
                       ? " // LOCAL ONLY" : " // STALE OR UNAVAILABLE")
                color: linksEditor.linkIsCurrent(linkRow.modelData)
                       ? Colors.cyan : Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: 148
                height: 27
                label: linksEditor.pendingUnlinkId === linkRow.modelData.id
                       ? "CONFIRM UNLINK" : "UNLINK LABEL"
                labelPixelSize: 9
                accentColor: Colors.orange
                interactive: linksEditor.linksStore !== null
                             && linksEditor.linksStore.state === "ready"
                onTriggered: {
                    if (linksEditor.pendingUnlinkId === linkRow.modelData.id) {
                        linksEditor.linksStore.unlink(linkRow.modelData.id);
                        linksEditor.pendingUnlinkId = "";
                    } else {
                        linksEditor.pendingUnlinkId = linkRow.modelData.id;
                    }
                }
            }
        }
    }
}
