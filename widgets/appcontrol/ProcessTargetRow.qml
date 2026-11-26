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
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        color: clicker.pressed ? Colors.magenta
               : root.selected || root.hovered ? Colors.yellow : Colors.dark

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
            anchors.leftMargin: 14
            width: 50
            horizontalAlignment: Text.AlignHCenter
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
            anchors.left: glyph.left
            anchors.leftMargin: -3
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
            anchors.leftMargin: 9
            anchors.right: mini.left
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0
            GohuText {
                width: parent.width
                text: root.controller.taskDisplayName(root.entry)
                textFormat: Text.PlainText
                elide: Text.ElideRight
                font.pixelSize: 15
                color: clicker.pressed ? Colors.black
                     : root.selected || root.hovered ? Colors.orange : Colors.red
            }
            GohuText {
                width: parent.width
                text: root.controller.taskRowMetric(root.entry) + " • PID " + String(root.entry.pid || "?")
                    + (root.hunter && root.protectedTask ? " • ⚠︎ PROTECTED" : "")
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
            Rectangle {
                anchors.fill: parent
                color: Colors.black
                opacity: 0.80
                border.width: 1
                border.color: root.accent
            }
            ProcessMiniGraph {
                objectName: "killTargetSharedMiniRenderer"
                anchors.fill: parent
                anchors.margins: 2
                geometry: root.controller.miniGeometry
                historyRevision: root.controller.miniHistoryRevision
                historyLimit: root.controller.miniHistoryLimit
                scrollDuration: root.controller.miniScrollDuration
                taskIdentity: String(root.entry.pid || 0) + "|" + String(root.entry.startTicks || 0) + "|" + String(root.entry.comm || "")
                metricKey: root.hunter ? root.controller.metricKey : "normal"
                combiView: mini.combi
                graphRange: root.controller.miniRange(metricKey)
                accent: root.accent
                readHistory: function() { return root.controller.miniHistory(root.entry, metricKey) }
                readMetricHistory: function(key) { return root.controller.miniHistory(root.entry, key) }
                metricRange: function(key) { return root.controller.miniMetricRange(key) }
            }
        }
        MouseArea {
            id: clicker
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onClicked: root.selectedRequested()
        }
        Item {
            width: 30
            height: 30
            anchors.right: parent.right
            anchors.rightMargin: 6
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
