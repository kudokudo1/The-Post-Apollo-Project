#!/usr/bin/env node
"use strict";
/*
 * TASKS M13k // synthetic encrypted draft host protocol. NOT PRODUCTION.
 *
 * A Quickshell Process can send ONE fixed CI-only JSON request on stdin.
 * Under a throwaway private HOME and private D-Bus/Secret Service session,
 * the host delegates to the already-tested M13g fixture in two independent
 * Node child processes. The only reply is a fixed, status-only JSON envelope.
 *
 * No user draft content, keys, filenames, keyring passwords, task mutations,
 * or native activation authority cross this IPC. All permissions remain false.
 * In the operator's regular session this process MUST refuse without starting
 * secret-tool or creating any files.
 */
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const cp=require("node:child_process");
const readline=require("node:readline");

const NAME="post-apollo-m13g-ci";
const ID="M13gSynthetic001";
const MARKER="postapollo-m13g-m13k-";
const FIXTURE=path.join(__dirname,"TaskSecretServiceRoundTripM13g.cjs");
const DENIED=[
    "productionActivation","sourceTrusted","persistAuthorized",
    "writeAuthorized","restoreAuthorized","replayAuthorized",
    "deleteAuthorized","keyReleaseAuthorized"
];
function response(status,verified=false) {
    const out={protocol:1,kind:"M13K_SYNTHETIC_HOST",status,
        syntheticRoundTripVerified:verified};
    for(const name of DENIED)out[name]=false;
    return out;
}
function exact(x,keys) {
    return x && typeof x==="object" && !Array.isArray(x)
        &&Object.keys(x).sort().join(",")===keys.slice().sort().join(",");
}
function safeDir(p) {
    try {
        const s=fs.lstatSync(p);
        return s.isDirectory()&&!s.isSymbolicLink()
            &&(s.mode&0o077)===0
            &&(typeof process.getuid!=="function"||s.uid===process.getuid());
    }catch(e){return false;}
}
function isolatedRoot(){
    const home=process.env.HOME;
    if(process.platform!=="linux" ||
        (typeof process.getuid==="function"&&process.getuid()===0) ||
        process.env.POST_APOLLO_M13K_ISOLATED!=="1" ||
        process.env.POST_APOLLO_M13G_DISPOSABLE!=="1" ||
        typeof home!=="string" ||
        path.dirname(home)!==os.tmpdir() ||
        !path.basename(home).startsWith(MARKER) ||
        typeof process.env.DBUS_SESSION_BUS_ADDRESS!=="string" ||
        !/^unix:path=\/tmp\/dbus-[A-Za-z0-9_-]+(?:,.*)?$/.test(process.env.DBUS_SESSION_BUS_ADDRESS) ||
        process.env.XDG_DATA_HOME!==path.join(home,".local/share") ||
        process.env.XDG_CONFIG_HOME!==path.join(home,".config") ||
        process.env.XDG_CACHE_HOME!==path.join(home,".cache") ||
        !safeDir(home))
        return null;
    const root=path.join(home,"m13g-disposable");
    return safeDir(root)?root:null;
}
function run(cmd,args,input) {
    const r=cp.spawnSync(cmd,args,{
        encoding:"utf8",input,timeout:12000,maxBuffer:1024,
        stdio:[input===undefined?"ignore":"pipe","pipe","pipe"]
    });
    return r.error||r.status!==0||r.stderr!==""?null:r.stdout.trim();
}
function keyExists() {
    const r=run("secret-tool",["lookup","service",NAME,"id",ID]);
    return r!==null && r.length>0;
}
function validFile(file) {
    let fd;
    try {
        fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
        const s=fs.fstatSync(fd);
        return s.isFile()&&s.nlink===1&&(s.mode&0o077)===0
            &&(typeof process.getuid!=="function"||s.uid===process.getuid());
    }catch(e){return false;}
    finally{if(fd!==undefined)fs.closeSync(fd);}
}
function perform(root) {
    const file=path.join(root,"draft.enc");
    let mayHaveKey=false;
    let result="REFUSED_SYNTHETIC_HOST";
    let keyClean=true,fileClean=true;
    try {
        if(fs.existsSync(file)||keyExists()) {
            result="REFUSED_SYNTHETIC_SOURCE_ALREADY_PRESENT";
        }else{
            mayHaveKey=true;
            const created=run(process.execPath,[FIXTURE,"create"]);
            if(created!=="SYNTHETIC_SECRET_STORED_AND_ENCRYPTED"){
                result="REFUSED_SYNTHETIC_ENCRYPT";
            }else if(!validFile(file)){
                result="REFUSED_SYNTHETIC_CIPHERTEXT";
            }else if(run(process.execPath,[FIXTURE,"reopen"])
                    !=="SYNTHETIC_SECRET_SERVICE_RESTART_PASS"){
                result="REFUSED_SYNTHETIC_REOPEN";
            }else if(run(process.execPath,[FIXTURE,"reopen-missing-key"])
                    !=="REFUSED_KEY_NOT_AVAILABLE"){
                result="REFUSED_SYNTHETIC_MISSING_KEY";
            }else{
                result="M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS";
            }
        }
    }catch(e){
        result="REFUSED_SYNTHETIC_EXCEPTION";
    }finally{
        if(mayHaveKey){
            const clear=run("secret-tool",["clear","service",NAME,"id",ID]);
            keyClean=clear!==null && !keyExists();
        }
        if(fs.existsSync(file)){
            if(validFile(file)){
                try {fs.unlinkSync(file);}catch(e){fileClean=false;}
            }else fileClean=false;
        }
        if(!keyClean||!fileClean){
            // No path or label leak; a failed cleanup MUST invalidate PASS.
            result="REFUSED_SYNTHETIC_CLEANUP_UNVERIFIED";
        }
    }
    return result;
}
function executeRequest(line) {
    if(typeof line!=="string"||Buffer.byteLength(line,"utf8")>256)
        return response("REFUSED_REQUEST_SHAPE");
    let request;
    try{request=JSON.parse(line);}catch(e){return response("REFUSED_REQUEST_SHAPE");}
    if(!exact(request,["protocol","kind","consent"])
        ||request.protocol!==1
        ||request.kind!=="RUN_SYNTHETIC_DRAFT"
        ||request.consent!=="CI_ONLY")
        return response("REFUSED_REQUEST_SHAPE");
    const root=isolatedRoot();
    if(!root)return response("REFUSED_NOT_DISPOSABLE_SESSION");
    const status=perform(root);
    return response(status,status==="M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS");
}
function emit(out) {
    process.stdout.write(JSON.stringify(out)+"\n");
}
if(process.argv.length!==3||process.argv[2]!=="--single-request"){
    emit(response("REFUSED_EXPLICIT_MODE_REQUIRED"));
}else if(!isolatedRoot()){
    emit(response("REFUSED_NOT_DISPOSABLE_SESSION"));
}else{
    // The Process/QML side must supply exactly one fixed request on stdin.
    const lines=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
    let handled=false;
    const alarm=setTimeout(()=>{
        if(!handled){handled=true;emit(response("REFUSED_REQUEST_TIMEOUT"));}
        lines.close();
    },6000);
    lines.on("line",line=>{
        if(handled)return;
        handled=true;clearTimeout(alarm);emit(executeRequest(line));
        lines.close();
    });
    lines.on("close",()=>{
        clearTimeout(alarm);
        if(!handled)emit(response("REFUSED_NO_REQUEST"));
    });
}
