#!/usr/bin/env python3
"""M4t3 fixture-only recovery driver, copied into disposable CI shell."""
import os
from pathlib import Path
import sys

import banking_manual_store as manual
import banking_manual_archive as archive
import banking_manual_portable as portable
import banking_manual_recovery as recovery
import banking_recovery_handoff_candidate as handoff

PASSWORD = "fictional only M4t3 passphrase"
DAMAGED = b'{"version":1,"revision":5,"session":null}\n'

def refuses(call, code):
    try:
        call()
    except manual.Refusal as e:
        assert str(e) == code, (str(e), code)
        return
    raise AssertionError("expected refusal " + code)

def guarded(d, request):
    return handoff.guarded_recovery(d, request, confirm_clients_closed=True)

def root():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert os.environ.get("POST_APOLLO_BANKING_M4T3") == "CI_DISPOSABLE_ONLY"
    work = Path(__file__).resolve().parents[2]
    assert work.name.startswith("banking-m4t3-native-")
    assert Path(os.environ["XDG_DATA_HOME"]) == work / "data"
    assert (work / "fixture-only").read_text() == "M4T3\n"
    return manual.store_dir()

def run(stage):
    d = root()
    rows = archive.run(d, {"action":"list"})["backups"]
    assert len(rows) == 1 and rows[0]["sourceRevision"] == 1
    backup = rows[0]
    names = list((d/"portable").glob("banking-*.sealed.json"))
    assert len(names) == 1
    sealed = names[0]
    p = portable.run(d, {"action":"preview","portableId":sealed.name,"password":PASSWORD})
    assert p["ciphertextAuthenticated"] is True and p["originAuthenticated"] is False
    assert p["sourceRevision"] == 1 and p["accountCount"] == 2 and p["entryCount"] == 2
    restore = {"action":"restore","backupId":backup["backupId"],"expectedRevision":2,
               "expectedBackupSha256":backup["sha256"],"confirmRestore":True}
    imp = {"action":"import","portableId":sealed.name,"password":PASSWORD,
           "expectedSha256":p["sha256"],"expectedRevision":4,
           "confirmImport":True,"confirmClientsClosed":True}
    primary = d/"manual-session.json"
    before = primary.read_bytes()
    if stage == "busy":
        assert manual.read_doc(d)["revision"] == 2
        refuses(lambda:guarded(d,restore),"CLIENT_LEASE_BUSY")
        refuses(lambda:guarded(d,imp),"CLIENT_LEASE_BUSY")
        assert primary.read_bytes() == before
    elif stage == "restore":
        refuses(lambda:handoff.guarded_recovery(d,restore),"EXPLICIT_CLOSED_CLIENTS_REQUIRED")
        refuses(lambda:guarded(d,{**restore,"expectedBackupSha256":"0"*64}),"STALE_BACKUP_SELECTION")
        assert primary.read_bytes() == before
        assert guarded(d,restore)["newRevision"] == 3
        refuses(lambda:guarded(d,restore),"STALE_REVISION")
    elif stage == "import":
        assert manual.read_doc(d) == {"version":1,"revision":4,"session":manual.empty_session()}
        refuses(lambda:guarded(d,{**imp,"password":"incorrect fictional passphrase"}),"PORTABLE_CRYPTO_REFUSED")
        refuses(lambda:guarded(d,{**imp,"expectedSha256":"0"*64}),"STALE_PORTABLE_SELECTION")
        assert primary.read_bytes() == before
        assert guarded(d,imp)["newRevision"] == 5
        refuses(lambda:guarded(d,{**imp,"expectedRevision":5}),"DESTINATION_NOT_EMPTY")
    elif stage == "recover":
        assert manual.read_doc(d)["revision"] == 5
        # Deliberate fixture-only corruption, only after all native clients exit.
        with handoff._lease(d,True):
            primary.write_bytes(DAMAGED)
        view = recovery.run(d, {"action":"preview","backupId":backup["backupId"]})
        req = {"action":"recover","backupId":backup["backupId"],
               "expectedPrimarySha256":view["primarySha256"],
               "expectedBackupSha256":backup["sha256"],"lastKnownRevision":5,
               "confirmRecovery":True,"confirmClientsClosed":True}
        refuses(lambda:guarded(d,{**req,"lastKnownRevision":4}),"REVISION_FLOOR_TOO_LOW")
        assert primary.read_bytes() == DAMAGED
        result = guarded(d,req)
        assert result["newRevision"] == 6
        assert (d/"recovery-quarantine"/result["quarantineId"]).read_bytes() == DAMAGED
    else:
        raise AssertionError("unknown fixture stage")
    print("M4T3_DRIVER_PASS " + stage, flush=True)

if __name__ == "__main__":
    assert len(sys.argv) == 2
    run(sys.argv[1])
