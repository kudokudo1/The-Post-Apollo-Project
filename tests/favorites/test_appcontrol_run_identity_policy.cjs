"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const host = fs.readFileSync(path.join(root, "widgets/AppControlW.qml"), "utf8");
const source = fs.readFileSync(path.join(root,
    "services/favorites/FavoritesAppControlRunIdentityPolicy.js"), "utf8");
const policy = {};
vm.runInNewContext(source.replace(/^\.pragma library\s*$/m,""),policy);

function donorFunction(name) {
    const found = new RegExp("(^|\\n)[ \\t]*function\\s+" + name
        + "\\s*\\(").exec(host);
    assert.ok(found,"missing donor " + name);
    const start = host.indexOf("function",found.index);
    const open = host.indexOf("{",start);
    let depth=0;
    for(let i=open;i<host.length;i++) {
        if(host[i]==="{")depth++;
        else if(host[i]==="}") {
            depth--;
            if(depth===0)return host.slice(start,i+1);
        }
    }
    throw new Error("unbalanced donor " + name);
}
function makeDonor() {
    const warnings = [];
    const f = new Function("logger",[
        "const runPrefixNormal=0,runPrefixKitty=1,runPrefixToolbox=2;",
        "const console={log:function(){logger.push(Array.from(arguments));}};",
        donorFunction("normalizeRunPrefixMode"),
        donorFunction("runFavoriteKey"),
        donorFunction("runFavoriteDataFromKey"),
        donorFunction("runFavoriteCommandFromKey"),
        "return {normalizeRunPrefixMode,runFavoriteKey,runFavoriteDataFromKey,runFavoriteCommandFromKey};"
    ].join("\n"))(warnings);
    return {f,warnings};
}
function plain(value) {return value==null?value:JSON.parse(JSON.stringify(value));}

test("prefix selection preserves donor coercion and fallback",()=>{
    const {f}=makeDonor();
    for(const mode of [undefined,null,"",0,"0",1,"1",2,"2",
        3,-1,NaN,false,true,[],{}, "toolbox", "kitty"]) {
        assert.equal(policy.normalizePrefix(mode),f.normalizeRunPrefixMode(mode));
    }
});

test("exact persisted RUN favorite keys match normal, Kitty and Toolbox modes",()=>{
    const {f}=makeDonor();
    const commands=[
        "",null,undefined," ","ls"," ls ","echo hello world",
        "toolbox:abc","kitty:foo","echo a|b",
        "bash -lc 'printf %s private'","printf 100%","/usr/bin/foo --flag",
        "echo café",42
    ];
    for(const command of commands)
        for(const mode of [0,1,2,99,"2"]) {
            assert.equal(policy.key(command,mode),f.runFavoriteKey(command,mode));
        }
    assert.equal(policy.key("echo hi",0),"run:echo%20hi");
    assert.equal(policy.key("echo hi",1),"run:kitty:echo%20hi");
    assert.equal(policy.key("echo hi",2),"run:toolbox:echo%20hi");
});

test("malformed, empty and legacy RUN keys return exact donor decoded values",()=>{
    const {f}=makeDonor();
    const keys=[
        null,undefined,"",false,7,"mode:3:ls","run:","run:kitty:",
        "run:toolbox:","run:echo%20hello","run:kitty:echo%20hello",
        "run:toolbox:echo%20hello","run:%ZZ","run:kitty:%E0%A4%A",
        "run:toolbox:%ZZ","run:kitty:foo|bar","run:toolbox:foo:bar",
        "run:echo%2Fhi","run:echo%7Cfoo","run:kitty:toolbox:hi",
        "run:toolbox:kitty:hi","run:normal:hi"
    ];
    for(const key of keys) {
        assert.deepEqual(plain(policy.dataFromKey(key)),
            plain(f.runFavoriteDataFromKey(key)));
        assert.equal(policy.commandFromKey(key),f.runFavoriteCommandFromKey(key));
    }
});

test("legacy codec remains private and has no execution or store authority",()=>{
    assert.doesNotMatch(source,/\bQuickshell\b|\bProcess\s*\{|\bexecDetached\s*\(/);
    assert.doesNotMatch(source,/\bFavoritesStore\b\s*\.|\bwriteAdapter\s*\(/);
    assert.doesNotMatch(source,/\blaunchApplication\s*\(|\bexecuteRunCommand\s*\(/);
    const universal=fs.readFileSync(path.join(root,
        "services/favorites/FavoritesUnifiedCatalog.qml"),"utf8");
    const display=fs.readFileSync(path.join(root,
        "services/favorites/FavoritesAppControlDisplayPolicy.js"),"utf8");
    assert.doesNotMatch(universal,/FavoritesAppControlRunIdentityPolicy/);
    assert.doesNotMatch(display,/FavoritesAppControlRunIdentityPolicy/);
    assert.doesNotMatch(source,/\bconsole\.(?:log|warn|error)\s*\(/);
});
