import QtQuick

// Team 8 — APPS Core launch planning.
//
// Pure planning only: this file performs no process execution and has no
// AppControl host dependency. It preserves the donor's APPS launch semantics
// while leaving execution hooks open for sibling providers.
//
// Surface-launch ownership is resolved: T5 owns the shared requirements /
// coordinator domain, while Team 8 owns launch intent and application of a
// supplied augmentation. This planner therefore treats augmentation as opaque
// launcher input and does not infer Kitty/AT-SPI/DevTools requirements itself.
// Team 7 identity is not used here.
QtObject {
    id: planner

    required property var coreProvider

    readonly property string planDesktopEntry: "desktop-entry"
    readonly property string planToolboxArgv: "toolbox-argv"
    readonly property string planToolboxShell: "toolbox-shell"
    readonly property string planBottle: "bottle"
    readonly property string planHidden: "hidden"
    readonly property string planUnavailable: "unavailable"

    function cleanedCommandTokens(entry) {
        if (!entry)
            return [];

        const raw = entry.command || [];

        if (Array.isArray(raw)) {
            const tokens = [];

            for (let i = 0; i < raw.length; i++) {
                const token = String(raw[i] || "").trim();

                if (!token)
                    continue;

                // Preserve donor behavior: desktop-entry field codes require
                // file/URL input and are discarded for launcher-style starts.
                if (/^%[fFuUdDnNickvm]$/.test(token))
                    continue;

                tokens.push(token);
            }

            return tokens;
        }

        const commandText =
            String(raw || "")
            .replace(/\s+%[fFuUdDnNickvm]\b/g, "")
            .trim();

        if (!commandText)
            return [];

        return ["__APPCONTROL_SHELL__", commandText];
    }

    function launchExecutableName(entry) {
        const tokens = cleanedCommandTokens(entry);

        if (tokens.length === 0)
            return "";

        if (tokens[0] === "__APPCONTROL_SHELL__") {
            const match = String(tokens[1] || "").trim().match(
                /^([A-Za-z0-9_./+@%:-]+)(?:\s|$)/
            );

            if (!match)
                return "";

            const pieces = match[1].split("/");
            return String(
                pieces[pieces.length - 1] || ""
            ).toLowerCase();
        }

        const first = String(tokens[0] || "");
        const pieces = first.split("/");

        return String(
            pieces[pieces.length - 1] || ""
        ).toLowerCase();
    }

    function bottleProgramName(entry) {
        if (!entry)
            return "";

        return String(
            coreProvider.displayName(entry)
            || entry.name
            || ""
        ).trim();
    }

    function normalPlan(entry, sourceMode) {
        if (!coreProvider.entryLaunchableForSource(entry, sourceMode)) {
            return {
                kind: planUnavailable,
                reason: "source-not-launchable",
                entry: entry
            };
        }

        if (entry && entry._hiddenCommand) {
            return {
                kind: planHidden,
                commandText: String(entry.name || "").trim(),
                entry: entry
            };
        }

        return {
            kind: planDesktopEntry,
            entry: entry
        };
    }

    function toolboxPlan(entry, sourceMode) {
        if (!coreProvider.entryLaunchableForSource(entry, sourceMode)) {
            return {
                kind: planUnavailable,
                reason: "source-not-launchable",
                entry: entry
            };
        }

        const tokens = cleanedCommandTokens(entry);

        if (tokens.length === 0) {
            return {
                kind: planUnavailable,
                reason: "missing-command",
                entry: entry
            };
        }

        if (tokens[0] === "__APPCONTROL_SHELL__") {
            return {
                kind: planToolboxShell,
                shellText: String(tokens[1] || ""),
                entry: entry
            };
        }

        return {
            kind: planToolboxArgv,
            argv: tokens.slice(),
            entry: entry
        };
    }

    function bottlePlan(entry, sourceMode, bottleName) {
        if (!coreProvider.entryLaunchableForSource(entry, sourceMode)) {
            return {
                kind: planUnavailable,
                reason: "source-not-launchable",
                entry: entry
            };
        }

        const bottle = String(bottleName || "").trim();

        if (!bottle) {
            return {
                kind: planUnavailable,
                reason: "missing-bottle",
                entry: entry
            };
        }

        const programName = bottleProgramName(entry);

        if (!programName) {
            return {
                kind: planUnavailable,
                reason: "missing-program-name",
                entry: entry
            };
        }

        return {
            kind: planBottle,
            bottleName: bottle,
            programName: programName,
            entry: entry
        };
    }

    function withSuppliedAugmentation(basePlan, suppliedAugmentation) {
        if (!basePlan || basePlan.kind === planUnavailable)
            return basePlan;

        // The augmentation payload is intentionally opaque here. Its
        // capability semantics, endpoint allocation, lease/correlation state
        // and bootstrap construction belong to the T5-domain-owned shared
        // SurfaceLaunch contract. Team 8 only carries the supplied result with
        // its mechanism-specific launch plan.
        const next = Object.assign({}, basePlan);
        next.surfaceLaunchAugmentation =
            suppliedAugmentation !== undefined
            ? suppliedAugmentation
            : null;

        return next;
    }

    function plan(entry, sourceMode, launchMode, bottleName,
                  suppliedAugmentation) {
        let basePlan;

        if (launchMode === coreProvider.launchToolbox)
            basePlan = toolboxPlan(entry, sourceMode);
        else if (launchMode === coreProvider.launchBottle)
            basePlan = bottlePlan(entry, sourceMode, bottleName);
        else
            basePlan = normalPlan(entry, sourceMode);

        return withSuppliedAugmentation(basePlan, suppliedAugmentation);
    }
}
