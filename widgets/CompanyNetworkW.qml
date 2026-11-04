import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"

// Company Network v0: navigation-only geographic operations chassis.
// No organization membership, employee directory or client data is loaded.
// A mapped, masked PanelWindow avoids repeated Wayland remap cycles.
PanelWindow {
    id: root

    property bool menuOpen: false
    property real dockCenterX: 0
    property real chassisTopY: 0

    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 12
    readonly property int frameWidth: Math.max(1, Math.min(640,
        (root.screen ? root.screen.width : 1280) - glowGutter * 2 - 20))
    readonly property int frameHeight: Math.max(1, Math.min(470,
        (root.screen ? root.screen.height : 720)
        - frameTopInset - bottomScreenGap - 20))

    readonly property var mainModes: [
        { id: "coverage", label: "COVERAGE", title: "TERRITORY COVERAGE",
          detail: "No verified state, county, city, or service-area records are connected." },
        { id: "network", label: "NETWORK", title: "HUBS & PARTNERS",
          detail: "Organization locations, service providers, and referral links are not connected." },
        { id: "workforce", label: "WORKFORCE", title: "TEAMS & ONBOARDING",
          detail: "Worker assignments and employee/client onboarding records are not connected." },
        { id: "expansion", label: "EXPANSION", title: "EXPANSION PLANNING",
          detail: "No proposed territories, staffing scenarios, or coverage forecasts are loaded." }
    ]
    property int selectedMainModeIndex: 0
    readonly property var activeMode: mainModes[selectedMainModeIndex]

    function toggle() {
        menuOpen = !menuOpen;
    }

    onMenuOpenChanged: {
        if (menuOpen)
            Qt.callLater(function() {
                if (root.menuOpen)
                    companyFrame.forceActiveFocus();
            });
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: Math.max(0, Math.min(
            (root.screen ? root.screen.height : root.implicitHeight)
                - root.implicitHeight,
            Math.round(root.chassisTopY - root.glowGutter)))
        left: Math.max(0, Math.min(
            (root.screen ? root.screen.width : root.implicitWidth)
                - root.implicitWidth,
            Math.round(root.dockCenterX - root.implicitWidth / 2)))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: menuOpen
    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.frameTopInset
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: companyFrame
        anchors.fill: parent
        anchors.leftMargin: root.glowGutter
        anchors.rightMargin: root.glowGutter
        anchors.topMargin: root.frameTopInset
        anchors.bottomMargin: root.bottomScreenGap
        visible: root.menuOpen
        focus: root.menuOpen
        Keys.onEscapePressed: function(event) {
            if (!root.menuOpen)
                return;
            root.menuOpen = false;
            event.accepted = true;
        }

        fillColor: Colors.black
        fillOpacity: 0.96
        borderColor: Colors.blue
        borderWidth: 1
        radius: 0
        glowVisible: root.menuOpen
        glowColor: Colors.blue

        Rectangle {
            id: header
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 56
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 15
                anchors.right: feedStatus.left
                anchors.rightMargin: 9
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
                text: "COMPANY // " + root.activeMode.label
            }

            Rectangle {
                id: feedStatus
                anchors.right: closeButton.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                width: 76
                height: 26
                color: Colors.dark
                border.color: Colors.blue
                border.width: 1

                GohuText {
                    anchors.centerIn: parent
                    font.pixelSize: 10
                    color: Colors.yellow
                    text: "NO DATA"
                }
            }

            ActionButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 34
                height: 32
                label: "×"
                labelPixelSize: 22
                contentPadding: 4
                accentColor: Colors.red
                destructive: true
                onLeftClicked: root.menuOpen = false
            }
        }

        Rectangle {
            id: headerDivider
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
            height: 2
            color: Colors.cyan
        }

        Column {
            id: mainModeRail
            anchors.top: headerDivider.bottom
            anchors.topMargin: 15
            anchors.left: parent.left
            anchors.leftMargin: 10
            width: 118
            spacing: 7

            Repeater {
                model: root.mainModes
                ModeButton {
                    required property var modelData
                    required property int index
                    width: mainModeRail.width
                    height: 54
                    textOnly: true
                    labelText: modelData.label
                    labelFontSize: 11
                    bordered: false
                    selected: root.selectedMainModeIndex === index
                    idlePrimaryColor: Colors.yellow
                    hoverPrimaryColor: Colors.blue
                    selectedPrimaryColor: Colors.blue
                    perimeterGlowColor: Colors.blue
                    onTriggered: root.selectedMainModeIndex = index
                }
            }
        }

        Rectangle {
            anchors.top: mainModeRail.top
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 15
            anchors.left: mainModeRail.right
            anchors.leftMargin: 8
            width: 2
            color: Colors.cyan
            opacity: 0.8
        }

        Item {
            id: contentPane
            anchors.top: headerDivider.bottom
            anchors.topMargin: 20
            anchors.left: mainModeRail.right
            anchors.leftMargin: 25
            anchors.right: parent.right
            anchors.rightMargin: 20
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 18

            Column {
                anchors.fill: parent
                spacing: 16

                GohuText {
                    width: parent.width
                    font.pixelSize: 19
                    font.bold: true
                    color: Colors.yellow
                    text: root.activeMode.title
                    wrapMode: Text.WordWrap
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 12
                    color: Colors.white
                    wrapMode: Text.WordWrap
                    text: root.activeMode.detail
                }

                Rectangle {
                    width: parent.width
                    height: 90
                    color: Colors.dark
                    border.color: Colors.blue
                    border.width: 1

                    Column {
                        anchors.centerIn: parent
                        spacing: 8
                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            font.pixelSize: 15
                            color: Colors.yellow
                            text: "GEOGRAPHIC NETWORK // V0"
                        }
                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            font.pixelSize: 11
                            color: Colors.white
                            text: "UI SCAFFOLD ONLY"
                        }
                    }
                }
            }
        }
    }
}
