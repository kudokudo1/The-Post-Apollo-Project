import QtQuick
import "../../components"

// Personal iPhone contact detail *presentation* only. Contact records have
// already been validated by BlueFerry's authorized read-only PHONE snapshot.
// This component does not fetch, persist, merge or send any personal data.
Rectangle {
    id: detail
    property var contact: null
    property bool canPrepareCall: false
    signal callRequested()
    signal messageRequested()

    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    clip: true
    visible: contact !== null

    Flickable {
        id: detailScroll
        anchors.fill: parent
        anchors.margins: 14
        clip: true
        contentWidth: width
        contentHeight: detailColumn.implicitHeight + 24
        flickableDirection: Flickable.VerticalFlick

        Column {
            id: detailColumn
            width: Math.max(0, detailScroll.width - 8)
            spacing: 12

            Text {
                width: parent.width
                text: "IPHONE CONTACT // PERSONAL // READ ONLY"
                color: Colors.cyan
                textFormat: Text.PlainText
                font.pixelSize: 11
                font.bold: true
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: detail.contact ? String(detail.contact.displayNameInProfile || "Unnamed contact") : ""
                color: Colors.orange
                textFormat: Text.PlainText
                font.pixelSize: 19
                font.bold: true
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }

            Text {
                width: parent.width
                text: "ORGANIZATION"
                color: Colors.cyan
                font.pixelSize: 10
            }
            Text {
                width: parent.width
                text: detail.contact && detail.contact.organization
                      ? String(detail.contact.organization) : "Not provided"
                color: Colors.white
                textFormat: Text.PlainText
                font.pixelSize: 12
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
            Text {
                width: parent.width
                text: "PRIMARY CONTACT"
                color: Colors.cyan
                font.pixelSize: 10
            }
            Text {
                width: parent.width
                text: detail.contact && detail.contact.primary
                      ? String(detail.contact.primary) : "Not provided"
                color: Colors.white
                textFormat: Text.PlainText
                font.pixelSize: 12
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
            Row {
                width: parent.width
                spacing: 16
                Text {
                    text: "PHONES: " + (detail.contact
                          ? Number(detail.contact.phoneCount || 0) : 0)
                    textFormat: Text.PlainText
                    color: Colors.cyan
                    font.pixelSize: 11
                }
                Text {
                    text: "EMAILS: " + (detail.contact
                          ? Number(detail.contact.emailCount || 0) : 0)
                    textFormat: Text.PlainText
                    color: Colors.cyan
                    font.pixelSize: 11
                }
            }
            Text {
                width: parent.width
                text: detail.contact && detail.contact.hasPhoto
                      ? "PHOTO REPORTED // Image not included in this snapshot."
                      : "NO PHOTO INCLUDED IN THIS SNAPSHOT"
                color: Colors.white
                opacity: 0.75
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }
            Text {
                width: parent.width
                text: "CONTACT ACTIONS"
                color: Colors.orange
                font.pixelSize: 12
                font.bold: true
            }
            Row {
                id: contactActions
                width: parent.width
                spacing: 6
                ActionButton {
                    width: Math.max(0, (contactActions.width - 12) / 3)
                    height: 34
                    label: "CALL"
                    labelPixelSize: 10
                    labelMinimumPixelSize: 8
                    accentColor: Colors.magenta
                    interactive: detail.contact !== null && detail.canPrepareCall
                    onTriggered: detail.callRequested()
                }
                ActionButton {
                    width: Math.max(0, (contactActions.width - 12) / 3)
                    height: 34
                    label: "MESSAGE"
                    labelPixelSize: 10
                    labelMinimumPixelSize: 8
                    accentColor: Colors.cyan
                    interactive: detail.contact !== null
                    onTriggered: detail.messageRequested()
                }
                ActionButton {
                    width: Math.max(0, (contactActions.width - 12) / 3)
                    height: 34
                    label: "FACETIME"
                    labelPixelSize: 9
                    labelMinimumPixelSize: 8
                    accentColor: Colors.orange
                    interactive: false // No BlueFerry FaceTime transport.
                }
            }
            Text {
                width: parent.width
                text: detail.canPrepareCall
                      ? "CALL opens the existing PHONE dialer with this number. You must review and confirm dialing."
                      : "CALL unavailable: this contact has no supported dialable primary phone number."
                color: Colors.orange
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "MESSAGE opens your existing conversations. PHONE cannot safely link a contact card to a thread or start a new SMS yet; sending remains disabled."
                color: Colors.cyan
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "FACETIME unavailable: the Linux BlueFerry HFP calling path does not provide FaceTime."
                color: Colors.orange
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "This read-only snapshot shows only the provided primary value and contact counts. Additional phone numbers and emails are not included."
                color: Colors.white
                opacity: 0.70
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }
    }

    NeonScrollBar {
        flickable: detailScroll
        handleStyle: "star"
        visible: detail.visible && scrollable
    }
}
