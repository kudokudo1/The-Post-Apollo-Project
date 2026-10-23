"""Opt-in, one-shot, read-only Sway -> MACHINE preview adapter.

Not imported by TimeW. No writes, restore actions, background pollers or shell.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Python isolated mode (-I) does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointModel import PreviewError, project

MAX_IPC_BYTES = 4_000_000
MAX_TREE_DEPTH = 48


def _read_json(command, runner=subprocess.run):
    try:
        result = runner(command, check=True, capture_output=True,
                        timeout=3, shell=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PreviewError("Sway read unavailable") from exc
    data = result.stdout
    if not isinstance(data, bytes) or len(data) > MAX_IPC_BYTES:
        raise PreviewError("Sway response too large")
    try:
        return json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise PreviewError("invalid Sway response") from exc


def normalize(outputs, workspaces, tree):
    """Project only allowlisted fields; never echo raw tree or titles."""
    if not isinstance(outputs, list) or not isinstance(workspaces, list) or not isinstance(tree, dict):
        raise PreviewError("invalid Sway structure")
    if len(outputs) > 16 or len(workspaces) > 128:
        raise PreviewError("Sway structure too large")
    simplified = {"outputs": [], "workspaces": [], "windows": []}
    for output in outputs:
        if not isinstance(output, dict):
            raise PreviewError("invalid output")
        if output.get("active") is False:
            continue
        simplified["outputs"].append({"name": output.get("name"), "rect": output.get("rect")})
    for ws in workspaces:
        if not isinstance(ws, dict):
            raise PreviewError("invalid workspace")
        simplified["workspaces"].append({"name": ws.get("name"), "output": ws.get("output")})

    def walk(node, workspace=None, floating=False, depth=0):
        if depth > MAX_TREE_DEPTH:
            raise PreviewError("Sway tree too deep")
        if not isinstance(node, dict):
            raise PreviewError("invalid tree node")
        kind = node.get("type")
        if kind == "workspace":
            workspace = node.get("name")
        # The compositor's transient container IDs are not persistent identity.
        app = node.get("app_id")
        if app is None and isinstance(node.get("window_properties"), dict):
            app = node["window_properties"].get("class")
        if kind == "con" and isinstance(app, str) and app:
            if workspace is not None and isinstance(app, str) and app:
                simplified["windows"].append({
                    "app_id": app, "workspace": workspace,
                    "floating": floating or node.get("floating") in ("user_on", "auto_on")})
                if len(simplified["windows"]) > 512:
                    raise PreviewError("too many windows")
        for key, is_floating in (("nodes", floating), ("floating_nodes", True)):
            children = node.get(key, [])
            if not isinstance(children, list):
                raise PreviewError("invalid tree children")
            for child in children:
                walk(child, workspace, is_floating, depth + 1)
    walk(tree)
    return simplified


def capture_preview(*, runner=subprocess.run, excluded_apps=()):
    """Explicit call required; executes only fixed Sway read IPC commands."""
    outputs = _read_json(["swaymsg", "-r", "-t", "get_outputs"], runner)
    workspaces = _read_json(["swaymsg", "-r", "-t", "get_workspaces"], runner)
    tree = _read_json(["swaymsg", "-r", "-t", "get_tree"], runner)
    return project(normalize(outputs, workspaces, tree),
                   excluded_apps=excluded_apps)


def main():
    # stdout is limited to allowlisted metadata. No input args or paths.
    try:
        print(json.dumps(capture_preview(), separators=(",", ":")))
    except PreviewError as exc:
        print(json.dumps({"status": "UNAVAILABLE", "reason": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
