import QtQuick

// Reusable voice-to-text COMPOSER CONTROL, not a microphone engine.
// Hospital Reception/Intercom (or another owner) supplies all state and
// handles toggleRequested; this component cannot start capture by itself.
ActionButton {
    id: voiceButton

    property bool backendReady: false
    property bool busy: false
    property bool processing: false
    property color idleAccent: Colors.omnitrix
    property string voiceGlyph: "🗣︎"
    // Reception historically glowed its speech glyph; Intercom did not.
    property bool glyphGlowEnabled: false

    signal toggleRequested()

    width: 42
    height: 42
    radius: 0
    showLabel: false
    acceptedButtons: Qt.LeftButton
    available: !processing
    selected: busy
    // A voice service may remain busy while a stop is processing. Preserve
    // its active visual state even when clicks are disabled.
    unavailableOpacity: 1.0
    opacity: busy || backendReady ? 1.0 : 0.48

    Accessible.role: Accessible.Button
    Accessible.name: processing ? "Voice-to-text processing"
                     : busy ? "Stop voice-to-text recording"
                     : "Start voice-to-text recording"

    idleFillColor: Colors.dark
    hoverFillColor: Colors.dark
    pressedFillColor: Colors.dark
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: Colors.yellow

    idleForegroundColor: idleAccent
    hoverForegroundColor: Colors.orange
    pressedForegroundColor: busy ? Colors.magenta : Colors.orange
    selectedForegroundColor: Colors.magenta
    keyboardSelectedForegroundColor: Colors.magenta

    idleBorderColor: idleAccent
    hoverBorderColor: Colors.orange
    pressedBorderColor: busy ? Colors.magenta : Colors.orange
    selectedBorderColor: Colors.magenta
    keyboardSelectedBorderColor: Colors.magenta
    idleBorderWidth: 1
    hoverBorderWidth: 2
    pressedBorderWidth: 2
    selectedBorderWidth: 2
    keyboardSelectedBorderWidth: 2

    softGlowEnabled: true
    softGlowSpread: 4
    idleSoftGlowColor: idleAccent
    hoverSoftGlowColor: Colors.orange
    pressedSoftGlowColor: busy ? Colors.magenta : Colors.orange
    selectedSoftGlowColor: Colors.magenta
    keyboardSelectedSoftGlowColor: Colors.magenta
    softGlowIdleOpacity: 0.34
    softGlowHoverOpacity: 0.48
    softGlowPressedOpacity: 0.48
    softGlowSelectedOpacity: 0.55
    softGlowKeyboardSelectedOpacity: 0.55

    wideGlowEnabled: false
    contentGlowEnabled: glyphGlowEnabled
    contentGlowSource: speechGlyph
    idleContentGlowColor: idleAccent
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: busy ? Colors.magenta : Colors.orange
    selectedContentGlowColor: Colors.magenta
    keyboardSelectedContentGlowColor: Colors.magenta
    contentGlowIdleOpacity: 0.54
    contentGlowHoverOpacity: 0.54
    contentGlowPressedOpacity: 0.54
    contentGlowSelectedOpacity: 0.54
    contentGlowKeyboardSelectedOpacity: 0.54

    GohuText {
        id: speechGlyph
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 1
        text: voiceButton.voiceGlyph
        textFormat: Text.PlainText
        font.pixelSize: 22
        color: voiceButton.foregroundColor
    }

    onLeftClicked: toggleRequested()
}
