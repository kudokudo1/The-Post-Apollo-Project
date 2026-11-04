#!/usr/bin/env node
"use strict";
/*
 * TASKS M13n // Actual positive Secret Service fixture invoked with stdin
 * deliberately HELD OPEN by the parent. A shell pipeline that closes input
 * automatically cannot catch the native QML subprocess hang.
 *
 * Only an explicitly private disposable M13k/G bus may run the positive
 * branch. No task content, raw host response or key is printed.
 */
const cp=require("node:child_process");
const path=require("node:path");
const os=require("node:os");
const fs=require("node:fs");
const host=path.join(__dirname,"TaskEncryptedDraftHostM13k.cjs");
const mode=process.argv[2];
const expected=mode==="--held-open-valid"
  ?"M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS"
  :mode==="--held-open-malformed"?"REFUSED_REQUEST_SHAPE":null;
function validEnv() {
  const home=process.env.HOME;
  return process.platform==="linux"
    &&typeof home==="string"
    &&path.dirname(home)===os.tmpdir()
    &&path.basename(home).startsWith("postapollo-m13g-m13k-")
    &&process.env.POST_APOLLO_M13K_ISOLATED==="1"
    &&process.env.POST_APOLLO_M13G_DISPOSABLE==="1"
    &&typeof process.env.DBUS_SESSION_BUS_ADDRESS==="string"
    &&/^unix:path=\/tmp\/dbus-[A-Za-z0-9_-]+(?:,.*)?$/.test(process.env.DBUS_SESSION_BUS_ADDRESS)
    &&fs.existsSync(path.join(home,"m13g-disposable"));
}
if(!expected||!validEnv()){
  process.stdout.write("M13N_REFUSED_PRIVATE_FIXTURE_REQUIRED\n");
  process.exitCode=2;
}else{
  const child=cp.spawn(process.execPath,[host,"--single-request"],{
    cwd:__dirname,env:process.env,stdio:["pipe","pipe","pipe"]
  });
  let output="",errs="",done=false;
  const timer=setTimeout(()=>{
    if(done)return;
    done=true;
    // Time-bound refusal: keep no orphan synthetic keyring child.
    child.kill("SIGKILL");
    process.stdout.write("M13N_REFUSED_HELD_STDIN_TIMEOUT\n");
    process.exitCode=1;
  },60000);
  child.stdout.setEncoding("utf8");
  child.stdout.on("data",chunk=>{
    output+=chunk;
    if(output.length>2048)child.kill("SIGKILL");
  });
  child.stderr.on("data",chunk=>{
    errs+="x";
    if(errs.length>8)child.kill("SIGKILL");
  });
  child.on("error",()=>{errs+="x";});
  child.on("close",code=>{
    clearTimeout(timer);
    if(done)return;
    done=true;
    let v=null;
    try {
      if(output.trim().split("\n").length===1)
        v=JSON.parse(output.trim());
    }catch(e){}
    const allowed=["protocol","kind","status","syntheticRoundTripVerified",
      "productionActivation","sourceTrusted","persistAuthorized",
      "writeAuthorized","restoreAuthorized","replayAuthorized",
      "deleteAuthorized","keyReleaseAuthorized"];
    const exact=v&&typeof v==="object"&&!Array.isArray(v)
      &&Object.keys(v).sort().join(",")===allowed.sort().join(",");
    const verified=expected==="M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS";
    const safe=code===0&&errs.length===0&&exact
      &&v.protocol===1&&v.kind==="M13K_SYNTHETIC_HOST"
      &&v.status===expected
      &&v.syntheticRoundTripVerified===verified
      &&["productionActivation","sourceTrusted","persistAuthorized",
          "writeAuthorized","restoreAuthorized","replayAuthorized",
          "deleteAuthorized","keyReleaseAuthorized"]
          .every(k=>v[k]===false);
    process.stdout.write(safe?(verified
      ?"M13N_HELD_STDIN_ENCRYPTED_CHILD_EXIT_PASS\n"
      :"M13N_HELD_STDIN_MALFORMED_CHILD_EXIT_PASS\n")
      :"M13N_REFUSED_CHILD_EXIT_OR_REPLY\n");
    if(!safe)process.exitCode=1;
  });
  // Model the exact bug: write one request and DO NOT END stdin before exit.
  const request=mode==="--held-open-valid"
    ?JSON.stringify({protocol:1,kind:"RUN_SYNTHETIC_DRAFT",consent:"CI_ONLY"})
    :JSON.stringify({protocol:1,kind:"UNSUPPORTED_REQUEST",consent:"CI_ONLY"});
  child.stdin.write(request+"\n");
}
