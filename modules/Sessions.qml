import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: sessionsDock

    property var messagingWindow

    implicitHeight: 50
    implicitWidth: 25

    color: Colors.black
    radius: 0

    // ============================================================
    // ICON + TEXT GLOW
    // ============================================================

    Item {
        id: sessionsTextGlowContainer

        anchors.fill: parent

        Image {
            id: sessionsIcon

            anchors.centerIn: parent

            source: Qt.resolvedUrl("../assets/Sessions.png")

            width: sessionsDock.width - 10
            height: sessionsDock.height - 5

            fillMode: Image.PreserveAspectFit

            smooth: false
        }

        DropShadow {
            id: sessionsTextGlow

            anchors.fill: sessionsIcon
            source: sessionsIcon

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            z: 2

            opacity: sessionsMouse.pressed ? 1.0 : sessionsMouse.containsMouse ? 0.8 : 0.6

            color: Colors.omnitrix

            transparentBorder: true
        }
    }

    // ============================================================
    // MOUSE
    // ============================================================

    MouseArea {
        id: sessionsMouse

        anchors.fill: parent

        hoverEnabled: true

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: function (mouse) {

            // ====================================================
            // LEFT CLICK
            // ====================================================

            if (mouse.button === Qt.LeftButton) {

                /*
                 * IMPORTANT:
                 *
                 * Do NOT change MessagingW.visible/menuOpen
                 * directly while this MouseArea is still handling
                 * the click.
                 *
                 * The Quickshell/Qt crash trace shows:
                 *
                 * QQuickMouseArea::clicked
                 * -> ProxyWindowBase::setVisibleDirect
                 * -> createWindow
                 * -> QQuickItem::setParentItem
                 * -> QQuickMouseArea::itemChange
                 * -> isUnderMouse
                 * -> SIGSEGV
                 *
                 * Qt.callLater() lets this mouse event finish
                 * before Quickshell creates/destroys the
                 * MessagingW PanelWindow.
                 */

                Qt.callLater(function () {
                    if (!sessionsDock.messagingWindow)
                        return;

                    sessionsDock.messagingWindow.menuOpen = !sessionsDock.messagingWindow.menuOpen;
                });
            }

            // ====================================================
            // RIGHT CLICK
            // ====================================================

            if (mouse.button === Qt.RightButton) {
                // Right-click function
            }
        }
    }

    // ============================================================
    // SOFT GLOW
    // ============================================================

    RectangularShadow {
        id: sessionsDockSoftGlow

        anchors.fill: parent

        spread: 3

        z: -1

        opacity: sessionsMouse.pressed ? 0.6 : sessionsMouse.containsMouse ? 0.5 : 0.4

        color: Colors.omnitrix
    }

    // ============================================================
    // WIDE GLOW
    // ============================================================

    RectangularShadow {
        id: sessionsDockWideGlow

        anchors.fill: parent

        spread: 10

        z: 1

        opacity: sessionsMouse.pressed ? 0.11 : sessionsMouse.containsMouse ? 0.10 : 0.07

        color: Colors.omnitrix
    }
}
