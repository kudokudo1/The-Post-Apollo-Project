#!/usr/bin/env node
"use strict";
// Real identity policy in a Node VM: no account access, filesystem writes
// or GUI runtime. QML .pragma is removed for these isolated policy tests.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/social/SocialIdentityPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, {filename:"SocialIdentityPolicy.js"});

const apps = [
    "sessions","discord","telegram","x","instagram","facebook",
    "reddit","threads","pinterest","truthsocial","bluesky",
    "tumblr","tiktok","snapchat","whatsapp","messenger",
    "linkedin","mastodon","nextdoor","steamchat","element",
    "groupme","lemon8","quora","pixelfed","zalo","signal",
    "wechat","line","viber","kakaotalk","bereal"
];
assert.equal(policy.APP_IDS.join(","), apps.join(","));
const initial = policy.initialDocument();
assert.equal(policy.validate(initial).ok, true);
assert.equal(initial.identities.length, 1);
assert.equal(initial.activeId, "identity-1");
assert.equal(initial.identities[0].layout.families.length, 1);
assert.equal(initial.identities[0].layout.families[0].name, "ALL APPS");
assert.equal(initial.identities[0].layout.families[0].appIds.join(","), apps.join(","));
assert.equal(initial.identities[0].layout.hiddenAppIds.length, 0);

const defaultResult = policy.create(initial, " Personal ", "default", "");
assert.equal(defaultResult.ok, true);
const personal = defaultResult.document;
assert.equal(personal.activeId, "identity-2");
assert.equal(personal.identities[1].name, "Personal");
assert.equal(personal.identities[1].layout.families.length, 1);
assert.equal(initial.identities.length, 1);  // Immutable return.
assert.equal(initial.activeId, "identity-1");

const blankResult = policy.create(personal, "Gaming", "empty", "");
assert.equal(blankResult.ok, true);
const blank = blankResult.document;
assert.equal(blank.identities[2].layout.families.length, 0);
assert.equal(blank.identities[2].layout.hiddenAppIds.length, 0);
assert.equal(blank.identities[0].layout.families[0].appIds.length, 32);

const copyResult = policy.create(blank, "Work", "copy", "identity-2");
assert.equal(copyResult.ok, true);
const copy = copyResult.document;
assert.equal(copy.identities[3].layout.families[0].appIds.join(","), apps.join(","));
assert.equal(copy.identities[3].layout.families[0].id, "family-1");
copy.identities[3].layout.families[0].appIds.splice(0, 1);
copy.identities[3].layout.hiddenAppIds.push("discord");
assert.equal(blank.identities[1].layout.families[0].appIds.length, 32);
assert.equal(blank.identities[1].layout.hiddenAppIds.length, 0);
assert.equal(copy.identities[1].layout.families[0].appIds.length, 32);
assert.equal(policy.validate(copy).ok, true);
assert.equal(policy.create(blank, "Bad copy", "copy", "missing").reason,
             "INVALID_COPY_SOURCE");
assert.equal(policy.create(blank, "Bad", "launch", "").reason, "INVALID_MODE");
assert.equal(policy.create(blank, " gaming ", "empty", "").reason, "DUPLICATE_NAME");
assert.equal(policy.create(blank, "", "default", "").reason, "INVALID_NAME");
assert.equal(policy.create(blank, "bad\nname", "default", "").reason, "INVALID_NAME");
assert.equal(policy.create(blank, "a".repeat(33), "default", "").reason,
             "INVALID_NAME");

const selected = policy.select(blank, "identity-1");
assert.equal(selected.ok, true);
assert.equal(selected.document.activeId, "identity-1");
assert.equal(blank.activeId, "identity-3");
assert.equal(policy.select(blank, blank.activeId).reason, "NO_CHANGE");
assert.equal(policy.select(blank, "identity-400").reason, "INVALID_IDENTITY");
assert.equal(policy.view("ready", blank, "").writable, true);
assert.equal(policy.view("saving", blank, "").writable, false);
assert.equal(policy.view("error", blank, "INVALID_JSON").identities.length, 0);
assert.equal(policy.view("unsupported", blank, "UNSUPPORTED_VERSION").error,
             "UNSUPPORTED_VERSION");

const parsed = policy.parse(JSON.stringify(blank));
assert.equal(parsed.ok, true);
assert.equal(parsed.document.identities.length, 3);
assert.equal(policy.parse("").reason, "INVALID_FILE");
assert.equal(policy.parse("{bad").reason, "INVALID_JSON");
assert.equal(policy.parse("x".repeat(65537)).reason, "INVALID_FILE");
assert.equal(policy.parse(JSON.stringify({...blank, version:2})).reason,
             "UNSUPPORTED_VERSION");
assert.equal(policy.parse(JSON.stringify({...blank, activeId:"absent"})).reason,
             "INVALID_ACTIVE_ID");
assert.equal(policy.parse(JSON.stringify({...blank, nextIdentityId:2})).reason,
             "SEQUENCE_REWIND");

const dup = JSON.parse(JSON.stringify(blank));
dup.identities[1].id = dup.identities[0].id;
assert.equal(policy.validate(dup).ok, false);
const dupeApp = JSON.parse(JSON.stringify(blank));
dupeApp.identities[0].layout.families[0].appIds.push("discord");
assert.equal(policy.validate(dupeApp).ok, false);
const foreign = JSON.parse(JSON.stringify(blank));
foreign.identities[0].layout.families[0].appIds[0] = "unknown-site";
assert.equal(policy.validate(foreign).ok, false);

const injected = JSON.parse(JSON.stringify(blank));
injected.password = "NEVER_SAVE";
injected.apiHash = "NEVER_SAVE";
injected.identities[0].sessionFile = "NEVER_SAVE";
injected.identities[0].layout.authToken = "NEVER_SAVE";
injected.identities[0].layout.families[0].password = "NEVER_SAVE";
const sanitized = policy.parse(JSON.stringify(injected));
assert.equal(sanitized.ok, true);
assert.equal(JSON.stringify(sanitized.document).includes("NEVER_SAVE"), false);
assert.equal(JSON.stringify(policy.view("ready", sanitized.document, ""))
             .includes("sessionFile"), false);

let capped = JSON.parse(JSON.stringify(blank));
while (capped.identities.length < 12) {
    let n = capped.nextIdentityId++;
    capped.identities.push({id:"identity-"+n,name:"Extra"+n,
                            layout:policy.emptyLayout()});
}
assert.equal(policy.validate(capped).ok, true);
assert.equal(policy.create(capped, "Over", "empty", "").reason, "CAPACITY");
console.log("Social identity: three creation choices, isolation, schema and safety PASS");
