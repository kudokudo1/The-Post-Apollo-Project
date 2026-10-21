import QtQuick
import Quickshell
import Quickshell.Wayland
import "modules"
import "widgets"

// Standalone click-and-keyboard harness for ApolloHubW.
// Does not replace Calendar or touch the live shell.qml.
Scope {
    PanelWindow {
        id: previewDockWindow
        screen: Quickshell.screens.find(s => s.name === "DP-5")
        anchors {
            top: true
            left: true
        }
        margins {
            top: 76
            left: 50
        }
        implicitWidth: 113
        implicitHeight: 50
        exclusiveZone: 0
        WlrLayershell.layer: WlrLayer.Overlay
        color: "transparent"

        ApolloHub {
            id: dock
            anchors.fill: parent
            menuOpen: window.menuOpen
            onToggleRequested: window.toggle()
        }

        ApolloHubW {
            id: window
            screen: previewDockWindow.screen
            keyboardActive: true
        }
    }
}
