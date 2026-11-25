#!/usr/bin/env python3
"""M4t4 native controls in a private temporary XDG tree; no real records."""
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from test_banking_client_bridge_m4t2 import ROOT, SCRIPTS, SESSION, environment, directory
import banking_manual_store as manual
import banking_manual_archive as archive
import banking_manual_portable as portable

PASSWORD="fictional M4t4 passphrase only"

def timeout_witness(qs,work,env):
    # Deliberately hang only copied disposable helpers. No financial command
    # executes in this second launch; first launch uses the actual helpers.
    for name in ("banking_manual_archive.py","banking_manual_portable.py"):
        (work/"scripts/finance"/name).write_text(
            "import os,sys,time\\n"
            "from pathlib import Path\\n"
            "Path(os.environ['XDG_DATA_HOME'],Path(__file__).stem+'.pid').write_text(str(os.getpid()))\\n"
            "sys.stdin.buffer.readline()\\n"
            "time.sleep(120)\\n")
    env={**env,"BANKING_M4T5_TIMEOUT_FIXTURE":"1"}
    p=subprocess.Popen([qs,"-p",str(work/"shell.qml"),"--no-color"],
        cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        text=True,errors="replace",start_new_session=True)
    try:
        output,_=p.communicate(timeout=60)
        print(output[-12000:])
        assert p.returncode==0 and "M4T5_TIMEOUT_PASS" in output and "M4T4_NATIVE_FAIL" not in output
        # Verify actual child exit before emergency process-group cleanup.
        for name in ("banking_manual_archive","banking_manual_portable"):
            pid=int((Path(env["XDG_DATA_HOME"])/(name+".pid")).read_text())
            try:
                os.kill(pid,0)
            except ProcessLookupError:
                pass
            else:
                raise AssertionError("timed-out child still exists")
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
    assert PASSWORD not in output
    print("M4T5_REAL_TIMEOUT_PASS // both actual deadlines, child exit and no reuse")

def main():
    if (os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("POST_APOLLO_BANKING_NATIVE_CI")!="1"
            or not os.environ.get("DISPLAY")):
        raise RuntimeError("DISPOSABLE_NATIVE_CI_REQUIRED")
    qs=shutil.which("qs") or shutil.which("quickshell")
    assert qs
    v=subprocess.run([qs,"--version"],capture_output=True,text=True,timeout=10)
    assert v.returncode==0 and "0.3.2" in v.stdout+v.stderr
    with tempfile.TemporaryDirectory(prefix="banking-m4t4-native-") as tmp:
        work=Path(tmp)
        for rel in ("widgets/FinanceBankingBackupControlsCandidate.qml",
                    "widgets/FinanceBankingPortableControlsCandidate.qml",
                    "widgets/FinanceBankingBackupControlsPolicy.js",
                    "widgets/FinanceBankingPortableControlsPolicy.js",
                    "services/finance/FinanceBankingBackupCandidateService.qml",
                    "services/finance/FinanceBankingPortableCandidateService.qml"):
            target=work/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/rel,target)
            assert target.read_bytes()==(ROOT/rel).read_bytes()
        shutil.copytree(ROOT/"components",work/"components")
        shutil.copytree(SCRIPTS,work/"scripts/finance")
        shutil.copy2(ROOT/"tests/finance/fixtures/M4t4BankingControlsNative.qml",work/"shell.qml")
        env=environment(work)
        d=directory(env)
        seeded=manual.run(d,{"action":"save","expectedRevision":0,"session":SESSION})
        primary=d/"manual-session.json"
        before=hashlib.sha256(primary.read_bytes()).hexdigest()
        p=subprocess.Popen([qs,"-p",str(work/"shell.qml"),"--no-color"],
            cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,errors="replace",start_new_session=True)
        try:
            output,_=p.communicate(timeout=60)
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
        assert p.returncode==0 and "M4T4_NATIVE_FAIL" not in output and "M4T4_NATIVE_PASS" in output
        assert manual.read_doc(d)==seeded
        assert hashlib.sha256(primary.read_bytes()).hexdigest()==before
        assert archive.run(d,{"action":"list"})["backups"]==[]
        sealed=list((d/"portable").glob("banking-*.sealed.json"))
        assert len(sealed)==1
        raw=sealed[0].read_bytes()
        assert PASSWORD.encode() not in raw and b"Fictional account" not in raw
        view=portable.run(d,{"action":"preview","portableId":sealed[0].name,"password":PASSWORD})
        assert view["sourceRevision"]==1 and view["accountCount"]==1 and view["entryCount"]==0
        assert view["ciphertextAuthenticated"] and not view["originAuthenticated"]
        assert PASSWORD not in output and "M4T5_CONTEXT_PASS" in output
        timeout_witness(qs,work,env)
        assert hashlib.sha256(primary.read_bytes()).hexdigest()==before
        assert len(list((d/"portable").glob("banking-*.sealed.json")))==1
    print("M4T4_REAL_QUICKSHELL_PASS // real native controls, two-click backup create/delete, cancelled actions, masked input clearing, encrypted export and authenticated preview, primary unchanged")

if __name__=="__main__":
    main()
