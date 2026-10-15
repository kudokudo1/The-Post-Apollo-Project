#!/usr/bin/env python3
"""Read-only Koinoikos + SwayFX focus snapshots for controlled desktop tests.

Usage:
  python3 scripts/focus_diagnostics.py snapshot
  python3 scripts/focus_diagnostics.py watch --limit 30

Only uses QS and read-only swaymsg IPC. Does not press keys, move native focus,
reload Sway, write files, or read browser content/text. A native Sway tree's
focused container is NOT necessarily the true seat-key recipient when a
layer-shell surface is active; verify real key delivery in the application.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
import sys
from typing import Any


def invoke(*args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            list(args), capture_output=True, text=True, timeout=3, check=False
        )
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def parse_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def query_quickshell() -> dict[str, Any]:
    code, text = invoke("qs", "ipc", "call", "relationshipFocus", "diagnose")
    value = parse_json(text) if code == 0 else None
    if isinstance(value, dict):
        return value
    return {"diagnosticsUnavailable": True, "reason": "QS diagnose IPC not available"}


def find_native_focused(tree: Any) -> dict[str, Any] | None:
    """Sway get_tree focus is native-container metadata, not seat key delivery."""
    if not isinstance(tree, dict):
        return None
    if tree.get("focused") is True:
        props = tree.get("window_properties")
        props = props if isinstance(props, dict) else {}
        return {
            "id": tree.get("id"),
            "app_id": tree.get("app_id"),
            "class": props.get("class"),
            "type": tree.get("type"),
        }
    for child in (*tree.get("nodes", []), *tree.get("floating_nodes", [])):
        match = find_native_focused(child)
        if match is not None:
            return match
    return None


def query_native_focus() -> dict[str, Any]:
    code, response = invoke("swaymsg", "-t", "get_tree")
    if code != 0:
        return {"swayTreeUnavailable": True}
    return {"focusedNativeContainer": find_native_focused(parse_json(response))}


def sample(trigger: str) -> dict[str, Any]:
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "trigger": trigger,
        "quickshell": query_quickshell(),
        "swayTree": query_native_focus(),
        "note": (
            "Native tree focus and QS intent do not prove keyboard event delivery. "
            "Check Tab/typing in the intended widget or Brave."
        ),
    }


def summarize_event(event: Any) -> str | None:
    if not isinstance(event, dict):
        return None
    binding = event.get("binding")
    if isinstance(binding, dict):
        return "binding:" + str(binding.get("command", ""))[:120]
    if isinstance(event.get("change"), str):
        change = event["change"]
        if change in ("focus", "new", "close", "move", "title", "floating"):
            return "window:" + change
        return "mode-or-window:" + change
    return None


def watch(limit: int) -> int:
    # Subscribes to notifications; never calls swaymsg focus or mode.
    command = [
        "swaymsg", "-m", "-t", "subscribe", '["binding","mode","window"]'
    ]
    try:
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1
        )
    except OSError:
        print("swaymsg subscription unavailable", file=sys.stderr)
        return 1
    n = 0
    try:
        assert proc.stdout is not None
        print(json.dumps(sample("started")), flush=True)
        for line in proc.stdout:
            kind = summarize_event(parse_json(line))
            if kind is None:
                continue
            print(json.dumps(sample(kind), separators=(",", ":")), flush=True)
            n += 1
            if n >= limit:
                break
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "watch"))
    parser.add_argument("--limit", type=int, default=30,
                        help="maximum subscription events before exit (default 30)")
    args = parser.parse_args(argv)
    if args.action == "snapshot":
        print(json.dumps(sample("manual"), indent=2))
        return 0
    if args.limit < 1:
        parser.error("--limit must be positive")
    return watch(args.limit)


if __name__ == "__main__":
    sys.exit(main())
