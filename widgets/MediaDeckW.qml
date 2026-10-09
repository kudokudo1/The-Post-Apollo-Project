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
    property int panelWidth: 960
    property int panelHeight: 370
    property int panelTopMargin: 78
    property int panelLeftMargin: 200
    property int contentInset: 14
    property int sectionSpacing: 10

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

        Row {
            id: deckSections

            anchors.fill: parent
            anchors.margins: deck.contentInset
            spacing: deck.sectionSpacing

            // Zone A — the future loadable cassette and animated label.
            SectionFrame {
                id: cassetteSection
                height: parent.height
                width: Math.round(
                    (deckSections.width - 2 * deckSections.spacing) * 0.44
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

            // Zone B — player information and meters, not a fixed UI yet.
            SectionFrame {
                id: displaySection
                height: parent.height
                width: Math.round(
                    (deckSections.width - 2 * deckSections.spacing) * 0.29
                )
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "DISPLAY / METERS"
                    color: Colors.cyan
                    font.pixelSize: 16
                }
            }

            // Zone C — reserved for the eventual transport/selector layout.
            SectionFrame {
                height: parent.height
                width: deckSections.width
                       - cassetteSection.width
                       - displaySection.width
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
            }
        }
    }
}
