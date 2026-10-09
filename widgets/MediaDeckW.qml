import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"

// Initial Hi-Fi deck chassis. Adapted from MenuTemplate.qml.template:
// a transparent PanelWindow, explicit open state, screen-edge anchors and
// three structural sections. Hardware artwork/controls come later.
PanelWindow {
    id: deck

    property bool menuOpen: false

    // Keep the first pass easy to resize/reposition during the design phase.
    property int panelWidth: 520
    property int panelHeight: 850
    property int panelTopMargin: 78
    property int panelLeftMargin: 200
    property int contentInset: 14
    property int sectionSpacing: 10
    // The three functional zones are now stacked, with controls receiving
    // the largest share. These proportions are still design parameters.
    property real displayHeightShare: 0.34
    property real cassetteHeightShare: 0.24

    // Only the local MPD backend is connected in this prototype.
    // A shared source-neutral transport service is a later milestone.
    function runLocalTransport(action) {
        const commands = {
            previous: ["mpc", "prev"],
            play: ["mpc", "play"],
            pause: ["mpc", "pause", "1"],
            next: ["mpc", "next"],
            rewind5: ["mpc", "seek", "-5"],
            forward5: ["mpc", "seek", "+5"],
            stop: ["mpc", "stop"]
        };

        const command = commands[action];
        if (command)
            Quickshell.execDetached(command);
    }

    screen: Quickshell.screens.find(s => s.name === "DP-5")

    visible: menuOpen
    implicitWidth: panelWidth
    implicitHeight: panelHeight
    color: "transparent"
    exclusiveZone: 0

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

    anchors {
        top: true
        left: true
        right: false
        bottom: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin
        right: 0
        bottom: 0
    }

    SurfaceFrame {
        anchors.fill: parent

        fillColor: Colors.black
        fillOpacity: 0.96
        borderColor: Colors.cyan
        borderWidth: 2

        Column {
            id: deckSections

            anchors.fill: parent
            anchors.margins: deck.contentInset
            spacing: deck.sectionSpacing

            // Top zone: the future text-first browser and playback display.
            SectionFrame {
                id: displaySection
                width: parent.width
                height: Math.round(
                    (deckSections.height - 2 * deckSections.spacing)
                    * deck.displayHeightShare
                )
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "DISPLAY / BROWSER"
                    color: Colors.cyan
                    font.pixelSize: 16
                }
            }

            // Middle zone: the future cassette or alternative loaded medium.
            SectionFrame {
                id: cassetteSection
                width: parent.width
                height: Math.round(
                    (deckSections.height - 2 * deckSections.spacing)
                    * deck.cassetteHeightShare
                )
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "CASSETTE BAY"
                    color: Colors.cyan
                    font.pixelSize: 16
                }
            }

            // Zone C — first tactile transport test, not the final hardware.
            SectionFrame {
                width: parent.width
                height: deckSections.height
                        - displaySection.height
                        - cassetteSection.height
                        - 2 * deckSections.spacing
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "CONTROLS"
                    color: Colors.cyan
                    font.pixelSize: 16
                }

                GohuText {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    text: "LOCAL / MPD"
                    color: Colors.orange
                    font.pixelSize: 11
                }

                Grid {
                    id: transportGrid

                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        topMargin: 48
                    }

                    columns: 4
                    spacing: 8

                    Repeater {
                        model: [
                            { label: "PREV", action: "previous" },
                            { label: "PLAY", action: "play" },
                            { label: "PAUSE", action: "pause" },
                            { label: "NEXT", action: "next" },
                            { label: "-5 SEC", action: "rewind5" },
                            { label: "+5 SEC", action: "forward5" },
                            { label: "STOP", action: "stop" }
                        ]

                        Rectangle {
                            id: transportKey

                            required property var modelData

                            width: (transportGrid.width
                                    - 3 * transportGrid.spacing) / 4
                            height: 50
                            radius: 3

                            color: keyMouse.pressed
                                   ? "#16131B"
                                   : keyMouse.containsMouse
                                   ? "#39333E"
                                   : "#29252E"

                            border.width: 1
                            border.color: keyMouse.pressed
                                          ? Colors.orange
                                          : keyMouse.containsMouse
                                          ? Colors.cyan
                                          : "#69616F"

                            transform: Translate {
                                y: keyMouse.pressed ? 1 : 0
                            }

                            GohuText {
                                anchors.centerIn: parent
                                text: transportKey.modelData.label
                                font.pixelSize: 12
                                color: keyMouse.pressed
                                       ? Colors.orange
                                       : keyMouse.containsMouse
                                       ? Colors.cyan
                                       : Colors.white
                            }

                            MouseArea {
                                id: keyMouse
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked: deck.runLocalTransport(
                                    transportKey.modelData.action
                                )
                            }
                        }
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    text: "TRANSPORT // FIRST HARDWARE TEST"
                    color: Colors.cyan
                    opacity: 0.6
                    font.pixelSize: 10
                }
            }
        }
    }
}
