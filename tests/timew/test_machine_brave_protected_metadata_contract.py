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
    assert mode=="deny"
    path=Path(sockpath)
    connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    connection.bind(str(path))
    os.chmod(path,0o666)  # disposable CI only
    connection.listen(1)
    print("READY",flush=True)
    try:
        peer_socket,_=connection.accept()
        with peer_socket:
            result=broker.handle_once(peer_socket,protected_root=Path(archive))
        print(json.dumps({"fixture_request_succeeded":result}),flush=True)
    finally:
        connection.close()
        path.unlink(missing_ok=True)
    return 0


def _run_metadata(archive,payload):
    """Direct source-reader CI fixture under service UID, NOT socket auth."""
    assert os.geteuid()==SERVICE_UID
    try:
        request=broker.parse_request(json.dumps(json.loads(payload),separators=(",",":")).encode())
        result=broker.metadata_from_protected_root(Path(archive),request)
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0
    except (broker.BrokerRefusal,vault.VaultError,OSError,ValueError):
        print('{"status":"refused"}',flush=True)
        return 1

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
                 "MachineBraveSealedVault.py",
                 "MachineBraveArchiveAdmissionIntent.py"):
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
            response=_ask_server(test_root,archive,"deny",payload)
            assert response==broker.REFUSED
        # Correctly formatted foreign UID still cannot receive metadata
        # through the test-only simulated authorizer.
        wrong_uid=_ask_server(test_root,archive,"deny",LIST_REQ,
                              uid=FOREIGN_UID)
        assert wrong_uid==broker.REFUSED

        # Positive reader format is exercised DIRECTLY under protected UID.
        # No browser socket can grant metadata, even to a valid client.
        def service_metadata(req):
            return _child_command(["--metadata",str(archive),json.dumps(req)],uid=SERVICE_UID)
        listed_run=service_metadata(LIST_REQ)
        assert listed_run.returncode==0,listed_run.stderr
        listed=json.loads(listed_run.stdout)
        assert listed['record_count']==1
        assert listed['records'][0]['record_id']==RECORD_ID
        inspected_run=service_metadata(INSPECT_REQ)
        assert inspected_run.returncode==0,inspected_run.stderr
        inspected=json.loads(inspected_run.stdout)
        assert inspected['record']==listed['records'][0]
        for item in (listed,inspected):
            value=json.dumps(item)
            for secret in ("https://","encrypted-synthetic-payload","passphrase"):
                assert secret not in value
        assert _ask_server(test_root,archive,"deny",LIST_REQ)==broker.REFUSED
        assert _ask_server(test_root,archive,"deny",INSPECT_REQ)==broker.REFUSED
        assert path.read_bytes()==before

        # File owner and mode are vital. If the directory becomes
        # ordinary same-UID storage, the broker must not treat it as a
        # protected service-owned vault.
        os.chown(archive,BROWSER_UID,BROWSER_UID)
        assert service_metadata(LIST_REQ).returncode != 0
        os.chown(archive,SERVICE_UID,SERVICE_UID)
        archive.chmod(0o755)
        assert service_metadata(LIST_REQ).returncode != 0
        archive.chmod(0o700)
        os.chmod(path,0o644)
        assert service_metadata(LIST_REQ).returncode != 0
        os.chmod(path,0o600)
        symlink=archive/"dddddddd-dddd-4ddd-8ddd-dddddddddddd.json"
        symlink.symlink_to(path.name)
        assert service_metadata(LIST_REQ).returncode != 0
        symlink.unlink()
        orphan=archive/".tmp-incomplete"
        orphan.write_bytes(b"partial")
        assert service_metadata(LIST_REQ).returncode != 0
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
    if len(sys.argv)>=2 and sys.argv[1]=="--metadata":
        assert len(sys.argv)==4
        sys.exit(_run_metadata(sys.argv[2],sys.argv[3]))
    if len(sys.argv)>=2 and sys.argv[1]=="--direct":
        assert len(sys.argv)==3
        sys.exit(_run_direct(sys.argv[2]))
    assert len(sys.argv)==1
    main()
