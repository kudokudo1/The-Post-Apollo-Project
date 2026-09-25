import QtQuick
import QtTest
import "../../services/audio"

TestCase {
    name: "Team6ApplicationAudioContracts"

    ApplicationAudioService {
        id: audio
    }

    function sinkInput(index, pid, binary, appId, appName, mediaName, muted, percent) {
        const value = percent === undefined ? 50 : percent;

        return {
            index: index,
            mute: !!muted,
            volume: {
                "front-left": { value_percent: String(value) + "%" },
                "front-right": { value_percent: String(value) + "%" }
            },
            properties: {
                "application.process.id": String(pid || 0),
                "application.process.binary": binary || "",
                "application.id": appId || "",
                "application.name": appName || "",
                "media.name": mediaName || ""
            }
        };
    }

    function test_normalizeTokenPreservesDonorShape() {
        compare(audio.normalizeToken("org.mozilla.Firefox.desktop"), "orgmozillafirefox");
        compare(audio.normalizeToken("Brave Browser"), "bravebrowser");
        compare(audio.normalizeToken(""), "");
    }

    function test_tokenMatchingRiskModes() {
        compare(audio.tokensMatch("brave", "brave", true), true);
        compare(audio.tokensMatch("org.mozilla.firefox", "firefox", false), true);
        compare(audio.tokensMatch("org.mozilla.firefox", "firefox", true), false);
        compare(audio.tokensMatch("app", "myapp", false), false);
    }

    function test_descriptorCopySanitizesEvidence() {
        const descriptor = audio.copyDescriptor({
            pids: [4242, "4242", 1, 0, -9, 5151],
            tokens: [
                "org.mozilla.Firefox.desktop",
                "org.mozilla.Firefox.desktop",
                "Firefox"
            ],
            strictTokens: true
        });

        compare(descriptor.pids.length, 2);
        compare(descriptor.pids[0], 4242);
        compare(descriptor.pids[1], 5151);
        compare(descriptor.tokens.length, 2);
        compare(descriptor.tokens[0], "orgmozillafirefox");
        compare(descriptor.tokens[1], "firefox");
        compare(descriptor.strictTokens, true);
    }

    function test_exactPidEvidenceIsSeparateFromTokenEvidence() {
        const stream = sinkInput(
            41,
            4242,
            "brave",
            "com.brave.Browser",
            "Brave",
            "Playback",
            false,
            55
        );

        const evidence = audio.descriptorMatchEvidence({
            pids: [4242],
            tokens: [],
            strictTokens: true
        }, stream);

        compare(evidence.matched, true);
        compare(evidence.pidMatch, true);
        compare(evidence.processId, 4242);
        compare(evidence.streamIndex, 41);
        compare(evidence.tokenMatches.length, 0);
    }

    function test_strictAppMatchingRejectsSuffixOnlyAlias() {
        const stream = sinkInput(
            42,
            5000,
            "firefox",
            "org.mozilla.firefox",
            "Firefox",
            "Playback",
            false,
            50
        );

        compare(audio.matchesDescriptor({
            pids: [],
            tokens: ["orgmozillafirefox"],
            strictTokens: true
        }, stream), false);

        compare(audio.matchesDescriptor({
            pids: [],
            tokens: ["firefox"],
            strictTokens: true
        }, stream), true);
    }

    function test_fuzzyWindowTabMatchingAllowsSuffixEvidence() {
        const stream = sinkInput(
            43,
            5000,
            "firefox",
            "org.mozilla.firefox",
            "Firefox",
            "Playback",
            false,
            50
        );

        const evidence = audio.descriptorMatchEvidence({
            pids: [],
            tokens: ["orgmozillafirefox"],
            strictTokens: false
        }, stream);

        compare(evidence.matched, true);
        compare(evidence.pidMatch, false);
        verify(evidence.tokenMatches.length > 0);
    }

    function test_strictPropertyTokensBlockGenericAliases() {
        const tokens = audio.streamPropertyTokens({
            "application.process.binary": "electron",
            "application.id": "com.example.Editor",
            "application.name": "Editor"
        }, true);

        compare(tokens.indexOf("electron"), -1);
        verify(tokens.indexOf("comexampleeditor") !== -1);
        verify(tokens.indexOf("editor") !== -1);
    }

    function test_resolveReportsPhysiologyNotHostAvailability() {
        const stream = sinkInput(
            44,
            6000,
            "demo",
            "org.example.demo",
            "Demo",
            "Playback",
            false,
            40
        );

        const resolved = audio.resolve({
            pids: [6000],
            tokens: [],
            strictTokens: true
        }, [stream]);

        compare(resolved.hasStreams, true);
        compare(resolved.streamsMuted, false);
        compare(resolved.observedVolumePercent, 40);
        compare(resolved.indexes.length, 1);
        compare(resolved.indexes[0], 44);
        compare(resolved.matches.length, 1);
        compare(resolved.matches[0].evidence.pidMatch, true);
        compare(resolved.available, undefined);
    }

    function test_resolveNoStreamUsesUnknownObservedVolume() {
        const resolved = audio.resolve({
            pids: [7000],
            tokens: [],
            strictTokens: true
        }, []);

        compare(resolved.hasStreams, false);
        compare(resolved.streamsMuted, false);
        compare(resolved.observedVolumePercent, -1);
    }

    function test_volumeMathNeverAmplifiesAboveUnity() {
        const streamA = sinkInput(
            45, 8000, "a", "a", "A", "Playback", false, 120
        );
        const streamB = sinkInput(
            46, 8001, "b", "b", "B", "Playback", false, 80
        );

        compare(audio.clampVolume(-20), 0);
        compare(audio.clampVolume(120), 100);
        compare(audio.averagedSinkVolume([streamA]), 100);
        compare(audio.averagedSinkVolume([streamA, streamB]), 100);
    }

    function test_rawEvidencePreservesPipeWireFields() {
        const stream = sinkInput(
            47,
            9000,
            "code",
            "com.visualstudio.code",
            "Visual Studio Code",
            "Playback",
            true,
            35
        );

        const evidence = audio.streamEvidence(stream);

        compare(evidence.streamIndex, 47);
        compare(evidence.mute, true);
        compare(evidence.applicationProcessId, "9000");
        compare(evidence.applicationProcessBinary, "code");
        compare(evidence.applicationId, "com.visualstudio.code");
        compare(evidence.applicationName, "Visual Studio Code");
        compare(evidence.mediaName, "Playback");
        compare(evidence.properties["application.id"], "com.visualstudio.code");
    }

    function test_team7ObservationAdapterKeepsProvenance() {
        audio.observationGeneration = 12;

        const stream = sinkInput(
            48,
            9100,
            "kitty",
            "kitty",
            "kitty",
            "Playback",
            false,
            60
        );

        const observation = audio.streamObservation(stream);

        compare(observation.provider, "PIPEWIRE");
        compare(observation.providerKey, "sink-input:48");
        compare(observation.lifetimeClass, "ephemeral");
        compare(observation.generation, 12);
        compare(observation.raw.streamIndex, 48);
        verify(observation.aliases.length > 0);

        let sawBinary = false;
        for (let i = 0; i < observation.aliases.length; i++) {
            const alias = observation.aliases[i];
            if (alias.kind === "application.process.binary") {
                sawBinary = true;
                compare(alias.value, "kitty");
                compare(alias.normalized, "kitty");
                compare(alias.provider, "PIPEWIRE");
            }
        }

        verify(sawBinary);

        compare(observation.relationships.length, 1);
        compare(observation.relationships[0].kind, "EXACT_PID");
        compare(observation.relationships[0].targetProvider, "PROCFS");
        compare(observation.relationships[0].targetKey, "pid:9100");
        compare(observation.relationships[0].strength, "exact");
        compare(
            observation.relationships[0].sourceField,
            "application.process.id"
        );

        compare(observation.semanticKey, undefined);
        compare(observation.applicationEntity, undefined);
    }

    function test_team7ObservationOmitsInvalidPidRelationship() {
        const stream = sinkInput(
            49,
            1,
            "demo",
            "org.example.demo",
            "Demo",
            "Playback",
            false,
            50
        );

        const observation = audio.streamObservation(stream);

        compare(observation.relationships.length, 0);
    }

    function test_parseSinkInputsAcceptsPactlArray() {
        const parsed = audio.parseSinkInputs(
            '[{"index":51,"mute":false,"properties":{"application.id":"demo"}}]'
        );

        compare(parsed.length, 1);
        compare(parsed[0].index, 51);
        compare(parsed[0].properties["application.id"], "demo");
    }

    function test_parseSinkInputsRejectsInvalidPayloads() {
        let malformedThrew = false;
        let objectThrew = false;

        try {
            audio.parseSinkInputs("{not-json");
        } catch (error) {
            malformedThrew = true;
        }

        try {
            audio.parseSinkInputs('{"index":51}');
        } catch (error) {
            objectThrew = true;
        }

        compare(malformedThrew, true);
        compare(objectThrew, true);
    }

    function test_sinkInputVolumeSupportsRawPulseValue() {
        const stream = {
            volume: {
                mono: { value: 32768 }
            }
        };

        compare(audio.sinkInputVolumePercent(stream), 50);
    }

    function test_futureStreamMutePolicyPlanning() {
        const policies = {
            "app:demo": {
                scope: "app",
                semanticKey: "demo",
                descriptor: {
                    pids: [10001],
                    tokens: [],
                    strictTokens: true
                }
            }
        };

        const noMatch = sinkInput(
            60, 10000, "other", "other", "Other", "Playback", false, 50
        );
        const futureMatch = sinkInput(
            61, 10001, "demo", "demo", "Demo", "Playback", false, 50
        );

        compare(audio.mutePolicyTargets([noMatch], policies).length, 0);

        const targets = audio.mutePolicyTargets([futureMatch], policies);
        compare(targets.length, 1);
        compare(targets[0], 61);
    }

    function test_pendingMutePlannerSupportsOneShotUnmute() {
        const policies = {
            "window:demo": {
                scope: "window",
                semanticKey: "demo",
                descriptor: {
                    pids: [11001],
                    tokens: [],
                    strictTokens: false
                },
                muted: false
            }
        };

        const mutedStream = sinkInput(
            62, 11001, "demo", "demo", "Demo", "Playback", true, 50
        );

        const targets = audio.pendingMuteTargets([mutedStream], policies);
        compare(targets.length, 1);
        compare(targets[0].index, 62);
        compare(targets[0].muted, false);

        mutedStream.mute = false;
        compare(audio.pendingMuteTargets([mutedStream], policies).length, 0);
    }

    function test_latestVolumePolicySerialWinsOverlap() {
        const stream = sinkInput(
            63, 12001, "demo", "demo", "Demo", "Playback", false, 50
        );

        const policies = {
            "app:demo": {
                descriptor: {
                    pids: [12001],
                    tokens: [],
                    strictTokens: true
                },
                percent: 25,
                serial: 4
            },
            "window:demo": {
                descriptor: {
                    pids: [12001],
                    tokens: [],
                    strictTokens: false
                },
                percent: 70,
                serial: 9
            },
            "tab:demo": {
                descriptor: {
                    pids: [12001],
                    tokens: [],
                    strictTokens: false
                },
                percent: 40,
                serial: 7
            }
        };

        const targets = audio.volumePolicyTargets([stream], policies);

        compare(targets["63"].percent, 70);
        compare(targets["63"].serial, 9);
    }

    function test_volumePolicyPlannerClampsTarget() {
        const stream = sinkInput(
            64, 13001, "demo", "demo", "Demo", "Playback", false, 50
        );

        const targets = audio.volumePolicyTargets([stream], {
            "app:demo": {
                descriptor: {
                    pids: [13001],
                    tokens: [],
                    strictTokens: true
                },
                percent: 175,
                serial: 1
            }
        });

        compare(targets["64"].percent, 100);
    }

    function test_policyNamespacesNormalizeScopeOnly() {
        compare(audio.policyStorageKey(" APP ", "demo"), "app:demo");
        compare(audio.policyStorageKey("WINDOW", "demo"), "window:demo");
        compare(audio.policyStorageKey("tab", "demo"), "tab:demo");
        compare(audio.volumePolicyKey(" APP ", "demo"), "app:demo");

        // Semantic keys are external coordinates and must not be normalized by
        // Team 6 into a competing identity model.
        compare(
            audio.policyStorageKey("app", "Org.Example.App"),
            "app:Org.Example.App"
        );
    }
}
