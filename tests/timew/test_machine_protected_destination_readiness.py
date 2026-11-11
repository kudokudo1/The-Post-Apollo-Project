#!/usr/bin/env python3
"""MACHINE // real kernel read-only protected destination preflight CI.

Root used ONLY by a disposable GitHub Actions fixture; inspected data and
test principal IDs are synthetic. No workstation/root deployment support.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineBraveSealedVault as vault
import MachineBraveProtectedDestinationReadiness as readiness

BROWSER = 24311
SERVICE = 24312
FOREIGN = 24313
A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

def sealed(identifier, marker):
    obj={
        "kind":vault.RECORD_KIND,"record_id":identifier,
        "created_at_utc":"2026-11-11T19:00:00+00:00",
        "envelope":{
            "kind":vault.ENVELOPE_KIND,"version":1,
            "algorithm":"AES-256-GCM","kdf":"PBKDF2-HMAC-SHA256",
            "iterations":600000,"salt":b64(b"0123456789abcdef"),
            "nonce":b64(b"0123456789ab"),"aad":vault.AAD,
            "ciphertext":b64(b"synthetic sealed bytes "+marker+b" fake GCM tag")
        }
    }
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    assert vault._record(raw,identifier)==obj
    return raw

SERVICE_CODE = r'''
import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import MachineBraveProtectedDestinationReadiness as readiness
from MachineBraveSealedVault import VaultError
path=Path(sys.argv[2])
mode=sys.argv[3]
try:
    if mode=="path":
        value=readiness.inspect_trusted_path_for_fixture(path)
    elif mode=="fd":
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:value=readiness.inspect_pinned_fd(fd)
        finally:os.close(fd)
    elif mode=="badfd":
        value=readiness.inspect_pinned_fd(0)
    else:
        raise RuntimeError("unknown fixture action")
except (readiness.ReadinessRefusal,VaultError,OSError,ValueError):
    print(json.dumps({"status":"refused"}))
    sys.exit(2)
print(json.dumps(value,sort_keys=True))
'''

DIRECT_CODE = r'''
import pathlib,sys
target=pathlib.Path(sys.argv[1])
operation=sys.argv[2]
file=target/("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa.json")
try:
    if operation=="list":list(target.iterdir())
    elif operation=="read":file.read_bytes()
    elif operation=="append":
        with file.open("ab") as f:f.write(b"attack")
    elif operation=="unlink":file.unlink()
    elif operation=="chmod":target.chmod(0o755)
    elif operation=="create":(target/"intruder.json").write_bytes(b"attack")
    else:raise RuntimeError("invalid test action")
except PermissionError:
    print("denied")
else:
    print("BYPASS")
'''

def demote(uid):
    def do():
        os.setgroups([])
        os.setresgid(uid,uid,uid)
        os.setresuid(uid,uid,uid)
    return do

def child(uid,code,*args):
    r=subprocess.run([sys.executable,"-B","-I","-c",code,*map(str,args)],
                     capture_output=True,text=True,timeout=9,preexec_fn=demote(uid))
    assert not r.stderr,r.stderr
    return r

def inspection(modules,target,mode="path"):
    child_result=child(SERVICE,SERVICE_CODE,modules,target,mode)
    assert child_result.returncode in (0,2),child_result.stdout
    return child_result.returncode,json.loads(child_result.stdout)

def rejected(modules,target,mode="path"):
    code,output=inspection(modules,target,mode)
    assert code==2,output
    assert output=={"status":"refused"}

def write_record(target,identifier,raw):
    item=target/(identifier+".json")
    item.write_bytes(raw)
    os.chown(item,SERVICE,SERVICE)
    item.chmod(0o600)
    return item

def assert_flags(out):
    assert out["status"]=="ci_only_protected_destination_observed"
    assert out["read_only"] is True
    for name in ("path_ancestry_authenticated","kernel_cross_uid_isolation_verified",
                 "selinux_policy_verified","backup_verified","client_authenticated",
                 "operator_consent_verified","migration_authorized","restore_allowed"):
        assert out[name] is False,(name,out[name])
    assert out["safe_actions"]==[]
    serial=json.dumps(out)
    for leaked in ('"ciphertext":','"envelope":','"nonce":',
                   "synthetic sealed bytes","https://","passphrase"):
        assert leaked not in serial

def main():
    assert sys.platform.startswith("linux")
    assert os.geteuid()==0,"Run only as root on disposable GitHub Actions CI"
    for uid in (BROWSER,SERVICE,FOREIGN):
        try: pwd.getpwuid(uid)
        except KeyError: continue
        raise RuntimeError("Fixture UID is a real account; stop")

    base=Path(tempfile.mkdtemp(prefix="machine-target-readiness-ci-"))
    assert base.parent==Path("/tmp")
    base.chmod(0o711)
    try:
        modules=base/"modules"
        modules.mkdir(mode=0o755)
        for name in ("MachineBraveProtectedDestinationReadiness.py",
                     "MachineBraveSealedVault.py"):
            original=ROOT/"services/time"/name
            copied=modules/name
            shutil.copyfile(original,copied)
            copied.chmod(0o644)
        target=base/"sealed"
        target.mkdir(mode=0o700)
        os.chown(target,SERVICE,SERVICE)
        target.chmod(0o700)

        # An empty but existing protected root is observable and creates
        # no files. This does NOT mean migration is approved.
        rc,empty=inspection(modules,target)
        assert rc==0
        assert_flags(empty)
        assert empty["observation"]["record_count"]==0
        assert empty["observation"]["records"]==[]
        assert not list(target.iterdir())
        assert inspection(modules,target,"fd")==inspection(modules,target)

        first=sealed(A,b"A")
        second=sealed(B,b"B")
        file_a=write_record(target,A,first)
        file_b=write_record(target,B,second)
        before={p.name:(p.read_bytes(),p.stat().st_mode,p.stat().st_ino)
                for p in (file_a,file_b)}
        rc,seen=inspection(modules,target)
        assert rc==0
        assert_flags(seen)
        assert seen["observation"]["record_count"]==2
        assert seen["observation"]["total_sealed_bytes"]==len(first)+len(second)
        assert [r["record_id"] for r in seen["observation"]["records"]]==[A,B]
        assert seen["observation"]["records"][0]["sha256"]==hashlib.sha256(first).hexdigest()
        assert seen["observation"]["records"][1]["sha256"]==hashlib.sha256(second).hexdigest()
        assert seen==inspection(modules,target)[1]
        assert seen==inspection(modules,target,"fd")[1]

        # Real kernel denial, not a mocked PermissionError.
        for uid in (BROWSER,FOREIGN):
            for op in ("list","read","append","unlink","chmod","create"):
                attack=child(uid,DIRECT_CODE,target,op)
                assert attack.returncode==0
                assert attack.stdout.strip()=="denied",(uid,op,attack.stdout)
        assert {p.name:(p.read_bytes(),p.stat().st_mode,p.stat().st_ino)
                for p in (file_a,file_b)}==before

        # This API cannot run as root, even when root can read the data.
        try:
            readiness.inspect_trusted_path_for_fixture(target)
        except readiness.ReadinessRefusal:
            pass
        else:raise AssertionError("root was accepted as service identity")

        # Refuse missing path and user-supplied final symlink.
        rejected(modules,base/"missing")
        link=base/"link-to-sealed"
        link.symlink_to(target.name,target_is_directory=True)
        rejected(modules,link)
        assert link.is_symlink()
        link.unlink()

        # Each misconfiguration is verified directly under service UID.
        target.chmod(0o755)
        rejected(modules,target)
        target.chmod(0o700)
        os.chown(target,BROWSER,BROWSER)
        rejected(modules,target)
        os.chown(target,SERVICE,SERVICE)
        file_a.chmod(0o644)
        rejected(modules,target)
        file_a.chmod(0o600)
        os.chown(file_a,BROWSER,BROWSER)
        rejected(modules,target)
        os.chown(file_a,SERVICE,SERVICE)
        alias=target/(C+".json")
        os.link(file_a,alias)
        rejected(modules,target)
        alias.unlink()
        alias.symlink_to(file_a.name)
        rejected(modules,target)
        alias.unlink()
        orphan=target/".tmp-incomplete"
        orphan.write_bytes(b"unfinished")
        rejected(modules,target)
        orphan.unlink()
        unexpected=target/"NOTES"
        unexpected.write_text("not a sealed record")
        rejected(modules,target)
        unexpected.unlink()

        # Invalid envelope or duplicate JSON keys fail closed.
        file_b.write_bytes(b'{"kind":"wrong"}\n')
        rejected(modules,target)
        file_b.write_bytes(second)
        assert inspection(modules,target)[1]==seen

        # No mutation, no source data URLs, no ready/grant flag.
        assert {p.name:(p.read_bytes(),p.stat().st_mode,p.stat().st_ino)
                for p in (file_a,file_b)}==before
        script=(ROOT/"services/time/MachineBraveProtectedDestinationReadiness.py").read_text()
        for forbidden in ("subprocess.","os.chown(","os.chmod(","os.unlink(",
                          "os.mkdir(","vault.put(","vault.delete(", "socket.bind("):
            assert forbidden not in script,forbidden
        assert "migration_authorized" in script
        assert inspection(modules,target,"badfd")[0]==2
    finally:
        assert base.parent==Path("/tmp")
        assert base.name.startswith("machine-target-readiness-ci-")
        shutil.rmtree(base)
    print("MACHINE protected destination readiness: service-UID inspection, actual browser UID denial, unsafe file refusal and no writes PASS")

if __name__=="__main__":
    main()
