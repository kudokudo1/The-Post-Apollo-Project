#!/usr/bin/env python3
"""M12i isolated native-FileView -> M12h disposable receipt host.

Only m11e-fileview-test/fixture-only.json and its existing test authority DB.
No QML import, TASKS path discovery, real source writes, or production service.
A caller-supplied "verify" is a hint, NOT authenticated native attribution.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("m12i_receipt_fixture",
                                            HERE/"TaskStageSourceReceiptM12h.py")
receipt=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=receipt
spec.loader.exec_module(receipt)
AdmissionError=receipt.AdmissionError
MAX_LINE=512
MAX_REQUESTS=60


def exact(obj, keys):
    return type(obj) is dict and set(obj)==set(keys)


def distinct(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            raise ValueError("DUPLICATE_KEY")
        result[k]=v
    return result


def frame(rid, kind, *, owner=None, ok=False, status="REFUSED",
          stage_id=None, payload=None, actual_hash=None):
    state=owner.snapshot() if owner is not None else {}
    return {
        "protocol":1,"requestId":rid,"kind":kind,"ok":bool(ok),
        "status":status,"phase":state.get("phase","UNVERIFIED"),
        "epoch":state.get("epoch"),"pending":state.get("pendingStage") is not None,
        "stageId":stage_id,"payload":payload,"actualSha256":actual_hash,
        "productionWriterAuthorized":False,"nativeStageAttributionProven":False,
        "realTasksAccessAuthorized":False
    }


def emit(out, value):
    out.write(json.dumps(value,separators=(",",":"),ensure_ascii=True)+"\n")
    out.flush()


def serve(db:Path, writer_id:str, *, bootstrap=False, incoming=None, outgoing=None):
    inp=incoming if incoming is not None else sys.stdin.buffer
    out=outgoing if outgoing is not None else sys.stdout
    try:
        # M12h checks exact existing private fixture source before DB opening.
        with receipt.DisposableStageReceipt(db,writer_id,bootstrap=bootstrap) as owner:
            emit(out,frame(0,"hello",owner=owner,ok=True,
                           status="TEST_OWNER_ATTACHED"))
            last=0
            active=None
            for _ in range(MAX_REQUESTS):
                raw=inp.readline(MAX_LINE+1)
                if raw==b"":
                    return 0
                if len(raw)>MAX_LINE or not raw.endswith(b"\n"):
                    emit(out,frame(None,"protocol",owner=owner,
                                   status="INVALID_PROTOCOL_LINE"))
                    return 2
                try:
                    request=json.loads(raw.decode("utf-8"),object_pairs_hook=distinct)
                except (ValueError,UnicodeError):
                    emit(out,frame(None,"protocol",owner=owner,status="INVALID_JSON"))
                    return 2
                rid=request.get("requestId") if type(request) is dict else None
                kind=request.get("kind") if type(request) is dict else None
                if (type(rid) is not int or rid<=last or rid>MAX_REQUESTS or
                        type(kind) is not str):
                    emit(out,frame(None,"protocol",owner=owner,
                                   status="INVALID_OR_REPLAYED_REQUEST"))
                    return 2
                last=rid
                shapes={
                    "status":{"requestId","kind"},
                    "reserve":{"requestId","kind","stageId"},
                    "verify":{"requestId","kind","stageId","epoch"},
                    "freeze":{"requestId","kind","epoch"}}
                if kind not in shapes or not exact(request,shapes[kind]):
                    emit(out,frame(rid,kind,owner=owner,status="UNSUPPORTED_COMMAND"))
                    continue
                result=None
                stage=None
                payload=None
                actual_hash=None
                ok=False
                code="REFUSED"
                try:
                    if kind=="reserve":
                        if active is not None:
                            raise AdmissionError("ONE_STAGE_AT_A_TIME")
                        result=owner.reserve(request["stageId"])
                        active=(result["stageId"],result["epoch"])
                        stage=result["stageId"]
                        payload=result["payload"].decode("utf-8")
                        code="SYNTHETIC_RESERVED"
                        ok=True
                    elif kind=="verify":
                        if (active is None or
                                type(request["epoch"]) is not int or
                                active!=(request["stageId"],request["epoch"])):
                            raise AdmissionError("STALE_VERIFICATION_HINT")
                        result=owner.settle_after_independent_readback(
                            request["stageId"],request["epoch"])
                        stage=request["stageId"]
                        ok=result["settled"]
                        code=result["status"]
                        actual_hash=result.get("actualSha256")
                        if ok:
                            active=None
                    elif kind=="freeze":
                        if (type(request["epoch"]) is not int or
                                active is not None):
                            raise AdmissionError("FREEZE_WITH_ACTIVE_STAGE")
                        result=owner.owner.freeze(request["epoch"])
                        code="TEST_FREEZE_REQUESTED"
                        ok=True
                    else:
                        code="TEST_STATUS"
                        ok=True
                    emit(out,frame(rid,kind,owner=owner,ok=ok,status=code,
                                   stage_id=stage,payload=payload,
                                   actual_hash=actual_hash))
                    if not ok:
                        return 2
                except (AdmissionError,ValueError,TypeError,KeyError):
                    emit(out,frame(rid,kind,owner=owner,status="TEST_HOST_REFUSED"))
                    # Fail closed, never silently rearm/retry a stage.
                    return 2
            emit(out,frame(None,"protocol",owner=owner,status="REQUEST_LIMIT"))
            return 2
    except (AdmissionError,OSError,ValueError,TypeError):
        emit(out,frame(0,"hello",status="TEST_HOST_UNAVAILABLE"))
        return 2


def main():
    p=argparse.ArgumentParser(description="M12i disposable stage receipt host")
    p.add_argument("--db",type=Path,required=True)
    p.add_argument("--writer-id",required=True)
    p.add_argument("--bootstrap-fixture",action="store_true")
    args=p.parse_args()
    return serve(args.db,args.writer_id,bootstrap=args.bootstrap_fixture)


if __name__=="__main__":
    raise SystemExit(main())
