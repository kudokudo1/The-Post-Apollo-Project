import QtQuick

// Team 8 — APPS Core action planning.
//
// Converts DesktopEntry/browser actions into pure execution intent. This file
// does not focus Sway windows, synthesize keys, launch processes, mutate host
// state, or own Favorites persistence.
//
// It preserves the donor's action-policy ordering while leaving execution to
// the eventual launch/action executor.
QtObject {
    id: planner

    required property var actionCatalog

    readonly property string planDesktopAction: "desktop-action"
    readonly property string planBrowserShortcut: "browser-shortcut"
    readonly property string planBrowserLaunch: "browser-launch"
    readonly property string planUnavailable: "unavailable"

    function stableActionId(action, fallbackIndex) {
        if (action && action._appControlBuiltin)
            return "builtin|" + String(action._appControlBuiltin);

        return "desktop|"
            + encodeURIComponent(
                String(
                    action && action.name
                    ? action.name
                    : Number(fallbackIndex || 0)
                )
            );
    }

    function desktopActionPlan(action, fallbackIndex) {
        if (!action) {
            return {
                kind: planUnavailable,
                reason: "missing-action",
                stableId: ""
            };
        }

        if (action._appControlBuiltin) {
            return browserBuiltinPlan(
                String(action._appControlBuiltin),
                null,
                fallbackIndex
            );
        }

        return {
            kind: planDesktopAction,
            action: action,
            stableId: stableActionId(action, fallbackIndex)
        };
    }

    function browserBuiltinPlan(action, entry, fallbackIndex) {
        const browser = actionCatalog.browserKind(entry);
        const id = String(action || "");
        const stableId = "builtin|" + id;

        if (!browser) {
            return {
                kind: planUnavailable,
                reason: "not-browser",
                stableId: stableId
            };
        }

        // Preserve donor precedence: when a native browser shortcut exists,
        // it wins over command-line launch destinations.
        const shortcut = actionCatalog.shortcutSequence(browser, id);

        if (shortcut.length > 0) {
            return {
                kind: planBrowserShortcut,
                browserKind: browser,
                action: id,
                sequence: shortcut.slice(),
                stableId: stableId
            };
        }

        // Donor special case: Gecko-family downloads is a stable about: page
        // launched through the browser command rather than a shortcut.
        if (browser !== "brave" && id === "downloads") {
            return {
                kind: planBrowserLaunch,
                browserKind: browser,
                action: id,
                extraArgs: ["--new-tab", "about:downloads"],
                stableId: stableId
            };
        }

        const extra = actionCatalog.launchArguments(browser, id);

        if (extra.length > 0) {
            return {
                kind: planBrowserLaunch,
                browserKind: browser,
                action: id,
                extraArgs: extra.slice(),
                stableId: stableId
            };
        }

        return {
            kind: planUnavailable,
            reason: "unsupported-browser-action",
            browserKind: browser,
            action: id,
            stableId: stableId,
            fallbackIndex: Number(fallbackIndex || 0)
        };
    }

    function plan(action, entry, fallbackIndex) {
        if (!action) {
            return {
                kind: planUnavailable,
                reason: "missing-action",
                stableId: ""
            };
        }

        if (action._appControlBuiltin) {
            return browserBuiltinPlan(
                String(action._appControlBuiltin),
                entry,
                fallbackIndex
            );
        }

        return {
            kind: planDesktopAction,
            action: action,
            stableId: stableActionId(action, fallbackIndex)
        };
    }
}
