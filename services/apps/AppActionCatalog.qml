import QtQuick

// Team 8 — APPS Core desktop/browser action catalog.
//
// Pure APPS behavior only. This catalog describes actions exposed by a
// DesktopEntry and the extra browser-wide actions AppControl layers on top.
// It performs no process execution, no tab discovery, no window matching,
// no audio work and no semantic application identity joins.
//
// browserKind() is intentionally a local behavior classifier, not a canonical
// identity decision. Team 7 remains authoritative for cross-provider identity.
QtObject {
    id: catalog

    function browserKind(entry) {
        if (!entry)
            return "";

        const behaviorHints = [
            entry.name || "",
            entry.id || "",
            entry.execString || "",
            entry.command || "",
            entry.comment || "",
            entry.startupClass || ""
        ].join(" ").toLowerCase();

        if (behaviorHints.indexOf("mullvad") !== -1)
            return "mullvad";

        if (behaviorHints.indexOf("brave") !== -1)
            return "brave";

        if (behaviorHints.indexOf("firefox") !== -1)
            return "firefox";

        return "";
    }

    function appendBuiltin(actions, kind, name) {
        actions.push({
            _appControlBuiltin: kind,
            name: name,
            icon: ""
        });
    }

    function desktopActions(entry) {
        if (!entry || entry._hiddenCommand)
            return [];

        const actions = [];
        const rawActions = entry.actions;

        // Preserve every action already published by the DesktopEntry.
        if (rawActions) {
            if (Array.isArray(rawActions)) {
                for (let i = 0; i < rawActions.length; i++)
                    actions.push(rawActions[i]);
            } else if (rawActions.values
                    && rawActions.values.length !== undefined) {
                for (let i = 0; i < rawActions.values.length; i++)
                    actions.push(rawActions.values[i]);
            } else if (rawActions.length !== undefined) {
                for (let i = 0; i < rawActions.length; i++)
                    actions.push(rawActions[i]);
            }
        }

        const kind = browserKind(entry);

        if (!kind)
            return actions;

        let hasNewWindow = false;
        let hasPrivateWindow = false;

        for (let i = 0; i < actions.length; i++) {
            const actionName =
                String(actions[i] && actions[i].name || "").toLowerCase();

            const privateAction =
                actionName.indexOf("incognito") !== -1
                || actionName.indexOf("private") !== -1;

            if (actionName.indexOf("new") !== -1
                    && actionName.indexOf("window") !== -1
                    && !privateAction) {
                hasNewWindow = true;
            }

            if (actionName.indexOf("new") !== -1
                    && actionName.indexOf("window") !== -1
                    && privateAction) {
                hasPrivateWindow = true;
            }
        }

        if (!hasNewWindow)
            appendBuiltin(actions, "new-window", "NEW WINDOW");

        if (!hasPrivateWindow) {
            appendBuiltin(
                actions,
                "new-private-window",
                kind === "brave"
                ? "NEW INCOGNITO WINDOW"
                : "NEW PRIVATE WINDOW"
            );
        }

        appendBuiltin(actions, "new-tab", "NEW TAB");
        appendBuiltin(actions, "history", "HISTORY");
        appendBuiltin(actions, "downloads", "DOWNLOADS");
        appendBuiltin(actions, "bookmarks", "BOOKMARKS");

        appendBuiltin(
            actions,
            "extensions",
            kind === "brave"
            ? "EXTENSIONS"
            : "ADD-ONS / EXTENSIONS"
        );

        appendBuiltin(actions, "settings", "SETTINGS");
        appendBuiltin(actions, "devtools", "DEVELOPER TOOLS");
        appendBuiltin(actions, "clear-data", "CLEAR BROWSING DATA");

        if (kind === "brave") {
            appendBuiltin(actions, "restore", "RESTORE RECENT TAB");
            appendBuiltin(actions, "task-manager", "TASK MANAGER");
        } else {
            appendBuiltin(actions, "passwords", "PASSWORDS");
            appendBuiltin(actions, "profile-manager", "PROFILE MANAGER");

            if (kind === "firefox")
                appendBuiltin(actions, "firefox-view", "FIREFOX VIEW");
        }

        return actions;
    }

    function shortcutSequence(browser, action) {
        const kind = String(browser || "");
        const id = String(action || "");

        if (id === "history")
            return kind === "brave"
                   ? ["ctrl", "h"]
                   : ["ctrl", "shift", "h"];

        if (id === "downloads")
            return kind === "brave" ? ["ctrl", "j"] : [];

        if (id === "bookmarks")
            return ["ctrl", "shift", "o"];

        if (id === "clear-data")
            return ["ctrl", "shift", "Delete"];

        if (id === "restore" && kind === "brave")
            return ["ctrl", "shift", "t"];

        if (id === "task-manager" && kind === "brave")
            return ["shift", "Escape"];

        if (id === "devtools")
            return ["F12"];

        return [];
    }

    function launchArguments(browser, action) {
        const kind = String(browser || "");
        const id = String(action || "");

        if (kind === "brave") {
            if (id === "new-window")
                return ["--new-window"];

            if (id === "new-tab")
                return ["--new-tab", "brave://newtab/"];

            if (id === "new-private-window")
                return ["--incognito", "--new-window"];

            if (id === "extensions")
                return ["brave://extensions/"];

            if (id === "settings")
                return ["brave://settings/"];

            return [];
        }

        if (id === "new-window")
            return ["--new-window", "about:newtab"];

        if (id === "new-tab")
            return ["--new-tab", "about:newtab"];

        if (id === "new-private-window")
            return ["--private-window"];

        if (id === "extensions")
            return ["--new-tab", "about:addons"];

        if (id === "settings")
            return ["--preferences"];

        if (id === "passwords")
            return ["--new-tab", "about:logins"];

        if (id === "profile-manager")
            return ["--ProfileManager"];

        if (id === "firefox-view")
            return ["--new-tab", "about:firefoxview"];

        return [];
    }
}
