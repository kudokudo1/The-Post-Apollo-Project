import assert from "node:assert/strict";
import {mkdtempSync,readFileSync,readdirSync,rmSync,statSync} from "node:fs";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {spawnSync} from "node:child_process";
import {
  randomBytes,pbkdf2Sync,createCipheriv,createDecipheriv
} from "node:crypto";

const root=resolve(new URL("../../",import.meta.url).pathname);
const script=join(root,"services/time/MachineBraveSealedVault.py");
const base=mkdtempSync(join(tmpdir(),"postapollo-sealed-e2e-"));
const env={...process.env,XDG_DATA_HOME:base};
const enc=x=>Buffer.from(x).toString("base64url");
const dec=x=>Buffer.from(x,"base64url");
const AAD="machine-brave-sealed-session-v1";
const password="TEST ONLY UNRELATED TO ANY REAL USER PASSWORD";
const token="SECRET_AUTH_QUERY_TOKEN";
const pages={kind:"machine-brave-test-synthetic-session",windows:[
  {label:"WORK",tabs:[
    "https://example.test/one",
    "https://example.test/private?auth="+token]},
  {label:"MEDIA",tabs:["https://radio.test/hello"]}
]};
function run(...args){
  const input=typeof args[args.length-1]==="object"?args.pop():null;
  const p=spawnSync("python3",["-B","-I",script,...args],{
    input:input===null?undefined:JSON.stringify(input)+"\n",
    cwd:root,env,encoding:"utf8",timeout:10000
  });
  assert.equal(p.error,undefined);
  assert.equal(p.stderr,"");
  return {exit:p.status,body:JSON.parse(p.stdout)};
}
try{
  const missing=run("list");
  assert.equal(missing.exit,0);
  assert.deepEqual(missing.body.records,[]);
  const original=Buffer.from(JSON.stringify(pages),"utf8");
  const salt=randomBytes(16),nonce=randomBytes(12),iterations=600000;
  const key=pbkdf2Sync(password,salt,iterations,32,"sha256");
  const cipher=createCipheriv("aes-256-gcm",key,nonce);
  cipher.setAAD(Buffer.from(AAD));
  const ciphertext=Buffer.concat([
    cipher.update(original),cipher.final(),cipher.getAuthTag()
  ]);
  const envelope={
    kind:AAD,version:1,algorithm:"AES-256-GCM",
    kdf:"PBKDF2-HMAC-SHA256",iterations,
    salt:enc(salt),nonce:enc(nonce),aad:AAD,ciphertext:enc(ciphertext)
  };
  const put=run("put",{
    kind:"machine-brave-sealed-vault-put-v1",
    operator_save_requested:true,envelope
  });
  assert.equal(put.exit,0);
  assert.equal(put.body.status,"sealed_record_saved");
  assert.equal(put.body.ciphertext_authentication_verified,false);
  assert.equal(put.body.restore_allowed,false);
  assert.deepEqual(put.body.safe_actions,[]);
  const dir=join(base,"post-apollo","machine","brave-sealed-vault");
  const files=readdirSync(dir);
  assert.equal(files.length,1);
  const bytes=readFileSync(join(dir,files[0]));
  assert.equal(statSync(join(dir,files[0])).mode & 0o777,0o600);
  for(const sensitive of [
    token,"https://","example.test","radio.test",password,
    '"windows":','"tabs":'
  ])assert.equal(bytes.includes(Buffer.from(sensitive)),false,sensitive);
  const read=run("read",put.body.record_id);
  assert.equal(read.exit,0);
  assert.equal(read.body.status,"sealed_record_read");
  assert.deepEqual(read.body.record.envelope,envelope);
  assert.equal(read.body.ciphertext_authentication_verified,false);
  const unpack=(secret,change)=>{
    const secretKey=pbkdf2Sync(secret,dec(envelope.salt),iterations,32,"sha256");
    const encrypted=Buffer.from(ciphertext);
    if(change)encrypted[0]^=1;
    const decipher=createDecipheriv("aes-256-gcm",secretKey,nonce);
    decipher.setAAD(Buffer.from(AAD));
    decipher.setAuthTag(encrypted.subarray(-16));
    return Buffer.concat([decipher.update(encrypted.subarray(0,-16)),
                          decipher.final()]).toString("utf8");
  };
  assert.deepEqual(JSON.parse(unpack(password,false)),pages);
  assert.throws(()=>unpack("wrong password",false));
  assert.throws(()=>unpack(password,true));

  const list=run("list");
  assert.equal(list.exit,0);
  assert.equal(list.body.records.length,1);
  assert.equal(list.body.records[0].record_id,put.body.record_id);
  assert.equal(JSON.stringify(list.body).includes(token),false);
  assert.equal(list.body.ciphertext_authentication_verified,false);
  assert.equal(list.body.restore_allowed,false);

  const wrong=run("delete",put.body.record_id,"0".repeat(64));
  assert.equal(wrong.exit,1);
  assert.equal(readdirSync(dir).length,1);
  const removed=run("delete",put.body.record_id,put.body.sha256);
  assert.equal(removed.exit,0);
  assert.equal(removed.body.status,"sealed_record_deleted");
  assert.equal(readdirSync(dir).length,0);
  assert.equal(run("list").body.records.length,0);
}finally{
  rmSync(base,{recursive:true,force:true});
}
console.log("MACHINE synthetic AES-256-GCM sealed snapshot survives vault roundtrip; no plaintext, delete PASS");
