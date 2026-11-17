"use strict";
// Execute the actual QML-imported JavaScript functions in a fresh JS VM.
// No request, FaceTime invite, phone number or contact leaves this test.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const file = "widgets/messanger/PhoneFaceTimeLinks.js";
const sandbox = vm.createContext({});
vm.runInContext(fs.readFileSync(file, "utf8"), sandbox, {filename: file});

const url = "https://facetime.apple.com/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA";
const normalized = sandbox.normalizeInvite(url);
assert.equal(normalized, url, "valid Apple invitation must preserve full token");
assert.equal(sandbox.normalizeInvite("  " + url + "  "), url);
const slash = url.replace("/join#", "/join/#");
assert.equal(sandbox.normalizeInvite(slash), slash, "Apple link slash variant");
for (const evil of [
    "http://facetime.apple.com/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA",
    "https://facetime.apple.com.evil.test/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA",
    "https://facetime.apple.com@evil.test/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA",
    "https://evil.test@facetime.apple.com/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA",
    "https://facetime.apple.com:443/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA",
    "https://facetime.apple.com/join?next=https://evil.test#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA",
    "https://facetime.apple.com/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA&redirect=https://evil.test",
    "https://facetime.apple.com/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA\nhttps://evil.test",
    "javascript:alert(1)", "facetime:15551234567", "facetime-audio:15551234567",
    "https://facetime.apple.com/join", "https://facetime.apple.com/join#v=1",
    "https://facetime.apple.com/join/#v=1&p=x&k=y", "#v=1&p=a&k=b",
    "https://facetime.apple.com/join#v=1&p=Ab1+QW4cR567Klm9&k=RvZ24B4smMfRWw19qzYWvA#extra",
    url + "A".repeat(2050),
    "", null, 1234, {}, [],
]) {
    assert.equal(sandbox.normalizeInvite(evil), "", "must refuse untrusted URL: " + String(evil).slice(0, 95));
}
const card = {
    hasAddressDetails: true,
    primary: "+1 (202) 555-0102",
    phoneNumbers: ["+1 (202) 555-0102"],
    emailAddresses: ["someone@example.test"],
};
assert.equal(sandbox.appleDeviceLink("audio", card), "facetime-audio:+12025550102");
assert.equal(sandbox.appleDeviceLink("video", card), "facetime:+12025550102");
assert.equal(sandbox.appleDeviceLink("VIDEO", card), "");
assert.equal(sandbox.appleDeviceLink("audio", null), "");
assert.equal(sandbox.appleDeviceLink("audio", {...card, hasAddressDetails:false}), "");
assert.equal(sandbox.appleDeviceLink("audio", {
    hasAddressDetails:true, phoneNumbers:[], emailAddresses:["someone@example.test"]
}), "facetime-audio:someone@example.test");
assert.equal(sandbox.appleDeviceLink("video", {
    hasAddressDetails:true, phoneNumbers:["tel:12025550102"], emailAddresses:[]
}), "");
assert.equal(sandbox.appleDeviceLink("video", {
    hasAddressDetails:true, phoneNumbers:["1;rm -rf"], emailAddresses:[]
}), "");
assert.equal(sandbox.appleDeviceLink("video", {
    hasAddressDetails:true, primary:"+12025550102", phoneNumbers:[], emailAddresses:[]
}), "", "primary display string alone is not authorized routing data");
assert.equal(sandbox.appleDeviceLink("audio", {
    hasAddressDetails:true, phoneNumbers:[], emailAddresses:["a@b.test#x"]
}), "", "email must never carry URI delimiter injection");
assert.match(sandbox.supportMessage("audio"), /Bluetooth.*cannot verify/);
assert.match(sandbox.supportMessage("video"), /no native FaceTime/);
console.log("FACETIME_HANDOFF_PASS // LIVE_JS_ALLOWLIST_AND_CONTACT_SOURCE_DENY_ONLY");
