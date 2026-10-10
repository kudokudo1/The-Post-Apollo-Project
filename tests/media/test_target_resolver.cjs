#!/usr/bin/env node
"use strict";

// Pure, no-PipeWire mutation regression checks for the Hi-Fi evidence resolver.
// Run: node tests/media/test_target_resolver.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
    path.join(__dirname, "../../services/media/MediaAudioTargetResolver.js"),
    "utf8"
);
const api = vm.createContext({});
vm.runInContext(source, api, {filename: "MediaAudioTargetResolver.js"});

function input(index, title, pid = "1234") {
    return {
        index: index,
        properties: {
            "application.process.id": pid,
            "application.process.binary": "brave",
            "application.id": "brave-browser",
            "media.name": title
        }
    };
}

const music = input(11, "Music A");
const video = input(16, "Video B");
const tts = input(29, "Playback");

assert.equal(api.resolve("browser", "Video B", [music, video], null).input, video,
             "Unique exact media title may select a stream");
assert.equal(api.resolve("browser", "Elsewhere", [music, video], null).input, null,
             "No media-title match must not choose a default stream");
assert.equal(api.resolve("browser", "Playback", [tts], null).input, null,
             "Generic metadata is not a verified automatic target");
assert.equal(api.resolve("browser", "Video B",
                         [video, input(17, "Video B")], null).mode, "AMBIGUOUS",
             "Duplicate title evidence cannot select an automatic target");

const manuallyPinned = api.bindManual("browser", "Video B", music);
assert.equal(api.resolve("browser", "Video B",
                         [tts, video, music], manuallyPinned).input, music,
             "A newly appearing TTS stream cannot change the selected target");
assert.equal(api.resolve("browser", "Video B",
                         [video], manuallyPinned).input, null,
             "Disappearing pinned stream cannot fall back to another stream");
assert.equal(api.resolve("browser", "Music A",
                         [music, video], manuallyPinned).mode, "STALE",
             "Changing MPRIS title invalidates the manual stream binding");
assert.equal(api.resolve("other", "Video B",
                         [music, video], manuallyPinned).mode, "STALE",
             "Changing MPRIS player invalidates the manual stream binding");
assert.equal(api.resolve("browser", "Video B",
                         [input(11, "Music A", "9999"), video], manuallyPinned).input,
             null, "Reused stream indexes cannot impersonate a previous PID");

const noIdentity = {index: 34, properties: {"media.name": "Video B"}};
assert.equal(api.resolve("browser", "Video B", [noIdentity], null).input, null,
             "Stream mutation targets require process evidence");

// Model successive observed media switches while AUTO FOLLOW is selected.
// Each evaluation uses the current MPRIS track; the temporary third stream
// is never chosen simply because it appeared in the list first.
const threeSources = [tts, music, video];
assert.equal(api.resolve("browser", "Music A", threeSources, null).input, music,
             "Auto-follow music is selected by title evidence");
assert.equal(api.resolve("browser", "Video B", threeSources, null).input, video,
             "Switching to the video re-evaluates its target");
assert.equal(api.resolve("browser", "Music A", [video, music], null).input, music,
             "Returning to music does not require an extra manual selection");
assert.equal(api.resolve("browser", "No Match", threeSources, null).input, null,
             "Unknown titles must continue to fail closed");
assert.equal(api.sameFingerprint(video, api.fingerprint(video)), true,
             "An armed target fingerprint remains valid for the same stream");
assert.equal(api.sameFingerprint(music, api.fingerprint(video)), false,
             "An arm for one stream must not authorize another");

// Wiring contracts. These checks cannot execute QML, but prevent accidental
// removal of the persistent mode and the arm-to-mute identity guard.
const deckSource = fs.readFileSync(
    path.join(__dirname, "../../widgets/MediaDeckW.qml"), "utf8"
);
assert.match(deckSource, /property bool autoFollowEnabled: true/,
             "AUTO FOLLOW is initially enabled");
assert.match(deckSource, /autoFollowEnabled \? null : manualAudioBinding/,
             "AUTO FOLLOW bypasses a stale manual binding");
assert.match(deckSource, /onPlayerAudioSessionKeyChanged:\s*\{[^}]*manualAudioBinding = null;[^}]*autoFollowEnabled = true;/,
             "Media changes must expire manual targeting and re-enable AUTO FOLLOW");
assert.match(deckSource, /manualAudioBinding = binding;\s*autoFollowEnabled = false;/,
             "NEXT STREAM must clearly enter current-track manual mode");
assert.match(deckSource, /AudioTarget\.sameFingerprint\(selectedAudioCandidate,/,
             "ARM must not authorize mutation of a replacement stream");

console.log("PASS: Hi-Fi auto-follow evidence, mode handoff, and fail-closed targeting");
