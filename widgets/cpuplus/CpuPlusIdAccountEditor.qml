import QtQuick
import "../../components"
import qs.services.social
import "../../services/social/SocialIdentityPolicy.js" as IdentityPolicy

// Local saved provider ACCOUNT NAMES, not sign-ins or live connection state.
// Keep all writes routed through the existing private AccountDetailsStore.
Item {
    id: accountEditor
    property string identityId: ""
    readonly property var identitySnapshot: SocialIdentityStore.snapshot
    readonly property bool identityExists:
        identitySnapshot && Array.isArray(identitySnapshot.identities)
        && identitySnapshot.identities.some(function(entry) {
            return entry.id === accountEditor.identityId;
        })
    readonly property bool canEdit: identityExists && identitySnapshot.writable
                                    && SocialAccountDetailsStore.state === "ready"
    readonly property bool editingText:
        serviceFilter.editingText || labelField.editingText

    property string selectedServiceId: ""
    property string selectedAccountId: ""
    property bool servicePickerOpen: false
    property string feedback: ""
    property string pendingAction: ""
    property string pendingIdentityId: ""
    property string confirmRemoveId: ""
    readonly property var storedRecord:
        identityExists && SocialAccountDetailsStore.state === "ready"
        ? SocialAccountDetailsStore.recordFor(identityId) : null
    readonly property var knownServices: IdentityPolicy.APP_IDS.concat(
        storedRecord && storedRecord.accounts
        ? Object.keys(storedRecord.accounts).filter(function(id) {
              return IdentityPolicy.APP_IDS.indexOf(id) === -1;
          }) : [])
    readonly property var filteredServices: knownServices.filter(function(id) {
        return id.toLowerCase().indexOf(serviceFilter.text.trim().toLowerCase()) >= 0;
    })
    readonly property var accounts:
        canEdit && selectedServiceId !== ""
        ? SocialAccountDetailsStore.accountNamesFor(identityId, selectedServiceId) : []
    readonly property var selectedAccount: accounts.find(function(entry) {
        return entry.id === selectedAccountId;
    }) || null
    implicitHeight: editorColumn.implicitHeight

    function chooseService(serviceId) {
        selectedServiceId = serviceId;
        selectedAccountId = "";
        confirmRemoveId = "";
        labelField.text = "";
        servicePickerOpen = false;
        serviceFilter.text = "";
        feedback = "";
    }

    function chooseAccount(entry) {
        selectedAccountId = entry.id;
        confirmRemoveId = "";
        labelField.text = entry.label;
        feedback = "";
    }

    function resetEditor() {
        selectedServiceId = "";
        selectedAccountId = "";
        confirmRemoveId = "";
        servicePickerOpen = false;
        labelField.text = "";
        serviceFilter.text = "";
        feedback = "";
    }

    onIdentityIdChanged: Qt.callLater(function() {
        accountEditor.resetEditor();
    })

    function saveAccountName() {
        const targetId = identityId;
        const serviceId = selectedServiceId;
        const accountId = selectedAccountId;
        const label = labelField.text.trim();
        if (!canEdit || serviceId === "" || !label || pendingAction !== "")
            return;
        const ok = accountId === ""
            ? SocialAccountDetailsStore.addAccountName(targetId, serviceId, label)
            : selectedAccount
            ? SocialAccountDetailsStore.renameAccountName(
                targetId, serviceId, accountId, label)
            : false;
        if (ok) {
            pendingAction = accountId === "" ? "ADD" : "RENAME";
            pendingIdentityId = targetId;
            feedback = "SAVING ACCOUNT LABEL...";
        } else {
            feedback = SocialAccountDetailsStore.errorCode || "SAVE NOT AVAILABLE";
        }
    }

    function removeAccountName() {
        if (!canEdit || !selectedAccount || pendingAction !== "")
            return;
        if (confirmRemoveId !== selectedAccountId) {
            confirmRemoveId = selectedAccountId;
            feedback = "CONFIRM REMOVE // LABEL ONLY";
            return;
        }
        const targetId = identityId;
        if (SocialAccountDetailsStore.removeAccountName(
                targetId, selectedServiceId, selectedAccountId)) {
            pendingAction = "REMOVE";
            pendingIdentityId = targetId;
            confirmRemoveId = "";
            feedback = "REMOVING LABEL...";
        } else {
            feedback = SocialAccountDetailsStore.errorCode || "REMOVE NOT AVAILABLE";
        }
    }

    Connections {
        target: SocialAccountDetailsStore
        function onStateChanged() {
            if (accountEditor.pendingAction === "")
                return;
            const action = accountEditor.pendingAction;
            if (SocialAccountDetailsStore.state === "ready") {
                accountEditor.pendingAction = "";
                if (accountEditor.pendingIdentityId === accountEditor.identityId) {
                    accountEditor.selectedAccountId = "";
                    labelField.text = "";
                    accountEditor.confirmRemoveId = "";
                    accountEditor.feedback = action + " SAVED // LOCAL LABEL";
                }
                accountEditor.pendingIdentityId = "";
            } else if (SocialAccountDetailsStore.state === "error") {
                accountEditor.pendingAction = "";
                accountEditor.pendingIdentityId = "";
                accountEditor.feedback = "LABEL SAVE FAILED // "
                    + (SocialAccountDetailsStore.errorCode || "STORAGE ERROR");
            }
        }
    }

    Column {
        id: editorColumn
        width: parent.width
        spacing: 9

        GohuText {
            width: parent.width
            text: "LINKED ACCOUNT NAMES"
            color: Colors.cyan
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "LOCAL LABELS ONLY // NOT PROVIDER SIGN-IN STATUS"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "SAVED SERVICES // "
                  + (accountEditor.storedRecord && accountEditor.storedRecord.accounts
                     ? Object.keys(accountEditor.storedRecord.accounts).length : 0)
            font.pixelSize: 9
        }

        Repeater {
            model: accountEditor.storedRecord && accountEditor.storedRecord.accounts
                   ? Object.keys(accountEditor.storedRecord.accounts) : []
            delegate: ActionButton {
                required property var modelData
                width: editorColumn.width
                height: 29
                label: modelData.toUpperCase() + " // "
                       + SocialAccountDetailsStore.accountNamesFor(
                           accountEditor.identityId, modelData).length
                labelPixelSize: 9
                accentColor: Colors.cyan
                selected: accountEditor.selectedServiceId === modelData
                onClicked: accountEditor.chooseService(modelData)
            }
        }

        ActionButton {
            width: parent.width
            height: 33
            label: accountEditor.servicePickerOpen ? "CLOSE SERVICES"
                   : accountEditor.selectedServiceId
                   ? "SERVICE // " + accountEditor.selectedServiceId.toUpperCase()
                   : "CHOOSE SERVICE"
            labelPixelSize: 9
            accentColor: Colors.orange
            selected: accountEditor.servicePickerOpen
            onClicked: accountEditor.servicePickerOpen =
                !accountEditor.servicePickerOpen
        }
        Column {
            width: parent.width
            spacing: 5
            visible: accountEditor.servicePickerOpen

            CpuPlusIdField {
                id: serviceFilter
                width: parent.width
                height: 34
                maxLength: 40
                placeholder: "FILTER SERVICES"
            }
            Rectangle {
                width: parent.width
                height: 178
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Flickable {
                    id: serviceScroll
                    anchors.fill: parent
                    anchors.margins: 4
                    contentWidth: width
                    contentHeight: serviceColumn.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    Column {
                        id: serviceColumn
                        width: parent.width
                        spacing: 3
                        Repeater {
                            model: accountEditor.filteredServices
                            delegate: ActionButton {
                                required property var modelData
                                width: serviceColumn.width
                                height: 29
                                label: modelData.toUpperCase()
                                labelPixelSize: 9
                                contentPadding: 3
                                accentColor: Colors.cyan
                                selected: accountEditor.selectedServiceId === modelData
                                onClicked: accountEditor.chooseService(modelData)
                            }
                        }
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 8
            visible: accountEditor.selectedServiceId !== ""

            QuietText {
                width: parent.width
                text: "SAVED NAMES // " + accountEditor.accounts.length
                color: Colors.cyan
                font.pixelSize: 10
            }
            Repeater {
                model: accountEditor.accounts
                delegate: ActionButton {
                    required property var modelData
                    width: parent.width
                    height: 32
                    label: modelData.label
                    labelPixelSize: 10
                    selected: accountEditor.selectedAccountId === modelData.id
                    accentColor: Colors.cyan
                    onClicked: accountEditor.chooseAccount(modelData)
                }
            }
            QuietText {
                width: parent.width
                visible: accountEditor.accounts.length === 0
                text: "NO ACCOUNT NAMES SAVED FOR THIS SERVICE"
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: accountEditor.selectedAccountId
                      ? "EDIT SELECTED NAME" : "+ ACCOUNT NAME"
                color: accountEditor.selectedAccountId ? Colors.cyan : Colors.magenta
                font.pixelSize: 10
            }
            CpuPlusIdField {
                id: labelField
                width: parent.width
                height: 36
                maxLength: 48
                placeholder: "LOCAL ACCOUNT LABEL"
            }
            ActionButton {
                width: parent.width
                height: 34
                label: accountEditor.selectedAccountId
                       ? "SAVE ACCOUNT NAME" : "+ ACCOUNT NAME"
                labelPixelSize: 9
                accentColor: accountEditor.selectedAccountId
                             ? Colors.green : Colors.magenta
                interactive: accountEditor.canEdit && accountEditor.pendingAction === ""
                             && labelField.text.trim().length > 0
                onClicked: accountEditor.saveAccountName()
            }
            ActionButton {
                width: parent.width
                height: 30
                label: "CANCEL ACCOUNT EDIT"
                labelPixelSize: 9
                accentColor: Colors.white
                interactive: accountEditor.pendingAction === ""
                onClicked: {
                    accountEditor.selectedAccountId = "";
                    accountEditor.confirmRemoveId = "";
                    labelField.text = "";
                    accountEditor.feedback = "";
                }
            }
            ActionButton {
                width: parent.width
                height: 34
                visible: accountEditor.selectedAccountId !== ""
                label: accountEditor.confirmRemoveId === accountEditor.selectedAccountId
                       ? "CONFIRM REMOVE LABEL" : "REMOVE ACCOUNT NAME"
                labelPixelSize: 9
                destructive: true
                accentColor: Colors.red
                interactive: accountEditor.canEdit && accountEditor.pendingAction === ""
                onClicked: accountEditor.removeAccountName()
            }
        }
        ActionButton {
            width: parent.width
            height: 30
            visible: SocialAccountDetailsStore.state === "error"
            label: "RELOAD ACCOUNT NAMES"
            labelPixelSize: 9
            accentColor: Colors.yellow
            onClicked: SocialAccountDetailsStore.refresh()
        }
        QuietText {
            width: parent.width
            visible: accountEditor.feedback !== ""
                     || SocialAccountDetailsStore.state === "error"
            text: accountEditor.feedback !== "" ? accountEditor.feedback
                  : (SocialAccountDetailsStore.errorCode || "ACCOUNT STORAGE UNAVAILABLE")
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
