#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"../..");
const read = name => fs.readFileSync(path.join(root,name),"utf8");
const policy={};
vm.runInNewContext(
    read("services/connections/ConnectionsBrokerPolicy.js")
        .replace(/^\.pragma library\s*/m, ""), policy);

function normalized(x) {return JSON.parse(JSON.stringify(x))}
assert.equal(policy.VERSION,1);
assert.deepEqual(normalized(policy.requirement("nasa-firms")),{
    known:true, provider:"nasa-firms", credentialKind:"api-key",
    operations:["fires.hotspots.read"], consumers:["weather-earth"],
    authentication:"keyring-key+provider-validation", grantEnabled:false
});
assert.deepEqual(normalized(policy.requirement("proton-mail")),{
    known:true, provider:"proton-mail", credentialKind:"mail-session",
    operations:["mail.read","mail.send","mail.modify"],
    consumers:["social-mail","notifications-mail"],
    authentication:"authenticated-mail-adapter+message-identity",
    grantEnabled:false
});
assert.equal(policy.requirement("not-listed").known,false);
assert.equal(policy.requirement("__proto__").known,false);
assert.equal(policy.requirement("nasa-firms/x").known,false);
assert.equal(policy.requirement("nasa-firms\nsecret").known,false);

for(const scope of [
    ["nasa-firms","weather-earth","fires.hotspots.read","TRUSTED_BROKER_NOT_ACTIVATED"],
    ["nasa-firms","social-mail","fires.hotspots.read","CONSUMER_NOT_REGISTERED"],
    ["nasa-firms","weather-earth","mail.read","SCOPE_NOT_ALLOWED"],
    ["proton-mail","social-mail","mail.send","TRUSTED_BROKER_NOT_ACTIVATED"],
    ["proton-mail","notifications-mail","mail.modify","TRUSTED_BROKER_NOT_ACTIVATED"],
    ["proton-mail","weather-earth","mail.read","CONSUMER_NOT_REGISTERED"],
    ["bogus","weather-earth","fires.hotspots.read","UNKNOWN_PROVIDER"],
]) {
    const d=policy.decision({provider:scope[0],consumer:scope[1],
                              operation:scope[2]});
    assert.equal(d.allowed,false);
    assert.equal(d.reason,scope[3]);
}
assert.equal(policy.decision({}).allowed,false);
for(const s of [
    "SERVICE_ACQUIRED","SERVICE_NOT_RUNNING","DBUS_PROBE_TOOL_MISSING",
    "SESSION_BUS_UNAVAILABLE","UNEXPECTED_DBUS_RESPONSE","WRONG_RESPONSE"
]) {
    const info=policy.normalizedProbe({status:s});
    assert.equal(info.unlocked,false);
    assert.equal(info.grantsEnabled,false);
    assert.equal(info.available,s==="SERVICE_ACQUIRED");
}
assert.equal(policy.normalizedProbe(null).status,"UNVERIFIED");
assert.equal(policy.normalizedProbe({status:"SERVICE_ACQUIRED",unlocked:true,grantsEnabled:true}).unlocked,false);

const service=read("services/connections/ConnectionsBroker.qml");
const details=read("widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml");
const moduleFile=read("services/connections/qmldir");
assert.match(service,/pragma Singleton/);
assert.match(moduleFile,/singleton ConnectionsBroker 1\.0 ConnectionsBroker.qml/);
assert.match(service,/readonly property bool credentialActionsEnabled: false/);
assert.match(service,/BrokerPolicy\.decision\(request\)/);
assert.match(service,/BrokerPolicy\.normalizedProbe\(result\)/);
assert.match(service,/function checkAvailability\(\)/);
assert.match(service,/running: false/);
assert.match(service,/ConnectionsSecretServiceProbe\.py/);
assert.doesNotMatch(service,/secret-tool|ReadAlias|SearchItems|Unlock\(|OpenSession\(|SetSecret|WriteCredential|FileView\s*\{/i);
assert.doesNotMatch(service,/Qt\.openUrlExternally|onCompleted:.*checkAvailability/i);
assert.match(details,/ConnectionsBroker\.requirement\(selectedId\)/);
assert.match(details,/ConnectionsBroker\.checkAvailability\(\)/);
assert.match(details,/CHECK KEYRING/);
assert.match(details,/GRANTS CLOSED/);
assert.match(details,/ConnectionsBroker\.label/);
assert.doesNotMatch(details,/passwordEchoMode|TextInput|secret-tool|credentialToClipboard/i);

console.log("C2a broker policy: known scopes, identity trust closed and read-only keyring UI PASS");
