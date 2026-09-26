import QtQuick

// Team 8 — APPS detail-action topology.
//
// Pure APPS policy only. This organ describes which APPS detail actions occupy
// which positions and their stable provider-owned IDs.
//
// It does not:
//   - mutate host selection/focus/navigation
//   - execute launches/actions
//   - own Favorites persistence
//   - own audio physiology (Team 6)
//   - own process/resource physiology (Team 1)
//
// Cross-team availability is supplied as plain facts by the eventual consumer.
QtObject {
    id: policy

    required property var actionCatalog
    required property var actionPlanner

    readonly property string actionLaunch: "launch"
    readonly property string actionHiddenKitty: "hidden-kitty"
    readonly property string actionHiddenFloat: "hidden-float"
    readonly property string actionHiddenFullscreen: "hidden-fullscreen"
    readonly property string actionHiddenBottles: "hidden-bottles"
    readonly property string actionHiddenToolbox: "hidden-toolbox"
    readonly property string actionHiddenKill: "hidden-kill"
    readonly property string actionBottles: "bottles"
    readonly property string actionToolbox: "toolbox"
    readonly property string actionMute: "mute-app"
    readonly property string actionFreeze: "freeze-app"
    readonly property string actionKill: "kill"
    readonly property string actionDesktop: "desktop-action"
    readonly property string actionUnavailable: "unavailable"

    function desktopActions(entry) {
        return actionCatalog.desktopActions(entry);
    }

    function actionCount(entry) {
        if (!entry)
            return 0;

        if (entry._hiddenCommand)
            return 7;

        return 6 + desktopActions(entry).length;
    }

    function stableId(entry, actionIndex) {
        if (!entry || actionIndex < 0)
            return "";

        if (actionIndex === 0)
            return actionLaunch;

        if (entry._hiddenCommand) {
            if (actionIndex === 1) return actionHiddenKitty;
            if (actionIndex === 2) return actionHiddenFloat;
            if (actionIndex === 3) return actionHiddenFullscreen;
            if (actionIndex === 4) return actionHiddenBottles;
            if (actionIndex === 5) return actionHiddenToolbox;
            if (actionIndex === 6) return actionHiddenKill;
            return "";
        }

        const actions = desktopActions(entry);
        const desktopCount = actions.length;

        if (actionIndex === desktopCount + 1)
            return actionBottles;

        if (actionIndex === desktopCount + 2)
            return actionToolbox;

        if (actionIndex === desktopCount + 3)
            return actionMute;

        if (actionIndex === desktopCount + 4)
            return actionFreeze;

        if (actionIndex === desktopCount + 5)
            return actionKill;

        const desktopIndex = actionIndex - 1;

        if (desktopIndex < 0 || desktopIndex >= desktopCount)
            return "";

        return actionPlanner.stableActionId(
            actions[desktopIndex],
            desktopIndex
        );
    }

    function descriptor(entry, actionIndex) {
        const id = stableId(entry, actionIndex);

        if (!id) {
            return {
                kind: actionUnavailable,
                stableId: "",
                index: Number(actionIndex)
            };
        }

        if (!entry._hiddenCommand) {
            const actions = desktopActions(entry);
            const desktopIndex = actionIndex - 1;

            if (desktopIndex >= 0 && desktopIndex < actions.length) {
                return {
                    kind: actionDesktop,
                    stableId: id,
                    index: Number(actionIndex),
                    desktopIndex: desktopIndex,
                    action: actions[desktopIndex]
                };
            }
        }

        return {
            kind: id,
            stableId: id,
            index: Number(actionIndex)
        };
    }

    function available(entry, actionIndex, facts) {
        if (!entry || actionIndex < 0)
            return false;

        const state = facts && typeof facts === "object"
            ? facts
            : {};

        if (state.actionsAvailable !== true)
            return false;

        if (actionIndex === 0)
            return state.launchable === true;

        if (entry._hiddenCommand) {
            if (actionIndex >= 1 && actionIndex <= 3)
                return true;

            if (actionIndex === 4)
                return !!state.bottleReady;

            if (actionIndex === 5 || actionIndex === 6)
                return String(entry.name || "").trim().length > 0;

            return false;
        }

        const actions = desktopActions(entry);
        const desktopCount = actions.length;

        if (actionIndex === desktopCount + 1)
            return !!state.bottleReady;

        if (actionIndex === desktopCount + 2)
            return !!state.toolboxLaunchable;

        if (actionIndex === desktopCount + 3)
            return !!state.audioAvailable;

        if (actionIndex === desktopCount + 4)
            return !!state.resourceFreezeAvailable;

        if (actionIndex === desktopCount + 5)
            return !!state.killAvailable;

        const desktopIndex = actionIndex - 1;

        return desktopIndex >= 0
            && desktopIndex < desktopCount;
    }
}
