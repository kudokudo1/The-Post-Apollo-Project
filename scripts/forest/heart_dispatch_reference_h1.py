"""Heart H1: bounded pre-dispatch reference comparison, never admission.

Pure, in-process candidate interface. Caller-supplied times, identities and
quantities are fixture references, not trusted source/currentness evidence.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from model_binding_i2 import BindingResult, BindingRefusal, preserve_binding
from resource_governor_p1 import (
    DIMENSIONS, ResourceRequest, ResourceRequirement, ResourceBudget,
    ResourceAvailability, ResourcePolicyRefusal, evaluate_resource_request,
)

SCHEMA = "post-apollo.forest.heart-dispatch-reference.h1"
# Proposed fixture ceiling, not a guarantee of live capacity or a lease.
MAX_AGE_NS = 5_000_000_000
MAX_NS = 2**63 - 1
_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
ENDPOINT = "http://127.0.0.1:11434"


class DispatchRefusal(ValueError):
    """Fixed refusal code."""


def _key(value):
    if type(value) is not str or not _KEY.fullmatch(value):
        raise DispatchRefusal("INVALID_REFERENCE_KEY")


def _time(value):
    if type(value) is not int or not 0 <= value <= MAX_NS:
        raise DispatchRefusal("INVALID_CLOCK_REFERENCE")


@dataclass(frozen=True, slots=True)
class TransportSettings:
    """First-Tree B2 subset only. No claim of enforced CPU/device limits."""
    model: str
    num_ctx: int
    max_predict: int

    def __post_init__(self):
        _key(self.model)
        if (type(self.num_ctx) is not int or not 512 <= self.num_ctx <= 8192
                or type(self.max_predict) is not int
                or not 1 <= self.max_predict <= min(512, self.num_ctx)):
            raise DispatchRefusal("INVALID_TRANSPORT_LIMIT")

    @property
    def config_digest(self):
        # Domain-separated candidate fingerprint of the B2 subset, not
        # a release digest or a claim of complete provider configuration.
        raw = json.dumps({
            "schema": "post-apollo.forest.heart-b2-settings.h1",
            "endpoint": ENDPOINT, "model": self.model,
            "num_ctx": self.num_ctx, "max_predict": self.max_predict,
        }, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class DispatchSnapshot:
    binding: BindingResult
    settings: TransportSettings
    operation_id: str
    attempt_id: str
    clock_domain: str
    captured_ns: int
    request: ResourceRequest
    requirement: ResourceRequirement
    budget: ResourceBudget
    availability: ResourceAvailability

    def __post_init__(self):
        for value in (self.operation_id, self.attempt_id, self.clock_domain):
            _key(value)
        _time(self.captured_ns)
        if (type(self.binding) is not BindingResult
                or type(self.settings) is not TransportSettings
                or type(self.request) is not ResourceRequest
                or type(self.requirement) is not ResourceRequirement
                or type(self.budget) is not ResourceBudget
                or type(self.availability) is not ResourceAvailability):
            raise DispatchRefusal("INVALID_SNAPSHOT")
        if self.requirement.request is not self.request:
            raise DispatchRefusal("REQUIREMENT_REQUEST_MISMATCH")


def _evaluate(s):
    try:
        b = s.binding
        preserve_binding(b, b.recommendation, b.registry,
                         required_features=b.required_features, evidence=b.evidence)
    except (BindingRefusal, AttributeError, TypeError):
        raise DispatchRefusal("INVALID_BINDING_REFERENCE") from None
    if b.binding is None:
        raise DispatchRefusal("MODEL_BINDING_UNRESOLVED")
    scope = b.recommendation.original.scope
    context = scope.context
    if context.clone_key is not None or context.origin != "INTERACTIVE":
        raise DispatchRefusal("FIRST_TREE_SCOPE_UNSUPPORTED")
    if b.recommendation.original.requested_form == "auto":
        raise DispatchRefusal("EXPLICIT_FORM_REQUIRED")
    if "chat" not in b.required_features:
        raise DispatchRefusal("CHAT_CAPABILITY_REQUIRED")
    if (s.settings.model != b.binding.identity.model_name
            or s.settings.num_ctx != b.binding.context_tokens
            or s.settings.max_predict != b.binding.output_tokens
            or s.settings.config_digest != b.binding.config_digest):
        raise DispatchRefusal("TRANSPORT_BINDING_MISMATCH")
    if (s.request.task_id, s.request.execution_context_id,
        s.request.model_form, s.request.reasoning_mode) != (
            context.task_id, context.execution_context_id,
            b.binding.form, b.recommendation.original.reasoning.mode):
        raise DispatchRefusal("RESOURCE_SCOPE_MISMATCH")
    # P1 allows unset ceilings and incremental zero. The first-Tree
    # candidate deliberately requires explicit ceilings and positive
    # requirements in every dimension: B2 cannot enforce CPU-only or
    # otherwise prove zero incremental demand at this seam.
    if any(getattr(s.budget, d) is None for d in DIMENSIONS):
        raise DispatchRefusal("EXPLICIT_BUDGET_REQUIRED")
    if any(getattr(s.requirement, d) == 0 for d in DIMENSIONS):
        raise DispatchRefusal("ZERO_DEMAND_UNESTABLISHED")
    try:
        return evaluate_resource_request(s.request, s.requirement,
                                         s.budget, s.availability).outcome
    except ResourcePolicyRefusal:
        raise DispatchRefusal("INVALID_RESOURCE_REFERENCE") from None


def compare_dispatch(original, current, *, now_ns):
    """Recompute both decisions; compare all references except capture time.

    No positive authorization, IO, reservation, retry, dispatch or clock read.
    A changed measurement requires a newly evaluated decision, not a replay.
    """
    def result(reason, outcome=None, matched=False):
        return {
            "schema": SCHEMA, "status": "UNKNOWN_HOLD", "reason": reason,
            "modeled_outcome": outcome, "dispatch_reference_matched": matched,
            "source_authenticated": False, "freshness_verified": False,
            "resource_reserved": False, "safe_to_start_inference": False,
            "permission_granted": False, "production_authority": False,
            "safe_actions": [],
        }
    if type(original) is not DispatchSnapshot or type(current) is not DispatchSnapshot:
        return result("INVALID_SNAPSHOT")
    try:
        _time(now_ns)
        if original.clock_domain != current.clock_domain:
            raise DispatchRefusal("CLOCK_DOMAIN_CHANGED")
        if not original.captured_ns < current.captured_ns <= now_ns:
            raise DispatchRefusal("CLOCK_ORDER_INVALID")
        if now_ns - original.captured_ns > MAX_AGE_NS:
            raise DispatchRefusal("REFERENCE_EXPIRED")
        old = _evaluate(original)
        new = _evaluate(current)
        if (original.binding != current.binding
                or original.settings != current.settings
                or original.operation_id != current.operation_id
                or original.attempt_id != current.attempt_id
                or original.request != current.request
                or original.requirement != current.requirement
                or original.budget != current.budget
                or original.availability != current.availability):
            return result("DISPATCH_REFERENCE_CHANGED", new)
        if old != "approve" or new != "approve":
            return result("MODELED_RESOURCE_NOT_FIT", new)
        return result("REFERENCE_MATCH_AUTHORITY_HOLD", new, True)
    except DispatchRefusal as exc:
        return result(str(exc))
