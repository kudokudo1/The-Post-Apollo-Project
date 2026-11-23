import QtQuick
import "../components"
import "FinanceBankingOfficialHandoffPolicy.js" as Official

// Banking M4d: an explicit, two-click handoff to the verified provider
// homepage, never a provider action, sign-in, payment or transaction receipt.
// The user must navigate within the official service after opening it.
Item {
    id: handoff
    property string providerId: ""
    property string sectionId: ""
    property bool armed: false
    property string outcome: ""
    readonly property var target: Official.destination(providerId,sectionId)
    implicitHeight: content.implicitHeight

    function resetConfirmation() {
        armed=false;
        outcome="";
    }
    onProviderIdChanged: resetConfirmation()
    onSectionIdChanged: resetConfirmation()
    onVisibleChanged: {
        if(!visible)resetConfirmation();
    }
    function requestOpen() {
        const fresh=Official.destination(providerId,sectionId);
        if(!fresh.ok || !Official.canOpen(fresh,providerId,sectionId)) {
            resetConfirmation();
            outcome="HANDOFF REFUSED // NO APPROVED DESTINATION";
            return false;
        }
        if(!armed) {
            armed=true;
            outcome="CLICK CONFIRM TO OPEN THE PROVIDER HOMEPAGE IN YOUR BROWSER";
            return false;
        }
        // Disarm before calling a host operation. Never forward account data,
        // copied credentials, identity labels, transaction amounts or deep links.
        armed=false;
        const accepted=Qt.openUrlExternally(fresh.url);
        outcome=accepted
            ? "BROWSER OPEN REQUEST SENT // NO PROVIDER ACTION WAS PERFORMED"
            : "BROWSER HANDOFF WAS NOT ACCEPTED // NO PROVIDER ACTION WAS PERFORMED";
        return accepted;
    }

    Column {
        id: content
        width: handoff.width
        spacing: 5
        GohuText {
            width: parent.width
            text: handoff.target.ok
                ? "OFFICIAL PROVIDER HOMEPAGE // "+handoff.target.host
                : handoff.target.reason
            font.pixelSize: 10
            color: handoff.target.ok?Colors.cyan:Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "EXTERNAL BROWSER // NOT A DIRECT LINK TO THIS FEATURE // VERIFY THE DOMAIN BEFORE SIGN-IN"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: handoff.target.ok?30:0
            visible: handoff.target.ok
            label: handoff.armed
                ? "CONFIRM OPEN "+handoff.target.providerName.toUpperCase()
                : "OPEN "+handoff.target.providerName.toUpperCase()+" OFFICIAL SITE"
            labelPixelSize: 9
            accentColor: handoff.armed?Colors.orange:Colors.cyan
            onLeftClicked: handoff.requestOpen()
        }
        GohuText {
            width: parent.width
            visible: !!handoff.outcome
            text: handoff.outcome
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
