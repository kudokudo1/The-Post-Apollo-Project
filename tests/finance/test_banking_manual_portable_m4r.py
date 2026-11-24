#!/usr/bin/env python3
"""M4r disposable cross-device encrypted export/import with real Node crypto."""
import copy
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/finance"))
import banking_manual_store as manual
import banking_manual_portable as portable

PASSWORD = "synthetic passphrase for test only"
MEMO = "SENSITIVE SYNTHETIC TRANSFER DESCRIPTION"
SESSION = {"mode":"manual","accounts":[
    {"id":"acct-1","providerId":"chime","productId":"chime-checking",
     "nickname":"Synthetic account","openingCents":12000,"origin":"manual"},
    {"id":"acct-2","providerId":"chime","productId":"chime-savings",
     "nickname":"Synthetic reserve","openingCents":None,"origin":"manual"}],
    "entries":[
      {"id":"entry-3","accountId":"acct-1","date":"2026-11-24",
       "description":MEMO,"amountCents":-2500,"origin":"manual",
       "transferId":"transfer-3","transferSide":"out"},
      {"id":"entry-4","accountId":"acct-2","date":"2026-11-24",
       "description":MEMO,"amountCents":2500,"origin":"manual",
       "transferId":"transfer-3","transferSide":"in"}],"nextId":5}

def refuses(call, reason):
    try:
        call()
    except manual.Refusal as err:
        assert str(err)==reason,(str(err),reason)
        return
    raise AssertionError("Expected "+reason)

def save(d, state=SESSION):
    return manual.run(d,{"action":"save","expectedRevision":0,"session":state})

def export(d, revision=1):
    return portable.run(d,{"action":"export","expectedRevision":revision,
                           "password":PASSWORD,"confirmExport":True})

def preview(d, name, password=PASSWORD):
    return portable.run(d,{"action":"preview","portableId":name,"password":password})

def request(p, revision=0):
    return {"action":"import","portableId":p["portableId"],"password":PASSWORD,
            "expectedSha256":p["sha256"],"expectedRevision":revision,
            "confirmImport":True,"confirmClientsClosed":True}

with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/"source"
    destination=Path(tmp)/"destination"
    original=save(source)
    refuses(lambda:portable.run(source,{"action":"export","expectedRevision":1,
                   "password":PASSWORD,"confirmExport":False}),"EXPLICIT_EXPORT_REQUIRED")
    refuses(lambda:export(source,2),"STALE_REVISION")
    first=export(source)
    second=export(source)
    assert first["portableId"]!=second["portableId"]
    file=source/"portable"/first["portableId"]
    other=source/"portable"/second["portableId"]
    raw=file.read_bytes()
    e=json.loads(raw)
    e2=json.loads(other.read_bytes())
    assert e["salt"]!=e2["salt"] and e["nonce"]!=e2["nonce"]
    assert e["ciphertext"]!=e2["ciphertext"]
    assert first["encrypted"] is True
    for secret in (PASSWORD,MEMO,"Synthetic account","openingCents","transferId"):
        assert secret.encode() not in raw,secret
    assert stat.S_IMODE(file.stat().st_mode)==0o600
    assert stat.S_IMODE(file.parent.stat().st_mode)==0o700
    assert manual.read_doc(source)==original
    assert not destination.exists()
    refuses(lambda:portable.run(destination,{"action":"prepare","confirmPrepare":False}),
            "EXPLICIT_PREPARE_REQUIRED")
    assert not destination.exists()
    portable.run(destination,{"action":"prepare","confirmPrepare":True})
    copied=destination/"portable"/file.name
    shutil.copyfile(file,copied)
    copied.chmod(0o600)
    p=preview(destination,file.name)
    assert p["sha256"]==first["sha256"] and p["sourceRevision"]==1
    assert p["accountCount"]==2 and p["entryCount"]==2
    assert p["ciphertextAuthenticated"] and not p["originAuthenticated"]
    assert "session" not in p and MEMO not in json.dumps(p)
    assert manual.read_doc(destination)==manual.empty_doc()
    assert not (destination/"manual-session.json").exists()
    refuses(lambda:preview(destination,file.name,"wrong synthetic password"),
            "PORTABLE_CRYPTO_REFUSED")
    refuses(lambda:preview(destination,"../"+file.name),"INVALID_PORTABLE_ID")
    c=request(p)
    for field in ("confirmImport","confirmClientsClosed"):
        refuses(lambda:portable.run(destination,{**c,field:False}),"EXPLICIT_IMPORT_REQUIRED")
    refuses(lambda:portable.run(destination,{**c,"expectedRevision":1}),"STALE_REVISION")
    refuses(lambda:portable.run(destination,{**c,"expectedSha256":"0"*64}),
            "STALE_PORTABLE_SELECTION")
    copied.chmod(0o644)
    refuses(lambda:preview(destination,file.name),"UNSAFE_PORTABLE_FILE")
    copied.chmod(0o600)
    # Authenticated encryption rejects modified ciphertext, even if a caller
    # obtains the changed file's new SHA-256.
    tampered=copy.deepcopy(e)
    ct=bytearray(portable.unb64(e["ciphertext"],manual.MAX_BYTES+16))
    ct[0]^=1
    tampered["ciphertext"]=portable.b64(ct)
    copied.write_text(json.dumps(tampered))
    refuses(lambda:preview(destination,file.name),"PORTABLE_CRYPTO_REFUSED")
    refuses(lambda:portable.run(destination,c),"STALE_PORTABLE_SELECTION")
    wrong_kdf={**e,"iterations":1}
    copied.write_text(json.dumps(wrong_kdf))
    refuses(lambda:preview(destination,file.name),"INVALID_ENVELOPE")
    copied.write_bytes(raw)
    assert not (destination/"manual-session.json").exists()
    result=portable.run(destination,c)
    assert result["newRevision"]==2
    assert manual.read_doc(destination)=={"version":1,"revision":2,"session":SESSION}
    assert manual.read_doc(source)==original
    refuses(lambda:portable.run(destination,c),"STALE_REVISION")
    refuses(lambda:portable.run(destination,{**c,"expectedRevision":2}),
            "DESTINATION_NOT_EMPTY")
    copied.unlink()
    copied.symlink_to(file)
    refuses(lambda:preview(destination,file.name),"PORTABLE_NOT_FOUND_OR_UNSAFE")

    # Real CLI failure must not expose password, financial content, or stack.
    env={**os.environ,"XDG_DATA_HOME":str(Path(tmp)/"cli-data")}
    root=Path(env["XDG_DATA_HOME"])/"post-apollo/finance/banking-manual"
    save(root)
    exported=export(root)
    proc=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/finance/banking_manual_portable.py")],
        input=json.dumps({"action":"preview","portableId":exported["portableId"],
                          "password":"wrong synthetic password"})+"\n",
        text=True,capture_output=True,env=env,timeout=30)
    assert proc.returncode==1 and not proc.stdout
    assert proc.stderr=="FINANCEW_BANKING_PORTABLE_ERROR PORTABLE_CRYPTO_REFUSED\n"

    # Full existing 300-entry bound survives real encryption.
    large=copy.deepcopy(SESSION)
    for i in range(5,303):
        large["entries"].append({"id":"entry-"+str(i),"accountId":"acct-1",
            "date":"2026-11-24","description":"é"*120,"amountCents":1,"origin":"manual"})
    large["nextId"]=303
    a=Path(tmp)/"large-source"; b=Path(tmp)/"large-dest"
    save(a,large); sealed=export(a)
    portable.run(b,{"action":"prepare","confirmPrepare":True})
    dest=b/"portable"/sealed["portableId"]
    shutil.copyfile(a/"portable"/sealed["portableId"],dest); dest.chmod(0o600)
    view=preview(b,sealed["portableId"])
    assert view["entryCount"]==300
    portable.run(b,request(view))
    assert manual.read_doc(b)["session"]==large

# Source-only gate: no QML mount, no automatic writer integration.
for path in ("widgets/FinanceBankingAccountsPane.qml",
             "widgets/FinanceBankingManualStorageControls.qml",
             "services/finance/FinanceBankingManualStore.qml"):
    assert "banking_manual_portable" not in (ROOT/path).read_text()
print("M4r PASS: actual AES-GCM cross-device roundtrip, wrong-password/tamper refusal, empty-destination CAS, private files, 300 entries and no activation")
