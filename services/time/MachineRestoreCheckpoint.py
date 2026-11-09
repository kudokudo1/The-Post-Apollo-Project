#!/usr/bin/env python3
"""MACHINE: one user-clicked checkpoint restore, with internal safety checks.

The QML sends only an existing checkpoint UUID. This process loads the saved
document itself and tries each uniquely identifiable window. A missing app may
be started once via an installed desktop entry, never a saved command or shell.
Ambiguous windows, unavailable displays and uncertain moves remain visible as
skipped results. No background execution, automatic retry or forced closes.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import load as load_checkpoint
from MachineWindowResolver import capture_and_resolve
from MachineMoveApproval import MoveApprovalGate
from MachineMoveReviewRead import _candidate_request
from MachineMoveApply import apply_one
from MachineMoveJournal import MoveJournal, suggested_path

MAX_APPS = 40
MAX_LAUNCHES = 12
DESKTOP_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
DENIED_DESKTOP_IDS = frozenset(("quickshell", "sway", "swayfx", "swaypx"))
RESULT_KIND = "machine-one-click-restore-result"


class RestoreError(ValueError):
    pass


def _move(checkpoint_id, document, candidate, *, read_runner, command_runner,
          apply_adapter=apply_one):
    """The RESTORE click is consent. Reuse M1q fresh preflight and journal.

    The exact M1q phrase is computed internally from a fresh, bound review.
    It is not presented as an authentication challenge to the operator.
    """
    request = _candidate_request({
        "checkpoint_id": checkpoint_id, "document": document,
        "candidate": candidate,
    })
    review = MoveApprovalGate().review(document, request,
                                      checkpoint_id=checkpoint_id,
                                      read_runner=read_runner)
    return apply_adapter({
        "checkpoint_id": checkpoint_id,
        "document": document,
        "candidate": candidate,
        "confirmation_text": review["confirmation_text"],
    }, read_runner=read_runner, command_runner=command_runner)


def _start_app(app_id, *, runner):
    # gtk-launch selects an installed .desktop ID; checkpoint contents are
    # NEVER used as a command line, file path, shell fragment or arguments.
    if (not isinstance(app_id, str) or not DESKTOP_ID.fullmatch(app_id)
            or app_id.lower() in DENIED_DESKTOP_IDS):
        return False
    try:
        result = runner(["gtk-launch", app_id],
                        check=False, capture_output=True,
                        timeout=6, shell=False)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def restore_checkpoint(checkpoint_id, *, load_adapter=load_checkpoint,
                       resolve_adapter=capture_and_resolve,
                       move_adapter=_move, launch_adapter=_start_app,
                       read_runner=subprocess.run,
                       command_runner=subprocess.run,
                       launch_runner=subprocess.run,
                       journal_factory=MoveJournal,
                       sleep=time.sleep):
    saved = load_adapter(checkpoint_id)
    if (not isinstance(saved, dict) or saved.get("status") != "loaded"
            or not isinstance(saved.get("checkpoint"), dict)
            or saved["checkpoint"].get("id") != checkpoint_id
            or not isinstance(saved.get("document"), dict)):
        raise RestoreError("SAVED DESKTOP NOT FOUND")
    document = saved["document"]
    apps = {}
    for win in document["windows"]:
        apps.setdefault(win["app_id"], []).append(win)
    if len(apps) > MAX_APPS:
        raise RestoreError("TOO MANY DISTINCT APPS IN CHECKPOINT")

    # An uncertain or interrupted previous action cannot be replayed.
    if journal_factory(suggested_path()).pending():
        return {"kind": RESULT_KIND, "checkpoint_id": checkpoint_id,
                "status": "needs_attention",
                "counts": {"moved": 0, "opened": 0, "in_place": 0,
                           "pending": 0, "skipped": len(apps)},
                "items": [{"app_id": "DESKTOP", "outcome": "skipped",
                           "reason": "A PREVIOUS MOVE NEEDS RECOVERY REVIEW"}],
                "no_automatic_retry": True}

    counts = {"moved": 0, "opened": 0, "in_place": 0,
              "pending": 0, "skipped": 0}
    items = []
    launches = 0
    stopped = False
    for app_id in sorted(apps):
        if stopped:
            counts["skipped"] += 1
            items.append({"app_id": app_id, "outcome": "skipped",
                          "reason": "RESTORE STOPPED AFTER AN UNCERTAIN MOVE"})
            continue
        if len(apps[app_id]) != 1:
            counts["skipped"] += 1
            items.append({"app_id": app_id, "outcome": "skipped",
                          "reason": "MULTIPLE WINDOWS NEED DISTINCT IDENTITIES"})
            continue
        try:
            resolution = resolve_adapter(document, runner=read_runner)
            if resolution.get("truncated"):
                raise RestoreError("LIVE WINDOW LIST TOO LARGE")
            matches = [c for c in resolution["candidates"]
                       if c.get("app_id") == app_id]
            if len(matches) != 1:
                raise RestoreError("WINDOW IDENTITY NOT UNIQUE")
            candidate = matches[0]
            outcome = candidate["status"]
            if outcome == "already":
                counts["in_place"] += 1
                items.append({"app_id": app_id, "outcome": "in_place",
                              "reason": "ALREADY IN SAVED WORKSPACE"})
                continue
            was_opened = False
            if outcome == "manual" and candidate["reason"] == "APP NOT RUNNING":
                if launches >= MAX_LAUNCHES:
                    raise RestoreError("APP OPEN LIMIT REACHED")
                launches += 1
                if not launch_adapter(app_id, runner=launch_runner):
                    raise RestoreError("INSTALLED APP LAUNCHER NOT AVAILABLE")
                was_opened = True
                # One launch per app. Wait only for observation, never relaunch.
                for pause in (0.4, 0.8, 1.2):
                    sleep(pause)
                    resolution = resolve_adapter(document, runner=read_runner)
                    matches = [c for c in resolution["candidates"]
                               if c.get("app_id") == app_id]
                    if len(matches) == 1 and matches[0]["status"] in ("candidate", "already"):
                        candidate = matches[0]
                        break
                else:
                    counts["pending"] += 1
                    items.append({"app_id": app_id, "outcome": "pending",
                                  "reason": "APP START REQUESTED; WINDOW NOT YET VISIBLE"})
                    continue
                outcome = candidate["status"]
            if outcome == "already":
                counts["opened" if was_opened else "in_place"] += 1
                items.append({"app_id": app_id,
                              "outcome": "opened" if was_opened else "in_place",
                              "reason": "VISIBLE ON SAVED WORKSPACE"})
                continue
            if outcome != "candidate":
                raise RestoreError(candidate.get("reason", "WINDOW NOT MATCHED"))
            result = move_adapter(checkpoint_id, document, candidate,
                                  read_runner=read_runner,
                                  command_runner=command_runner)
            if result["status"] == "verified_moved":
                counts["opened" if was_opened else "moved"] += 1
                items.append({"app_id": app_id,
                              "outcome": "opened" if was_opened else "moved",
                              "reason": "WINDOW PLACEMENT VERIFIED"})
            else:
                counts["skipped"] += 1
                stopped = True
                items.append({"app_id": app_id, "outcome": "skipped",
                              "reason": "MOVE UNCERTAIN; NO AUTOMATIC RETRY"})
        except (ValueError, KeyError, TypeError, OSError,
                subprocess.SubprocessError) as error:
            counts["skipped"] += 1
            # Only show stable authored error categories, never Sway IPC,
            # arbitrary native errors, paths, launch output or private titles.
            reason = str(error) if isinstance(error, RestoreError) else "MOVE NOT VERIFIED"
            items.append({"app_id": app_id, "outcome": "skipped", "reason": reason})
            if not isinstance(error, RestoreError):
                stopped = True
    status = "complete" if counts["skipped"] == 0 and counts["pending"] == 0 else "partial"
    return {"kind": RESULT_KIND, "checkpoint_id": checkpoint_id,
            "status": status, "counts": counts, "items": items,
            "no_automatic_retry": True}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] != "restore":
        print(json.dumps({"status": "error", "reason": "INVALID RESTORE REQUEST"}))
        return 2
    try:
        result = restore_checkpoint(args[1])
    except (RestoreError, ValueError, KeyError, TypeError, OSError,
            subprocess.SubprocessError):
        result = {"status": "error", "reason": "SAVED DESKTOP CANNOT BE RESTORED"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["status"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
