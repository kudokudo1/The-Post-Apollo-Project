import QtQuick

// Team 7 — Desktop Identity evidence bridge.
//
// Parallel-safe by design:
//   - no AppControlW dependency
//   - no process/audio/window mutations
//   - no provider lifetime ownership
//   - no canonical ApplicationEntity construction yet
//
// This object standardizes raw observations and relationship evidence so
// DesktopEntry, Sway, process, surface, and audio providers can meet at one
// semantic boundary later without discarding provenance.
QtObject {
    id: identityEvidence

    readonly property string lifetimePersistent: "persistent"
    readonly property string lifetimeSession: "session"
    readonly property string lifetimeApplicationInstance: "application-instance"
    readonly property string lifetimeEphemeral: "ephemeral"

    readonly property string strengthExact: "exact"
    readonly property string strengthHeuristic: "heuristic"

    readonly property string resolutionResolved: "resolved"
    readonly property string resolutionAmbiguous: "ambiguous"
    readonly property string resolutionUnresolved: "unresolved"

    function asText(value) {
        return value === undefined || value === null
               ? ""
               : String(value);
    }

    // Preserves the current donor normalization rule as matching evidence.
    // A normalized token is never a semantic identity key.
    function normalizeToken(value) {
        return asText(value)
            .toLowerCase()
            .replace(/\.desktop$/i, "")
            .replace(/[^a-z0-9]+/g, "");
    }

    function positivePid(value) {
        const pid = Number(value || 0);

        return !isNaN(pid)
               && Math.floor(pid) === pid
               && pid > 1
               ? pid
               : 0;
    }

    function positivePids(values) {
        if (!Array.isArray(values))
            return [];

        const result = [];

        for (let i = 0; i < values.length; i++) {
            const pid = positivePid(values[i]);

            if (pid > 1 && result.indexOf(pid) === -1)
                result.push(pid);
        }

        return result;
    }

    function makeAlias(kind, value, provider) {
        const raw = asText(value);

        if (!raw)
            return null;

        return {
            kind: asText(kind),
            value: raw,
            normalized: normalizeToken(raw),
            provider: asText(provider)
        };
    }

    function appendAlias(target, kind, value, provider) {
        const alias = makeAlias(kind, value, provider);

        if (alias)
            target.push(alias);
    }

    function makeRelationship(kind, targetProvider, targetKey,
                              strength, sourceField) {
        const key = asText(targetKey);

        if (!key)
            return null;

        return {
            kind: asText(kind),
            targetProvider: asText(targetProvider),
            targetKey: key,
            strength: strength === strengthHeuristic
                      ? strengthHeuristic
                      : strengthExact,
            sourceField: asText(sourceField)
        };
    }

    function observation(provider, providerKey, lifetimeClass,
                         raw, aliases, relationships, generation) {
        const lifetime = lifetimeClass === lifetimePersistent
                      || lifetimeClass === lifetimeSession
                      || lifetimeClass === lifetimeApplicationInstance
                      || lifetimeClass === lifetimeEphemeral
                      ? lifetimeClass
                      : lifetimeEphemeral;

        return {
            provider: asText(provider),
            providerKey: asText(providerKey),
            lifetimeClass: lifetime,
            generation: generation === undefined ? null : generation,
            raw: raw || ({}),
            aliases: Array.isArray(aliases) ? aliases.slice() : [],
            relationships: Array.isArray(relationships)
                           ? relationships.slice()
                           : []
        };
    }

    function commandTokens(entry) {
        if (!entry)
            return [];

        if (Array.isArray(entry.command))
            return entry.command.slice();

        const raw = asText(entry.command).trim();

        return raw ? [raw] : [];
    }

    function commandBaseName(entry) {
        const tokens = commandTokens(entry);

        if (tokens.length === 0)
            return "";

        const first = asText(tokens[0]).trim();
        const pieces = first.split("/");

        return pieces.length > 0
               ? pieces[pieces.length - 1]
               : first;
    }

    function desktopIdLeaf(entry) {
        const id = asText(entry && entry.id)
            .replace(/\.desktop$/i, "");
        const parts = id.split(".");

        return parts.length > 0 ? parts[parts.length - 1] : "";
    }

    function desktopEntryObservation(entry) {
        if (!entry)
            return observation("DESKTOP_ENTRY", "", lifetimePersistent,
                               ({}), [], [], null);

        const id = asText(entry.id);
        const aliases = [];

        appendAlias(aliases, "desktop-entry.id", id, "DESKTOP_ENTRY");
        appendAlias(aliases, "desktop-entry.startup-class",
                    entry.startupClass, "DESKTOP_ENTRY");
        appendAlias(aliases, "desktop-entry.name",
                    entry.name, "DESKTOP_ENTRY");
        appendAlias(aliases, "desktop-entry.command-basename",
                    commandBaseName(entry), "DESKTOP_ENTRY");
        appendAlias(aliases, "desktop-entry.id-leaf",
                    desktopIdLeaf(entry), "DESKTOP_ENTRY");

        const raw = {
            id: id,
            name: asText(entry.name),
            genericName: asText(entry.genericName),
            comment: asText(entry.comment),
            startupClass: asText(entry.startupClass),
            command: commandTokens(entry)
        };

        return observation(
            "DESKTOP_ENTRY",
            id ? "desktop-entry:" + id : "",
            lifetimePersistent,
            raw,
            aliases,
            [],
            null
        );
    }

    function swayWindowObservation(windowInfo, generation) {
        if (!windowInfo)
            return observation("SWAY", "", lifetimeEphemeral,
                               ({}), [], [], generation);

        const aliases = [];
        const relationships = [];
        const conId = windowInfo.id;
        const pid = positivePid(windowInfo.pid);

        appendAlias(aliases, "sway.app-id",
                    windowInfo.appId, "SWAY");
        appendAlias(aliases, "sway.class",
                    windowInfo.className, "SWAY");
        appendAlias(aliases, "sway.instance",
                    windowInfo.instance, "SWAY");
        appendAlias(aliases, "sway.title",
                    windowInfo.name, "SWAY");

        if (pid > 1) {
            relationships.push(makeRelationship(
                "EXACT_PID",
                "PROCFS",
                "pid:" + String(pid),
                strengthExact,
                "pid"
            ));
        }

        const raw = {
            id: conId,
            name: asText(windowInfo.name),
            appId: asText(windowInfo.appId),
            className: asText(windowInfo.className),
            instance: asText(windowInfo.instance),
            pid: pid,
            focused: !!windowInfo.focused,
            workspace: asText(windowInfo.workspace),
            output: asText(windowInfo.output),
            floating: !!windowInfo.floating,
            tabbed: !!windowInfo.tabbed,
            tabGroupId: windowInfo.tabGroupId === undefined
                        ? null
                        : windowInfo.tabGroupId,
            tabGroupName: asText(windowInfo.tabGroupName),
            fullscreen: !!windowInfo.fullscreen,
            rect: windowInfo.rect || null
        };

        return observation(
            "SWAY",
            conId === undefined || conId === null
            ? ""
            : "sway-con:" + String(conId),
            lifetimeEphemeral,
            raw,
            aliases,
            relationships,
            generation
        );
    }

    function processObservation(entry, generation) {
        if (!entry)
            return observation("PROCFS", "", lifetimeEphemeral,
                               ({}), [], [], generation);

        const pid = positivePid(entry.pid);
        const ppid = positivePid(entry.ppid);
        const aliases = [];
        const relationships = [];

        appendAlias(aliases, "proc.comm",
                    entry.comm || entry.name, "PROCFS");
        appendAlias(aliases, "proc.exe",
                    entry.exe || entry.executable, "PROCFS");

        if (ppid > 1) {
            relationships.push(makeRelationship(
                "PROC_PARENT",
                "PROCFS",
                "pid:" + String(ppid),
                strengthExact,
                "ppid"
            ));
        }

        const raw = {
            pid: pid,
            ppid: ppid,
            comm: asText(entry.comm || entry.name),
            exe: asText(entry.exe || entry.executable),
            args: asText(entry.args || entry.cmdline),
            user: asText(entry.user)
        };

        return observation(
            "PROCFS",
            pid > 1 ? "pid:" + String(pid) : "",
            lifetimeEphemeral,
            raw,
            aliases,
            relationships,
            generation
        );
    }

    // Consumes Team 5's identityEvidence(entry) record without claiming that
    // provider-local surface identity is application identity.
    function surfaceObservation(evidence, generation) {
        if (!evidence)
            return observation("SURFACE", "", lifetimeEphemeral,
                               ({}), [], [], generation);

        const provider = asText(evidence.provider) || "SURFACE";
        const aliases = [];
        const relationships = [];
        const pids = positivePids(evidence.processPids);

        appendAlias(aliases, "surface.app-name",
                    evidence.appName, provider);
        appendAlias(aliases, "surface.window-name",
                    evidence.windowName, provider);

        for (let i = 0; i < pids.length; i++) {
            relationships.push(makeRelationship(
                "PROVIDER_PROCESS_PID",
                "PROCFS",
                "pid:" + String(pids[i]),
                strengthExact,
                "processPids"
            ));
        }

        const raw = {
            providerKey: asText(evidence.providerKey),
            appName: asText(evidence.appName),
            windowName: asText(evidence.windowName),
            path: asText(evidence.path),
            role: evidence.role === undefined
                  ? null
                  : evidence.role,
            roleName: asText(evidence.roleName),
            busName: asText(evidence.busName),
            objectPath: asText(evidence.objectPath),
            processPids: pids,
            debugPort: Number(evidence.debugPort || 0),
            targetId: asText(evidence.targetId),
            webSocketDebuggerUrl: asText(evidence.webSocketDebuggerUrl),
            kittyAddress: asText(evidence.kittyAddress),
            kittyTabId: evidence.kittyTabId === undefined
                        ? null
                        : evidence.kittyTabId
        };

        return observation(
            provider,
            asText(evidence.providerKey),
            lifetimeEphemeral,
            raw,
            aliases,
            relationships,
            generation
        );
    }

    // Consumes T5-domain SurfaceLaunch bootstrap/correlation output as its
    // own application-instance observation. These coordinates help join a
    // launch transaction to later process/surface observations, but they are
    // never persistent semantic application identity.
    function surfaceLaunchObservation(launchMetadata, generation) {
        if (!launchMetadata)
            return observation("SURFACE_LAUNCH", "",
                               lifetimeApplicationInstance,
                               ({}), [], [], generation);

        const bootstrap = launchMetadata.bootstrap || launchMetadata;
        const correlationId = asText(
            bootstrap.correlationId
            || launchMetadata.correlationId
        );
        const debugPort = Number(
            bootstrap.debugPort
            || launchMetadata.debugPort
            || 0
        );
        const requested = Array.isArray(
            launchMetadata.requestedCapabilities
        ) ? launchMetadata.requestedCapabilities.slice() : [];
        const applied = Array.isArray(
            launchMetadata.appliedCapabilities
        ) ? launchMetadata.appliedCapabilities.slice() : [];
        const unsupported = Array.isArray(
            launchMetadata.unsupportedCapabilities
        ) ? launchMetadata.unsupportedCapabilities.slice() : [];

        const raw = {
            correlationId: correlationId,
            kittyListenOn: asText(
                bootstrap.kittyListenOn
                || launchMetadata.kittyListenOn
            ),
            debugAddress: asText(
                bootstrap.debugAddress
                || launchMetadata.debugAddress
            ),
            debugPort: !isNaN(debugPort) && debugPort > 0
                       ? debugPort
                       : 0,
            requestedCapabilities: requested,
            appliedCapabilities: applied,
            unsupportedCapabilities: unsupported
        };

        return observation(
            "SURFACE_LAUNCH",
            correlationId
            ? "surface-launch:" + correlationId
            : "",
            lifetimeApplicationInstance,
            raw,
            [],
            [],
            generation
        );
    }

    // Resolution remains a separate semantic step. This envelope deliberately
    // admits ambiguity and does not "pick the first match".
    function resolutionEnvelope(status, candidates, evidence, reason) {
        const valid = status === resolutionResolved
                   || status === resolutionAmbiguous
                   || status === resolutionUnresolved;

        return {
            status: valid ? status : resolutionUnresolved,
            candidates: Array.isArray(candidates)
                        ? candidates.slice()
                        : [],
            evidence: Array.isArray(evidence)
                      ? evidence.slice()
                      : [],
            reason: asText(reason)
        };
    }
}
