import Quickshell
import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../components"

PanelWindow {
    id: cpuPlusWindow

    property bool menuOpen: false
    property int selectedModeIndex: 0

    readonly property var modes: [
        {
            name: "FAVORITES",
            symbol: "(˵✧ᴗ✧˵)",
            kind: "text"
        },
        {
            name: "PROCESS",
            symbol: "(-_•)︻デ═一",
            kind: "text"
        },
        {
            name: "THERMAL",
            symbol: "",
            kind: "thermal"
        },
        {
            name: "SYSTEM",
            symbol: "🖳",
            kind: "text"
        }
    ]

    function open() {
        menuOpen = true;
    }

    function close() {
        menuOpen = false;
    }

    function toggle() {
        menuOpen = !menuOpen;
    }

    function selectMode(index) {
        selectedModeIndex = Math.max(
            0,
            Math.min(modes.length - 1, Number(index || 0))
        );
    }

    // ============================================================
    // SHARED THERMAL ICON
    // Copied from AppControl's canonical THERMAL composition so the
    // two surfaces speak the same visual language.
    // ============================================================

    Component {
        id: thermalIconComponent

        Item {
            id: thermalIconRoot

            property color iconColor: Colors.orange
            property color glowColor: Colors.orange
            property real iconScale: 1.0
            property real glowOpacity: 0.46
            property bool pressed: false

            opacity: 1.0
            implicitWidth: 59 * iconScale
            implicitHeight: 24 * iconScale
            width: implicitWidth
            height: implicitHeight

            Item {
                id: thermalIconScaledContent

                width: 59
                height: 24

                anchors.centerIn: parent

                scale: thermalIconRoot.iconScale
                transformOrigin: Item.Center
                opacity: 1.0

                GohuText {
                    id: thermalIconTopLeftStar

                    x: 15
                    y: -3

                    text: "⋆"

                    font.pixelSize: 7

                    opacity: 1.0

                    color:
                        thermalIconRoot.pressed
                        ? Colors.black
                        : thermalIconRoot.iconColor
                }

                DropShadow {
                    anchors.fill: thermalIconTopLeftStar
                    source: thermalIconTopLeftStar

                    visible: !thermalIconRoot.pressed

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 4
                    samples: 5

                    opacity: thermalIconRoot.glowOpacity
                    color: thermalIconRoot.glowColor

                    transparentBorder: true
                }

                Row {
                    id: thermalIconOuterRow

                    anchors.centerIn: parent

                    spacing: 1

                    Row {
                        id: thermalIconLeftCoreRow

                        anchors.verticalCenter: parent.verticalCenter

                        spacing: -9

                        Item {
                            width: thermalIconLeft.implicitWidth
                            height: 24

                            GohuText {
                                id: thermalIconLeft

                                anchors.verticalCenter: parent.verticalCenter

                                text: "₊˚⊹"

                                font.pixelSize: 13
                                font.letterSpacing: -1.6

                                opacity: 1.0

                                color:
                                    thermalIconRoot.pressed
                                    ? Colors.black
                                    : thermalIconRoot.iconColor
                            }

                            DropShadow {
                                anchors.fill: thermalIconLeft
                                source: thermalIconLeft

                                visible: !thermalIconRoot.pressed

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 5
                                samples: 5

                                opacity: thermalIconRoot.glowOpacity
                                color: thermalIconRoot.glowColor

                                transparentBorder: true
                            }
                        }

                        Item {
                            width: thermalIconCore.implicitWidth
                            height: 24

                            Text {
                                id: thermalIconCore

                                anchors.verticalCenter: parent.verticalCenter

                                text: "🌡"

                                font.family: "Noto Sans Symbols2"
                                font.pixelSize: 20
                                font.weight: Font.Bold

                                opacity: 1.0

                                color:
                                    thermalIconRoot.pressed
                                    ? Colors.black
                                    : thermalIconRoot.iconColor
                            }

                            DropShadow {
                                anchors.fill: thermalIconCore
                                source: thermalIconCore

                                visible: !thermalIconRoot.pressed

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 5
                                samples: 5

                                opacity: thermalIconRoot.glowOpacity * 0.76
                                color: thermalIconRoot.glowColor

                                transparentBorder: true
                            }
                        }
                    }

                    Item {
                        width: thermalIconRight.implicitWidth
                        height: 24

                        GohuText {
                            id: thermalIconRight

                            anchors.verticalCenter: parent.verticalCenter

                            text: "๋࣭⭑"

                            font.pixelSize: 13

                            opacity: 1.0

                            color:
                                thermalIconRoot.pressed
                                ? Colors.black
                                : thermalIconRoot.iconColor
                        }

                        DropShadow {
                            anchors.fill: thermalIconRight
                            source: thermalIconRight

                            visible: !thermalIconRoot.pressed

                            horizontalOffset: 0
                            verticalOffset: 0

                            radius: 5
                            samples: 5

                            opacity: thermalIconRoot.glowOpacity
                            color: thermalIconRoot.glowColor

                            transparentBorder: true
                        }
                    }
                }
            }
        }
    }

    // ============================================================
    // WINDOW
    // AppControlW: 834 wide x 674 tall
    // CPU++:       674 wide x 834 tall
    // ============================================================

    implicitWidth: 674
    implicitHeight: 834

    anchors {
        top: true
        right: true
    }

    // Original right margin was 2. Increase by 80px to move the
    // entire CPU++ chassis left without changing its dimensions.
    margins {
        top: -3
        right: 82
    }

    color: "transparent"
    surfaceFormat.opaque: false
    focusable: true
    visible: menuOpen

    // ============================================================
    // OUTER CHASSIS GLOW
    // Structural glow remains orange at every interaction state.
    // ============================================================

    RectangularShadow {
        anchors.fill: background

        spread: 6
        z: -20

        opacity: 0.38
        color: Colors.orange
    }

    RectangularShadow {
        anchors.fill: background

        spread: 12
        z: -21

        opacity: 0.12
        color: Colors.orange
    }

    Rectangle {
        id: background

        anchors.fill: parent
        anchors.margins: 12

        color: "transparent"
    }

    // ============================================================
    // TOP MODE SELECTOR
    // ============================================================

    Rectangle {
        id: modeRail

        height: 110

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.topMargin: 12

        // Swapped with the CPU++ native control panel.
        color: Colors.dark

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.22
            color: Colors.orange
        }

        GohuText {
            id: modeRailHeader

            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 14
            anchors.topMargin: 8

            text: "CPU++"

            font.pixelSize: 15
            color: Colors.magenta
        }

        Rectangle {
            id: modeRailHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: modeRailHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 5

            height: 2

            color: Colors.cyan
        }

        Row {
            id: modeButtonRow

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.bottomMargin: 8

            height: 58
            spacing: 8

            Repeater {
                model: cpuPlusWindow.modes

                Rectangle {
                    id: modeButton

                    required property int index
                    required property var modelData

                    readonly property bool isSelected:
                        index === cpuPlusWindow.selectedModeIndex

                    readonly property bool isHovered:
                        modeMouse.containsMouse

                    readonly property bool isPressed:
                        modeMouse.pressed

                    readonly property color contentColor:
                        isPressed
                        ? Colors.black
                        : isSelected
                        ? Colors.magenta
                        : isHovered
                        ? Colors.orange
                        : Colors.cyan

                    width:
                        (
                            modeButtonRow.width
                            - modeButtonRow.spacing
                              * (cpuPlusWindow.modes.length - 1)
                        )
                        / cpuPlusWindow.modes.length

                    height: parent.height

                    scale:
                        isPressed
                        ? 0.99
                        : isHovered
                        ? 1.025
                        : isSelected
                        ? 1.01
                        : 1.0

                    color:
                        isPressed
                        ? Colors.magenta
                        : isHovered || isSelected
                        ? Colors.yellow
                        : Colors.black

                    border.width: 1
                    border.color: Colors.cyan

                    Behavior on scale {
                        NumberAnimation {
                            duration: 90
                            easing.type: Easing.OutQuad
                        }
                    }

                    Column {
                        width: parent.width
                        anchors.centerIn: parent

                        spacing: 1

                        Item {
                            width: parent.width
                            height: 29

                            Loader {
                                id: thermalModeIcon

                                anchors.centerIn: parent

                                visible: modelData.kind === "thermal"
                                sourceComponent:
                                    visible
                                    ? thermalIconComponent
                                    : undefined

                                onLoaded: {
                                    item.iconScale = 0.82;
                                    item.iconColor = Qt.binding(function() {
                                        return modeButton.contentColor;
                                    });
                                    item.pressed = Qt.binding(function() {
                                        return modeButton.isPressed;
                                    });
                                    item.glowOpacity = 0.34;
                                }
                            }

                            GohuText {
                                id: textModeIcon

                                anchors.centerIn: parent

                                visible: modelData.kind !== "thermal"

                                text: modelData.symbol

                                font.pixelSize:
                                    modelData.name === "PROCESS"
                                    ? 12
                                    : modelData.name === "FAVORITES"
                                    ? 14
                                    : 18

                                color: modeButton.contentColor

                                layer.enabled: !modeButton.isPressed
                                layer.effect: DropShadow {
                                    horizontalOffset: 0
                                    verticalOffset: 0

                                    radius: 7
                                    samples: 9

                                    opacity:
                                        modeButton.isHovered
                                        || modeButton.isSelected
                                        ? 0.60
                                        : 0.30

                                    color: Colors.orange

                                    transparentBorder: true
                                }
                            }
                        }

                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter

                            text: modelData.name

                            font.pixelSize: 10
                            color: modeButton.contentColor
                        }
                    }

                    MouseArea {
                        id: modeMouse

                        anchors.fill: parent

                        hoverEnabled: true

                        onClicked: {
                            cpuPlusWindow.selectMode(index);
                        }
                    }

                    // Orange glow is invariant; only its reach/intensity changes.
                    RectangularShadow {
                        anchors.fill: parent

                        spread:
                            modeButton.isHovered
                            ? 6
                            : modeButton.isSelected
                            ? 4
                            : 2

                        z: -1

                        opacity:
                            modeButton.isPressed
                            ? 0.62
                            : modeButton.isHovered
                            ? 0.56
                            : modeButton.isSelected
                            ? 0.46
                            : 0.10

                        color: Colors.orange
                    }

                    RectangularShadow {
                        anchors.fill: parent

                        spread:
                            modeButton.isHovered
                            ? 16
                            : modeButton.isSelected
                            ? 11
                            : 7

                        z: -2

                        opacity:
                            modeButton.isPressed
                            ? 0.16
                            : modeButton.isHovered
                            ? 0.14
                            : modeButton.isSelected
                            ? 0.11
                            : 0.035

                        color: Colors.orange
                    }
                }
            }
        }
    }

    // ============================================================
    // SHARED APPCONTROL INSTRUMENT BAY
    // ============================================================

    Rectangle {
        id: sharedInstrumentPane

        width: 390

        anchors.left: parent.left
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.leftMargin: 12
        anchors.bottomMargin: 12

        color: Qt.rgba(
            Colors.black.r,
            Colors.black.g,
            Colors.black.b,
            0.95
        )

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: sharedInstrumentHeader

            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 16
            anchors.topMargin: 16

            text: "SHARED INSTRUMENT"

            font.pixelSize: 13
            color: Colors.magenta
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedInstrumentHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2

            color: Colors.cyan
        }
    }

    // ============================================================
    // CPU++ NATIVE EXPANSION BAY
    // ============================================================

    Rectangle {
        id: nativeControlPane

        anchors.left: sharedInstrumentPane.right
        anchors.right: parent.right
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.rightMargin: 12
        anchors.bottomMargin: 12

        // Swapped with the top mode selector panel.
        color: Colors.black

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: nativeControlHeader

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top

            anchors.topMargin: 16

            text: "CPU++ CONTROL"

            font.pixelSize: 13
            color: Colors.magenta
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: nativeControlHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2

            color: Colors.cyan
        }
    }
}
