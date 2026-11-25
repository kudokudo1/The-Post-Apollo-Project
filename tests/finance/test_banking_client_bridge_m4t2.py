#!/usr/bin/env python3
"""M4t2 real wire protocol tests; optional CI-only native Quickshell witness."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=ROOT/"scripts/finance"
sys.path.insert(0,str(SCRIPTS))
import banking_manual_store as manual
import banking_recovery_handoff_candidate as handoff

PREFIX="FINANCEW_BANKING_CLIENT "
SESSION={"mode":"manual","accounts":[{"id":"acct-1","providerId":"chime",
    "productId":"chime-checking","nickname":"Fictional account","openingCents":10000,
    "origin":"manual"}],"entries":[],"nextId":2}

def environment(work):
    env=dict(os.environ)
    for key,name in (("HOME","home"),("XDG_CONFIG_HOME","config"),("XDG_DATA_HOME","data"),
                     ("XDG_STATE_HOME","state"),("XDG_CACHE_HOME","cache"),("XDG_RUNTIME_DIR","runtime")):
        p=work/name
        p.mkdir(mode=0o700)
        env[key]=str(p)
    env.update(GITHUB_ACTIONS="true",POST_APOLLO_BANKING_M4T2="CI_DISPOSABLE_ONLY",
               QT_QPA_PLATFORM="xcb",QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
               WAYLAND_DISPLAY="",NO_COLOR="1")
    for key in ("SWAYSOCK","I3SOCK","PYTHONPATH","PYTHONHOME"):
        env.pop(key,None)
    return env

def directory(env):
    return Path(env["XDG_DATA_HOME"])/"post-apollo/finance/banking-manual"

def lease_free(d):
    with handoff._lease(d,True):
        pass

def wire():
    with tempfile.TemporaryDirectory(prefix="banking-m4t2-wire-") as tmp:
        env=environment(Path(tmp))
        d=directory(env)
        cmd=[sys.executable,"-B",str(SCRIPTS/"banking_client_bridge_candidate.py")]
        def receive(p):
            assert select.select([p.stdout],[],[],10)[0], "wire timeout"
            line=p.stdout.readline()
            assert line.startswith(PREFIX),repr(line)
            return json.loads(line[len(PREFIX):])
        def start():
            p=subprocess.Popen(cmd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,text=True)
            children.append(p)
            return p,receive(p)
        def send(p,r):
            p.stdin.write(json.dumps(r)+"\n")
            p.stdin.flush()
        def req(hello,seq,action,rev,**extra):
            return dict(generation=hello["generation"],sequence=seq,action=action,
                        expectedRevision=rev,**extra)
        def refused(p):
            out,err=p.communicate(timeout=10)
            assert p.returncode==1 and not out and err=="FINANCEW_BANKING_CLIENT_REFUSED\n"
        children=[]
        try:
            p,a=start()
            q,b=start()
            assert a["kind"]=="ready" and a["document"]==manual.empty_doc()
            assert a["generation"]!=b["generation"]
            try:
                lease_free(d)
            except manual.Refusal as e:
                assert str(e)=="CLIENT_LEASE_BUSY"
            else:
                raise AssertionError("live lease not retained")
            send(p,req(a,1,"save",0,session=SESSION,confirm=True))
            assert receive(p)["document"]["revision"]==1
            send(q,req(b,1,"refresh",0))
            refused(q)
            send(p,req(a,2,"refresh",1))
            assert receive(p)["document"]["session"]==SESSION
            send(p,req(a,3,"close",1))
            assert receive(p)==dict(kind="result",generation=a["generation"],sequence=3,action="close")
            p.communicate(timeout=10)
            assert p.returncode==0
            lease_free(d)
            for change in ({"generation":a["generation"]},{"sequence":2},{"expectedRevision":0},
                           {"action":"import"},{"extra":True}):
                x,h=start()
                send(x,{**req(h,1,"refresh",1),**change})
                refused(x)
                lease_free(d)
            x,h=start()
            x.kill()
            x.communicate(timeout=10)
            lease_free(d)
            x,h=start()
            x.communicate(timeout=10) # EOF
            assert x.returncode==0
            lease_free(d)
            assert manual.read_doc(d)["session"]==SESSION
        finally:
            for p in children:
                if p.poll() is None:
                    p.kill()
                    p.communicate(timeout=10)
        denied=subprocess.run(cmd,input="",text=True,capture_output=True,
            env={**env,"POST_APOLLO_BANKING_M4T2":""},timeout=10)
        assert denied.returncode==1 and not denied.stdout
    for path in ("shell.qml","widgets/FinanceW.qml","widgets/FinanceBankingPane.qml",
                 "widgets/FinanceBankingManualStorageControls.qml"):
        assert "FinanceBankingRevisionBridgeCandidate" not in (ROOT/path).read_text(),path
    print("M4T2_WIRE_PASS")

def native():
    if (os.environ.get("GITHUB_ACTIONS")!="true"
            or os.environ.get("POST_APOLLO_BANKING_NATIVE_CI")!="1"
            or not os.environ.get("DISPLAY")):
        raise RuntimeError("DISPOSABLE_NATIVE_CI_REQUIRED")
    qs=shutil.which("qs") or shutil.which("quickshell")
    assert qs,"Quickshell missing"
    version=subprocess.run([qs,"--version"],text=True,capture_output=True,timeout=10)
    assert version.returncode==0 and "0.3.2" in version.stdout+version.stderr
    with tempfile.TemporaryDirectory(prefix="banking-m4t2-native-") as tmp:
        work=Path(tmp)
        for rel in ("services/finance/FinanceBankingRevisionBridgeCandidate.qml",
                    "widgets/FinanceBankingAccountsPolicy.js"):
            target=work/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/rel,target)
        shutil.copytree(SCRIPTS,work/"scripts/finance")
        shutil.copy2(ROOT/"tests/finance/fixtures/M4t2BankingNative.qml",work/"shell.qml")
        env=environment(work)
        p=subprocess.Popen([qs,"-p",str(work/"shell.qml"),"--no-color"],
            cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,errors="replace",start_new_session=True)
        try:
            output,_=p.communicate(timeout=60)
            # Check before process-group cleanup so cleanup cannot hide a leak.
            if p.returncode==0 and "M4T2_NATIVE_PASS" in output:
                lease_free(directory(env))
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
        assert p.returncode==0 and "M4T2_NATIVE_FAIL" not in output and "M4T2_NATIVE_PASS" in output
        d=directory(env)
        assert manual.read_doc(d)=={"version":1,"revision":2,"session":manual.empty_session()}
        lease_free(d)
        print("M4T2_REAL_QUICKSHELL_PASS // correlated writes, stale refusal, clean close, disable, fresh generation and released lease")

if __name__=="__main__":
    if sys.argv[1:]==["--native"]:
        native()
    elif not sys.argv[1:]:
        wire()
    else:
        raise SystemExit("unknown test mode")
