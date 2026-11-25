"""Recovery of original Bristlecone layered Hot Context, fixture-only.

Already selected, owner-resolved records only. No store, matcher, learning
approval, runtime instructions injection, cache, or execution admission.
"""
from dataclasses import dataclass
import json

from context_first_tree_m2 import ContextRefusal, _key
from shared_context_b6r1 import TaskContext

MAX_RECORDS = 32
MAX_RECORD_BYTES = 4096
MAX_ASSEMBLY_BYTES = 16384
MAX_GENERATION = 2**53 - 1
LAYERS = (
    ("user-correction", "User Corrections"),
    ("user-constraint", "User Constraints"),
    ("user-preference", "User Preferences"),
    ("current-context", "Current Context"),
    ("operational-learning", "Operational Learning"),
)
KINDS = frozenset(kind for kind, _ in LAYERS)


def _generation(value):
    if type(value) is not int or not 0 <= value <= MAX_GENERATION:
        raise ContextRefusal("INVALID_HOT_GENERATION")


def _body(value):
    if type(value) is not str or not value.strip() or len(value) > MAX_RECORD_BYTES:
        raise ContextRefusal("INVALID_HOT_TEXT")
    if any(ord(c) < 32 and c not in "\n\t" or 0x7f <= ord(c) <= 0x9f
           or 0x202a <= ord(c) <= 0x202e or 0x2066 <= ord(c) <= 0x2069
           or 0xd800 <= ord(c) <= 0xdfff
           for c in value):
        raise ContextRefusal("INVALID_HOT_TEXT")
    # Surrogates are rejected above, before encoding. Never attach a
    # UnicodeEncodeError containing the rejected body to a refusal.
    if len(value.encode("utf-8")) > MAX_RECORD_BYTES:
        raise ContextRefusal("INVALID_HOT_TEXT")


@dataclass(frozen=True, slots=True)
class HotRouteStamp:
    """A fresh owner-selected route for a single task/input, not a grant."""
    context: TaskContext
    input_generation: int
    policy_generation: int
    user_context_generation: int
    operational_generation: int
    user_record_ids: tuple
    operational_record_ids: tuple

    def __post_init__(self):
        if type(self.context) is not TaskContext:
            raise ContextRefusal("INVALID_HOT_CONTEXT")
        for value in (self.input_generation, self.policy_generation,
                      self.user_context_generation, self.operational_generation):
            _generation(value)
        for ids in (self.user_record_ids, self.operational_record_ids):
            if type(ids) is not tuple or len(ids) > MAX_RECORDS:
                raise ContextRefusal("INVALID_HOT_SELECTION")
            for key in ids:
                _key(key)
        ids = self.user_record_ids + self.operational_record_ids
        if len(ids) > MAX_RECORDS or len(set(ids)) != len(ids):
            raise ContextRefusal("INVALID_HOT_SELECTION")


@dataclass(frozen=True, slots=True)
class SelectedHotRecord:
    """Synthetic selected record; active is a fixture field, not approval."""
    principal_key: str
    tree_key: str
    record_id: str
    kind: str
    generation: int
    active: bool
    text: str

    def __post_init__(self):
        for key in (self.principal_key, self.tree_key, self.record_id):
            _key(key)
        if type(self.kind) is not str or self.kind not in KINDS:
            raise ContextRefusal("INVALID_HOT_KIND")
        _generation(self.generation)
        if type(self.active) is not bool:
            raise ContextRefusal("INVALID_HOT_RECORD")
        _body(self.text)


@dataclass(frozen=True, slots=True)
class HotAssembly:
    route: HotRouteStamp
    reference_text: str
    record_ids: tuple
    sections: tuple
    byte_count: int


def assemble_hot_context(requested, *, current, user_records=(),
                         operational_records=(), max_bytes=MAX_ASSEMBLY_BYTES):
    """Deterministic, whole-record reference fragment; never dispatch it.

    Owner must establish provenance, exact independently current route and
    selection. This does not authorize retrieval or use of remembered data.
    Byte budget includes framing; it is NOT tokenizer/model fit evidence.
    """
    if (type(requested) is not HotRouteStamp or type(current) is not HotRouteStamp
            or requested != current):
        raise ContextRefusal("HOT_ROUTE_CHANGED")
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_ASSEMBLY_BYTES:
        raise ContextRefusal("INVALID_HOT_BUDGET")
    for records, ids, generation, operational in (
        (user_records, current.user_record_ids, current.user_context_generation, False),
        (operational_records, current.operational_record_ids,
         current.operational_generation, True),
    ):
        if (type(records) is not tuple or len(records) != len(ids)
                or any(type(r) is not SelectedHotRecord for r in records)):
            raise ContextRefusal("INVALID_HOT_SELECTION")
        if tuple(r.record_id for r in records) != ids:
            raise ContextRefusal("HOT_SELECTION_CHANGED")
        for record in records:
            if (not record.active or record.principal_key != current.context.principal_key
                    or record.tree_key != current.context.tree_key
                    or record.generation != generation
                    or (record.kind == "operational-learning") != operational):
                raise ContextRefusal("HOT_RECORD_SCOPE_CHANGED")
    records = user_records + operational_records
    if not records:
        return HotAssembly(current, "", (), (), 0)
    # A JSON reference block preserves record boundaries even when text
    # contains headings or quotes. Labeling is not prompt-injection defense.
    sections = []
    ordered = []
    blocks = []
    for kind, label in LAYERS:
        group = tuple(r for r in records if r.kind == kind)
        if group:
            sections.append(label)
            ordered.extend(r.record_id for r in group)
            blocks.append({"layer": label, "records": [r.text for r in group]})
    text = ("Forest Hot Context (remembered reference data; current instructions "
            "and active policy take precedence).\n"
            + json.dumps(blocks, ensure_ascii=False, separators=(",", ":")))
    size = len(text.encode("utf-8"))
    if size > max_bytes:
        raise ContextRefusal("HOT_BUDGET_EXCEEDED")
    return HotAssembly(current, text, tuple(ordered), tuple(sections), size)
