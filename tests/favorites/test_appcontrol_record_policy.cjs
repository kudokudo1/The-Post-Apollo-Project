"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const host = fs.readFileSync(path.join(root, "widgets/AppControlW.qml"), "utf8");
const src = fs.readFileSync(path.join(root,
    "services/favorites/FavoritesAppControlRecordPolicy.js"), "utf8");
const policy = {};
vm.runInNewContext(src.replace(/^\.pragma library\s*$/m, ""), policy);

function donorFunction(name) {
    const re = new RegExp("(^|\\n)[ \\t]*function[ \\t]+" + name + "[ \\t]*\\(");
    const m = re.exec(host);
    assert.ok(m, "missing AppControl donor function " + name);
    const start = host.indexOf("function", m.index);
    const opening = host.indexOf("{", start);
    let depth = 0;
    for (let i = opening; i < host.length; i++) {
        if (host[i] === "{") depth++;
        else if (host[i] === "}") {
            depth--;
            if (depth === 0) return host.slice(start, i + 1);
        }
    }
    throw Error("unbalanced donor function " + name);
}
const appDonor = new Function("favoriteKeyFor", "appControlWindow", [
    "const appsModeIndex=1;",
    donorFunction("favoriteRecordForApp"),
    "return favoriteRecordForApp;"
].join("\n"));
const runDonor = new Function(
    "normalizeRunPrefixMode", "runRecord", "runFavoriteKey",
    "runPrefixName", "runShellName", [
        "const runModeIndex=3;",
        donorFunction("favoriteRecordForRunCommand"),
        "return favoriteRecordForRunCommand;"
    ].join("\n")
);
function plain(obj) { return JSON.parse(JSON.stringify(obj)); }
function noAction(obj) {
    const copy = {...obj};
    delete copy.execute;
    return plain(copy);
}

test("application wrappers exactly match live donor fields and source reference", () => {
    const cases = [
        {key:"org.mozilla.Firefox.desktop",id:"firefox",name:"Firefox",
         genericName:"Web Browser",comment:"Browse",keywords:"web;internet;",
         icon:"firefox",actions:[{id:"private"}],command:["firefox"],
         startupClass:"firefox"},
        {key:"app:missing",name:""},
        {key:"app:toolbox",id:0,comment:0,keywords:[],actions:[]},
        {key:"app:%2Funicode",name:"文書",command:["/bin/test","--private"]}
    ];
    for (const entry of cases) {
        const fired = [];
        const owner = {launchApplication:e=>fired.push(e)};
        const donor = appDonor(e=>e.key, owner)(entry);
        const shared = policy.appRecord(entry,entry.key,1,owner.launchApplication);
        assert.deepEqual(noAction(shared),noAction(donor));
        assert.strictEqual(shared._sourceItem,entry);
        assert.equal(fired.length,0,"wrapping must never launch an application");
        donor.execute();
        shared.execute();
        assert.deepEqual(fired,[entry,entry],"only owner callback may launch");
    }
});

test("RUN wrappers retain donor source, resolved prefix and privacy-bearing text", () => {
    const normalized = x=>(x===1||x===2)?x:0;
    const source = (command,origin,prefix)=>({
        label:"RUN "+command,name:command,commandText:command,
        genericName:"RUN "+origin,origin,prefix,args:"--private"
    });
    const key = (command,prefix)=>"run:"+prefix+":"+encodeURIComponent(command);
    const prefixName = mode=>["NORMAL","KITTY","TOOLBOX"][mode];
    const shellName = ()=>"Bash";
    const donor = runDonor(normalized,source,key,prefixName,shellName);
    for(const [command,prefix] of [
        ["ls -l",0],["echo two words",1],
        ["toolbox run --container alpha",2],["printf '%s' private",9]
    ]) {
        const mode=normalized(prefix), row=source(command,"FAVORITE",mode);
        const actual=policy.runRecord(row,key(command,mode),mode,3,
            prefixName(mode),shellName());
        const expected=donor(command,prefix);
        assert.deepEqual(noAction(actual),noAction(expected));
        assert.strictEqual(actual._sourceItem,row);
        assert.equal(actual.commandText,command);
    }
});

test("local wrappers neither perform commands nor write Favorites storage", () => {
    assert.doesNotMatch(src,/\bQuickshell\b|\bProcess\s*\{|\bexecDetached\s*\(/);
    assert.doesNotMatch(src,/favoriteStore\.|FavoritesService\.|writeAdapter\s*\(/);
    assert.doesNotMatch(src,/\bkill\s*\(|\bspawn\s*\(|\bxdg-open\b/);
    const catalog=fs.readFileSync(path.join(root,
        "services/favorites/FavoritesUnifiedCatalog.qml"),"utf8");
    const management=fs.readFileSync(path.join(root,
        "services/favorites/FavoritesManagementPolicy.js"),"utf8");
    assert.doesNotMatch(catalog,/FavoritesAppControlRecordPolicy|_sourceItem\.commandText/);
    assert.doesNotMatch(management,/FavoritesAppControlRecordPolicy|_sourceItem\.commandText/);
});
