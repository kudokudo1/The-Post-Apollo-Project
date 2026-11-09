"""MACHINE geometry v2: pure projection of one already-acquired Sway frame.

This is NOT a CLI, live capture service, database migration or restore engine.
A future authorized capture coordinator must read Sway once and allocate
checkpoint-local window UUIDs in the *same transaction* as the M2b session
identity sidecar. Sway con_ids are used only as transient lookup keys and are
never emitted. No titles, PIDs, URLs, commands, env or window contents survive.
"""
from __future__ import annotations

from collections import Counter
import math
import uuid

MAX_OUTPUTS = 16
MAX_WORKSPACES = 128
MAX_WINDOWS = 512
MAX_NODES = 4096
MAX_DEPTH = 48
MAX_CHILDREN = 512
MAX_NAME = 128
KIND = "machine-geometry-v2-proposal"
LAYOUTS = frozenset(("none", "splith", "splitv", "stacked", "tabbed",
                     "horizontal", "vertical"))


class GeometryError(ValueError):
    pass


def _text(value, *, name):
    if (not isinstance(value, str) or not 1 <= len(value) <= MAX_NAME
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise GeometryError("INVALID " + name)
    return value


def _rectangle(value, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, dict):
        raise GeometryError("MISSING OR INVALID RECTANGLE")
    result = {}
    for field in ("x", "y", "width", "height"):
        entry = value.get(field)
        if type(entry) is not int or abs(entry) > 100000:
            raise GeometryError("INVALID RECTANGLE COMPONENT")
        if field in ("width", "height") and entry < 0:
            raise GeometryError("NEGATIVE RECTANGLE SIZE")
        result[field] = entry
    return result


def _uuid(value):
    if not isinstance(value, str):
        raise GeometryError("INVALID WINDOW KEY")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise GeometryError("INVALID WINDOW KEY") from exc
    if str(parsed) != value:
        raise GeometryError("NONCANONICAL WINDOW KEY")
    return value


def _number(value, *, default=None):
    if value is None:
        return default
    if type(value) not in (int, float) or not math.isfinite(value):
        raise GeometryError("INVALID LAYOUT NUMBER")
    return float(value)


def _app_id(node):
    value = node.get("app_id")
    if value is None:
        props = node.get("window_properties")
        if isinstance(props, dict):
            value = props.get("class")
    return None if value is None else _text(value, name="APPLICATION")


def _nodes(value):
    if not isinstance(value, list) or len(value) > MAX_CHILDREN:
        raise GeometryError("INVALID TREE CHILDREN")
    return value


def project_geometry(outputs, workspaces, tree, *, window_keys):
    """Project precise rectangles and tiling hierarchy from supplied Sway JSON.

    `window_keys` maps transient positive compositor IDs to independently
    allocated checkpoint-local canonical UUIDs; its compositor keys are never
    returned. It is supplied by the same future capture transaction that
    constructs M2b identity records. This function performs no I/O.
    """
    if (not isinstance(outputs, list) or len(outputs) > MAX_OUTPUTS
            or not isinstance(workspaces, list)
            or len(workspaces) > MAX_WORKSPACES
            or not isinstance(tree, dict)
            or not isinstance(window_keys, dict)):
        raise GeometryError("INVALID CAPTURE INPUT")

    saved_outputs, active_outputs = [], set()
    for source in outputs:
        if not isinstance(source, dict) or source.get("active") is False:
            continue
        connector = _text(source.get("name"), name="OUTPUT")
        if connector in active_outputs:
            raise GeometryError("DUPLICATE OUTPUT")
        active_outputs.add(connector)
        scale = _number(source.get("scale"), default=1.0)
        if not 0.1 <= scale <= 8:
            raise GeometryError("INVALID OUTPUT SCALE")
        transform = source.get("transform", "normal")
        saved_outputs.append({
            "connector": connector, "rect": _rectangle(source.get("rect")),
            "scale": scale, "transform": _text(transform, name="TRANSFORM")})
    if not saved_outputs:
        raise GeometryError("NO ACTIVE OUTPUTS")

    declared_workspaces = {}
    for source in workspaces:
        if not isinstance(source, dict):
            raise GeometryError("INVALID WORKSPACE")
        name = _text(source.get("name"), name="WORKSPACE")
        output = _text(source.get("output"), name="WORKSPACE OUTPUT")
        if name in declared_workspaces or output not in active_outputs:
            raise GeometryError("DUPLICATE OR DISCONNECTED WORKSPACE")
        declared_workspaces[name] = output

    used_keys, used_con_ids = set(), set()
    collected, observed = [], {}
    state = {"nodes": 0}

    def build(node, *, workspace, output, floating, depth):
        if depth > MAX_DEPTH or not isinstance(node, dict):
            raise GeometryError("INVALID GEOMETRY DEPTH")
        kind = node.get("type")
        if kind not in ("con", "floating_con"):
            raise GeometryError("UNSUPPORTED WINDOW CONTAINER")
        state["nodes"] += 1
        if state["nodes"] > MAX_NODES:
            raise GeometryError("TOO MANY CONTAINERS")
        layout = node.get("layout", "none")
        if layout not in LAYOUTS:
            raise GeometryError("UNKNOWN LAYOUT")
        percent = _number(node.get("percent"))
        if percent is not None and not 0 < percent <= 1:
            raise GeometryError("INVALID SPLIT FRACTION")
        is_floating = floating or kind == "floating_con" or (
            node.get("floating") in ("user_on", "auto_on"))
        part = {
            "layout": layout, "percent": percent,
            "rect": _rectangle(node.get("rect")),
            "window_key": None, "children": [], "floating_children": [],
        }
        app = _app_id(node)
        if app is not None:
            con_id = node.get("id")
            if type(con_id) is not int or con_id <= 0:
                raise GeometryError("INVALID TRANSIENT WINDOW ID")
            if con_id in used_con_ids:
                raise GeometryError("DUPLICATE TRANSIENT WINDOW ID")
            used_con_ids.add(con_id)
            key = _uuid(window_keys.get(con_id))
            if key in used_keys:
                raise GeometryError("DUPLICATE CHECKPOINT WINDOW KEY")
            used_keys.add(key)
            part["window_key"] = key
            fullscreen = node.get("fullscreen_mode", 0)
            if type(fullscreen) is not int or not 0 <= fullscreen <= 2:
                raise GeometryError("INVALID FULLSCREEN MODE")
            collected.append({
                "window_key": key, "app_id": app, "workspace": workspace,
                "output": output, "floating": is_floating,
                "rect": _rectangle(node.get("rect")),
                "window_rect": _rectangle(node.get("window_rect"), optional=True),
                "deco_rect": _rectangle(node.get("deco_rect"), optional=True),
                "geometry": _rectangle(node.get("geometry"), optional=True),
                "fullscreen_mode": fullscreen,
            })
            if len(collected) > MAX_WINDOWS:
                raise GeometryError("TOO MANY WINDOWS")

        for source_key, target_key, flag in (
                ("nodes", "children", is_floating),
                ("floating_nodes", "floating_children", True)):
            for child in _nodes(node.get(source_key, [])):
                part[target_key].append(build(
                    child, workspace=workspace, output=output,
                    floating=flag, depth=depth + 1))
        return part

    def visit(node, *, output=None, depth=0):
        if depth > MAX_DEPTH or not isinstance(node, dict):
            raise GeometryError("INVALID SWAY TREE")
        kind = node.get("type")
        if kind == "output":
            output = node.get("name")
        if kind == "workspace":
            name = node.get("name")
            if name not in declared_workspaces:
                return
            if output != declared_workspaces[name] or name in observed:
                raise GeometryError("WORKSPACE OUTPUT OR IDENTITY CHANGED")
            main = [build(child, workspace=name, output=output,
                          floating=False, depth=depth + 1)
                    for child in _nodes(node.get("nodes", []))]
            floaters = [build(child, workspace=name, output=output,
                              floating=True, depth=depth + 1)
                        for child in _nodes(node.get("floating_nodes", []))]
            observed[name] = {
                "name": name, "output": output,
                "rect": _rectangle(node.get("rect")),
                "layout": node.get("layout", "none"),
                "children": main, "floating_children": floaters,
            }
            if observed[name]["layout"] not in LAYOUTS:
                raise GeometryError("UNKNOWN WORKSPACE LAYOUT")
            return
        for child in _nodes(node.get("nodes", [])):
            visit(child, output=output, depth=depth + 1)
        for child in _nodes(node.get("floating_nodes", [])):
            visit(child, output=output, depth=depth + 1)

    visit(tree)
    if set(observed) != set(declared_workspaces):
        raise GeometryError("SAVED WORKSPACE NOT PRESENT IN SWAY TREE")
    if set(window_keys) != used_con_ids:
        raise GeometryError("INCOMPLETE OR EXTRANEOUS WINDOW KEY MAP")
    return {
        "schema_version": 2, "kind": KIND,
        "coordinate_space": "sway-logical-pixels",
        "outputs": saved_outputs,
        "workspaces": [observed[name] for name in declared_workspaces],
        "windows": collected,
        "capture_only": True,
        "session_identity_verified": False,
    }


def compare_to_v1(proposal, v1_document):
    """Pure v1 multiset check; geometries never backfill absent v1 detail."""
    from MachineCheckpointStore import validate as validate_v1
    old = validate_v1(v1_document)
    if not isinstance(proposal, dict) or proposal.get("kind") != KIND:
        raise GeometryError("INVALID GEOMETRY PROPOSAL")
    actual = Counter((w["app_id"], w["workspace"], w["floating"])
                     for w in proposal["windows"])
    expected = Counter((w["app_id"], w["workspace"], w["floating"])
                       for w in old["windows"])
    return {"v1_window_multiset_matches": actual == expected,
            "exact_session_match": False,
            "safe_restore_actions": []}
