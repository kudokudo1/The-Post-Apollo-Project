"""B6-R2 Minimum Useful Canopy: pure capability selection, not authorization.

One definition per capability. Tree profiles reference those definitions.
Workshop core and individual optional selections produce metadata only.
No tool schemas, imports of tools, model context, dispatch, IO or issuer.
Historical mappings describe archived design, NOT current provider support.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from shared_context_b6r1 import TaskContext

_ID = re.compile(r"[a-z][a-z0-9-]{0,63}\Z", re.ASCII)
MAX_ITEMS = 128


class CapabilityRefusal(ValueError):
    """Stable refusal without echoing identifiers."""


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise CapabilityRefusal("INVALID_CAPABILITY_IDENTIFIER")


def _ids(values):
    if type(values) is not tuple or len(values) > MAX_ITEMS:
        raise CapabilityRefusal("INVALID_SELECTION")
    for value in values:
        _id(value)
    if len(set(values)) != len(values):
        raise CapabilityRefusal("DUPLICATE_SELECTION")


@dataclass(frozen=True, slots=True)
class Capability:
    key: str
    kind: str
    sticky_allowed: bool = False
    historical_target: str | None = None

    def __post_init__(self):
        _id(self.key)
        if type(self.kind) is not str or self.kind not in (
                "toolset", "context", "skill", "capability"):
            raise CapabilityRefusal("INVALID_KIND")
        if type(self.sticky_allowed) is not bool:
            raise CapabilityRefusal("INVALID_STICKY_POLICY")
        if self.historical_target is not None:
            if (type(self.historical_target) is not str
                    or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}",
                                        self.historical_target, re.ASCII)):
                raise CapabilityRefusal("INVALID_HISTORICAL_TARGET")


@dataclass(frozen=True, slots=True)
class Workshop:
    key: str
    core: tuple[str, ...]
    ready: tuple[str, ...] = ()

    def __post_init__(self):
        _id(self.key)
        _ids(self.core)
        _ids(self.ready)
        if not self.core or set(self.core) & set(self.ready):
            raise CapabilityRefusal("INVALID_WORKSHOP_POLICY")


@dataclass(frozen=True, slots=True)
class Registry:
    definitions: tuple[Capability, ...]

    def __post_init__(self):
        if (type(self.definitions) is not tuple
                or not 1 <= len(self.definitions) <= MAX_ITEMS
                or any(type(v) is not Capability for v in self.definitions)):
            raise CapabilityRefusal("INVALID_REGISTRY")
        _ids(tuple(v.key for v in self.definitions))

    def find(self, key):
        _id(key)
        for definition in self.definitions:
            if definition.key == key:
                return definition
        raise CapabilityRefusal("UNKNOWN_CAPABILITY")


@dataclass(frozen=True, slots=True)
class TreeProfile:
    """Reference policy bound to one principal and Tree via TaskContext.

    All fields are synthetic; caller-provided profiles cannot grant rights.
    Registry definitions can be shared without sharing Tree membership.
    """
    scope: TaskContext
    registry: Registry
    owned: tuple[str, ...]
    general_ready: tuple[str, ...]
    workshops: tuple[Workshop, ...]

    def __post_init__(self):
        if type(self.scope) is not TaskContext or type(self.registry) is not Registry:
            raise CapabilityRefusal("INVALID_PROFILE_SCOPE")
        _ids(self.owned)
        _ids(self.general_ready)
        if (type(self.workshops) is not tuple
                or not 1 <= len(self.workshops) <= MAX_ITEMS
                or any(type(w) is not Workshop for w in self.workshops)):
            raise CapabilityRefusal("INVALID_WORKSHOPS")
        _ids(tuple(w.key for w in self.workshops))
        for key in self.owned:
            self.registry.find(key)
        members = set(self.owned)
        if not set(self.general_ready) <= members:
            raise CapabilityRefusal("UNOWNED_GENERAL_REFERENCE")
        for workshop in self.workshops:
            if not set(workshop.core + workshop.ready) <= members:
                raise CapabilityRefusal("UNOWNED_WORKSHOP_REFERENCE")

    def workshop(self, key):
        _id(key)
        for workshop in self.workshops:
            if workshop.key == key:
                return workshop
        raise CapabilityRefusal("UNKNOWN_WORKSHOP")


@dataclass(frozen=True, slots=True)
class SelectionPlan:
    """Selected metadata references, not loaded runtime capabilities."""
    context: TaskContext
    workshop: str
    core: tuple[str, ...]
    selected: tuple[str, ...]
    dormant: tuple[str, ...]
    sticky: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def status(self):
        return "UNKNOWN_HOLD"

    @property
    def permission_granted(self):
        return False

    @property
    def production_authority(self):
        return False

    @property
    def model_execution_permitted(self):
        return False

    @property
    def safe_actions(self):
        return ()


def plan_selection(profile, context, workshop_key, *,
                   general=(), ready=(), sticky=(), prior=None):
    """Plan core plus explicitly selected individual capabilities.

    Sticky carry requires a prior selection in the same exact context and
    Workshop and explicit request to retain; no implicit group activation.
    It is recomputed against current profile membership and sticky policy.
    Prior records are forgeable reference values, not authorization or a
    durable runtime cache. No cross-context or cross-Workshop carry.
    """
    if type(profile) is not TreeProfile or type(context) is not TaskContext:
        raise CapabilityRefusal("INVALID_CONTEXT")
    if profile.scope != context:
        raise CapabilityRefusal("PROFILE_CONTEXT_MISMATCH")
    workshop = profile.workshop(workshop_key)
    for values in (general, ready, sticky):
        _ids(values)
    if not set(general) <= set(profile.general_ready):
        raise CapabilityRefusal("GENERAL_SELECTION_OUTSIDE_POLICY")
    if not set(ready) <= set(workshop.ready):
        raise CapabilityRefusal("READY_SELECTION_OUTSIDE_WORKSHOP")
    if sticky:
        if (type(prior) is not SelectionPlan or prior.context != context
                or prior.workshop != workshop.key):
            raise CapabilityRefusal("STICKY_CONTEXT_MISMATCH")
        _ids(prior.selected)
        eligible = set(profile.general_ready + workshop.core + workshop.ready)
        for key in sticky:
            if (key not in prior.selected or key not in eligible
                    or not profile.registry.find(key).sticky_allowed):
                raise CapabilityRefusal("STICKY_SELECTION_REFUSED")
    elif prior is not None:
        raise CapabilityRefusal("UNUSED_PRIOR_SELECTION")
    # Stable order, only one definition even when promoted General -> Core.
    selected = tuple(dict.fromkeys(workshop.core + general + ready + sticky))
    dormant = tuple(key for key in profile.owned if key not in selected)
    unresolved = tuple(key for key in selected
                       if profile.registry.find(key).historical_target is None)
    return SelectionPlan(context, workshop.key, workshop.core, selected,
                         dormant, sticky, unresolved)


# Source-only recovery of archived Bristlecone registry + adapter names.
# None means no historical target, NOT a current runtime availability check.
BRISTLECONE_REGISTRY = Registry((
    Capability("todo", "toolset", True, "todo"),
    Capability("clarify", "toolset", True, "clarify"),
    Capability("session", "context", True, "session_search"),
    Capability("memory", "context", True, "memory"),
    Capability("leaf", "context", True),
    Capability("web", "toolset", False, "web"),
    Capability("file", "toolset", False, "file"),
    Capability("terminal", "toolset", False, "terminal"),
    Capability("code-execution", "toolset", False, "code_execution"),
    Capability("debugging", "skill", True, "systematic-debugging"),
    Capability("testing", "skill", True, "test-driven-development"),
    Capability("special", "capability"),
    Capability("model-evaluation", "skill", False, "evaluation"),
    Capability("model-benchmarking", "skill"),
    Capability("model-inference", "skill", False, "inference"),
    Capability("quantization", "skill"),
    Capability("training", "skill"),
    Capability("runtime-inspection", "capability"),
))
BRISTLECONE_GENERAL = ("todo", "clarify", "session", "memory", "leaf")
BRISTLECONE_WORKSHOPS = (
    Workshop("research", ("web",)),
    Workshop("design", ("memory", "clarify")),
    Workshop("code-debug", ("file", "terminal"),
             ("code-execution", "debugging", "testing", "special")),
    Workshop("model", ("file", "terminal"),
             ("model-evaluation", "model-benchmarking", "model-inference",
              "quantization", "training", "runtime-inspection")),
)


def bristlecone_reference_profile(context):
    """Historical profile only; exact synthetic key, not alias resolution."""
    if type(context) is not TaskContext or context.tree_key != "bristlecone":
        raise CapabilityRefusal("PROFILE_TREE_MISMATCH")
    return TreeProfile(context, BRISTLECONE_REGISTRY,
                       tuple(v.key for v in BRISTLECONE_REGISTRY.definitions),
                       BRISTLECONE_GENERAL, BRISTLECONE_WORKSHOPS)
