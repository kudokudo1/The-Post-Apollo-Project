#!/usr/bin/env python3
"""M2c synthetic mixed-application adapter declarations, no real app access."""
import copy
import json
from pathlib import Path
import sys
import uuid

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineAdapterRegistry import (
    RegistryError, build_registry, find_declared_adapter,
    list_schema_capabilities, validate_manifest,
)
from MachineSessionIdentityV2 import (
    SidecarError, validate_sidecar, describe_coverage,
)


def key(n):
    return str(uuid.UUID(int=n))


def manifest(adapter, family, app, kinds, platforms):
    return {"adapter_id": adapter, "family": family,
            "app_ids": [app], "item_kinds": kinds,
            "target_hosts": platforms, "state": "schema_only"}


extra_adapters = [
    manifest("browser.firefox", "browser", "firefox",
             ["browser_tab", "browser_group"], ["linux_wayland", "windows", "macos"]),
    manifest("browser.chrome", "browser", "google-chrome",
             ["browser_tab"], ["linux_x11", "windows"]),
    manifest("terminal.ghostty", "terminal", "com.mitchellh.ghostty",
             ["terminal_tab", "terminal_split"], ["linux_wayland", "macos"]),
    manifest("editor.vscode", "editor", "code",
             ["editor_tab", "editor_group"], ["linux_wayland", "windows", "macos"]),
    manifest("editor.zed", "editor", "dev.zed.Zed",
             ["editor_tab"], ["linux_wayland", "macos"]),
    manifest("office.libreoffice", "office", "libreoffice-writer",
             ["document_tab"], ["linux_wayland", "windows", "macos"]),
    manifest("future.custom_app", "custom_family", "custom-app",
             ["custom_session_item"], ["linux_wayland"]),
]
registry = build_registry(extra_adapters)
assert len(registry) == 9
assert registry["brave"]["family"] == "browser"
assert registry["kitty"]["family"] == "terminal"
assert registry["terminal.ghostty"]["state"] == "schema_only"
assert registry["editor.vscode"]["item_kinds"] == ("editor_tab", "editor_group")
assert find_declared_adapter(registry, "browser.firefox", "firefox")["family"] == "browser"
assert find_declared_adapter(registry, "none", "unfamiliar-app")["family"] == "generic"
catalog = list_schema_capabilities(extra_adapters)
assert catalog["installed_adapter_count"] == 0
assert catalog["active_runtime_adapters"] == []
assert not catalog["live_capture_supported"]
assert not catalog["live_reopen_supported"]
assert all(x["state"] == "schema_only" for x in catalog["descriptors"])

def window(n, app, workspace, adapter, kind):
    return {
        "window_key": key(n), "app_id": app,
        "workspace": workspace, "floating": False,
        "identity": {
            "adapter": adapter,
            "status": "reported" if adapter != "none" else "not_requested",
            "namespace_key": key(8000+n) if adapter != "none" else None,
            "instance_key": key(10000+n) if adapter != "none" else None,
        },
        "capabilities": {
            "window_identity": "reported" if adapter != "none" else "not_requested",
            "inner_items": "reported" if kind else "not_requested",
            "reopen_window": "unsupported",
        },
        "items": ([{"item_key": key(20000+n), "kind": kind,
                    "position": 0, "adapter_item_key": None}] if kind else []),
    }


rows = (
    [window(n, "brave-browser", "1" if n < 10 else "2",
            "brave", "browser_tab") for n in range(1,18)] +
    [window(n, "kitty", "3", "kitty", "terminal_tab") for n in range(18,22)] +
    [window(22, "firefox", "2", "browser.firefox", "browser_tab"),
     window(23, "google-chrome", "2", "browser.chrome", "browser_tab"),
     window(24, "com.mitchellh.ghostty", "1", "terminal.ghostty", "terminal_split"),
     window(25, "code", "1", "editor.vscode", "editor_tab"),
     window(26, "dev.zed.Zed", "1", "editor.zed", "editor_tab"),
     window(27, "libreoffice-writer", "2", "office.libreoffice", "document_tab"),
     window(28, "custom-app", "1", "future.custom_app", "custom_session_item"),
     window(29, "unknown-app", "3", "none", None)]
)
checkpoint = key(42)
sidecar = {"schema_version": 2, "kind": "machine-session-identity-sidecar",
           "checkpoint_id": checkpoint, "windows": rows}
v1 = {"schema_version": 1, "kind": "sway-layout-selection-preview",
      "preview_only": True, "label": "Example",
      "captured_at_utc": "2026-10-24T12:00:00+00:00",
      "outputs": [{"connector": "DP-5", "rect": {
          "x": 0, "y": 0, "width": 2560, "height": 1440}}],
      "workspaces": [{"name": name, "output": "DP-5"}
                     for name in ("1", "2", "3")],
      "windows": [{"app_id": x["app_id"], "workspace": x["workspace"],
                   "floating": x["floating"]} for x in rows]}
before = copy.deepcopy(sidecar)
before_v1 = copy.deepcopy(v1)
accepted = validate_sidecar(sidecar, v1_checkpoint=v1,
                            adapter_manifests=extra_adapters)
assert accepted == sidecar
assert before == sidecar and before_v1 == v1
coverage = describe_coverage(sidecar, adapter_manifests=extra_adapters)
assert coverage["window_count"] == 29
assert coverage["identity_claims"]["reported"] == 28
assert coverage["identity_claims"]["not_requested"] == 1
assert coverage["exact_session_match"] is False
assert coverage["safe_actions"] == []
assert coverage["per_window_identity_verified"] is False
assert coverage["executable"] is False
assert "firefox" not in json.dumps(coverage)
assert "custom-app" not in json.dumps(coverage)

def refuses(mutator, manifests=extra_adapters):
    copy = __import__("copy").deepcopy(sidecar)
    mutator(copy)
    try:
        validate_sidecar(copy, v1_checkpoint=v1, adapter_manifests=manifests)
    except SidecarError:
        return
    raise AssertionError("unsafe app adapter or item kind accepted")

# Unregistered names cannot invent an app-specific authority.
refuses(lambda p: p["windows"][21]["identity"].update(adapter="browser.unknown"),
        [])
refuses(lambda p: p["windows"][21]["identity"].update(adapter="browser.unknown"))
refuses(lambda p: p["windows"][22]["identity"].update(adapter="browser.firefox"))
refuses(lambda p: p["windows"][24]["identity"].update(adapter="terminal.ghostty"))
refuses(lambda p: p["windows"][24]["items"][0].update(kind="terminal_split"))
refuses(lambda p: p["windows"][23]["items"][0].update(kind="browser_tab"))
refuses(lambda p: p["windows"][27]["identity"].update(adapter="editor.vscode"))
refuses(lambda p: p["windows"][27]["items"].append({
    "item_key": key(40000), "kind": "custom_session_item",
    "position": 1, "adapter_item_key": None}))
refuses(lambda p: p["windows"][27]["identity"].update(status="reported"))
refuses(lambda p: p["windows"][27]["capabilities"].update(reopen_window="reported"))
refuses(lambda p: p["windows"][21]["items"][0].update(url="SECRET"))
refuses(lambda p: p["windows"][25]["items"][0].update(document_path="/private"))
refuses(lambda p: p["windows"][23].update(workspace="3"))

# A generic fallback can record layout only for a completely unknown app.
unknown = window(33, "unregistered-sandbox", "2", "none", None)
copy_unknown = copy.deepcopy(sidecar)
copy_unknown["windows"].append(unknown)
validate_sidecar(copy_unknown, adapter_manifests=extra_adapters)
assert all(not x["safe_actions"] for x in [])  # no app execution exists

def bad_manifest(m):
    try:
        validate_manifest(m)
    except RegistryError:
        return
    raise AssertionError("invalid manifest accepted")

def bad_registry(m):
    try:
        build_registry(m)
    except RegistryError:
        return
    raise AssertionError("invalid registry accepted")

bad_manifest(dict(extra_adapters[0], state="installed"))
bad_manifest(dict(extra_adapters[0], state="active"))
bad_manifest(dict(extra_adapters[0], command="bash"))
bad_manifest(dict(extra_adapters[0], python_module="malicious"))
bad_manifest(dict(extra_adapters[0], app_ids=["firefox", "firefox"]))
bad_manifest(dict(extra_adapters[0], app_ids=[""]))
bad_manifest(dict(extra_adapters[0], item_kinds=["browser_tab"]*2))
bad_manifest(dict(extra_adapters[0], item_kinds=["browser_tab", "unsafe\n"] ))
bad_manifest(dict(extra_adapters[0], target_hosts=["android"]))
bad_manifest(dict(extra_adapters[0], target_hosts=["linux_wayland", "linux_wayland"]))
bad_manifest(dict(extra_adapters[0], adapter_id="none"))
bad_manifest(dict(extra_adapters[0], adapter_id="Browser.Firefox"))
bad_manifest(dict(extra_adapters[0], adapter_id="../x"))
bad_manifest(dict(extra_adapters[0], family=[]))
bad_registry([extra_adapters[0], extra_adapters[0]])
bad_registry([dict(extra_adapters[0], adapter_id="brave")])
bad_registry([dict(extra_adapters[0], adapter_id="x"+str(n)) for n in range(65)])
bad_registry("not a registry")
print("MACHINE M2C: MIXED 29-WINDOW UNIVERSAL ADAPTER DECLARATIONS PASS / ZERO ACTIONS")
