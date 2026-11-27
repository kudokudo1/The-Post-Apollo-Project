"""Recovered Forest AUTO usefulness policy; synthetic, no execution.

Historical semantic triggers only. An explicit preference takes precedence.
Recommendation is not a model binding, availability, grant or reservation.
No model, provider, filesystem, network, resources, prompt classifier or IO.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType

from shared_context_b6r1 import TaskContext

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
_SIGNAL = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z", re.ASCII)
_VALUES = MappingProxyType({
    "task_complexity": frozenset(("low", "normal", "high")),
    "known_small_failure": frozenset(("absent", "present")),
    "small_capability_suitability": frozenset(("sufficient", "insufficient", "unknown")),
})
_TRIGGERS = (
    ("task_complexity", "high", "high_task_complexity"),
    ("known_small_failure", "present", "known_small_failure"),
    ("small_capability_suitability", "insufficient", "small_capability_insufficient"),
)
_MAX_EVIDENCE = 32


class RoutingRefusal(ValueError):
    """Static refusal code; never expose raw evidence or exception text."""


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise RoutingRefusal("INVALID_IDENTIFIER")


def _context(context):
    if type(context) is not TaskContext:
        raise RoutingRefusal("INVALID_TASK_CONTEXT")


def _choice(value, choices, reason):
    if type(value) is not str or value not in choices:
        raise RoutingRefusal(reason)


@dataclass(frozen=True, slots=True)
class TurnScope:
    context: TaskContext
    turn_id: str

    def __post_init__(self):
        _context(self.context)
        _id(self.turn_id)


@dataclass(frozen=True, slots=True)
class ReasoningLeaseReference:
    """Fixture description of a temporary lease, never a reservation."""
    context: TaskContext
    lease_id: str
    revision: int
    mode: str
    remaining: int

    def __post_init__(self):
        _context(self.context)
        _id(self.lease_id)
        for value in (self.revision, self.remaining):
            if type(value) is not int or not 1 <= value <= 2**53 - 1:
                raise RoutingRefusal("INVALID_REASONING_LEASE")
        _choice(self.mode, ("light", "normal", "deep"), "INVALID_REASONING")


@dataclass(frozen=True, slots=True)
class ReasoningControlReference:
    """H16c synthetic turn projection; no source authentication or writes.

    Auto mode is a supplied per-turn recommendation, not a router or
    implicit default. A lease is scoped to the execution context, not
    transferable to another lifetime. COMPLETE is only fixture coverage.
    """
    scope: TurnScope
    revision: int
    coverage: str
    baseline: str
    explicit_mode: str | None = None
    temporary: ReasoningLeaseReference | None = None
    automatic_mode: str | None = None

    def __post_init__(self):
        if type(self.scope) is not TurnScope:
            raise RoutingRefusal("INVALID_TURN_SCOPE")
        if type(self.revision) is not int or not 1 <= self.revision <= 2**53 - 1:
            raise RoutingRefusal("INVALID_REASONING_CONTROL")
        _choice(self.coverage, ("COMPLETE", "UNKNOWN"), "INVALID_REASONING_CONTROL")
        _choice(self.baseline, ("auto", "light", "normal", "deep"),
                "INVALID_REASONING_CONTROL")
        for value in (self.explicit_mode, self.automatic_mode):
            if value is not None:
                _choice(value, ("light", "normal", "deep"), "INVALID_REASONING")
        if self.temporary is not None:
            if type(self.temporary) is not ReasoningLeaseReference:
                raise RoutingRefusal("INVALID_REASONING_LEASE")
            if self.temporary.context != self.scope.context:
                raise RoutingRefusal("REASONING_SCOPE_MISMATCH")


def _effective_reasoning(control):
    if type(control) is not ReasoningControlReference:
        raise RoutingRefusal("INVALID_REASONING_CONTROL")
    if control.coverage != "COMPLETE":
        raise RoutingRefusal("REASONING_COVERAGE_HOLD")
    if control.explicit_mode is not None:
        return control.explicit_mode, "explicit"
    if control.temporary is not None:
        return control.temporary.mode, "temporary"
    if control.baseline != "auto":
        return control.baseline, "pinned"
    if control.automatic_mode is not None:
        return control.automatic_mode, "automatic"
    raise RoutingRefusal("REASONING_COVERAGE_HOLD")


@dataclass(frozen=True, slots=True)
class ReasoningReference:
    """Resolved fixture reasoning; legacy direct references are nonauthoritative."""
    scope: TurnScope
    mode: str
    source: str
    control: ReasoningControlReference | None = None

    def __post_init__(self):
        if type(self.scope) is not TurnScope:
            raise RoutingRefusal("INVALID_TURN_SCOPE")
        if type(self.mode) is not str:
            raise RoutingRefusal("INVALID_REASONING")
        mode = self.mode.strip().lower()
        mode = {"quick": "light", "standard": "normal"}.get(mode, mode)
        _choice(mode, ("light", "normal", "deep"), "INVALID_REASONING")
        object.__setattr__(self, "mode", mode)
        _choice(self.source, ("explicit", "temporary", "pinned", "automatic",
                              "fallback"), "INVALID_REASONING_SOURCE")
        if self.control is not None:
            if (type(self.control) is not ReasoningControlReference
                    or self.control.scope != self.scope):
                raise RoutingRefusal("REASONING_SCOPE_MISMATCH")
            if _effective_reasoning(self.control) != (self.mode, self.source):
                raise RoutingRefusal("REASONING_CONTROL_MISMATCH")

    @property
    def selected_lease(self):
        """Original selected lease reference; not a claim or consumption."""
        if self.control is not None and self.source == "temporary":
            return self.control.temporary
        return None


def controlled_reasoning_reference(original, current):
    """Freeze equal fixture observations; no durable settlement or authority."""
    if (type(original) is not ReasoningControlReference
            or type(current) is not ReasoningControlReference):
        raise RoutingRefusal("INVALID_REASONING_CONTROL")
    if original != current:
        raise RoutingRefusal("REASONING_REFERENCE_CHANGED")
    mode, source = _effective_reasoning(original)
    return ReasoningReference(original.scope, mode, source, original)


@dataclass(frozen=True, slots=True)
class SemanticEvidence:
    """Producer-labelled reference, NOT proof of producer authenticity."""
    scope: TurnScope
    signal: str
    value: str
    producer: str

    def __post_init__(self):
        if type(self.scope) is not TurnScope:
            raise RoutingRefusal("INVALID_TURN_SCOPE")
        for item in (self.signal, self.value):
            if type(item) is not str or not _SIGNAL.fullmatch(item):
                raise RoutingRefusal("INVALID_EVIDENCE")
        _id(self.producer)


@dataclass(frozen=True, slots=True)
class FormControlReference:
    """H16b fixed reference to an already scoped control projection.

    COMPLETE is a synthetic observation, not proof of authorization.
    None denotes absence only in the complete original projection.
    Task override is either absent or explicitly bound to this TaskContext.
    No durable control reader/writer, lease or provider action.
    """
    scope: TurnScope
    revision: int
    coverage: str
    exact_form: str | None = None
    task_form: str | None = None
    task_context: TaskContext | None = None
    baseline: str | None = None
    tree_default: str | None = None

    def __post_init__(self):
        if type(self.scope) is not TurnScope:
            raise RoutingRefusal("INVALID_CONTROL_REFERENCE")
        if type(self.revision) is not int or not 1 <= self.revision <= 2**53 - 1:
            raise RoutingRefusal("INVALID_CONTROL_REFERENCE")
        _choice(self.coverage, ("COMPLETE", "UNKNOWN"), "INVALID_CONTROL_REFERENCE")
        for value in (self.exact_form, self.task_form):
            if value is not None:
                _choice(value, ("small", "big"), "INVALID_CONTROL_REFERENCE")
        for value in (self.baseline, self.tree_default):
            if value is not None:
                _choice(value, ("auto", "small", "big"), "INVALID_CONTROL_REFERENCE")
        if self.task_form is None:
            if self.task_context is not None:
                raise RoutingRefusal("INVALID_CONTROL_REFERENCE")
        elif (type(self.task_context) is not TaskContext
              or self.task_context != self.scope.context):
            raise RoutingRefusal("CONTROL_SCOPE_MISMATCH")


def _effective_form(control):
    if type(control) is not FormControlReference:
        raise RoutingRefusal("INVALID_CONTROL_REFERENCE")
    if control.coverage != "COMPLETE":
        raise RoutingRefusal("CONTROL_COVERAGE_HOLD")
    for value in (control.exact_form, control.task_form, control.baseline,
                  control.tree_default):
        if value is not None:
            return value
    raise RoutingRefusal("CONTROL_COVERAGE_HOLD")


@dataclass(frozen=True, slots=True)
class RoutingInput:
    scope: TurnScope
    requested_form: str
    reasoning: ReasoningReference
    evidence: tuple[SemanticEvidence, ...] = ()
    control: FormControlReference | None = None

    def __post_init__(self):
        if type(self.scope) is not TurnScope:
            raise RoutingRefusal("INVALID_TURN_SCOPE")
        if type(self.requested_form) is not str:
            raise RoutingRefusal("INVALID_FORM_CONTROL")
        form = self.requested_form.strip().lower()
        _choice(form, ("auto", "small", "big"), "INVALID_FORM_CONTROL")
        object.__setattr__(self, "requested_form", form)
        if self.control is not None:
            if type(self.control) is not FormControlReference or self.control.scope != self.scope:
                raise RoutingRefusal("CONTROL_SCOPE_MISMATCH")
            if _effective_form(self.control) != form:
                raise RoutingRefusal("CONTROL_FORM_MISMATCH")
        if type(self.reasoning) is not ReasoningReference or self.reasoning.scope != self.scope:
            raise RoutingRefusal("REASONING_SCOPE_MISMATCH")
        if type(self.evidence) is not tuple or len(self.evidence) > _MAX_EVIDENCE:
            raise RoutingRefusal("INVALID_EVIDENCE")
        for item in self.evidence:
            if type(item) is not SemanticEvidence or item.scope != self.scope:
                raise RoutingRefusal("EVIDENCE_SCOPE_MISMATCH")


def controlled_routing_input(original, current, *, reasoning, evidence=()):
    """Compare original and current fixture references before I1 routing.

    Independent real observations are not produced here. Retain original
    control revision/scope in RoutingInput so existing I1/I2 equality
    comparisons cannot silently drop it. Legacy direct I1 inputs remain
    non-authoritative. No currentness or permission claim from equality.
    """
    if (type(original) is not FormControlReference
            or type(current) is not FormControlReference):
        raise RoutingRefusal("INVALID_CONTROL_REFERENCE")
    if original != current:
        raise RoutingRefusal("CONTROL_REFERENCE_CHANGED")
    form = _effective_form(original)
    return RoutingInput(original.scope, form, reasoning, evidence, original)


@dataclass(frozen=True, slots=True)
class ModelFormRecommendation:
    """Frozen recommendation, not a resolved executable model binding."""
    original: RoutingInput
    form: str
    reasons: tuple[str, ...]

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
    def resolved_binding(self):
        return None


def recommend(routing):
    if type(routing) is not RoutingInput:
        raise RoutingRefusal("INVALID_ROUTING_INPUT")
    values = {}
    # Validate recognized evidence even for explicit requests. Explicit
    # selection does not let malformed evidence alter a decision.
    for item in routing.evidence:
        allowed = _VALUES.get(item.signal)
        if allowed is None:
            continue
        if item.value not in allowed:
            raise RoutingRefusal("INVALID_RECOGNIZED_EVIDENCE")
        if item.signal in values and values[item.signal] != item.value:
            raise RoutingRefusal("CONTRADICTORY_EVIDENCE")
        values[item.signal] = item.value
    if routing.requested_form != "auto":
        return ModelFormRecommendation(routing, routing.requested_form,
                                       ("explicit_form",))
    reasons = tuple(reason for signal, value, reason in _TRIGGERS
                    if values.get(signal) == value)
    return ModelFormRecommendation(
        routing, "big" if reasons else "small",
        reasons or ("no_big_escalation_evidence",),
    )


def preserve_recommendation(previous, current):
    """Exact reference continuity for same turn; never reroute a retry.

    Equality is not a durable receipt, replay protection or retry permission.
    Changed inputs HOLD via refusal; a new turn needs a new recommendation.
    Recompute solely to reject manually malformed previous reference objects.
    """
    if type(previous) is not ModelFormRecommendation or type(current) is not RoutingInput:
        raise RoutingRefusal("INVALID_RECOMMENDATION_REFERENCE")
    if previous.original != current:
        raise RoutingRefusal("ROUTING_INPUT_CHANGED")
    if previous != recommend(current):
        raise RoutingRefusal("INVALID_RECOMMENDATION_REFERENCE")
    return previous


def presentation_reference(recommendation):
    """Fixed bounded view. Not the UI wire contract or an authorized status."""
    if type(recommendation) is not ModelFormRecommendation:
        raise RoutingRefusal("INVALID_RECOMMENDATION_REFERENCE")
    if recommendation != recommend(recommendation.original):
        raise RoutingRefusal("INVALID_RECOMMENDATION_REFERENCE")
    return {
        "schema": "post-apollo.forest.model-form-reference.v1",
        "status": "UNKNOWN_HOLD",
        "requestedForm": recommendation.original.requested_form,
        "recommendedForm": recommendation.form,
        "resolvedForm": None,
        "resolvedBinding": None,
        "reasoningMode": recommendation.original.reasoning.mode,
        "reasons": list(recommendation.reasons),
        "sourceAuthenticated": False,
        "permissionGranted": False,
        "productionAuthority": False,
        "modelExecutionPermitted": False,
        "safeActions": [],
    }
