// Company Network M3 UI/authority source contracts, no QML runtime required.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname,"../..");
const src = p => fs.readFileSync(path.join(root,p),"utf8");

test("non-personal owner-local hub store has a single Python writer",()=>{
    const adapter=src("services/company/CompanyHubStore.qml");
    assert.match(adapter,/post-apollo\.company-hubs\.local\.v1/);
    assert.match(adapter,/CompanyHubDirectory\.py/);
    assert.match(adapter,/function createHub/);
    assert.match(adapter,/function archiveHub/);
    assert.match(adapter,/expectedRevision:saved\.revision/);
    assert.match(adapter,/onExited: function\(code\)/);
    assert.match(adapter,/savedSuccessfully/);
    assert.doesNotMatch(adapter,/SocialIdentityStore|SocialOrganizationDirectoryStore/);
});

test("map placement and selectable reported hub pins are explicitly not coverage",()=>{
    const pane=src("widgets/CompanyCoveragePane.qml");
    assert.match(pane,/import "\.\.\/services\/company"/);
    assert.match(pane,/CompanyHubStore \{/);
    assert.match(pane,/CompanyHubEditor \{/);
    assert.match(pane,/labelText: root\.hubPlacementArmed \? "PICK MAP" : "\+ HUB"/);
    assert.match(pane,/Geo\.unproject\(/);
    assert.match(pane,/root\.openHubEditor\(/);
    assert.match(pane,/ctx\.strokeStyle=chosenHub\?"#C74EC7":"#ED981A"/);
    assert.match(pane,/root\.hubRows\.filter/);
    assert.match(pane,/onSaveRequested: function\(hub\)/);
    assert.match(pane,/NO COMPANY COVERAGE VERIFIED/);
    assert.doesNotMatch(pane,/Process\s*\{|FileView\s*\{/);
});

test("editor does not request people records or account credentials",()=>{
    const editor=src("widgets/CompanyHubEditor.qml");
    for(const field of ["label","organizationLabel","city","regionCode",
        "countryCode","longitude","latitude","serviceFamily"])
        assert.match(editor,new RegExp(field));
    assert.match(editor,/onTriggered: editor\.save\(\)/);
    assert.match(editor,/Do not enter client or employee details/);
    assert.doesNotMatch(editor,/clientName|employeeId|apiToken|password/);
});

test("M3 preserves existing dock and avoids other workers' window/icon edits",()=>{
    const shell=src("shell.qml");
    assert.ok(shell.indexOf("id: companyNetworkHost")>=0);
    assert.ok(shell.indexOf("id: companyNetworkHost")<shell.indexOf("id: tasksHost"));
    const widget=src("widgets/CompanyNetworkW.qml");
    assert.match(widget,/CompanyCoveragePane/);
});
