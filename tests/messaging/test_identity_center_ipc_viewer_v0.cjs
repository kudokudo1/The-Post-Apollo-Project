// Execute the ACTUAL QML JavaScript validation and read lifecycle functions.
// Does not claim a native Quickshell render, production host or account login.
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const reader = fs.readFileSync(path.join(
    root, "widgets/messanger/IdentityCenterOrganizationDisplayReader.qml"
), "utf8");
const sections = fs.readFileSync(path.join(
    root, "widgets/messanger/IdentityCenterSettingsSections.qml"
), "utf8");
const selector = fs.readFileSync(path.join(
    root, "widgets/messanger/AppSelector.qml"
), "utf8");

function qmlFunction(name) {
    const key = "    function " + name + "(";
    const begin = reader.indexOf(key);
    assert.ok(begin !== -1, "Missing QML function " + name);
    const brace = reader.indexOf("{", begin + key.length);
    assert.ok(brace !== -1, "Missing function body");
    let depth = 0;
    for (let pos = brace; pos < reader.length; pos++) {
        if (reader[pos] === "{") depth++;
        if (reader[pos] === "}") depth--;
        if (depth === 0)
            return reader.slice(begin, pos + 1);
    }
    throw new Error("Unterminated QML function " + name);
}

const sandbox = {
    active: true,
    snapshot: null,
    displaySchema: "post-apollo.identity.desktop-context-display.v0",
    pythonPath: "/usr/bin/python3",
    readerPath: "/fake-code/identity_display_reader_cli_v0.py",
    snapshotProcess: {running: false, command: []},
    Date: {now: () => 1000 * 1_800_000_000},
};
vm.createContext(sandbox);
vm.runInContext(
    ["clear", "exactKeys", "identifier", "validDisplay", "receive", "refresh"]
        .map(qmlFunction).join("\n\n"), sandbox,
);
function display() {
    return {
        schema: sandbox.displaySchema,
        status: "READY",
        organizations: [
            {organizationId: "llc_a", kind: "llc", scopeGrants: [{
                action: "records.read", divisionId: "health",
                unitId: "maryland", expiresAt: null,
            }]},
            {organizationId: "llc_b", kind: "llc", scopeGrants: []},
        ],
        portfolios: [{portfolioId: "family",
                      organizationIds: ["llc_a", "llc_b"]}],
        canSwitchOrganization: false,
    };
}
function accepted(value) {
    return sandbox.validDisplay(JSON.parse(JSON.stringify(value)));
}
function rejected(item, reason) {
    assert.equal(accepted(item), false, reason);
}
assert.equal(accepted(display()), true, "Valid tenant summary not displayable");

for (const [field, value] of Object.entries({
    accessToken: "secret", role: "admin", sessionId: "synthetic",
    principalId: "user", canSwitchOrganization: true,
})) {
    const candidate = display();
    candidate[field] = value;
    rejected(candidate, "Rejected extra authority field " + field);
}
let item = display();
item.portfolios[0].organizationIds.push("nonprofit");
rejected(item, "Portfolio cannot introduce external tenant");
item = display();
item.organizations[1].organizationId = "llc_a";
rejected(item, "Duplicate organization");
item = display();
item.organizations[0].scopeGrants[0].expiresAt = 1_799_999_999;
rejected(item, "Expired scope preview");
item = display();
item.organizations[0].scopeGrants[0].action = "records.delete";
rejected(item, "Unknown privilege");
item = display();
item.organizations[0].kind = "admin";
rejected(item, "Unknown org kind");
item = display();
item.organizations = [];
rejected(item, "READY with zero memberships");
item = display();
item.status = "SIGNED_OUT";
rejected(item, "Signed-out response with stale memberships");
item = display();
item.organizations[0].scopeGrants[0].accessToken = "secret";
rejected(item, "Extra grant field");

for (const status of ["SIGNED_OUT", "NOT_CONNECTED", "UNAVAILABLE", "NO_MEMBERSHIPS"]) {
    const empty = {
        schema: sandbox.displaySchema, status,
        organizations: [], portfolios: [], canSwitchOrganization: false,
    };
    assert.equal(accepted(empty), true, status + " empty view rejected");
    sandbox.receive(JSON.stringify(empty));
    assert.equal(sandbox.snapshot.status, status);
}
sandbox.receive(JSON.stringify(display()));
assert.equal(sandbox.snapshot.status, "READY");
sandbox.receive("{not valid json");
assert.equal(sandbox.snapshot, null, "Malformed output retained old data");
sandbox.receive(JSON.stringify(display()));
sandbox.active = false;
sandbox.receive(JSON.stringify(display()));
assert.equal(sandbox.snapshot, null, "Late response after close retained data");
sandbox.active = true;
sandbox.receive(JSON.stringify(display()));
sandbox.snapshotProcess.running = false;
sandbox.refresh();
assert.equal(sandbox.snapshot, null, "Refresh must clear stale snapshot first");
assert.equal(sandbox.snapshotProcess.running, true);
assert.equal(sandbox.snapshotProcess.command.join(" "), [
    "/usr/bin/python3",
    "/fake-code/identity_display_reader_cli_v0.py",
    "--json",
].join(" "));
assert.ok(reader.includes("interval: 5000"));
assert.ok(reader.includes("running: reader.active"));
assert.ok(reader.includes("if (!active)"));
assert.ok(!reader.includes("console.log("));
assert.ok(!reader.includes("Qt.openUrlExternally"));
assert.ok(!reader.includes("accessToken"));
assert.ok(!reader.includes("refreshToken"));
assert.ok(!reader.includes("Bearer "));
assert.ok(sections.includes('active: sections.settingsOpen'));
assert.ok(sections.includes('&& sections.activeSection === "ORGANIZATIONS"'));
assert.ok(sections.includes("sections.organizationDisplaySnapshot = snapshot"));
assert.ok(selector.includes("settingsOpen: appSelector.settingsOpen"));
assert.ok(sections.includes('interactive: false'));

console.log("PASS: real QML JS display schema/lifecycle contracts and fixed reader only");
