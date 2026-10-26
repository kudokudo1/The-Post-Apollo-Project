#!/usr/bin/env python3
"""M11g disposable OS-owned synthetic FileView test host, NOT a TASKS writer.

Lifetime M10p flock + durable stage reservation. The *host*, rather than a
QML callback boolean, verifies exact synthetic fixture bytes before settle.
Bootstrap is explicit and only for a new private m11e-fileview-test folder.
No real TASKS path, SQLite task mutation, network, transport or auto-rearm.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

ROOT=Path(__file__).resolve().parents[3]
AUTH_FILE=ROOT/"tests/tasks/fixtures/TaskSqliteWriterAuthorityFixture.py"
spec=importlib.util.spec_from_file_location("m11g_m10p_authority",AUTH_FILE)
auth=importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)
AdmissionError=auth.AdmissionError
MARK="M11E_SYNTHETIC_ONLY"
MAX_LINE=1024
MAX_REQUESTS=100
MAX_FIXTURE=2048


def exact(data, fields):
    return type(data) is dict and set(data)==set(fields)


def distinct_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_KEY")
        result[key]=value
    return result


def fixture_file(db):
    if (not isinstance(db, Path) or not db.is_absolute()
            or db.name!="handoff-test.db"
            or db.parent.name!="m11e-fileview-test"):
        raise AdmissionError("EXPLICIT_ISOLATED_HOST_PATH_REQUIRED")
    return db.parent/"fixture-only.json"


def read_bytes(path):
    try:
        meta=path.lstat()
        if (path.is_symlink() or not stat.S_ISREG(meta.st_mode)
                or meta.st_uid!=os.geteuid()
                or stat.S_IMODE(meta.st_mode)&0o077 or meta.st_nlink!=1
                or not 0<meta.st_size<=MAX_FIXTURE):
            raise AdmissionError("UNSAFE_SYNTHETIC_FILE")
        fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
        try:
            current=os.fstat(fd)
            if (current.st_dev,current.st_ino)!=(meta.st_dev,meta.st_ino):
                raise AdmissionError("SYNTHETIC_FILE_REPLACED")
            data=os.read(fd,MAX_FIXTURE+1)
            after=os.fstat(fd)
            if (len(data)!=meta.st_size or
                    (current.st_mtime_ns,current.st_ctime_ns,current.st_size)!=
                    (after.st_mtime_ns,after.st_ctime_ns,after.st_size)):
                raise AdmissionError("SYNTHETIC_FILE_CHANGED")
        finally:
            os.close(fd)
        tail=path.lstat()
        if (tail.st_dev,tail.st_ino)!=(meta.st_dev,meta.st_ino):
            raise AdmissionError("SYNTHETIC_PATH_REPLACED")
        return data
    except (OSError,FileNotFoundError) as exc:
        raise AdmissionError("SYNTHETIC_FILE_UNAVAILABLE") from exc


def decode(data):
    try:
        text=data.decode("utf-8")
        doc=json.loads(text,object_pairs_hook=distinct_pairs)
    except (ValueError,UnicodeError,TypeError):
        raise AdmissionError("INVALID_SYNTHETIC_JSON")
    if (not exact(doc,("fixture","revision","counter","marker"))
            or doc["fixture"]!=MARK or doc["marker"]!="sample"
            or type(doc["revision"]) is not int
            or not 0<=doc["revision"]<=1000000
            or type(doc["counter"]) is not int
            or doc["counter"]!=doc["revision"]):
        raise AdmissionError("INVALID_SYNTHETIC_DOCUMENT")
    return doc


def stable_file(path):
    first=read_bytes(path)
    second=read_bytes(path)
    if first!=second:
        raise AdmissionError("SYNTHETIC_READBACK_CHANGED")
    return second,decode(second)


def encode_next(doc):
    n=doc["revision"]+1
    if n>1000000:
        raise AdmissionError("SYNTHETIC_REVISION_EXHAUSTED")
    return (json.dumps({"fixture":MARK,"revision":n,"counter":n,
        "marker":"sample"},ensure_ascii=True,separators=(",",":"))+"\n").encode("utf-8")


def reply(rid,kind,ok,status,host=None,payload=None):
    snap=host.snapshot() if host is not None else None
    return {"protocol":1,"requestId":rid,"kind":kind,"ok":bool(ok),
        "status":status,"phase":snap["phase"] if snap else "UNKNOWN",
        "epoch":snap["epoch"] if snap else None,
        "pending":snap["pendingStage"] is not None if snap else False,
        "payload":payload if ok and kind=="admit" else None,
        "liveWriterAuthorized":False,"sqliteWriteAuthorized":False,
        "remoteWriteAuthorized":False,"migrationAuthorized":False}


def send(sink,response):
    sink.write(json.dumps(response,ensure_ascii=True,separators=(",",":"))+"\n")
    sink.flush()


def serve(db,writer_id,*,bootstrap=False,source=None,sink=None):
    incoming=source if source is not None else sys.stdin.buffer
    outgoing=sink if sink is not None else sys.stdout
    try:
        file=fixture_file(db)
        # Fail before any SQLite init if the synthetic file is not safe.
        _,model=stable_file(file)
        with auth.Authority(db,writer_id,bootstrap=bootstrap) as host:
            send(outgoing,reply(0,"hello",True,"TEST_OWNER_ATTACHED",host))
            last=0
            active=None
            last_known_revision=model["revision"]
            for _ in range(MAX_REQUESTS):
                line=incoming.readline(MAX_LINE+1)
                if line==b"":
                    return 0
                if len(line)>MAX_LINE or not line.endswith(b"\n"):
                    send(outgoing,reply(None,"protocol",False,"OVERSIZED_REQUEST",host))
                    return 2
                try:
                    req=json.loads(line.decode("utf-8"),object_pairs_hook=distinct_pairs)
                except (ValueError,UnicodeError):
                    send(outgoing,reply(None,"protocol",False,"INVALID_JSON",host))
                    return 2
                rid=req.get("requestId") if type(req) is dict else None
                kind=req.get("kind") if type(req) is dict else None
                if (type(rid) is not int or rid<=last or rid>MAX_REQUESTS
                        or type(kind) is not str):
                    send(outgoing,reply(None,"protocol",False,"REPLAYED_REQUEST",host))
                    return 2
                last=rid
                shapes={"status":{"requestId","kind"},
                    "admit":{"requestId","kind","stageId"},
                    "verify":{"requestId","kind","stageId"},
                    "fail":{"requestId","kind","stageId"},
                    "freeze":{"requestId","kind","expectedEpoch"}}
                if kind not in shapes or set(req)!=shapes[kind]:
                    send(outgoing,reply(rid,kind,False,"UNSUPPORTED_COMMAND",host))
                    continue
                try:
                    payload=None
                    if kind=="admit":
                        if active is not None:
                            raise AdmissionError("STAGE_ALREADY_OWNED")
                        data,document=stable_file(file)
                        if document["revision"]!=last_known_revision:
                            raise AdmissionError("EXTERNAL_FIXTURE_CHANGE")
                        expected=encode_next(document)
                        reservation=host.admit_stage(req["stageId"])
                        active={"stageId":req["stageId"],"expected":expected,
                            "baseline":hashlib.sha256(data).hexdigest(),
                            "epoch":reservation["epoch"]}
                        payload=expected.decode("utf-8")
                    elif kind=="verify":
                        if active is None or req["stageId"]!=active["stageId"]:
                            raise AdmissionError("STALE_STAGE_CALLBACK")
                        try:
                            data,_=stable_file(file)
                            if data!=active["expected"]:
                                raise AdmissionError("HOST_READBACK_MISMATCH")
                        except AdmissionError:
                            host.settle_stage(active["stageId"],saved=False)
                            active=None
                            raise
                        host.settle_stage(active["stageId"],saved=True)
                        last_known_revision+=1
                        active=None
                    elif kind=="fail":
                        if active is None or req["stageId"]!=active["stageId"]:
                            raise AdmissionError("STALE_STAGE_CALLBACK")
                        host.settle_stage(active["stageId"],saved=False)
                        active=None
                    elif kind=="freeze":
                        host.freeze(req["expectedEpoch"])
                    send(outgoing,reply(rid,kind,True,"TEST_ONLY_OBSERVATION",host,payload))
                except (AdmissionError,TypeError,ValueError) as exc:
                    code=str(exc)
                    if not code.isupper() or len(code)>72:
                        code="TEST_OPERATION_REFUSED"
                    send(outgoing,reply(rid,kind,False,code,host))
            send(outgoing,reply(None,"protocol",False,"REQUEST_LIMIT",host))
            return 2
    except Exception:
        send(outgoing,reply(0,"hello",False,"TEST_HOST_UNAVAILABLE"))
        return 2


if __name__=="__main__":
    ap=argparse.ArgumentParser(description="M11g standalone FileView fixture lock host")
    ap.add_argument("--db",type=Path,required=True)
    ap.add_argument("--writer-id",required=True)
    ap.add_argument("--bootstrap-fixture",action="store_true")
    args=ap.parse_args()
    raise SystemExit(serve(args.db,args.writer_id,bootstrap=args.bootstrap_fixture))
