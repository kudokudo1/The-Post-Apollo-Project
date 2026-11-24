#!/usr/bin/env python3
"""M4o private Banking storage: exact schema, CAS, immutable pair IDs and security."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile

root=Path(__file__).resolve().parents[2]
source=root/"scripts/finance/banking_manual_store.py"
spec=importlib.util.spec_from_file_location("banking_manual_store",source)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def refuses(f,code=None):
    try:
        f()
    except m.Refusal as exc:
        if code: assert str(exc)==code,(code,exc)
        return
    raise AssertionError("Expected refusal: "+str(code))

def a(identifier,nick,opening=None,provider="chime",product="chime-checking"):
    return {"id":identifier,"providerId":provider,"productId":product,
            "nickname":nick,"openingCents":opening,"origin":"manual"}

def e(identifier,owner,amount,description="Manual",date="2026-11-24",**extra):
    return {"id":identifier,"accountId":owner,"date":date,
            "description":description,"amountCents":amount,"origin":"manual",**extra}

initial={"mode":"manual","accounts":[
    a("acct-1","Personal",10000),
    a("acct-2","Emergency",None,provider="chime",product="chime-savings")],
    "entries":[
        e("entry-3","acct-1",-2000,"Savings transfer",transferId="transfer-3",transferSide="out"),
        e("entry-4","acct-2",2000,"Savings transfer",transferId="transfer-3",transferSide="in"),
        e("entry-5","acct-1",-350,"Lunch"),
        e("entry-6","acct-2",100,"Money in")],
    "nextId":7}
assert m.validate_session(initial) is initial

with tempfile.TemporaryDirectory() as t:
    d=Path(t)/"manual"
    first=m.run(d,{"action":"list"})
    assert first==m.empty_doc()
    assert not d.exists(),"read-only list must not create storage"
    refuses(lambda:m.run(d,{"action":"save","expectedRevision":0,
                           "session":m.empty_session()}),"ONLY_MANUAL_ACCOUNTS_CAN_BE_SAVED")
    refuses(lambda:m.run(d,{"action":"save","expectedRevision":0,
                           "session":{**initial,"mode":"demo"}}),"INVALID_MANUAL_SESSION")
    assert not d.exists(),"invalid input must fail before creating disk path"
    saved=m.run(d,{"action":"save","expectedRevision":0,"session":initial})
    assert saved["version"]==1 and saved["revision"]==1
    assert saved["session"]==initial
    assert m.run(d,{"action":"list"})==saved
    f=d/"manual-session.json"
    lock=d/"manual-session.lock"
    for target in (d,f,lock):
        mode=stat.S_IMODE(target.stat().st_mode)
        assert mode==(0o700 if target==d else 0o600),(target,oct(mode))
    refuses(lambda:m.run(d,{"action":"save","expectedRevision":0,
                           "session":initial}),"STALE_REVISION")
    assert m.run(d,{"action":"list"})==saved
    updated=copy.deepcopy(initial)
    updated["accounts"][0]["nickname"]="Renamed"
    updated["accounts"][0]["openingCents"]=0
    updated["entries"][2]["amountCents"]=-200
    saved2=m.run(d,{"action":"save","expectedRevision":1,"session":updated})
    assert saved2["revision"]==2
    assert m.run(d,{"action":"list"})["session"]==updated
    assert m.run(d,{"action":"list"})["session"]["entries"][0]["transferId"]=="transfer-3"
    assert m.run(d,{"action":"list"})["session"]["accounts"][1]["openingCents"] is None
    refuses(lambda:m.run(d,{"action":"clear","expectedRevision":1,
                           "confirmClear":True}),"STALE_REVISION")
    refuses(lambda:m.run(d,{"action":"clear","expectedRevision":2,
                           "confirmClear":False}),"CLEAR_CONFIRMATION_REQUIRED")
    assert m.run(d,{"action":"list"})["session"]==updated
    cleared=m.run(d,{"action":"clear","expectedRevision":2,"confirmClear":True})
    assert cleared["revision"]==3 and cleared["session"]==m.empty_session()
    assert m.run(d,{"action":"list"})==cleared
    refuses(lambda:m.run(d,{"action":"clear","expectedRevision":3,
                            "confirmClear":True}),"NOTHING_SAVED")
    assert m.run(d,{"action":"list"})==cleared
    saved3=m.run(d,{"action":"save","expectedRevision":3,"session":initial})
    assert saved3["revision"]==4
    assert m.run(d,{"action":"list"})["session"]==initial

    # Existing unsafe file must be refused, never silently overwritten.
    f.chmod(0o644)
    refuses(lambda:m.run(d,{"action":"list"}),"UNSAFE_RECORD")
    refuses(lambda:m.run(d,{"action":"save","expectedRevision":4,
                           "session":initial}),"UNSAFE_RECORD")
    f.chmod(0o600)
    f.unlink()
    f.symlink_to(d/"missing")
    refuses(lambda:m.run(d,{"action":"list"}),"UNSAFE_RECORD")
    f.unlink()
    d.chmod(0o777)
    refuses(lambda:m.run(d,{"action":"list"}),"UNSAFE_DIRECTORY")

# Malformed or duplicate JSON keys must not produce ambiguous saved states.
refuses(lambda:m.decode(b'{"action":"list","action":"clear"}'),"DUPLICATE_JSON_FIELD")
refuses(lambda:m.decode(b'{"action":NaN}'),"INVALID_JSON")
refuses(lambda:m.decode(b'{"action":"list"\xff}'),"INVALID_JSON")
refuses(lambda:m.run(Path("/unused"),{"action":"list","extra":1}),"INVALID_COMMAND")
refuses(lambda:m.run(Path("/unused"),{"action":"save","expectedRevision":True,
                            "session":initial}),"INVALID_REVISION")

bad=[]
def corrupt(mutator):
    b=copy.deepcopy(initial)
    mutator(b)
    bad.append(b)
corrupt(lambda x:x.update(mode="demo"))
corrupt(lambda x:x.update(nextId=6))
corrupt(lambda x:x.update(nextId=1_000_001))
corrupt(lambda x:x["accounts"][0].update(origin="demo"))
corrupt(lambda x:x["accounts"][0].update(providerId="unknown"))
corrupt(lambda x:x["accounts"][0].update(openingCents=True))
corrupt(lambda x:x["accounts"][0].update(openingCents=1_000_000_000))
corrupt(lambda x:x["accounts"][0].update(nickname=" Unsafe "))
corrupt(lambda x:x["accounts"][1].update(nickname="PERSONAL",productId="chime-checking"))
corrupt(lambda x:x["entries"][0].update(accountId="acct-999"))
corrupt(lambda x:x["entries"][0].update(date="2026-02-30"))
corrupt(lambda x:x["entries"][0].update(amountCents=-999999999999))
corrupt(lambda x:x["entries"][0].update(transferId="transfer-4"))
corrupt(lambda x:x["entries"][1].update(transferSide="out"))
corrupt(lambda x:x["entries"][1].update(amountCents=3000))
corrupt(lambda x:x["entries"][1].update(description="Mismatch"))
corrupt(lambda x:x["entries"][1].pop("transferId"))
corrupt(lambda x:x["entries"][0].update(extra="field"))
corrupt(lambda x:x["accounts"][0].update(extra="field"))
corrupt(lambda x:x["entries"][2].update(id="entry-3"))
corrupt(lambda x:x["accounts"][1].update(id="acct-1"))
corrupt(lambda x:x.update(entries=x["entries"]*76))
for i,s in enumerate(bad):
    refuses(lambda:m.validate_session(s))
assert len(bad)==22,len(bad)

# 300 entries with full-length UTF-8 titles and complete account data must
# survive a round trip within the same bounded format.
large=copy.deepcopy(initial)
large["entries"]=large["entries"][:2]
for i in range(5,303):
    large["entries"].append(e("entry-"+str(i),"acct-1",1,
                              description="É"*120))
large["nextId"]=303
assert len(large["entries"])==300
with tempfile.TemporaryDirectory() as t:
    d=Path(t)/"banking"
    saved=m.run(d,{"action":"save","expectedRevision":0,"session":large})
    assert saved["session"]==large
    assert m.run(d,{"action":"list"})==saved
    assert (d/"manual-session.json").stat().st_size <= m.MAX_BYTES

print("Banking M4o: revisioned local manual snapshots, pair preservation, 300-record roundtrip, symlink/privacy guards, malformed refusal, no-demo persistence PASS")
