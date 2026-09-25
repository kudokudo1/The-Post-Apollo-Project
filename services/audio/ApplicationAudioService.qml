import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: applicationAudioService

    // Shared APP / WINDOW / TAB audio physiology.
    //
    // Semantic desktop identity is intentionally NOT owned here. Callers must
    // provide stable target keys and matching descriptors. Team 7 is expected
    // to become the authority for those descriptors.
    readonly property real volumeMaxPercent: 100

    property var sinkInputs: []
    property int observationGeneration: 0
    property bool loading: false
    property string errorText: ""

    // Persistent future-stream mute policies. APP / WINDOW / TAB remain
    // separate semantic scopes even though they share one storage object.
    // Composite storage keys preserve the donor's separate policy namespaces.
    property var mutePolicies: ({})

    // One-shot synchronization requests, used when an existing stream must be
    // driven to a requested mute state immediately after policy changes.
    property var pendingMuteStates: ({})

    // Volume policies from APP / WINDOW / TAB may overlap the same stream.
    // The most recently touched policy wins, matching the current donor rule.
    property var volumePolicies: ({})
    property int volumePolicySerial: 0

    signal refreshed(var inputs)
    signal policyApplied()
    signal mutationIssued(string kind, var indexes, var value)

    function normalizeToken(value) {
        if (!value)
            return "";

        let token = String(value).toLowerCase();

        if (token.endsWith(".desktop"))
            token = token.slice(0, -8);

        return token.replace(/[^a-z0-9]/g, "");
    }

    function tokensMatch(left, right, strict) {
        const a = normalizeToken(left);
        const b = normalizeToken(right);

        if (!a || !b)
            return false;

        if (a === b)
            return true;

        if (strict)
            return false;

        const shorterLength = Math.min(a.length, b.length);
        if (shorterLength < 4)
            return false;

        return a.endsWith(b) || b.endsWith(a);
    }

    function blockedStrictToken(token) {
        return [
            "electron", "chromium", "browser", "application", "desktop",
            "terminal", "flatpak", "env", "sh", "bash", "zsh",
            "stable", "beta", "dev", "bin", "org", "com", "io", "net"
        ].indexOf(token) !== -1;
    }

    function streamPropertyTokens(properties, strict) {
        if (!properties)
            return [];

        const raw = strict
            ? [
                properties["application.process.binary"] || "",
                properties["application.id"] || "",
                properties["application.name"] || ""
            ]
            : [
                properties["application.process.binary"] || "",
                properties["application.name"] || "",
                properties["application.id"] || "",
                properties["media.name"] || ""
            ];

        const tokens = [];

        function addToken(value) {
            const normalized = applicationAudioService.normalizeToken(value);

            if (normalized.length < 3)
                return;

            if (strict && applicationAudioService.blockedStrictToken(normalized))
                return;

            if (tokens.indexOf(normalized) === -1)
                tokens.push(normalized);
        }

        for (let i = 0; i < raw.length; i++) {
            const value = String(raw[i] || "");
            addToken(value);

            if (strict) {
                const pieces = value.split(/[^A-Za-z0-9]+/);
                for (let p = 0; p < pieces.length; p++)
                    addToken(pieces[p]);
            }
        }

        return tokens;
    }

    function copyDescriptor(descriptor) {
        if (!descriptor)
            return null;

        const pids = [];
        const rawPids = Array.isArray(descriptor.pids)
            ? descriptor.pids
            : [];

        for (let i = 0; i < rawPids.length; i++) {
            const pid = Number(rawPids[i] || 0);
            if (pid > 1 && pids.indexOf(pid) === -1)
                pids.push(pid);
        }

        const tokens = [];
        const rawTokens = Array.isArray(descriptor.tokens)
            ? descriptor.tokens
            : [];

        for (let i = 0; i < rawTokens.length; i++) {
            const token = normalizeToken(rawTokens[i]);
            if (token.length >= 3 && tokens.indexOf(token) === -1)
                tokens.push(token);
        }

        return {
            pids: pids,
            tokens: tokens,
            strictTokens: !!descriptor.strictTokens
        };
    }

    function policyStorageKey(scope, key) {
        const scopeText = String(scope || "").trim().toLowerCase();
        const keyText = String(key || "");

        if (!scopeText || !keyText)
            return "";

        return scopeText + ":" + keyText;
    }

    // Matching is evidence, not semantic identity. Team 7 owns the latter.
    // Keep the evidence inspectable so callers can distinguish an exact PID
    // attachment from a weaker token heuristic.
    function descriptorMatchEvidence(descriptor, sinkInput) {
        const result = {
            matched: false,
            pidMatch: false,
            processId: 0,
            streamIndex: -1,
            strictTokens: !!(descriptor && descriptor.strictTokens),
            tokenMatches: []
        };

        if (!descriptor || !sinkInput)
            return result;

        const props = sinkInput.properties || {};
        const processId = Number(props["application.process.id"] || 0);
        const streamIndex = Number(sinkInput.index);
        const pids = Array.isArray(descriptor.pids)
            ? descriptor.pids
            : [];

        result.processId = processId > 0 ? processId : 0;
        result.streamIndex = isNaN(streamIndex) ? -1 : streamIndex;

        if (processId > 1 && pids.indexOf(processId) !== -1) {
            result.pidMatch = true;
            result.matched = true;
        }

        const wanted = Array.isArray(descriptor.tokens)
            ? descriptor.tokens
            : [];
        if (wanted.length === 0)
            return result;

        const strict = !!descriptor.strictTokens;
        const available = streamPropertyTokens(props, strict);

        for (let i = 0; i < wanted.length; i++) {
            for (let j = 0; j < available.length; j++) {
                if (!tokensMatch(wanted[i], available[j], strict))
                    continue;

                const pair = String(wanted[i]) + "|" + String(available[j]);
                if (result.tokenMatches.indexOf(pair) === -1)
                    result.tokenMatches.push(pair);

                result.matched = true;
            }
        }

        return result;
    }

    function matchesDescriptor(descriptor, sinkInput) {
        return descriptorMatchEvidence(descriptor, sinkInput).matched;
    }

    function sinkInputVolumePercent(input) {
        if (!input || !input.volume)
            return 100;

        const volume = input.volume;
        const keys = Object.keys(volume);
        let total = 0;
        let count = 0;

        for (let i = 0; i < keys.length; i++) {
            const channel = volume[keys[i]];
            if (!channel || typeof channel !== "object")
                continue;

            let value = NaN;
            const percentText = String(channel.value_percent || "");

            if (percentText.length > 0)
                value = parseFloat(percentText.replace("%", ""));
            else if (channel.value !== undefined)
                value = Number(channel.value) / 65536.0 * 100.0;

            if (!isNaN(value)) {
                total += value;
                count += 1;
            }
        }

        return count > 0 ? total / count : 100;
    }

    function clampVolume(percent) {
        return Math.max(
            0,
            Math.min(volumeMaxPercent, Number(percent || 0))
        );
    }

    function averagedSinkVolume(inputs) {
        if (!inputs || inputs.length === 0)
            return 100;

        let total = 0;

        for (let i = 0; i < inputs.length; i++)
            total += sinkInputVolumePercent(inputs[i]);

        return clampVolume(total / inputs.length);
    }

    function resolve(descriptor, inputs) {
        const source = inputs || sinkInputs || [];
        const matchingInputs = [];
        const indexes = [];
        const matches = [];
        let allMuted = true;

        for (let i = 0; i < source.length; i++) {
            const input = source[i];
            const evidence = descriptorMatchEvidence(descriptor, input);

            if (!evidence.matched)
                continue;

            matchingInputs.push(input);
            matches.push({
                streamIndex: evidence.streamIndex,
                evidence: evidence
            });

            const index = Number(input.index);
            if (!isNaN(index))
                indexes.push(index);

            if (!input.mute)
                allMuted = false;
        }

        return {
            // Raw pactl records remain intact for Team 7 fixture capture and
            // future diagnostics. The matches list carries separate join evidence.
            //
            // Do not expose donor-style "AudioAvailable" here. In AppControl
            // that flag means different host/UI things for APP, WINDOW and TAB.
            // Team 6 reports only observable stream physiology.
            inputs: matchingInputs,
            matches: matches,
            indexes: indexes,
            hasStreams: matchingInputs.length > 0,
            streamsMuted: indexes.length > 0 && allMuted,
            observedVolumePercent: matchingInputs.length > 0
                ? averagedSinkVolume(matchingInputs)
                : -1
        };
    }

    // Raw observation adapter for Team 7 fixture capture. Values remain
    // exactly as reported by pactl; this is evidence, not semantic identity.
    function streamEvidence(input) {
        const props = input && input.properties || {};

        return {
            streamIndex: input ? input.index : undefined,
            mute: input ? !!input.mute : false,
            volume: input ? input.volume : undefined,
            applicationProcessId: props["application.process.id"],
            applicationProcessBinary: props["application.process.binary"],
            applicationId: props["application.id"],
            applicationName: props["application.name"],
            mediaName: props["media.name"],
            properties: props
        };
    }

    function evidenceSnapshot(inputs) {
        const source = inputs || sinkInputs || [];
        const snapshot = [];

        for (let i = 0; i < source.length; i++)
            snapshot.push(streamEvidence(source[i]));

        return snapshot;
    }

    // Team 7 compatibility adapter. This is an observation record, not a
    // canonical ApplicationEntity. Team 7 now freezes the common evidence
    // envelope, while semantic resolution and canonical entities remain
    // separate concerns.
    function streamObservation(input) {
        const evidence = streamEvidence(input);
        const aliases = [];
        const relationships = [];

        function addAlias(kind, value) {
            const rawValue = String(value || "");
            if (!rawValue)
                return;

            aliases.push({
                kind: String(kind || ""),
                value: rawValue,
                normalized: applicationAudioService.normalizeToken(rawValue),
                provider: "PIPEWIRE"
            });
        }

        addAlias("application.process.binary", evidence.applicationProcessBinary);
        addAlias("application.id", evidence.applicationId);
        addAlias("application.name", evidence.applicationName);
        addAlias("media.name", evidence.mediaName);

        const pid = Number(evidence.applicationProcessId || 0);
        if (!isNaN(pid) && Math.floor(pid) === pid && pid > 1) {
            relationships.push({
                kind: "EXACT_PID",
                targetProvider: "PROCFS",
                targetKey: "pid:" + String(pid),
                strength: "exact",
                sourceField: "application.process.id"
            });
        }

        const providerKey = evidence.streamIndex === undefined
            || evidence.streamIndex === null
            ? ""
            : "sink-input:" + String(evidence.streamIndex);

        return {
            provider: "PIPEWIRE",
            providerKey: providerKey,
            lifetimeClass: "ephemeral",
            generation: observationGeneration,
            raw: evidence,
            aliases: aliases,
            relationships: relationships
        };
    }

    function observationSnapshot(inputs) {
        const source = inputs || sinkInputs || [];
        const snapshot = [];

        for (let i = 0; i < source.length; i++)
            snapshot.push(streamObservation(source[i]));

        return snapshot;
    }

    function parseSinkInputs(text) {
        const parsed = JSON.parse(String(text || "[]"));

        if (!Array.isArray(parsed))
            throw new Error("pactl sink-input payload was not an array");

        return parsed;
    }

    function refresh() {
        refreshTimer.restart();
    }

    function requestPolicyRefresh() {
        policyRefreshTimer.restart();
    }

    function setSinkInputMute(indexes, muted) {
        if (!Array.isArray(indexes))
            return false;

        const valid = [];

        for (let i = 0; i < indexes.length; i++) {
            const index = Number(indexes[i]);
            if (isNaN(index) || index < 0 || Math.floor(index) !== index)
                continue;

            valid.push(index);
            Quickshell.execDetached([
                "pactl",
                "set-sink-input-mute",
                String(index),
                muted ? "1" : "0"
            ]);
        }

        if (valid.length > 0)
            mutationIssued("mute", valid, !!muted);

        return valid.length > 0;
    }

    function setSinkInputVolumes(indexes, percent) {
        if (!Array.isArray(indexes))
            return false;

        const target = clampVolume(percent);
        const percentText = Math.round(target) + "%";
        const valid = [];

        for (let i = 0; i < indexes.length; i++) {
            const index = Number(indexes[i]);
            if (isNaN(index) || index < 0 || Math.floor(index) !== index)
                continue;

            valid.push(index);
            Quickshell.execDetached([
                "pactl",
                "set-sink-input-volume",
                String(index),
                percentText
            ]);
        }

        if (valid.length > 0)
            mutationIssued("volume", valid, target);

        return valid.length > 0;
    }

    function setMutePolicy(scope, key, descriptor, enabled) {
        const policyKey = policyStorageKey(scope, key);
        if (!policyKey)
            return false;

        const next = Object.assign({}, mutePolicies);

        if (enabled) {
            const stored = copyDescriptor(descriptor);
            if (!stored)
                return false;

            next[policyKey] = {
                scope: String(scope || "").trim().toLowerCase(),
                semanticKey: String(key || ""),
                descriptor: stored
            };
        } else {
            delete next[policyKey];
        }

        mutePolicies = next;
        requestPolicyRefresh();
        return true;
    }

    function mutePolicyActive(scope, key) {
        const policyKey = policyStorageKey(scope, key);
        return !!policyKey && mutePolicies[policyKey] !== undefined;
    }

    function queueMuteState(scope, key, descriptor, muted) {
        const policyKey = policyStorageKey(scope, key);
        const stored = copyDescriptor(descriptor);

        if (!policyKey || !stored)
            return false;

        const next = Object.assign({}, pendingMuteStates);
        next[policyKey] = {
            scope: String(scope || "").trim().toLowerCase(),
            semanticKey: String(key || ""),
            descriptor: stored,
            muted: !!muted
        };

        pendingMuteStates = next;
        requestPolicyRefresh();
        return true;
    }

    // Preserve the donor's WINDOW-unmute rule: a narrow WINDOW action may
    // clear a broader APP mute policy that contains the same live PID, but it
    // must not erase unrelated WINDOW/TAB rules.
    function clearMutePoliciesWithPid(scope, pid) {
        const scopeText = String(scope || "").trim().toLowerCase();
        const targetPid = Number(pid || 0);

        if (!scopeText || targetPid <= 1)
            return false;

        const keys = Object.keys(mutePolicies);
        const next = Object.assign({}, mutePolicies);
        let changed = false;

        for (let i = 0; i < keys.length; i++) {
            const policy = mutePolicies[keys[i]] || {};
            if (String(policy.scope || "") !== scopeText)
                continue;

            const descriptor = policy.descriptor || {};
            const pids = descriptor.pids || [];

            if (pids.indexOf(targetPid) !== -1) {
                delete next[keys[i]];
                changed = true;
            }
        }

        if (changed) {
            mutePolicies = next;
            requestPolicyRefresh();
        }

        return changed;
    }

    // Provider-owned lifetimes stay outside Team 6. A provider can explicitly
    // tell the service which semantic keys remain live for one scope; the
    // service only removes audio policies tied to identities that disappeared.
    function retainPolicyKeys(scope, liveKeys) {
        const scopeText = String(scope || "").trim().toLowerCase();
        if (!scopeText)
            return false;

        const live = ({});
        const source = Array.isArray(liveKeys) ? liveKeys : [];

        for (let i = 0; i < source.length; i++) {
            const key = String(source[i] || "");
            if (key)
                live[key] = true;
        }

        let changed = false;

        const muteNext = Object.assign({}, mutePolicies);
        const muteKeys = Object.keys(mutePolicies);
        for (let i = 0; i < muteKeys.length; i++) {
            const policy = mutePolicies[muteKeys[i]] || {};
            if (String(policy.scope || "") !== scopeText)
                continue;
            if (!live[String(policy.semanticKey || "")]) {
                delete muteNext[muteKeys[i]];
                changed = true;
            }
        }

        const volumeNext = Object.assign({}, volumePolicies);
        const volumeKeys = Object.keys(volumePolicies);
        for (let i = 0; i < volumeKeys.length; i++) {
            const policy = volumePolicies[volumeKeys[i]] || {};
            if (String(policy.scope || "") !== scopeText)
                continue;
            if (!live[String(policy.semanticKey || "")]) {
                delete volumeNext[volumeKeys[i]];
                changed = true;
            }
        }

        if (changed) {
            mutePolicies = muteNext;
            volumePolicies = volumeNext;
        }

        return changed;
    }

    function volumePolicyKey(scope, key) {
        return policyStorageKey(scope, key);
    }

    function setVolumePolicy(scope, key, descriptor, percent) {
        const policyKey = volumePolicyKey(scope, key);
        const stored = copyDescriptor(descriptor);

        if (!policyKey || !stored)
            return false;

        volumePolicySerial += 1;

        const next = Object.assign({}, volumePolicies);
        next[policyKey] = {
            scope: String(scope || "").trim().toLowerCase(),
            semanticKey: String(key || ""),
            descriptor: stored,
            percent: clampVolume(percent),
            serial: volumePolicySerial
        };

        volumePolicies = next;
        requestPolicyRefresh();
        return true;
    }

    function clearVolumePolicy(scope, key) {
        const policyKey = volumePolicyKey(scope, key);
        if (!policyKey || volumePolicies[policyKey] === undefined)
            return false;

        const next = Object.assign({}, volumePolicies);
        delete next[policyKey];
        volumePolicies = next;
        return true;
    }

    function volumePolicyPercentFor(scope, key) {
        const policyKey = volumePolicyKey(scope, key);
        if (!policyKey || volumePolicies[policyKey] === undefined)
            return -1;

        return Number(volumePolicies[policyKey].percent);
    }

    // Pure policy planners keep matching/arbitration testable without issuing
    // mutations. The apply* functions below are the only layer that turns a
    // plan into pactl side effects.
    function mutePolicyTargets(inputs, policies) {
        const source = Array.isArray(inputs) ? inputs : [];
        const policyMap = policies || ({});
        const keys = Object.keys(policyMap);
        const targets = [];

        for (let i = 0; i < source.length; i++) {
            const input = source[i];
            const index = Number(input.index);

            if (isNaN(index) || input.mute)
                continue;

            for (let p = 0; p < keys.length; p++) {
                const policy = policyMap[keys[p]] || {};
                if (!matchesDescriptor(policy.descriptor, input))
                    continue;

                targets.push(index);
                break;
            }
        }

        return targets;
    }

    function pendingMuteTargets(inputs, policies) {
        const source = Array.isArray(inputs) ? inputs : [];
        const policyMap = policies || ({});
        const keys = Object.keys(policyMap);
        const targets = [];

        for (let k = 0; k < keys.length; k++) {
            const policy = policyMap[keys[k]] || {};

            for (let i = 0; i < source.length; i++) {
                const input = source[i];
                const index = Number(input.index);

                if (isNaN(index)
                        || !matchesDescriptor(policy.descriptor, input))
                    continue;

                if (!!input.mute !== !!policy.muted) {
                    targets.push({
                        index: index,
                        muted: !!policy.muted
                    });
                }
            }
        }

        return targets;
    }

    function volumePolicyTargets(inputs, policies) {
        const source = Array.isArray(inputs) ? inputs : [];
        const policyMap = policies || ({});
        const targets = ({});
        const keys = Object.keys(policyMap);

        function consider(index, percent, serial) {
            const key = String(index);
            const candidateSerial = Number(serial || 0);
            const current = targets[key];

            if (!current
                    || candidateSerial >= Number(current.serial || 0)) {
                targets[key] = {
                    percent: applicationAudioService.clampVolume(percent),
                    serial: candidateSerial
                };
            }
        }

        for (let p = 0; p < keys.length; p++) {
            const policy = policyMap[keys[p]] || {};

            for (let i = 0; i < source.length; i++) {
                const input = source[i];
                const index = Number(input.index);

                if (isNaN(index)
                        || !matchesDescriptor(policy.descriptor, input))
                    continue;

                consider(index, policy.percent, policy.serial);
            }
        }

        return targets;
    }

    function applyMutePolicies(inputs) {
        const targets = mutePolicyTargets(inputs, mutePolicies);

        for (let i = 0; i < targets.length; i++)
            setSinkInputMute([targets[i]], true);
    }

    function applyPendingMuteStates(inputs) {
        const targets = pendingMuteTargets(inputs, pendingMuteStates);

        for (let i = 0; i < targets.length; i++)
            setSinkInputMute([targets[i].index], targets[i].muted);

        // One-shot synchronization: persistent mute behavior lives in
        // mutePolicies, just as in the donor.
        pendingMuteStates = ({});
    }

    function applyVolumePolicies(inputs) {
        const targets = volumePolicyTargets(inputs, volumePolicies);
        const targetIndexes = Object.keys(targets);

        for (let i = 0; i < targetIndexes.length; i++) {
            const indexText = targetIndexes[i];
            const index = Number(indexText);
            const target = Number(targets[indexText].percent);
            let current = NaN;

            for (let j = 0; j < inputs.length; j++) {
                if (Number(inputs[j].index) === index) {
                    current = sinkInputVolumePercent(inputs[j]);
                    break;
                }
            }

            if (isNaN(current) || Math.abs(current - target) >= 1.0)
                setSinkInputVolumes([index], target);
        }
    }

    function applyPolicies(inputs) {
        applyMutePolicies(inputs);
        applyPendingMuteStates(inputs);
        applyVolumePolicies(inputs);
        policyApplied();
    }

    Timer {
        id: refreshTimer
        interval: 80
        repeat: false

        onTriggered: {
            applicationAudioService.loading = true;
            discoveryProcess.exec([
                "pactl",
                "-f",
                "json",
                "list",
                "sink-inputs"
            ]);
        }
    }

    Process {
        id: discoveryProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const inputs = applicationAudioService.parseSinkInputs(text);
                    applicationAudioService.observationGeneration += 1;
                    applicationAudioService.sinkInputs = inputs;
                    applicationAudioService.errorText = "";
                    applicationAudioService.refreshed(inputs);
                } catch (error) {
                    applicationAudioService.errorText = String(error);
                }

                applicationAudioService.loading = false;
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0)
                    applicationAudioService.errorText = message;
            }
        }
    }

    Timer {
        id: policyTimer
        interval: 1200
        repeat: true
        triggeredOnStart: true

        running:
            Object.keys(applicationAudioService.mutePolicies).length > 0
            || Object.keys(applicationAudioService.pendingMuteStates).length > 0
            || Object.keys(applicationAudioService.volumePolicies).length > 0

        onTriggered: {
            policyProcess.exec([
                "pactl",
                "-f",
                "json",
                "list",
                "sink-inputs"
            ]);
        }
    }

    Timer {
        id: policyRefreshTimer
        interval: 40
        repeat: false

        onTriggered: {
            policyProcess.exec([
                "pactl",
                "-f",
                "json",
                "list",
                "sink-inputs"
            ]);
        }
    }

    Process {
        id: policyProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const inputs = applicationAudioService.parseSinkInputs(text);
                    applicationAudioService.observationGeneration += 1;
                    applicationAudioService.sinkInputs = inputs;
                    applicationAudioService.errorText = "";
                    applicationAudioService.applyPolicies(inputs);
                    applicationAudioService.refreshed(inputs);
                } catch (error) {
                    applicationAudioService.errorText = String(error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0)
                    applicationAudioService.errorText = message;
            }
        }
    }
}
