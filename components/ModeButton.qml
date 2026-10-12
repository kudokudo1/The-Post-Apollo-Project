import QtQuick

// Reusable MAIN MODE button: owning menu controls geometry, selection, keyboard
// navigation and activation effects. This component owns the shared visual
// grammar, pointer signaling and sampled icon/label glows.
// No existing widget is automatically migrated by its presence.
Rectangle {
    id: modeButton

    // Supply menu-specific artwork as direct children; it will live inside
    // customContentHost. Set customArtwork: true and supply the relevant
    // customPrimaryGlowSource / customLabelGlowSource if it needs sampled glow.
    default property alias contentData: customContentHost.data

    property bool selected: false
    property bool keyboardActive: false
    property bool keyboardSelected: false
    property bool interactive: true

    property bool bordered: false
    property real borderThickness: 1
    property color idleFillColor: Colors.black
    property color hoveredFillColor: Colors.yellow
    property color selectedFillColor: Colors.yellow
    property color pressedFillColor: Colors.magenta
    property color idlePrimaryColor: Colors.cyan
    property color hoverPrimaryColor: Colors.orange
    property color selectedPrimaryColor: Colors.magenta
    property color pressedPrimaryColor: Colors.black
    property color pressedBorderColor: Colors.black
    property color perimeterGlowColor: Colors.orange

    // Menu chooses arrangement, sizing and custom glyph composition.
    property bool customArtwork: false
    property Item customPrimaryGlowSource: null
    property Item customLabelGlowSource: null
    property bool primaryGlowEnabled: true
    property bool labelGlowEnabled: true
    property bool horizontalContent: false
    property bool textOnly: false
    property string iconText: "✦"
    property string labelText: "MODE"
    property int iconFontSize: 17
    property int labelFontSize: 11
    property real contentSpacing: 2

    // Provisional until the orange-vs-magenta caption glow screen comparison.
    property color labelGlowColor: Colors.white

    signal triggered()
    // Host resets keyboard-primary and synchronizes its navigation anchor to
    // this item on ACTUAL pointer motion. Stationary pointer does not steal it.
    signal pointerMoved()
    signal pointerExited()
    signal wheel(var wheelEvent)

    readonly property bool pointerInside: pointer.containsMouse
    readonly property bool primaryHovered:
        keyboardActive ? keyboardSelected : pointerInside
    readonly property bool secondaryHovered:
        keyboardActive && pointerInside && !keyboardSelected
    readonly property bool hovered: primaryHovered || secondaryHovered
    readonly property bool pressed: pointer.pressed

    readonly property color primaryColor:
        pressed ? pressedPrimaryColor
        : selected ? selectedPrimaryColor
        : hovered ? hoverPrimaryColor
        : idlePrimaryColor

    // Black pressed glyph, but retain its earlier COLOR IDENTITY in the glow.
    readonly property color primaryGlowColor:
        selected ? selectedPrimaryColor
        : hovered ? hoverPrimaryColor
        : idlePrimaryColor

    readonly property color labelColor:
        pressed ? pressedPrimaryColor : Colors.white
    readonly property real labelOpacity:
        pressed ? VisualLanguage.modeLabelPressedOpacity
        : selected || hovered ? VisualLanguage.modeLabelActiveOpacity
        : VisualLanguage.modeLabelIdleOpacity

    // The secondary mouse hover is orange-foreground on BLACK, not yellow.
    color:
        pressed ? pressedFillColor
        : selected ? selectedFillColor
        : primaryHovered ? hoveredFillColor
        : idleFillColor

    border.width: bordered ? borderThickness : 0
    border.color:
        pressed ? pressedBorderColor
        : selected ? selectedPrimaryColor
        : hovered ? hoverPrimaryColor
        : idlePrimaryColor
    clip: false

    ModeButtonCloseHalo {
        selected: modeButton.selected
        hovered: modeButton.hovered
        pressed: modeButton.pressed
        keyboardSelected: modeButton.keyboardActive && modeButton.keyboardSelected
        color: modeButton.perimeterGlowColor
    }
    ModeButtonWideHalo {
        selected: modeButton.selected
        hovered: modeButton.hovered
        pressed: modeButton.pressed
        keyboardSelected: modeButton.keyboardActive && modeButton.keyboardSelected
        color: modeButton.perimeterGlowColor
    }

    Item {
        id: defaultContentHost
        anchors.fill: parent
        visible: !modeButton.customArtwork

        Grid {
            anchors.centerIn: parent
            columns: modeButton.horizontalContent ? 2 : 1
            rows: modeButton.horizontalContent ? 1 : 2
            spacing: modeButton.contentSpacing

            GohuText {
                id: defaultIcon
                visible: !modeButton.textOnly
                text: modeButton.iconText
                font.pixelSize: modeButton.iconFontSize
                color: modeButton.primaryColor
            }
            QuietText {
                id: defaultLabel
                visible: modeButton.labelText.length > 0
                text: modeButton.labelText
                font.pixelSize: modeButton.labelFontSize
                color: modeButton.textOnly
                       ? modeButton.primaryColor : modeButton.labelColor
                quietOpacity: modeButton.textOnly
                              ? 1.0 : modeButton.labelOpacity
            }
        }
    }

    Item {
        id: customContentHost
        anchors.fill: parent
        visible: modeButton.customArtwork
    }

    readonly property Item primaryGlowSource:
        customArtwork ? customPrimaryGlowSource
        : textOnly ? defaultLabel : defaultIcon
    readonly property Item labelGlowSource:
        customArtwork ? customLabelGlowSource
        : textOnly ? null : defaultLabel

    TextHashGlow {
        safeSource: modeButton.primaryGlowSource
        requestedVisible: modeButton.primaryGlowEnabled
                          && modeButton.primaryGlowSource !== null
                          && modeButton.primaryGlowSource.visible
        foregroundColor: modeButton.primaryColor
        preferredGlowColor: modeButton.primaryGlowColor
        modeButtonRecipe: true
        modeSelected: modeButton.selected
        modeHovered: modeButton.hovered
    }

    TextHashGlow {
        safeSource: modeButton.labelGlowSource
        requestedVisible: modeButton.labelGlowEnabled
                          && !modeButton.pressed
                          && modeButton.labelGlowSource !== null
                          && modeButton.labelGlowSource.visible
        foregroundColor: modeButton.labelColor
        preferredGlowColor: modeButton.labelGlowColor
        radius: VisualLanguage.modeLabelGlowRadius
        samples: VisualLanguage.modeLabelGlowSamples
        opacity: modeButton.selected || modeButton.hovered
                 ? VisualLanguage.modeLabelGlowActiveOpacity
                 : VisualLanguage.modeLabelGlowIdleOpacity
    }

    MouseArea {
        id: pointer
        anchors.fill: parent
        z: 10
        hoverEnabled: true
        enabled: modeButton.interactive
        acceptedButtons: Qt.LeftButton
        onPositionChanged: modeButton.pointerMoved()
        onExited: modeButton.pointerExited()
        onWheel: function(wheelEvent) { modeButton.wheel(wheelEvent); }
        onClicked: modeButton.triggered()
    }
}
