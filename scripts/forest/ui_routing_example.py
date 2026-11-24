#!/usr/bin/env python3
"""ForestW synthetic routing example, backed by the existing I1 policy."""
import json
import sys
from shared_context_b6r1 import TaskContext
from model_form_routing_i1 import (
    TurnScope, ReasoningReference, SemanticEvidence, RoutingInput,
    recommend, presentation_reference,
)

SIGNALS = (
    ("task_complexity", ("unset", "low", "normal", "high")),
    ("known_small_failure", ("unset", "absent", "present")),
    ("small_capability_suitability", ("unset", "sufficient", "insufficient", "unknown")),
)


def recommendation(args):
    if (len(args) != 5 or args[0] not in ("auto", "small", "big")
            or args[1] not in ("light", "normal", "deep")
            or any(v not in allowed for v, (_, allowed) in zip(args[2:], SIGNALS))):
        raise ValueError("INVALID_EXAMPLE")
    scope = TurnScope(TaskContext("forestw-example", "bristlecone", None,
                                  "example-task", "example-context", 1, "INTERACTIVE"),
                      "example-turn")
    reasoning = ReasoningReference(scope, args[1], "explicit")
    evidence = tuple(SemanticEvidence(scope, name, value, "example-input")
                     for value, (name, _) in zip(args[2:], SIGNALS) if value != "unset")
    return recommend(RoutingInput(scope, args[0], reasoning, evidence))


def evaluate(args):
    result = recommendation(args)
    return {"schema": "post-apollo.forest.ui-routing-example.i1",
            "inputs": args, "reference": presentation_reference(result)}


if __name__ == "__main__":
    try:
        print(json.dumps(evaluate(sys.argv[1:]), separators=(",", ":")))
    except ValueError:
        print("FORESTW_ROUTING_EXAMPLE_REFUSED", file=sys.stderr)
        sys.exit(2)
