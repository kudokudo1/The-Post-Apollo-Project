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
    assert.match(widget,/glowVisible: false/);
    assert.match(widget,/color: root\.prismBorderColor/);
    assert.match(widget,/border\.color: root\.prismBorderColor/);
    assert.doesNotMatch(widget,/borderColor: Colors\.cyan/);
});

test("header preserves the requested right-to-left single-row control order",()=>{
    const header=widget.slice(widget.indexOf("id: prismHeader"),widget.indexOf("id: prismDivider"));
    assert.match(header,/height: 40/);
    assert.match(header,/layoutDirection: Qt.RightToLeft/);
    const ids=["closePrismButton","prismReloadButton","prismSourceIndicator","prismIndexButton","expandPrismButton","collapsePrismButton"];
    let last=-1;
    for(const id of ids) {
        const at=header.indexOf("id: "+id);
        assert.ok(at>last,id+" follows the preceding right-to-left control");
        last=at;
    }
    assert.match(header,/Math.min\(94,/);
    assert.match(header,/text: "COLOR \/\/ SYNTAGMA"/);
    for(const frameWidth of [260,300,349,432,560,760]) {
        const control=Math.max(16,Math.min(28,Math.floor((frameWidth-100)/6)));
        const badge=Math.max(0,Math.min(94,frameWidth-5*control-15-45));
        assert.ok(5*control+badge+15<=frameWidth-45);
    }
});

test("structural glows reuse the Prism button spectrum",()=>{
    const halo=file("components/PrismBorderGlow.qml");
    assert.match(halo,/Artwork\.prismGeometry\(\)/);
    assert.match(halo,/recipe\.spectrumStops/);
    assert.match(halo,/recipe\.spectrumIndices/);
    assert.match(halo,/Colors.orange, Colors.yellow, Colors.green, Colors.cyan/);
    assert.match(halo,/Colors.blue, Colors.purple, Colors.magenta/);
    assert.match(halo,/c\.createLinearGradient\(p,p\+h,p\+2\/w\/norm,p\+h-2\/h\/norm\)/);
    assert.match(halo,/c\.strokeRect/);
    assert.doesNotMatch(halo,/ctx\.putImageData\(/);
    assert.match(widget,/borderVisible: false/);
    assert.match(widget,/border\.width: 1/);
    assert.equal((widget.match(/PrismBorderGlow\s*\{/g)||[]).length,5);
    assert.equal((widget.match(/divider: true/g)||[]).length,2);
    assert.match(file("components/qmldir"),/PrismBorderGlow 1.0 PrismBorderGlow.qml/);
});

test("ordinary buttons keep their own glow rules; only structure and text use Prism",()=>{
    const header=widget.slice(widget.indexOf("id: prismHeader"),widget.indexOf("id: prismDivider"));
    assert.doesNotMatch(header,/(?:softGlowEnabled|wideGlowEnabled|perimeterGlowEnabled)\s*:/);
    assert.equal((header.match(/PrismBorderGlow\s*\{/g)||[]).length,1);
    const badge=header.slice(header.indexOf("id: prismSourceIndicator"),header.indexOf("DiagnosticsDockButton {"));
    assert.match(badge,/border.width: 1/);
    assert.match(badge,/border.color: Colors.white/);
    assert.match(badge,/PrismBorderGlow \{ anchors.fill: parent \}/);
    assert.match(header,/PrismTextGlow \{ labelItem: prismTitleText \}/);
    assert.match(badge,/PrismTextGlow \{ labelItem: prismSourceText/);
    const glow=file("components/PrismTextGlow.qml");
    assert.match(glow,/Artwork\.prismGeometry\(\)/);
    assert.match(glow,/recipe\.spectrumStops/);
    assert.match(glow,/c\.strokeText\(text,x,y\)/);
    assert.match(glow,/metrics\.elidedText/);
    assert.doesNotMatch(glow,/\b(?:Timer|Process|ShaderEffectSource)\s*\{/);
    assert.match(file("components/qmldir"),/PrismTextGlow 1.0 PrismTextGlow.qml/);
});

test("Prism grows upward from Trash's shared bottom baseline",()=>{
    assert.match(widget,/frameBottomClearance: Math\.max\(0, fullHeightReserve - chassisTopY\)/);
    assert.match(widget,/top: false\s+bottom: true/);
    assert.match(widget,/bottom: Math\.max\(0, root\.frameBottomClearance - root\.bottomScreenGap\)/);
    assert.match(widget,/height: root\.frameHeight/);
    assert.match(shell,/chassisTopY: 80/);
    const reserve=165, top=80, bottom=reserve-top;
    assert.equal(bottom,85);
    for(const screenHeight of [900,1080,1440,2000])
        for(const targetHeight of [790,1020,1345]) {
            const h=Math.min(targetHeight,screenHeight-reserve);
            assert.ok(screenHeight-bottom-h>=top);
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

test("Prism starts with standard SYNTAGMA and ATLAS top navigation",()=>{
    assert.match(widget,/property string helpPage: "syntagma"/);
    assert.match(widget,/\{ id: "syntagma", label: "SYNTAGMA" \},\s*\{ id: "atlas", label: "ATLAS" \}/);
    const nav=widget.slice(widget.indexOf("id: prismMainModes"),widget.indexOf("id: prismBody"));
    assert.match(nav,/ModeButton\s*\{/);
    assert.match(nav,/model: root\.helpModes/);
    assert.match(nav,/selected: !root\.indexOpen && root\.helpPage === modelData\.id/);
    assert.match(nav,/onTriggered: root\.selectHelpPage\(modelData\.id\)/);
    assert.match(widget,/helpPage = page;\s*indexOpen = false;/);
    assert.match(widget,/PrismHelpContent\s*\{/);
    const help=file("widgets/PrismHelpContent.qml");
    assert.match(help,/help\.page === "syntagma"/);
    assert.match(help,/help\.page === "atlas"/);
    assert.match(help,/NO DEFINITIONS YET/);
    assert.match(help,/help\.atlasZones\.slice\(0, 3\)/);
    assert.match(help,/help\.atlasZones\.slice\(3, 6\)/);
    assert.doesNotMatch(help,/\b(?:Process|FileView|PanelWindow|MouseArea|Timer)\s*\{/);
});
test("Atlas maps mounted shell groups in their actual order, not Prism installation status",()=>{
    const atlas=vm.createContext({});
    vm.runInContext(file("services/prism/PrismAtlas.js").replace(/^\s*\.pragma library\s*/,""),atlas);
    const zones=atlas.mapZones();
    assert.deepEqual(Array.from(zones,z=>z.id),["top-left","top-center","top-right","bottom-left","bottom-center","bottom-right"]);
    const bounds=[
        ["// ===== LEFT MODULES","// ===== CENTER MODULE"],
        ["// ===== CENTER MODULE","// ===== RIGHT MODULES"],
        ["// ===== RIGHT MODULES","// ===== BOTTOM-CENTER SYSTEM TRAY"],
        ["// ===== BOTTOM UTILITIES","// ===== POWER"],
        ["// ===== BOTTOM-CENTER SYSTEM TRAY","// ===== BOTTOM UTILITIES"],
        ["// ===== POWER",null]
    ];
    const seen=new Set();
    for(let i=0;i<zones.length;i++){
        const [start,end]=bounds[i];
        const from=shell.indexOf(start),to=end?shell.indexOf(end):shell.length;
        assert.ok(from>=0&&to>from,zones[i].id);
        const group=shell.slice(from,to);
        let last=-1;
        for(const entry of zones[i].entries){
            const pos=group.search(new RegExp("\\b"+entry.mount+"\\s*\\{"));
            assert.ok(pos>last,entry.mount+" is mounted in source order");
            assert.ok(!seen.has(entry.mount),entry.mount+" is unique");
            seen.add(entry.mount);
            last=pos;
        }
    }
    assert.equal(seen.size,23);
    const copy=atlas.mapZones();
    copy[0].entries[0].name="EDIT";
    assert.equal(atlas.mapZones()[0].entries[0].name,"APP CONTROL");
    assert.equal(context.registered().length,1,"Atlas does not fabricate Prism registrations");
});
