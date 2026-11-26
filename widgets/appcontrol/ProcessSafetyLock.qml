import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

// KILL lock presentation follows the existing AppControl lock plate and
// glyph grammar. The consumer supplies the existing owner's safety methods;
// this component never grants permissions or sends a process signal itself.
Item {
    id: root
    required property var controller
    property var taskItem: null
    property string actionKind: ""
    property color accentColor: Colors.red
    readonly property bool master: actionKind.length === 0
    readonly property bool isProtected: !!taskItem && controller.isProtected(taskItem)
    readonly property string mode: isProtected
        ? controller.lockMode(taskItem, actionKind) : ""
    readonly property bool masterUnlocked: isProtected && !master
        && controller.lockMode(taskItem, "") !== ""
    readonly property string localMode: !master && controller.localLockMode
        ? controller.localLockMode(taskItem, actionKind) : ""
    readonly property bool stickyUnlocked: mode === "sticky"
    readonly property bool unlocked: mode === "once" || stickyUnlocked
    visible: isProtected
    Accessible.name: master ? "Master process lock" : actionKind + " process lock"
    Accessible.description: masterUnlocked ? "Master authorization is active; individual lock changes do not revoke it." : "Left click: one-shot; right click: sticky."

    Rectangle {
        id: plate
        anchors.fill: parent
        anchors.margins: 3
        color: Colors.black
        opacity: root.master ? 0.96 : 0.92
        border.width: 1
        border.color: root.accentColor
    }
    RectangularShadow {
        anchors.fill: plate
        anchors.margins: root.master ? -3 : -4
        spread: root.master ? 3 : 4
        z: -1
        opacity: mouse.containsMouse ? 0.38 : root.unlocked ? 0.25 : 0.15
        color: root.accentColor
    }
    GohuText {
        anchors.centerIn: parent
        text: root.stickyUnlocked ? "" : root.unlocked ? "☍" : ""
        font.pixelSize: root.stickyUnlocked ? 15 : 12
        color: root.accentColor
        layer.enabled: true
        layer.effect: DropShadow {
            radius: root.master ? 3 : 5
            samples: root.master ? 3 : 5
            opacity: 0.30
            color: root.accentColor
            transparentBorder: true
        }
    }
    GohuText {
        anchors.right: parent.right
        anchors.top: parent.top
        text: root.localMode === "sticky" ? "" : "+"
        font.pixelSize: 8
        color: root.accentColor
        visible: root.masterUnlocked && root.localMode !== ""
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: root.isProtected
                 && root.controller.canChangeLock(root.taskItem)
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(event) {
            event.accepted = true;
            root.controller.toggleLock(root.taskItem, root.actionKind,
                                       event.button === Qt.RightButton);
        }
    }
}
