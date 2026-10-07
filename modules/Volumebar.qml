import QtQuick
import Quickshell
import "../components"
import QtQuick.Layouts
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import Quickshell.Services.Pipewire

DockButton {
    id: volumebarDock

    property int contentEdgePadding: 2

    implicitHeight: 50
    // Keep the established 130px baseline, but grow when a wider state
    // (notably MUTE / NOT READY) needs more room. This preserves the
    // existing typography while guaranteeing a small edge buffer.
    implicitWidth: Math.max(130, Math.ceil(root.implicitWidth) + (contentEdgePadding * 2))

    contentGlowEnabled: false

    normalDockGlowColor:
        !root.ready
        ? Colors.blue
        : root.muted
        ? Colors.yellow
        : root.glowColor
    hoverDockGlowColor: normalDockGlowColor
    pressedDockGlowColor: normalDockGlowColor

    softGlowIdleOpacity: 0.40
    softGlowHoverOpacity: 0.50
    softGlowPressedOpacity: 0.60

    wideGlowIdleOpacity: 0.07
    wideGlowHoverOpacity: 0.09
    wideGlowPressedOpacity: 0.12

    RowLayout {
        id: root

        spacing: 8
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: 1

        property var sink: Pipewire.defaultAudioSink
        // readonly property bool ready: false
        readonly property bool ready: sink && sink.ready
        readonly property bool muted: ready && sink.audio.muted
        readonly property int vol: ready ? Math.round(sink.audio.volume * 100) : 0

        readonly property color volumeColor: {
            if (root.vol <= 15)
                return Colors.white;

            if (root.vol <= 125)
                return Colors.cyan;

            if (root.vol <= 165) {
                var t = (root.vol - 125) / 40;

                return Qt.rgba(Colors.cyan.r + (Colors.orange.r - Colors.cyan.r) * t, Colors.cyan.g + (Colors.orange.g - Colors.cyan.g) * t, Colors.cyan.b + (Colors.orange.b - Colors.cyan.b) * t, 1);
            }

            if (root.vol <= 250) {
                var t = (root.vol - 165) / 85;

                return Qt.rgba(Colors.orange.r + (Colors.magenta.r - Colors.orange.r) * t, Colors.orange.g + (Colors.magenta.g - Colors.orange.g) * t, Colors.orange.b + (Colors.magenta.b - Colors.orange.b) * t, 1);
            }

            if (root.vol <= 300) {
                var t = (root.vol - 250) / 50;

                return Qt.rgba(Colors.magenta.r + (Colors.red.r - Colors.magenta.r) * t, Colors.magenta.g + (Colors.red.g - Colors.magenta.g) * t, Colors.magenta.b + (Colors.red.b - Colors.magenta.b) * t, 1);
            }

            return Colors.red;
        }

        readonly property color glowColor: {
            if (root.vol <= 125)
                return Colors.cyan;

            if (root.vol <= 165) {
                var t = (root.vol - 125) / 40;

                return Qt.rgba(Colors.cyan.r + (Colors.orange.r - Colors.cyan.r) * t, Colors.cyan.g + (Colors.orange.g - Colors.cyan.g) * t, Colors.cyan.b + (Colors.orange.b - Colors.cyan.b) * t, 1);
            }

            if (root.vol <= 250) {
                var t = (root.vol - 165) / 85;

                return Qt.rgba(Colors.orange.r + (Colors.magenta.r - Colors.orange.r) * t, Colors.orange.g + (Colors.magenta.g - Colors.orange.g) * t, Colors.orange.b + (Colors.magenta.b - Colors.orange.b) * t, 1);
            }

            if (root.vol <= 300) {
                var t = (root.vol - 250) / 50;

                return Qt.rgba(Colors.magenta.r + (Colors.red.r - Colors.magenta.r) * t, Colors.magenta.g + (Colors.red.g - Colors.magenta.g) * t, Colors.magenta.b + (Colors.red.b - Colors.magenta.b) * t, 1);
            }

            return Colors.red;
        }

        readonly property string icon: {
            if (!ready)
                return "ᓬ(｡•́︿•̀｡)";

            if (muted)
                return "⊹˖(ᴗ˳ᴗ)ᶻ𝗓";

            if (vol === 0)
                return "░░░░░░░";

            if (vol <= 15)
                return "█░░░░░░";

            if (vol <= 30)
                return "██░░░░░";

            if (vol <= 45)
                return "███░░░░";

            if (vol <= 60)
                return "████░░░";

            if (vol <= 75)
                return "█████░░";

            if (vol <= 99)
                return "██████░";

            return "███████";
        }

        Item {
            id: volumebarIconContainer

            implicitWidth: volumebarIcon.implicitWidth
            implicitHeight: volumebarIcon.implicitHeight

            GohuText {
                id: volumebarIcon

                anchors.fill: parent

                text: root.icon

                font.pixelSize: 20

                color: {
                    if (!root.ready)
                        return Colors.blue;

                    if (root.muted)
                        return Colors.yellow;

                    return root.volumeColor;
                }
            }

            DropShadow {
                id: iconGlow

                anchors.fill: volumebarIcon
                source: volumebarIcon

                horizontalOffset: 0
                verticalOffset: 0

                radius: 14
                samples: 15

                z: 2

                opacity: volumebarDock.pressed ? 1.0 : volumebarDock.hovered ? 0.8 : 0.6

                color: !root.ready ? Colors.blue : root.muted ? Colors.yellow : root.vol <= 15 ? Colors.cyan : root.volumeColor

                transparentBorder: true
            }
        }

        Item {
            id: volumebarTextContainer

            implicitWidth: volumebarText.implicitWidth
            implicitHeight: volumebarText.implicitHeight

            Text {
                id: volumebarText

                anchors.fill: parent

                text: {
                    if (!root.ready)
                        return "ᕒ";

                    if (root.muted)
                        return " ࣪ ˖ ";

                    return root.vol + "%";
                }

                font.pixelSize: 20

                color: {
                    if (!root.ready)
                        return Colors.blue;

                    if (root.muted)
                        return Colors.yellow;

                    return root.volumeColor;
                }
            }

            DropShadow {
                id: textGlow

                anchors.fill: volumebarText
                source: volumebarText

                horizontalOffset: 0
                verticalOffset: 0

                radius: 14
                samples: 15

                z: 2

                opacity: volumebarDock.pressed ? 1.0 : volumebarDock.hovered ? 0.8 : 0.6

                color: !root.ready ? Colors.blue : root.muted ? Colors.yellow : root.vol <= 15 ? Colors.cyan : root.volumeColor

                transparentBorder: true
            }
        }
    }

    PwObjectTracker {
        objects: [root.sink]
    }

    onRightClicked: {
        if (root.ready)
            root.sink.audio.muted = !root.sink.audio.muted;
    }

    onWheel: function(wheelEvent) {
        if (!root.ready)
            return;

        if (wheelEvent.angleDelta.y > 0)
            root.sink.audio.volume = root.sink.audio.volume + 0.05;
        else if (wheelEvent.angleDelta.y < 0)
            root.sink.audio.volume =
                Math.max(root.sink.audio.volume - 0.05, 0.0);
    }

}
