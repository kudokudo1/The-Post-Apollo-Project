import QtQuick
import Quickshell

// Syntagma // ordinary Hospital action adapter.
// Intentionally separate from selectors, main modes, record rows, and
// specialized safety-critical controls. The shared ActionButton owns
// interactions and glow layers; the owner still controls space allocation.
ActionButton {
    id: action

    // Compatibility for existing Hospital view actions.
    property color accent: Colors.cyan
    property bool enabledAction: true
    property bool selectedAction: false
    property string compactIcon: "·"
    property string miniIcon: compactIcon
    property string actionDescription: label

    readonly property real textBudget: Math.max(0, width - 12)
    readonly property bool fullLabelFits:
        labelMeasure.implicitWidth <= textBudget
    readonly property bool compactIconFits:
        iconMeasure.implicitWidth <= textBudget

    implicitHeight: 35
    height: 35
    available: enabledAction
    selected: selectedAction
    accentColor: accent
    showLabel: false
    contentItem.clip: true

    Accessible.role: Accessible.Button
    Accessible.name: actionDescription

    acceptedButtons: Qt.LeftButton
    idleFillColor: Colors.black
    hoverFillColor: Colors.yellow
    selectedFillColor: Colors.yellow
    keyboardSelectedFillColor: Colors.yellow
    pressedFillColor: destructive ? Colors.red : Colors.magenta

    readonly property color activeSemanticColor:
        accent === Colors.cyan ? Colors.orange : accent
    readonly property color legibleHoverColor:
        accent === Colors.yellow ? Colors.orange : activeSemanticColor

    idleForegroundColor: accent
    hoverForegroundColor: legibleHoverColor
    selectedForegroundColor: legibleHoverColor
    keyboardSelectedForegroundColor: legibleHoverColor
    pressedForegroundColor: Colors.black

    idleBorderColor: accent
    hoverBorderColor: activeSemanticColor
    selectedBorderColor: activeSemanticColor
    keyboardSelectedBorderColor: activeSemanticColor
    pressedBorderColor: destructive ? Colors.red : activeSemanticColor
    // The independent border-thickness decision remains deferred.
    idleBorderWidth: 1
    hoverBorderWidth: 1
    selectedBorderWidth: 1
    keyboardSelectedBorderWidth: 1
    pressedBorderWidth: 1

    contentGlowSource: actionText
    contentGlowEnabled: true
    idleContentGlowColor: accent
    hoverContentGlowColor: activeSemanticColor
    selectedContentGlowColor: activeSemanticColor
    keyboardSelectedContentGlowColor: activeSemanticColor
    pressedContentGlowColor: activeSemanticColor
    contentGlowIdleOpacity: 0.35
    contentGlowHoverOpacity: 0.75
    contentGlowSelectedOpacity: 0.75
    contentGlowKeyboardSelectedOpacity: 0.75
    contentGlowPressedOpacity: 1.0

    softGlowEnabled: true
    softGlowSpread: 3
    idleSoftGlowColor: accent
    hoverSoftGlowColor: activeSemanticColor
    selectedSoftGlowColor: activeSemanticColor
    keyboardSelectedSoftGlowColor: activeSemanticColor
    pressedSoftGlowColor: activeSemanticColor
    softGlowIdleOpacity: 0.25
    softGlowHoverOpacity: 0.55
    softGlowSelectedOpacity: 0.55
    softGlowKeyboardSelectedOpacity: 0.55
    softGlowPressedOpacity: 0.60

    // The wide halo is a rare opt-in, not a mandatory crowded-row effect.
    wideGlowEnabled: false

    GohuText {
        id: labelMeasure
        visible: false
        text: action.label
        font.pixelSize: 8
    }

    GohuText {
        id: iconMeasure
        visible: false
        text: action.compactIcon
        font.pixelSize: 12
    }

    GohuText {
        id: actionText
        anchors.centerIn: parent
        width: action.textBudget
        height: Math.max(0, action.height - 8)
        visible: width > 0
        text: action.fullLabelFits ? action.label
              : action.compactIconFits ? action.compactIcon
              : action.miniIcon
        font.pixelSize: action.fullLabelFits ? 11
                        : action.compactIconFits ? 12 : 9
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: action.fullLabelFits ? 8 : 7
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideNone
        color: action.foregroundColor
    }
}
