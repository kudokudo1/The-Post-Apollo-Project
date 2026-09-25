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
    property bool loading: false
    property string errorText: ""

    // Persistent future-stream mute policies. A policy being present means
    // "keep matching streams muted"; unmute removes the persistent policy.
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
        const rawPids = descriptor.pids || [];

        for (let i = 0; i < rawPids.length; i++) {
            const pid = Number(rawPids[i] || 0);
            if (pid > 1 && pids.indexOf(pid) === -1)
                pids.push(pid);
        }

        const tokens = [];
        const rawTokens = descriptor.tokens || [];

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

    function matchesDescriptor(descriptor, sinkInput) {
        if (!descriptor || !sinkInput)
            return false;

        const props = sinkInput.properties || {};
        const processId = Number(props["application.process.id"] || 0);
        const pids = descriptor.pids || [];

        if (processId > 1 && pids.indexOf(processId) !== -1)
            return true;

        const wanted = descriptor.tokens || [];
        if (wanted.length === 0)
            return false;

        const strict = !!descriptor.strictTokens;
        const available = streamPropertyTokens(props, strict);

        for (let i = 0; i < wanted.length; i++) {
            for (let j = 0; j < available.length; j++) {
                if (tokensMatch(wanted[i], available[j], strict))
                    return true;
            }
        }

        return false;
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
        let allMuted = true;

        for (let i = 0; i < source.length; i++) {
            const input = source[i];

            if (!matchesDescriptor(descriptor, input))
                continue;

            matchingInputs.push(input);

            const index = Number(input.index);
            if (!isNaN(index))
                indexes.push(index);

            if (!input.mute)
                allMuted = false;
        }

        return {
            inputs: matchingInputs,
            indexes: indexes,
            available: matchingInputs.length > 0,
            muted: indexes.length > 0 && allMuted,
            volumePercent: matchingInputs.length > 0
                ? averagedSinkVolume(matchingInputs)
                : 100
        };
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
            if (isNaN(index))
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
            if (isNaN(index))
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

    function setMutePolicy(key, descriptor, enabled) {
        const policyKey = String(key || "");
        if (!policyKey)
            return false;

        const next = Object.assign({}, mutePolicies);

        if (enabled) {
            const stored = copyDescriptor(descriptor);
            if (!stored)
                return false;

            next[policyKey] = stored;
        } else {
            delete next[policyKey];
        }

        mutePolicies = next;
        requestPolicyRefresh();
        return true;
    }

    function mutePolicyActive(key) {
        const policyKey = String(key || "");
        return !!policyKey && mutePolicies[policyKey] !== undefined;
    }

    function queueMuteState(key, descriptor, muted) {
        const policyKey = String(key || "");
        const stored = copyDescriptor(descriptor);

        if (!policyKey || !stored)
            return false;

        const next = Object.assign({}, pendingMuteStates);
        next[policyKey] = {
            descriptor: stored,
            muted: !!muted
        };

        pendingMuteStates = next;
        requestPolicyRefresh();
        return true;
    }

    function clearPoliciesWithPid(pid) {
        const targetPid = Number(pid || 0);
        if (targetPid <= 1)
            return false;

        const keys = Object.keys(mutePolicies);
        const next = Object.assign({}, mutePolicies);
        let changed = false;

        for (let i = 0; i < keys.length; i++) {
            const descriptor = mutePolicies[keys[i]] || {};
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

    function volumePolicyKey(scope, key) {
        const scopeText = String(scope || "");
        const keyText = String(key || "");

        if (!scopeText || !keyText)
            return "";

        return scopeText + ":" + keyText;
    }

    function setVolumePolicy(scope, key, descriptor, percent) {
        const policyKey = volumePolicyKey(scope, key);
        const stored = copyDescriptor(descriptor);

        if (!policyKey || !stored)
            return false;

        volumePolicySerial += 1;

        const next = Object.assign({}, volumePolicies);
        next[policyKey] = {
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

    function applyMutePolicies(inputs) {
        const keys = Object.keys(mutePolicies);

        if (keys.length === 0)
            return;

        for (let i = 0; i < inputs.length; i++) {
            const input = inputs[i];
            const index = Number(input.index);

            if (isNaN(index) || input.mute)
                continue;

            for (let p = 0; p < keys.length; p++) {
                if (matchesDescriptor(mutePolicies[keys[p]], input)) {
                    setSinkInputMute([index], true);
                    break;
                }
            }
        }
    }

    function applyPendingMuteStates(inputs) {
        const keys = Object.keys(pendingMuteStates);

        if (keys.length === 0)
            return;

        for (let k = 0; k < keys.length; k++) {
            const policy = pendingMuteStates[keys[k]];

            for (let i = 0; i < inputs.length; i++) {
                const input = inputs[i];
                const index = Number(input.index);

                if (isNaN(index)
                        || !matchesDescriptor(policy.descriptor, input))
                    continue;

                if (!!input.mute !== !!policy.muted)
                    setSinkInputMute([index], !!policy.muted);
            }
        }

        // One-shot synchronization: persistent mute behavior lives in
        // mutePolicies, just as in the donor.
        pendingMuteStates = ({});
    }

    function applyVolumePolicies(inputs) {
        const targets = ({});
        const keys = Object.keys(volumePolicies);

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
            const policy = volumePolicies[keys[p]];

            for (let i = 0; i < inputs.length; i++) {
                const input = inputs[i];
                const index = Number(input.index);

                if (isNaN(index)
                        || !matchesDescriptor(policy.descriptor, input))
                    continue;

                consider(index, policy.percent, policy.serial);
            }
        }

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
