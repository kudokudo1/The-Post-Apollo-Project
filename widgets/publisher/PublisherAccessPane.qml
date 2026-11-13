import QtQuick
import QtQuick.Controls
import qs.services.publisher
import qs.services.social
import "../../services/publisher/PublisherAccessIntentPolicy.js" as AccessPolicy
import "../../components"

// P1.5 // Local account-specific access REQUESTS, never authorizations.
// No QML state, selector, saved alias or check-box grants publishing permission.
// No credential exchange, OAuth or outgoing provider request exists here.
Rectangle {
    id: access
    color: Colors.black
    clip: true

    property string feedback: "PUBLISHING ACCESS DISABLED // NO TRUSTED BROKER"
    property string withdrawArmedId: ""
    readonly property var storeSnapshot: PublisherAccessIntentStore.snapshot
    readonly property var identitySnapshot: SocialIdentityStore.snapshot
    readonly property string currentIdentityId:
        identitySnapshot.writable === true ? identitySnapshot.activeId : ""
    readonly property string currentIdentityName:
        currentIdentityId !== "" ? identitySnapshot.activeName : "NOT AVAILABLE"
    readonly property var availableProviders: AccessPolicy.providerIds()
    readonly property var availableScopes: AccessPolicy.scopes(providerChoice.currentText)
    readonly property var identityIntents: storeSnapshot.intents.filter(function(item) {
        return item.identityId === currentIdentityId;
    })

    function submit() {
        if (currentIdentityId === "") {
            feedback = "IDENTITY UNAVAILABLE // NO REQUEST SAVED";
            return;
        }
        var ok = PublisherAccessIntentStore.requestAccess(
            currentIdentityId, contextChoice.currentText,
            providerChoice.currentText, accountAlias.text.trim(),
            scopeChoice.currentText);
        feedback = ok ? "REQUEST SAVE ADMITTED // NOT AUTHORIZED"
                      : "REQUEST REFUSED // " + PublisherAccessIntentStore.actionError;
    }
    function withdraw(item) {
        if (!item || item.status !== "requested") return;
        if (withdrawArmedId !== item.id) {
            withdrawArmedId = item.id;
            feedback = "WITHDRAW REQUEST " + item.id + "? CLICK AGAIN";
            return;
        }
        withdrawArmedId = "";
        var ok = PublisherAccessIntentStore.withdrawRequest(item.id);
        feedback = ok ? "WITHDRAW SAVE ADMITTED // AWAIT CONFIRMATION"
                      : "WITHDRAW REFUSED // " + PublisherAccessIntentStore.actionError;
    }
    onCurrentIdentityIdChanged: withdrawArmedId = ""
    onVisibleChanged: if (!visible) withdrawArmedId = ""

    Connections {
        target: PublisherAccessIntentStore
        function onActionCompleted(action,intentId) {
            if (!access.visible) return;
            access.withdrawArmedId = "";
            access.feedback = action.toUpperCase() + " SAVED // " + intentId
                              + " // ZERO PUBLISHING GRANTS";
        }
        function onStorageStateChanged() {
            if (PublisherAccessIntentStore.storageState === "error"
                    || PublisherAccessIntentStore.storageState === "unsupported") {
                access.feedback = "LOCAL ACCESS INTENTS BLOCKED // "
                                  + PublisherAccessIntentStore.errorCode;
            }
        }
    }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: fields.implicitHeight + 16
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: fields
            width: scroll.width
            spacing: 9

            Text {
                width: parent.width
                color: Colors.white
                font.bold: true
                font.pixelSize: 14
                text: "ACCESS // ACCOUNT-SPECIFIC REQUESTS"
            }
            Text {
                width: parent.width
                color: Colors.orange
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                text: "HOST NOT CONNECTED // GRANTS 0 // PUBLISHING DENIED. "
                    + "Saving an account name or request does NOT grant access."
            }
            Text {
                width: parent.width
                font.pixelSize: 12
                color: Colors.cyan
                text: "SOCIAL LAYOUT // " + currentIdentityName
                      + " // " + (currentIdentityId || "NOT AVAILABLE")
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                font.pixelSize: 10
                color: Colors.white
                wrapMode: Text.WordWrap
                text: "This local identity is only an organization label. "
                      + "The account below is an unverified display alias."
            }
            Row {
                width: parent.width
                height: 36
                spacing: 6
                ComboBox {
                    id: contextChoice
                    width: (parent.width - parent.spacing) / 2
                    height: 35
                    model: ["personal","organization"]
                }
                ComboBox {
                    id: providerChoice
                    width: (parent.width - parent.spacing) / 2
                    height: 35
                    model: access.availableProviders
                }
            }
            TextField {
                id: accountAlias
                width: parent.width
                height: 36
                placeholderText: "ACCOUNT ALIAS // NOT USERNAME OR PASSWORD"
                placeholderTextColor: Colors.cyan
                color: Colors.white
                selectByMouse: true
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: accountAlias.activeFocus ? Colors.magenta : Colors.cyan
                }
            }
            Text {
                width: parent.width
                color: Colors.cyan
                font.pixelSize: 11
                text: "REQUESTED OPERATION // ONE SCOPE PER RECORD"
            }
            ComboBox {
                id: scopeChoice
                width: parent.width
                height: 36
                model: access.availableScopes
                onModelChanged: currentIndex = 0
            }
            ActionButton {
                width: parent.width
                height: 36
                label: "SAVE REQUEST // NO AUTHORIZATION"
                accentColor: Colors.magenta
                available: access.currentIdentityId !== ""
                           && access.storeSnapshot.writable === true
                           && accountAlias.text.trim() !== ""
                           && scopeChoice.currentText !== ""
                onTriggered: access.submit()
            }
            Row {
                width: parent.width
                height: 36
                spacing: 6
                Text {
                    width: parent.width * 0.64
                    height: 33
                    font.pixelSize: 10
                    color: Colors.white
                    verticalAlignment: Text.AlignVCenter
                    text: "LOCAL REQUESTS // " + access.identityIntents.length
                }
                ActionButton {
                    width: parent.width * 0.36 - parent.spacing
                    height: 33
                    label: "RELOAD"
                    accentColor: Colors.cyan
                    available: PublisherAccessIntentStore.storageState !== "saving"
                    onTriggered: {
                        if (PublisherAccessIntentStore.reloadFromDisk())
                            access.feedback = "RELOADING REQUESTS";
                        else
                            access.feedback = "RELOAD REFUSED";
                    }
                }
            }
            Repeater {
                model: access.identityIntents
                Rectangle {
                    required property var modelData
                    width: fields.width
                    height: 94
                    color: Colors.black
                    border.width: 1
                    border.color: modelData.status === "requested"
                                  ? Colors.cyan : Colors.orange
                    Column {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 4
                        Text {
                            width: parent.width
                            font.pixelSize: 11
                            color: Colors.white
                            text: modelData.id + " // "
                                  + modelData.provider.toUpperCase()
                                  + " // " + modelData.accountAlias
                            elide: Text.ElideRight
                        }
                        Text {
                            width: parent.width
                            font.pixelSize: 10
                            color: Colors.cyan
                            text: modelData.context.toUpperCase()
                                  + " // " + modelData.scope.toUpperCase()
                                  + " // " + modelData.status.toUpperCase()
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            width: parent.width
                            height: 27
                            label: access.withdrawArmedId === modelData.id
                                   ? "CONFIRM WITHDRAW"
                                   : modelData.status === "requested"
                                     ? "WITHDRAW REQUEST" : "WITHDRAWN"
                            accentColor: Colors.orange
                            available: modelData.status === "requested"
                                       && access.storeSnapshot.writable === true
                            onTriggered: access.withdraw(modelData)
                        }
                    }
                }
            }
            Text {
                width: parent.width
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                text: access.feedback
            }
            Text {
                width: parent.width
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                text: "FUTURE: verified host-owned account consent, signed calling "
                      + "application, expiry, scope enforcement and revocation. "
                      + "Neither this view nor existing Social sessions satisfy those checks."
            }
        }
    }
}
