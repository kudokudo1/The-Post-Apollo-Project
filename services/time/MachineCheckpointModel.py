"""Pure, read-only MACHINE Sway metadata projection. No IPC, disk or execution.

This module accepts an already supplied Sway JSON-shaped fixture and produces
an allowlisted preview. It deliberately does not capture live desktop state.
"""
from __future__ import annotations
from datetime import datetime, timezone

MAX_OUTPUTS = 16
MAX_WORKSPACES = 128
MAX_WINDOWS = 512
MAX_TEXT = 128


class PreviewError(ValueError):
    pass


def _name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_TEXT:
        raise PreviewError("invalid metadata identifier")
    if any(ord(c) < 32 for c in value):
        raise PreviewError("control character in metadata identifier")
    return value


def _int(value, minimum=0, maximum=100000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise PreviewError("invalid numeric metadata")
    return value


def _rect(value):
    if not isinstance(value, dict):
        raise PreviewError("invalid rectangle")
    return {k: _int(value.get(k), -100000 if k in ("x", "y") else 1,
                    100000) for k in ("x", "y", "width", "height")}


def project(source, *, excluded_apps=(), captured_at=None):
    """Return immutable-schema candidate metadata only; never persist it.

    Source requires distinct output, workspace and window arrays.
    Caller supplies fixtures/IPC results, but this module never obtains them.
    Exclusions are *app IDs*, not window titles, paths or commands.
    """
    if not isinstance(source, dict):
        raise PreviewError("invalid source")
    if not isinstance(excluded_apps, (tuple, list, set)):
        raise PreviewError("invalid exclusions")
    excluded = {_name(x) for x in excluded_apps}
    limits = (("outputs", MAX_OUTPUTS), ("workspaces", MAX_WORKSPACES),
              ("windows", MAX_WINDOWS))
    for key, maximum in limits:
        if not isinstance(source.get(key), list) or len(source[key]) > maximum:
            raise PreviewError("invalid or oversized " + key)
    timestamp = captured_at or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str) or len(timestamp) > 48:
        raise PreviewError("invalid capture time")
    outputs = []
    for item in source["outputs"]:
        if not isinstance(item, dict):
            raise PreviewError("invalid output")
        outputs.append({"connector": _name(item.get("name")),
                        "rect": _rect(item.get("rect"))})
    workspaces = []
    for item in source["workspaces"]:
        if not isinstance(item, dict):
            raise PreviewError("invalid workspace")
        workspaces.append({"name": _name(item.get("name")),
                           "output": _name(item.get("output"))})
    windows = []
    omitted = 0
    for item in source["windows"]:
        if not isinstance(item, dict):
            raise PreviewError("invalid window")
        app = _name(item.get("app_id"))
        if app in excluded:
            omitted += 1
            continue
        windows.append({"app_id": app,
                        "workspace": _name(item.get("workspace")),
                        "floating": item.get("floating") is True})
    return {"schema_version": 1, "kind": "sway-layout-metadata-preview",
            "captured_at_utc": timestamp, "outputs": outputs,
            "workspaces": workspaces, "windows": windows,
            "excluded_counts": {"windows": omitted},
            "preview_only": True}
