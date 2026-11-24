"""B6-R1 shared Forest semantic reference; no protected execution.

Bark is a presentation surface, not a principal or Tree. These immutable
values describe boundaries for disposable tests. Matching them is NOT
authentication, permission, a live lease, a wire schema or authorization.
No IO, storage opener, scheduler, model call, issuer or dispatch callback.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re

_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
_REQUEST = re.compile(r"[A-Za-z0-9_-]{16,96}\Z", re.ASCII)
_MAX_GENERATION = 2**53 - 1
_BARK_FIELDS = frozenset(("requestId", "treeKey", "generation", "action"))


class ContractRefusal(ValueError):
    """Stable validation error; no input values echoed."""


def _key(value, field):
    if type(value) is not str or _KEY.fullmatch(value) is None:
        raise ContractRefusal("INVALID_" + field)


def _generation(value):
    if type(value) is not int or not 1 <= value <= _MAX_GENERATION:
        raise ContractRefusal("INVALID_GENERATION")


@dataclass(frozen=True, slots=True)
class TaskContext:
    """Owner-side reference, never construct from Bark request fields.

    Separate durable Tree identity from Clone/task/execution context.
    No model or runtime identifier defines Tree identity. Optional Clone
    means base Tree; a retained task context requires no running process.
    """
    principal_key: str
    tree_key: str
    clone_key: str | None
    task_id: str
    execution_context_id: str
    generation: int
    origin: str

    def __post_init__(self):
        for name in ("principal_key", "tree_key", "task_id",
                     "execution_context_id"):
            _key(getattr(self, name), name.upper())
        if self.clone_key is not None:
            _key(self.clone_key, "CLONE_KEY")
        _generation(self.generation)
        if type(self.origin) is not str or self.origin not in (
                "INTERACTIVE", "BACKGROUND"):
            raise ContractRefusal("INVALID_TASK_ORIGIN")


@dataclass(frozen=True, slots=True)
class BarkListRequest:
    """Untrusted presentation selection, not a native wire contract."""
    request_id: str
    requested_tree: str
    view_generation: int

    def __post_init__(self):
        if (type(self.request_id) is not str
                or _REQUEST.fullmatch(self.request_id) is None):
            raise ContractRefusal("INVALID_REQUEST_ID")
        _key(self.requested_tree, "REQUESTED_TREE")
        _generation(self.view_generation)


def parse_list_fields(fields):
    """Exact in-memory request fields; do not use as a network decoder.

    No owner, DB path, recipient, Clone, grant or model may be asserted by
    a Bark. Production byte decoding/authentication remains separate.
    """
    if (type(fields) is not dict or len(fields) != len(_BARK_FIELDS)
            or any(type(k) is not str for k in fields)
            or set(fields) != _BARK_FIELDS):
        raise ContractRefusal("INVALID_BARK_FIELDS")
    if type(fields["action"]) is not str or fields["action"] != "LIST_SESSIONS":
        raise ContractRefusal("UNSUPPORTED_ACTION")
    return BarkListRequest(fields["requestId"], fields["treeKey"],
                           fields["generation"])


@dataclass(frozen=True, slots=True)
class BarkAttachment:
    """Disposable host-side recipient reference; not authenticated evidence.

    One attachment links one task/context to one presentation recipient.
    Multiple attachments may reference the same task. A background task
    may exist without an attachment. No permission follows from this link.
    """
    context: TaskContext
    bark_id: str
    requester_id: str
    release_id: str
    seat_id: str
    recipient_id: str
    requested_tree: str
    view_generation: int
    attached: bool = True

    def __post_init__(self):
        if type(self.context) is not TaskContext:
            raise ContractRefusal("INVALID_TASK_CONTEXT")
        for name in ("bark_id", "requester_id", "release_id", "seat_id",
                     "recipient_id", "requested_tree"):
            _key(getattr(self, name), name.upper())
        _generation(self.view_generation)
        if type(self.attached) is not bool:
            raise ContractRefusal("INVALID_ATTACHMENT_STATE")

    def detach(self):
        """Pure presentation state transition, NOT a live revoke fence.

        Does not alter the immutable task/context or another attachment.
        Actual background execution and cancellation are outside R1.
        """
        return replace(self, attached=False)


@dataclass(frozen=True, slots=True)
class ListOperationReference:
    """Disposable operation binding; never accepted as an issuer grant."""
    attachment: BarkAttachment
    request: BarkListRequest
    operation_id: str

    def __post_init__(self):
        if type(self.attachment) is not BarkAttachment:
            raise ContractRefusal("INVALID_ATTACHMENT")
        if type(self.request) is not BarkListRequest:
            raise ContractRefusal("INVALID_REQUEST")
        _key(self.operation_id, "OPERATION_ID")
        if (self.request.requested_tree != self.attachment.requested_tree
                or self.request.view_generation != self.attachment.view_generation):
            raise ContractRefusal("REQUEST_ATTACHMENT_MISMATCH")
        if not self.attachment.attached:
            raise ContractRefusal("DETACHED_BARK")


@dataclass(frozen=True, slots=True)
class ReferenceResult:
    """No positive admission path, even when references match."""
    reason: str

    @property
    def status(self):
        return "UNKNOWN_HOLD"

    @property
    def permission_granted(self):
        return False

    @property
    def source_authenticated(self):
        return False

    @property
    def production_authority(self):
        return False

    @property
    def safe_actions(self):
        return ()


def compare_list_reference(original, request, current_attachment,
                           current_context):
    """Compare fixture bindings only, not independently observed currentness.

    Reference equality is deliberately not authorization. Production must
    obtain independently current source/seat/recipient and storage scope,
    C5 LIST and separate title consent, then fence actual outbound submission.
    """
    if (type(original) is not ListOperationReference
            or type(request) is not BarkListRequest
            or type(current_attachment) is not BarkAttachment
            or type(current_context) is not TaskContext):
        return ReferenceResult("INVALID_REFERENCE")
    if not current_attachment.attached:
        return ReferenceResult("DETACHED_BARK")
    if current_context != original.attachment.context:
        return ReferenceResult("TASK_CONTEXT_CHANGED")
    if current_attachment.context != current_context:
        return ReferenceResult("ATTACHMENT_CONTEXT_MISMATCH")
    if current_attachment != original.attachment:
        return ReferenceResult("ATTACHMENT_CHANGED")
    if request != original.request:
        return ReferenceResult("REQUEST_CHANGED")
    return ReferenceResult("REFERENCE_MATCH_AUTHORITY_HOLD")


def public_status(result):
    """Only fixed non-sensitive diagnostics; no identifiers or session rows."""
    if type(result) is not ReferenceResult or type(result.reason) is not str:
        reason = "INVALID_REFERENCE"
    elif result.reason in (
            "INVALID_REFERENCE", "DETACHED_BARK", "TASK_CONTEXT_CHANGED",
            "ATTACHMENT_CONTEXT_MISMATCH", "ATTACHMENT_CHANGED",
            "REQUEST_CHANGED", "REFERENCE_MATCH_AUTHORITY_HOLD"):
        reason = result.reason
    else:
        reason = "INVALID_REFERENCE"
    return {
        "schema": "post-apollo.forest.shared-reference.b6-r1",
        "status": "UNKNOWN_HOLD",
        "reason": reason,
        "sourceAuthenticated": False,
        "permissionGranted": False,
        "productionAuthority": False,
        "privateTitleDisclosureGranted": False,
        "modelExecutionPermitted": False,
        "safeActions": [],
    }
