import QtQuick
import "../../components"
import qs.services.social
import "../../services/social/SocialIdentityPolicy.js" as IdentityPolicy

// Reuses Social's *local* organization directory and association writer.
// Neither record set proves tenant membership, role or provider login.
Item {
    id: editor
    property string identityId: ""
    property bool expanded: false
    property string chosenOrgId: ""
    property string chosenBranchId: ""
    property bool accountMode: false
    property string chosenServiceId: ""
    property string chosenAccountId: ""
    property string confirmUnlinkId: ""
    property string pendingAction: ""
    property string pendingIdentityId: ""
    property string feedback: ""

    readonly property var identitySnapshot: SocialIdentityStore.snapshot
    readonly property bool validIdentity:
        identitySnapshot && identitySnapshot.writable
        && Array.isArray(identitySnapshot.identities)
        && identitySnapshot.identities.some(function(entry) {
            return entry.id === editor.identityId;
        })
    readonly property bool directoryReady:
        SocialOrganizationDirectoryStore.state === "ready"
    readonly property bool linksReady:
        SocialOrganizationLinksStore.state === "ready"
    readonly property var organizations:
        directoryReady ? SocialOrganizationDirectoryStore.saved.organizations : []
    readonly property var availableOrganizations:
        organizations.filter(function(entry) { return !entry.archived; })
    readonly property var chosenOrganization:
        availableOrganizations.find(function(entry) {
            return entry.id === editor.chosenOrgId;
        }) || null
    readonly property var availableBranches:
        chosenOrganization ? chosenOrganization.branches.filter(function(entry) {
            return !entry.archived;
        }) : []
    readonly property var savedLinks:
        linksReady ? SocialOrganizationLinksStore.saved.links : []
    readonly property var identityLinks:
        savedLinks.filter(function(entry) {
            return entry.identityId === editor.identityId;
        })
    readonly property bool detailsReady:
        SocialAccountDetailsStore.state === "ready"
    readonly property var savedAccountRecord:
        validIdentity && detailsReady
        ? SocialAccountDetailsStore.recordFor(identityId) : null
    readonly property var accountServices:
        savedAccountRecord && savedAccountRecord.accounts
        ? Object.keys(savedAccountRecord.accounts).filter(function(serviceId) {
            return IdentityPolicy.APP_IDS.indexOf(serviceId) !== -1;
        }) : []
    readonly property var chosenAccounts:
        accountServices.indexOf(chosenServiceId) !== -1 && detailsReady
        ? SocialAccountDetailsStore.accountNamesFor(identityId, chosenServiceId) : []
    readonly property bool accountChoiceValid:
        chosenAccounts.some(function(account) {
            return account.id === editor.chosenAccountId;
        })
    readonly property bool branchChoiceValid:
        chosenBranchId === "" || availableBranches.some(function(branch) {
            return branch.id === editor.chosenBranchId;
        })
    readonly property bool targetAlreadyLinked:
        identityLinks.some(function(link) {
            return link.orgId === editor.chosenOrgId
                   && link.branchId === (editor.chosenBranchId || null)
                   && link.serviceId === (editor.accountMode
                                          ? editor.chosenServiceId : null)
                   && link.accountId === (editor.accountMode
                                          ? editor.chosenAccountId : null);
        })
    readonly property bool canSaveLink:
        validIdentity && directoryReady && linksReady
        && pendingAction === "" && chosenOrganization !== null
        && branchChoiceValid && (!accountMode
                                 || (detailsReady && accountChoiceValid))
        && !targetAlreadyLinked
    implicitHeight: content.implicitHeight

    function resetChoices() {
        chosenOrgId = "";
        chosenBranchId = "";
        accountMode = false;
        chosenServiceId = "";
        chosenAccountId = "";
        confirmUnlinkId = "";
        feedback = "";
    }
    onIdentityIdChanged: Qt.callLater(function() {
        editor.resetChoices();
    })

    function orgName(orgId) {
        if (!directoryReady)
            return "ORGANIZATION UNAVAILABLE // " + orgId;
        const found = organizations.find(function(entry) { return entry.id === orgId; });
        return found ? found.name + (found.archived ? " (ARCHIVED)" : "")
                     : "MISSING ORGANIZATION // " + orgId;
    }
    function branchName(orgId, branchId) {
        if (branchId === null)
            return "ORGANIZATION LEVEL";
        if (!directoryReady)
            return "BRANCH UNAVAILABLE // " + branchId;
        const org = organizations.find(function(entry) { return entry.id === orgId; });
        const branch = org ? org.branches.find(function(entry) {
            return entry.id === branchId;
        }) : null;
        return branch ? branch.name + (branch.archived ? " (ARCHIVED)" : "")
                      : "MISSING BRANCH // " + branchId;
    }
    function accountName(link) {
        if (link.serviceId === null)
            return "LOCAL ID LABEL";
        if (!detailsReady)
            return "ACCOUNT NAMES NOT LOADED";
        const entries = SocialAccountDetailsStore.accountNamesFor(
            link.identityId, link.serviceId);
        const found = entries.find(function(entry) {
            return entry.id === link.accountId;
        });
        return link.serviceId.toUpperCase() + " // "
               + (found ? found.label : "MISSING ACCOUNT NAME");
    }

    function saveLink() {
        if (!canSaveLink)
            return;
        const targetId = identityId;
        const accepted = accountMode
            ? SocialOrganizationLinksStore.linkAccountLabel(
                chosenOrgId, chosenBranchId || null,
                targetId, chosenServiceId, chosenAccountId)
            : SocialOrganizationLinksStore.linkIdentity(
                chosenOrgId, chosenBranchId || null, targetId);
        if (accepted) {
            pendingAction = "LINK";
            pendingIdentityId = targetId;
            confirmUnlinkId = "";
            feedback = "SAVING LOCAL ASSOCIATION...";
        } else {
            feedback = SocialOrganizationLinksStore.errorCode
                       || "LINK WRITE UNAVAILABLE";
        }
    }
    function requestUnlink(link) {
        if (!linksReady || !validIdentity || pendingAction !== ""
                || link.identityId !== identityId)
            return;
        // Two-click remove, scoped to the current ID and existing link key.
        if (confirmUnlinkId !== link.id) {
            confirmUnlinkId = link.id;
            feedback = "CONFIRM UNLINK // " + orgName(link.orgId);
            return;
        }
        const targetId = identityId;
        const stillPresent = identityLinks.some(function(entry) {
            return entry.id === link.id && entry.identityId === targetId;
        });
        if (!stillPresent) {
            confirmUnlinkId = "";
            feedback = "ASSOCIATION CHANGED // SELECT AGAIN";
            return;
        }
        if (SocialOrganizationLinksStore.unlink(link.id)) {
            pendingAction = "UNLINK";
            pendingIdentityId = targetId;
            confirmUnlinkId = "";
            feedback = "REMOVING LOCAL ASSOCIATION...";
        } else {
            feedback = SocialOrganizationLinksStore.errorCode
                       || "UNLINK WRITE UNAVAILABLE";
        }
    }

    Connections {
        target: SocialOrganizationLinksStore
        function onStateChanged() {
            if (editor.pendingAction === "")
                return;
            const action = editor.pendingAction;
            if (SocialOrganizationLinksStore.state === "ready") {
                editor.pendingAction = "";
                if (editor.pendingIdentityId === editor.identityId)
                    editor.feedback = action === "LINK"
                                      ? "ASSOCIATION SAVED // LOCAL"
                                      : "ASSOCIATION REMOVED // LOCAL";
                editor.pendingIdentityId = "";
            } else if (SocialOrganizationLinksStore.state === "error") {
                editor.pendingAction = "";
                editor.pendingIdentityId = "";
                editor.feedback = "ASSOCIATION SAVE FAILED // "
                    + (SocialOrganizationLinksStore.errorCode || "STORAGE ERROR");
            }
        }
    }

    Column {
        id: content
        width: parent.width
        spacing: 9

        GohuText {
            width: parent.width
            text: "ORGANIZATIONS // ASSOCIATIONS"
            color: Colors.cyan
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "LINK THIS ID TO LOCAL COMPANIES, NONPROFITS, BRANCHES "
                  + "OR SAVED ACCOUNT NAMES. NO LOGIN, MEMBERSHIP OR PERMISSION CHANGE."
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "CURRENT LINKS // " + editor.identityLinks.length
            color: Colors.magenta
            font.pixelSize: 10
        }
        ActionButton {
            width: parent.width
            height: 34
            label: editor.expanded
                   ? "HIDE ASSOCIATIONS"
                   : "EDIT ASSOCIATIONS // " + editor.identityLinks.length
            labelPixelSize: 9
            accentColor: Colors.magenta
            selected: editor.expanded
            onClicked: editor.expanded = !editor.expanded
        }
        Column {
            id: expandedContent
            width: parent.width
            spacing: 9
            visible: editor.expanded

            Repeater {
                model: editor.identityLinks
                delegate: Column {
                    id: linkRow
                    required property var modelData
                    width: content.width
                    spacing: 4

                    QuietText {
                        width: parent.width
                        text: editor.orgName(linkRow.modelData.orgId)
                              + " / " + editor.branchName(
                                  linkRow.modelData.orgId, linkRow.modelData.branchId)
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Row {
                        width: parent.width
                        spacing: 5
                        QuietText {
                            width: parent.width - unlinkButton.width - parent.spacing
                            text: editor.accountName(linkRow.modelData)
                            color: Colors.cyan
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }
                        ActionButton {
                            id: unlinkButton
                            width: 104
                            height: 31
                            label: editor.confirmUnlinkId === linkRow.modelData.id
                                   ? "CONFIRM X" : "UNLINK X"
                            labelPixelSize: 9
                            destructive: true
                            accentColor: Colors.red
                            interactive: editor.linksReady && editor.validIdentity
                                         && editor.pendingAction === ""
                            onClicked: editor.requestUnlink(linkRow.modelData)
                        }
                    }
                }
            }
            QuietText {
                width: parent.width
                visible: editor.identityLinks.length === 0
                text: "NO LOCAL ASSOCIATIONS SAVED FOR THIS ID"
                color: Colors.white
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 29
                visible: editor.confirmUnlinkId !== ""
                label: "CANCEL UNLINK"
                labelPixelSize: 9
                accentColor: Colors.white
                onClicked: {
                    editor.confirmUnlinkId = "";
                    editor.feedback = "";
                }
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }
            QuietText {
                width: parent.width
                text: "1 // SELECT LOCAL ORGANIZATION"
                font.pixelSize: 9
                color: Colors.cyan
            }
            Rectangle {
                width: parent.width
                height: 132
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                Flickable {
                    anchors.fill: parent
                    anchors.margins: 4
                    contentWidth: width
                    contentHeight: orgChoices.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: orgChoices
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: editor.availableOrganizations
                            delegate: ActionButton {
                                required property var modelData
                                width: orgChoices.width
                                height: 32
                                label: modelData.name
                                labelPixelSize: 9
                                selected: editor.chosenOrgId === modelData.id
                                accentColor: Colors.cyan
                                onClicked: {
                                    editor.chosenOrgId = modelData.id;
                                    editor.chosenBranchId = "";
                                    editor.confirmUnlinkId = "";
                                }
                            }
                        }
                    }
                }
            }
            QuietText {
                width: parent.width
                visible: editor.availableOrganizations.length === 0
                text: editor.directoryReady
                      ? "NO ACTIVE LOCAL ORGANIZATIONS // CREATE IN SOCIAL ACCOUNT CENTER"
                      : "DIRECTORY // " + SocialOrganizationDirectoryStore.state.toUpperCase()
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                visible: editor.chosenOrganization !== null
                text: "2 // ASSOCIATION LEVEL"
                color: Colors.cyan
                font.pixelSize: 9
            }
            Column {
                width: parent.width
                spacing: 4
                visible: editor.chosenOrganization !== null
                ActionButton {
                    width: parent.width
                    height: 31
                    label: "ORGANIZATION LEVEL"
                    labelPixelSize: 9
                    selected: editor.chosenBranchId === ""
                    accentColor: Colors.cyan
                    onClicked: editor.chosenBranchId = ""
                }
                Repeater {
                    model: editor.availableBranches
                    delegate: ActionButton {
                        required property var modelData
                        width: content.width
                        height: 31
                        label: "BRANCH // " + modelData.name
                        labelPixelSize: 9
                        selected: editor.chosenBranchId === modelData.id
                        accentColor: Colors.cyan
                        onClicked: editor.chosenBranchId = modelData.id
                    }
                }
            }
            QuietText {
                width: parent.width
                text: "3 // LINK LOCAL ID OR SAVED ACCOUNT NAME"
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Row {
                width: parent.width
                spacing: 4
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 31
                    label: "LOCAL ID"
                    labelPixelSize: 9
                    selected: !editor.accountMode
                    accentColor: Colors.cyan
                    onClicked: {
                        editor.accountMode = false;
                        editor.chosenServiceId = "";
                        editor.chosenAccountId = "";
                    }
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 31
                    label: "ACCOUNT NAME"
                    labelPixelSize: 9
                    selected: editor.accountMode
                    accentColor: Colors.cyan
                    onClicked: editor.accountMode = true
                }
            }
            Column {
                width: parent.width
                spacing: 5
                visible: editor.accountMode
                QuietText {
                    width: parent.width
                    text: "SAVED ACCOUNT SERVICES // " + editor.accountServices.length
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: editor.accountServices
                    delegate: ActionButton {
                        required property string modelData
                        width: content.width
                        height: 31
                        label: modelData.toUpperCase()
                        labelPixelSize: 9
                        selected: editor.chosenServiceId === modelData
                        accentColor: Colors.cyan
                        onClicked: {
                            editor.chosenServiceId = modelData;
                            editor.chosenAccountId = "";
                        }
                    }
                }
                Repeater {
                    model: editor.chosenAccounts
                    delegate: ActionButton {
                        required property var modelData
                        width: content.width
                        height: 31
                        label: modelData.label
                        labelPixelSize: 9
                        selected: editor.chosenAccountId === modelData.id
                        accentColor: Colors.cyan
                        onClicked: editor.chosenAccountId = modelData.id
                    }
                }
            }
            ActionButton {
                width: parent.width
                height: 35
                label: editor.accountMode ? "+ LINK ACCOUNT NAME" : "+ LINK LOCAL ID"
                labelPixelSize: 9
                accentColor: Colors.magenta
                interactive: editor.canSaveLink
                onClicked: editor.saveLink()
            }
            QuietText {
                width: parent.width
                visible: editor.targetAlreadyLinked
                text: "THIS LOCAL ASSOCIATION ALREADY EXISTS"
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                visible: editor.feedback !== ""
                text: editor.feedback
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                visible: !editor.directoryReady || !editor.linksReady
                         || (editor.accountMode && !editor.detailsReady)
                text: "STORES // DIRECTORY: "
                      + SocialOrganizationDirectoryStore.state.toUpperCase()
                      + " / LINKS: " + SocialOrganizationLinksStore.state.toUpperCase()
                      + " / ACCOUNT NAMES: " + SocialAccountDetailsStore.state.toUpperCase()
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 30
                visible: !editor.directoryReady
                label: "RELOAD ORGANIZATIONS"
                labelPixelSize: 9
                accentColor: Colors.yellow
                interactive: SocialOrganizationDirectoryStore.state !== "saving"
                onClicked: SocialOrganizationDirectoryStore.refresh()
            }
            ActionButton {
                width: parent.width
                height: 30
                visible: !editor.linksReady
                label: "RELOAD ASSOCIATIONS"
                labelPixelSize: 9
                accentColor: Colors.yellow
                interactive: SocialOrganizationLinksStore.state !== "saving"
                onClicked: SocialOrganizationLinksStore.refresh()
            }
            QuietText {
                width: parent.width
                text: "EDIT ORGANIZATION / BRANCH RECORDS IN "
                      + "SOCIAL // USER SETTINGS // ORGANIZATIONS."
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }
}
