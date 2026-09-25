import QtQuick
import Quickshell

// Standalone Team 6 runtime probe.
//
// Load this file explicitly as a Quickshell configuration while Team 6 remains
// off the serialized AppControl host lane. The probe performs synthetic
// descriptor/matching checks and one read-only live sink-input discovery pass.
//
// It never calls Team 6 mute/volume mutation APIs.
Scope {
    id: probeRoot

    property int checks: 0
    property int failures: 0
    property bool liveSnapshotSeen: false

    function expect(condition, label) {
        checks += 1;

        if (condition) {
            console.log("TEAM6 PROBE PASS", label);
            return;
        }

        failures += 1;
        console.log("TEAM6 PROBE FAIL", label);
    }

    function syntheticInput(index, pid, binary, appId, appName, mediaName) {
        return {
            index: index,
            mute: false,
            volume: {
                "front-left": { value_percent: "50%" },
                "front-right": { value_percent: "50%" }
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

    function runSyntheticChecks() {
        const brave = syntheticInput(
            42,
            4242,
            "brave",
            "com.brave.Browser",
            "Brave",
            "Playback"
        );

        let descriptor = {
            pids: [4242],
            tokens: [],
            strictTokens: true
        };

        let evidence = audio.descriptorMatchEvidence(descriptor, brave);
        expect(evidence.matched, "exact PID matches");
        expect(evidence.pidMatch, "exact PID is reported as PID evidence");

        descriptor = {
            pids: [],
            tokens: ["brave"],
            strictTokens: true
        };
        evidence = audio.descriptorMatchEvidence(descriptor, brave);
        expect(evidence.matched, "strict exact token matches");
        expect(!evidence.pidMatch, "token match stays separate from PID evidence");

        const firefox = syntheticInput(
            43,
            5000,
            "firefox",
            "org.mozilla.firefox",
            "Firefox",
            "Playback"
        );

        descriptor = {
            pids: [],
            tokens: ["orgmozillafirefox"],
            strictTokens: false
        };
        expect(
            audio.matchesDescriptor(descriptor, firefox),
            "fuzzy suffix mode preserves donor WINDOW/TAB behavior"
        );

        descriptor.strictTokens = true;
        expect(
            !audio.matchesDescriptor(descriptor, firefox),
            "strict mode rejects suffix-only match"
        );

        descriptor = {
            pids: [],
            tokens: ["app"],
            strictTokens: false
        };
        expect(
            !audio.matchesDescriptor(descriptor, firefox),
            "short fuzzy token is rejected"
        );

        const resolved = audio.resolve(
            {
                pids: [4242],
                tokens: [],
                strictTokens: true
            },
            [brave]
        );

        expect(resolved.hasStreams === true, "resolve reports stream existence");
        expect(resolved.streamsMuted === false, "resolve reports observed mute state");
        expect(
            Math.abs(resolved.observedVolumePercent - 50) < 0.01,
            "resolve reports observed volume"
        );
        expect(
            resolved.available === undefined,
            "resolve does not invent host AudioAvailable semantics"
        );
        expect(
            resolved.matches.length === 1
                && resolved.matches[0].evidence.pidMatch,
            "resolve carries separate join evidence"
        );

        expect(
            audio.volumePolicyKey(" APP ", "demo") === "app:demo",
            "volume policy scope normalization"
        );
        expect(
            audio.policyStorageKey(" WINDOW ", "demo") === "window:demo",
            "mute policy scope normalization"
        );
    }

    ApplicationAudioService {
        id: audio

        onRefreshed: function(inputs) {
            probeRoot.liveSnapshotSeen = true;
            const evidence = evidenceSnapshot(inputs);

            console.log(
                "TEAM6 PROBE live snapshot",
                "streams=" + evidence.length
            );

            for (let i = 0; i < evidence.length; i++) {
                const row = evidence[i];

                console.log(
                    "TEAM6 PROBE stream",
                    row.streamIndex,
                    "pid=" + String(row.applicationProcessId || ""),
                    "binary=" + String(row.applicationProcessBinary || ""),
                    "appId=" + String(row.applicationId || ""),
                    "appName=" + String(row.applicationName || ""),
                    "media=" + String(row.mediaName || "")
                );
            }
        }

        onErrorTextChanged: {
            if (errorText.length > 0)
                console.log("TEAM6 PROBE live discovery error", errorText);
        }
    }

    Component.onCompleted: {
        runSyntheticChecks();
        audio.refresh();
    }

    Timer {
        interval: 5000
        running: true
        repeat: false

        onTriggered: {
            console.log(
                failures === 0
                    ? "TEAM6 APPLICATION AUDIO PROBE: PASS"
                    : "TEAM6 APPLICATION AUDIO PROBE: FAIL",
                "checks=" + probeRoot.checks,
                "failures=" + probeRoot.failures,
                "liveSnapshotSeen=" + probeRoot.liveSnapshotSeen
            );

            Qt.quit();
        }
    }
}
