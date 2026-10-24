#!/usr/bin/env python3
"""M2a pure tests: 17 Brave + 4 Kitty, no window-ID guesses or live reads."""
import copy
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineWindowMultiplicity import compare_v1_layout, InventoryError

rect = {"x": 0, "y": 0, "width": 1920, "height": 1080}
outs = [{"connector": "DP-5", "rect": rect}]
wss = [{"name": "1", "output": "DP-5"},
       {"name": "2", "output": "DP-5"},
       {"name": "3", "output": "DP-5"}]
def w(app, ws, floating=False):
    return {"app_id": app, "workspace": ws, "floating": floating}

windows = (
    [w("brave-browser", "1") for _ in range(8)] +
    [w("brave-browser", "2") for _ in range(6)] +
    [w("brave-browser", "3") for _ in range(3)] +
    [w("kitty", "1") for _ in range(2)] +
    [w("kitty", "2")] + [w("kitty", "3")]
)
saved = {"schema_version": 1, "kind": "sway-layout-selection-preview",
         "preview_only": True, "captured_at_utc": "2026-10-24T12:00:00+00:00",
         "label": "Example 7", "outputs": outs, "workspaces": wss,
         "windows": windows}
def live(windows, outputs=outs, workspaces=wss):
    return {"outputs": [
        {"name": o["connector"], "rect": o["rect"]} for o in outputs],
        "workspaces": copy.deepcopy(workspaces),
        "windows": copy.deepcopy(windows)}
def app(result, name):
    return next(x for x in result["apps"] if x["app_id"] == name)
def rejects(bad_saved, bad_live):
    try:
        compare_v1_layout(bad_saved, bad_live)
        raise AssertionError("accepted invalid/private state")
    except InventoryError:
        pass

original = copy.deepcopy(saved)
data = live(list(reversed(windows)))
original_live = copy.deepcopy(data)
report = compare_v1_layout(saved, data)
assert report["kind"] == "machine-multi-instance-layout-inventory"
assert report["status"] == "layout_counts_match_identity_unverified"
assert report["layout_counts_match"] is True
assert report["window_placement_counts_match"] is True
assert report["monitor_layout_matches"] and report["workspace_layout_matches"]
assert report["session_identity_verified"] is False
assert report["exact_session_match"] is False
assert report["safe_actions"] == []
assert report["no_launch_or_move_approved"] is True
assert report["counts"] == {
    "saved_windows": 21, "live_windows": 21, "matching_placement_count": 21,
    "missing_saved_positions": 0, "extra_live_positions": 0,
    "apps_in_saved": 2, "apps_in_live": 2,
}
assert app(report, "brave-browser")["matching_placement_count"] == 17
assert app(report, "kitty")["matching_placement_count"] == 4
assert all(x["state"] == "layout_counts_match_identity_unverified"
           and not x["per_window_identity_verified"]
           and not x["per_tab_identity_verified"]
           and x["safe_window_actions"] == [] for x in report["apps"])
assert saved == original and data == original_live
assert "con_id" not in str(report) and "PRIVATE" not in str(report)

# Same counts of Brave overall, but two are on wrong workspaces; do not
# "pair" them, guess which are which or claim exact matching.
moved = copy.deepcopy(windows)
for idx in (0, 1):
    moved[idx]["workspace"] = "3"
shifted = compare_v1_layout(saved, live(moved))
assert shifted["status"] == "layout_differs_identity_unverified"
assert shifted["counts"]["matching_placement_count"] == 19
assert shifted["counts"]["missing_saved_positions"] == 2
assert shifted["counts"]["extra_live_positions"] == 2
assert app(shifted, "brave-browser")["saved_windows"] == 17
assert app(shifted, "brave-browser")["live_windows"] == 17
assert app(shifted, "brave-browser")["missing_saved_positions"] == 2
assert app(shifted, "brave-browser")["extra_live_positions"] == 2
assert shifted["safe_actions"] == []

# Missing individual Brave instances, extras, app entirely closed.
missing = compare_v1_layout(saved, live(windows[2:]))
assert missing["counts"]["saved_windows"] == 21
assert missing["counts"]["live_windows"] == 19
assert app(missing, "brave-browser")["missing_saved_positions"] == 2
assert app(missing, "brave-browser")["extra_live_positions"] == 0
none_kitty = compare_v1_layout(saved, live(windows[:17]))
assert app(none_kitty, "kitty")["state"] == "app_not_running"
assert app(none_kitty, "kitty")["missing_saved_positions"] == 4
assert none_kitty["safe_actions"] == []
extra = compare_v1_layout(saved, live(windows + [w("brave-browser", "3"), w("firefox", "2")]))
assert app(extra, "brave-browser")["extra_live_positions"] == 1
assert app(extra, "firefox")["state"] == "extra_live_app_not_in_checkpoint"
assert app(extra, "firefox")["saved_windows"] == 0
assert app(extra, "firefox")["extra_live_positions"] == 1
assert extra["counts"]["extra_live_positions"] == 2

# Floating mismatch is a placement difference, not evidence of identity.
float_changed = copy.deepcopy(windows)
float_changed[-1]["floating"] = True
float_result = compare_v1_layout(saved, live(float_changed))
assert float_result["counts"]["matching_placement_count"] == 20
assert float_result["counts"]["missing_saved_positions"] == 1
assert float_result["counts"]["extra_live_positions"] == 1

# A matching number of window positions does NOT imply monitor/workspace match.
wrong_monitor = copy.deepcopy(outs)
wrong_monitor[0]["rect"]["width"] = 1919
monitor_result = compare_v1_layout(saved, live(windows, outputs=wrong_monitor))
assert not monitor_result["monitor_layout_matches"]
assert monitor_result["window_placement_counts_match"]
assert not monitor_result["layout_counts_match"]
ws_changed = copy.deepcopy(wss)
ws_changed[2]["output"] = "OTHER"
rejects(saved, live(windows, workspaces=ws_changed))
additional_output = outs + [
    {"connector": "HDMI-A-1",
     "rect": {"x": 1920, "y": 0, "width": 1360, "height": 768}}]
extra_output = compare_v1_layout(saved, live(windows, outputs=additional_output))
assert not extra_output["layout_counts_match"] and extra_output["window_placement_counts_match"]

# The old v1 single instance is also only *placement* identity.
single = copy.deepcopy(saved)
single["windows"] = [w("kitty", "1")]
single_r = compare_v1_layout(single, live(single["windows"]))
assert single_r["layout_counts_match"]
assert single_r["exact_session_match"] is False
assert single_r["safe_actions"] == []

# Strict allowlist prevents accidental title, PID, URL or command capture.
rejects(dict(saved, secret="PRIVATE"), live(windows))
rejects(saved, dict(live(windows), extra="PRIVATE"))
rejects(saved, live(windows + [dict(w("kitty", "1"), title="PRIVATE")]))
rejects(saved, live(windows + [dict(w("kitty", "1"), pid=1234)]))
rejects(saved, live(windows + [dict(w("kitty", "1"), url="https://private")]))
rejects(saved, live(windows + [dict(w("kitty", "1"), command="curl")]))
rejects(saved, live(windows + [dict(w("kitty", "1"), floating=1)]))
rejects(saved, {"outputs": [], "workspaces": "bad", "windows": []})
rejects(saved, live(windows * 30))

print("MACHINE M2A: 17 BRAVE + 4 KITTY MULTI-INSTANCE PLACEMENT PASS / NO IDENTITY CLAIM")
