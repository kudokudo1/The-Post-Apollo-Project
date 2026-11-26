import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

// KILL-only projection of the donor selector's row grammar: 50px card,
// process glyph, protected indicator, live metric, mini-history, and star.
// No process mutations or persistent identity construction in the delegate.
Item {
    id: root
    required property var entry
    required property var controller
    property bool selected: false
    property bool hovered: false
    signal selectedRequested()
    height: 50

    readonly property bool hunter: controller.killViewMode === controller.killViewHunter
    readonly property bool protectedTask: controller.isProtected(entry)
    readonly property color accent: hunter
        ? (protectedTask ? Colors.red : controller.hunterMetricAccent())
        : Number(entry.cpuInstant !== undefined ? entry.cpuInstant : entry.cpu) >= 25
          ? Colors.red : Colors.magenta
    readonly property bool favorite: controller.isTaskFavorite(entry)

    Rectangle {
        id: plate
        anchors.fill: parent
        anchors.margins: 4
        color: clicker.pressed ? Colors.magenta
               : root.selected || root.hovered ? Colors.yellow : Colors.dark
        border.width: 1
        border.color: root.selected || root.hovered ? Colors.red : root.accent

        RectangularShadow {
            anchors.fill: parent
            spread: 3
            z: -1
            opacity: root.selected || root.hovered ? 0.45 : 0.0
            color: Colors.red
        }

        GohuText {
            id: glyph
            anchors.left: parent.left
            anchors.leftMargin: 7
            anchors.verticalCenter: parent.verticalCenter
            text: root.controller.taskGlyph(root.entry)
            font.pixelSize: 11
            color: clicker.pressed ? Colors.black
                 : root.selected || root.hovered ? Colors.orange : Colors.red
            layer.enabled: !clicker.pressed
            layer.effect: DropShadow {
                radius: 6
                samples: 5
                opacity: 0.46
                color: glyph.color
                transparentBorder: true
            }
        }
        GohuText {
            anchors.right: glyph.left
            anchors.rightMargin: 1
            anchors.verticalCenter: glyph.verticalCenter
            visible: root.protectedTask
            text: ""
            font.pixelSize: 8
            color: root.controller.lockMode(root.entry, "") !== ""
                ? Colors.white : Colors.magenta
        }

        Column {
            id: labelColumn
            anchors.left: glyph.right
            anchors.leftMargin: 6
            anchors.right: mini.left
            anchors.rightMargin: 5
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            GohuText {
                width: parent.width
                text: String(root.entry.comm || root.entry.name || "PROCESS")
                textFormat: Text.PlainText
                elide: Text.ElideRight
                font.pixelSize: 12
                color: clicker.pressed ? Colors.black
                     : root.selected || root.hovered ? Colors.orange : root.accent
            }
            GohuText {
                width: parent.width
                text: root.controller.taskRowMetric(root.entry)
                font.pixelSize: 10
                elide: Text.ElideRight
                color: clicker.pressed ? Colors.black
                     : root.selected || root.hovered ? Colors.orange : root.accent
            }
        }

        Item {
            id: mini
            objectName: "killTargetMiniGraph"
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 5
            anchors.bottomMargin: 5
            width: 82
            clip: true
            readonly property bool combi: root.hunter
                && root.controller.hunterMetricMode === root.controller.hunterMetricCombined
            readonly property int revision: root.controller.miniHistoryRevision
            property real scrollOffset: 0
            NumberAnimation {
                id: motion
                target: mini
                property: "scrollOffset"
                to: 0
                duration: 1080
                easing.type: Easing.Linear
            }
            onRevisionChanged: {
                motion.stop();
                scrollOffset = width / 47;
                motion.start();
            }
            Rectangle {
                anchors.fill: parent
                color: Colors.black
                opacity: 0.80
                border.width: 1
                border.color: root.accent
            }
            Repeater {
                model: mini.combi
                    ? [{key:"cpu",accent:Colors.orange},{key:"mem",accent:Colors.magenta},
                       {key:"io",accent:Colors.cyan},{key:"age",accent:Colors.white}]
                    : [{key:root.hunter ? root.controller.metricKey : "normal",
                        accent:root.accent}]
                delegate: Item {
                    id: trace
                    required property var modelData
                    anchors.fill: mini
                    anchors.margins: 2
                    readonly property var points: {
                        const rev = mini.revision;
                        return root.controller.miniGraphPoints(
                            root.entry, modelData.key, width, height);
                    }
                    Repeater {
                        model: Math.max(0, trace.points.length - 1)
                        delegate: Rectangle {
                            required property int index
                            readonly property point p1: trace.points[index]
                            readonly property point p2: trace.points[index + 1]
                            x: p1.x + mini.scrollOffset
                            y: p1.y - height / 2
                            width: Math.max(1, Math.hypot(p2.x-p1.x,p2.y-p1.y))
                            height: 1
                            color: trace.modelData.accent
                            transformOrigin: Item.Left
                            rotation: Math.atan2(p2.y-p1.y,p2.x-p1.x)*180/Math.PI
                            antialiasing: true
                        }
                    }
                }
            }
        }
        MouseArea {
            id: clicker
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onClicked: root.selectedRequested()
        }
        Item {
            width: 23
            height: 30
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            z: 500
            GohuText {
                anchors.centerIn: parent
                text: root.favorite ? "✦" : "✧"
                font.pixelSize: 19
                color: root.favorite ? (root.accent === Colors.red ? Colors.magenta : root.accent)
                      : Colors.white
                opacity: root.favorite ? 1 : 0.62
                layer.enabled: true
                layer.effect: DropShadow {
                    radius: root.favorite ? 8 : 5
                    samples: 5
                    opacity: root.favorite ? 0.58 : 0.12
                    color: root.accent
                    transparentBorder: true
                }
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                preventStealing: true
                onClicked: function(event) {
                    event.accepted = true;
                    root.selectedRequested();
                    root.controller.toggleTaskFavorite(root.entry);
                }
            }
        }
    }
}
