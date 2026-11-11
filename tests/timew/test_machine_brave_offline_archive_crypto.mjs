import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {mkdtempSync,readFileSync,readdirSync,rmSync,statSync} from "node:fs";
import {tmpdir} from "node:os";
import {resolve,join,dirname,basename} from "node:path";
import {spawnSync} from "node:child_process";
import {sealSelectedSession} from "../../integrations/machine/brave-topology/session-seal.mjs";
import {inspectSealedSnapshot} from "../../integrations/machine/brave-topology/session-unseal.mjs";

const repo=resolve(new URL("../../",import.meta.url).pathname);
const dataHome=mkdtempSync(join(tmpdir(),"machine-offline-durable-test-"));
let disposable=null;
const password="SYNTHETIC OFFLINE ARCHIVE PASSPHRASE ONLY";
const token="DEMO-SECRET-PARAM-NOT-REAL";
function py(lines,args=[],payload=null){
  const res=spawnSync("python3",["-B","-I","-c",lines.join("\n"),...args],{
    cwd:repo,encoding:"utf8",
    input:payload===null?undefined:JSON.stringify(payload)+"\n",
    timeout:30000
  });
  assert.equal(res.error,undefined);
  assert.equal(res.stderr,"");
  assert.equal(res.status,0,res.stdout);
  return JSON.parse(res.stdout);
}
try{
  const envelope=await sealSelectedSession({
    label:"WORK",passphrase:password,includeSensitive:true,
    tabs:[
      {index:0,url:"https://example.test/start",pinned:true,wasActive:true},
      {index:2,url:"https://private.test/path?token="+token,
       pinned:false,wasActive:false},
    ]
  },webcrypto);
  const initCode=[
    "import json,os,sys",
    "sys.path.insert(0,'services/time')",
    "from MachineBraveDisposableTrial import init_trial,register_trial",
    "from MachineBraveFocusTrial import register_focus",
    "from MachineBraveTitleTrial import register as title",
    "from MachineBraveSaveTrial import register as save",
    "from MachineBraveReadTrial import register as reader",
    "import MachineBraveSealedVault as vault",
    "r=init_trial()['trial_root']",
    "e='a'*32",
    "register_trial(r,e)",
    "register_focus(r,e)",
    "title(r,e)",
    "save(r,e)",
    "reader(r,e)",
    "original=os.environ.get('XDG_DATA_HOME')",
    "os.environ['XDG_DATA_HOME']=r+'/vault-data'",
    "try:",
    "    report=vault.put({'kind':vault.REQUEST_KIND,'operator_save_requested':True,",
    "                      'envelope':json.load(sys.stdin)})",
    "finally:",
    "    if original is None:os.environ.pop('XDG_DATA_HOME',None)",
    "    else:os.environ['XDG_DATA_HOME']=original",
    "print(json.dumps({'trial':r,'record_id':report['record_id'],'sha256':report['sha256']}))",
  ];
  const created=py(initCode,[],envelope);
  disposable=created.trial;
  assert.equal(dirname(disposable),"/tmp");
  assert.match(basename(disposable),/^postapollo-machine-brave-trial-[A-Za-z0-9_-]{6,}$/);

  // No local production write. Test explicitly injects temporary data home
  // and consent to exercise the same archive code as a manual CLI.
  const archiveCode=[
    "import json,sys",
    "from pathlib import Path",
    "sys.path.insert(0,'services/time')",
    "import MachineBraveOfflineArchive as offline",
    "trial,record_id,digest,home=sys.argv[1:]",
    "preview=offline.inspect(trial,record_id)",
    "assert preview['source_sha256']==digest",
    "out=offline.archive(trial,record_id,digest,",
    "    confirmation=lambda rid:rid==record_id,destination=Path(home))",
    "print(json.dumps(out))",
  ];
  const imported=py(archiveCode,[
    disposable,created.record_id,created.sha256,dataHome
  ]);
  assert.equal(imported.status,"offline_sealed_record_archived");
  assert.equal(imported.source_record_id,created.record_id);
  assert.equal(imported.restore_allowed,false);
  assert.equal(imported.ciphertext_authentication_verified,false);
  assert.equal(imported.persistent_origin_authenticated,false);
  const archiveDir=join(dataHome,"post-apollo/machine/brave-sealed-vault");
  const files=readdirSync(archiveDir);
  assert.deepEqual(files,[imported.archive_record_id+".json"]);
  const storedPath=join(archiveDir,files[0]);
  assert.equal(statSync(storedPath).mode & 0o777,0o600);
  const fileBytes=readFileSync(storedPath);
  for(const secret of ["https://","example.test","private.test",
                       token,password,'\"tabs\"']){
    assert.equal(fileBytes.includes(Buffer.from(secret)),false,secret);
  }
  const record=JSON.parse(fileBytes.toString("utf8"));
  assert.deepEqual(record.envelope,envelope);
  const preview=await inspectSealedSnapshot(record.envelope,password,webcrypto);
  assert.equal(preview.status,"authenticated_redacted_review");
  assert.deepEqual(preview.tabs.map(v=>v.hostname),
    ["example.test","private.test"]);
  assert.equal(preview.sensitive_count,1);
  assert.equal(preview.restore_allowed,false);
  assert.equal(JSON.stringify(preview).includes(token),false);
  await assert.rejects(
    ()=>inspectSealedSnapshot(record.envelope,"not the password 1234",webcrypto)
  );
  const repeat=py(archiveCode,[
    disposable,created.record_id,created.sha256,dataHome
  ]);
  assert.equal(repeat.status,"already_archived");
  assert.equal(readdirSync(archiveDir).length,1);

  // Original disposable record remains byte-identical, not moved/deleted.
  const originalPath=join(disposable,"vault-data/post-apollo/machine/brave-sealed-vault",
    created.record_id+".json");
  const source=JSON.parse(readFileSync(originalPath,"utf8"));
  assert.deepEqual(source.envelope,envelope);
}finally{
  if(disposable!==null){
    assert.equal(dirname(disposable),"/tmp");
    assert.match(basename(disposable),/^postapollo-machine-brave-trial-[A-Za-z0-9_-]{6,}$/);
    rmSync(disposable,{recursive:true,force:true});
  }
  rmSync(dataHome,{recursive:true,force:true});
}
console.log("MACHINE actual synthetic WebCrypto sealed record -> offline archive -> authenticated redacted read PASS");
