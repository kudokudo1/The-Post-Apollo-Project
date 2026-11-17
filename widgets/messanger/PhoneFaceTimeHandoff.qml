import QtQuick
import "../../components"
import "PhoneFaceTimeLinks.js" as FaceTimeLinks

// Shared, user-initiated FaceTime Audio/Video handoff in existing PHONE views.
// This never opens facetime: schemes on Linux and never claims a native call.
// Apple-device URI is selectable text only. The only external action is an
// explicitly reviewed, exact-origin FaceTime HTTPS invitation.
Rectangle {
    id: handoff
    property string mode: "video"
    property var contact: null
    property string reviewedInvite: ""
    property string result: "IDLE"
    signal closeRequested()

    width: parent ? parent.width : 320
    height: handoffColumn.implicitHeight + 24
    color: Colors.dark
    border.width: 1
    border.color: mode === "audio" ? Colors.cyan : Colors.orange
    clip: true

    function clear() {
        reviewedInvite = "";
        result = "IDLE";
        // Mode/contact initialization may precede child creation in QML.
        if (inviteInput)
            inviteInput.text = "";
    }

    function reviewInvite() {
        if (!visible)
            return;
        reviewedInvite = FaceTimeLinks.normalizeInvite(inviteInput.text);
        result = reviewedInvite !== "" ? "REVIEW" : "INVALID";
    }

    function openReviewedInvite() {
        if (!visible || result !== "REVIEW"
                || reviewedInvite === ""
                || reviewedInvite !== FaceTimeLinks.normalizeInvite(inviteInput.text)) {
            reviewedInvite = "";
            result = "INVALID";
            return;
        }
        // Only this second explicit click may hand off the validated HTTPS
        // link to the default browser. No WebRTC join is implied by success.
        var selected = reviewedInvite;
        reviewedInvite = "";
        result = Qt.openUrlExternally(selected) ? "BROWSER_REQUESTED" : "OPEN_FAILED";
    }

    onModeChanged: clear()
    onContactChanged: clear()
    onVisibleChanged: {
        if (!visible)
            clear();
    }

    Column {
        id: handoffColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 9

        Text {
            width: parent.width
            text: handoff.mode === "audio" ? "FACETIME AUDIO // HANDOFF" : "FACETIME VIDEO // HANDOFF"
            color: handoff.mode === "audio" ? Colors.cyan : Colors.orange
            font.bold: true
            font.pixelSize: 12
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "NATIVE LINUX FACETIME // NOT CONNECTED"
            color: Colors.orange
            font.pixelSize: 11
            font.bold: true
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: FaceTimeLinks.supportMessage(handoff.mode)
            color: Colors.white
            font.pixelSize: 11
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "JOIN AN INVITED FACETIME CALL // WEB"
            color: Colors.cyan
            font.pixelSize: 11
            font.bold: true
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 37
            border.width: 1
            border.color: Colors.magenta
            color: Colors.black
            TextInput {
                id: inviteInput
                anchors.fill: parent
                anchors.margins: 7
                color: Colors.magenta
                font.pixelSize: 11
                maximumLength: 2048
                selectByMouse: true
                clip: true
                cursorDelegate: Rectangle {
                    width: 2
                    height: inviteInput.font.pixelSize + 2
                    color: Colors.orange
                }
                onTextChanged: {
                    handoff.reviewedInvite = "";
                    handoff.result = "IDLE";
                }
            }
            Text {
                anchors.fill: parent
                anchors.margins: 7
                visible: inviteInput.text.length === 0
                text: "Paste https://facetime.apple.com/join#..."
                color: Colors.white
                opacity: 0.55
                font.pixelSize: 10
                verticalAlignment: Text.AlignVCenter
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
        }
        Row {
            width: parent.width
            spacing: 8
            ActionButton {
                width: Math.max(0, (handoffColumn.width - 8) / 2)
                height: 34
                label: "REVIEW INVITE"
                labelPixelSize: 10
                accentColor: Colors.magenta
                interactive: inviteInput.text.length > 0
                onTriggered: handoff.reviewInvite()
            }
            ActionButton {
                width: Math.max(0, (handoffColumn.width - 8) / 2)
                height: 34
                label: "OPEN INVITE"
                labelPixelSize: 10
                accentColor: Colors.green
                interactive: handoff.result === "REVIEW"
                             && handoff.reviewedInvite !== ""
                             && handoff.reviewedInvite === FaceTimeLinks.normalizeInvite(inviteInput.text)
                onTriggered: handoff.openReviewedInvite()
            }
        }
        Text {
            width: parent.width
            text: handoff.result === "REVIEW"
                  ? "APPLE INVITE REVIEWED // Opening sends the invitation token to the browser. Join only if you trust its sender."
                  : handoff.result === "INVALID"
                    ? "INVALID INVITE // Paste a complete HTTPS FaceTime invitation from facetime.apple.com. No browser opened."
                    : handoff.result === "BROWSER_REQUESTED"
                      ? "BROWSER OPEN REQUESTED // Join in Chrome or Edge; browser access, microphone, camera and host approval are separate."
                      : handoff.result === "OPEN_FAILED"
                        ? "NO BROWSER HANDOFF // No external application accepted the request."
                        : "FaceTime invite required. Chrome or Edge recommended; FaceTime Audio cannot be started directly from Linux."
            color: handoff.result === "INVALID" || handoff.result === "OPEN_FAILED"
                   ? Colors.orange : Colors.white
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "APPLE-DEVICE CONTACT HANDOFF // NO LINUX DIAL"
            color: Colors.cyan
            font.bold: true
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 32
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            TextInput {
                id: appleDeviceLink
                anchors.fill: parent
                anchors.margins: 6
                text: FaceTimeLinks.appleDeviceLink(handoff.mode, handoff.contact)
                color: Colors.cyan
                font.pixelSize: 11
                readOnly: true
                selectByMouse: true
                clip: true
            }
        }
        Text {
            width: parent.width
            text: appleDeviceLink.text !== ""
                  ? "Optional: select and copy the link above for use on an Apple device. It does not place a call from this Linux desktop. Verify the person on your iPhone."
                  : "Select an authorized contact with a phone number or email to prepare an Apple-device link; otherwise start the call on your iPhone."
            color: Colors.white
            opacity: 0.86
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: Math.min(130, handoffColumn.width)
            height: 31
            label: "CLOSE FACETIME"
            labelPixelSize: 10
            accentColor: Colors.orange
            onTriggered: handoff.closeRequested()
        }
    }
}
