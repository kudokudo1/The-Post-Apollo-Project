#!/usr/bin/env python3
"""ForestW public historical Workshop reference. No real task or tool execution."""
import json
import sys
from shared_context_b6r1 import TaskContext
from capability_registry_b6r2 import bristlecone_reference_profile, plan_selection

SCHEMA = "post-apollo.forest.ui-workshop-reference.b6r2"


def run(args):
    if len(args) != 3 or any(len(v) > 1024 for v in args):
        raise ValueError("INVALID_INPUT")
    workshop, general, ready = args
    # Fixed disposable context; never accept a real identity from the Bark.
    ctx = TaskContext("forestw-example", "bristlecone", None,
                      "workshop-example", "workshop-example", 1, "INTERACTIVE")
    profile = bristlecone_reference_profile(ctx)
    plan = plan_selection(profile, ctx, workshop,
                          general=tuple(general.split(",")) if general else (),
                          ready=tuple(ready.split(",")) if ready else ())
    return {
        "schema": SCHEMA, "inputs": args, "profile": "BRISTLECONE_HISTORICAL_REFERENCE",
        "definitions": [{"key": d.key, "kind": d.kind,
                         "sticky_allowed": d.sticky_allowed,
                         "historical_target": d.historical_target}
                        for d in profile.registry.definitions],
        "general_ready": list(profile.general_ready),
        "workshops": [{"key": w.key, "core": list(w.core), "ready": list(w.ready)}
                      for w in profile.workshops],
        "plan": {"workshop": plan.workshop, "core": list(plan.core),
                 "selected": list(plan.selected), "dormant": list(plan.dormant),
                 "unresolved": list(plan.unresolved), "status": plan.status},
        "permission_granted": plan.permission_granted,
        "production_authority": plan.production_authority,
        "model_execution_permitted": plan.model_execution_permitted,
        "safe_actions": list(plan.safe_actions),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(run(sys.argv[1:]), separators=(",", ":")))
    except ValueError:
        print("FORESTW_WORKSHOP_REFERENCE_REFUSED", file=sys.stderr)
        sys.exit(2)
