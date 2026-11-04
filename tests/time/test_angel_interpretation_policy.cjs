// ANGEL M2 pure interpretation UI input/provenance contracts.
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "../..");
const raw = fs.readFileSync(path.join(root,
    "services/time/AngelInterpretationPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*$/m, "");
const policy = {};
vm.runInNewContext(raw, policy, {filename: "AngelInterpretationPolicy.js"});
const copy = (x) => JSON.parse(JSON.stringify(x));

for (const digits of ["0", "101", "202", "222", "347", "0000"]) {
    assert.equal(policy.validDigits(digits), true);
    assert.equal(policy.lookupEligible(digits), true);
    assert.equal(policy.lookupUrl(digits),
        "https://www.astrology.com/numerology/angel-numbers/"
        + digits + "-meaning");
}
for (const digits of ["12345", "12345678"]) {
    assert.equal(policy.validDigits(digits), true);
    assert.equal(policy.lookupEligible(digits), false);
    assert.equal(policy.lookupUrl(digits), "");
}
for (const bad of ["", "5:55", "347\n", "../347", "１２３", "123456789"]) {
    assert.equal(policy.lookupEligible(bad), false);
    assert.equal(policy.lookupUrl(bad), "");
}
assert.deepEqual(copy(policy.arithmeticReduction("347")), {sum:14,digit:5});
assert.deepEqual(copy(policy.arithmeticReduction("101")), {sum:2,digit:2});
assert.deepEqual(copy(policy.arithmeticReduction("0000")), {sum:0,digit:0});
assert.deepEqual(copy(policy.arithmeticReduction("9999")), {sum:36,digit:9});
assert.equal(policy.arithmeticReduction("../"), null);

const response = {
    status:"ready", digits:"347", provider:"Astrology.com",
    url:policy.lookupUrl("347"), section:"Numerology meaning",
    excerpt:"The publisher discusses number 347 through the numerological themes associated with its constituent digits and their combined interpretations."
};
const good = policy.interpretResponse(JSON.stringify(response), "347");
assert.equal(good.ok, true);
assert.equal(good.provider, "Astrology.com");
assert.equal(good.url, policy.lookupUrl("347"));
assert.equal(good.digits, "347");
for (const bad of [
    {...response, digits:"222"},
    {...response, url:"https://evil.example/numerology/angel-numbers/347-meaning"},
    {...response, provider:"Unverified"},
    {...response, section:"Wrong heading"},
    {...response, excerpt:"short"},
    {...response, excerpt:"a".repeat(251)},
    {...response, excerpt:"Line\nbreak"},
    {...response, status:"SOURCE_NOT_VERIFIED"}
]) {
    assert.equal(policy.interpretResponse(JSON.stringify(bad), "347").ok, false);
}
assert.equal(policy.interpretResponse("not json", "347").ok, false);
assert.equal(policy.interpretResponse(JSON.stringify(response), "12345678").ok, false);

console.log("ANGEL_INTERPRETATION_POLICY_PASS");
