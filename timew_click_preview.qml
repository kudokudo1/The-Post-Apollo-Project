import QtQuick
import Quickshell
import Quickshell.Wayland
import "modules"
import "widgets"

// Standalone click + keyboard preview. Not loaded by shell.qml.
// Launch as a separate Quickshell configuration, never by restarting the bar.
Scope {
    PanelWindow {
        id: previewDockWindow
        screen: Quickshell.screens.find(s => s.name === "DP-5")
        anchors {
            top: true
            right: true
        }
        margins {
            top: 76
            right: 13
        }
        implicitWidth: clock.width
        implicitHeight: clock.height
        exclusiveZone: 0
        WlrLayershell.layer: WlrLayer.Overlay
        color: "transparent"
        mask: Region {
            width: clock.width
            height: 50
        }

        Clock {
            id: clock
            timeWindow: timewWindow
        }

        TimeW {
            id: timewWindow
            screen: previewDockWindow.screen
            keyboardActive: true
        }
    }
}
