"""MACHINE v2: pure optional checkpoint scope selection.

All outputs, workspaces and windows are included by default. A custom
selection may explicitly include named monitors, workspaces and unique
checkpoint-local window keys. Selection never queries Sway, writes a file or
restores anything. The input is a *validated, current capture*; a future
customize UI must bind any selected keys to that capture and revalidate them
before the one final SAVE operation.

Tiled rectangles and split proportions retain their *original* positions.
Pruning a sibling does not mean Sway can reproduce its old rectangle without
a later geometry-aware restore planner.
"""
from __future__ import annotations

import uuid

from MachineGeometryStoreV2 import validate_geometry, GeometryStoreError

MAX_ITEMS = 512


class SelectionError(ValueError):
    pass


def _item(value, *, window):
    if not isinstance(value, str):
        raise SelectionError("INVALID SELECTION IDENTIFIER")
    if window:
        try:
            normalized = str(uuid.UUID(value))
        except (ValueError, AttributeError) as exc:
            raise SelectionError("INVALID WINDOW SELECTION KEY") from exc
        if normalized != value:
            raise SelectionError("INVALID WINDOW SELECTION KEY")
    elif not 1 <= len(value) <= 128 or any(
            ord(char) < 32 or ord(char) == 127 for char in value):
        raise SelectionError("INVALID SELECTION IDENTIFIER")
    return value


def _selected(selection, key, available, *, window=False, require_some=False):
    """None/missing selects everything; an explicit [] selects nothing."""
    if key not in selection or selection[key] is None:
        return set(available)
    given = selection[key]
    if not isinstance(given, list) or len(given) > MAX_ITEMS:
        raise SelectionError("INVALID SELECTION LIST")
    chosen = [_item(x, window=window) for x in given]
    if len(chosen) != len(set(chosen)):
        raise SelectionError("DUPLICATE SELECTION")
    result = set(chosen)
    if not result.issubset(available):
        raise SelectionError("STALE OR UNKNOWN SELECTION")
    if require_some and not result:
        raise SelectionError("NO MONITORS SELECTED")
    return result


def select_geometry(geometry, selection=None):
    """Return strict, storage-compatible geometry pruned to selected scope.

    Selection is None or dict containing optional lists:
      outputs: connector names
      workspaces: workspace names
      windows: checkpoint-local window UUIDs

    Any omitted/None list means "all that remain after parent selection".
    Explicit lists are allowlists, *not* exclusions. An empty windows list is
    allowed, so a workspace with zero selected windows can be checkpointed.

    Conflicting child/parent scopes are errors, never silent omissions.
    Every retained window must occur once in the retained tiling tree.
    """
    try:
        source = validate_geometry(geometry)
    except (GeometryStoreError, KeyError, TypeError) as exc:
        raise SelectionError("INVALID CAPTURE SOURCE") from exc
    if selection is None:
        selection = {}
    if not isinstance(selection, dict) or not set(selection).issubset(
            {"outputs", "workspaces", "windows"}):
        raise SelectionError("UNKNOWN SELECTION FIELDS")

    outputs_all = {x["connector"] for x in source["outputs"]}
    workspaces_all = {x["name"] for x in source["workspaces"]}
    windows_all = {x["window_key"] for x in source["windows"]}

    outputs = _selected(selection, "outputs", outputs_all, require_some=True)
    workspaces = _selected(selection, "workspaces", workspaces_all)
    windows = _selected(selection, "windows", windows_all, window=True)
    output_by_ws = {x["name"]: x["output"] for x in source["workspaces"]}
    workspace_by_key = {x["window_key"]: x["workspace"]
                        for x in source["windows"]}

    # Missing selectors imply "all within selected parent scopes"; supplied
    # explicit scopes are binding requests, not hints to silently drop items.
    explicit_workspaces = selection.get("workspaces") is not None
    explicit_windows = selection.get("windows") is not None
    if explicit_workspaces and any(
            output_by_ws[name] not in outputs for name in workspaces):
        raise SelectionError("WORKSPACE ON EXCLUDED MONITOR")
    workspaces = {name for name in workspaces
                  if output_by_ws[name] in outputs}
    if explicit_windows and any(
            workspace_by_key[key] not in workspaces for key in windows):
        raise SelectionError("WINDOW IN EXCLUDED WORKSPACE")
    windows = {key for key in windows
               if workspace_by_key[key] in workspaces}

    def prune(node):
        key = node["window_key"]
        # A window-bearing branch is indivisible. If a selected nested child
        # exists below an excluded window parent, final strict geometry
        # validation will reject it as missing, rather than silently saving.
        if key is not None and key not in windows:
            return None
        tiled = [part for child in node["children"]
                 if (part := prune(child)) is not None]
        floating = [part for child in node["floating_children"]
                    if (part := prune(child)) is not None]
        if key is None and not tiled and not floating:
            return None
        return dict(node, children=tiled, floating_children=floating)

    selected_workspaces = []
    for ws in source["workspaces"]:
        if ws["name"] not in workspaces:
            continue
        tiled = [part for child in ws["children"]
                 if (part := prune(child)) is not None]
        floating = [part for child in ws["floating_children"]
                    if (part := prune(child)) is not None]
        selected_workspaces.append(
            dict(ws, children=tiled, floating_children=floating))

    limited = dict(source,
                   outputs=[x for x in source["outputs"]
                            if x["connector"] in outputs],
                   workspaces=selected_workspaces,
                   windows=[x for x in source["windows"]
                            if x["window_key"] in windows])
    # Verify every selected indexed window still appears in the pruned
    # tiling/floating tree with the same workspace and exact rectangle.
    try:
        return validate_geometry(limited)
    except GeometryStoreError as exc:
        raise SelectionError("SELECTION BREAKS TILING RELATIONSHIPS") from exc
