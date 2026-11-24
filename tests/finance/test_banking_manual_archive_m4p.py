#!/usr/bin/env python3
"""Banking M4p: explicit private backups, CAS restore, and refusal cases."""
import copy
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"scripts"/"finance"))
import banking_manual_store as manual
import banking_manual_archive as archive

def refusal(fn, code=None):
    try:
        fn()
    except manual.Refusal as err:
        if code is not None:
            assert str(err)==code,(code,str(err))
        return
    raise AssertionError("Expected a refusal: "+str(code))

def account(n,kind,nickname,opening):
    return {"id":"acct-"+str(n),"providerId":"chime","productId":kind,
            "nickname":nickname,"openingCents":opening,"origin":"manual"}

def entry(n,acct,cents,memo,**link):
    return {"id":"entry-"+str(n),"accountId":acct,
            "date":"2026-11-24","description":memo,"amountCents":cents,
            "origin":"manual",**link}

original={"mode":"manual","accounts":[
    account(1,"chime-checking","Checking",10000),
    account(2,"chime-savings","Savings",None)],
    "entries":[
      entry(3,"acct-1",-700,"Transfer test",transferId="transfer-3",transferSide="out"),
      entry(4,"acct-2",700,"Transfer test",transferId="transfer-3",transferSide="in"),
      entry(5,"acct-1",-123,"Coffee"),
      entry(6,"acct-2",400,"Deposit")],
    "nextId":7}

with tempfile.TemporaryDirectory() as tmp:
    store=Path(tmp)/"finance"/"banking-manual"
    assert archive.run(store,{"action":"list"})=={"action":"list","backups":[]}
    assert not store.exists()
    refusal(lambda:archive.run(store,{"action":"create","expectedRevision":1,
                                     "confirmBackup":True}),"STALE_REVISION")
    # A source save is the only way to establish manual data for backup.
    first=manual.run(store,{"action":"save","expectedRevision":0,"session":original})
    assert first["revision"]==1
    refusal(lambda:archive.run(store,{"action":"create","expectedRevision":0,
                                     "confirmBackup":True}),"INVALID_REVISION")
    refusal(lambda:archive.run(store,{"action":"create","expectedRevision":1,
                                     "confirmBackup":False}),"CONFIRM_BACKUP_REQUIRED")
    assert archive.run(store,{"action":"list"})["backups"]==[]
    result=archive.run(store,{"action":"create","expectedRevision":1,
                              "confirmBackup":True})
    meta=result["backup"]
    identity=meta["backupId"]
    assert archive.valid_backup_id(identity)
    assert meta["sourceRevision"]==1
    assert meta["accountCount"]==2 and meta["entryCount"]==4
    assert meta["connected"] is False and meta["bankVerified"] is False
    assert meta["encrypted"] is False
    assert archive.run(store,{"action":"inspect","backupId":identity})["backup"]==meta
    assert archive.run(store,{"action":"list"})["backups"]==[meta]
    assert manual.read_doc(store)==first,"Backup may not mutate source revision"
    for path, expected in ((store,0o700),(store/"backups",0o700),
                           (store/"backups"/identity,0o600)):
        assert stat.S_IMODE(path.stat().st_mode)==expected, (path,oct(path.stat().st_mode))
    assert "session" not in archive.run(store,{"action":"inspect","backupId":identity})
    raw=(store/"backups"/identity).read_bytes()
    assert b"Transfer test" in raw,"Backup is plainly not encrypted"

    newer=copy.deepcopy(original)
    newer["accounts"][0]["nickname"]="Checking renamed"
    newer["entries"][-1]["amountCents"]=200
    second=manual.run(store,{"action":"save","expectedRevision":1,"session":newer})
    assert second["revision"]==2
    refusal(lambda:archive.run(store,{"action":"create","expectedRevision":1,
                                     "confirmBackup":True}),"STALE_REVISION")
    restore_args={"action":"restore","backupId":identity,
                  "expectedRevision":2,"expectedBackupSha256":meta["sha256"],
                  "confirmRestore":True}
    refusal(lambda:archive.run(store,{**restore_args,"confirmRestore":False}),
            "CONFIRM_RESTORE_REQUIRED")
    refusal(lambda:archive.run(store,{**restore_args,"expectedRevision":1}),
            "STALE_REVISION")
    refusal(lambda:archive.run(store,{**restore_args,"expectedBackupSha256":"0"*64}),
            "STALE_BACKUP_SELECTION")
    assert manual.read_doc(store)==second
    success=archive.run(store,restore_args)
    assert success["newRevision"]==3 and success["restored"] is True
    restored=manual.read_doc(store)
    assert restored["revision"]==3 and restored["session"]==original
    assert manual.validate_session(restored["session"])==original
    assert restored["session"]["entries"][0]["transferId"]=="transfer-3"
    assert restored["session"]["accounts"][1]["openingCents"] is None
    assert archive.run(store,{"action":"inspect","backupId":identity})["backup"]==meta
    refusal(lambda:archive.run(store,restore_args),"STALE_REVISION")

    refusal(lambda:archive.run(store,{"action":"delete","backupId":identity,
                    "expectedBackupSha256":meta["sha256"],"confirmDelete":False}),
            "CONFIRM_DELETE_REQUIRED")
    refusal(lambda:archive.run(store,{"action":"delete","backupId":identity,
                    "expectedBackupSha256":"0"*64,"confirmDelete":True}),
            "STALE_BACKUP_SELECTION")
    assert archive.run(store,{"action":"delete","backupId":identity,
                    "expectedBackupSha256":meta["sha256"],"confirmDelete":True})["deleted"]
    assert archive.run(store,{"action":"list"})["backups"]==[]
    refusal(lambda:archive.run(store,restore_args),"STALE_REVISION")
    refusal(lambda:archive.run(store,{"action":"inspect","backupId":identity}),
            "BACKUP_NOT_FOUND")
    refusal(lambda:archive.run(store,{"action":"inspect","backupId":"../manual-session.json"}),
            "INVALID_BACKUP_ID")

    # Private archive list is bounded; no uncontrolled backup hoarding.
    records=[]
    for i in range(archive.MAX_BACKUPS):
        item=archive.run(store,{"action":"create","expectedRevision":3,
                                "confirmBackup":True})["backup"]
        records.append(item)
    assert len(archive.run(store,{"action":"list"})["backups"])==archive.MAX_BACKUPS
    refusal(lambda:archive.run(store,{"action":"create","expectedRevision":3,
                                     "confirmBackup":True}),"BACKUP_LIMIT")
    for item in records:
        archive.run(store,{"action":"delete","backupId":item["backupId"],
                  "expectedBackupSha256":item["sha256"],"confirmDelete":True})
    assert archive.run(store,{"action":"list"})["backups"]==[]

    # Checksum refuses on-disk manipulation before restore.
    item=archive.run(store,{"action":"create","expectedRevision":3,
                            "confirmBackup":True})["backup"]
    p=store/"backups"/item["backupId"]
    obj=json.loads(p.read_text())
    obj["document"]["session"]["accounts"][0]["nickname"]="Tampered"
    p.write_text(json.dumps(obj))
    p.chmod(0o600)
    refusal(lambda:archive.run(store,{"action":"inspect","backupId":item["backupId"]}),
            "BACKUP_CHECKSUM_MISMATCH")
    refusal(lambda:archive.run(store,{"action":"restore","backupId":item["backupId"],
                    "expectedRevision":3,"expectedBackupSha256":item["sha256"],
                    "confirmRestore":True}),"BACKUP_CHECKSUM_MISMATCH")
    assert manual.read_doc(store)["revision"]==3
    p.unlink()
    p.symlink_to(store/"manual-session.json")
    refusal(lambda:archive.run(store,{"action":"inspect","backupId":item["backupId"]}),
            "UNSAFE_BACKUP")
    p.unlink()
    (store/"backups").chmod(0o777)
    refusal(lambda:archive.run(store,{"action":"list"}),"UNSAFE_DIRECTORY")

with tempfile.TemporaryDirectory() as tmp:
    store=Path(tmp)/"banking"
    first=manual.run(store,{"action":"save","expectedRevision":0,"session":original})
    item=archive.run(store,{"action":"create","expectedRevision":1,
                            "confirmBackup":True})["backup"]
    manual.run(store,{"action":"clear","expectedRevision":1,"confirmClear":True})
    restored=archive.run(store,{"action":"restore","backupId":item["backupId"],
                  "expectedRevision":2,"expectedBackupSha256":item["sha256"],
                  "confirmRestore":True})
    assert restored["newRevision"]==3
    assert manual.read_doc(store)["session"]==original

print("Banking M4p: private create/list/inspect/restore/delete, atomic backup, CAS, paired transfer recovery, integrity/permissions refusal, bounded archive PASS")
