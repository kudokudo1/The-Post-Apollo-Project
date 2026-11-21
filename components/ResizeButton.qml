import QtQuick

// Ordinary window-chassis size-step arrows. Presentation/input only:
// consumers keep ownership of their actual size levels, window geometry,
// unsaved edits and keyboard focus. A request must not resize by itself.
//
// Visual and interaction states deliberately inherit ActionButton defaults;
// unlike CloseButton, no custom hover, pressed or glow recipes apply.
ActionButton {
    id: resizeButton

    // Supported direction values: "left", "up", "down", "right".
    // Left/down decrease; up/right increase.
    property string direction: "down"
    readonly property bool directionValid:
        direction === "left" || direction === "up"
        || direction === "down" || direction === "right"
    readonly property bool increasing:
        direction === "up" || direction === "right"
    readonly property int sizeDelta: increasing ? 1 : -1

    // Colors.yellow exists in the canonical palette; purple does not yet.
    // Keep the approved purple identity local and overridable rather than
    // silently treating the established magenta interaction color as purple.
    property color decreaseAccentColor: Colors.yellow
    property color increaseAccentColor: "#A46AFF"

    implicitWidth: 30
    implicitHeight: 30
    width: implicitWidth
    height: width  // 1:1, including a 28px compact-width override

    label: direction === "left" ? "⮜"
           : direction === "up" ? "⮝"
           : direction === "right" ? "➤"
           : "⮟"
    labelPixelSize: 17
    accentColor: increasing ? increaseAccentColor : decreaseAccentColor
    interactive: available && directionValid
    Accessible.name: increasing ? "Increase window size" : "Decrease window size"

    // ActionButton retains its original black idle, yellow/orange hover,
    // magenta/black press, disabled fade and EXACT inherited glow values:
    // glyph: .34 / .72 / 0, soft: .22 / .56 / .60, wide disabled.
    // Its existing SafeDropShadow samples the actual rendered arrow glyph.
    signal resizeRequested(int delta)
    onLeftClicked: {
        if (directionValid)
            resizeButton.resizeRequested(sizeDelta);
    }
}
