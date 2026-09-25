import QtQuick
import Quickshell

Scope {
    id: systemControl

    // Shared mutation backend only. Confirmation UI, keyboard/focus state,
    // selection state, and refresh scheduling policy remain with each host.
    required property var processControl

    signal refreshRequested()
    signal rebootRequested(var entry)

    function runComponentAction(entry, action) {
        if (!entry || !action)
            return false;

        if (action === "disconnect") {
            if (entry.controlKind !== "network"
                    || !entry.canDisconnect
                    || !entry.controlTarget)
                return false;

            Quickshell.execDetached([
                "nmcli",
                "device",
                "disconnect",
                String(entry.controlTarget)
            ]);

            refreshRequested();
            return true;
        }

        if (action === "reconnect") {
            if (entry.controlKind !== "network"
                    || !entry.canReconnect
                    || !entry.controlTarget)
                return false;

            Quickshell.execDetached([
                "nmcli",
                "device",
                "connect",
                String(entry.controlTarget)
            ]);

            refreshRequested();
            return true;
        }

        if (action === "reboot") {
            if (!entry.canReboot)
                return false;

            // The host owns the confirmation surface. It may call
            // executeReboot() only after the user confirms.
            rebootRequested(entry);
            return true;
        }

        return false;
    }

    function executeReboot() {
        Quickshell.execDetached([
            "systemctl",
            "reboot"
        ]);

        return true;
    }

    function terminateContributor(entry) {
        if (!entry
                || !entry.killable
                || Number(entry.pid || 0) <= 1)
            return false;

        if (!processControl
                || !processControl.sendSignal(
                    Number(entry.pid || 0),
                    "-TERM"
                ))
            return false;

        refreshRequested();
        return true;
    }
}
