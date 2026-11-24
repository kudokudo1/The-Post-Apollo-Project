from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from model_form_routing_i1 import TurnScope, ReasoningReference, RoutingInput, recommend
from model_binding_i2 import (
    ModelIdentity, ModelBinding, BindingRegistry, BindingEvidence,
    BindingRefusal, resolve_reference, preserve_binding, public_binding_status,
)


def digest(c):
    return "sha256:" + c * 64


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.scope = TurnScope(TaskContext("owner-a", "bristlecone", None,
                                "task-a", "ctx-a", 1, "INTERACTIVE"), "turn-a")
        self.route = recommend(RoutingInput(self.scope, "big",
                               ReasoningReference(self.scope, "deep", "explicit")))
        self.identity = ModelIdentity("fixture:big", digest("a"), "ollama",
                                      "runtime-a", "0.0.1", digest("b"))
        self.big = ModelBinding("big-binding", "big", self.identity,
                                digest("c"), 4096, 256)
        self.small = replace(self.big, binding_id="small-binding", form="small",
                             identity=replace(self.identity, model_name="fixture:small",
                                              artifact_digest=digest("d")))
        self.registry = BindingRegistry("owner-a", "bristlecone", 1, (self.small, self.big))
        self.evidence = BindingEvidence(self.scope, self.big, "fixture-observer",
                                        "obs-a", True, ("chat", "reasoning"), 8192)

    def resolve(self, registry=None, evidence=None, features=("chat", "reasoning")):
        r = resolve_reference(self.route, self.registry if registry is None else registry,
                              required_features=features, evidence=evidence)
        self.assertEqual(r.status, "UNKNOWN_HOLD")
        self.assertFalse(r.permission_granted)
        self.assertFalse(r.model_execution_permitted)
        self.assertFalse(r.resource_fit_established)
        self.assertFalse(r.production_authority)
        return r

    def test_exact_reference_match(self):
        r = self.resolve(evidence=self.evidence)
        self.assertIs(r.binding, self.big)
        self.assertEqual(r.reason, "REFERENCE_BINDING_MATCH_AUTHORITY_HOLD")

    def test_unbound_big_never_falls_back(self):
        r = self.resolve(replace(self.registry, bindings=(self.small,)))
        self.assertEqual(r.reason, "FORM_UNBOUND")
        self.assertIsNone(r.binding)

    def test_no_evidence_no_resolution(self):
        self.assertEqual(self.resolve().reason, "MODEL_EVIDENCE_MISSING")

    def test_same_name_changed_digest_refused(self):
        other = replace(self.big, identity=replace(self.identity, artifact_digest=digest("e")))
        self.assertEqual(self.resolve(evidence=replace(self.evidence, binding=other)).reason,
                         "MODEL_EVIDENCE_MISMATCH")

    def test_runtime_identity_changes_refused(self):
        for changes in ({"runtime_instance": "runtime-b"}, {"runtime_version": "0.0.2"},
                        {"runtime_release_digest": digest("e")}, {"adapter": "other"}):
            other = replace(self.big, identity=replace(self.identity, **changes))
            self.assertEqual(self.resolve(evidence=replace(self.evidence, binding=other)).reason,
                             "MODEL_EVIDENCE_MISMATCH")

    def test_configuration_and_context_changes_refused(self):
        for changes in ({"config_digest": digest("e")}, {"context_tokens": 2048},
                        {"output_tokens": 128}, {"binding_id": "another"}):
            self.assertEqual(self.resolve(evidence=replace(self.evidence,
                             binding=replace(self.big, **changes))).reason,
                             "MODEL_EVIDENCE_MISMATCH")

    def test_turn_context_and_clone_mismatch(self):
        for scope in (replace(self.scope, turn_id="other"),
                      replace(self.scope, context=replace(self.scope.context, generation=2)),
                      replace(self.scope, context=replace(self.scope.context, clone_key="other"))):
            self.assertEqual(self.resolve(evidence=replace(self.evidence, scope=scope)).reason,
                             "MODEL_EVIDENCE_MISMATCH")

    def test_wrong_registry_principal_or_tree_refused(self):
        for change in ({"principal_key": "other"}, {"tree_key": "maple"}):
            with self.assertRaisesRegex(BindingRefusal, "REGISTRY_SCOPE_MISMATCH"):
                self.resolve(replace(self.registry, **change), self.evidence)

    def test_install_false_and_unknown(self):
        for value, reason in ((False, "MODEL_NOT_INSTALLED"), (None, "INSTALL_STATUS_UNKNOWN")):
            self.assertEqual(self.resolve(evidence=replace(self.evidence, installed=value)).reason, reason)

    def test_missing_capability_evidence(self):
        for change in ({"supported_features": None}, {"max_context_tokens": None}):
            self.assertEqual(self.resolve(evidence=replace(self.evidence, **change)).reason,
                             "CAPABILITY_EVIDENCE_UNKNOWN")

    def test_empty_is_not_unknown(self):
        r = self.resolve(evidence=replace(self.evidence, supported_features=()))
        self.assertEqual(r.reason, "REQUIRED_FEATURE_UNSUPPORTED")

    def test_required_feature_mismatch(self):
        self.assertEqual(self.resolve(evidence=self.evidence, features=("vision",)).reason,
                         "REQUIRED_FEATURE_UNSUPPORTED")

    def test_context_limit(self):
        self.assertEqual(self.resolve(evidence=replace(self.evidence, max_context_tokens=2048)).reason,
                         "CONTEXT_LIMIT_INSUFFICIENT")

    def test_bad_digest_and_bounds(self):
        for val in ("fixture", "sha256:"+"A"*64, None):
            with self.assertRaises(BindingRefusal):
                replace(self.identity, artifact_digest=val)
        for changes in ({"context_tokens": True}, {"context_tokens": 0},
                        {"output_tokens": 5000}, {"form": "auto"}):
            with self.assertRaises(BindingRefusal):
                replace(self.big, **changes)

    def test_duplicate_slots_or_ids_refused(self):
        for bindings in ((self.big, self.big), (self.big, replace(self.small, binding_id=self.big.binding_id))):
            with self.assertRaises(BindingRefusal):
                replace(self.registry, bindings=bindings)

    def test_preserve_exact_reference(self):
        r = self.resolve(evidence=self.evidence)
        self.assertIs(preserve_binding(r, self.route, self.registry,
                      required_features=("chat", "reasoning"), evidence=self.evidence), r)

    def test_changed_registry_or_evidence_never_rebinds_retry(self):
        r = self.resolve(evidence=self.evidence)
        for registry, evidence in ((replace(self.registry, revision=2), self.evidence),
                                   (self.registry, replace(self.evidence, observation_id="obs-b"))):
            with self.assertRaisesRegex(BindingRefusal, "BINDING_REFERENCE_CHANGED"):
                preserve_binding(r, self.route, registry,
                                 required_features=("chat", "reasoning"), evidence=evidence)

    def test_projection_no_live_binding_claim(self):
        r = self.resolve(evidence=self.evidence)
        p = public_binding_status(r)
        self.assertTrue(p["referenceBindingMatched"])
        self.assertIsNone(p["resolvedBinding"])
        self.assertFalse(p["resourceFitEstablished"])
        self.assertNotIn("fixture:big", str(p))
        self.assertNotIn(digest("a"), str(p))
        with self.assertRaises(BindingRefusal):
            public_binding_status(replace(r, reason="private data"))

    def test_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.big.context_tokens = 12

    def test_unknown_or_duplicate_features_refused(self):
        for features in (("file",), ("chat", "chat"), ["chat"], (None,)):
            with self.assertRaises(BindingRefusal):
                self.resolve(evidence=self.evidence, features=features)


if __name__ == "__main__":
    unittest.main()
