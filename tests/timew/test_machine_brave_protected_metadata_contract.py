#!/usr/bin/env python3
"""CI-only privileged OS principal isolation and deny-only metadata seam tests.

Executed under passwordless sudo ONLY on disposable GitHub runner. Uses two
ephemeral numeric UIDs and an isolated tempfile. Never modifies local user
files, /etc/passwd, service units, SELinux policy, or real Brave profiles.
"""
from __future__ import annotations
import base64
import errno
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveProtectedMetadataContract as broker
import MachineBraveSealedVault as vault

BROWSER_UID=24101
SERVICE_UID=24102
FOREIGN_UID=24103
RECORD_ID="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TEST_SCRIPT_PATH=None  # CI fixture path for demoted process
LIST_REQ={"kind":broker.REQUEST_KIND,"action":broker.LIST,
          "challenge":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}
INSPECT_REQ={"kind":broker.REQUEST_KIND,"action":broker.INSPECT,
             "challenge":"cccccccc-cccc-4ccc-8ccc-cccccccccccc","record_id":RECORD_ID}


def _frame(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    return struct.pack("=I",len(raw))+raw


def _read_exact(sock,size):
    result=b""
    while len(result)<size:
        part=sock.recv(size-len(result))
        if not part:
            raise AssertionError("unexpected broker disconnect")
        result+=part
    return result


def _read_reply(sock):
    size=struct.unpack("=I",_read_exact(sock,4))[0]
    assert 0<size<=broker.MAX_RESPONSE
    return json.loads(_read_exact(sock,size))


def _as_uid(uid):
    os.setgroups([])
    os.setresgid(uid,uid,uid)
    os.setresuid(uid,uid,uid)


def _run_server(sockpath,archive,mode):
    assert os.geteuid()==SERVICE_UID
    assert mode in ("deny","synthetic")
    path=Path(sockpath)
    connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    connection.bind(str(path))
    os.chmod(path,0o666) # CI only, no production listener or unit
    connection.listen(1)
    print("READY",flush=True)
    try:
        peer_socket,_=connection.accept()
        with peer_socket:
            if mode=="deny":
                result=broker.handle_once(
                    peer_socket,protected_root=Path(archive))
            else:
                # Synthetic trust fixture, NOT a C3e process witness or
                # C5 user-consent receipt. Enforce a known kernel UID.
                def fixture_auth(peer,request,sha256):
                    return (peer.uid==BROWSER_UID and peer.gid==BROWSER_UID
                            and peer.pid>1 and len(sha256)==64 and
                            request["kind"]==broker.REQUEST_KIND)
                result=broker.handle_once(
                    peer_socket,protected_root=Path(archive),
                    test_only_grant=fixture_auth)
        print(json.dumps({"fixture_request_succeeded":result}),flush=True)
    finally:
        connection.close()
        path.unlink(missing_ok=True)
    return 0


def _run_client(sockpath,payload):
    assert os.geteuid() in (BROWSER_UID,FOREIGN_UID)
    request=json.loads(payload)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(4.0)
        sock.connect(sockpath)
        sock.sendall(_frame(request))
        response=_read_reply(sock)
    print(json.dumps(response,sort_keys=True),flush=True)
    return 0


def _run_direct(archive):
    assert os.geteuid()==BROWSER_UID
    archive=Path(archive)
    target=archive/(RECORD_ID+".json")
    result={}
    for name,fn in {
        "direct_read":lambda:target.open("rb").read(1),
        "direct_list":lambda:list(archive.iterdir()),
        "direct_unlink":lambda:target.unlink(),
        "direct_write":lambda:target.write_bytes(b"attack"),
        "direct_chmod":lambda:archive.chmod(0o755),
    }.items():
        try:
            fn()
        except PermissionError:
            result[name]="permission_denied"
        else:
            result[name]="UNSAFE_BYPASS"
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0


def _child_command(args,uid=None,timeout=12):
    def demote():
        if uid is not None:_as_uid(uid)
    return subprocess.run(
        [sys.executable,"-B","-I",str(TEST_SCRIPT_PATH or Path(__file__).resolve()),*args],
        capture_output=True,text=True,timeout=timeout,
        preexec_fn=demote if uid is not None else None)


def _ask_server(root,archive,mode,payload,uid=BROWSER_UID):
    sockpath=root/"metadata.sock"
    args=[sys.executable,"-B","-I",str(TEST_SCRIPT_PATH or Path(__file__).resolve()),
          "--server",str(sockpath),str(archive),mode]
    server=subprocess.Popen(
        args,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        preexec_fn=lambda:_as_uid(SERVICE_UID))
    try:
        ready=server.stdout.readline().strip()
        assert ready=="READY",("server failed to bind",ready,server.poll())
        client=_child_command(
            ["--client",str(sockpath),json.dumps(payload)],uid=uid)
        assert client.returncode==0,(client.stderr,client.stdout)
        answer=json.loads(client.stdout)
        stdout,stderr=server.communicate(timeout=6)
        assert server.returncode==0,(stdout,stderr)
        assert not stderr,stderr
        assert "fixture_request_succeeded" in stdout
        return answer
    finally:
        if server.poll() is None:
            server.kill()
            server.communicate(timeout=4)


def _b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _setup_archive(root):
    directory=root/"sealed"
    directory.mkdir(mode=0o700)
    record={
        "kind":vault.RECORD_KIND,"record_id":RECORD_ID,
        "created_at_utc":"2026-11-11T12:00:00+00:00",
        "envelope":{
            "kind":vault.ENVELOPE_KIND,"version":1,
            "algorithm":"AES-256-GCM","kdf":"PBKDF2-HMAC-SHA256",
            "iterations":600000,"salt":_b64(b"0123456789abcdef"),
            "nonce":_b64(b"0123456789ab"),"aad":vault.AAD,
            "ciphertext":_b64(b"encrypted-synthetic-payload-plus-gcm-tag")
        }
    }
    path=directory/(RECORD_ID+".json")
    path.write_text(json.dumps(record,sort_keys=True,
                               separators=(",",":"))+"\n")
    os.chown(directory,SERVICE_UID,SERVICE_UID)
    os.chown(path,SERVICE_UID,SERVICE_UID)
    directory.chmod(0o700)
    path.chmod(0o600)
    return directory,path


def main():
    if os.geteuid()!=0:
        raise RuntimeError("CI privileged UID isolation test must run as root")
    for uid in (BROWSER_UID,SERVICE_UID,FOREIGN_UID):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            pass
        else:
            raise RuntimeError("reserved CI fixture UID already assigned; refuse")
    test_root=Path(tempfile.mkdtemp(prefix="machine-ci-protected-metadata-"))
    assert test_root.parent==Path("/tmp")
    os.chown(test_root,SERVICE_UID,SERVICE_UID)
    test_root.chmod(0o755)  # service can create CI socket; browser can only traverse
    # The runner checkout is private to its owner, so demoted fixture UIDs
    # need disposable read-only copies of just the test and dependencies.
    global TEST_SCRIPT_PATH
    fixture_tests=test_root/"tests"/"timew"
    fixture_modules=test_root/"services"/"time"
    fixture_tests.mkdir(parents=True,mode=0o755)
    fixture_modules.mkdir(parents=True,mode=0o755)
    original=Path(__file__).resolve()
    TEST_SCRIPT_PATH=fixture_tests/original.name
    shutil.copyfile(original,TEST_SCRIPT_PATH)
    for name in ("MachineBraveProtectedMetadataContract.py",
                 "MachineBraveSealedVault.py"):
        shutil.copyfile(ROOT/"services"/"time"/name,fixture_modules/name)
    for path in (TEST_SCRIPT_PATH,*fixture_modules.iterdir()):
        path.chmod(0o644)
    try:
        archive,path=_setup_archive(test_root)
        before=path.read_bytes()

        # Kernel enforces the first security boundary independently of broker
        # protocol, process name, extension origin and claimed identity.
        direct=_child_command(["--direct",str(archive)],uid=BROWSER_UID)
        assert direct.returncode==0,direct.stderr
        result=json.loads(direct.stdout)
        assert set(result)=={
            "direct_read","direct_list","direct_unlink",
            "direct_write","direct_chmod"
        }
        assert set(result.values())=={"permission_denied"}
        assert path.read_bytes()==before

        # Deny-only broker refuses even structurally valid requests.
        denied=_ask_server(test_root,archive,"deny",LIST_REQ)
        assert denied==broker.REFUSED
        # A client cannot supply its own authenticated role, origin,
        # arbitrary archive path, or magic approval field.
        for payload in [
            {**LIST_REQ,"uid":SERVICE_UID},
            {**LIST_REQ,"origin":"chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"},
            {**LIST_REQ,"authorized":True},
            {**LIST_REQ,"path":str(archive)},
            {**INSPECT_REQ,"record_id":"../../etc/passwd"},
            {**INSPECT_REQ,"action":"DELETE"},
            {**LIST_REQ,"challenge":"wrong"},
        ]:
            response=_ask_server(test_root,archive,"synthetic",payload)
            assert response==broker.REFUSED
        # Correctly formatted foreign UID still cannot receive metadata
        # through the test-only simulated authorizer.
        wrong_uid=_ask_server(test_root,archive,"synthetic",LIST_REQ,
                              uid=FOREIGN_UID)
        assert wrong_uid==broker.REFUSED

        # Positive CI fixture explicitly does NOT claim real client
        # provenance or human consent. It exercises bounded metadata only.
        listed=_ask_server(test_root,archive,"synthetic",LIST_REQ)
        assert listed["status"]=="test_only_metadata_listed"
        assert listed["challenge"]==LIST_REQ["challenge"]
        assert listed["record_count"]==1
        assert listed["client_authenticated"] is False
        assert listed["operator_consent_verified"] is False
        assert listed["restore_allowed"] is False
        assert listed["safe_actions"]==[]
        assert listed["records"][0]["record_id"]==RECORD_ID
        inspected=_ask_server(test_root,archive,"synthetic",INSPECT_REQ)
        assert inspected["status"]=="test_only_metadata_inspected"
        assert inspected["record"]==listed["records"][0]
        assert inspected["client_authenticated"] is False
        assert inspected["operator_consent_verified"] is False
        for obj in (listed,inspected):
            output=json.dumps(obj)
            for forbidden in (
                "ciphertext\":", "https://","passphrase","envelope\":",
                "encrypted-synthetic-payload","/tmp/machine-ci"
            ):
                assert forbidden not in output,forbidden
        assert path.read_bytes()==before

        # File owner and mode are vital. If the directory becomes
        # ordinary same-UID storage, the broker must not treat it as a
        # protected service-owned vault.
        os.chown(archive,BROWSER_UID,BROWSER_UID)
        assert _ask_server(test_root,archive,"synthetic",LIST_REQ)==broker.REFUSED
        os.chown(archive,SERVICE_UID,SERVICE_UID)
        archive.chmod(0o755)
        assert _ask_server(test_root,archive,"synthetic",LIST_REQ)==broker.REFUSED
        archive.chmod(0o700)
        os.chmod(path,0o644)
        assert _ask_server(test_root,archive,"synthetic",LIST_REQ)==broker.REFUSED
        os.chmod(path,0o600)
        symlink=archive/"dddddddd-dddd-4ddd-8ddd-dddddddddddd.json"
        symlink.symlink_to(path.name)
        assert _ask_server(test_root,archive,"synthetic",LIST_REQ)==broker.REFUSED
        symlink.unlink()
        orphan=archive/".tmp-incomplete"
        orphan.write_bytes(b"partial")
        assert _ask_server(test_root,archive,"synthetic",LIST_REQ)==broker.REFUSED
        orphan.unlink()

        assert path.read_bytes()==before
    finally:
        assert test_root.parent==Path("/tmp")
        assert test_root.name.startswith("machine-ci-protected-metadata-")
        shutil.rmtree(test_root)
    print("MACHINE protected broker: kernel distinct-UID direct bypass denied; synthetic metadata protocol PASS")


if __name__=="__main__":
    if len(sys.argv)>=2 and sys.argv[1]=="--server":
        assert len(sys.argv)==5
        sys.exit(_run_server(sys.argv[2],sys.argv[3],sys.argv[4]))
    if len(sys.argv)>=2 and sys.argv[1]=="--client":
        assert len(sys.argv)==4
        sys.exit(_run_client(sys.argv[2],sys.argv[3]))
    if len(sys.argv)>=2 and sys.argv[1]=="--direct":
        assert len(sys.argv)==3
        sys.exit(_run_direct(sys.argv[2]))
    assert len(sys.argv)==1
    main()
