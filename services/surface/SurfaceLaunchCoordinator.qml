pragma Singleton

import QtQuick
import "." as SurfaceBackend

// T5-domain-owned, launcher-neutral surface instrumentation coordinator.
//
// This object constructs launch augmentation and tracks logical endpoint leases.
// It does NOT execute processes. T8 / RUN / future launch domains decide when
// and how to apply the returned argv/env/bootstrap data.
//
// Lease lifetime is explicitly independent from TabSurfaceProvider.active.
// Call releaseCorrelation() only from launch/application lifetime bookkeeping.
QtObject {
    id: coordinator

    property int _correlationSerial: 0

    // Mutable authority state stays behind underscore-prefixed implementation
    // properties. Consumers receive defensive snapshots below.
    property var _leaseState: ({})
    property var _correlationState: ({})

    readonly property var leases: copyMap(_leaseState)
    readonly property var correlationState: copyMap(_correlationState)

    readonly property int fallbackPortStart: 9300
    readonly property int fallbackPortEnd: 9499

    function copyValue(value) {
        if (Array.isArray(value)) {
            const result = [];

            for (let i = 0; i < value.length; i++)
                result.push(copyValue(value[i]));

            return result;
        }

        if (value && typeof value === "object") {
            const result = {};
            const keys = Object.keys(value);

            for (let i = 0; i < keys.length; i++) {
                const key = keys[i];
                result[key] = copyValue(value[key]);
            }

            return result;
        }

        return value;
    }

    function copyMap(source) {
        return copyValue(source || ({}));
    }

    function asText(value) {
        return value === undefined || value === null
            ? ""
            : String(value);
    }

    function safeToken(value) {
        return asText(value)
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .slice(0, 48);
    }

    function kittyListenAddress(correlationId) {
        // Keep generated abstract socket names bounded even if correlation
        // hints or serials grow. The unique timestamp/serial portion appears
        // at the front of the correlation id before the human hint.
        const token = safeToken(correlationId).slice(0, 60);

        return "unix:@appcontrol-kitty-" + token;
    }

    function newCorrelationId(evidence) {
        _correlationSerial += 1;

        const hint = safeToken(
            evidence && (
                evidence.stableHint
                || evidence.localId
                || evidence.id
                || evidence.displayName
                || evidence.name
                || evidence.executable
            )
        ) || "surface";

        return [
            "surface",
            String(Date.now()),
            String(_correlationSerial),
            hint
        ].join("-");
    }

    function commandTokens(evidence) {
        return SurfaceBackend.SurfaceLaunchRequirements.normalizedCommandTokens(evidence);
    }

    function hasArgPrefix(evidence, prefix) {
        const tokens = commandTokens(evidence);

        for (let i = 0; i < tokens.length; i++) {
            if (asText(tokens[i]).indexOf(prefix) === 0)
                return true;
        }

        return false;
    }

    function existingDebugPort(evidence) {
        const explicit = Number(
            evidence && (
                evidence.existingDebugPort
                || evidence.debugPort
            ) || 0
        );

        if (explicit > 0)
            return explicit;

        const tokens = commandTokens(evidence);

        for (let i = 0; i < tokens.length; i++) {
            const token = asText(tokens[i]);

            if (token.indexOf("--remote-debugging-port=") === 0) {
                const port = Number(token.split("=", 2)[1] || 0);
                return port > 0 ? port : 0;
            }

            if (token === "--remote-debugging-port"
                    && i + 1 < tokens.length) {
                const port = Number(tokens[i + 1] || 0);
                return port > 0 ? port : 0;
            }
        }

        return 0;
    }

    function existingDebugAddress(evidence) {
        const explicit = asText(
            evidence && (
                evidence.existingDebugAddress
                || evidence.debugAddress
            )
        ).trim();

        if (explicit)
            return explicit;

        const tokens = commandTokens(evidence);

        for (let i = 0; i < tokens.length; i++) {
            const token = asText(tokens[i]);

            if (token.indexOf("--remote-debugging-address=") === 0)
                return token.split("=", 2)[1] || "";

            if (token === "--remote-debugging-address"
                    && i + 1 < tokens.length)
                return asText(tokens[i + 1]);
        }

        return "";
    }

    function debugAddressIsLoopback(value) {
        const address = asText(value).trim().toLowerCase();

        // Missing address preserves current donor behavior when a caller
        // already supplied its own debug port. Explicit broad/non-loopback
        // addresses are not equivalent to T5's loopback-only bootstrap.
        return !address
            || address === "127.0.0.1"
            || address === "localhost"
            || address === "::1"
            || address === "[::1]";
    }

    function existingKittyListenOn(evidence) {
        const explicit = asText(
            evidence && (
                evidence.existingKittyListenOn
                || evidence.kittyListenOn
            )
        ).trim();

        if (explicit)
            return explicit;

        const tokens = commandTokens(evidence);

        for (let i = 0; i < tokens.length; i++) {
            const token = asText(tokens[i]);

            if (token.indexOf("--listen-on=") === 0)
                return token.slice("--listen-on=".length);

            if (token === "--listen-on" && i + 1 < tokens.length)
                return asText(tokens[i + 1]);
        }

        return "";
    }

    function kittyRemoteControlMode(evidence) {
        const explicit = asText(
            evidence && (
                evidence.existingKittyRemoteControlMode
                || evidence.kittyRemoteControlMode
            )
        ).trim();

        if (explicit)
            return explicit;

        const tokens = commandTokens(evidence);

        for (let i = 0; i < tokens.length; i++) {
            const token = asText(tokens[i]);

            if (token.indexOf("allow_remote_control=") === 0)
                return token.split("=", 2)[1] || "";

            if (token === "-o"
                    && i + 1 < tokens.length) {
                const option = asText(tokens[i + 1]);

                if (option.indexOf("allow_remote_control=") === 0)
                    return option.split("=", 2)[1] || "";
            }
        }

        return "";
    }

    function kittyRemoteControlEnabled(evidence) {
        return kittyRemoteControlMode(evidence) === "socket-only";
    }

    function leaseKey(kind, value) {
        return asText(kind) + ":" + asText(value);
    }

    function leaseInUse(kind, value) {
        return !!_leaseState[leaseKey(kind, value)];
    }

    function addLease(kind, value, correlationId, capability, source) {
        const key = leaseKey(kind, value);
        const existing = _leaseState[key];

        if (existing) {
            return {
                ok: false,
                conflict: {
                    kind: asText(kind),
                    value: value,
                    requestedCorrelationId: asText(correlationId),
                    existingCorrelationId:
                        asText(existing.correlationId),
                    capability: asText(capability)
                }
            };
        }

        const next = Object.assign({}, _leaseState);

        next[key] = {
            kind: asText(kind),
            value: value,
            correlationId: asText(correlationId),
            capability: asText(capability),
            source: asText(source) || "generated",
            state: "reserved"
        };

        _leaseState = next;

        return {
            ok: true,
            lease: next[key]
        };
    }

    function normalizedObservedLease(row) {
        row = row || ({});

        const kind = asText(row.kind).trim();
        const value = row.value;
        const providerKey = asText(row.providerKey).trim();
        const capability = asText(row.capability).trim();

        if (!kind)
            return null;

        if (kind === "devtools-port") {
            const port = Number(value || 0);

            if (!(port > 0))
                return null;

            return {
                kind: kind,
                value: port,
                providerKey: providerKey,
                capability: capability
                    || SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools
            };
        }

        if (kind === "kitty-listen-on") {
            const address = asText(value).trim();

            if (!address)
                return null;

            return {
                kind: kind,
                value: address,
                providerKey: providerKey,
                capability: capability
                    || SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote
            };
        }

        return null;
    }

    function normalizedCompleteObservationKinds(options) {
        const known = [
            "devtools-port",
            "kitty-listen-on"
        ];

        if (options && options.complete === true)
            return known.slice();

        const raw =
            options && Array.isArray(options.completeKinds)
            ? options.completeKinds
            : [];
        const result = [];

        for (let i = 0; i < raw.length; i++) {
            const kind = asText(raw[i]).trim();

            if (known.indexOf(kind) === -1)
                continue;

            if (result.indexOf(kind) === -1)
                result.push(kind);
        }

        return result;
    }

    function reconcileObservedInstrumentation(rows, options) {
        const source = Array.isArray(rows) ? rows : [];
        const completeKinds =
            normalizedCompleteObservationKinds(options);
        const desired = {};
        const normalized = [];

        for (let i = 0; i < source.length; i++) {
            const item = normalizedObservedLease(source[i]);

            if (!item)
                continue;

            const key = leaseKey(item.kind, item.value);

            if (desired[key])
                continue;

            desired[key] = item;
            normalized.push(item);
        }

        const next = {};
        const existingKeys = Object.keys(_leaseState);

        // Launch-transaction/application-instance leases always survive
        // reconciliation. Observed leases survive partial snapshots too:
        // absence becomes pruning evidence only when the caller explicitly
        // declares the snapshot complete.
        for (let i = 0; i < existingKeys.length; i++) {
            const key = existingKeys[i];
            const lease = _leaseState[key];

            if (!lease)
                continue;

            if (lease.source === "observed"
                    && completeKinds.indexOf(lease.kind) !== -1)
                continue;

            next[key] = lease;
        }

        let adopted = 0;
        let shadowed = 0;

        for (let i = 0; i < normalized.length; i++) {
            const item = normalized[i];
            const key = leaseKey(item.kind, item.value);

            if (next[key]) {
                // A known transaction lease already owns this coordinate.
                // Runtime observation confirms occupancy but must not rewrite
                // correlation/source provenance.
                shadowed += 1;
                continue;
            }

            next[key] = {
                kind: item.kind,
                value: item.value,
                correlationId: "",
                capability: item.capability,
                providerKey: item.providerKey,
                source: "observed",
                state: "observed"
            };
            adopted += 1;
        }

        _leaseState = next;

        return {
            adopted: adopted,
            shadowed: shadowed,
            observedCount: normalized.length,
            completeKinds: completeKinds.slice(),
            complete: completeKinds.length === 2
        };
    }

    function allocateDebugPort(preferred, correlationId) {
        const wanted = Number(preferred || 0);

        if (wanted > 0 && !leaseInUse("devtools-port", wanted))
            return wanted;

        for (let port = fallbackPortStart;
                port <= fallbackPortEnd;
                port++) {
            if (!leaseInUse("devtools-port", port))
                return port;
        }

        return 0;
    }

    function releaseCorrelation(correlationId) {
        const id = asText(correlationId);

        if (!id)
            return false;

        const hadState = !!_correlationState[id];
        const nextLeases = {};
        const keys = Object.keys(_leaseState);
        let removedLease = false;

        for (let i = 0; i < keys.length; i++) {
            const key = keys[i];
            const lease = _leaseState[key];

            if (lease && lease.correlationId === id) {
                removedLease = true;
                continue;
            }

            nextLeases[key] = lease;
        }

        _leaseState = nextLeases;

        const states = Object.assign({}, _correlationState);
        delete states[id];
        _correlationState = states;

        return removedLease || hadState;
    }

    function markLaunchSucceeded(correlationId) {
        const id = asText(correlationId);

        if (!id || !_correlationState[id])
            return false;

        const states = Object.assign({}, _correlationState);
        const current = states[id];

        states[id] = Object.assign({}, current, {
            state: "launched"
        });
        _correlationState = states;
        return true;
    }

    function markLaunchFailed(correlationId) {
        return releaseCorrelation(correlationId);
    }

    function buildAugmentation(evidence, requestedCapabilities) {
        const description =
            SurfaceBackend.SurfaceLaunchRequirements.describe(evidence, requestedCapabilities);

        // Explicit opt-in means an empty capability request is a true no-op:
        // no correlation record, no lease state, no launch mutation.
        if (description.requestedCapabilities.length === 0) {
            return {
                correlationId: "",
                requestedCapabilities: [],
                appliedCapabilities: [],
                unsupportedCapabilities: [],
                env: {},
                argvAfterExecutable: [],
                argvAppend: [],
                bootstrap: {
                    correlationId: "",
                    kittyListenOn: "",
                    debugAddress: "",
                    debugPort: 0
                },
                leases: [],
                conflicts: [],
                ready: true
            };
        }

        // Unsupported/unknown explicit requests fail before any endpoint
        // allocation so rejected preparation cannot strand lease state.
        if (description.unsupportedCapabilities.length > 0) {
            return {
                correlationId: "",
                requestedCapabilities:
                    description.requestedCapabilities.slice(),
                appliedCapabilities: [],
                unsupportedCapabilities:
                    description.unsupportedCapabilities.slice(),
                env: {},
                argvAfterExecutable: [],
                argvAppend: [],
                bootstrap: {
                    correlationId: "",
                    kittyListenOn: "",
                    debugAddress: "",
                    debugPort: 0
                },
                leases: [],
                conflicts: [],
                ready: false
            };
        }

        const correlationId = newCorrelationId(evidence);
        const env = {};
        const argvAfterExecutable = [];
        const argvAppend = [];
        const leaseRows = [];
        const conflictRows = [];
        const metadata = {
            correlationId: correlationId,
            kittyListenOn: "",
            debugAddress: "",
            debugPort: 0
        };

        const supported = description.supportedCapabilities;
        const applied = [];

        if (supported.indexOf(
                    SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote
                ) !== -1) {
            const existingListenOn = existingKittyListenOn(evidence);
            const remoteMode = kittyRemoteControlMode(evidence);
            let listenOn = existingListenOn;

            if (remoteMode && remoteMode !== "socket-only") {
                conflictRows.push({
                    kind: "kitty-remote-control-mode",
                    value: remoteMode,
                    requestedCorrelationId: correlationId,
                    existingCorrelationId: "",
                    capability:
                        SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote,
                    reason: "requires-socket-only"
                });
            } else {
                if (!kittyRemoteControlEnabled(evidence)) {
                    argvAfterExecutable.push(
                        "-o",
                        "allow_remote_control=socket-only"
                    );
                }

                if (listenOn) {
                    const reservation = addLease(
                        "kitty-listen-on",
                        listenOn,
                        correlationId,
                        SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote,
                        "caller-supplied"
                    );

                    if (reservation.ok)
                        leaseRows.push(reservation.lease);
                    else
                        conflictRows.push(reservation.conflict);
                } else {
                    listenOn =
                        "unix:@appcontrol-kitty-" + correlationId;

                    argvAfterExecutable.push(
                        "--listen-on",
                        listenOn
                    );

                    const reservation = addLease(
                        "kitty-listen-on",
                        listenOn,
                        correlationId,
                        SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote,
                        "generated"
                    );

                    if (reservation.ok)
                        leaseRows.push(reservation.lease);
                    else
                        conflictRows.push(reservation.conflict);
                }

                metadata.kittyListenOn = listenOn;
            }

            const kittyConflict = conflictRows.some(function(item) {
                return item.capability
                    === SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote;
            });

            if (!kittyConflict)
                applied.push(SurfaceBackend.SurfaceLaunchRequirements.capabilityKittyRemote);
        }

        if (supported.indexOf(
                    SurfaceBackend.SurfaceLaunchRequirements.capabilityAccessibility
                ) !== -1) {
            env.NO_AT_BRIDGE = "0";
            env.ACCESSIBILITY_ENABLED = "1";
            env.QT_ACCESSIBILITY = "1";
            env.QT_LINUX_ACCESSIBILITY_ALWAYS_ON = "1";

            if (!hasArgPrefix(
                        evidence,
                        "--force-renderer-accessibility"
                    )) {
                argvAppend.push(
                    "--force-renderer-accessibility=complete"
                );
            }

            applied.push(SurfaceBackend.SurfaceLaunchRequirements.capabilityAccessibility);
        }

        if (supported.indexOf(
                    SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools
                ) !== -1) {
            const existingPort = existingDebugPort(evidence);
            const existingAddress = existingDebugAddress(evidence);
            let port = existingPort;
            let address = existingAddress;

            if (port > 0) {
                if (!debugAddressIsLoopback(existingAddress)) {
                    conflictRows.push({
                        kind: "devtools-debug-address",
                        value: existingAddress,
                        requestedCorrelationId: correlationId,
                        existingCorrelationId: "",
                        capability:
                            SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools,
                        reason: "requires-loopback"
                    });
                } else {
                    const reservation = addLease(
                        "devtools-port",
                        port,
                        correlationId,
                        SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools,
                        "caller-supplied"
                    );

                    if (reservation.ok)
                        leaseRows.push(reservation.lease);
                    else
                        conflictRows.push(reservation.conflict);
                }
            } else {
                port = allocateDebugPort(
                    SurfaceBackend.SurfaceLaunchRequirements.preferredDebugPort(evidence),
                    correlationId
                );

                if (port > 0) {
                    if (!address) {
                        address = "127.0.0.1";
                        argvAppend.push(
                            "--remote-debugging-address=" + address
                        );
                    }

                    argvAppend.push(
                        "--remote-debugging-port=" + String(port)
                    );

                    const reservation = addLease(
                        "devtools-port",
                        port,
                        correlationId,
                        SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools,
                        "generated"
                    );

                    if (reservation.ok)
                        leaseRows.push(reservation.lease);
                    else
                        conflictRows.push(reservation.conflict);
                } else {
                    conflictRows.push({
                        kind: "devtools-port",
                        value: 0,
                        requestedCorrelationId: correlationId,
                        existingCorrelationId: "",
                        capability:
                            SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools,
                        reason: "no-available-port"
                    });
                }
            }

            metadata.debugAddress = port > 0 ? address : "";
            metadata.debugPort = port;

            const devToolsConflict = conflictRows.some(function(item) {
                return item.capability
                    === SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools;
            });

            if (port > 0 && !devToolsConflict)
                applied.push(SurfaceBackend.SurfaceLaunchRequirements.capabilityDevTools);
        }

        const ready = conflictRows.length === 0;

        if (!ready) {
            // Preparation never reached an executable state. Any successful
            // sibling reservations created earlier in this transaction must
            // be released immediately; there is no application lifetime yet.
            releaseCorrelation(correlationId);
        } else {
            const state = {
                state: "prepared",
                requestedCapabilities:
                    description.requestedCapabilities.slice(),
                supportedCapabilities:
                    description.supportedCapabilities.slice(),
                appliedCapabilities: applied.slice(),
                ready: true,
                metadata: Object.assign({}, metadata)
            };
            const states = Object.assign({}, _correlationState);
            states[correlationId] = state;
            _correlationState = states;
        }

        return {
            correlationId: correlationId,
            requestedCapabilities:
                description.requestedCapabilities.slice(),
            appliedCapabilities: ready ? applied.slice() : [],
            unsupportedCapabilities:
                description.unsupportedCapabilities.slice(),

            // Fail closed: a rejected augmentation carries diagnostics and
            // correlation context only. It must not carry executable partial
            // mutations that a weak consumer could accidentally apply.
            env: ready ? env : {},
            argvAfterExecutable:
                ready ? argvAfterExecutable : [],
            argvAppend: ready ? argvAppend : [],
            bootstrap:
                ready
                ? Object.assign({}, metadata)
                : {
                    correlationId: correlationId,
                    kittyListenOn: "",
                    debugAddress: "",
                    debugPort: 0
                },
            leases: ready ? leaseRows.slice() : [],
            conflicts: conflictRows.slice(),
            ready: ready
        };
    }
}
