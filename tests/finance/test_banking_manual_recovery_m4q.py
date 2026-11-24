#!/usr/bin/env python3
"""M4q disposable damaged-primary recovery and quarantine tests."""
import copy
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"scripts"/"finance"))
import banking_manual_store as manual
import banking_manual_archive as archive
import banking_manual_recovery as recovery

def refuses(fn, reason):
    try:
        fn()
    except manual.Refusal as err:
        assert str(err)==reason,(str(err),reason)
        return
    raise AssertionError("Expected "+reason)

session={"mode":"manual","accounts":[
    {"id":"acct-1","providerId":"chime","productId":"chime-checking",
     "nickname":"Example","openingCents":12000,"origin":"manual"},
    {"id":"acct-2","providerId":"chime","productId":"chime-savings",
     "nickname":"Reserve","openingCents":None,"origin":"manual"}],
    "entries":[
    {"id":"entry-3","accountId":"acct-1","date":"2026-11-24",
     "description":"Transfer","amountCents":-2500,"origin":"manual",
     "transferId":"transfer-3","transferSide":"out"},
    {"id":"entry-4","accountId":"acct-2","date":"2026-11-24",
     "description":"Transfer","amountCents":2500,"origin":"manual",
     "transferId":"transfer-3","transferSide":"in"}],"nextId":5}

def setup(d):
    manual.run(d,{"action":"save","expectedRevision":0,"session":session})
    return archive.run(d,{"action":"create","expectedRevision":1,
                          "confirmBackup":True})["backup"]

def preview(d,b):
    return recovery.run(d,{"action":"preview","backupId":b["backupId"]})

def command(p,revision):
    return {"action":"recover","backupId":p["backup"]["backupId"],
            "expectedPrimarySha256":p["primarySha256"],
            "expectedBackupSha256":p["backup"]["sha256"],
            "lastKnownRevision":revision,"confirmRecovery":True,
            "confirmClientsClosed":True}

with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)/"banking"
    b=setup(d)
    primary=d/"manual-session.json"
    q=d/"recovery-quarantine"
    refuses(lambda:preview(d,b),"PRIMARY_IS_VALID_USE_NORMAL_RESTORE")
    assert not q.exists()
    original=b'{"version":1,"revision":9,"session":'
    primary.write_bytes(original)
    p=preview(d,b)
    assert p["primarySha256"]==recovery.sha(original)
    assert p["primaryBytes"]==len(original)
    assert p["primaryRevisionHint"] is None
    assert p["observedRevisionFloor"]==1
    assert not p["revisionHistoryVerified"] and p["requiresClosedClients"]
    assert not q.exists() and primary.read_bytes()==original
    c=command(p,9)
    for field in ("confirmRecovery","confirmClientsClosed"):
        refuses(lambda:recovery.run(d,{**c,field:False}),
                "EXPLICIT_RECOVERY_CONFIRMATION_REQUIRED")
    refuses(lambda:recovery.run(d,{**c,"expectedPrimarySha256":"0"*64}),
            "STALE_PRIMARY_SELECTION")
    refuses(lambda:recovery.run(d,{**c,"expectedBackupSha256":"0"*64}),
            "STALE_BACKUP_SELECTION")
    refuses(lambda:recovery.run(d,{**c,"lastKnownRevision":0}),
            "REVISION_FLOOR_TOO_LOW")
    assert not q.exists() and primary.read_bytes()==original
    # A cooperating writer holding the existing M4o lock blocks recovery.
    with open(d/"manual-session.lock","rb") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        refuses(lambda:recovery.run(d,c),"WRITE_BUSY")
    assert not q.exists()
    # Inject a failure before primary replacement. The original remains in
    # place, and a retry can reuse the already-preserved quarantine copy.
    with patch.object(manual,"write_doc",side_effect=OSError("test failure")):
        try:
            recovery.run(d,c)
        except OSError:
            pass
        else:
            raise AssertionError("Expected injected failure")
    name="damaged-"+recovery.sha(original)+".bin"
    assert primary.read_bytes()==original and (q/name).read_bytes()==original
    assert stat.S_IMODE(q.stat().st_mode)==0o700
    assert stat.S_IMODE((q/name).stat().st_mode)==0o600
    result=recovery.run(d,c)
    assert result["newRevision"]==10 and result["quarantineId"]==name
    assert manual.read_doc(d)=={"version":1,"revision":10,"session":session}
    assert len(list(q.iterdir()))==1
    assert archive.run(d,{"action":"inspect","backupId":b["backupId"]})["backup"]==b
    refuses(lambda:recovery.run(d,c),"PRIMARY_IS_VALID_USE_NORMAL_RESTORE")

with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)/"banking"
    b=setup(d)
    primary=d/"manual-session.json"
    primary.write_text(json.dumps({"version":2,"revision":2,"session":session}))
    refuses(lambda:preview(d,b),"UNKNOWN_PRIMARY_VERSION")
    primary.write_text(json.dumps({"version":1,"revision":24,"session":{}}))
    p=preview(d,b)
    assert p["primaryRevisionHint"]==24 and p["observedRevisionFloor"]==24
    refuses(lambda:recovery.run(d,command(p,23)),"REVISION_FLOOR_TOO_LOW")
    primary.write_bytes(b"changed")
    refuses(lambda:recovery.run(d,command(p,24)),"STALE_PRIMARY_SELECTION")
    p=preview(d,b)
    primary.chmod(0o644)
    refuses(lambda:preview(d,b),"UNSAFE_RECOVERY_FILE")
    primary.chmod(0o600)
    primary.unlink()
    primary.symlink_to(d/"backups"/b["backupId"])
    refuses(lambda:preview(d,b),"RECOVERY_FILE_UNAVAILABLE")
    primary.unlink()
    refuses(lambda:preview(d,b),"RECOVERY_FILE_UNAVAILABLE")
    primary.write_bytes(b"broken")
    primary.chmod(0o600)
    hardlink=d/"alias"
    os.link(primary,hardlink)
    refuses(lambda:preview(d,b),"UNSAFE_RECOVERY_FILE")
    hardlink.unlink()
    p=preview(d,b)
    q=d/"recovery-quarantine"
    q.mkdir(mode=0o700)
    target=q/("damaged-"+p["primarySha256"]+".bin")
    target.write_bytes(b"not the original")
    target.chmod(0o600)
    refuses(lambda:recovery.run(d,command(p,24)),"QUARANTINE_MISMATCH")
    assert primary.read_bytes()==b"broken"

print("M4q PASS: valid/unknown/unsafe primary refusal, stale selection, lock, durable quarantine, failed-commit retry, original pair preservation and revision floor")
