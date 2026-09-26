import QtQuick
import Quickshell

// Team 8 — APPS Core metadata/presentation policy.
//
// Owns APPS-local display metadata and presentation overrides only.
// It does not classify semantic identity, discover applications, mutate host
// navigation, or own global theme state.
QtObject {
    id: presentation

    property var appOverrides: ({})

    function overrideFor(entry) {
        if (!entry || !entry.name)
            return null;

        return appOverrides[entry.name] || null;
    }

    function displayName(entry) {
        if (!entry)
            return "NO SELECTION";

        const override = overrideFor(entry);

        return override && override.name
               ? override.name
               : (entry.name || "APPLICATION");
    }

    function displayDescription(entry) {
        if (!entry)
            return "";

        const override = overrideFor(entry);

        if (override && override.description)
            return override.description;

        return entry.genericName || entry.comment || "APPLICATION";
    }

    function longDescription(entry) {
        if (!entry)
            return "";

        const override = overrideFor(entry);

        if (override && override.longDescription)
            return override.longDescription;

        return entry.comment || "";
    }

    function displayIcon(entry) {
        if (!entry)
            return "";

        const override = overrideFor(entry);

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
