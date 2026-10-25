import QtQuick
import Quickshell
import Quickshell.Wayland
import "../../components"

PanelWindow {
    id: discordBackingWindow

    // MessagingW remains the source of truth for where the Discord region
    // belongs. This window only supplies the blank purple surface underneath
    // the real Vesktop window.
    property var hostSocial: null

    // Never fall back to one specific monitor: use the active Social screen.
    screen: hostSocial ? hostSocial.screen : null

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
        top: hostSocial && screen ? Math.round(hostSocial.discordY - screen.y) : 0

        right: hostSocial && screen ? Math.round((screen.x + screen.width) - (hostSocial.discordX + hostSocial.discordWidth)) : 0
    }

    implicitWidth: hostSocial ? Math.max(1, hostSocial.discordWidth) : 1

    implicitHeight: hostSocial ? Math.max(1, hostSocial.discordHeight) : 1

    // A true bottom-layer panel, never a Sway desktop application window.
    // The AppSelector remains in Social's regular FloatingWindow; the
    // floating Vesktop client draws over this empty backing.
    WlrLayershell.layer: WlrLayer.Bottom

    exclusiveZone: 0

    color: "transparent"
    surfaceFormat.opaque: false

    // The backing exists only while Discord is selected and is
    // click-through. Its content never belongs in the normal overlay layer.
    visible: hostSocial !== null && hostSocial.menuOpen
             && hostSocial.discordSelected

    mask: Region {
        x: 0
        y: 0
        width: 0
        height: 0
    }

    Rectangle {
        anchors.fill: parent

        color: Colors.black

        // Visual backing for the *empty* Contact List and Chat Feed shells.
        // It never covers the app's Sway surface: WlrLayer.Bottom remains
        // below floating Vesktop.
        opacity: 0.85

        radius: 0
    }
}
