import QtQuick
import Quickshell

// Team 8 — APPS Core
//
// Standalone provider seam prepared on certified fused baseline 943d273.
//
// This file is intentionally NOT wired into AppControlW yet. It owns only
// behavior that remains APPS-specific after shared physiology is removed.
//
// It does not own:
//   - application/window/tab semantic identity (Team 7)
//   - tab/surface discovery or activation (Team 5)
//   - application/window/tab audio (Team 6)
//   - process/resource scope, limits, freeze or termination (Team 1)
//   - Favorites persistence/reconstruction (Team 2)
//   - RUN command discovery/history (future RunService)
//
// HIDDEN entries are accepted through hiddenEntries so the future RunService
// can supply them without APPS rebuilding a second command catalog.
QtObject {
    id: provider

    readonly property int sourceNative: 0
    readonly property int sourceFlatpak: 1
    readonly property int sourceHidden: 2

    readonly property int launchNormal: 0
    readonly property int launchToolbox: 1
    readonly property int launchBottle: 2

    // Future RunService adapter input. Records remain provider-owned by RUN;
    // APPS only consumes application-shaped rows supplied through this seam.
    property var hiddenEntries: []

    // APPS-local presentation overrides. These intentionally do not define
    // semantic identity; Team 7 remains authoritative for identity joins.
    property var appOverrides: ({})

    function desktopEntries() {
        const values = DesktopEntries.applications.values;

        if (!values)
            return [];

        return [...values];
    }

    function sourceEntries(sourceMode) {
        if (sourceMode === sourceHidden)
            return Array.isArray(hiddenEntries)
                   ? hiddenEntries.slice()
                   : [];

        // Preserve donor behavior: NORMAL and FLATPAK both inspect the same
        // DesktopEntries catalog. The source selector changes classification /
        // action availability rather than hiding the other package form.
        return desktopEntries();
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

    function appOverride(entry) {
        if (!entry || !entry.name)
            return null;

        return appOverrides[entry.name] || null;
    }

    function displayName(entry) {
        if (!entry)
            return "NO SELECTION";

        const override = appOverride(entry);

        return override && override.name
               ? override.name
               : (entry.name || "APPLICATION");
    }

    function displayDescription(entry) {
        if (!entry)
            return "";

        const override = appOverride(entry);

        if (override && override.description)
            return override.description;

        return entry.genericName || entry.comment || "APPLICATION";
    }

    function longDescription(entry) {
        if (!entry)
            return "";

        const override = appOverride(entry);

        if (override && override.longDescription)
            return override.longDescription;

        return entry.comment || "";
    }

    function displayIcon(entry) {
        if (!entry)
            return "";

        const override = appOverride(entry);

        return override && override.icon
               ? override.icon
               : (entry.icon || "");
    }

    function iconSource(entry) {
        const icon = displayIcon(entry);

        if (!icon)
            return "";

        if (icon.indexOf("/") === 0 || icon.indexOf("file:") === 0)
            return icon;

        return Quickshell.iconPath(icon, true);
    }
}
