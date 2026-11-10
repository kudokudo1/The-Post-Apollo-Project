#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalDictationTextPolicy.js"), "utf8");
const ctx = vm.createContext({});
vm.runInContext(source, ctx);
const merge = (a,b,cap=4000) => ctx.appendTranscription(a,b,cap);

let checks = 0;
function accept(before, speech, expected, max=4000) {
    checks++;
    const result = merge(before,speech,max);
    assert.equal(result.accepted,true);
    assert.equal(result.text,expected);
    assert.equal(result.submitted,false);
    assert.equal(result.saved,false);
    assert.equal(result.launched,false);
}
function refuse(before,speech,reason,max=4000){
    checks++;
    const result = merge(before,speech,max);
    assert.equal(result.accepted,false);
    assert.equal(result.text,before);
    assert.match(result.reason,reason);
}
accept("","Inspect the Finance widget","Inspect the Finance widget");
accept("Inspect the Finance widget","report bugs","Inspect the Finance widget report bugs");
accept("Keep my draft\n","new spoken sentence","Keep my draft\nnew spoken sentence");
accept("First sentence.","Second sentence.","First sentence. Second sentence.");
accept("left","\nspoken   with\twhitespace\n","left spoken with whitespace");
accept("typed meanwhile","dictated after user typing","typed meanwhile dictated after user typing");
accept("Existing","NEW", "Existing NEW", 15);
refuse("Existing","LONGER THAN LIMIT",/TEXT LIMIT/, 15);
refuse("Unchanged","",/NO USABLE SPEECH/);
refuse("Unchanged","    \t\n   ",/NO USABLE SPEECH/);
refuse("Never lose work",null,/NO USABLE SPEECH/);
refuse("x".repeat(3999),"another word",/TEXT LIMIT/);
assert.equal(merge("a", "\u0000").accepted,false);
assert.equal(merge("a", "\u007f").accepted,false);
assert.equal(merge("a","z",1).accepted,false);
assert.equal(merge("A", "B", 3).accepted,true);
assert(!source.includes("...")); // Qt QML parser compatibility regression
console.log("HOSPITAL SURGERY DICTATION // PASS // "+checks+
    " insertion scenarios, current text preserved, no autosubmit/authority");
