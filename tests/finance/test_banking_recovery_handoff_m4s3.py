#!/usr/bin/env python3
"""M4s3 real Linux process exclusion and disposable recovery only."""
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/finance"
sys.path.insert(0, str(SCRIPTS))
import banking_manual_store as manual
import banking_manual_archive as archive
import banking_manual_recovery as recovery
import banking_manual_portable as portable
import banking_recovery_handoff_candidate as handoff

SESSION = {"mode":"manual","accounts":[{"id":"acct-1","providerId":"chime",
    "productId":"chime-checking","nickname":"Fictional account",
    "openingCents":10000,"origin":"manual"}],"entries":[],"nextId":2}
PASSWORD = "fictional only passphrase"

def refuses(call, code):
    try:
        call()
    except manual.Refusal as e:
        assert str(e) == code, (str(e), code)
        return
    raise AssertionError("Expected " + code)

def save(d, revision=0, session=SESSION):
    return manual.run(d, {"action":"save","expectedRevision":revision,"session":session})

def execute(d, command):
    return handoff.guarded_recovery(d, command, confirm_clients_closed=True)

def child(d):
    script = ("import sys; from pathlib import Path; "
              "sys.path.insert(0,sys.argv[1]); "
              "import banking_recovery_handoff_candidate as h\n"
              "with h.client_lifetime(Path(sys.argv[2])):\n"
              " print('READY',flush=True)\n"
              " sys.stdin.readline()\n")
    p = subprocess.Popen([sys.executable,"-B","-c",script,str(SCRIPTS),str(d)],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([p.stdout],[],[],10)[0], "child lease startup timeout"
        assert p.stdout.readline().strip() == "READY"
        return p
    except BaseException:
        p.kill()
        p.communicate(timeout=10)
        raise

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    d = root / "local"
    save(d)
    backup = archive.run(d,{"action":"create","expectedRevision":1,"confirmBackup":True})["backup"]
    changed = {**SESSION,"accounts":[{**SESSION["accounts"][0],"openingCents":20000}]}
    save(d,1,changed)
    restore = {"action":"restore","backupId":backup["backupId"],
        "expectedRevision":2,"expectedBackupSha256":backup["sha256"],"confirmRestore":True}
    original = (d/"manual-session.json").read_bytes()
    refuses(lambda:handoff.guarded_recovery(d,restore),"EXPLICIT_CLOSED_CLIENTS_REQUIRED")
    refuses(lambda:execute(d,{"action":"save"}),"INVALID_RECOVERY_HANDOFF")
    refuses(lambda:execute(d,{**restore,"extra":True}),"INVALID_RECOVERY_HANDOFF")
    p = child(d)
    try:
        with handoff.client_lifetime(d): # two shared holders
            refuses(lambda:execute(d,restore),"CLIENT_LEASE_BUSY")
        refuses(lambda:execute(d,restore),"CLIENT_LEASE_BUSY")
        assert (d/"manual-session.json").read_bytes()==original
        p.kill() # kernel releases the lease on process death
    finally:
        if p.poll() is None:
            p.kill()
        p.communicate(timeout=10)
    assert p.returncode < 0
    with handoff._lease(d, True):
        def attempt_client():
            with handoff.client_lifetime(d):
                raise AssertionError("unexpected client")
        refuses(attempt_client,"CLIENT_LEASE_BUSY")
        refuses(lambda:execute(d,restore),"CLIENT_LEASE_BUSY")
    inode=(d/handoff.LOCK_NAME).stat().st_ino
    receipt=execute(d,restore)
    assert receipt["newRevision"]==3
    assert manual.read_doc(d)["session"]==SESSION
    assert (d/handoff.LOCK_NAME).stat().st_ino==inode
    refuses(lambda:save(d,2,changed),"STALE_REVISION")
    refuses(lambda:execute(d,restore),"STALE_REVISION")
    # A fresh client must load the recovered revision while holding the lease.
    with handoff.client_lifetime(d):
        assert manual.read_doc(d)["revision"]==3

    # Damaged-file recovery keeps its explicit selection and revision floor.
    damaged=b'{"version":1,"revision":3,"session":null}\n'
    (d/"manual-session.json").write_bytes(damaged)
    preview=recovery.run(d,{"action":"preview","backupId":backup["backupId"]})
    cmd={"action":"recover","backupId":backup["backupId"],
         "expectedPrimarySha256":preview["primarySha256"],
         "expectedBackupSha256":backup["sha256"],"lastKnownRevision":3,
         "confirmRecovery":True,"confirmClientsClosed":True}
    with handoff.client_lifetime(d):
        refuses(lambda:execute(d,cmd),"CLIENT_LEASE_BUSY")
    assert (d/"manual-session.json").read_bytes()==damaged
    result=execute(d,cmd)
    assert result["newRevision"]==4
    assert (d/"recovery-quarantine"/result["quarantineId"]).read_bytes()==damaged

    # Real portable crypto + empty-destination import under lifetime lease.
    sealed=portable.run(d,{"action":"export","expectedRevision":4,
                           "password":PASSWORD,"confirmExport":True})
    dest=root/"destination"
    portable.run(dest,{"action":"prepare","confirmPrepare":True})
    f=dest/"portable"/sealed["portableId"]
    shutil.copyfile(d/"portable"/sealed["portableId"],f)
    f.chmod(0o600)
    view=portable.run(dest,{"action":"preview","portableId":f.name,"password":PASSWORD})
    request={"action":"import","portableId":f.name,"password":PASSWORD,
             "expectedSha256":view["sha256"],"expectedRevision":0,
             "confirmImport":True,"confirmClientsClosed":True}
    with handoff.client_lifetime(dest):
        refuses(lambda:execute(dest,request),"CLIENT_LEASE_BUSY")
    assert not (dest/"manual-session.json").exists()
    refuses(lambda:execute(dest,{**request,"confirmClientsClosed":False}),"EXPLICIT_IMPORT_REQUIRED")
    assert execute(dest,request)["newRevision"]==5
    assert manual.read_doc(dest)["session"]==SESSION
    refuses(lambda:execute(dest,{**request,"expectedRevision":5}),"DESTINATION_NOT_EMPTY")

    # Unsafe lock files refuse; no deletion/replacement to force entry.
    unsafe=root/"unsafe"
    unsafe.mkdir(mode=0o700)
    lock=unsafe/handoff.LOCK_NAME
    target=root/"target"
    target.write_bytes(b"unchanged")
    lock.symlink_to(target)
    def open_unsafe():
        with handoff.client_lifetime(unsafe):
            raise AssertionError("unsafe lease accepted")
    refuses(open_unsafe,"UNSAFE_CLIENT_LEASE")
    assert target.read_bytes()==b"unchanged" and lock.is_symlink()
    lock.unlink()
    lock.write_bytes(b"")
    lock.chmod(0o644)
    refuses(open_unsafe,"UNSAFE_CLIENT_LEASE")
    lock.chmod(0o600)
    os.link(lock,unsafe/"other")
    refuses(open_unsafe,"UNSAFE_CLIENT_LEASE")

for path in ("widgets/FinanceW.qml","widgets/FinanceBankingPane.qml",
             "widgets/FinanceBankingManualStorageControls.qml",
             "services/finance/FinanceBankingManualStore.qml",
             "scripts/finance/banking_manual_store.py",
             "scripts/finance/banking_manual_archive.py",
             "scripts/finance/banking_manual_recovery.py",
             "scripts/finance/banking_manual_portable.py"):
    assert "banking_recovery_handoff_candidate" not in (ROOT/path).read_text(),path
print("M4s3 PASS: real process lifetime exclusion, SIGKILL release, guarded restore/recovery/import, stale revision and no live integration")
