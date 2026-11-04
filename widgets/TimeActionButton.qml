import QtQuick
import "../components"

// Local Clock action recipe: preserve the shared ActionButton behavior while
// giving TIME controls white identity, SYNC yellow, and CANCEL red. A selected
// timezone is visibly "open": yellow center plus magenta lettering/halo.
ActionButton {
    id: timeAction

    property string actionRole: "time" // time | sync | cancel
    readonly property color roleColor:
        actionRole === "sync" ? Colors.yellow
        : actionRole === "cancel" ? Colors.red : Colors.white

    destructive: actionRole === "cancel"
    accentColor: roleColor
    trackLabelGlowLocally: true
    idleFillColor: Colors.black
    hoverFillColor: Colors.black
    pressedFillColor: Colors.black
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: selectedFillColor

    idleForegroundColor: roleColor
    hoverForegroundColor: roleColor
    pressedForegroundColor: roleColor
    selectedForegroundColor: Colors.magenta
    keyboardSelectedForegroundColor: Colors.magenta

    idleBorderColor: roleColor
    hoverBorderColor: roleColor
    pressedBorderColor: roleColor
    selectedBorderColor: Colors.magenta
    keyboardSelectedBorderColor: Colors.magenta

    idleContentGlowColor: roleColor
    hoverContentGlowColor: roleColor
    pressedContentGlowColor: roleColor
    selectedContentGlowColor: Colors.magenta
    keyboardSelectedContentGlowColor: Colors.magenta

    idleSoftGlowColor: roleColor
    hoverSoftGlowColor: roleColor
    pressedSoftGlowColor: roleColor
    selectedSoftGlowColor: Colors.magenta
    keyboardSelectedSoftGlowColor: Colors.magenta

    wideGlowEnabled: true
    idleWideGlowColor: roleColor
    hoverWideGlowColor: roleColor
    pressedWideGlowColor: roleColor
    selectedWideGlowColor: Colors.magenta
    keyboardSelectedWideGlowColor: Colors.magenta
    wideGlowIdleOpacity: 0.04
    wideGlowHoverOpacity: 0.08
    wideGlowSelectedOpacity: 0.14
}
