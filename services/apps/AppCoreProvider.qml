import QtQuick
import Quickshell

// Team 8 — APPS Core
//
// Standalone provider seam prepared on certified fused baseline 943d273.
//
// This file is intentionally NOT wired into AppControlW yet. It owns APPS
// catalog/source behavior only after shared physiology is removed.
//
// It does not own:
//   - application/window/tab semantic identity (Team 7)
//   - tab/surface discovery or activation (Team 5)
//   - application/window/tab audio (Team 6)
//   - process/resource scope, limits, freeze or termination (Team 1)
//   - Favorites persistence/reconstruction (Team 2)
//   - RUN command discovery/history (future RunService)
//
// HIDDEN rows are adapted separately by AppHiddenAdapter from the future
// RunService command catalog; this provider does not own a duplicate HIDDEN
// catalog seam.
QtObject {
    id: provider

    readonly property int sourceNative: 0
    readonly property int sourceFlatpak: 1
    readonly property int sourceHidden: 2

    readonly property int launchNormal: 0
    readonly property int launchToolbox: 1
    readonly property int launchBottle: 2

    function desktopEntries() {
        const values = DesktopEntries.applications.values;

        if (!values)
            return [];

        return [...values];
    }

    function entryIsFlatpak(entry) {
        if (!entry)
            return false;

        const command = entry.command || [];
        const joined = Array.isArray(command)
                       ? command.map(function(token) {
                             return String(token || "").toLowerCase();
                         }).join(" ")
                       : String(command || "").toLowerCase();

        return joined.indexOf("flatpak run") !== -1
               || joined.indexOf("/flatpak ") !== -1
               || joined.indexOf("flatpak --") !== -1;
    }

    function sourceLabel(entry) {
        if (entry && entry._hiddenCommand)
            return "HIDDEN";

        return entryIsFlatpak(entry) ? "FLATPAK" : "NORMAL";
    }

    function entryHasLaunchCommand(entry) {
        if (!entry)
            return false;

        const command = entry.command;

        if (Array.isArray(command))
            return command.length > 0
                   && String(command[0] || "").trim().length > 0;

        return String(command || "").trim().length > 0;
    }

    function entryMatchesSource(entry, sourceMode) {
        if (!entry)
            return false;

        if (sourceMode === sourceHidden)
            return !!entry._hiddenCommand;

        if (entry._hiddenCommand)
            return false;

        const flatpak = entryIsFlatpak(entry);

        return sourceMode === sourceFlatpak
               ? flatpak
               : !flatpak;
    }

    function entryLaunchableForSource(entry, sourceMode) {
        if (!entry || !entryHasLaunchCommand(entry))
            return false;

        if (sourceMode === sourceHidden)
            return !!entry._hiddenCommand;

        if (entry._hiddenCommand)
            return false;

        // Preserve donor semantics:
        // NORMAL may launch native or Flatpak desktop entries.
        // FLATPAK is strict and only launches Flatpak entries.
        if (sourceMode === sourceFlatpak)
            return entryIsFlatpak(entry);

        return true;
    }

    function actionsAvailableForSource(entry, sourceMode) {
        if (!entry)
            return false;

        if (sourceMode === sourceFlatpak && !entryIsFlatpak(entry))
            return false;

        if (sourceMode === sourceHidden)
            return !!entry._hiddenCommand;

        return !entry._hiddenCommand;
    }


}
