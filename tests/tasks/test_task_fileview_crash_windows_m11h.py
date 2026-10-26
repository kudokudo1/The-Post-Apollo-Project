#!/usr/bin/env python3
"""M11h real crash-window tests for OS-owned *synthetic* FileView host.

No Quickshell launched: we simulate its atomic FileView rename on private
temporary JSON fixture data. Real separate Python hosts crash using
os._exit(86) at exact commit boundaries, then a new process must encounter
RECOVERY_REVIEW and NEVER receive write authority or stage admission.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
HOST=ROOT/"tests/tasks/fixtures/TaskFileViewOwnerHostM11g.py"
GENERATOR=ROOT/"tests/tasks/fixtures/m11e_fileview_fixture.py"
QML=ROOT/"services/projects/TaskFileViewHostBridgeM11g.qml"
WRITER="m11h-crash-owner-0001"
NEXT="m11h-restart-owner-0002"


def fixture(root,name):
    directory=root/name/"m11e-fileview-test"
    directory.mkdir(mode=0o700,parents=True)
    src=directory/"fixture-only.json"
    p=subprocess.run([sys.executable,"-B","-I",str(GENERATOR),"--file",str(src)],
                     capture_output=True,text=True,timeout=10)
    assert p.returncode==0,p.stderr
    return directory/"handoff-test.db",src


def boot(db,*,bootstrap=False,fault=None,owner=WRITER):
    args=[sys.executable,"-B","-I",str(HOST),
          "--db",str(db),"--writer-id",owner]
    if bootstrap: args.append("--bootstrap-fixture")
    if fault is not None: args.extend(["--m11h-test-fault",fault])
    p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,text=True,bufsize=1)
    msg=json.loads(p.stdout.readline())
    for key in ("liveWriterAuthorized","sqliteWriteAuthorized",
                "remoteWriteAuthorized","migrationAuthorized"):
        assert msg[key] is False,(key,msg)
    return p,msg


def request(p,rid,kind,**fields):
    p.stdin.write(json.dumps({"requestId":rid,"kind":kind,**fields})+"\n")
    p.stdin.flush()
    line=p.stdout.readline()
    assert line,(p.returncode,kind)
    reply=json.loads(line)
    assert reply["requestId"]==rid and reply["kind"]==kind,reply
    for key in ("liveWriterAuthorized","sqliteWriteAuthorized",
                "remoteWriteAuthorized","migrationAuthorized"):
        assert reply[key] is False,reply
    return reply


def crash_request(p,rid,kind,**fields):
    p.stdin.write(json.dumps({"requestId":rid,"kind":kind,**fields})+"\n")
    p.stdin.flush()
    p.wait(timeout=10)
    assert p.returncode==86,p.returncode
    assert p.stdout.read()=="", "No false success acknowledgment after crash"
    p.stdin.close()
    assert p.stderr.read()==""


def stop(p):
    p.stdin.close()
    p.wait(timeout=10)
    assert p.returncode==0,p.returncode
    assert p.stderr.read()==""


def simulate_atomic_save(target,raw):
    # Mimic FileView's temp-file + rename with only generated test bytes.
    assert target.name=="fixture-only.json"
    temporary=target.parent/"m11h-synthetic.tmp"
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as output:
        output.write(raw.encode())
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary,target)


def durable(db):
    with sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True) as dbconn:
        dbconn.row_factory=sqlite3.Row
        assert dbconn.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert dbconn.execute("PRAGMA user_version").fetchone()[0]==1
        rows=dbconn.execute("SELECT phase,epoch,pending_stage,owner_id "
                            "FROM authority WHERE id=1").fetchall()
        assert len(rows)==1
        return dict(rows[0])


def recovery(db,pending):
    fresh,hello=boot(db,owner=NEXT)
    assert hello["ok"] is True and hello["phase"]=="RECOVERY_REVIEW"
    assert hello["pending"] is pending
    assert hello["epoch"]==1
    assert hello["payload"] is None
    refused=request(fresh,1,"admit",stageId="m11h-should-never-rearm")
    assert refused["ok"] is False
    assert refused["status"]=="LEGACY_STAGE_FROZEN"
    assert refused["phase"]=="RECOVERY_REVIEW"
    stale=request(fresh,2,"verify",stageId="m11h-crashed-stage-0001")
    assert stale["ok"] is False
    assert stale["status"]=="STALE_STAGE_CALLBACK"
    assert stale["payload"] is None
    stop(fresh)
    return durable(db)


with tempfile.TemporaryDirectory(prefix="postapollo-m11h-crash-") as name:
    root=Path(name)

    # Crash immediately after durable stage admission but BEFORE sending a
    # receipt. It must not become a successful synthetic FileView write.
    db,src=fixture(root,"admitted-no-reply")
    original=src.read_bytes()
    p,hello=boot(db,bootstrap=True,fault="after_admit_commit")
    assert hello["ok"] and hello["phase"]=="JSON_ACTIVE"
    crash_request(p,1,"admit",stageId="m11h-crashed-stage-0001")
    prior=durable(db)
    assert prior["phase"]=="JSON_ACTIVE" and prior["pending_stage"]=="m11h-crashed-stage-0001"
    assert src.read_bytes()==original
    later=recovery(db,True)
    assert later["pending_stage"]=="m11h-crashed-stage-0001"

    # Crash AFTER exact FileView bytes were read but BEFORE committing a
    # settlement. The file advanced but durable pending stage persists.
    db,src=fixture(root,"readback-before-commit")
    p,hello=boot(db,bootstrap=True,fault="after_readback_before_settle")
    offer=request(p,1,"admit",stageId="m11h-crashed-stage-0001")
    assert offer["ok"] and offer["pending"]
    simulate_atomic_save(src,offer["payload"])
    crash_request(p,2,"verify",stageId="m11h-crashed-stage-0001")
    prior=durable(db)
    assert prior["phase"]=="JSON_ACTIVE" and prior["pending_stage"]
    assert json.loads(src.read_bytes())["revision"]==1
    recovery(db,True)

    # Crash AFTER COMMIT of successful settlement but BEFORE host reply.
    # Application has an ambiguous acknowledgment: never blindly replay.
    db,src=fixture(root,"settled-no-reply")
    p,hello=boot(db,bootstrap=True,fault="after_settle_commit")
    offer=request(p,1,"admit",stageId="m11h-crashed-stage-0001")
    simulate_atomic_save(src,offer["payload"])
    crash_request(p,2,"verify",stageId="m11h-crashed-stage-0001")
    prior=durable(db)
    assert prior["phase"]=="JSON_ACTIVE" and prior["pending_stage"] is None
    assert json.loads(src.read_bytes())["revision"]==1
    recovery(db,False)

    # Crash AFTER durable freeze commit but BEFORE freeze acknowledgment.
    db,src=fixture(root,"frozen-no-reply")
    p,hello=boot(db,bootstrap=True,fault="after_freeze_commit")
    crash_request(p,1,"freeze",expectedEpoch=0)
    prior=durable(db)
    assert prior["phase"]=="FREEZE_REQUESTED" and prior["epoch"]==1
    assert prior["pending_stage"] is None
    fresh,hello=boot(db,owner=NEXT)
    assert hello["phase"]=="RECOVERY_REVIEW" and hello["epoch"]==2
    assert not request(fresh,1,"admit",stageId="m11h-after-freeze-0001")["ok"]
    stop(fresh)

    # Unexpected crash before any save: even a valid fixture and old
    # JSON_ACTIVE record cannot be inherited as write authority.
    db,src=fixture(root,"unclean-idle")
    p,hello=boot(db,bootstrap=True)
    p.kill()
    p.wait(timeout=10)
    p.stdin.close()
    recovery(db,False)

    # A duplicated or malformed command while a stage is pending must not
    # produce a settlement, and a later process cannot clear that stage.
    db,src=fixture(root,"replayed-command")
    p,hello=boot(db,bootstrap=True)
    stage=request(p,1,"admit",stageId="m11h-crashed-stage-0001")
    assert stage["pending"]
    p.stdin.write(json.dumps({"requestId":1,"kind":"verify",
        "stageId":"m11h-crashed-stage-0001"})+"\n")
    p.stdin.flush()
    bad=json.loads(p.stdout.readline())
    assert not bad["ok"] and bad["status"]=="REPLAYED_REQUEST"
    p.wait(timeout=10)
    assert p.returncode==2
    p.stdin.close()
    assert src.read_bytes()==original
    recovery(db,True)

    # Fault instrumentation must NEVER be reachable by production QML.
    qml=QML.read_text()
    assert "--m11h-test-fault" not in qml
    assert "TaskFileViewOwnerHostM11g.py" in qml
    assert "TaskFileViewHostBridgeM11g" not in (ROOT/"shell.qml").read_text()
    assert "Quickshell.dataDir" not in qml
    assert "ApolloHubTodoStore" not in qml

print("M11h abrupt crash windows, ambiguous ACK and durable restart fences: PASS")
