#!/usr/bin/env python3
"""C2f request lifecycle: isolated fake host, no live credentials or UI grants."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"services/connections/experiments/C2fFakeRequestLifecycle.py"
spec=importlib.util.spec_from_file_location("c2f_fake_request",SOURCE)
assert spec and spec.loader
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

@contextmanager
def isolated():
    with tempfile.TemporaryDirectory(prefix="postapollo-c2c-ci-",dir="/tmp") as root:
        folder=Path(root)
        home=folder/"home"
        home.mkdir(mode=0o700)
        marker=folder/".ci-only-authority"
        marker.write_text("C2C_PRIVATE_SOCKETPAIR_ONLY\n",encoding="utf8")
        marker.chmod(0o600)
        previous=os.environ.copy()
        os.environ.update({
            "HOME":str(home),"GITHUB_ACTIONS":"true",
            "POST_APOLLO_C2C_FAKE_ONLY":"1",
            "POST_APOLLO_FIRMS_MAP_KEY":"FAKE_LEAK_CANARY",
            "PYTHONPATH":"/tmp/SHOULD_NOT_BE_INHERITED",
        })
        try:
            yield folder,home
        finally:
            os.environ.clear()
            os.environ.update(previous)
            assert sorted(x.name for x in folder.iterdir())==[
                ".ci-only-authority","home"],"UNEXPECTED_TEST_FILE_WRITE"
            assert list(home.iterdir())==[],"UNEXPECTED_CREDENTIAL_OR_STATE_WRITE"

def refused(result,reason):
    assert result=={"ok":False,"reason":reason},(result,reason)

class FakeClock:
    def __init__(self):
        self.time=10000.0
    def __call__(self):
        return self.time
    def advance(self,ms):
        self.time+=ms/1000

def validate_snapshot(r):
    assert r["ok"] and r["simulated"]
    assert r["provider"]=="nasa-firms"
    assert r["consumer"]=="weather-earth"
    assert r["operation"]=="fires.hotspots.read"
    assert r["profile"]=="ci-only-profile"
    assert r["realGrantActive"] is False
    assert r["canApproveInProduction"] is False
    assert r["credentialPresent"] is False
    assert not any(x in json.dumps(r) for x in (
        "FAKE_LEAK_CANARY","C2C_SYNTHETIC_NEVER","FD=", "PASSWORD", "TOKEN"
    ))
    assert set(r)=={"ok","requestId","state","provider","consumer",
                    "operation","profile","reason","expiresInMs",
                    "credentialPresent","realGrantActive",
                    "canApproveInProduction","simulated"}

def must_stop(app):
    assert app._host.state=="CLOSED"
    assert app._host._control is None
    for p in [app._host._broker,app._host._weather]:
        if p is not None:
            assert p.poll() is not None,"ORPHAN_C2F_CHILD"

def exercise():
    # Import and object construction alone cannot launch an OS process.
    initial=m.FakeRequestLifecycle()
    assert initial._host.pids==() and initial._host.state=="STOPPED"
    refused(initial.request_weather_hotspots(),"HOST_UNAVAILABLE")
    must_stop(initial)
    refused(initial.start(),"HOST_ALREADY_CLOSED")
    assert initial.close()=={"ok":True,"state":"CLOSED"}

    with isolated():
        clock=FakeClock()
        with m.FakeRequestLifecycle(clock=clock) as a:
            refused(a.review("wrong"),"REQUEST_NOT_FOUND")
            refused(a.operator_decide("wrong","approve",confirmed=True),"REQUEST_NOT_FOUND")
            refused(a.request_weather_hotspots(ttl_ms=True),"INVALID_REQUEST_TTL")
            refused(a.request_weather_hotspots(ttl_ms=9),"INVALID_REQUEST_TTL")
            refused(a.request_weather_hotspots(ttl_ms=60001),"INVALID_REQUEST_TTL")
            request=a.request_weather_hotspots()
            assert request["state"]=="PENDING" and request["simulated"] is True
            rid=request["requestId"]
            assert len(rid)==32
            validate_snapshot(a.review(rid))
            refused(a.request_weather_hotspots(),"REQUEST_ALREADY_PENDING")
            refused(a.execute_fake(rid),"REQUEST_NOT_APPROVED")
            refused(a.operator_decide(rid,"approve",confirmed=False),
                    "EXPLICIT_CONFIRMATION_REQUIRED")
            refused(a.operator_decide(rid,"approve",confirmed=1),
                    "EXPLICIT_CONFIRMATION_REQUIRED")
            refused(a.operator_decide(rid,"grant",confirmed=True),
                    "DECISION_NOT_ALLOWED")
            # Fake Weather process cannot approve through its own FD.
            refused(a._host.read_fake_hotspots({"op":"approve","approved":True}),
                    "CLIENT_CANNOT_APPROVE_OR_REVOKE")
            assert a.operator_decide(rid,"approve",confirmed=True)=={
                "ok":True,"state":"APPROVED","simulated":True}
            assert a.review(rid)["state"]=="APPROVED"
            refused(a.operator_decide(rid,"approve",confirmed=True),
                    "REQUEST_NOT_PENDING")
            result=a.execute_fake(rid)
            assert result["ok"] is True
            assert result["state"]=="COMPLETED"
            assert result["simulated"] is True
            assert len(result["observations"])==2
            assert all(x["synthetic"] for x in result["observations"])
            assert "FAKE_LEAK_CANARY" not in json.dumps(result)
            assert "C2C_SYNTHETIC_NEVER" not in json.dumps(result)
            assert a.review(rid)["state"]=="COMPLETED"
            refused(a.execute_fake(rid),"REQUEST_NOT_APPROVED")
            refused(a.cancel(rid),"REQUEST_ALREADY_FINAL")
            refused(a.operator_decide(rid,"deny"),"REQUEST_NOT_PENDING")

            # Pending rejection never grants anything, including later reuse.
            second=a.request_weather_hotspots()
            assert second["requestId"]!=rid
            refused(a.review(rid),"REQUEST_NOT_FOUND")
            sid=second["requestId"]
            assert a.operator_decide(sid,"deny") == {
                "ok":True,"state":"DENIED","simulated":True}
            assert a.review(sid)["reason"]=="OPERATOR_DENIED"
            refused(a.execute_fake(sid),"REQUEST_NOT_APPROVED")

            # Host cancellation from a pending state.
            third=a.request_weather_hotspots()
            tid=third["requestId"]
            assert a.cancel(tid)["state"]=="CANCELLED"
            refused(a.operator_decide(tid,"approve",confirmed=True),
                    "REQUEST_NOT_PENDING")

            # Cancellation of an approved request MUST revoke broker grant.
            fourth=a.request_weather_hotspots()
            fid=fourth["requestId"]
            assert a.operator_decide(fid,"approve",confirmed=True)["ok"] is True
            assert a.cancel(fid)["state"]=="CANCELLED"
            refused(a._host.read_fake_hotspots(),"NO_OPERATOR_GRANT")
            refused(a.execute_fake(fid),"REQUEST_NOT_APPROVED")

            # Host-owned request expiry with injected monotonic clock.
            exp=a.request_weather_hotspots(ttl_ms=20)
            eid=exp["requestId"]
            clock.advance(25)
            assert a.review(eid)["state"]=="EXPIRED"
            assert a.review(eid)["reason"]=="REQUEST_EXPIRED"
            refused(a.operator_decide(eid,"approve",confirmed=True),
                    "REQUEST_NOT_PENDING")

            # Expiration after approval revokes the existing fake broker grant.
            exp2=a.request_weather_hotspots(ttl_ms=25)
            xid=exp2["requestId"]
            assert a.operator_decide(xid,"approve",confirmed=True)["ok"] is True
            clock.advance(30)
            assert a.review(xid)["state"]=="EXPIRED"
            refused(a._host.read_fake_hotspots(),"NO_OPERATOR_GRANT")
            refused(a.execute_fake(xid),"REQUEST_NOT_APPROVED")
        must_stop(a)

        # Shutdown while approved closes authority even if never used.
        z=m.FakeRequestLifecycle()
        assert z.start()["ok"] is True
        zr=z.request_weather_hotspots()["requestId"]
        assert z.operator_decide(zr,"approve",confirmed=True)["ok"] is True
        assert z.close()=={"ok":True,"state":"CLOSED"}
        must_stop(z)
        assert z.review(zr)["state"]=="CANCELLED"
        assert z.review(zr)["reason"]=="HOST_SHUTDOWN"
        refused(z.execute_fake(zr),"REQUEST_NOT_APPROVED")

        # If either child dies, pending host state fails closed and reaps both.
        for child in ("_weather","_broker"):
            crash=m.FakeRequestLifecycle()
            assert crash.start()["ok"] is True
            item=crash.request_weather_hotspots()["requestId"]
            assert crash.operator_decide(item,"approve",confirmed=True)["ok"] is True
            p=getattr(crash._host,child)
            p.kill()
            p.wait(timeout=3)
            assert crash.review(item)["state"]=="FAILED"
            assert crash.review(item)["reason"]=="HOST_DISCONNECTED"
            must_stop(crash)

        # Test-only CLI has an explicit fake marker and refuses ordinary use.
        env={"HOME":"/tmp","GITHUB_ACTIONS":"false"}
        r=subprocess.run([sys.executable,"-B",str(SOURCE),"--fake-self-check"],
                         env=env,capture_output=True,text=True,timeout=4)
        assert r.returncode==2 and "REFUSED_C2F_FAKE_TEST" in r.stdout
        assert r.stderr==""

        # Run the exact self-check with the disposable marked test HOME.
        r=subprocess.run([sys.executable,"-B",str(SOURCE),"--fake-self-check"],
                         env=m._host._child_env(),capture_output=True,
                         text=True,timeout=8)
        assert r.returncode==0,(r.stdout,r.stderr)
        assert "C2F_PASS // FAKE_REQUEST_REVIEW_APPROVE_EXECUTE_CLOSE" in r.stdout
        assert r.stderr==""
    print("C2F_PASS // PENDING_REVIEW_DENY_CANCEL_EXPIRE_COMPLETE_CRASH_AND_REPLAY")

def static_safety():
    source=SOURCE.read_text(encoding="utf8")
    production=(ROOT/"services/connections/ConnectionsBroker.qml").read_text()
    assert "readonly property bool credentialActionsEnabled: false" in production
    assert "TRUSTED_BROKER_NOT_ACTIVATED" in (
        ROOT/"services/connections/ConnectionsBrokerPolicy.js").read_text()
    for forbidden in (".bind(",".listen(","AF_INET","secret-tool",
                      "Quickshell.env(","http://","https://","sudo","systemctl"):
        assert forbidden not in source,forbidden
    assert "operator_decide" in source and "request_weather_hotspots" in source
    assert "realGrantActive" in source and "canApproveInProduction" in source
    assert "HOST_SHUTDOWN" in source and "REQUEST_EXPIRED" in source
    assert "self._host.approve(confirmed=True" in source
    assert "self._host.revoke()" in source

if __name__=="__main__":
    static_safety()
    exercise()
