import QtQuick

// Team 8 — APPS Core launch planning.
//
// Pure planning only: this file performs no process execution and has no
// AppControl host dependency. It preserves the donor's APPS launch semantics
// while leaving execution hooks open for sibling providers.
//
// Surface-launch ownership is resolved: T5 owns the shared requirements /
// coordinator domain, while Team 8 owns launch intent and application of a
// supplied launcher-neutral augmentation.
//
// Team 5's published payload currently exposes:
//   ready, env, argvAfterExecutable, argvAppend, bootstrap, correlationId,
//   leases/conflicts and requested/applied capability metadata.
//
// Team 8 consumes only that generic shape. It does not infer Kitty/AT-SPI/
// DevTools requirements or endpoint policy itself.
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
            entry: entry,
            commandTokens: cleanedCommandTokens(entry)
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

    function copyStringArray(value) {
        if (!Array.isArray(value))
            return [];

        return value.map(function(item) {
            return String(item || "");
        });
    }

    function copyStringMap(value) {
        const result = {};

        if (!value || typeof value !== "object")
            return result;

        const keys = Object.keys(value);

        for (let i = 0; i < keys.length; i++)
            result[String(keys[i])] = String(value[keys[i]] || "");

        return result;
    }

    function normalizedSurfaceAugmentation(value) {
        if (value === undefined || value === null)
            return null;

        const ready = value.ready !== false;

        return {
            ready: ready,
            correlationId: String(value.correlationId || ""),
            env: copyStringMap(value.env),
            argvAfterExecutable:
                copyStringArray(value.argvAfterExecutable),
            argvAppend: copyStringArray(value.argvAppend),
            bootstrap:
                value.bootstrap && typeof value.bootstrap === "object"
                ? Object.assign({}, value.bootstrap)
                : {},
            requestedCapabilities:
                copyStringArray(value.requestedCapabilities),
            appliedCapabilities:
                copyStringArray(value.appliedCapabilities),
            unsupportedCapabilities:
                copyStringArray(value.unsupportedCapabilities),
            leases:
                Array.isArray(value.leases)
                ? value.leases.slice()
                : [],
            conflicts:
                Array.isArray(value.conflicts)
                ? value.conflicts.slice()
                : []
        };
    }

    function augmentedArgv(entry, argv, augmentation) {
        const source = Array.isArray(argv)
            ? argv.slice()
            : [];

        if (source.length === 0 || !augmentation)
            return source;

        const afterExecutable =
            augmentation.argvAfterExecutable || [];
        const append = augmentation.argvAppend || [];

        // For direct/native argv, token 0 is the application executable and
        // argvAfterExecutable belongs immediately after it.
        //
        // Flatpak DesktopEntries are launcher wrappers:
        //   flatpak run ... APP_ID [application argv...]
        // Token 0 is therefore NOT the application executable. Team 8 owns
        // this transport distinction, so application-facing augmentation is
        // carried after the existing Flatpak command/application coordinates
        // rather than being injected into flatpak's own option space.
        if (coreProvider.entryIsFlatpak(entry)) {
            return source
                .concat(afterExecutable)
                .concat(append);
        }

        return [source[0]]
            .concat(afterExecutable)
            .concat(source.slice(1))
            .concat(append);
    }

    function withSuppliedAugmentation(basePlan, suppliedAugmentation) {
        if (!basePlan || basePlan.kind === planUnavailable)
            return basePlan;

        const augmentation =
            normalizedSurfaceAugmentation(suppliedAugmentation);

        if (!augmentation)
            return basePlan;

        if (!augmentation.ready) {
            return {
                kind: planUnavailable,
                reason: "surface-launch-not-ready",
                entry: basePlan.entry || null,
                surfaceLaunchAugmentation: augmentation
            };
        }

        const next = Object.assign({}, basePlan);
        next.surfaceLaunchAugmentation = augmentation;
        next.launchEnv = Object.assign({}, augmentation.env);

        // Argv-based launch mechanisms can be transformed immediately without
        // knowing any provider-specific capability semantics.
        if (Array.isArray(basePlan.commandTokens)) {
            next.commandTokens = augmentedArgv(
                basePlan.entry,
                basePlan.commandTokens,
                augmentation
            );
        }

        if (Array.isArray(basePlan.argv)) {
            next.argv = augmentedArgv(
                basePlan.entry,
                basePlan.argv,
                augmentation
            );
        }

        // Shell/Bottles plans retain the normalized augmentation for their
        // mechanism-specific executor. The SurfaceLaunch domain owns what the
        // mutation means; Team 8 owns how that mutation is transported through
        // the selected launch mechanism.
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
