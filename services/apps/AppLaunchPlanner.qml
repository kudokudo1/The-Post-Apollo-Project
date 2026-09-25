import QtQuick

// Team 8 — APPS Core launch planning.
//
// Pure planning only: this file performs no process execution and has no
// AppControl host dependency. It preserves the donor's APPS launch semantics
// while leaving execution hooks open for sibling providers.
//
// Team 5 may later wrap NORMAL execution to inject accessibility / surface
// discovery flags. Team 7 identity is not used here.
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

    function collectBottleNames(value, output) {
        if (value === null || value === undefined)
            return;

        if (typeof value === "string") {
            const name = value.trim();

            if (name && output.indexOf(name) === -1)
                output.push(name);

            return;
        }

        if (Array.isArray(value)) {
            for (let i = 0; i < value.length; i++) {
                const item = value[i];

                if (typeof item === "string") {
                    collectBottleNames(item, output);
                    continue;
                }

                if (item && typeof item === "object") {
                    if (item.name)
                        collectBottleNames(item.name, output);
                    else if (item.Name)
                        collectBottleNames(item.Name, output);
                    else if (item.bottle)
                        collectBottleNames(item.bottle, output);
                }
            }

            return;
        }

        if (typeof value === "object") {
            if (value.name)
                collectBottleNames(value.name, output);

            if (value.Name)
                collectBottleNames(value.Name, output);

            if (value.bottles)
                collectBottleNames(value.bottles, output);

            const keys = Object.keys(value);

            for (let i = 0; i < keys.length; i++) {
                const key = keys[i];

                if (key !== "bottles"
                        && key !== "name"
                        && key !== "Name"
                        && value[key]
                        && typeof value[key] === "object") {
                    collectBottleNames(key, output);
                }
            }
        }
    }

    function bottleNamesFromPayload(payload) {
        const names = [];
        collectBottleNames(payload, names);
        return names;
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

    function plan(entry, sourceMode, launchMode, bottleName) {
        if (launchMode === coreProvider.launchToolbox)
            return toolboxPlan(entry, sourceMode);

        if (launchMode === coreProvider.launchBottle)
            return bottlePlan(entry, sourceMode, bottleName);

        return normalPlan(entry, sourceMode);
    }
}
