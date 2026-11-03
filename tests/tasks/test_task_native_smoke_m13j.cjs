#!/usr/bin/env node
"use strict";
/* M13j: launcher tested with a synthetic module tree, not user's files.
 * --run launches only a FAKE quickshell executable in CI. */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const cp=require("node:child_process");
const ROOT=path.resolve(__dirname,"../..");
const SCRIPT=path.join(ROOT,"tests/tasks/tools/task_m13j_native_smoke.sh");
const entry="TaskEncryptedRecoveryBridgeM13i 1.0 TaskEncryptedRecoveryBridgeM13i.qml";
function fakeTree(t) {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"postapollo-m13j-ci-"));
    t.after(()=>fs.rmSync(temp,{recursive:true,force:true}));
    const root=path.join(temp,"config"),hub=path.join(root,"services/hub");
    fs.mkdirSync(hub,{recursive:true});
    fs.writeFileSync(path.join(hub,"qmldir"),"module qs.services.hub\n"+entry+"\n");
    for(const name of ["TaskEncryptedRecoveryBridgeM13i.qml","TaskRecoveryProviderHostM13i.py"])
        fs.writeFileSync(path.join(hub,name),"CI_FAKE_ONLY");
    fs.writeFileSync(path.join(root,"TaskEncryptedRecoveryHarnessM13i.qml"),"CI_FAKE_ONLY");
    return {temp,root,hub};
}
function smoke(args,env) {
    return cp.spawnSync("bash",[SCRIPT,...args],{
        encoding:"utf8",timeout:2500,maxBuffer:8192,env:{...process.env,...env}
    });
}
test("preflight reports missing files and never repairs them",t=>{
    const {root,hub}=fakeTree(t);
    const first=smoke(["--preflight",root]);
    assert.equal(first.status,0);
    assert.equal(first.stdout.trim(),"M13J_LOCAL_MODULE_READY");
    fs.unlinkSync(path.join(hub,"TaskEncryptedRecoveryBridgeM13i.qml"));
    const absent=smoke(["--preflight",root]);
    assert.equal(absent.status,2);
    assert.equal(absent.stdout.trim(),"M13J_MISSING_BRIDGE_QML");
    assert.equal(fs.existsSync(path.join(hub,"TaskEncryptedRecoveryBridgeM13i.qml")),false);
});
test("unregistered, duplicated and bad module refuse",t=>{
    const {root,hub}=fakeTree(t);
    for(const body of [
        "module qs.services.hub\n",
        "module qs.services.hub\n"+entry+"\n"+entry+"\n",
        "module qs.services.other\n"+entry+"\n",
    ]){
        fs.writeFileSync(path.join(hub,"qmldir"),body);
        const result=smoke(["--preflight",root]);
        assert.equal(result.status,2);
        assert.match(result.stdout,/M13J_(BRIDGE_UNREGISTERED|INVALID_HUB_MODULE)/);
    }
});
test("invalid modes refuse before loading any files",t=>{
    const {root}=fakeTree(t);
    const result=smoke(["--activate-live",root]);
    assert.equal(result.status,2);
    assert.equal(result.stdout.trim(),"M13J_REFUSED_ARGS");
});
test("run launches only separate test panel using fake quickshell",t=>{
    const {root,temp}=fakeTree(t);
    const bin=path.join(temp,"bin");
    fs.mkdirSync(bin);
    fs.writeFileSync(path.join(bin,"quickshell"),
        "#!/bin/sh\nprintf 'CI_FAKE_LAUNCH %s %s\\n' \"$1\" \"$2\"\n");
    fs.chmodSync(path.join(bin,"quickshell"),0o700);
    const result=smoke(["--run",root],{PATH:bin+":"+process.env.PATH});
    assert.equal(result.status,0,result.stderr);
    assert.equal(result.stdout,
        "M13J_LOCAL_MODULE_READY\nM13J_STARTING_STANDALONE_PANEL\n"
        +"CI_FAKE_LAUNCH -p "+path.join(root,"TaskEncryptedRecoveryHarnessM13i.qml")+"\n");
});
test("source script contains no local git or production process changes",()=>{
    const raw=fs.readFileSync(SCRIPT,"utf8");
    assert.match(raw,/exec "\$shell_binary" -p "\$panel"/);
    assert.match(raw,/^set -euo pipefail$/m);
    assert.doesNotMatch(raw,/\b(?:git|sudo|killall|pkill|systemctl|gnome-keyring-daemon|secret-tool)\s+/);
    assert.doesNotMatch(raw,/\b(?:rm|sed -i|cp|mv|touch|install|chmod|chown|truncate)\s+/);
    assert.doesNotMatch(raw,/quickshell\s+-p\s+.*shell\.qml/);
});
test("existing M13i panel offers only a read-only provider check",()=>{
    const panel=fs.readFileSync(path.join(ROOT,"TaskEncryptedRecoveryHarnessM13i.qml"),"utf8");
    assert.match(panel,/onClicked:\s*bridge\.inspectProvider\(\)/);
    assert.match(panel,/TaskEncryptedRecoveryBridgeM13i\s*\{/);
    assert.doesNotMatch(panel,/secret-tool|FileView\s*\{|\.setText\(|\.write\(/);
    const qmldir=fs.readFileSync(path.join(ROOT,"services/hub/qmldir"),"utf8");
    assert.equal(qmldir.split(/\r?\n/).filter(s=>s===entry).length,1);
});
