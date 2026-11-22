import QtQuick

// Reusable ASK/SEND composer control. No service calls or implicit submit.
// The hosting view decides when SEND means stop+submit, and whether a
// secondary/right-click action is permitted by its own authorization policy.
ActionButton {
    id: askSendButton

    property bool enabledAction: false
    property bool recording: false
    property bool processing: false
    property bool allowSecondaryAction: false
    property string askLabel: "ASK"
    property string sendLabel: "SEND"
    property string processingLabel: "..."
    property color idleAccent: Colors.green
    property color recordingAccent: Colors.magenta
    property real restingGlowOpacity: 0.30

    signal primaryRequested()
    signal secondaryRequested()

    width: 86
    height: 42
    radius: 0
    showLabel: false
    acceptedButtons: allowSecondaryAction
        ? (Qt.LeftButton | Qt.RightButton) : Qt.LeftButton
    available: enabledAction
    unavailableOpacity: 1.0

    Accessible.role: Accessible.Button
    Accessible.name: processing ? "Sending unavailable while transcribing"
                     : recording ? sendLabel : askLabel

    idleFillColor: Colors.dark
    hoverFillColor: Colors.dark
    pressedFillColor: Colors.black
    selectedFillColor: Colors.dark

    idleForegroundColor: recording ? recordingAccent : idleAccent
    hoverForegroundColor: recording ? recordingAccent : Colors.orange
    pressedForegroundColor: recording ? recordingAccent : Colors.orange
    selectedForegroundColor: recordingAccent

    idleBorderColor: recording ? recordingAccent : idleAccent
    hoverBorderColor: recording ? recordingAccent : Colors.orange
    pressedBorderColor: recording ? recordingAccent : Colors.orange
    selectedBorderColor: recordingAccent
    idleBorderWidth: 1
    hoverBorderWidth: 2
    pressedBorderWidth: 2

    softGlowEnabled: true
    softGlowSpread: 4
    idleSoftGlowColor: recording ? recordingAccent : idleAccent
    hoverSoftGlowColor: recording ? recordingAccent : Colors.orange
    pressedSoftGlowColor: recording ? recordingAccent : Colors.orange
    softGlowIdleOpacity: enabledAction ? restingGlowOpacity : 0.12
    softGlowHoverOpacity: 0.48
    softGlowPressedOpacity: 0.48

    // Historical Reception and Intercom SEND labels have no separate text
    // halo; the shared ActionButton supplies the perimeter only.
    contentGlowEnabled: false
    wideGlowEnabled: false

    GohuText {
        id: askSendText
        anchors.centerIn: parent
        text: askSendButton.processing ? askSendButton.processingLabel
            : askSendButton.recording ? askSendButton.sendLabel
            : askSendButton.askLabel
        textFormat: Text.PlainText
        font.pixelSize: 11
        opacity: askSendButton.enabledAction ? 1.0 : 0.34
        color: askSendButton.foregroundColor
    }

    onLeftClicked: primaryRequested()
    onRightClicked: {
        if (allowSecondaryAction)
            secondaryRequested();
    }
}
