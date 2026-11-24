#!/usr/bin/env python3
"""Synthetic I1/I2 reference join. No installed model, actual identity or IO."""
from dataclasses import replace
import json
import sys
from ui_routing_example import recommendation
from model_form_routing_i1 import presentation_reference
from model_binding_i2 import (
    ModelIdentity, ModelBinding, BindingRegistry, BindingEvidence,
    resolve_reference, public_binding_status,
)

SCENARIOS = ("unbound", "missing", "mismatch", "not-installed", "install-unknown",
             "capability-unknown", "feature-unsupported", "context-insufficient", "match")


def evaluate(args):
    if len(args) != 6 or args[5] not in SCENARIOS:
        raise ValueError("INVALID_EXAMPLE")
    route = recommendation(args[:5])
    scenario = args[5]
    scope = route.original.scope
    # Deliberately fictional artifacts; never copy model names or preferences.
    def binding(form, char):
        identity = ModelIdentity("fixture:" + form, "sha256:" + char*64,
                                 "fixture-adapter", "fixture-runtime", "0.0.1",
                                 "sha256:" + "b"*64)
        return ModelBinding("fixture-" + form, form, identity,
                            "sha256:" + "c"*64, 4096, 256)
    small, big = binding("small", "a"), binding("big", "d")
    chosen = small if route.form == "small" else big
    bindings = tuple(b for b in (small, big)
                     if scenario != "unbound" or b.form != route.form)
    registry = BindingRegistry(scope.context.principal_key, scope.context.tree_key, 1, bindings)
    evidence = None
    if scenario not in ("unbound", "missing"):
        evidence = BindingEvidence(scope, chosen, "fixture-observer", "fixture-observation",
                                   True, ("chat", "reasoning"), 8192)
        if scenario == "mismatch":
            evidence = replace(evidence, binding=replace(chosen,
                identity=replace(chosen.identity, artifact_digest="sha256:" + "e"*64)))
        elif scenario == "not-installed":
            evidence = replace(evidence, installed=False)
        elif scenario == "install-unknown":
            evidence = replace(evidence, installed=None)
        elif scenario == "capability-unknown":
            evidence = replace(evidence, supported_features=None)
        elif scenario == "feature-unsupported":
            evidence = replace(evidence, supported_features=("chat",))
        elif scenario == "context-insufficient":
            evidence = replace(evidence, max_context_tokens=2048)
    result = resolve_reference(route, registry, required_features=("chat", "reasoning"),
                               evidence=evidence)
    return {"schema":"post-apollo.forest.ui-binding-example.i2", "inputs":args,
            "routing":presentation_reference(route), "binding":public_binding_status(result)}


if __name__ == "__main__":
    try:
        print(json.dumps(evaluate(sys.argv[1:]), separators=(",", ":")))
    except ValueError:
        print("FORESTW_BINDING_EXAMPLE_REFUSED", file=sys.stderr)
        sys.exit(2)
