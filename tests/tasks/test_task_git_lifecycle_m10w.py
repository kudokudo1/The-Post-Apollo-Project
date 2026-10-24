#!/usr/bin/env python3
"""M10w strict review-only GIT lifecycle proposal contract; zero DB/network IO."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "m10w_lifecycle", ROOT / "services/projects/ExperimentalTaskGitLifecycleM10w.py")
spec.loader = spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
validator = mod.records._validator
TIME = 1700000000000


def project(pid, name, family):
    return {"id": pid, "name": name, "family": family,
            "remote": None if family=="normal" else {
                "provider":"github","owner":"kudokudo1",
                "projectNodeId":"PVT_UNVERIFIED_"+pid,"projectNumber":14},
            "fields": [] if family=="normal" else [
                {"id":"f1","label":"Private","kind":"text","scope":"local"}],
            "createdAtMs":TIME,"updatedAtMs":TIME}


def task(tid, pid, name, *, remote=None, values=None):
    return {"id":tid,"title":name,"projectId":pid,"done":False,
            "priority":"medium","description":"Preserve content","dueDate":"2026-10-24",
            "createdAtMs":TIME,"updatedAtMs":TIME,
            "remote":remote,"values":{} if values is None else values}


REMOTE={"projectItemNodeId":"PVTI_UNVERIFIED",
        "contentKind":"DRAFT_ISSUE","contentNodeId":None}


def fixture():
    return {"version":2,"revision":0,"nextId":4,"nextProjectId":4,
            "nextOperationId":1,
            "projects":[project("p1","Home","normal"),
                        project("p2","Git A","git"),project("p3","Git B","git")],
            "tasks":[task("t1","p1","Local"),
                     task("t2","p2","Local-only GIT task"),
                     task("t3","p2","Remote-shaped GIT task",remote=REMOTE)],
            "operations":[]}


def denied(model, request, code):
    old=copy.deepcopy(model)
    try:
        mod.propose(model,request)
    except mod.StoreError as exc:
        assert code in str(exc),(code,str(exc))
        assert model==old
        return
    raise AssertionError("Expected "+code)


base=fixture()
validator.validate(base)
initial=copy.deepcopy(base)
create={"kind":"CREATE_GIT_TASK","taskId":"t2"}
delete={"kind":"DELETE_GIT_TASK","taskId":"t3","confirmed":True}
move={"kind":"MOVE_GIT_TASK","taskId":"t3","targetProjectId":"p3"}

c=mod.propose(base,create)
d=mod.propose(base,delete)
m=mod.propose(base,move)
assert base==initial
assert [p["kind"] for p in (c,d,m)]==[
    "CREATE_GIT_TASK","DELETE_GIT_TASK","MOVE_GIT_TASK"]
for p in (c,d,m):
    assert p["previewVersion"]==1
    assert p["proposedJournalVersion"]==3
    assert p["sourceModelVersion"]==2
    assert p["status"]=="REVIEW_ONLY"
    assert p["expectedRevision"]==0
    assert p["expectedModelHash"]==mod.records._hash(base)
    assert p["proposedOperationId"]=="op1"  # None are reserved!
    assert p["existingOperationIds"]==[]
    assert p["remoteWriteAuthorized"] is False
    assert p["journalWriteAuthorized"] is False
    assert p["localWriteAuthorized"] is False
    assert p["remoteSent"] is False
    assert p["remoteAcknowledged"] is False
    assert "VERSIONED_JOURNAL_MIGRATION" in p["requiredGates"]
    assert "FRESH_REMOTE_IDENTITY_AND_BASELINE" in p["requiredGates"]
    assert "EXPLICIT_OPERATOR_APPROVAL" in p["requiredGates"]
    assert p["fingerprint"]==mod._hash({
        k:v for k,v in p.items() if k!="fingerprint"})
assert c["taskBefore"]["remote"] is None
assert d["taskBefore"]["remote"]==REMOTE
assert m["targetProjectId"]=="p3"
assert m["targetProjectReference"]==base["projects"][2]["remote"]
assert "REMOTE_CREATE_IDEMPOTENCY_AND_IDENTITY_BINDING" in c["requiredGates"]
assert "REMOTE_ARCHIVE_VS_DELETE_POLICY" in d["requiredGates"]
assert "TARGET_FIELD_MAPPING_AND_ROLLBACK" in m["requiredGates"]
assert mod.review_current(base,create,c)=={
    "current":True,"reason":"PREVIEW_MATCHES_ONLY",
    "localWriteAuthorized":False,
    "journalWriteAuthorized":False,"remoteWriteAuthorized":False}

# Tampering and stale changes invalidate the review, including a changed
# task body with unchanged revision and a forged proposed operation ID.
fake=copy.deepcopy(d)
fake["taskBefore"]["description"]="Modified"
assert not mod.review_current(base,delete,fake)["current"]
fake=copy.deepcopy(m)
fake["proposedOperationId"]="op999"
assert not mod.review_current(base,move,fake)["current"]
changed=copy.deepcopy(base)
changed["tasks"][2]["title"]="Edited"
changed["revision"]+=1
validator.validate(changed)
assert not mod.review_current(changed,delete,d)["current"]
assert not mod.review_current(base,delete,[])["current"]
assert not mod.review_current(base,delete,{"fingerprint":"bogus"})["current"]

denied(base,{"kind":"CREATE_GIT_TASK","taskId":"t1"},"GIT_PROJECT_REQUIRED")
denied(base,{"kind":"CREATE_GIT_TASK","taskId":"t3"},
       "TASK_ALREADY_HAS_REMOTE_REFERENCE")
denied(base,{"kind":"DELETE_GIT_TASK","taskId":"t2","confirmed":True},
       "REMOTE_DELETE_IDENTITY_REQUIRED")
denied(base,{"kind":"DELETE_GIT_TASK","taskId":"t3","confirmed":False},
       "DELETE_CONFIRMATION_REQUIRED")
denied(base,{"kind":"DELETE_GIT_TASK","taskId":"t3","confirmed":1},
       "DELETE_CONFIRMATION_REQUIRED")
denied(base,{"kind":"MOVE_GIT_TASK","taskId":"t3","targetProjectId":"p1"},
       "CROSS_FAMILY_MOVE_UNSUPPORTED")
denied(base,{"kind":"MOVE_GIT_TASK","taskId":"t2","targetProjectId":"p3"},
       "REMOTE_MOVE_IDENTITY_REQUIRED")
denied(base,{"kind":"MOVE_GIT_TASK","taskId":"t3","targetProjectId":"p2"},
       "NO_CHANGE")
denied(base,{"kind":"MOVE_GIT_TASK","taskId":"t3","targetProjectId":"p9"},
       "UNKNOWN_TARGET_PROJECT")
denied(base,{"kind":"MOVE_GIT_TASK","taskId":"t3","targetProjectId":12},
       "INVALID_TARGET_PROJECT")
denied(base,{"kind":"CREATE_GIT_TASK","taskId":"t9"},"UNKNOWN_TASK")
denied(base,{"kind":"CREATE_GIT_TASK","taskId":"t2","automatic":True},
       "INVALID_LIFECYCLE_REQUEST")
denied(base,{"kind":"CREATE_GIT_TASK","taskId":"t2","confirmed":True},
       "INVALID_LIFECYCLE_REQUEST")
denied(base,{"kind":"ARCHIVE_GIT_TASK","taskId":"t3"},
       "INVALID_LIFECYCLE_REQUEST")

# An existing custom value cannot be reinterpreted under a target project's
# own definition. Normal-to-GIT, unlink and GIT-to-GIT with custom data
# require a separate policy rather than destructive auto-transfer.
value_model=copy.deepcopy(base)
value_model["tasks"][2]["values"]={"f1":"Keep this"}
validator.validate(value_model)
denied(value_model,move,"LOCAL_FIELD_TRANSFER_POLICY_REQUIRED")

# A pending edit for the affected task blocks lifecycle preview, including
# create-before-edit dependencies not representable in the v2 journal.
queued=copy.deepcopy(base)
queued["revision"]=1
queued["nextOperationId"]=2
queued["tasks"][2]["priority"]="urgent"
queued["operations"]=[{"id":"op1","taskId":"t3","projectId":"p2",
                       "field":"priority","before":"medium","after":"urgent",
                       "createdRevision":1,"state":"PENDING","ackToken":None}]
validator.validate(queued)
assert mod.propose(queued,create)["proposedOperationId"]=="op2"
denied(queued,delete,"TASK_DEPENDENCY_REVIEW_REQUIRED")
denied(queued,move,"TASK_DEPENDENCY_REVIEW_REQUIRED")

# A previously ACKNOWLEDGED field op does not itself imply verified identity.
ack=copy.deepcopy(queued)
ack["operations"][0]["state"]="ACKNOWLEDGED"
ack["operations"][0]["ackToken"]="synthetic-receipt"
validator.validate(ack)
assert mod.propose(ack,delete)["proposedOperationId"]=="op2"
for state in ("SENDING","UNCERTAIN","CONFLICT"):
    blocked=copy.deepcopy(queued)
    blocked["operations"][0]["state"]=state
    validator.validate(blocked)
    denied(blocked,create,"RECOVERY_REVIEW_REQUIRED")

# Capacity and unknown schema content remain fail-closed, never truncating.
capacity=copy.deepcopy(base)
capacity["nextOperationId"]=1000000000
validator.validate(capacity)
denied(capacity,create,"JOURNAL_CAPACITY_REVIEW_REQUIRED")
oversized=copy.deepcopy(base)
oversized["version"]=3
denied(oversized,create,"INVALID_MODEL_VERSION_OR_FIELDS")
unknown=copy.deepcopy(base)
unknown["tasks"][1]["newRemoteFlag"]="true"
denied(unknown,create,"INVALID_TASK")
print("M10w versioned lifecycle proposal contract and no-actuation gates: PASS")
