"""I2 exact model binding reference. No IO or positive execution authority.

Recover the historical freeze-once binding pattern. All supplied values
are forgeable synthetic references, not installed artifact attestation.
Runtime options are descriptive, never passed to a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from model_form_routing_i1 import (
    TurnScope, ModelFormRecommendation, preserve_recommendation, RoutingRefusal,
)
from shared_context_b6r1 import TaskContext

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_FEATURES = ("chat", "tool-calling", "reasoning", "vision", "structured-output")


class BindingRefusal(ValueError):
    pass


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise BindingRefusal("INVALID_IDENTIFIER")


def _digest(value):
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise BindingRefusal("INVALID_DIGEST")


def _uint(value, maximum, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise BindingRefusal("INVALID_QUANTITY")


def _features(value):
    if (type(value) is not tuple or len(value) > len(_FEATURES)
            or any(type(v) is not str or v not in _FEATURES for v in value)
            or len(set(value)) != len(value)):
        raise BindingRefusal("INVALID_FEATURES")


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    model_name: str
    artifact_digest: str
    adapter: str
    runtime_instance: str
    runtime_version: str
    runtime_release_digest: str

    def __post_init__(self):
        for v in (self.model_name, self.adapter, self.runtime_instance,
                  self.runtime_version):
            _id(v)
        _digest(self.artifact_digest)
        _digest(self.runtime_release_digest)


@dataclass(frozen=True, slots=True)
class ModelBinding:
    binding_id: str
    form: str
    identity: ModelIdentity
    config_digest: str
    context_tokens: int
    output_tokens: int

    def __post_init__(self):
        _id(self.binding_id)
        if type(self.form) is not str or self.form not in ("small", "big"):
            raise BindingRefusal("INVALID_FORM")
        if type(self.identity) is not ModelIdentity:
            raise BindingRefusal("INVALID_MODEL_IDENTITY")
        _digest(self.config_digest)
        _uint(self.context_tokens, 2**31-1, 1)
        _uint(self.output_tokens, self.context_tokens, 1)


@dataclass(frozen=True, slots=True)
class BindingRegistry:
    """Owner/Tree scoped equipment reference; no UI preference promotion."""
    principal_key: str
    tree_key: str
    revision: int
    bindings: tuple[ModelBinding, ...]

    def __post_init__(self):
        _id(self.principal_key)
        _id(self.tree_key)
        _uint(self.revision, 2**53-1, 1)
        if (type(self.bindings) is not tuple or len(self.bindings) > 2
                or any(type(b) is not ModelBinding for b in self.bindings)):
            raise BindingRefusal("INVALID_REGISTRY")
        if (len({b.form for b in self.bindings}) != len(self.bindings)
                or len({b.binding_id for b in self.bindings}) != len(self.bindings)):
            raise BindingRefusal("DUPLICATE_BINDING")


@dataclass(frozen=True, slots=True)
class BindingEvidence:
    """One task-local observation reference, not source/currentness proof.

    None features or context limit means unknown. Empty features means
    observed no supported features, not unknown. No RAM/residency inputs.
    """
    scope: TurnScope
    binding: ModelBinding
    producer: str
    observation_id: str
    installed: bool | None
    supported_features: tuple[str, ...] | None
    max_context_tokens: int | None

    def __post_init__(self):
        if type(self.scope) is not TurnScope or type(self.binding) is not ModelBinding:
            raise BindingRefusal("INVALID_EVIDENCE_BINDING")
        _id(self.producer)
        _id(self.observation_id)
        if self.installed is not None and type(self.installed) is not bool:
            raise BindingRefusal("INVALID_INSTALL_STATUS")
        if self.supported_features is not None:
            _features(self.supported_features)
        if self.max_context_tokens is not None:
            _uint(self.max_context_tokens, 2**31-1, 1)


@dataclass(frozen=True, slots=True)
class BindingResult:
    recommendation: ModelFormRecommendation
    registry: BindingRegistry
    required_features: tuple[str, ...]
    evidence: BindingEvidence | None
    binding: ModelBinding | None
    reason: str

    @property
    def status(self):
        return "UNKNOWN_HOLD"

    @property
    def permission_granted(self):
        return False

    @property
    def model_execution_permitted(self):
        return False

    @property
    def production_authority(self):
        return False

    @property
    def resource_fit_established(self):
        return False


def resolve_reference(recommendation, registry, *, required_features, evidence=None):
    """Never substitute the other form; no binding on insufficient evidence.

    Only matching complete reference evidence resolves the descriptive
    binding. No claim of actual installed artifact or live provider support.
    """
    if type(recommendation) is not ModelFormRecommendation:
        raise BindingRefusal("INVALID_RECOMMENDATION")
    try:
        preserve_recommendation(recommendation, recommendation.original)
    except RoutingRefusal:
        raise BindingRefusal("INVALID_RECOMMENDATION") from None
    scope = recommendation.original.scope
    ctx = scope.context
    if type(registry) is not BindingRegistry:
        raise BindingRefusal("INVALID_REGISTRY")
    if (registry.principal_key, registry.tree_key) != (ctx.principal_key, ctx.tree_key):
        raise BindingRefusal("REGISTRY_SCOPE_MISMATCH")
    _features(required_features)
    if evidence is not None and type(evidence) is not BindingEvidence:
        raise BindingRefusal("INVALID_EVIDENCE")
    chosen = next((b for b in registry.bindings if b.form == recommendation.form), None)

    def result(reason, binding=None):
        return BindingResult(recommendation, registry, required_features,
                             evidence, binding, reason)

    if chosen is None:
        return result("FORM_UNBOUND")
    if evidence is None:
        return result("MODEL_EVIDENCE_MISSING")
    if evidence.scope != scope or evidence.binding != chosen:
        return result("MODEL_EVIDENCE_MISMATCH")
    if evidence.installed is False:
        return result("MODEL_NOT_INSTALLED")
    if evidence.installed is None:
        return result("INSTALL_STATUS_UNKNOWN")
    if evidence.supported_features is None or evidence.max_context_tokens is None:
        return result("CAPABILITY_EVIDENCE_UNKNOWN")
    if not set(required_features) <= set(evidence.supported_features):
        return result("REQUIRED_FEATURE_UNSUPPORTED")
    if chosen.context_tokens > evidence.max_context_tokens:
        return result("CONTEXT_LIMIT_INSUFFICIENT")
    return result("REFERENCE_BINDING_MATCH_AUTHORITY_HOLD", chosen)


def preserve_binding(previous, recommendation, registry, *, required_features, evidence=None):
    """Compare frozen inputs, never permit an automatic retry or rebind.

    Recompute for fixture integrity only. Actual durable original-outcome
    lookup remains separate. Registry revision or config changes refuse.
    """
    if type(previous) is not BindingResult:
        raise BindingRefusal("INVALID_BINDING_REFERENCE")
    current = resolve_reference(recommendation, registry,
                                required_features=required_features, evidence=evidence)
    if current != previous:
        raise BindingRefusal("BINDING_REFERENCE_CHANGED")
    return previous


def public_binding_status(result):
    if type(result) is not BindingResult:
        raise BindingRefusal("INVALID_BINDING_REFERENCE")
    preserve_binding(result, result.recommendation, result.registry,
                     required_features=result.required_features, evidence=result.evidence)
    return {
        "schema": "post-apollo.forest.binding-reference.i2",
        "status": "UNKNOWN_HOLD",
        "reason": result.reason,
        "requestedForm": result.recommendation.original.requested_form,
        "recommendedForm": result.recommendation.form,
        "referenceBindingMatched": result.binding is not None,
        "resolvedForm": None,
        "resolvedBinding": None,
        "sourceAuthenticated": False,
        "permissionGranted": False,
        "resourceFitEstablished": False,
        "modelExecutionPermitted": False,
        "productionAuthority": False,
        "safeActions": [],
    }
