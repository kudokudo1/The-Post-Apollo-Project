#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const {spawnSync} = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const repo = path.resolve(__dirname,"../..");
const file = path.join(repo,"tests/connections/fixtures/C2bFakeBrokerOnly.cjs");
const script = fs.readFileSync(file,"utf8");
const setup = fs.readFileSync(
    path.join(repo,"tests/connections/fixtures/C2bSecretServiceIsolated.sh"),
    "utf8"
);

// Guard before all modes, including a forged namespace and fake GITHUB_ACTIONS.
const testEnv = {...process.env,
    GITHUB_ACTIONS: "",
    POST_APOLLO_C2B_FAKE_ONLY: "",
    DBUS_SESSION_BUS_ADDRESS: ""
};
for (const argv of [
    [],["--seed","ab".repeat(16)],["--exercise","ab".repeat(16)],
    ["--missing","ab".repeat(16)],["--cleanup","ab".repeat(16)]
]) {
    const res = spawnSync(process.execPath,[file,...argv],{
        env:testEnv,encoding:"utf8",timeout:3000,maxBuffer:512
    });
    assert.equal(res.status,1);
    assert.equal(res.stdout.trim(),"REFUSED_C2B_DISPOSABLE_GUARD");
    assert.equal(res.stderr,"");
}
assert.match(script,/GITHUB_ACTIONS !== "true"/);
assert.match(script,/POST_APOLLO_C2B_FAKE_ONLY !== "1"/);
assert.match(script,/postapollo-c2b-ci-/);
assert.match(script,/DBUS_SESSION_BUS_ADDRESS/);
assert.match(script,/C2B_DISPOSABLE_ONLY/);
assert.match(script,/private.*SIMULATION|in-process SIMULATION/i);
assert.match(script,/const impostor = Object\.freeze/);
assert.match(script,/actor !== authorizedActor/);
assert.match(script,/grant(?:ed)?\.delete\(token\)/);
assert.match(script,/g\.revoked/);
assert.match(script,/when >= g\.until/);
assert.match(script,/operation !== OPERATION/);
assert.match(script,/provider !== SCOPE/);
assert.match(script,/lookup\(nonce\).*Key retrieved only after grant check/);
assert.match(script,/fakeProvider\(secret,SOURCE,BOUNDS,1\)/);
assert.match(script,/observations:\[/);
assert.match(script,/simulated:true/);
assert.match(script,/secretTool\(\["store", "--label="/);
assert.match(script,/secretTool\(\["clear",\.\.\.attrs\(nonce\)\]/);
assert.match(script,/secretTool\(\["lookup", \.\.\.attrs\(nonce\)\]/);
// Assert on executable code, not comments mentioning network tools.
const executable = script.split("\n")
    .filter(line => !line.trim().startsWith("//")
                    && !line.trim().startsWith("*"))
    .join("\n");
assert.doesNotMatch(executable,/https?:\/\/|\bfetch\s*\(|XMLHttpRequest|spawnSync\(["']curl|request_url\(/);
assert.doesNotMatch(script,/POST_APOLLO_FIRMS_MAP_KEY|Quickshell|services\/hub\/ApolloHubTodo/);
assert.doesNotMatch(script,/console\.log\(secret|JSON\.stringify\(secret/);
assert.match(setup,/dbus-run-session/); // workflow wraps the script, not script itself
assert.match(setup,/gnome-keyring-daemon --unlock --components=secrets/);
assert.match(setup,/unset POST_APOLLO_FIRMS_MAP_KEY/);
assert.match(setup,/C2B_MISSING_KEY_REFUSED/);
assert.match(setup,/C2B_SYNTHETIC_ITEM_CLEARED/);
assert.match(setup,/C2B_PASS \/\/ ISOLATED_SECRET_SERVICE/);
assert.doesNotMatch(setup,/sudo|systemctl|quickshell -p|Qt\.openUrlExternally/);

// Production remains explicitly closed: no QML writes, no credential entry,
// no real NASA request helper changes or implicit provider activation.
const productionBroker = fs.readFileSync(
    path.join(repo,"services/connections/ConnectionsBroker.qml"),"utf8");
const productionPolicy = fs.readFileSync(
    path.join(repo,"services/connections/ConnectionsBrokerPolicy.js"),"utf8");
assert.match(productionBroker,/readonly property bool credentialActionsEnabled: false/);
assert.match(productionPolicy,/return \{allowed:false,reason:"TRUSTED_BROKER_NOT_ACTIVATED"\}/);
const firms = fs.readFileSync(
    path.join(repo,"services/weather/FirmsHotspotService.qml"),"utf8");
assert.match(firms,/Quickshell\.env\("POST_APOLLO_FIRMS_MAP_KEY"\)/);

console.log("C2b fake broker test isolation, denied production authority and secret boundaries: PASS");
