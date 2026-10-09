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

console.log("PASS: Hi-Fi resolver evidence, ambiguity, and fail-closed targeting");
