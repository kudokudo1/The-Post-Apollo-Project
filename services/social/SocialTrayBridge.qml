pragma Singleton

import QtQuick
import Quickshell

// Same-process activation link between the system tray and Social. No
// external qs process, D-Bus call, session state, or persistent storage.
// Tray owns the gesture; MessagingW owns opening and docking Vesktop.
Singleton {
    id: router

    signal discordActivationRequested()

    function requestDiscordActivation() {
        discordActivationRequested();
    }
}
