import QtQuick
import Quickshell
import Quickshell.Wayland
import "modules"
import "widgets"

// Isolated click-preview for the Company Network dock and window.
// This is NOT loaded by shell.qml and does not modify the live taskbar.
Scope {
    PanelWindow {
        id: previewDockWindow
        screen: Quickshell.screens.find(s => s.name === "DP-5")
                || Quickshell.screens[0]
        anchors {
            top: true
            left: true
        }
        margins {
            top: 76
            left: 50
        }
        implicitWidth: companyButton.implicitWidth
        implicitHeight: 50
        exclusiveZone: 0
        WlrLayershell.layer: WlrLayer.Overlay
        color: "transparent"

        CompanyNetwork {
            id: companyButton
            anchors.fill: parent
            menuOpen: companyWindow.menuOpen
            onToggleRequested: companyWindow.toggle()
        }

        CompanyNetworkW {
            id: companyWindow
            screen: previewDockWindow.screen
            dockCenterX: previewDockWindow.margins.left + companyButton.width / 2
            chassisTopY: 145
        }
    }
}
