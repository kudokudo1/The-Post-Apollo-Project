#!/usr/bin/env python3
"""Trash++ U8 read-only source-boundary audit for Hi-Fi / Media.

No Media code import, subprocess, network, filesystem mutation, GIO operation,
deletion approval or source-owner authorization. This is an inventory, not a
provider adapter, live capability probe or grant of permission.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

SCHEMA = "post-apollo.trash-media-boundary.u8"
PATHS = (
    "widgets/MediaDeckW.qml",
    "widgets/MediaDeckBrowserControls.qml",
    "modules/Mediaplayer.qml",
    "services/media/HeadlessMediaController.qml",
    "scripts/media/headless_mpd.py",
    "scripts/media/media_controller.py",
    "scripts/media/media_controller_cli.py",
    "scripts/media/media_controller_server.py",
    "scripts/media/media_intent_store.py",
)
MAX_SOURCE_BYTES = 150_000


def _read(root: Path, relative: str) -> str:
    path = root / relative
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_SOURCE_BYTES:
        raise ValueError("Unrecognized or oversized source: " + relative)
    return path.read_text(encoding="utf-8")


def _function(tree: ast.Module, name: str, owner: str | None = None):
    nodes = tree.body
    if owner:
        matches = [x for x in nodes if isinstance(x, ast.ClassDef) and x.name == owner]
        if len(matches) != 1:
            raise ValueError("Missing unique owner: " + owner)
        nodes = matches[0].body
    matches = [x for x in nodes if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
               and x.name == name]
    if len(matches) != 1:
        raise ValueError("Missing unique method: " + str(owner) + "." + name)
    return matches[0]


def _calls(node: ast.AST, attr: str, first_arg: str | None = None) -> bool:
    for call in ast.walk(node):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue
        if call.func.attr != attr:
            continue
        if first_arg is None or (call.args and isinstance(call.args[0], ast.Constant)
                                 and call.args[0].value == first_arg):
            return True
    return False


def _literal(node: ast.AST, value: str) -> bool:
    return any(isinstance(x, ast.Constant) and x.value == value for x in ast.walk(node))


def _queue_branch(dispatch: ast.AST) -> ast.If:
    matches = [
        node for node in ast.walk(dispatch) if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name) and node.test.left.id == "op"
        and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "queue_remove"
    ]
    if len(matches) != 1:
        raise ValueError("Missing unique queue_remove branch")
    return matches[0]


def inventory(root: Path) -> dict:
    """Read only the fixed repo source paths and return a bounded public report."""
    root = Path(root)
    files: dict[str, str] = {}
    problems: list[str] = []
    for path in PATHS:
        try:
            files[path] = _read(root, path)
        except (OSError, UnicodeError, ValueError) as exc:
            problems.append(path + ": " + type(exc).__name__)
    boundaries = [
        {"kind": "mpd-queue-entry", "operation": "queue_remove / deleteid",
         "owner": "media-controller/mpd", "effect": "remove one MPD queue entry",
         "filesystemTrash": False, "genericBurn": False, "sourceOwnerReview": True},
        {"kind": "mpd-queue", "operation": "MpdBackend.clear",
         "owner": "media-controller/mpd", "effect": "clear MPD playback queue only; not exposed by current controller dispatch",
         "filesystemTrash": False, "genericBurn": False, "sourceOwnerReview": True},
        {"kind": "intent-state", "operation": "IntentStore.save / os.replace",
         "owner": "media-controller", "effect": "replace private saved selection and loaded queue coordinates",
         "filesystemTrash": False, "genericBurn": False, "sourceOwnerReview": True},
        {"kind": "runtime-socket", "operation": "run / path.unlink",
         "owner": "media-controller", "effect": "remove stale or owned controller socket only",
         "filesystemTrash": False, "genericBurn": False, "sourceOwnerReview": True},
    ]
    try:
        mpd = ast.parse(files["scripts/media/headless_mpd.py"])
        controller = ast.parse(files["scripts/media/media_controller.py"])
        intent = ast.parse(files["scripts/media/media_intent_store.py"])
        server = ast.parse(files["scripts/media/media_controller_server.py"])
        remove = _function(mpd, "remove", "MpdBackend")
        clear = _function(mpd, "clear", "MpdBackend")
        dispatch = _function(controller, "dispatch", "MediaController")
        queue_remove = _queue_branch(dispatch)
        save = _function(intent, "save", "IntentStore")
        run = _function(server, "run")
        if not (_calls(remove, "command", "deleteid")
                and _calls(remove, "isdecimal")
                and not any(_calls(remove, dangerous) for dangerous in
                            ("unlink", "rmdir", "remove", "replace", "rmtree"))):
            problems.append("MPD queue removal no longer has the expected ID-only command")
        if not _calls(clear, "command", "clear"):
            problems.append("MPD clear command has drifted")
        if _literal(dispatch, "clear"):
            problems.append("Controller exposes a clear operation; inspect its authority")
        if not (_literal(queue_remove, "ACTIVE_TRACK") and _calls(queue_remove, "remove")
                and _calls(queue_remove, "isdecimal")
                and not any(_calls(queue_remove, dangerous) for dangerous in
                            ("unlink", "rmdir", "rmtree", "replace"))):
            problems.append("Controller queue_remove validation or scope has drifted")
        if not (_calls(save, "replace") and _calls(save, "unlink")
                and _literal(intent, "controller-intent-v1.json")):
            problems.append("Private intent-state replacement/cleanup changed")
        if not (_calls(run, "unlink") and _calls(run, "S_ISSOCK")
                and _literal(server, "Refusing a symlink socket path")
                and _literal(server, "Refusing to replace a non-owned/non-socket path")):
            problems.append("Private socket cleanup protection changed")
        for ui_path in ("widgets/MediaDeckW.qml", "widgets/MediaDeckBrowserControls.qml",
                        "modules/Mediaplayer.qml"):
            if re.search(r"\bTrashLifecycleActionDeck\s*\{", files[ui_path]):
                problems.append("Media UI added a shared lifecycle deck: owner review needed at " + ui_path)
    except (KeyError, SyntaxError, ValueError) as exc:
        problems.append("Source invariant unreadable: " + type(exc).__name__ + ": " + str(exc)[:160])
    return {
        "schema": SCHEMA,
        "state": "INVENTORIED_READ_ONLY" if not problems else "DRIFT_OWNER_REVIEW_REQUIRED",
        "readOnly": True,
        "actionAuthority": False,
        "sourceOwnerApproval": False,
        "mediaFileDeleteSupported": False,
        "genericTrashEligible": False,
        "scannedFiles": [
            {"path": path, "sha256": hashlib.sha256(files[path].encode("utf-8")).hexdigest()}
            for path in PATHS if path in files
        ],
        "boundaries": boundaries,
        "problems": problems,
        "next": "Media-owner-reviewed file-storage and retention contract before any GIO Trash integration",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(json.dumps({"ok": False, "error": "NO_ARGUMENTS_ALLOWED"}))
        return 2
    root = Path(__file__).resolve().parents[2]
    result = inventory(root)
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if not result["problems"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
