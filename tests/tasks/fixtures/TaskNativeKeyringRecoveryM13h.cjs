#!/usr/bin/env node
"use strict";
/*
 * TASKS M13h // EXPLICIT MANUAL DISPOSABLE FEDORA TEST.
 * Uses the running session Secret Service only after the operator invokes
 * --native-disposable-test. Creates exactly one random-attribute test item,
 * and one synthetic encrypted file in a new private tmpdir. Reopens from a
 * new Node process, then clears only the test item and removes the temp file.
 * No production draft paths, real task contents, app credentials, keyring
 * enumeration, global keyring unlock, backup modification or daemon launch.
 * This tests a live keyring roundtrip, NOT authenticated per-app unlock.
 */
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const cp=require('node:child_process');
const crypto=require('node:crypto');
const {constants:C}=fs;
const encrypted=require('./TaskEncryptedRecoveryM13f.cjs');
const SERVICE='post-apollo-tasks-m13h-disposable-test';
const LABEL='Post-Apollo M13h disposable synthetic test key';
const CONTEXT={installationId:'M13hNativeTest001',stageId:'m13a-M13hOldSession001-7-1',epoch:8,surface:'HUB'};
const FAKE={kind:'M13F_FAKE_DRAFT',surface:'HUB',value:{title:'M13H_SYNTHETIC_ONLY',description:'NO_REAL_TASK_DATA'}};
const TOKEN=/^[a-f0-9]{32}$/;
const RUN_TIMEOUT_MS=90000; // Allows the OS keyring to request an unlock.

function secret(args,input) {
    const p=cp.spawnSync('secret-tool',args,{input,encoding:'utf8',timeout:RUN_TIMEOUT_MS,maxBuffer:4096});
    return p.error||p.status!==0?null:p.stdout;
}
function attrs(token) {return ['post-apollo-test',SERVICE,'nonce',token];}
function lookup(token) {
    const raw=secret(['lookup',...attrs(token)]);
    if(typeof raw!=='string')return null;
    const value=raw.trim();
    if(!/^[A-Za-z0-9+/]{43}=$/.test(value))return null;
    const key=Buffer.from(value,'base64');
    if(key.length!==32||key.toString('base64')!==value){key.fill(0);return null;}
    return key;
}
function clear(token) {return secret(['clear',...attrs(token)])!==null;}
function safeRoot(root) {
    if(typeof root!=='string'||!path.basename(root).startsWith('postapollo-m13h-')
      ||path.dirname(root)!==os.tmpdir())return false;
    try {
        const st=fs.lstatSync(root);
        return st.isDirectory()&&!st.isSymbolicLink()&&(st.mode&0o077)===0
            &&(typeof process.getuid!=='function'||st.uid===process.getuid());
    }catch(e){return false;}
}
function safeCiphertext(file) {
    if(path.basename(file)!=='draft.enc'||!safeRoot(path.dirname(file)))return null;
    let fd;
    try {
        fd=fs.openSync(file,C.O_RDONLY|C.O_NOFOLLOW);
        const st=fs.fstatSync(fd);
        if(!st.isFile()||st.nlink!==1||(st.mode&0o077)!==0
           ||(typeof process.getuid==='function'&&st.uid!==process.getuid()))return null;
        return fs.readFileSync(fd,{encoding:'utf8'});
    }catch(e){return null;}
    finally{if(fd!==undefined)fs.closeSync(fd);}
}
function verify(token,file,missing) {
    if(!TOKEN.test(token))return 'REFUSED_INVALID_TEST_ID';
    const raw=safeCiphertext(file);
    if(raw===null)return 'REFUSED_CIPHERTEXT_UNAVAILABLE';
    const locked=encrypted.inspectLocked({envelopeRaw:raw});
    if(!locked.ok||Object.hasOwn(locked,'draft'))return 'REFUSED_LOCKED_PREVIEW';
    const key=lookup(missing?'00000000000000000000000000000000':token);
    if(!key)return 'REFUSED_KEY_UNAVAILABLE';
    try {
        const opened=encrypted.openAfterUnlock({envelopeRaw:raw,identity:CONTEXT,key,unlocked:true});
        return opened.ok && opened.reason==='SYNTHETIC_DECRYPTION_VERIFIED'
            &&opened.draft?.value?.title===FAKE.value.title
            &&opened.draft?.value?.description===FAKE.value.description
            &&opened.persistAuthorized===false &&opened.writeAuthorized===false
            ?'M13H_FRESH_PROCESS_RECOVERY_PASS':'REFUSED_DECRYPTION';
    }finally{key.fill(0);}
}
function child(mode,token,file) {
    const result=cp.spawnSync(process.execPath,[__filename,mode,token,file],{
        encoding:'utf8',timeout:RUN_TIMEOUT_MS+10000,maxBuffer:4096,
        // No secret key is inherited. The child asks the session keyring.
        env:process.env
    });
    if(result.error||result.status!==0||result.stderr!=='')return 'REFUSED_CHILD_PROCESS';
    return result.stdout.trim();
}
function preflight() {
    if(process.platform!=='linux'||typeof process.getuid==='function'&&process.getuid()===0)
        return 'REFUSED_NON_USER_LINUX_SESSION_REQUIRED';
    if(typeof process.env.DBUS_SESSION_BUS_ADDRESS!=='string'||!process.env.DBUS_SESSION_BUS_ADDRESS)
        return 'REFUSED_SESSION_BUS_UNAVAILABLE';
    const owner=cp.spawnSync('gdbus',['call','--session',
       '--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus',
       '--method','org.freedesktop.DBus.NameHasOwner','org.freedesktop.secrets'],
       {encoding:'utf8',timeout:4000,maxBuffer:512});
    if(owner.error||owner.status!==0||!/\(\s*true\s*,?\s*\)/.test(owner.stdout))
        return 'REFUSED_SECRET_SERVICE_NOT_RUNNING';
    return null;
}
function run() {
    const gate=preflight();
    if(gate)return gate;
    const token=crypto.randomBytes(16).toString('hex');
    const key=crypto.randomBytes(32);
    let root=null,file=null,mayExist=false,itemCleaned=true,fileCleaned=true;
    try {
        root=fs.mkdtempSync(path.join(os.tmpdir(),'postapollo-m13h-'));
        if(!safeRoot(root))return 'REFUSED_TEMP_DIRECTORY';
        file=path.join(root,'draft.enc');
        // Unique random selectors ensure no pre-existing item is touched.
        const preexisting=lookup(token);
        if(preexisting){preexisting.fill(0);return 'REFUSED_TEST_ID_COLLISION';}
        mayExist=true; // Includes ambiguous store timeout after remote write.
        const stored=secret(['store','--label='+LABEL,...attrs(token)],key.toString('base64')+'\n');
        if(stored===null)return 'REFUSED_KEYRING_STORE';
        const recovered=lookup(token);
        if(!recovered)return 'REFUSED_KEYRING_LOOKUP';
        const matched=crypto.timingSafeEqual(key,recovered);
        recovered.fill(0);
        if(!matched)return 'REFUSED_KEYRING_READBACK_MISMATCH';
        const sealed=encrypted.seal({identity:CONTEXT,key,draft:FAKE,optedIn:true});
        if(!sealed.ok||sealed.persistAuthorized!==false)return 'REFUSED_ENCRYPTION';
        if(sealed.envelopeRaw.includes(FAKE.value.title)||sealed.envelopeRaw.includes(FAKE.value.description))
            return 'REFUSED_PLAINTEXT_PRESENT';
        const fd=fs.openSync(file,C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,0o600);
        try{fs.writeFileSync(fd,sealed.envelopeRaw,'utf8');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
        const dirfd=fs.openSync(root,C.O_RDONLY|C.O_DIRECTORY);
        try{fs.fsyncSync(dirfd);}finally{fs.closeSync(dirfd);}
        if(child('--child-verify',token,file)!=='M13H_FRESH_PROCESS_RECOVERY_PASS')
            return 'REFUSED_FRESH_PROCESS_RECOVERY';
        if(child('--child-missing-key',token,file)!=='REFUSED_KEY_UNAVAILABLE')
            return 'REFUSED_MISSING_KEY_GATE';
        return 'M13H_NATIVE_ENCRYPTED_RESTART_PASS';
    }catch(e){return 'REFUSED_NATIVE_TEST_EXCEPTION';}
    finally{
        key.fill(0);
        if(mayExist) {
            itemCleaned=clear(token);
            const remaining=lookup(token);
            if(remaining){remaining.fill(0);itemCleaned=false;}
        }
        if(root&&safeRoot(root)){
            if(file){try{fs.unlinkSync(file);}catch(e){if(e.code!=='ENOENT')fileCleaned=false;}}
            try{fs.rmdirSync(root);}catch(e){fileCleaned=false;}
        }else if(root){fileCleaned=false;}
        if(!itemCleaned||!fileCleaned){
            if(!itemCleaned)process.stderr.write('M13H_TEST_KEY_CLEANUP_UNVERIFIED id='+token+'\n');
            if(!fileCleaned)process.stderr.write('M13H_TEST_FILE_CLEANUP_UNVERIFIED\n');
            // Crypto success plus leaked test material is not a PASS.
            return 'REFUSED_TEST_CLEANUP_UNVERIFIED';
        }
    }
}
const mode=process.argv[2];
if(mode==='--native-disposable-test'){
    const outcome=run();
    process.stdout.write(outcome+'\n');
    if(!outcome.startsWith('M13H_NATIVE_ENCRYPTED_RESTART_PASS'))process.exitCode=1;
}else if((mode==='--child-verify'||mode==='--child-missing-key')&&process.argv.length===5){
    // Child entry points are read-only and never create/remove keys.
    const gate=preflight();
    const outcome=gate||verify(process.argv[3],process.argv[4],mode==='--child-missing-key');
    process.stdout.write(outcome+'\n');
}else{
    process.stdout.write('M13H_MANUAL_DISPOSABLE_TEST_ONLY\n');
}
