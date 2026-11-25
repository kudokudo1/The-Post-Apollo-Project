#!/usr/bin/env python3
"""M4t3 CI-only real native Banking recovery lifecycle, no live configuration."""
import copy
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

from test_banking_client_bridge_m4t2 import ROOT, SCRIPTS, environment, directory, lease_free
import banking_manual_store as manual
import banking_manual_archive as archive
import banking_manual_portable as portable

PASSWORD = "fictional only M4t3 passphrase"
ORIGINAL = {"mode":"manual","accounts":[
    {"id":"acct-1","providerId":"chime","productId":"chime-checking",
     "nickname":"Fictional checking","openingCents":10000,"origin":"manual"},
    {"id":"acct-2","providerId":"cashapp","productId":"cash-balance",
     "nickname":"Fictional wallet","openingCents":5000,"origin":"manual"}],
    "entries":[
        {"id":"entry-3","accountId":"acct-1","amountCents":-1200,"date":"2026-01-01",
         "description":"Fictional transfer","origin":"manual","transferId":"transfer-5","transferSide":"out"},
        {"id":"entry-4","accountId":"acct-2","amountCents":1200,"date":"2026-01-01",
         "description":"Fictional transfer","origin":"manual","transferId":"transfer-5","transferSide":"in"}],
    "nextId":6}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(d, revision, session):
    return manual.run(d,{"action":"save","expectedRevision":revision,"session":session})

def main():
    if (os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("POST_APOLLO_BANKING_NATIVE_CI")!="1"
            or not os.environ.get("DISPLAY")):
        raise RuntimeError("DISPOSABLE_NATIVE_CI_REQUIRED")
    qs=shutil.which("qs") or shutil.which("quickshell")
    assert qs,"Quickshell missing"
    version=subprocess.run([qs,"--version"],text=True,capture_output=True,timeout=10)
    assert version.returncode==0 and "0.3.2" in version.stdout+version.stderr
    with tempfile.TemporaryDirectory(prefix="banking-m4t3-native-") as tmp:
        work=Path(tmp)
        (work/"fixture-only").write_text("M4T3\n")
        for rel in ("services/finance/FinanceBankingRevisionBridgeCandidate.qml",
                    "widgets/FinanceBankingAccountsPolicy.js"):
            target=work/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/rel,target)
            assert digest(target)==digest(ROOT/rel)
        shutil.copytree(SCRIPTS,work/"scripts/finance")
        shutil.copy2(ROOT/"tests/finance/fixtures/m4t3_recovery_driver.py",
                     work/"scripts/finance/m4t3_recovery_driver.py")
        shutil.copy2(ROOT/"tests/finance/fixtures/M4t3BankingRecoveryNative.qml",work/"shell.qml")
        env=environment(work)
        env["POST_APOLLO_BANKING_M4T3"]="CI_DISPOSABLE_ONLY"
        d=directory(env)
        source=work/"separate-source-device"
        assert save(source,0,ORIGINAL)["revision"]==1
        export=portable.run(source,{"action":"export","expectedRevision":1,
                                   "password":PASSWORD,"confirmExport":True})
        sealed=source/"portable"/export["portableId"]
        source_before=digest(source/"manual-session.json")
        assert b"Fictional transfer" not in sealed.read_bytes()
        assert PASSWORD.encode() not in sealed.read_bytes()
        assert save(d,0,ORIGINAL)["revision"]==1
        backup=archive.run(d,{"action":"create","expectedRevision":1,"confirmBackup":True})["backup"]
        backup_path=d/"backups"/backup["backupId"]
        portable.run(d,{"action":"prepare","confirmPrepare":True})
        copied=d/"portable"/sealed.name
        shutil.copyfile(sealed,copied)
        copied.chmod(0o600)
        assert digest(copied)==export["sha256"]
        before={p:digest(p) for p in (backup_path,copied,sealed)}
        changed=copy.deepcopy(ORIGINAL)
        changed["accounts"][0]["openingCents"]=20000
        assert save(d,1,changed)["revision"]==2
        p=subprocess.Popen([qs,"-p",str(work/"shell.qml"),"--no-color"],
            cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,errors="replace",start_new_session=True)
        try:
            output,_=p.communicate(timeout=105)
            if p.returncode==0 and "M4T3_NATIVE_PASS" in output:
                # Never let emergency cleanup hide a leaked client lock.
                lease_free(d)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL)
            output,_=p.communicate(timeout=10)
            print(output[-12000:])
            raise
        finally:
            try:
                os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
        print(output[-12000:])
        assert p.returncode==0 and "M4T3_NATIVE_FAIL" not in output and "M4T3_NATIVE_PASS" in output
        assert manual.read_doc(d)=={"version":1,"revision":6,"session":ORIGINAL}
        assert digest(source/"manual-session.json")==source_before
        assert {p:digest(p) for p in before}==before
        quarantines=list((d/"recovery-quarantine").glob("damaged-*.bin"))
        assert len(quarantines)==1
        assert quarantines[0].read_bytes()==b'{"version":1,"revision":5,"session":null}\n'
        assert quarantines[0].name=="damaged-"+digest(quarantines[0])+".bin"
        lease_free(d)
    for rel in ("shell.qml","widgets/FinanceW.qml","widgets/FinanceBankingPane.qml",
                "widgets/FinanceBankingManualStorageControls.qml"):
        assert "M4t3BankingRecoveryNative" not in (ROOT/rel).read_text()
        assert "m4t3_recovery_driver" not in (ROOT/rel).read_text()
    print("M4T3_REAL_QUICKSHELL_PASS // active-client refusal, exact backup restore, cross-root encrypted import, damaged recovery, transfer continuity, original copies unchanged")

if __name__=="__main__":
    main()
