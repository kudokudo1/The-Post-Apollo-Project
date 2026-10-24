"""MACHINE M1n: read-only inspection of interrupted move journal entries.

A Sway container ID is transient and can be reused; apparent matches are NOT
proof that the same historical process/window survived. No journal updates,
auto-retry, rollback, or live UI actions exist in this module.
"""
from __future__ import annotations

from MachineMoveJournal import MoveJournal
from MachineWindowMovePilot import MoveRefused, _read_state
from MachineWindowResolver import ResolutionError, _walk_live


class ReconciliationError(ValueError):
    pass


def inspect_pending(journal, *, read_runner):
    if not isinstance(journal, MoveJournal):
        raise ReconciliationError("EXPLICIT JOURNAL REQUIRED")
    pending = journal.pending()
    if not pending:
        # A status read never polls Sway when there is no unresolved operation.
        return {"kind": "machine-interrupted-move-review", "read_only": True,
                "executable": False, "items": [], "manual_review_required": False}
    try:
        outputs, workspaces, tree = _read_state(read_runner)
        windows = _walk_live(tree)
        active = {
            o["name"] for o in outputs
            if isinstance(o, dict) and o.get("active") is not False
            and isinstance(o.get("name"), str)
        }
        layout = {w["name"]: w["output"] for w in workspaces
                  if isinstance(w, dict) and isinstance(w.get("name"), str)
                  and isinstance(w.get("output"), str)}
        if len(layout) != len(workspaces):
            raise ReconciliationError("DUPLICATE OR INVALID WORKSPACE")
        ids = [row["con_id"] for row in windows if row["con_id"] is not None]
        if len(ids) != len(set(ids)):
            raise ReconciliationError("DUPLICATE LIVE CONTAINER ID")
        available = True
    except (MoveRefused, ResolutionError, ReconciliationError, KeyError, TypeError):
        windows, layout, active, available = [], {}, set(), False

    items = []
    for record in pending:
        before = record["before"]
        status = "state_unavailable"
        observed = None
        if available:
            same_app = [x for x in windows if x["app_id"] == before["app_id"]]
            same_id = [x for x in windows if x["con_id"] == before["con_id"]]
            if len(same_app) > 1 or len(same_id) > 1:
                status = "ambiguous_candidate"
            elif len(same_id) == 1 and same_id[0]["app_id"] != before["app_id"]:
                status = "identity_conflict"
            elif len(same_id) != 1 or len(same_app) == 0:
                status = "saved_window_not_identified"
            else:
                win = same_id[0]
                observed = win["workspace"]
                output = layout.get(observed)
                if output is None or output not in active or win["fullscreen"]:
                    status = "workspace_or_window_unavailable"
                elif observed == before["target_workspace"]:
                    status = "appears_at_target"
                elif observed == before["workspace"]:
                    status = "appears_at_origin"
                else:
                    status = "appears_elsewhere"
        items.append({
            "operation_id": record["id"],
            "durable_phase": record["phase"],
            "before": before,
            "observed_workspace": observed,
            "advisory_state": status,
            "evidence_is_not_process_identity": True,
            "requires_manual_review": True,
            "automatic_retry_allowed": False,
            "automatic_undo_allowed": False,
        })
    return {"kind": "machine-interrupted-move-review", "read_only": True,
            "executable": False, "items": items,
            "manual_review_required": True}
