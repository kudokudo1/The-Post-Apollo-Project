import QtQuick
import Quickshell
import Quickshell.Wayland
import "../../components"

PanelWindow {
    id: discordBackingWindow

    // MessagingW remains the source of truth for where the Discord region
    // belongs. This window only supplies the blank purple surface underneath
    // the real Vesktop window.
    property var messagingWindow: null

    screen: messagingWindow && messagingWindow.screen ? messagingWindow.screen : Quickshell.screens.find(s => s.name === "DP-5")

    anchors {
        top: true
        bottom: false
        left: false
        right: true
    }

    // Position this backing from the same GLOBAL Discord rectangle that
    // MessagingW uses for Vesktop. That keeps the backing aligned even though
    // this surface lives on a different layer-shell layer.
    margins {
        top: messagingWindow && screen ? Math.round(messagingWindow.discordY - screen.y) : 0

        right: messagingWindow && screen ? Math.round((screen.x + screen.width) - (messagingWindow.discordX + messagingWindow.discordWidth)) : 0
    }

    implicitWidth: messagingWindow ? Math.max(1, messagingWindow.discordWidth) : 1

    implicitHeight: messagingWindow ? Math.max(1, messagingWindow.discordHeight) : 1

    // This is deliberately BELOW normal application windows.
    // MessagingW itself stays Overlay so AppSelector remains above Discord.
    WlrLayershell.layer: WlrLayer.Bottom

    exclusiveZone: 0

    color: "transparent"
    surfaceFormat.opaque: false

    // Keep the native surface alive, like MessagingW, but make it completely
    // click-through.
    visible: true

    mask: Region {
        x: 0
        y: 0
        width: 0
        height: 0
    }

    Rectangle {
        anchors.fill: parent

        color: Colors.black

        // Match ChatFeed's current base background.
        opacity: discordBackingWindow.messagingWindow && discordBackingWindow.messagingWindow.menuOpen && discordBackingWindow.messagingWindow.discordSelected ? 0.85 : 0.0

        radius: 0
    }
}
