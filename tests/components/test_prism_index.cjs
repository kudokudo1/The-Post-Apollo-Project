const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const repo=path.resolve(__dirname,"../..");
const file=p=>fs.readFileSync(path.join(repo,p),"utf8");
const widget=file("widgets/PrismW.qml");
const dock=file("modules/PrismDock.qml");
const shell=file("shell.qml");
const registrySource=file("services/prism/PrismIndex.js");
const context=vm.createContext({});
vm.runInContext(registrySource.replace(/^\s*\.pragma library\s*/,""),context);

test("widget color identity is directly bound to Prism's real fixed border",()=>{
    const button=file("components/PrismButton.qml");
    assert.match(button,/idleBorderColor: Colors\.white/);
    assert.match(button,/hoverBorderColor: Colors\.white/);
    assert.match(button,/idleBorderWidth: 1/);
    assert.match(dock,/readonly property color prismBorderColor: prismButton\.idleBorderColor/);
    assert.match(shell,/prismBorderColor: prismDock\.prismBorderColor/);
    assert.match(widget,/property color prismBorderColor: Colors\.white/);
    assert.match(widget,/borderColor: root\.prismBorderColor/);
    assert.match(widget,/glowColor: root\.prismBorderColor/);
    assert.match(widget,/color: root\.prismBorderColor/);
    assert.match(widget,/border\.color: root\.prismBorderColor/);
    assert.doesNotMatch(widget,/borderColor: Colors\.cyan/);
});

test("header is an accessible two-row family, not a squeezed narrow strip",()=>{
    assert.match(widget,/id: prismHeader/);
    assert.match(widget,/height: 84/);
    assert.match(widget,/id: prismToolbar/);
    assert.match(widget,/id: prismSourceIndicator/);
    assert.match(widget,/text: "COLOR \/\/ SYNTAGMA"/);
    assert.doesNotMatch(widget,/text: "●.*SYNTAGMA"/);
    assert.match(widget,/ResizeButton\s*\{/);
    assert.match(widget,/CloseButton\s*\{/);
    // All the controls have a bounded slot at both 432px and a 300px frame.
    for(const frameWidth of [300,349,432,560,760]) {
        const rowWidth=frameWidth-24;
        const spacing=5, fixed=28+28+30+38, gaps=spacing*5;
        const badge=Math.max(0,Math.min(126,rowWidth-fixed-gaps));
        const spacer=Math.max(0,rowWidth-fixed-badge-gaps);
        assert.ok(fixed+badge+spacer+gaps<=rowWidth);
    }
});

test("reload is a visible disabled shared control with no fake refresh",()=>{
    const reload=widget.match(/ReloadButton\s*\{([\s\S]*?)\n\s*\}/);
    assert.ok(reload,"standard ReloadButton exists");
    assert.match(reload[1],/objectName: "prismReloadButton"/);
    assert.match(reload[1],/available: false/);
    assert.match(reload[1],/Reload Prism index not yet available/);
    assert.doesNotMatch(widget,/onReloadRequested\s*:/);
    assert.doesNotMatch(widget,/\b(?:Process|FileView|Http|Timer)\s*\{/);
});

test("diagnostics button opens and closes an actual index within this widget",()=>{
    assert.match(widget,/DiagnosticsDockButton\s*\{/);
    assert.match(widget,/diagnosticsOpen: root\.indexOpen/);
    assert.match(widget,/onToggleRequested: root\.indexOpen = !root\.indexOpen/);
    assert.match(widget,/objectName: "prismPlacementIndex"/);
    assert.match(widget,/visible: root\.indexOpen/);
    assert.match(widget,/onMenuOpenChanged: if \(!menuOpen\) indexOpen = false/);
    assert.match(widget,/model: root\.registeredLocations/);
    assert.match(widget,/text: modelData\.name/);
    assert.match(widget,/text: modelData\.location/);
    assert.match(widget,/text: modelData\.definitions/);
});

test("placement index includes exactly the currently installed Prism context",()=>{
    assert.match(widget,/import "\.\.\/services\/prism\/PrismIndex\.js" as PrismIndex/);
    assert.match(widget,/PrismIndex\.registered\(\)/);
    const entries=context.registered();
    assert.equal(entries.length,1);
    assert.equal(entries[0].id,"post-apollo");
    assert.equal(entries[0].name,"POST APOLLO");
    assert.equal(entries[0].location,"BOTTOM DOCK // BESIDE TRASH");
    assert.equal(entries[0].definitions,0);
    assert.equal(entries[0].source,"modules/PrismDock.qml");
    assert.ok(fs.existsSync(path.join(repo,entries[0].source)));
    assert.match(shell,/PrismDock\s*\{/);
    assert.match(shell,/PrismW\s*\{/);
    const changed=context.registered();
    changed[0].name="NOT THE REGISTERED VALUE";
    assert.equal(context.registered()[0].name,"POST APOLLO");
    assert.doesNotMatch(widget,/\b(?:serviceAvailable|healthReady|isLive|scanRunning)\s*:/);
});
