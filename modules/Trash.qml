import Quickshell
import QtQuick
import Quickshell.Io
import Quickshell.Wayland
import "../components"

// TRASH // First bottom-left utility. Match Power's actual 50x50 button
// geometry and edge clearances without touching the top dock or Power.
// This first panel is presentation only: no file or process operations.
PanelWindow {
    id: trashLauncher

    property bool menuOpen: false

    function toggle() {
        menuOpen = !menuOpen;
        if (menuOpen)
            trashMenu.forceActiveFocus();
    }

    IpcHandler {
        target: "trash"

        function toggle() {
            trashLauncher.toggle();
        }
    }

    anchors {
        top: false
        bottom: true
        left: true
        right: false
    }

    // Mirror Power: outer 10px margin + inner 15px offset = 25px edge;
    // 10px window bottom + 10px button bottom offset = 20px bottom.
    margins {
        top: 0
        bottom: 10
        left: 10
        right: 0
    }

    implicitWidth: 220
    implicitHeight: 290

    color: "transparent"
    WlrLayershell.keyboardFocus: menuOpen
                                    ? WlrKeyboardFocus.Exclusive
                                    : WlrKeyboardFocus.None

    // Only the visible button and, when open, the panel take pointer input.
    mask: Region {
        Region {
            item: trashButton
        }

        Region {
            x: trashMenu.x
            y: trashMenu.y
            width: trashMenu.visible ? trashMenu.width : 0
            height: trashMenu.visible ? trashMenu.height : 0
        }
    }

    Item {
        id: trashArea
        width: 220
        height: 290
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        DockButton {
            id: trashButton
            x: 15
            y: 230
            width: 50
            height: 50
            z: 1
            radius: width / 100

            acceptedButtons: Qt.LeftButton
            open: trashLauncher.menuOpen

            // Match top-row DockButton glow strengths, radii and spreads
            // by inheriting its numeric defaults rather than Power's
            // intentionally subdued overrides. Color planes stay independent:
            // closed icon = white with Omnitrix sampled glow;
            // closed chassis = green; open = yellow + magenta icon/glows.
            normalForegroundColor: Colors.white
            hoverForegroundColor: Colors.white
            pressedForegroundColor: Colors.white
            openForegroundColor: Colors.magenta

            normalContentGlowColor: Colors.omnitrix
            hoverContentGlowColor: Colors.omnitrix
            pressedContentGlowColor: Colors.omnitrix

            normalDockGlowColor: Colors.green
            hoverDockGlowColor: Colors.green
            pressedDockGlowColor: Colors.green

            openFillColor: Colors.yellow
            openGlowColor: Colors.magenta

            // The sampled glow follows the actual rendered glyph at every
            // interaction state, instead of painting a detached silhouette.
            contentGlowSource: trashGlyph

            Text {
                id: trashGlyph
                anchors.centerIn: parent
                // Text-presentation variation keeps the glyph monochrome.
                text: "♻︎"
                font.pixelSize: 35
                color: trashButton.foregroundColor
            }

            onLeftClicked: trashLauncher.toggle()
        }
    }

    Rectangle {
        id: trashMenu
        x: 35
        y: 20
        width: 150
        height: 200
        z: 1
        radius: 4
        color: Colors.black
        border.width: 1
        border.color: Colors.green

        visible: trashLauncher.menuOpen
        focus: trashLauncher.menuOpen

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape) {
                trashLauncher.menuOpen = false;
                event.accepted = true;
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: 9
            spacing: 10

            Row {
                width: parent.width
                height: 24
                spacing: 3

                Text {
                    width: parent.width - 26
                    height: parent.height
                    text: "TRASH // INDEX"
                    color: Colors.magenta
                    font.pixelSize: 11
                    verticalAlignment: Text.AlignVCenter
                }

                ActionButton {
                    width: 23
                    height: 22
                    label: "X"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    onLeftClicked: trashLauncher.toggle()
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
            }

            Text {
                width: parent.width
                text: "SYSTEM TRASH"
                color: Colors.white
                font.pixelSize: 12
            }

            Text {
                width: parent.width
                text: "RESTORE // BURN"
                color: Colors.green
                font.pixelSize: 10
            }

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "TRASH VIEW NOT CONNECTED YET. NO FILE ACTIONS IN THIS PREVIEW."
                color: Colors.cyan
                font.pixelSize: 10
            }
        }
    }
}
