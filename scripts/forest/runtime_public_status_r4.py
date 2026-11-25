"""R4: fixed status candidate for an isolated public fixture.

No sender, UI binding, authentication, protected admission or model execution.
The owner must independently establish disposable public provenance and
resolve the current attachment and operation before every observation.
Never use this projector on a private operation, even for status alone.
"""
from __future__ import annotations

from types import MappingProxyType
from enum import Enum
from dataclasses import dataclass

from runtime_events_r3 import InternalEvent, OperationRef
from shared_context_b6r1 import BarkAttachment, _KEY

SCHEMA = "postapollo.forest.public-runtime-status.v1"


class Observation(Enum):
    # Internal sentinel, deliberately not JSON serializable. None means
    # withdrawal; NO_UPDATE means retain display without sending anything.
    NO_UPDATE = 0


@dataclass(frozen=True, slots=True)
class FixtureTreeBinding:
    """Host-resolved first-Tree pair, not an alias registry or proof of trust.

    The fixture host must select this independently of Bark inputs. Only
    the explicitly coordinated first-Tree pair is supported. Other Trees
    require an agreed mapping rather than normalization or guesswork.
    """
    canonical_tree: str
    presentation_tree: str

    def __post_init__(self):
        if (type(self.canonical_tree) is not str
                or type(self.presentation_tree) is not str
                or (self.canonical_tree, self.presentation_tree)
                != ("cherry", "CHERRY")):
            raise ValueError("UNAPPROVED_FIXTURE_TREE_PAIR")

    def matches(self, operation, attachment):
        return (type(operation) is OperationRef
                and type(attachment) is BarkAttachment
                and operation.context_ref.context.clone_key is None
                and operation.context_ref.context.tree_key == self.canonical_tree
                and attachment.context == operation.context_ref.context
                and attachment.requested_tree == self.presentation_tree)


def _packet(status):
    return {"schema": SCHEMA, "status": status,
            "sourceAuthenticated": False, "permissionGranted": False,
            "productionAuthority": False, "modelExecutionPermitted": False,
            "safeActions": []}


class PublicRuntimeStatus:
    """One attachment lifetime; owner-thread only, no actual outbound send.

    Once withdrawn it never reattaches, and once terminal it never resumes.
    Candidate packets contain fixed labels only, not any internal identifier,
    ordinal, text, error, timing or model setting. No release authorization
    follows from a valid projection. Actual send requires owner review.
    """

    def __init__(self, operation: OperationRef, attachment: BarkAttachment, *,
                 tree_binding: FixtureTreeBinding):
        if (type(operation) is not OperationRef
                or type(attachment) is not BarkAttachment
                or not attachment.attached
                or type(tree_binding) is not FixtureTreeBinding
                or not tree_binding.matches(operation, attachment)):
            raise ValueError("INVALID_FIXTURE_BINDING")
        self._operation = operation
        self._attachment = attachment
        self._tree_binding = tree_binding
        self._ordinal = 0
        self._attempt = None
        self._phase = "INITIAL"
        self._status = "IDLE"
        self._withdrawn = False
        self._terminal = False
        self._stop = False

    def _current(self, operation, attachment, tree_binding):
        if (self._withdrawn
                or type(operation) is not OperationRef
                or operation != self._operation
                or type(attachment) is not BarkAttachment
                or not attachment.attached
                or attachment != self._attachment
                or type(tree_binding) is not FixtureTreeBinding
                or tree_binding != self._tree_binding
                or not tree_binding.matches(operation, attachment)):
            self._withdrawn = True
            return False
        return True

    def withdraw(self):
        """Local view withdrawal; neither STOP nor permission revocation."""
        self._withdrawn = True

    def snapshot(self, *, current_operation, current_attachment, current_tree_binding):
        if not self._current(current_operation, current_attachment, current_tree_binding):
            return None
        return _packet(self._status)

    def _change(self, previous):
        return (_packet(self._status) if previous != self._status
                else Observation.NO_UPDATE)

    def _hold(self):
        previous = self._status
        self._terminal = True
        self._status = "UNKNOWN_HOLD"
        return self._change(previous)

    def observe(self, event, *, current_operation, current_attachment, current_tree_binding):
        if not self._current(current_operation, current_attachment, current_tree_binding):
            return None
        if self._terminal:
            # Duplicate/postterminal events cannot revive or promote a view.
            return self._hold()
        if (type(event) is not InternalEvent
                or event.operation != self._operation
                or type(event.ordinal) is not int
                or event.ordinal != self._ordinal + 1
                or type(event.payload) is not MappingProxyType):
            return self._hold()
        previous = self._status
        name = event.payload.get("event")
        if type(name) is not str:
            return self._hold()
        if name == "RESERVED":
            if (self._phase != "REQUESTED"
                    or type(event.attempt_id) is not str
                    or _KEY.fullmatch(event.attempt_id) is None
                    or event.payload.get("attempt_id") != event.attempt_id):
                return self._hold()
            self._attempt = event.attempt_id
        elif event.attempt_id != self._attempt:
            return self._hold()
        self._ordinal = event.ordinal

        if name == "REQUESTED" and self._phase == "INITIAL":
            self._phase = "REQUESTED"
            self._status = "REQUEST_PENDING"
        elif name == "RESERVED" and self._phase == "REQUESTED":
            self._phase = "RESERVED"
            self._status = "PREPARING"
        elif name == "STARTED" and self._phase == "RESERVED":
            self._phase = "STARTED"
            self._status = "GENERATING"
        elif name == "DELTA" and self._phase in ("STARTED", "DELTA"):
            if event.payload.get("provisional") is not True:
                return self._hold()
            self._phase = "DELTA"
            self._status = "GENERATING"
        elif name == "COMMITTED" and self._phase == "DELTA":
            self._terminal = True
            self._status = "LOCAL_COMMIT_RECORDED"
        elif name == "UNKNOWN_HOLD" and self._phase != "INITIAL":
            return self._hold()
        else:
            return self._hold()
        if self._stop and not self._terminal:
            self._status = "STOP_REQUESTED"
        return self._change(previous)

    def observe_stop_ack(self, disposition, attempt_id, *,
                         current_operation, current_attachment, current_tree_binding):
        """Owner reports actual R2 STOP disposition; does not dispatch STOP.

        Never accept this observation directly from Bark. A latched STOP
        is not terminal cancellation. An entry-won/closed ACK adds no claim.
        """
        if not self._current(current_operation, current_attachment, current_tree_binding):
            return None
        if self._terminal:
            return Observation.NO_UPDATE
        if (type(disposition) is not str
                or disposition not in ("STOP_LATCHED",
                    "COMMIT_ENTRY_ALREADY_WON", "CONTROL_CLOSED")
                or attempt_id != self._attempt
                or self._phase == "INITIAL"):
            return self._hold()
        previous = self._status
        if disposition == "STOP_LATCHED":
            self._stop = True
            self._status = "STOP_REQUESTED"
        return self._change(previous)

    def finish(self, *, current_operation, current_attachment, current_tree_binding):
        """Missing terminal evidence is HOLD, never inferred success."""
        if not self._current(current_operation, current_attachment, current_tree_binding):
            return None
        return Observation.NO_UPDATE if self._terminal else self._hold()
