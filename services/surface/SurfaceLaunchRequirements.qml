import QtQuick

// T5 domain authority: surface discoverability requirements.
//
// This object does not launch processes, own DesktopEntries, or mutate provider
// lifetime. Launch domains supply neutral launch evidence and explicitly opt in
// to the capabilities they want augmented.
QtObject {
    id: requirements

    readonly property string capabilityKittyRemote: "KITTY_REMOTE"
    readonly property string capabilityAccessibility: "ACCESSIBILITY"
    readonly property string capabilityDevTools: "DEVTOOLS"

    readonly property var knownCapabilities: [
        capabilityKittyRemote,
        capabilityAccessibility,
        capabilityDevTools
    ]

    function asText(value) {
        return value === undefined || value === null
            ? ""
            : String(value);
    }

    function normalizedCommandTokens(evidence) {
        if (!evidence)
            return [];

        const raw = evidence.argv || evidence.commandTokens || [];

        if (Array.isArray(raw)) {
            const result = [];

            for (let i = 0; i < raw.length; i++) {
                const token = asText(raw[i]).trim();

                if (token)
                    result.push(token);
            }

            return result;
        }

        const text = asText(raw).trim();
        return text ? [text] : [];
    }

    function evidenceHaystack(evidence) {
        evidence = evidence || ({});

        return [
            asText(evidence.displayName || evidence.name),
            asText(evidence.localId || evidence.id),
            asText(evidence.startupClass),
            asText(evidence.executable),
            normalizedCommandTokens(evidence).join(" ")
        ].join(" ").toLowerCase();
    }

    function stableLaunchHint(evidence) {
        evidence = evidence || ({});

        return asText(
            evidence.stableHint
            || evidence.localId
            || evidence.id
            || evidence.displayName
            || evidence.name
            || evidence.executable
            || "surface-launch"
        );
    }

    function looksLikeKitty(evidence) {
        const haystack = evidenceHaystack(evidence);
        const display = asText(
            evidence && (evidence.displayName || evidence.name)
        ).toLowerCase();

        return display === "kitty"
            || haystack.indexOf("kitty") !== -1;
    }

    function looksLikeChromiumElectron(evidence) {
        const haystack = evidenceHaystack(evidence);

        return haystack.indexOf("brave") !== -1
            || haystack.indexOf("chromium") !== -1
            || haystack.indexOf("google-chrome") !== -1
            || haystack.indexOf("chrome ") !== -1
            || haystack.indexOf("code-oss") !== -1
            || haystack.indexOf("vscode") !== -1
            || haystack.indexOf("visual studio code") !== -1
            || haystack.indexOf("codium") !== -1
            || haystack.indexOf("electron") !== -1;
    }

    function preferredDebugPort(evidence) {
        const haystack = evidenceHaystack(evidence);

        if (haystack.indexOf("brave") !== -1)
            return 9222;

        if (haystack.indexOf("google-chrome") !== -1
                || haystack.indexOf("chrome ") !== -1)
            return 9223;

        if (haystack.indexOf("chromium") !== -1)
            return 9224;

        if (haystack.indexOf("code-oss") !== -1
                || haystack.indexOf("visual studio code") !== -1
                || haystack.indexOf("vscode") !== -1)
            return 9225;

        if (haystack.indexOf("codium") !== -1)
            return 9226;

        if (haystack.indexOf("electron") !== -1) {
            const key = stableLaunchHint(evidence);
            let hash = 0;

            for (let i = 0; i < key.length; i++)
                hash = ((hash * 31) + key.charCodeAt(i)) & 0x7fffffff;

            return 9300 + (hash % 200);
        }

        return 0;
    }

    function normalizeCapabilities(values) {
        if (!Array.isArray(values))
            return [];

        const result = [];

        for (let i = 0; i < values.length; i++) {
            const value = asText(values[i]).toUpperCase();

            if (knownCapabilities.indexOf(value) === -1)
                continue;

            if (result.indexOf(value) === -1)
                result.push(value);
        }

        return result;
    }

    // T5 owns the domain knowledge needed to suggest what discoverability
    // instrumentation would help this launch. The launcher remains free to
    // request none, some, or all of these capabilities explicitly.
    function suggestedCapabilities(evidence) {
        if (looksLikeKitty(evidence))
            return [capabilityKittyRemote];

        if (looksLikeChromiumElectron(evidence)) {
            return [
                capabilityAccessibility,
                capabilityDevTools
            ];
        }

        return [];
    }

    function requirementFor(capability, evidence) {
        const value = asText(capability).toUpperCase();

        if (value === capabilityKittyRemote) {
            return {
                capability: value,
                supported: looksLikeKitty(evidence),
                reason: looksLikeKitty(evidence)
                    ? "kitty-remote-discovery"
                    : "not-kitty-launch",
                endpointKind: "unix-abstract",
                preferredPort: 0
            };
        }

        if (value === capabilityAccessibility) {
            return {
                capability: value,
                supported: looksLikeChromiumElectron(evidence),
                reason: looksLikeChromiumElectron(evidence)
                    ? "chromium-electron-accessibility"
                    : "unsupported-accessibility-family",
                endpointKind: "",
                preferredPort: 0
            };
        }

        if (value === capabilityDevTools) {
            const port = preferredDebugPort(evidence);

            return {
                capability: value,
                supported:
                    looksLikeChromiumElectron(evidence)
                    && port > 0,
                reason:
                    port > 0
                    ? "chromium-electron-devtools"
                    : "unsupported-devtools-family",
                endpointKind: "tcp-loopback",
                preferredPort: port
            };
        }

        return {
            capability: value,
            supported: false,
            reason: "unknown-capability",
            endpointKind: "",
            preferredPort: 0
        };
    }

    function describe(evidence, requestedCapabilities) {
        const requested = normalizeCapabilities(requestedCapabilities);
        const items = [];
        const supported = [];
        const unsupported = [];

        for (let i = 0; i < requested.length; i++) {
            const item = requirementFor(requested[i], evidence);

            items.push(item);

            if (item.supported)
                supported.push(item.capability);
            else
                unsupported.push(item.capability);
        }

        return {
            requestedCapabilities: requested,
            supportedCapabilities: supported,
            unsupportedCapabilities: unsupported,
            requirements: items
        };
    }
}
