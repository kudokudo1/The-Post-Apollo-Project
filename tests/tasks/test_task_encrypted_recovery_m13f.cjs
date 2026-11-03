#!/usr/bin/env node
"use strict";
/*
 * M13f // disposable encrypted recovery capability test.
 * Synthetic content only. Test-only fresh child receives ephemeral key via
 * stdin, NEVER command-line args, environment, disk, logs or Git artifact.
 * It does not prove a production key provider, OS secure memory, or actual
 * consent/unlock. Only this test, not the reusable module, creates files.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const crypto=require("node:crypto");
const cp=require("node:child_process");
const {constants:C}=fs;
const ROOT=path.resolve(__dirname,"../..");
const model=require("./fixtures/TaskEncryptedRecoveryM13f.cjs");
const identity=()=>({
    installationId:"M13fFakeInstall001",stageId:"m13a-M13fOldSession001-7-1",
    epoch:8,surface:"HUB"
});
const sample=()=>({kind:"M13F_FAKE_DRAFT",surface:"HUB",
    value:{title:"M13F_FAKE_PRIVATE_TITLE",description:"M13F_SYNTHETIC_CONTENT_ONLY"}});
const key=()=>crypto.randomBytes(32);
function noPower(x) {
    for(const name of Object.keys(model.NO_POWER))
        assert.equal(x[name],false,name);
}
function seal(k=key(),extra={}) {
    return model.seal({identity:identity(),key:k,draft:sample(),
                       optedIn:true,...extra});
}
function scratch() {
    const root=fs.mkdtempSync(path.join(os.tmpdir(),"m13f-crypto-test-"));
    return {root,source:path.join(root,"m13f-disposable-draft.enc"),
        cleanup(){fs.rmSync(root,{recursive:true,force:true});}};
}
function writeExclusive(f,raw) {
    assert.equal(fs.statSync(f.root).mode&0o077,0);
    const fd=fs.openSync(f.source,C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,0o600);
    try {fs.writeFileSync(fd,raw,"utf8");fs.fsyncSync(fd);}
    finally {fs.closeSync(fd);}
    const dirfd=fs.openSync(f.root,C.O_RDONLY|C.O_DIRECTORY);
    try {fs.fsyncSync(dirfd);}finally{fs.closeSync(dirfd);}
}
const childCode=[
    "'use strict';",
    "const fs=require('node:fs');",
    "const C=fs.constants;",
    "const cryptoModel=require(process.argv[1]);",
    "const fd=fs.openSync(process.argv[2],C.O_RDONLY|C.O_NOFOLLOW);",
    "const st=fs.fstatSync(fd);",
    "if(!st.isFile() ||st.nlink!==1 ||(st.mode&0o077)!==0)process.exit(21);",
    "let raw;try{raw=fs.readFileSync(fd,'utf8');}finally{fs.closeSync(fd);}",
    "const input=JSON.parse(fs.readFileSync(0,'utf8'));",
    "const k=input.key?Buffer.from(input.key,'base64'):null;",
    "const result=cryptoModel.openAfterUnlock({envelopeRaw:raw,",
    "  identity:input.identity,key:k,unlocked:input.unlocked});",
    "if(k)k.fill(0);",
    "const ok=result.ok===true&&result.reason==='SYNTHETIC_DECRYPTION_VERIFIED'",
    "  &&result.draft?.value?.title==='M13F_FAKE_PRIVATE_TITLE'",
    "  &&result.draft?.value?.description==='M13F_SYNTHETIC_CONTENT_ONLY'",
    "  &&result.persistAuthorized===false;",
    "process.stdout.write(ok?'SYNTHETIC_UNLOCK_PASS':",
    "  (!result.ok?'SYNTHETIC_UNLOCK_REFUSED':'UNEXPECTED_RESULT'));"
].join("\n");
function freshProcess(f,k,other={}) {
    // Test-only stdin fake key handoff simulates an external unlock service.
    const input={key:k?k.toString("base64"):null,identity:identity(),
        unlocked:true,...other};
    const child=cp.spawnSync(process.execPath,["-e",childCode,
        path.join(__dirname,"fixtures/TaskEncryptedRecoveryM13f.cjs"),
        f.source],{input:JSON.stringify(input),encoding:"utf8",timeout:10000,
            env:{PATH:process.env.PATH||"/usr/bin:/bin"}});
    assert.equal(child.status,0,"fresh child exit; no private output emitted");
    assert.equal(child.stderr,"","no private/error traces");
    return child.stdout;
}
test("disabled opt-in cannot produce bytes, unlocked flag cannot be assumed",()=>{
    const k=key();
    try {
        const blocked=seal(k,{optedIn:false});
        assert.equal(blocked.ok,false);
        assert.equal(blocked.reason,"OPT_IN_REQUIRED");
        assert.equal(Object.hasOwn(blocked,"envelopeRaw"),false);
        noPower(blocked);
        const done=seal(k);
        assert.equal(done.ok,true,done.reason);
        noPower(done);
        const locked=model.openAfterUnlock({envelopeRaw:done.envelopeRaw,
            identity:identity(),key:k,unlocked:false});
        assert.equal(locked.ok,false);
        assert.equal(locked.reason,"SEPARATE_UNLOCK_REQUIRED");
        noPower(locked);
    }finally{k.fill(0);}
});
test("AES-256-GCM ciphertext persists in disposable root and fresh process unlocks",()=>{
    const f=scratch(),k=key();
    try {
        const prepared=seal(k);
        assert.equal(prepared.ok,true,prepared.reason);
        writeExclusive(f,prepared.envelopeRaw);
        const bytes=fs.readFileSync(f.source,"utf8");
        assert.equal(bytes,prepared.envelopeRaw);
        assert.equal(fs.statSync(f.source).mode&0o077,0);
        assert.ok(!bytes.includes("M13F_FAKE_PRIVATE_TITLE"));
        assert.ok(!bytes.includes("M13F_SYNTHETIC_CONTENT_ONLY"));
        assert.ok(!bytes.includes(k.toString("base64")));
        const onlyLocked=model.inspectLocked({envelopeRaw:bytes});
        assert.equal(onlyLocked.ok,true,onlyLocked.reason);
        assert.equal(onlyLocked.locked,true);
        assert.equal(onlyLocked.recoveryAvailable,true);
        assert.equal(Object.hasOwn(onlyLocked,"draft"),false);
        noPower(onlyLocked);
        assert.equal(freshProcess(f,k),"SYNTHETIC_UNLOCK_PASS");
        // No key after simulated restart is explicitly not recoverable.
        assert.equal(freshProcess(f,null),"SYNTHETIC_UNLOCK_REFUSED");
        assert.equal(freshProcess(f,key()),"SYNTHETIC_UNLOCK_REFUSED");
        assert.equal(freshProcess(f,k,{unlocked:false}),"SYNTHETIC_UNLOCK_REFUSED");
    }finally{k.fill(0);f.cleanup();}
});
test("new nonce for every encryption under the same test key",()=>{
    const k=key();
    try {
        const a=JSON.parse(seal(k).envelopeRaw);
        const b=JSON.parse(seal(k).envelopeRaw);
        assert.notEqual(a.nonce,b.nonce);
        assert.notEqual(a.ciphertext,b.ciphertext);
        assert.notEqual(a.tag,b.tag);
        assert.equal(a.cipher,"aes-256-gcm");
        assert.equal(Buffer.from(a.nonce,"base64").length,12);
        assert.equal(Buffer.from(a.tag,"base64").length,16);
    }finally{k.fill(0);}
});
test("change in installation, stage, epoch, surface or key prevents unlock",()=>{
    const k=key(),prepared=seal(k);
    try {
        for(const altered of [
            {installationId:"M13fOtherInstall02"},
            {stageId:"m13a-M13fOtherSession22-7-1"},
            {epoch:9},{surface:"DETAILS"}
        ]) {
            const result=model.openAfterUnlock({
                envelopeRaw:prepared.envelopeRaw,
                identity:{...identity(),...altered},key:k,unlocked:true});
            assert.equal(result.ok,false,JSON.stringify(altered));
            assert.equal(result.reason,"AUTHENTICATION_OR_CONTEXT_MISMATCH");
            assert.equal(Object.hasOwn(result,"draft"),false);
            noPower(result);
        }
        const wrong=model.openAfterUnlock({envelopeRaw:prepared.envelopeRaw,
            identity:identity(),key:key(),unlocked:true});
        assert.equal(wrong.ok,false);
        noPower(wrong);
    }finally{k.fill(0);}
});
test("tampered nonce/tag/ciphertext, malformed format and foreign fields are refused",()=>{
    const k=key(),prepared=seal(k);
    try {
        const base=JSON.parse(prepared.envelopeRaw);
        const cases=[];
        for(const field of ["nonce","tag","ciphertext"]) {
            const v={...base};
            const data=Buffer.from(v[field],"base64");
            data[0]^=1;
            v[field]=data.toString("base64");
            cases.push(v);
        }
        cases.push({...base,format:2});
        cases.push({...base,cipher:"aes-256-cbc"});
        cases.push({...base,extra:"foreign"});
        cases.push({...base,tag:"not-base64!"});
        cases.push({...base,ciphertext:""});
        for(const variant of cases) {
            const result=model.openAfterUnlock({
                envelopeRaw:JSON.stringify(variant),
                identity:identity(),key:k,unlocked:true});
            assert.equal(result.ok,false,JSON.stringify(variant).slice(0,50));
            assert.equal(Object.hasOwn(result,"draft"),false);
            noPower(result);
        }
    }finally{k.fill(0);}
});
test("in-place clobber and second create blocked by exclusive test-only file create",()=>{
    const f=scratch(),k=key();
    try {
        const first=seal(k),second=seal(k);
        writeExclusive(f,first.envelopeRaw);
        assert.throws(()=>writeExclusive(f,second.envelopeRaw),
            e=>e&&e.code==="EEXIST");
        assert.equal(fs.readFileSync(f.source,"utf8"),first.envelopeRaw);
        assert.equal(freshProcess(f,k),"SYNTHETIC_UNLOCK_PASS");
    }finally{k.fill(0);f.cleanup();}
});
test("no real draft, key provider or production writer changes",()=>{
    const fixture=fs.readFileSync(path.join(__dirname,
        "fixtures/TaskEncryptedRecoveryM13f.cjs"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,
        "services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.doesNotMatch(fixture,/\b(?:fs\.|writeFile|openSync|unlinkSync|rmSync|renameSync|spawnSync|setTimeout|FileView|Process\s*\{)/);
    assert.doesNotMatch(store+shell,/TaskEncryptedRecoveryM13f/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const flag of ["ticketProducerEnabled","guardedWriterEnabled",
        "independentlyAuthenticatedTicketReceipt"])
        assert.match(store,new RegExp("readonly property bool "+flag+":\\s*false"));
});
