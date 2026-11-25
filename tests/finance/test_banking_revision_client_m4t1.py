#!/usr/bin/env python3
"""M4t1 disposable Linux revision-bound client lifecycle tests."""
import copy
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/finance"
sys.path.insert(0, str(SCRIPTS))
import banking_manual_store as manual
import banking_manual_archive as archive
import banking_recovery_handoff_candidate as handoff
import banking_revision_client_candidate as candidate

SESSION = {"mode":"manual","accounts":[{"id":"acct-1","providerId":"chime",
    "productId":"chime-checking","nickname":"Fictional account",
    "openingCents":10000,"origin":"manual"}],"entries":[],"nextId":2}
CHANGED = copy.deepcopy(SESSION)
CHANGED["accounts"][0]["openingCents"] = 20000

def refuses(call, code):
    try:
        call()
    except manual.Refusal as e:
        assert str(e) == code, (str(e), code)
        return
    raise AssertionError("Expected " + code)

with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "banking"
    with candidate.revision_client(d) as a:
        assert a.snapshot() == manual.empty_doc()
        refuses(lambda:a.save(0,SESSION),"CLIENT_CONFIRMATION_REQUIRED")
        initial = a.save(0,SESSION,confirm=True)
        assert initial["revision"] == 1
        initial["session"]["accounts"][0]["openingCents"] = 999
        assert a.snapshot()["session"] == SESSION
        backup = archive.run(d,{"action":"create","expectedRevision":1,
                                "confirmBackup":True})["backup"]
        with candidate.revision_client(d) as b:
            assert b.snapshot()["session"] == SESSION
            assert a.save(1,CHANGED,confirm=True)["revision"] == 2
            # The other client's revision cannot advance on a refresh.
            refuses(b.refresh,"CLIENT_BASELINE_CHANGED")
            refuses(lambda:b.save(2,SESSION,confirm=True),"CLIENT_RELOAD_REQUIRED")
            refuses(b.snapshot,"CLIENT_RELOAD_REQUIRED")
            assert manual.read_doc(d)["session"] == CHANGED
        # Caller cannot attach stale UI state to a newer revision via refresh.
        refuses(lambda:a.save(1,SESSION,confirm=True),"CLIENT_EXPECTED_REVISION_MISMATCH")
        assert a.refresh()["revision"] == 2
        restore={"action":"restore","backupId":backup["backupId"],
            "expectedRevision":2,"expectedBackupSha256":backup["sha256"],"confirmRestore":True}
        refuses(lambda:handoff.guarded_recovery(d,restore,confirm_clients_closed=True),
                "CLIENT_LEASE_BUSY")
    refuses(a.snapshot,"CLIENT_CLOSED")

    # Actual independent process retains the lease during its loaded session.
    script=("import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
            "import banking_revision_client_candidate as c\n"
            "with c.revision_client(Path(sys.argv[2])) as client:\n"
            " print(client.snapshot()['revision'],flush=True)\n"
            " sys.stdin.readline()\n")
    p=subprocess.Popen([sys.executable,"-B","-c",script,str(SCRIPTS),str(d)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert select.select([p.stdout],[],[],10)[0], "client startup timeout"
        assert p.stdout.readline().strip()=="2"
        refuses(lambda:handoff.guarded_recovery(d,restore,confirm_clients_closed=True),
                "CLIENT_LEASE_BUSY")
        p.communicate(input="\n",timeout=10)
        assert p.returncode==0
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate(timeout=10)
    assert handoff.guarded_recovery(d,restore,confirm_clients_closed=True)["newRevision"]==3
    with candidate.revision_client(d) as fresh:
        assert fresh.snapshot()["session"]==SESSION
        assert fresh.snapshot()["revision"]==3
        # Same revision, different bytes representing different data.
        manual.write_doc(d,{"version":1,"revision":3,"session":CHANGED})
        refuses(lambda:fresh.save(3,SESSION,confirm=True),"CLIENT_BASELINE_CHANGED")
        refuses(fresh.refresh,"CLIENT_RELOAD_REQUIRED")
        assert manual.read_doc(d)["session"]==CHANGED

    # Race after pre-read: existing writer CAS refuses the stale request.
    with candidate.revision_client(d) as race:
        real_run=manual.run
        def intervening(directory,request):
            real_run(directory,{"action":"save","expectedRevision":3,"session":SESSION})
            return real_run(directory,request)
        with patch.object(manual,"run",side_effect=intervening):
            refuses(lambda:race.save(3,CHANGED,confirm=True),"STALE_REVISION")
        refuses(race.refresh,"CLIENT_RELOAD_REQUIRED")
        assert manual.read_doc(d)["revision"]==4

    # Uncertain commit cannot be retried in the same client context.
    with candidate.revision_client(d) as uncertain:
        def lost_receipt(directory,request):
            real_run(directory,request)
            raise manual.Refusal("INJECTED_POSTCOMMIT_FAILURE")
        with patch.object(manual,"run",side_effect=lost_receipt):
            refuses(lambda:uncertain.save(4,CHANGED,confirm=True),"INJECTED_POSTCOMMIT_FAILURE")
        refuses(lambda:uncertain.save(5,SESSION,confirm=True),"CLIENT_RELOAD_REQUIRED")
    with candidate.revision_client(d) as resolved:
        assert resolved.snapshot()["revision"]==5
        assert resolved.snapshot()["session"]==CHANGED
        refuses(lambda:resolved.clear(5),"CLIENT_CONFIRMATION_REQUIRED")
        assert resolved.clear(5,confirm=True)["revision"]==6
        assert resolved.snapshot()["session"]==manual.empty_session()

    # Signed QML integer ceiling cannot silently overflow.
    manual.write_doc(d,{"version":1,"revision":candidate.MAX_REVISION,"session":SESSION})
    with candidate.revision_client(d) as capped:
        refuses(lambda:capped.save(candidate.MAX_REVISION,CHANGED,confirm=True),
                "CLIENT_REVISION_OUT_OF_RANGE")
    manual.write_doc(d,{"version":1,"revision":candidate.MAX_REVISION+1,"session":SESSION})
    def oversized():
        with candidate.revision_client(d):
            raise AssertionError("oversize revision loaded")
    refuses(oversized,"CLIENT_REVISION_OUT_OF_RANGE")

for path in ("widgets/FinanceW.qml","widgets/FinanceBankingPane.qml",
             "widgets/FinanceBankingManualStorageControls.qml",
             "services/finance/FinanceBankingManualStore.qml",
             "scripts/finance/banking_manual_store.py"):
    assert "banking_revision_client_candidate" not in (ROOT/path).read_text(),path
print("M4t1 PASS: immutable revision baseline, concurrent clients, process lease, CAS race, uncertain write, clear and no live mount")
