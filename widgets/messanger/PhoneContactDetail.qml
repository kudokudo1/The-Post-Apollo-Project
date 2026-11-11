import QtQuick
import "../../components"

// Personal iPhone contact detail *presentation* only. Contact records have
// already been validated by BlueFerry's authorized read-only PHONE snapshot.
// This component does not fetch, persist, merge or send any personal data.
Rectangle {
    id: detail
    property var contact: null
    property bool canPrepareCall: false
    // P40: no installed signed host, C5 consent or authenticated encrypted
    // save response is available to QML. A read preference is not write grant.
    readonly property bool personalMetadataWritable: false
    readonly property string personalMetadataStatus:
        "UNAVAILABLE // VERIFIED CONTACT SAVE HOST REQUIRED"
    signal callRequested()
    signal messageRequested()
    signal callNumberRequested(string number)

    // Display-only eligibility. PHONE also revalidates against the selected
    // authorized contact before transferring a number to its gated CALLS UI.
    function canPrepareNumber(value) {
        if (typeof value !== "string")
            return false;
        var raw = value.trim();
        if (!/^[+]?[0-9 ()-]{3,32}$/.test(raw))
            return false;
        return /^[+]?[0-9]{3,18}$/.test(raw.replace(/[ ()-]/g, ""));
    }

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

            Row {
                id: contactHeader
                width: parent.width
                spacing: 8
                Text {
                    width: Math.max(0, contactHeader.width - 84)
                    text: "IPHONE CONTACT // PERSONAL // READ ONLY"
                    color: Colors.cyan
                    textFormat: Text.PlainText
                    font.pixelSize: 11
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: 76
                    height: 28
                    label: "EDIT"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    interactive: false // No authenticated local contact editor.
                }
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
                    width: Math.max(0, (contactActions.width - 18) / 4)
                    height: 34
                    label: "CALL"
                    labelPixelSize: 10
                    labelMinimumPixelSize: 8
                    accentColor: Colors.magenta
                    interactive: detail.contact !== null && detail.canPrepareCall
                    onTriggered: detail.callRequested()
                }
                ActionButton {
                    width: Math.max(0, (contactActions.width - 18) / 4)
                    height: 34
                    label: "MESSAGE"
                    labelPixelSize: 10
                    labelMinimumPixelSize: 8
                    accentColor: Colors.cyan
                    interactive: detail.contact !== null
                    onTriggered: detail.messageRequested()
                }
                ActionButton {
                    width: Math.max(0, (contactActions.width - 18) / 4)
                    height: 34
                    label: "FACETIME"
                    labelPixelSize: 9
                    labelMinimumPixelSize: 8
                    accentColor: Colors.orange
                    interactive: false // No BlueFerry FaceTime transport.
                }
                ActionButton {
                    width: Math.max(0, (contactActions.width - 18) / 4)
                    height: 34
                    label: "EMAIL"
                    labelPixelSize: 9
                    labelMinimumPixelSize: 8
                    accentColor: Colors.magenta
                    interactive: false // Email routing not connected.
                }
            }
            Text {
                width: parent.width
                text: "PERSONAL // FAVORITE"
                color: Colors.orange
                font.pixelSize: 12
                font.bold: true
            }
            Row {
                id: favoriteActions
                width: parent.width
                spacing: 8
                ActionButton {
                    width: Math.min(146, favoriteActions.width)
                    height: 34
                    label: "☆ FAVORITE"
                    labelPixelSize: 11
                    labelMinimumPixelSize: 9
                    accentColor: Colors.magenta
                    interactive: detail.personalMetadataWritable
                                 && detail.contact !== null
                    // Deliberately no onTriggered or invented saved state.
                }
                Text {
                    width: Math.max(0, favoriteActions.width - 154)
                    height: 34
                    verticalAlignment: Text.AlignVCenter
                    text: "NOT SAVED // UNAVAILABLE"
                    color: Colors.orange
                    textFormat: Text.PlainText
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
            Text {
                width: parent.width
                text: detail.personalMetadataStatus
                color: Colors.cyan
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "PERSONAL // NOTES"
                color: Colors.orange
                font.pixelSize: 12
                font.bold: true
            }
            Rectangle {
                id: localNotesPlaceholder
                width: parent.width
                height: 88
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta
                clip: true
                Text {
                    anchors.fill: parent
                    anchors.margins: 10
                    text: "NOTES UNAVAILABLE // Notes will appear only after the verified encrypted Personal save host is connected."
                    color: Colors.cyan
                    textFormat: Text.PlainText
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
            Row {
                id: personalNotesActions
                width: parent.width
                spacing: 8
                ActionButton {
                    width: Math.max(0, (personalNotesActions.width - 8) / 2)
                    height: 32
                    label: "EDIT NOTE"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    interactive: false // No note editor or verified save authority.
                }
                ActionButton {
                    width: Math.max(0, (personalNotesActions.width - 8) / 2)
                    height: 32
                    label: "DELETE NOTE"
                    labelPixelSize: 10
                    accentColor: Colors.red
                    destructive: true
                    interactive: false // No trusted vault deletion response.
                }
            }
            Text {
                width: parent.width
                text: "Favorites and notes have not been read or saved. The iPhone contact provider stays READ ONLY."
                color: Colors.white
                opacity: 0.75
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.magenta
            }
            Text {
                width: parent.width
                text: "SAVED PHONE NUMBERS"
                color: Colors.orange
                font.pixelSize: 12
                font.bold: true
            }
            Text {
                width: parent.width
                text: detail.contact && detail.contact.hasAddressDetails
                      ? (detail.contact.phoneNumbers.length === 0
                         ? "No phone numbers in this loaded contact card."
                         : "Number types were not provided by BlueFerry 0.9.1. All entries are UNLABELED.")
                      : "The connected contact provider returned counts only; individual numbers are not available in this snapshot."
                color: Colors.white
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: detail.contact && detail.contact.hasAddressDetails
                       ? detail.contact.phoneNumbers : []
                delegate: Rectangle {
                    id: phoneNumberEntry
                    required property var modelData
                    width: detailColumn.width
                    height: 75
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Text {
                        anchors.top: parent.top
                        anchors.topMargin: 7
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        text: "PHONE // UNLABELED"
                        color: Colors.magenta
                        textFormat: Text.PlainText
                        font.pixelSize: 10
                    }
                    Row {
                        id: dialRow
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 8
                        spacing: 6
                        Rectangle {
                            width: Math.max(0, dialRow.width - 98)
                            height: 32
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            clip: true
                            TextInput {
                                anchors.fill: parent
                                anchors.leftMargin: 7
                                anchors.rightMargin: 7
                                verticalAlignment: TextInput.AlignVCenter
                                text: String(phoneNumberEntry.modelData)
                                readOnly: true
                                selectByMouse: true
                                color: Colors.cyan
                                font.pixelSize: 11
                                clip: true
                            }
                        }
                        ActionButton {
                            width: 92
                            height: 32
                            label: "MAKE CALL"
                            labelPixelSize: 9
                            labelMinimumPixelSize: 8
                            accentColor: Colors.magenta
                            interactive: detail.contact !== null
                                         && detail.canPrepareNumber(phoneNumberEntry.modelData)
                            onTriggered: detail.callNumberRequested(String(phoneNumberEntry.modelData))
                        }
                    }
                }
            }
            Text {
                width: parent.width
                text: "SAVED EMAIL ADDRESSES"
                color: Colors.orange
                font.pixelSize: 12
                font.bold: true
            }
            Text {
                width: parent.width
                visible: !detail.contact || !detail.contact.hasAddressDetails
                         || detail.contact.emailAddresses.length === 0
                text: detail.contact && detail.contact.hasAddressDetails
                      ? "No email addresses in this loaded contact card."
                      : "The connected contact provider did not expose individual email addresses."
                color: Colors.white
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: detail.contact && detail.contact.hasAddressDetails
                       ? detail.contact.emailAddresses : []
                delegate: Rectangle {
                    id: emailAddressEntry
                    required property var modelData
                    width: detailColumn.width
                    height: 55
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Text {
                        anchors.top: parent.top
                        anchors.topMargin: 5
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        text: "EMAIL // UNLABELED"
                        color: Colors.magenta
                        textFormat: Text.PlainText
                        font.pixelSize: 10
                    }
                    TextInput {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 6
                        height: 25
                        text: String(emailAddressEntry.modelData)
                        readOnly: true
                        selectByMouse: true
                        color: Colors.cyan
                        font.pixelSize: 11
                        clip: true
                    }
                }
            }
            Text {
                width: parent.width
                text: detail.canPrepareCall
                      ? "CALL opens the existing PHONE dialer with the primary number. Every MAKE CALL also requires review and confirmation."
                      : "Primary CALL is unavailable without a dialable primary number. A valid MAKE CALL entry can still open the dialer."
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
                text: "FACETIME unavailable: Linux BlueFerry HFP does not provide FaceTime. EMAIL remains unavailable until a verified route exists."
                color: Colors.orange
                textFormat: Text.PlainText
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "Only numbers and emails returned in the currently approved, read-only iPhone cache are shown. The legacy provider supplies no labels. These ephemeral contact records are not saved as Post Apollo identities."
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
