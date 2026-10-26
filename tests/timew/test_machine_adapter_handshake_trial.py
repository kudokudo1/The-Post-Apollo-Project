#!/usr/bin/env python3
"""M2d2 simulated, scoped app-to-host handshake: no real consent or access."""
import copy
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineAdapterHandshakeTrial import HandshakeError, SyntheticHandshakeSession


def uid(n):
    return str(uuid.UUID(int=n))


extra = [
    {"adapter_id": "browser.firefox", "family": "browser",
     "app_ids": ["firefox"], "item_kinds": ["browser_tab"],
     "target_hosts": ["linux_wayland", "windows"], "state": "schema_only"},
    {"adapter_id": "editor.vscode", "family": "editor",
     "app_ids": ["code"], "item_kinds": ["editor_tab"],
     "target_hosts": ["linux_wayland"], "state": "schema_only"},
    {"adapter_id": "terminal.ghostty", "family": "terminal",
     "app_ids": ["com.mitchellh.ghostty"], "item_kinds": ["terminal_tab"],
     "target_hosts": ["linux_wayland"], "state": "schema_only"},
]


def fixture(session, n, *, adapter, app, time=1000, host="linux_wayland"):
    host_id = uid(1000+n)
    nonce = uid(2000+n)
    challenge = session.begin(
        nonce=nonce, host_observation_id=host_id, app_id=app,
        adapter_id=adapter, host_target=host, now_seconds=time,
        ttl_seconds=12, permission_fixture="explicit_synthetic_allow")
    assert challenge["nonce"] == nonce
    assert challenge["read_only"] and challenge["synthetic_only"]
    assert not challenge["action_allowed"]
    host_echo = {"scope_id": session.scope_id, "nonce": nonce,
                 "host_observation_id": host_id, "app_id": app,
                 "source": "synthetic_host"}
    app_echo = {"scope_id": session.scope_id, "nonce": nonce,
                "host_observation_id": host_id, "app_id": app,
                "adapter_id": adapter, "namespace_key": uid(8000+n),
                "instance_key": uid(9000+n), "inner_item_count": 2,
                "source": "synthetic_app"}
    return nonce, host_echo, app_echo


def refuses(fn):
    try:
        fn()
    except HandshakeError:
        return
    raise AssertionError("unsafe fixture handshake succeeded")


session = SyntheticHandshakeSession(uid(42), adapter_manifests=extra)
# 17 Brave, 4 Kitty, Firefox, VS Code, Ghostty.
result_count = 0
for n in range(1, 25):
    if n <= 17: app, adapter = "brave-browser", "brave"
    elif n <= 21: app, adapter = "kitty", "kitty"
    elif n == 22: app, adapter = "firefox", "browser.firefox"
    elif n == 23: app, adapter = "code", "editor.vscode"
    else: app, adapter = "com.mitchellh.ghostty", "terminal.ghostty"
    nonce, host_echo, app_echo = fixture(session, n, adapter=adapter, app=app)
    result = session.verify(nonce, host_echo, app_echo, now_seconds=1004)
    assert result["status"] == "fixture_challenge_echo_matched"
    assert result["reported_inner_item_count"] == 2
    assert result["synthetic_provenance_only"] is True
    assert result["real_app_identity_verified"] is False
    assert result["real_host_binding_verified"] is False
    assert result["operator_consent_verified"] is False
    assert result["exact_session_match"] is False
    assert result["safe_actions"] == [] and not result["action_allowed"]
    assert not result["executable"] and result["read_only"]
    assert "instance_key" not in result and "namespace_key" not in result
    result_count += 1
    refuses(lambda: session.verify(nonce, host_echo, app_echo, now_seconds=1005))
assert result_count == 24

def case(number, alteration, *, to_host=False, to_app=False,
         now=1004, expect_error=True):
    temp = SyntheticHandshakeSession(uid(43+number), adapter_manifests=extra)
    nonce, host_echo, app_echo = fixture(
        temp, number+50, adapter="brave", app="brave-browser")
    before = copy.deepcopy((host_echo, app_echo))
    if to_host: alteration(host_echo)
    elif to_app: alteration(app_echo)
    else: alteration(temp)
    if expect_error:
        refuses(lambda: temp.verify(nonce, host_echo, app_echo, now_seconds=now))
        # Failed attempt consumes nonce. A second reply cannot rescue/replay.
        refuses(lambda: temp.verify(nonce, before[0], before[1], now_seconds=1004))
    else:
        data=temp.verify(nonce, host_echo, app_echo, now_seconds=now)
        assert data["status"]=="fixture_challenge_echo_matched"

case(1, lambda d: d.update(source="real_host"), to_host=True)
case(2, lambda d: d.update(source="real_app"), to_app=True)
case(3, lambda d: d.update(private_url="https://private"), to_app=True)
case(4, lambda d: d.update(command="terminal secret"), to_host=True)
case(5, lambda d: d.update(app_id="kitty"), to_app=True)
case(6, lambda d: d.update(app_id="kitty"), to_host=True)
case(7, lambda d: d.update(adapter_id="kitty"), to_app=True)
case(8, lambda d: d.update(scope_id=uid(1)), to_app=True)
case(9, lambda d: d.update(scope_id=uid(2)), to_host=True)
case(10, lambda d: d.update(host_observation_id=uid(90)), to_app=True)
case(11, lambda d: d.update(nonce=uid(91)), to_app=True)
case(12, lambda d: d.update(instance_key="bad"), to_app=True)
case(13, lambda d: d.update(namespace_key="profile"), to_app=True)
case(14, lambda d: d.update(inner_item_count=True), to_app=True)
case(15, lambda d: d.update(inner_item_count=-1), to_app=True)
case(16, lambda d: d.update(inner_item_count=9000), to_app=True)
case(17, lambda d: d.update(instance_key=None), to_app=True)
case(18, lambda d: d.update(scope_id=[]), to_app=True)
case(19, lambda d: None, now=1013)
case(20, lambda d: None, now=999)
case(21, lambda d: d.update(instance_key=uid(9999)), to_app=True, expect_error=False)

cancel = SyntheticHandshakeSession(uid(500), adapter_manifests=extra)
nonce, host_echo, app_echo = fixture(cancel, 200, adapter="brave", app="brave-browser")
assert cancel.cancel(nonce)["status"]=="cancelled_fixture"
refuses(lambda: cancel.verify(nonce, host_echo, app_echo, now_seconds=1001))
refuses(lambda: cancel.cancel(nonce))
refuses(lambda: fixture(cancel, 200, adapter="brave", app="brave-browser"))

denied = SyntheticHandshakeSession(uid(501), adapter_manifests=extra)
options = {"nonce": uid(100), "host_observation_id": uid(200),
           "app_id": "brave-browser", "adapter_id": "brave",
           "host_target": "linux_wayland", "now_seconds": 1000,
           "ttl_seconds": 10, "permission_fixture": "explicit_synthetic_allow"}
def bad_begin(**changes):
    args = dict(options, **changes)
    refuses(lambda: denied.begin(**args))
for invalid in ("denied", "not_requested", "implicit", True, None):
    bad_begin(permission_fixture=invalid)
bad_begin(adapter_id="kitty")
bad_begin(adapter_id="none")
bad_begin(adapter_id="unknown")
bad_begin(host_target="macos")
bad_begin(host_target="android")
bad_begin(ttl_seconds=0)
bad_begin(ttl_seconds=31)
bad_begin(ttl_seconds=True)
bad_begin(app_id="brave-browser\nPRIVATE")
bad_begin(nonce="bad")
bad_begin(now_seconds=True)
bad_begin(now_seconds=float("nan"))
bad_begin(now_seconds=-1)
assert not denied.pending and not denied.all_nonces

# Duplicate live-host correlation and app instance claims are refused.
multi = SyntheticHandshakeSession(uid(510), adapter_manifests=extra)
n1, h1, a1 = fixture(multi, 300, adapter="brave", app="brave-browser")
refuses(lambda: fixture(multi, 300, adapter="brave", app="brave-browser"))
multi.verify(n1, h1, a1, now_seconds=1001)
n2, h2, a2 = fixture(multi, 301, adapter="brave", app="brave-browser")
a2["namespace_key"] = a1["namespace_key"]
a2["instance_key"] = a1["instance_key"]
refuses(lambda: multi.verify(n2,h2,a2,now_seconds=1001))
assert not multi.pending
print("MACHINE M2D2: 24 MULTI-APP SCOPED HANDSHAKE FIXTURES PASS / NO REAL AUTHORITY")
