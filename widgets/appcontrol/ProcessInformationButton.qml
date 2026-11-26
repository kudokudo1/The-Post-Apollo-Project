import QtQuick
import "../../components"

// Same visual recipe as CPU++ CAP / DETAILS information controls.
ActionButton {
    id: root
    width: 24
    height: 22
    label: "i"
    contentPadding: 2
    accentColor: Colors.yellow
    idleForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    selectedForegroundColor: Colors.magenta
    idleContentGlowColor: Colors.yellow
    hoverContentGlowColor: Colors.yellow
    selectedContentGlowColor: Colors.magenta
    contentGlowIdleOpacity: 0.85
    acceptedButtons: Qt.LeftButton
    keyboardActivationSignal: "leftClicked"
    Accessible.name: "Process information"
}
