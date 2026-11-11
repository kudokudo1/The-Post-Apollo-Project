#!/usr/bin/env python3
"""MACHINE intent binding: exact bytes/peer/purpose but NO positive admission."""
import dataclasses
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/time"))
import MachineBraveArchiveAdmissionIntent as binding
import MachineBraveProtectedMetadataContract as broker

CHALLENGE="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RECORD="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
KIND=broker.REQUEST_KIND

def encode(data):
    return json.dumps(data,sort_keys=True,separators=(",",":")).encode()

def refused(call,*args,**kwargs):
    try:call(*args,**kwargs)
    except binding.IntentRefusal:return
    raise AssertionError("UNTRUSTED MACHINE INTENT ACCEPTED")

list_req={"kind":KIND,"action":broker.LIST,"challenge":CHALLENGE}
inspect_req={"kind":KIND,"action":broker.INSPECT,
             "challenge":CHALLENGE,"record_id":RECORD}
raw=encode(inspect_req)
a=binding.bind_request(raw,peer_pid=1001,peer_uid=2000,peer_gid=2000)
assert a.admission_allowed is False
assert dataclasses.is_dataclass(a)
assert a.challenge==CHALLENGE
assert a.record_id==RECORD
assert a.action==broker.INSPECT
assert a.request_sha256==hashlib.sha256(raw).hexdigest()
assert a.intent_sha256==hashlib.sha256(a.canonical_bytes).hexdigest()
subject=json.loads(a.canonical_bytes)
assert subject=={
    "kind":binding.DOMAIN,"audience":binding.AUDIENCE,
    "purpose":binding.PURPOSE,"action":broker.INSPECT,
    "challenge":CHALLENGE,"record_id":RECORD,
    "request_sha256":hashlib.sha256(raw).hexdigest(),
    "peer_pid":1001,"peer_uid":2000,"peer_gid":2000
}
assert binding.external_authority_available() is False

# There is NO allowed receipt form yet, regardless of claims.
for claimed in (None,True,False,{},{"signed":True},{"C3e":"PASS"},
                {"C5":"APPROVED"},{"signed":True,"consent":True},
                {"purpose":binding.PURPOSE,"authorized":True,
                 "record_id":RECORD,"challenge":CHALLENGE}):
    assert binding.may_read_metadata(a,claimed_receipt=claimed) is False
assert binding.may_read_metadata(a) is False

# Exact socket bytes are bound: whitespace changes count; peer UID, PID and
# GID each change the intent digest. These digests are not signatures.
inputs=[
    binding.bind_request(json.dumps(inspect_req).encode(),
                         peer_pid=1001,peer_uid=2000,peer_gid=2000),
    binding.bind_request(raw,peer_pid=1002,peer_uid=2000,peer_gid=2000),
    binding.bind_request(raw,peer_pid=1001,peer_uid=2001,peer_gid=2000),
    binding.bind_request(raw,peer_pid=1001,peer_uid=2000,peer_gid=2001),
    binding.bind_request(encode({**inspect_req,
                   "challenge":"cccccccc-cccc-4ccc-8ccc-cccccccccccc"}),
                   peer_pid=1001,peer_uid=2000,peer_gid=2000),
    binding.bind_request(encode({**inspect_req,
                   "record_id":"dddddddd-dddd-4ddd-8ddd-dddddddddddd"}),
                   peer_pid=1001,peer_uid=2000,peer_gid=2000),
]
assert all(v.intent_sha256!=a.intent_sha256 for v in inputs)
assert all(v.admission_allowed is False for v in inputs)

# A duplicate packet has the same binding but is STILL denied. No one-use
# authorization ledger is implied by deterministic hashing.
replayed=binding.bind_request(raw,peer_pid=1001,peer_uid=2000,peer_gid=2000)
assert replayed.intent_sha256==a.intent_sha256
assert binding.may_read_metadata(replayed,claimed_receipt={"replayed":False}) is False

# LIST cannot be repurposed into read one record, DELETE, RESTORE or export.
listed=binding.bind_request(encode(list_req),peer_pid=1001,
                            peer_uid=2000,peer_gid=2000)
assert listed.record_id is None
assert listed.intent_sha256!=a.intent_sha256
assert listed.admission_allowed is False
assert binding.may_read_metadata(listed) is False

for wrong in (
    {**list_req,"origin":"chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"},
    {**list_req,"client_authenticated":True},
    {**list_req,"signed":True,"consented":True},
    {**list_req,"peer_uid":2000},
    {**list_req,"record_id":RECORD},
    {**inspect_req,"record_id":"../../etc/passwd"},
    {**inspect_req,"action":"RESTORE"},
    {**inspect_req,"action":"DELETE"},
    {**inspect_req,"action":"EXPORT_CIPHERTEXT"},
    {**inspect_req,"path":"/tmp/sealed"},
    {**inspect_req,"challenge":"bogus"},
    {**inspect_req,"kind":"machine-privileged-archive-request"},
):
    refused(binding.bind_request,encode(wrong),
            peer_pid=1001,peer_uid=2000,peer_gid=2000)

for malformed in (
    b"",b"null",b"[]",b"not JSON",b"{}",
    b'{"kind":"a","kind":"b"}',
    encode(inspect_req)+b"\n"*4096,
    b"\xff"*5,
):
    refused(binding.bind_request,malformed,
            peer_pid=1001,peer_uid=2000,peer_gid=2000)

for invalid_peer in (
    {"peer_pid":0,"peer_uid":2000,"peer_gid":2000},
    {"peer_pid":True,"peer_uid":2000,"peer_gid":2000},
    {"peer_pid":1001,"peer_uid":-1,"peer_gid":2000},
    {"peer_pid":1001,"peer_uid":False,"peer_gid":2000},
    {"peer_pid":1001,"peer_uid":2000,"peer_gid":-1},
    {"peer_pid":1001,"peer_uid":2000,"peer_gid":"2000"},
):
    refused(binding.bind_request,raw,**invalid_peer)

# Source-level invariant: positive reader exists for privileged fixture,
# but NO test-only callback or metadata read is reachable from ingress.
source=(ROOT/"services/time/MachineBraveProtectedMetadataContract.py").read_text()
handler=source.split("def handle_once(",1)[1].split(
    '\n\nif __name__ == "__main__":',1)[0]
assert "test_only_grant" not in source
assert "metadata_from_protected_root(" not in handler
assert "admission.bind_request(" in handler
assert "admission.may_read_metadata(" in handler
assert "refuse()" in handler
assert "return False" in handler
assert "restore_allowed" in broker.REFUSED and broker.REFUSED["restore_allowed"] is False

print("MACHINE metadata request/peer binding and all claimed authority/replay refusals PASS")
