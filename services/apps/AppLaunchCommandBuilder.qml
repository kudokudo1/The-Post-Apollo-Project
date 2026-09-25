import QtQuick

// Team 8 — APPS Core launch command builder.
//
// Pure command construction only. No process is started here.
//
// It converts AppLaunchPlanner intent into mechanism-specific execution
// descriptors while failing closed when a supplied SurfaceLaunch mutation
// cannot be carried safely by the selected mechanism.
QtObject {
    id: builder

    readonly property string commandDesktopEntry: "desktop-entry-execute"
    readonly property string commandArgv: "argv"
    readonly property string commandRunDispatch: "run-dispatch"
    readonly property string commandUnavailable: "unavailable"

    function hasEntries(map) {
        return !!map
            && typeof map === "object"
            && Object.keys(map).length > 0;
    }

    function hasArgMutation(augmentation) {
        if (!augmentation)
            return false;

        return (
            Array.isArray(augmentation.argvAfterExecutable)
            && augmentation.argvAfterExecutable.length > 0
        ) || (
            Array.isArray(augmentation.argvAppend)
            && augmentation.argvAppend.length > 0
        );
    }

    function envArgv(map) {
        if (!hasEntries(map))
            return [];

        const keys = Object.keys(map).sort();
        const result = ["env"];

        for (let i = 0; i < keys.length; i++) {
            const key = String(keys[i]);
            result.push(
                key + "=" + String(map[key] || "")
            );
        }

        return result;
    }

    function shellQuote(value) {
        return "'"
            + String(value || "").replace(/'/g, "'\"'\"'")
            + "'";
    }

    function unavailable(reason, plan) {
        return {
            kind: commandUnavailable,
            reason: String(reason || "unavailable"),
            plan: plan || null
        };
    }

    function buildDesktopEntry(plan, shellPath) {
        const augmentation =
            plan.surfaceLaunchAugmentation || null;
        const env = plan.launchEnv || {};
        const tokens = Array.isArray(plan.commandTokens)
            ? plan.commandTokens.slice()
            : [];

        // Preserve ordinary DesktopEntry execution when no launch mutation is
        // required. The eventual executor may call entry.execute().
        if (!augmentation) {
            return {
                kind: commandDesktopEntry,
                entry: plan.entry || null,
                plan: plan
            };
        }

        if (tokens.length === 0)
            return unavailable("missing-command", plan);

        if (tokens[0] === "__APPCONTROL_SHELL__") {
            // We can safely carry environment-only augmentation around an
            // opaque shell command. We cannot correctly place application argv
            // mutations without parsing/re-writing shell syntax.
            if (hasArgMutation(augmentation)) {
                return unavailable(
                    "surface-launch-shell-argv-transport-unresolved",
                    plan
                );
            }

            const shell = String(shellPath || "/bin/sh");

            return {
                kind: commandArgv,
                argv: envArgv(env).concat([
                    shell,
                    "-lc",
                    String(tokens[1] || "")
                ]),
                correlationId:
                    String(augmentation.correlationId || ""),
                plan: plan
            };
        }

        return {
            kind: commandArgv,
            argv: envArgv(env).concat(tokens),
            correlationId:
                String(augmentation.correlationId || ""),
            plan: plan
        };
    }

    function buildToolboxArgv(plan) {
        const env = plan.launchEnv || {};
        const command = ["toolbox", "run"];

        if (hasEntries(env))
            command.push.apply(command, envArgv(env));

        command.push.apply(
            command,
            Array.isArray(plan.argv)
            ? plan.argv
            : []
        );

        return {
            kind: commandArgv,
            argv: command,
            correlationId:
                plan.surfaceLaunchAugmentation
                ? String(
                      plan.surfaceLaunchAugmentation.correlationId || ""
                  )
                : "",
            plan: plan
        };
    }

    function buildToolboxShell(plan) {
        const augmentation =
            plan.surfaceLaunchAugmentation || null;

        if (augmentation && hasArgMutation(augmentation)) {
            return unavailable(
                "surface-launch-toolbox-shell-argv-transport-unresolved",
                plan
            );
        }

        const command = ["toolbox", "run"];
        const env = plan.launchEnv || {};

        if (hasEntries(env))
            command.push.apply(command, envArgv(env));

        command.push(
            "bash",
            "-lc",
            String(plan.shellText || "")
        );

        return {
            kind: commandArgv,
            argv: command,
            correlationId:
                augmentation
                ? String(augmentation.correlationId || "")
                : "",
            plan: plan
        };
    }

    function bottleScript(plan) {
        const bottle = shellQuote(plan.bottleName);
        const program = shellQuote(plan.programName);

        return (
            "if command -v flatpak >/dev/null 2>&1 "
            + "&& flatpak info com.usebottles.bottles >/dev/null 2>&1; then "
            + "exec flatpak run --command=bottles-cli "
            + "com.usebottles.bottles run -b "
            + bottle
            + " -p "
            + program
            + "; else exec bottles-cli run -b "
            + bottle
            + " -p "
            + program
            + "; fi"
        );
    }

    function buildBottle(plan) {
        const augmentation =
            plan.surfaceLaunchAugmentation || null;

        // The donor Bottles mechanism launches a configured program by bottle
        // and program name. It does not expose an application argv/env channel
        // in the code we are preserving. Do not silently drop SurfaceLaunch
        // mutation. Keep this closed until the mechanism-specific transport is
        // explicitly implemented/tested.
        if (augmentation
                && (
                    hasEntries(plan.launchEnv)
                    || hasArgMutation(augmentation)
                )) {
            return unavailable(
                "surface-launch-bottle-transport-unresolved",
                plan
            );
        }

        return {
            kind: commandArgv,
            argv: [
                "sh",
                "-lc",
                bottleScript(plan)
            ],
            correlationId:
                augmentation
                ? String(augmentation.correlationId || "")
                : "",
            plan: plan
        };
    }

    function buildHidden(plan) {
        // HIDDEN rows originate from RUN. Team 8 adapts them for APPS but
        // delegates actual command-launch mechanism back to the RUN domain.
        return {
            kind: commandRunDispatch,
            commandText: String(plan.commandText || ""),
            surfaceLaunchAugmentation:
                plan.surfaceLaunchAugmentation || null,
            plan: plan
        };
    }

    function build(plan, shellPath) {
        if (!plan)
            return unavailable("missing-plan", null);

        if (plan.kind === "unavailable")
            return unavailable(plan.reason || "unavailable", plan);

        if (plan.kind === "desktop-entry")
            return buildDesktopEntry(plan, shellPath);

        if (plan.kind === "toolbox-argv")
            return buildToolboxArgv(plan);

        if (plan.kind === "toolbox-shell")
            return buildToolboxShell(plan);

        if (plan.kind === "bottle")
            return buildBottle(plan);

        if (plan.kind === "hidden")
            return buildHidden(plan);

        return unavailable("unknown-plan-kind", plan);
    }
}
