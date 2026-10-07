import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

Rectangle {
    id: destructiveConfirmOverlay

    required property var controller
    anchors.fill: parent
    visible: controller.destructiveConfirmOpen
    color: Qt.rgba(
        Colors.dark.r, Colors.dark.g, Colors.dark.b, 0.88
    )
    z: 9000

    MouseArea {
        anchors.fill: parent
        // Consume all clicks behind the modal. Clicking outside does not
        // accidentally confirm a destructive action.
        onClicked: function(mouse) { mouse.accepted = true; }
    }

    Rectangle {
        id: destructiveConfirmDialog
        property bool hunterStatusView:
            controller.hunterOperationPhase === "running"
            || controller.hunterOperationPhase === "report"
        property bool confirmKillHovered: false
        property bool confirmKillPressed: false
        property color modalAccent:
            hunterStatusView
            ? controller.hunterOperationAccent
            : controller.destructiveConfirmKind === "protected-freeze"
              || controller.destructiveConfirmKind === "task-freeze"
            ? Colors.cyan
            : Colors.red

        width: Math.min(500, parent.width - 70)
        height:
            hunterStatusView ? 410
            : controller.destructiveConfirmKind === "kill-hogs"
              || controller.destructiveConfirmKind === "kill-mice"
            ? 350
            : controller.destructiveConfirmKind === "protected-freeze"
              || controller.destructiveConfirmKind === "protected-term"
              || controller.destructiveConfirmKind === "task-freeze"
              || controller.destructiveConfirmKind === "task-term"
              || controller.destructiveConfirmKind === "protected-restart"
              || controller.destructiveConfirmKind === "task-restart"
            ? 260 : 190
        anchors.centerIn: parent
        color: Colors.black
        border.width: 1
        border.color: modalAccent
        z: 1

        RectangularShadow {
            anchors.fill: parent
            spread: 12
            z: -1
            opacity: 0.58
            color: destructiveConfirmDialog.modalAccent
        }

        GohuText {
            id: destructiveConfirmTitleText
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 22
            text: {
                const kind = controller.destructiveConfirmKind;
                if (!destructiveConfirmDialog.hunterStatusView
                        && (kind === "kill-hogs" || kind === "kill-mice")) {
                    const firing = destructiveConfirmDialog.confirmKillPressed;
                    const armed = firing
                                  ? "(=ᗜ=)デ╾━"
                                  : (destructiveConfirmDialog.confirmKillHovered
                                     || controller.destructiveConfirmChoice === 1)
                                  ? "ദ്ദി(-_•)デ╾━"
                                  : "(-_•)デ╾━";
                    const animal = kind === "kill-mice"
                                   ? (firing ? "(ᐢ××ᐢ)౨" : "(ᐢ..ᐢ)౨")
                                   : (firing ? "₍˄×⚇×˄₎" : "₍˄·͈⚇·͈˄₎");
                    const label = kind === "kill-mice"
                                  ? "CONFIRM KILL MICE"
                                  : "CONFIRM KILL HOGS";
                    return "⚠︎ " + armed + "  " + animal + "  " + label + "  ⚠︎";
                }
                return controller.destructiveConfirmTitle;
            }
            font.pixelSize: 16
            color: destructiveConfirmDialog.modalAccent
        }

        DropShadow {
            anchors.fill: destructiveConfirmTitleText
            source: destructiveConfirmTitleText
            radius: 7
            samples: 7
            opacity: 0.58
            color: destructiveConfirmDialog.modalAccent
            transparentBorder: true
        }

                    Rectangle {
            id: destructiveConfirmMessageFrame
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: destructiveConfirmTitleText.bottom
            anchors.bottom:
                hunterProgressFrame.visible
                ? hunterProgressFrame.top : destructiveConfirmActionRow.top
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            anchors.topMargin: 16
            anchors.bottomMargin: 12
            color: Colors.black
            border.width: 1
            border.color: Colors.red
            clip: true

            Flickable {
                id: destructiveConfirmMessageFlick
                anchors.left: parent.left
                anchors.right: destructiveConfirmMessageScrollTrack.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 10
                anchors.rightMargin: 6
                anchors.topMargin: 8
                anchors.bottomMargin: 8

                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick
                contentWidth: width
                contentHeight: destructiveConfirmMessageText.implicitHeight

                GohuText {
                    id: destructiveConfirmMessageText
                    width: destructiveConfirmMessageFlick.width
                    text: controller.destructiveConfirmMessage
                    font.pixelSize: 10
                    color: Colors.white
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                }
            }

            NeonScrollBar {
                id: destructiveConfirmMessageScrollTrack

                flickable: destructiveConfirmMessageFlick

                x: parent.width - width - 4
                y: 5
                height: Math.max(0, parent.height - 10)
                z: 20

                barAreaWidth: 9
                railWidth: 9
                barHandleWidth: 6
                minimumHandleHeight: 24

                railColor: Colors.red
                railOpacity: 0.92
                railRadius: 0
                railGlowEnabled: false

                handleColor: Colors.magenta
                handleOpacity: 0.92
                barHandleRadius: 0
                handleBorderWidth: 0
                barGlowIdleSpread: 2
                barGlowHoverSpread: 2
                barGlowIdleOpacity: 0.28
                barGlowHoverOpacity: 0.28

                preserveDragOffset: true
                wheelEnabled: false
                pointerCursorShape: Qt.ArrowCursor

                visible: scrollable
            }
        }

        Rectangle {
            id: hunterProgressFrame
            visible: destructiveConfirmDialog.hunterStatusView
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: destructiveConfirmActionRow.top
            anchors.leftMargin: 28
            anchors.rightMargin: 28
            anchors.bottomMargin: 14
            height: 12
            color: Colors.dark
            border.width: 1
            border.color: controller.hunterOperationAccent

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.margins: 2
                width:
                    Math.max(0, parent.width - 4)
                    * (controller.hunterOperationTotal > 0
                       ? Math.min(
                           1.0,
                           controller.hunterOperationCompleted
                           / controller.hunterOperationTotal
                       )
                       : 0)
                color: controller.hunterOperationAccent
            }

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.42
                color: controller.hunterOperationAccent
            }
        }

        Row {
            id: destructiveConfirmActionRow
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 20
            spacing: 18

            Repeater {
                model:
                    destructiveConfirmDialog.hunterStatusView
                    ? [
                        {
                            key:
                                controller.hunterOperationPhase === "running"
                                ? "hide" : "close-report",
                            label:
                                controller.hunterOperationPhase === "running"
                                ? "HIDE" : "CLOSE REPORT",
                            accent: Colors.cyan,
                            choice: 0
                        }
                      ]
                    : [
                        { key: "cancel", label: "CANCEL", accent: Colors.cyan, choice: 0 },
                        {
                            key: "confirm",
                            label: controller.destructiveConfirmActionLabel,
                            accent:
                                controller.destructiveConfirmKind === "protected-freeze"
                                || controller.destructiveConfirmKind === "task-freeze"
                                ? Colors.cyan : Colors.red,
                            choice: 1
                        }
                      ]

                Rectangle {
                    id: destructiveConfirmButton
                    required property var modelData
                    width:
                        destructiveConfirmDialog.hunterStatusView ? 190 : 150
                    height: 34
                    property bool isSelected:
                        controller.destructiveConfirmChoice
                        === modelData.choice
                    property bool isHovered:
                        !controller.keyboardActive
                        && destructiveConfirmMouse.containsMouse
                    property bool isPressed: destructiveConfirmMouse.pressed

                    readonly property bool isKillConfirm:
                        modelData.key === "confirm"
                        && modelData.accent === Colors.red

                    color:
                        isKillConfirm && isPressed
                        ? Colors.red
                        : isKillConfirm && (isHovered || isSelected)
                        ? Colors.yellow
                        : modelData.key === "confirm" && isPressed
                        ? modelData.accent
                        : modelData.key === "confirm"
                        ? Colors.dark
                        : isPressed ? Colors.magenta
                        : isSelected || isHovered ? Colors.yellow
                        : Colors.dark
                    border.width: 1
                    border.color:
                        isKillConfirm && isPressed
                        ? Colors.black
                        : modelData.accent

                    GohuText {
                        id: destructiveConfirmButtonText
                        anchors.centerIn: parent
                        width: parent.width - 8
                        horizontalAlignment: Text.AlignHCenter
                        text: {
                            if (destructiveConfirmButton.modelData.key !== "confirm")
                                return destructiveConfirmButton.modelData.label;
                            if (destructiveConfirmButton.isPressed)
                                return "(=ᗜ=)デ╾━ ๋࣭⭑  " + destructiveConfirmButton.modelData.label;
                            if (destructiveConfirmButton.isHovered
                                    || destructiveConfirmButton.isSelected)
                                return "ദ്ദി(-_•)デ╾━  " + destructiveConfirmButton.modelData.label;
                            return "(-_•)デ╾━  " + destructiveConfirmButton.modelData.label;
                        }
                        font.pixelSize: 11
                        fontSizeMode: Text.Fit
                        minimumPixelSize: 8
                        color:
                            destructiveConfirmButton.isPressed
                            ? Colors.black
                            : destructiveConfirmButton.modelData.accent
                    }

                    DropShadow {
                        anchors.fill: destructiveConfirmButtonText
                        source: destructiveConfirmButtonText
                        radius: 7
                        samples: 7
                        opacity: 0.56
                        color: destructiveConfirmButton.modelData.accent
                        transparentBorder: true
                    }

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 4
                        z: -1
                        opacity:
                            destructiveConfirmButton.isSelected
                            || destructiveConfirmButton.isHovered
                            ? 0.52 : 0.28
                        color: destructiveConfirmButton.modelData.accent
                    }

                    MouseArea {
                        id: destructiveConfirmMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: {
                            controller.keyboardActive = false;
                            controller.destructiveConfirmChoice = modelData.choice;
                            destructiveConfirmDialog.confirmKillHovered =
                                destructiveConfirmButton.isKillConfirm;
                        }
                        onPositionChanged: function(mouse) {
                            if (!containsMouse)
                                return;

                            controller.keyboardActive = false;
                            controller.destructiveConfirmChoice = modelData.choice;
                            destructiveConfirmDialog.confirmKillHovered =
                                destructiveConfirmButton.isKillConfirm;
                        }
                        onExited: {
                            if (destructiveConfirmButton.isKillConfirm) {
                                destructiveConfirmDialog.confirmKillHovered = false;
                                destructiveConfirmDialog.confirmKillPressed = false;
                            }
                        }
                        onPressedChanged: {
                            if (destructiveConfirmButton.isKillConfirm)
                                destructiveConfirmDialog.confirmKillPressed = pressed;
                        }
                        onClicked: {
                            controller.destructiveConfirmChoice =
                                modelData.choice;
                            if (modelData.key === "cancel")
                                controller.cancelDestructiveConfirm();
                            else if (modelData.key === "hide"
                                     || modelData.key === "close-report")
                                controller.dismissHunterOperationWindow();
                            else
                                controller.executeDestructiveConfirm();
                        }
                    }
                }
            }
        }
    }
}
