import QtQuick

// Team 8 — APPS Core action execution descriptor builder.
//
// Pure descriptor construction only. No process launch, Sway focus, virtual
// keyboard synthesis, host navigation, or Favorites mutation.
//
// Browser shortcut execution intentionally stops at a neutral request:
//   source DesktopEntry + browser kind + key sequence.
// A future executor may resolve/focus the correct running application/window
// through the shared window/identity architecture before synthesizing keys.
QtObject {
    id: builder

    required property var launchPlanner

    readonly property string commandDesktopAction: "desktop-action-execute"
    readonly property string commandBrowserLaunch: "browser-launch-argv"
    readonly property string commandBrowserShortcut: "browser-shortcut-request"
    readonly property string commandUnavailable: "unavailable"

    function unavailable(reason, plan) {
        return {
            kind: commandUnavailable,
            reason: String(reason || "unavailable"),
            plan: plan || null
        };
    }

    function buildDesktopAction(plan) {
        if (!plan || !plan.action)
            return unavailable("missing-desktop-action", plan);

        return {
            kind: commandDesktopAction,
            action: plan.action,
            entry: plan.entry || null,
            stableId: String(plan.stableId || ""),
            plan: plan
        };
    }

    function buildBrowserShortcut(plan) {
        const sequence = Array.isArray(plan && plan.sequence)
            ? plan.sequence.slice()
            : [];

        if (sequence.length === 0)
            return unavailable("missing-browser-shortcut", plan);

        return {
            kind: commandBrowserShortcut,
            browserKind: String(plan.browserKind || ""),
            action: String(plan.action || ""),
            sequence: sequence,
            entry: plan.entry || null,
            stableId: String(plan.stableId || ""),
            plan: plan
        };
    }

    function buildBrowserLaunch(plan) {
        if (!plan || !plan.entry)
            return unavailable("missing-browser-entry", plan);

        const tokens =
            launchPlanner.cleanedCommandTokens(plan.entry);

        // Preserve donor behavior: browser launch actions are only executed
        // when a concrete argv form exists. Opaque shell command strings do
        // not get rewritten here.
        if (tokens.length === 0)
            return unavailable("missing-browser-command", plan);

        if (tokens[0] === "__APPCONTROL_SHELL__") {
            return unavailable(
                "browser-launch-shell-command-unresolved",
                plan
            );
        }

        return {
            kind: commandBrowserLaunch,
            argv: tokens.concat(
                Array.isArray(plan.extraArgs)
                ? plan.extraArgs
                : []
            ),
            entry: plan.entry,
            browserKind: String(plan.browserKind || ""),
            action: String(plan.action || ""),
            stableId: String(plan.stableId || ""),
            plan: plan
        };
    }

    function build(plan) {
        if (!plan)
            return unavailable("missing-plan", null);

        if (plan.kind === "unavailable")
            return unavailable(plan.reason || "unavailable", plan);

        if (plan.kind === "desktop-action")
            return buildDesktopAction(plan);

        if (plan.kind === "browser-shortcut")
            return buildBrowserShortcut(plan);

        if (plan.kind === "browser-launch")
            return buildBrowserLaunch(plan);

        return unavailable("unknown-action-plan-kind", plan);
    }
}
