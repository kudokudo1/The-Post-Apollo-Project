import QtQuick
import "../../components"
import qs.services.social

// CPU++ right bay. Reuse the existing atomic Social identity writer and
// private account-details writer, with edits pinned to the inspected local ID.
Item {
    id: detailsEditor
    property string identityId: ""
    readonly property var snapshot: SocialIdentityStore.snapshot
    readonly property var inspectedIdentity:
        snapshot && Array.isArray(snapshot.identities)
        ? snapshot.identities.find(function(item) {
              return item.id === detailsEditor.identityId;
          }) || null : null
    readonly property bool canRename:
        inspectedIdentity !== null && snapshot.writable
    readonly property bool canSaveContact:
        canRename && SocialAccountDetailsStore.state === "ready"
    readonly property var contactRecord:
        SocialAccountDetailsStore.state === "ready" && inspectedIdentity
        ? SocialAccountDetailsStore.recordFor(identityId) : null
    readonly property bool editingText:
        nameField.editingText || emailField.editingText
        || phoneField.editingText || linkedAccounts.editingText
    property string renameFeedback: ""
    property string contactFeedback: ""
    property string pendingRenameId: ""
    property string pendingContactId: ""
    implicitHeight: editorColumn.implicitHeight

    function resetDrafts() {
        nameField.text = inspectedIdentity ? inspectedIdentity.name : "";
        emailField.text = contactRecord ? (contactRecord.email || "") : "";
        phoneField.text = contactRecord ? (contactRecord.phone || "") : "";
        renameFeedback = "";
        contactFeedback = "";
    }
    onIdentityIdChanged: Qt.callLater(function() {
        detailsEditor.resetDrafts();
    })
    Component.onCompleted: resetDrafts()

    function saveName() {
        const targetId = identityId;
        if (!canRename || pendingRenameId !== ""
                || !nameField.text.trim())
            return;
        if (SocialIdentityStore.renameIdentity(targetId, nameField.text)) {
            pendingRenameId = targetId;
            renameFeedback = "SAVING ID NAME...";
        } else {
            renameFeedback = SocialIdentityStore.identityActionError || "RENAME NOT AVAILABLE";
        }
    }

    function saveContact() {
        const targetId = identityId;
        if (!canSaveContact || pendingContactId !== "")
            return;
        if (SocialAccountDetailsStore.saveContact(
                targetId, emailField.text, phoneField.text)) {
            pendingContactId = targetId;
            contactFeedback = "SAVING CONTACT...";
        } else {
            contactFeedback = SocialAccountDetailsStore.errorCode
                              || "CONTACT SAVE NOT AVAILABLE";
        }
    }

    Connections {
        target: SocialIdentityStore
        function onStorageStateChanged() {
            if (detailsEditor.pendingRenameId === "")
                return;
            if (SocialIdentityStore.storageState === "ready") {
                const id = detailsEditor.pendingRenameId;
                detailsEditor.pendingRenameId = "";
                if (id === detailsEditor.identityId) {
                    nameField.text = detailsEditor.inspectedIdentity
                                     ? detailsEditor.inspectedIdentity.name : "";
                    detailsEditor.renameFeedback = "ID NAME SAVED // LOCAL";
                }
            } else if (SocialIdentityStore.storageState === "error"
                       || SocialIdentityStore.storageState === "unsupported") {
                detailsEditor.pendingRenameId = "";
                detailsEditor.renameFeedback = "ID SAVE FAILED // "
                    + (SocialIdentityStore.errorCode || "STORAGE ERROR");
            }
        }
    }
    Connections {
        target: SocialAccountDetailsStore
        function onStateChanged() {
            if (detailsEditor.pendingContactId === "")
                return;
            if (SocialAccountDetailsStore.state === "ready") {
                const id = detailsEditor.pendingContactId;
                detailsEditor.pendingContactId = "";
                if (id === detailsEditor.identityId) {
                    emailField.text = detailsEditor.contactRecord
                                      ? (detailsEditor.contactRecord.email || "") : "";
                    phoneField.text = detailsEditor.contactRecord
                                      ? (detailsEditor.contactRecord.phone || "") : "";
                    detailsEditor.contactFeedback = "CONTACT SAVED // LOCAL";
                }
            } else if (SocialAccountDetailsStore.state === "error") {
                detailsEditor.pendingContactId = "";
                detailsEditor.contactFeedback = "CONTACT SAVE FAILED // "
                    + (SocialAccountDetailsStore.errorCode || "STORAGE ERROR");
            }
        }
    }

    Column {
        id: editorColumn
        width: parent.width
        spacing: 10

        GohuText {
            width: parent.width
            text: detailsEditor.inspectedIdentity
                  ? detailsEditor.inspectedIdentity.name : "NO ID SELECTED"
            color: Colors.magenta
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "LOCAL KEY // " + (detailsEditor.inspectedIdentity
                                      ? detailsEditor.inspectedIdentity.id : "NONE")
            color: Colors.cyan
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "LAYOUT FAMILIES // " + (detailsEditor.inspectedIdentity
                                            ? detailsEditor.inspectedIdentity.familyCount : 0)
            font.pixelSize: 10
        }
        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }

        GohuText {
            width: parent.width
            text: "RENAME LOCAL ID"
            font.pixelSize: 11
            color: Colors.cyan
        }
        QuietText {
            width: parent.width
            text: "DISPLAY NAME ONLY // STABLE ID KEY AND ACCOUNT LINKS ARE RETAINED"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        CpuPlusIdField {
            id: nameField
            width: parent.width
            height: 36
            maxLength: 32
            placeholder: "LOCAL ID DISPLAY NAME"
        }
        Row {
            width: parent.width
            spacing: 6
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 34
                label: "SAVE NAME"
                labelPixelSize: 9
                accentColor: Colors.green
                interactive: detailsEditor.canRename
                             && detailsEditor.pendingRenameId === ""
                             && nameField.text.trim().length > 0
                onClicked: detailsEditor.saveName()
            }
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 34
                label: "CANCEL"
                labelPixelSize: 9
                accentColor: Colors.white
                interactive: detailsEditor.pendingRenameId === ""
                onClicked: {
                    nameField.text = detailsEditor.inspectedIdentity
                                     ? detailsEditor.inspectedIdentity.name : "";
                    detailsEditor.renameFeedback = "";
                }
            }
        }
        QuietText {
            width: parent.width
            visible: detailsEditor.renameFeedback !== ""
                     || SocialIdentityStore.storageState === "error"
            text: detailsEditor.renameFeedback !== ""
                  ? detailsEditor.renameFeedback
                  : "IDENTITY STORAGE // " + SocialIdentityStore.errorCode
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        CpuPlusIdOrganizationLinksEditor {
            id: organizationLinks
            width: parent.width
            height: implicitHeight
            identityId: detailsEditor.identityId
        }
        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        GohuText {
            width: parent.width
            text: "CONTACT DEFAULTS"
            color: Colors.cyan
            font.pixelSize: 11
        }
        QuietText {
            width: parent.width
            text: "LOCAL NOTES // NEVER SENT TO PROVIDERS"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "DEFAULT EMAIL"
            color: Colors.cyan
            font.pixelSize: 9
        }
        CpuPlusIdField {
            id: emailField
            width: parent.width
            height: 36
            maxLength: 254
            hints: Qt.ImhEmailCharactersOnly
            placeholder: "NAME@EXAMPLE.COM"
        }
        QuietText {
            width: parent.width
            text: "DEFAULT PHONE"
            color: Colors.cyan
            font.pixelSize: 9
        }
        CpuPlusIdField {
            id: phoneField
            width: parent.width
            height: 36
            maxLength: 24
            hints: Qt.ImhDialableCharactersOnly
            placeholder: "PHONE NUMBER"
        }
        Row {
            width: parent.width
            spacing: 6
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 34
                label: "SAVE CONTACT"
                labelPixelSize: 9
                accentColor: Colors.green
                interactive: detailsEditor.canSaveContact
                             && detailsEditor.pendingContactId === ""
                onClicked: detailsEditor.saveContact()
            }
            ActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 34
                label: "CANCEL"
                labelPixelSize: 9
                accentColor: Colors.white
                interactive: detailsEditor.pendingContactId === ""
                onClicked: {
                    emailField.text = detailsEditor.contactRecord
                                      ? (detailsEditor.contactRecord.email || "") : "";
                    phoneField.text = detailsEditor.contactRecord
                                      ? (detailsEditor.contactRecord.phone || "") : "";
                    detailsEditor.contactFeedback = "";
                }
            }
        }
        QuietText {
            width: parent.width
            visible: detailsEditor.contactFeedback !== ""
                     || SocialAccountDetailsStore.state === "error"
            text: detailsEditor.contactFeedback !== ""
                  ? detailsEditor.contactFeedback
                  : "CONTACT STORAGE // " + SocialAccountDetailsStore.errorCode
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        CpuPlusIdAccountEditor {
            id: linkedAccounts
            width: parent.width
            height: implicitHeight
            identityId: detailsEditor.identityId
        }
    }
}
