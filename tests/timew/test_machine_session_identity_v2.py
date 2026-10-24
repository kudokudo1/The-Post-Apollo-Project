#!/usr/bin/env python3
"""M2b synthetic v2 proposal tests: 17 Brave / 4 Kitty, v1 untouched."""
import copy
import json
from pathlib import Path
import sys
import uuid

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineSessionIdentityV2 import (
    SidecarError, validate_sidecar, describe_coverage,
)


def key(n):
    return str(uuid.UUID(int=n))


def window(n, app, ws, *, adapter, items_count=0):
    known = adapter != "none"
    identity = {
        "adapter": adapter, "status": "reported" if known else "not_requested",
        "namespace_key": key(9001 if adapter == "brave" else 9002) if known else None,
        "instance_key": key(10000 + n) if known else None,
    }
    caps = {
        "window_identity": "reported" if known else "not_requested",
        "inner_items": "partial" if items_count else "not_requested",
        "reopen_window": "unsupported",
    }
    kind = "browser_tab" if adapter == "brave" else "terminal_tab"
    return {
        "window_key": key(n), "app_id": app, "workspace": ws, "floating": False,
        "identity": identity, "capabilities": caps,
        "items": [
            {"item_key": key(20000 + n * 20 + position), "kind": kind,
             "position": position, "adapter_item_key": None}
            for position in range(items_count)],
    }


rows = (
    [window(n, "brave-browser", "1" if n <= 8 else "2" if n <= 14 else "3",
            adapter="brave", items_count=2) for n in range(1, 18)] +
    [window(n, "kitty", "1" if n < 20 else "3",
            adapter="kitty", items_count=1) for n in range(18, 22)]
)
record = {
    "schema_version": 2, "kind": "machine-session-identity-sidecar",
    "checkpoint_id": key(42), "windows": rows,
}
v1 = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "My desktop",
    "captured_at_utc": "2026-10-24T12:00:00+00:00",
    "outputs": [{"connector": "DP-5",
                 "rect": {"x": 0, "y": 0, "width": 2560, "height": 1440}}],
    "workspaces": [{"name": n, "output": "DP-5"} for n in ("1", "2", "3")],
    "windows": [
        {"app_id": w["app_id"], "workspace": w["workspace"],
         "floating": w["floating"]} for w in rows],
}
original_v1 = copy.deepcopy(v1)
original_v2 = copy.deepcopy(record)
cleaned = validate_sidecar(record, v1_checkpoint=v1)
assert cleaned == record
assert v1 == original_v1 and record == original_v2
assert len(cleaned["windows"]) == 21
assert len(set(w["window_key"] for w in cleaned["windows"])) == 21
assert len(set(w["identity"]["instance_key"] for w in cleaned["windows"])) == 21
assert len([w for w in cleaned["windows"] if w["app_id"] == "brave-browser"]) == 17
assert len([w for w in cleaned["windows"] if w["app_id"] == "kitty"]) == 4
assert all(isinstance(w["identity"]["namespace_key"], str)
           for w in cleaned["windows"])
coverage = describe_coverage(record)
assert coverage["window_count"] == 21
assert coverage["inner_item_count"] == 38
assert coverage["identity_claims"]["reported"] == 21
assert coverage["exact_session_match"] is False
assert coverage["per_window_identity_verified"] is False
assert coverage["safe_actions"] == []
assert coverage["v1_storage_unchanged"] is True
assert coverage["read_only"] and not coverage["executable"]
assert "app_id" not in str(coverage)
assert "brave-browser" not in str(coverage)
assert "PRIVATE" not in json.dumps(cleaned)

def rejected(variant, legacy=None):
    try:
        validate_sidecar(variant, v1_checkpoint=legacy)
    except SidecarError:
        return
    raise AssertionError("invalid identity sidecar accepted")

def changed(edit, legacy=None):
    p = copy.deepcopy(record)
    edit(p)
    rejected(p, legacy)

changed(lambda p: p.update(schema_version=1))
changed(lambda p: p.update(schema_version=True))
changed(lambda p: p.update(kind="sway-layout-selection-preview"))
changed(lambda p: p.update(checkpoint_id="nonsense"))
changed(lambda p: p.update(checkpoint_id=key(42).upper()))
changed(lambda p: p.update(private_data="SECRET"))
changed(lambda p: p["windows"][0].update(title="PRIVATE"))
changed(lambda p: p["windows"][0].update(pid=789))
changed(lambda p: p["windows"][0].update(url="https://example.com"))
changed(lambda p: p["windows"][0].update(command="bash"))
changed(lambda p: p["windows"][0].update(profile_path="/home/user/.config/Brave"))
changed(lambda p: p["windows"][0]["identity"].update(profile_name="Personal"))
changed(lambda p: p["windows"][0]["identity"].update(instance_key=key(10002)))
changed(lambda p: p["windows"][0].update(window_key=p["windows"][1]["window_key"]))
changed(lambda p: p["windows"][0].update(floating=1))
changed(lambda p: p["windows"][0].update(app_id="bad\napp"))
changed(lambda p: p["windows"][0].update(workspace=""))
changed(lambda p: p["windows"][0]["identity"].update(adapter="firefox"))
changed(lambda p: p["windows"][0]["identity"].update(status="verified"))
changed(lambda p: p["windows"][0]["identity"].update(status="denied"))
changed(lambda p: p["windows"][0]["identity"].update(instance_key="not-a-uuid"))
changed(lambda p: p["windows"][0]["identity"].update(namespace_key="private-profile"))
changed(lambda p: p["windows"][0]["capabilities"].update(reopen_window="executable"))
changed(lambda p: p["windows"][0]["capabilities"].update(launch_recipe="unsafe"))
changed(lambda p: p["windows"][0]["items"][0].update(url="https://private"))
changed(lambda p: p["windows"][0]["items"][0].update(title="private"))
changed(lambda p: p["windows"][0]["items"][0].update(kind="terminal_tab"))
changed(lambda p: p["windows"][0]["items"][0].update(position=0.5))
changed(lambda p: p["windows"][0]["items"][0].update(position=True))
changed(lambda p: p["windows"][0]["items"][0].update(item_key=p["windows"][0]["items"][1]["item_key"]))
changed(lambda p: p["windows"][0]["items"][0].update(position=p["windows"][0]["items"][1]["position"]))
changed(lambda p: p["windows"][0]["items"][0].update(adapter_item_key="SECRET"))
changed(lambda p: p["windows"][0]["items"][0].update(kind=[]))
changed(lambda p: p["windows"].append(copy.deepcopy(p["windows"][0])))
changed(lambda p: p["windows"].extend(copy.deepcopy(p["windows"]) * 25))
changed(lambda p: p["windows"][0].update(items=p["windows"][0]["items"] * 3000))
changed(lambda p: p["windows"][0].update(items="not-array"))
changed(lambda p: p["windows"][0].update(items=[{"item_key": key(567),
              "kind": "browser_tab", "position": -1, "adapter_item_key": None}]))
changed(lambda p: p["windows"][0].update(identity={"adapter": "none"}))
changed(lambda p: p["windows"][0].update(extra="private"))
changed(lambda p: p["windows"][0]["identity"].update(status="unsupported",
                                                     instance_key=None,
                                                     namespace_key=None))
changed(lambda p: p["windows"][0].update(app_id="not-brave"), v1)
changed(lambda p: p["windows"][0].update(workspace="3"), v1)
changed(lambda p: p["windows"][0].update(floating=True), v1)
changed(lambda p: p["windows"].pop(), v1)

legacy_modified = copy.deepcopy(v1)
legacy_modified["windows"][0]["title"] = "PRIVATE"
rejected(record, legacy_modified)

# Unknown and denied are legitimate *non-identifying* data, not invalid
# user setups. They must not inherit fictitious IDs from the adapter.
unknown = copy.deepcopy(record)
w = unknown["windows"][0]
w["identity"] = {"adapter": "none", "status": "not_requested",
                 "namespace_key": None, "instance_key": None}
w["capabilities"] = {"window_identity": "not_requested",
                     "inner_items": "not_requested", "reopen_window": "not_requested"}
w["items"] = []
validate_sidecar(unknown, v1_checkpoint=v1)
assert describe_coverage(unknown)["identity_claims"]["not_requested"] == 1

denied = copy.deepcopy(unknown)
denied["windows"][0]["identity"]["status"] = "denied"
denied["windows"][0]["capabilities"] = {
    "window_identity": "denied", "inner_items": "denied", "reopen_window": "denied"}
validate_sidecar(denied, v1_checkpoint=v1)
partial = copy.deepcopy(record)
partial["windows"][0]["identity"]["status"] = "partial"
partial["windows"][0]["identity"]["instance_key"] = None
validate_sidecar(partial, v1_checkpoint=v1)

# Input is only a proposed model. Even 21 distinct synthetic UUIDs do NOT
# authenticate that the same processes/tabs exist after a restart.
assert not describe_coverage(record)["exact_session_match"]
assert record == original_v2 and v1 == original_v1
print("MACHINE M2B: V2 SYNTHETIC WINDOW/TAB IDENTITY SCHEMA PASS / V1 INTACT")
