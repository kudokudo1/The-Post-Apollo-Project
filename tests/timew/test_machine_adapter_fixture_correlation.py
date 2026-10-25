#!/usr/bin/env python3
"""Fixture-only M2d: multiple browser/terminal/editor windows correlate safely."""
import copy
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineAdapterFixtureCorrelation import (
    CorrelationError, inspect_fixture_correlations,
)

def uid(n):
    return str(uuid.UUID(int=n))

extra = [
    {"adapter_id": "browser.firefox", "family": "browser",
     "app_ids": ["firefox"], "item_kinds": ["browser_tab"],
     "target_hosts": ["linux_wayland"], "state": "schema_only"},
    {"adapter_id": "editor.vscode", "family": "editor",
     "app_ids": ["code"], "item_kinds": ["editor_tab"],
     "target_hosts": ["linux_wayland"], "state": "schema_only"},
]

def spec(n):
    if n <= 17: return "brave-browser", "brave", "browser_tab", "1" if n < 10 else "2", 500
    if n <= 21: return "kitty", "kitty", "terminal_tab", "3", 501
    if n == 22: return "firefox", "browser.firefox", "browser_tab", "2", 502
    return "code", "editor.vscode", "editor_tab", "1", 503

rows = []
hosts = []
reports = []
for n in range(1,24):
    app, adapter, kind, workspace, namespace = spec(n)
    row = {
        "window_key": uid(100+n),
        "app_id": app, "workspace": workspace, "floating": False,
        "identity": {"adapter": adapter, "status": "reported",
                     "namespace_key": uid(namespace),
                     "instance_key": uid(1000+n)},
        "capabilities": {"window_identity": "reported",
                         "inner_items": "reported", "reopen_window": "unsupported"},
        "items": [{"item_key": uid(2000+n), "kind": kind,
                   "position": 0, "adapter_item_key": None}],
    }
    rows.append(row)
    hosts.append({"observation_id": uid(3000+n), "app_id": app,
                  "workspace": workspace, "floating": False,
                  "challenge": uid(4000+n)})
    reports.append({"challenge": uid(4000+n), "adapter_id": adapter,
                    "app_id": app, "namespace_key": uid(namespace),
                    "instance_key": uid(1000+n), "inner_item_count": 1})

sidecar = {"schema_version": 2, "kind": "machine-session-identity-sidecar",
           "checkpoint_id": uid(42), "windows": rows}
host = {"schema_version": 1, "kind": "synthetic-host-window-observations",
        "scope_id": uid(9000), "windows": hosts}
apps = {"schema_version": 1, "kind": "synthetic-app-session-observations",
        "scope_id": uid(9000), "observations": reports}
original = copy.deepcopy((sidecar, host, apps))
report = inspect_fixture_correlations(
    sidecar, {**host, "windows": list(reversed(hosts))},
    {**apps, "observations": list(reversed(reports))}, adapter_manifests=extra)
assert len(report["windows"]) == 23
assert report["saved_windows"] == 23 and report["fixture_correlations"] == 23
assert report["unresolved_saved_windows"] == 0
assert report["unlinked_host_windows"] == 0
assert report["extra_reported_instances"] == 0
assert report["input_provenance"] == "synthetic_untrusted"
assert report["read_only"] and not report["executable"]
assert not report["live_identity_verified"] and not report["exact_session_match"]
assert not report["capture_enabled"] and not report["restore_enabled"]
assert not report["launch_enabled"] and report["safe_actions"] == []
assert all(w["state"] == "correlated_in_synthetic_fixture"
           and w["placement"] == "placement_fields_match"
           and w["inner_items"] == "item_counts_match_contents_unverified"
           and not w["live_identity_verified"] and w["safe_actions"] == []
           for w in report["windows"])
assert report["windows"][0]["synthetic_host_observation_id"] == uid(3001)
assert original == (sidecar, host, apps)

# Matching app counts and placements do not imply correctly identified
# instances. Swap reports between two Brave windows while preserving hosts.
swapped = copy.deepcopy(apps)
swapped["observations"][0]["instance_key"], swapped["observations"][1]["instance_key"] = (
    swapped["observations"][1]["instance_key"], swapped["observations"][0]["instance_key"])
swapped_result = inspect_fixture_correlations(sidecar, host, swapped, adapter_manifests=extra)
assert swapped_result["fixture_correlations"] == 23
assert swapped_result["windows"][0]["synthetic_host_observation_id"] == uid(3002)
assert swapped_result["windows"][1]["synthetic_host_observation_id"] == uid(3001)
assert not swapped_result["exact_session_match"]

# A misplaced instance is descriptive, with no move/restore permissions.
misplaced = copy.deepcopy(host)
misplaced["windows"][0]["workspace"] = "3"
moved = inspect_fixture_correlations(sidecar, misplaced, apps, adapter_manifests=extra)
assert moved["windows"][0]["placement"] == "placement_fields_differ"
assert moved["safe_actions"] == []

# Missing adapter observations cannot be interpreted as absent applications.
unlinked = copy.deepcopy(apps)
unlinked["observations"].pop(0)
left = inspect_fixture_correlations(sidecar, host, unlinked, adapter_manifests=extra)
assert left["fixture_correlations"] == 22
assert left["unlinked_host_windows"] == 1
assert left["unresolved_saved_windows"] == 1
assert left["windows"][0]["state"] == "no_fixture_correlation"
assert left["safe_actions"] == []

# Generic unknown app can retain layout fields but not claim an inner session.
generic = copy.deepcopy(sidecar)
generic["windows"].append({
    "window_key": uid(999), "app_id": "unregistered-app", "workspace": "1",
    "floating": False,
    "identity": {"adapter": "none", "status": "not_requested",
                 "namespace_key": None, "instance_key": None},
    "capabilities": {"window_identity": "not_requested", "inner_items": "not_requested",
                     "reopen_window": "not_requested"}, "items": []})
g = inspect_fixture_correlations(generic, host, apps, adapter_manifests=extra)
assert g["windows"][-1]["state"] == "identity_not_available"
assert g["unresolved_saved_windows"] == 1
assert g["fixture_correlations"] == 23

# Reported inner-item counts do not reveal or prove tab contents.
different = copy.deepcopy(apps)
different["observations"][0]["inner_item_count"] = 2
result = inspect_fixture_correlations(sidecar, host, different, adapter_manifests=extra)
assert result["windows"][0]["inner_items"] == "item_counts_differ"
assert not result["exact_session_match"]

# Extra app observations are inventory evidence, never launch/delete plans.
extra_host = copy.deepcopy(host)
extra_apps = copy.deepcopy(apps)
extra_host["windows"].append({
    "observation_id": uid(3999), "app_id": "brave-browser",
    "workspace": "2", "floating": False, "challenge": uid(4999)})
extra_apps["observations"].append({
    "challenge": uid(4999), "adapter_id": "brave", "app_id": "brave-browser",
    "namespace_key": uid(500), "instance_key": uid(1999),
    "inner_item_count": 4})
e = inspect_fixture_correlations(sidecar, extra_host, extra_apps, adapter_manifests=extra)
assert e["extra_reported_instances"] == 1
assert e["safe_actions"] == []

def rejects(*, edited_sidecar=None, edited_host=None, edited_apps=None, manifests=extra):
    try:
        inspect_fixture_correlations(
            edited_sidecar if edited_sidecar is not None else sidecar,
            edited_host if edited_host is not None else host,
            edited_apps if edited_apps is not None else apps,
            adapter_manifests=manifests)
    except CorrelationError:
        return
    raise AssertionError("unsafe synthetic observation accepted")

def bad_host(edit):
    x = copy.deepcopy(host); edit(x); rejects(edited_host=x)
def bad_app(edit):
    x = copy.deepcopy(apps); edit(x); rejects(edited_apps=x)

bad_host(lambda x: x.update(kind="live_authenticated"))
bad_host(lambda x: x.update(scope_id=uid(1)))
bad_host(lambda x: x.update(secret="PRIVATE"))
bad_host(lambda x: x["windows"][0].update(title="PRIVATE"))
bad_host(lambda x: x["windows"][0].update(pid=1234))
bad_host(lambda x: x["windows"][0].update(floating=1))
bad_host(lambda x: x["windows"][0].update(challenge=x["windows"][1]["challenge"]))
bad_host(lambda x: x["windows"][0].update(observation_id=x["windows"][1]["observation_id"]))
bad_host(lambda x: x["windows"].append(copy.deepcopy(x["windows"][0])))
bad_host(lambda x: x.update(windows=x["windows"]*24))
bad_app(lambda x: x.update(scope_id=uid(1)))
bad_app(lambda x: x.update(status="trusted"))
bad_app(lambda x: x["observations"][0].update(url="https://private"))
bad_app(lambda x: x["observations"][0].update(command="sudo command"))
bad_app(lambda x: x["observations"][0].update(challenge=uid(7999)))
bad_app(lambda x: x["observations"][0].update(challenge=x["observations"][1]["challenge"]))
bad_app(lambda x: x["observations"][0].update(app_id="kitty"))
bad_app(lambda x: x["observations"][0].update(adapter_id="kitty"))
bad_app(lambda x: x["observations"][0].update(adapter_id="unregistered"))
bad_app(lambda x: x["observations"][0].update(adapter_id="none"))
bad_app(lambda x: x["observations"][0].update(inner_item_count=True))
bad_app(lambda x: x["observations"][0].update(inner_item_count=-1))
bad_app(lambda x: x["observations"][0].update(inner_item_count=9000))
bad_app(lambda x: x["observations"][0].update(instance_key=x["observations"][1]["instance_key"]))
bad_app(lambda x: x["observations"][0].update(namespace_key="browser-profile-name"))
bad_app(lambda x: x["observations"].append(copy.deepcopy(x["observations"][0])))
bad_app(lambda x: x.update(observations=x["observations"]*30))
rejects(manifests=[])
assert (sidecar,host,apps) == original
print("MACHINE M2D: 23 MULTI-APP SYNTHETIC WINDOW CORRELATIONS PASS / ZERO LIVE AUTHORITY")
