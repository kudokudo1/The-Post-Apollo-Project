"""MACHINE M2a: pure, read-only multi-instance desktop layout inventory.

This does NOT identify individual windows. V1 checkpoints only store app_id,
workspace and floating state. Identical aggregate positions do not prove that
the *same* Brave/Kitty windows, tabs, processes or sessions are running.

Input `live_projection` must already be the restricted output of
MachineSwayRead.normalize(), not raw Sway tree. No IPC/CLI, file writes,
application launching, action planning, browser reads or journal operations.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import StoreError, validate

MAX_OUTPUTS = 16
MAX_WORKSPACES = 128
MAX_WINDOWS = 512


class InventoryError(ValueError):
    pass


def _live_document(value):
    """Use the EXISTING v1 schema validator; never relax its privacy rules."""
    if not isinstance(value, dict) or set(value) != {
            "outputs", "workspaces", "windows"}:
        raise InventoryError("INVALID ALLOWLISTED LIVE PROJECTION")
    outputs = value["outputs"]
    workspaces = value["workspaces"]
    windows = value["windows"]
    if (not isinstance(outputs, list) or len(outputs) > MAX_OUTPUTS
            or not isinstance(workspaces, list) or len(workspaces) > MAX_WORKSPACES
            or not isinstance(windows, list) or len(windows) > MAX_WINDOWS):
        raise InventoryError("OVERSIZED OR INVALID LIVE PROJECTION")
    clean_outputs = []
    for row in outputs:
        if not isinstance(row, dict) or set(row) != {"name", "rect"}:
            raise InventoryError("UNSAFE LIVE OUTPUT FIELD")
        clean_outputs.append({"connector": row["name"], "rect": row["rect"]})
    for row in workspaces:
        if not isinstance(row, dict) or set(row) != {"name", "output"}:
            raise InventoryError("UNSAFE LIVE WORKSPACE FIELD")
    for row in windows:
        if not isinstance(row, dict) or set(row) != {
                "app_id", "workspace", "floating"}:
            raise InventoryError("UNSAFE LIVE WINDOW FIELD")
    try:
        return validate({
            "schema_version": 1, "kind": "sway-layout-selection-preview",
            "preview_only": True, "captured_at_utc": "2026-01-01T00:00:00+00:00",
            "label": "LIVE", "outputs": clean_outputs,
            "workspaces": workspaces, "windows": windows,
        })
    except StoreError as exc:
        raise InventoryError("INVALID LIVE PROJECTION") from exc


def _positions(document):
    return Counter(
        (w["app_id"], w["workspace"], w["floating"])
        for w in document["windows"]
    )


def _counts_by_app(positions):
    totals = Counter()
    for (app, _, _), count in positions.items():
        totals[app] += count
    return totals


def _outputs(document):
    return {o["connector"]: tuple(o["rect"][k]
            for k in ("x", "y", "width", "height"))
            for o in document["outputs"]}


def _workspaces(document):
    return {w["name"]: w["output"] for w in document["workspaces"]}


def compare_v1_layout(saved_document, live_projection):
    """Compare multiplicities, never pair a saved window with a live window.

    The result can *describe* same placement counts, but cannot grant a move,
    declare exact session equality, recover a tab, or assert historical identity.
    """
    try:
        saved = validate(saved_document)
    except (StoreError, TypeError, KeyError) as exc:
        raise InventoryError("INVALID SAVED V1 CHECKPOINT") from exc
    live = _live_document(live_projection)

    expected = _positions(saved)
    current = _positions(live)
    saved_by_app = _counts_by_app(expected)
    live_by_app = _counts_by_app(current)
    apps = sorted(set(saved_by_app) | set(live_by_app))
    entries = []
    matched_total = 0
    for app in apps:
        saved_total = saved_by_app[app]
        live_total = live_by_app[app]
        matched = sum(min(count, current.get(position, 0))
                      for position, count in expected.items()
                      if position[0] == app)
        matched_total += matched
        missing = saved_total - matched
        additional = live_total - matched
        if saved_total and not live_total:
            state = "app_not_running"
        elif not missing and not additional:
            state = "layout_counts_match_identity_unverified"
        elif not saved_total:
            state = "extra_live_app_not_in_checkpoint"
        else:
            state = "layout_positions_differ"
        entries.append({
            "app_id": app,
            "saved_windows": saved_total,
            "live_windows": live_total,
            "matching_placement_count": matched,
            "missing_saved_positions": missing,
            "extra_live_positions": additional,
            "state": state,
            # Even one identical-looking instance has no persistent identity
            # in v1. The ambiguity is about identity, NOT invalid user setup.
            "per_window_identity_verified": False,
            "per_tab_identity_verified": False,
            "safe_window_actions": [],
        })

    monitor_match = _outputs(saved) == _outputs(live)
    workspace_match = _workspaces(saved) == _workspaces(live)
    counts_match = expected == current
    layout_match = monitor_match and workspace_match and counts_match
    saved_count = sum(saved_by_app.values())
    live_count = sum(live_by_app.values())
    return {
        "kind": "machine-multi-instance-layout-inventory",
        "schema_version": 1,
        "read_only": True, "executable": False,
        "session_identity_verified": False,
        "exact_session_match": False,
        "requires_app_specific_identity": True,
        "monitor_layout_matches": monitor_match,
        "workspace_layout_matches": workspace_match,
        "window_placement_counts_match": counts_match,
        "layout_counts_match": layout_match,
        "status": ("layout_counts_match_identity_unverified"
                   if layout_match else "layout_differs_identity_unverified"),
        "counts": {
            "saved_windows": saved_count, "live_windows": live_count,
            "matching_placement_count": matched_total,
            "missing_saved_positions": saved_count - matched_total,
            "extra_live_positions": live_count - matched_total,
            "apps_in_saved": len(saved_by_app),
            "apps_in_live": len(live_by_app),
        },
        "apps": entries,
        "safe_actions": [],
        "no_launch_or_move_approved": True,
    }
