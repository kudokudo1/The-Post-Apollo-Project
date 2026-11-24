#!/usr/bin/env python3
"""UI-only synthetic resource fit calculator; calls the existing Core P1 policy."""
import json
import re
import sys
from resource_governor_p1 import (
    ResourceRequest, ResourceRequirement, ResourceBudget, ResourceAvailability,
    ResourcePolicyRefusal, evaluate_resource_request,
)

SCHEMA = "post-apollo.forest.ui-resource-fit.p1-example"
MAX_VALUE = 1000000000


def quantity(token):
    if token == "?":
        return None
    if not re.fullmatch(r"0|[1-9][0-9]{0,9}", token):
        raise ValueError("INVALID_QUANTITY")
    value = int(token)
    if value > MAX_VALUE:
        raise ValueError("INVALID_QUANTITY")
    return value


def evaluate(argv):
    # Nine explicit hypothetical quantities, ordered requirement/budget/available
    # within each dimension. No model name, user task, host reading or file path.
    if len(argv) != 10 or argv[0] not in ("defer", "deny"):
        raise ValueError("INVALID_ARGUMENTS")
    values = [quantity(v) for v in argv[1:]]
    req = ResourceRequest(
        task_id="forestw-example", execution_context_id="forestw-example",
        model_form="small", reasoning_mode="normal", priority="standard",
        source="forestw-hypothetical-inputs", may_defer=argv[0] == "defer",
    )
    requirements = ResourceRequirement(req, "example", *values[0::3])
    budget = ResourceBudget("example", *values[1::3])
    available = ResourceAvailability("example", *values[2::3])
    result = evaluate_resource_request(req, requirements, budget, available)
    return {
        "schema": SCHEMA, "inputs": argv, "outcome": result.outcome,
        "reasons": list(result.reasons), "authority_scope": result.authority_scope,
        "production_authority": result.production_authority,
        "permission_granted": result.permission_granted,
        "safe_to_start_inference": result.safe_to_start_inference,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(evaluate(sys.argv[1:]), separators=(",", ":")))
    except (ValueError, ResourcePolicyRefusal):
        print("FORESTW_RESOURCE_EXAMPLE_REFUSED", file=sys.stderr)
        sys.exit(2)
