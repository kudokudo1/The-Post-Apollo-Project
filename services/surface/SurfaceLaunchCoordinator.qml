import QtQuick

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

    required property var requirements

    property int correlationSerial: 0
    property var leases: ({})
    property var correlationState: ({})

    readonly property int fallbackPortStart: 9300
    readonly property int fallbackPortEnd: 9499

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

    function newCorrelationId(evidence) {
        correlationSerial += 1;

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
            String(correlationSerial),
            hint
        ].join("-");
    }

    function commandTokens(evidence) {
        return requirements.normalizedCommandTokens(evidence);
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

    function existingKittyListenOn(evidence) {
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
        return !!leases[leaseKey(kind, value)];
    }

    function addLease(kind, value, correlationId, capability, source) {
        const key = leaseKey(kind, value);
        const existing = leases[key];

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

        const next = Object.assign({}, leases);

        next[key] = {
            kind: asText(kind),
            value: value,
            correlationId: asText(correlationId),
            capability: asText(capability),
            source: asText(source) || "generated",
            state: "reserved"
        };

        leases = next;

        return {
            ok: true,
            lease: next[key]
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

        const nextLeases = {};
        const keys = Object.keys(leases);
        let removed = false;

        for (let i = 0; i < keys.length; i++) {
            const key = keys[i];
            const lease = leases[key];

            if (lease && lease.correlationId === id) {
                removed = true;
                continue;
            }

            nextLeases[key] = lease;
        }

        leases = nextLeases;

        const states = Object.assign({}, correlationState);
        delete states[id];
        correlationState = states;

        return removed;
    }

    function markLaunchSucceeded(correlationId) {
        const id = asText(correlationId);

        if (!id)
            return;

        const states = Object.assign({}, correlationState);
        const current = states[id] || ({});

        states[id] = Object.assign({}, current, {
            state: "launched"
        });
        correlationState = states;
    }

    function markLaunchFailed(correlationId) {
        releaseCorrelation(correlationId);
    }

    function buildAugmentation(evidence, requestedCapabilities) {
        const description =
            requirements.describe(evidence, requestedCapabilities);

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
                    requirements.capabilityKittyRemote
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
                        requirements.capabilityKittyRemote,
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
                        requirements.capabilityKittyRemote,
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
                        requirements.capabilityKittyRemote,
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
                    === requirements.capabilityKittyRemote;
            });

            if (!kittyConflict)
                applied.push(requirements.capabilityKittyRemote);
        }

        if (supported.indexOf(
                    requirements.capabilityAccessibility
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

            applied.push(requirements.capabilityAccessibility);
        }

        if (supported.indexOf(
                    requirements.capabilityDevTools
                ) !== -1) {
            const existingPort = existingDebugPort(evidence);
            const existingAddress = existingDebugAddress(evidence);
            let port = existingPort;
            let address = existingAddress;

            if (port > 0) {
                const reservation = addLease(
                    "devtools-port",
                    port,
                    correlationId,
                    requirements.capabilityDevTools,
                    "caller-supplied"
                );

                if (reservation.ok)
                    leaseRows.push(reservation.lease);
                else
                    conflictRows.push(reservation.conflict);
            } else {
                port = allocateDebugPort(
                    requirements.preferredDebugPort(evidence),
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
                        requirements.capabilityDevTools,
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
                            requirements.capabilityDevTools,
                        reason: "no-available-port"
                    });
                }
            }

            metadata.debugAddress = port > 0 ? address : "";
            metadata.debugPort = port;

            const devToolsConflict = conflictRows.some(function(item) {
                return item.capability
                    === requirements.capabilityDevTools;
            });

            if (port > 0 && !devToolsConflict)
                applied.push(requirements.capabilityDevTools);
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
            const states = Object.assign({}, correlationState);
            states[correlationId] = state;
            correlationState = states;
        }

        return {
            correlationId: correlationId,
            requestedCapabilities:
                description.requestedCapabilities.slice(),
            appliedCapabilities: ready ? applied.slice() : [],
            unsupportedCapabilities:
                description.unsupportedCapabilities.slice(),
            env: env,
            argvAfterExecutable: argvAfterExecutable,
            argvAppend: argvAppend,
            bootstrap: Object.assign({}, metadata),
            leases: ready ? leaseRows.slice() : [],
            conflicts: conflictRows.slice(),
            ready: ready
        };
    }
}
