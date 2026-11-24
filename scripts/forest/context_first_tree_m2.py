"""DOC 4F M2: disposable public fixture context, not production admission.

Caller must own an isolated synthetic B1 database and resolve the current
TaskContext/session binding independently. No database opening, authentication,
permission, model execution, wire serialization, or durable Clone registry.
"""
from dataclasses import dataclass
import sqlite3

from shared_context_b6r1 import TaskContext
from session_journal_v0 import ForestSessionJournal, KEY, MAX_BODY, MAX_PAGE
from capability_registry_b6r2 import (
    SelectionPlan, TreeProfile, CapabilityRefusal, plan_selection,
)
from ollama_chat_transport import (
    MAX_HISTORY, MAX_MESSAGE_BYTES, MAX_TOTAL_PROMPT_BYTES,
    ChatRefusal, _messages,
)


class ContextRefusal(ValueError):
    """Fixed reason; never echo journal values."""


def _key(value):
    if type(value) is not str or KEY.fullmatch(value) is None:
        raise ContextRefusal("INVALID_IDENTIFIER")


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise ContextRefusal("INVALID_INTEGER")


@dataclass(frozen=True, slots=True)
class SessionContextRef:
    context: TaskContext
    session_id: str
    expected_revision: int
    user_turn_id: str

    def __post_init__(self):
        if type(self.context) is not TaskContext:
            raise ContextRefusal("INVALID_CONTEXT")
        if self.context.clone_key is not None:
            raise ContextRefusal("CLONE_BINDING_UNAVAILABLE")
        _key(self.session_id)
        _key(self.user_turn_id)
        _integer(self.expected_revision)


@dataclass(frozen=True, slots=True)
class HistoryTurn:
    turn_id: str
    ordinal: int
    role: str
    content: str
    provider: str
    model: str
    recorded_at_ms: int

    def __post_init__(self):
        _key(self.turn_id)
        _integer(self.ordinal, 1)
        _integer(self.recorded_at_ms, 1)
        if type(self.role) is not str or self.role not in ("user", "assistant"):
            raise ContextRefusal("INVALID_HISTORY")
        if self.role == "assistant":
            _key(self.provider)
            _key(self.model)
        elif self.provider != "" or self.model != "":
            raise ContextRefusal("INVALID_HISTORY")
        if type(self.content) is not str or not self.content or "\x00" in self.content:
            raise ContextRefusal("INVALID_HISTORY")
        try:
            size = len(self.content.encode("utf-8"))
        except UnicodeError as exc:
            raise ContextRefusal("INVALID_HISTORY") from exc
        if size > MAX_BODY:
            raise ContextRefusal("INVALID_HISTORY")


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    ref: SessionContextRef
    messages: tuple[HistoryTurn, ...]
    omitted_prefix_count: int
    capability_plan: SelectionPlan | None

    def transport_messages(self):
        # New copies; no journal metadata or capability data reaches B2.
        return _messages([{"role": t.role, "content": t.content}
                          for t in self.messages])


def select_history(ref, newest_rows, *, capability_plan=None):
    """Pure selection over bounded newest-first *committed* B1 turn records.

    Retain a contiguous suffix. An older unfit row ends selection; never
    skip it and take earlier rows, slice bytes, or change the journal.
    Byte limits are not tokenizer fit evidence.
    """
    if type(ref) is not SessionContextRef:
        raise ContextRefusal("INVALID_REFERENCE")
    if capability_plan is not None and (
            type(capability_plan) is not SelectionPlan
            or capability_plan.context != ref.context):
        raise ContextRefusal("CAPABILITY_CONTEXT_MISMATCH")
    if (type(newest_rows) is not tuple
            or not 1 <= len(newest_rows) <= MAX_HISTORY
            or any(type(t) is not HistoryTurn for t in newest_rows)):
        raise ContextRefusal("INVALID_HISTORY")
    latest = newest_rows[0]
    if latest.role != "user" or latest.turn_id != ref.user_turn_id:
        raise ContextRefusal("LATEST_USER_MISMATCH")
    if latest.ordinal > ref.expected_revision:
        raise ContextRefusal("INVALID_HISTORY_REVISION")
    if (len({t.turn_id for t in newest_rows}) != len(newest_rows)
            or any(t.ordinal != latest.ordinal - i
                   for i, t in enumerate(newest_rows))
            or len(newest_rows) != min(latest.ordinal, MAX_HISTORY)):
        raise ContextRefusal("INVALID_HISTORY_ORDER")
    chosen = []
    total = 0
    for turn in newest_rows:
        size = len(turn.content.encode("utf-8"))
        if size > MAX_MESSAGE_BYTES or total + size > MAX_TOTAL_PROMPT_BYTES:
            if not chosen:
                raise ContextRefusal("LATEST_USER_TOO_LARGE")
            break
        chosen.append(turn)
        total += size
    ordered = tuple(reversed(chosen))
    snapshot = ContextSnapshot(ref, ordered, ordered[0].ordinal - 1,
                               capability_plan)
    try:
        snapshot.transport_messages()
    except ChatRefusal as exc:
        raise ContextRefusal("TRANSPORT_HISTORY_REFUSED") from exc
    return snapshot


def _journal(journal):
    if type(journal) is not ForestSessionJournal:
        raise ContextRefusal("INVALID_JOURNAL")
    return journal.db


def snapshot_in_transaction(journal, requested, *, current, capability_plan=None):
    """Read a scoped snapshot inside the caller's existing transaction.

    B3 must eventually call within its BEGIN IMMEDIATE reservation transaction,
    before inference, and keep existing unique attempt/commit/recovery rules.
    in_transaction alone cannot prove writer ownership or fixture provenance.
    No standalone snapshot may authorize execution or be reused after commit.
    """
    if (type(requested) is not SessionContextRef
            or type(current) is not SessionContextRef
            or requested != current):
        raise ContextRefusal("CONTEXT_CHANGED")
    db = _journal(journal)
    if not db.in_transaction:
        raise ContextRefusal("TRANSACTION_REQUIRED")
    if capability_plan is not None and (
            type(capability_plan) is not SelectionPlan
            or capability_plan.context != current.context):
        raise ContextRefusal("CAPABILITY_CONTEXT_MISMATCH")
    ctx = current.context
    try:
        row = db.execute(
            "SELECT state, revision FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND session_id=?",
            (ctx.principal_key, ctx.tree_key, current.session_id),
        ).fetchone()
        if row is None:
            raise ContextRefusal("SESSION_SCOPE_MISMATCH")
        if row[0] != "OPEN":
            raise ContextRefusal("SESSION_NOT_OPEN")
        if row[1] != current.expected_revision:
            raise ContextRefusal("STALE_REVISION")
        rows = db.execute(
            "SELECT turn_id,ordinal,role,body,provider_key,model_key,recorded_at_ms "
            "FROM forest_turns WHERE session_id=? ORDER BY ordinal DESC LIMIT ?",
            (current.session_id, MAX_HISTORY),
        ).fetchall()
        return select_history(current, tuple(HistoryTurn(*r) for r in rows),
                              capability_plan=capability_plan)
    except sqlite3.Error as exc:
        raise ContextRefusal("STORAGE_REFUSED") from exc


@dataclass(frozen=True, slots=True)
class WorkshopContextRef:
    """M5 host-owned fixture selection reference, not an activation grant.

    Bind workshop selection to the exact session/user turn as well as the
    task-scoped profile. No sticky inheritance until host custody is defined.
    """
    session: SessionContextRef
    profile: TreeProfile
    workshop: str
    general: tuple[str, ...] = ()
    ready: tuple[str, ...] = ()

    def __post_init__(self):
        if (type(self.session) is not SessionContextRef
                or type(self.profile) is not TreeProfile
                or self.profile.scope != self.session.context):
            raise ContextRefusal("WORKSHOP_CONTEXT_MISMATCH")
        try:
            plan_selection(self.profile, self.session.context, self.workshop,
                           general=self.general, ready=self.ready)
        except CapabilityRefusal as exc:
            raise ContextRefusal("WORKSHOP_SELECTION_REFUSED") from exc


def snapshot_with_workshop_in_transaction(journal, requested, *, current):
    """Compose B6 selection and M2 snapshot in the existing transaction.

    Compare independent host fixture references including exact profile and
    selection. Recompute the plan from current policy, never accept a
    supplied SelectionPlan or carry prior sticky selections. Reference
    equality does not establish host authority or independent currentness.
    Metadata stays internal; transport messages remain role/content only.
    """
    if (type(requested) is not WorkshopContextRef
            or type(current) is not WorkshopContextRef
            or requested != current):
        raise ContextRefusal("WORKSHOP_REFERENCE_CHANGED")
    try:
        plan = plan_selection(current.profile, current.session.context,
                              current.workshop, general=current.general,
                              ready=current.ready)
    except CapabilityRefusal as exc:
        raise ContextRefusal("WORKSHOP_SELECTION_REFUSED") from exc
    return snapshot_in_transaction(journal, requested.session,
                                   current=current.session, capability_plan=plan)


def list_open_metadata_fixture(journal, context, *, limit=MAX_PAGE):
    """Internal title-free fixture metadata, never a display or C5 response.

    Scope owner AND Tree AND OPEN before LIMIT; no title or body read.
    The host must independently establish fixture provenance. Do not export
    even IDs/counts through this method to an unapproved recipient.
    """
    if type(context) is not TaskContext:
        raise ContextRefusal("INVALID_CONTEXT")
    if context.clone_key is not None:
        raise ContextRefusal("CLONE_BINDING_UNAVAILABLE")
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE:
        raise ContextRefusal("INVALID_LIMIT")
    db = _journal(journal)
    try:
        rows = db.execute(
            "SELECT session_id,revision,updated_at_ms FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND state='OPEN' "
            "ORDER BY updated_at_ms DESC,session_id LIMIT ?",
            (context.principal_key, context.tree_key, limit),
        ).fetchall()
    except sqlite3.Error as exc:
        raise ContextRefusal("STORAGE_REFUSED") from exc
    return tuple(tuple(row) for row in rows)
