"""M4: public disposable history projections, never protected access.

The owner must supply an isolated synthetic B1 journal and independently
resolved original/current references. Nothing here authenticates the host,
opens a database, grants rights, sends bytes, or resumes execution.
"""
from dataclasses import dataclass
import json
import re
import sqlite3

from shared_context_b6r1 import BarkAttachment
from session_journal_v0 import KEY, MAX_PAGE, MAX_BODY, ForestSessionJournal
from context_first_tree_m2 import ContextRefusal, HistoryTurn, list_open_metadata_fixture

SESSION_SCHEMA = "postapollo.forest.public-session-display.v1"
HISTORY_SCHEMA = "postapollo.forest.public-history-display.v1"
TREE_HINTS = frozenset(("CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH"))
REQUEST = re.compile(r"[A-Za-z0-9_-]{16,96}\Z", re.ASCII)
MAX_SAFE_INT = 2**53 - 1
MAX_HISTORY_PAGE = 16
MAX_FRAME_BYTES = 65536
# No database title is read. Public fixture label only.
FIXTURE_TITLE = "Public conversation"


def _integer(value, low=0, high=MAX_SAFE_INT):
    if type(value) is not int or not low <= value <= high:
        raise ContextRefusal("INVALID_DISPLAY_INTEGER")


def _key(value):
    if type(value) is not str or KEY.fullmatch(value) is None:
        raise ContextRefusal("INVALID_DISPLAY_IDENTIFIER")


@dataclass(frozen=True, slots=True)
class PublicViewRef:
    attachment: BarkAttachment
    request_id: str

    def __post_init__(self):
        if type(self.attachment) is not BarkAttachment:
            raise ContextRefusal("INVALID_VIEW")
        if (not self.attachment.attached
                or self.attachment.context.clone_key is not None
                or self.attachment.requested_tree not in TREE_HINTS):
            raise ContextRefusal("INVALID_VIEW")
        if type(self.request_id) is not str or REQUEST.fullmatch(self.request_id) is None:
            raise ContextRefusal("INVALID_REQUEST")


@dataclass(frozen=True, slots=True)
class ListRef:
    view: PublicViewRef
    limit: int = MAX_PAGE

    def __post_init__(self):
        if type(self.view) is not PublicViewRef:
            raise ContextRefusal("INVALID_VIEW")
        _integer(self.limit, 1, MAX_PAGE)


@dataclass(frozen=True, slots=True)
class HistoryPageRef:
    view: PublicViewRef
    session_id: str
    revision: int
    after: int = 0
    limit: int = MAX_HISTORY_PAGE

    def __post_init__(self):
        if type(self.view) is not PublicViewRef:
            raise ContextRefusal("INVALID_VIEW")
        _key(self.session_id)
        _integer(self.revision)
        _integer(self.after)
        _integer(self.limit, 1, MAX_HISTORY_PAGE)


def _checked(journal, requested, current, kind):
    if type(requested) is not kind or type(current) is not kind or requested != current:
        raise ContextRefusal("VIEW_CHANGED")
    if type(journal) is not ForestSessionJournal:
        raise ContextRefusal("INVALID_JOURNAL")
    if not journal.db.in_transaction:
        raise ContextRefusal("TRANSACTION_REQUIRED")
    # Canonical Tree and visible hint are independently bound by fixture host.
    # Equality of refs is not evidence of trusted source/currentness.
    return requested.view.attachment.context


def _envelope(view, schema):
    return {"schema": schema, "requestId": view.request_id,
            "treeKey": view.attachment.requested_tree,
            "generation": view.attachment.view_generation}


def _size(frame):
    # Candidate JSON size, not actual serialized-byte release evidence.
    return len(json.dumps(frame, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def list_public_fixture_in_transaction(journal, requested, *, current):
    """Four-field UI2.1 projection with fixed, explicitly public titles.

    No title/body read. This is an internal fixture value, not a send.
    """
    context = _checked(journal, requested, current, ListRef)
    frame = _envelope(requested.view, SESSION_SCHEMA)
    rows = list_open_metadata_fixture(journal, context, limit=requested.limit)
    seen = set()
    frame["sessions"] = []
    for session_id, revision, updated_at_ms in rows:
        _key(session_id)
        _integer(revision)
        _integer(updated_at_ms, 1)
        if session_id in seen:
            raise ContextRefusal("INVALID_LIST")
        seen.add(session_id)
        frame["sessions"].append({"session_id": session_id, "title": FIXTURE_TITLE,
                                  "revision": revision, "updated_at_ms": updated_at_ms})
    if _size(frame) > MAX_FRAME_BYTES:
        raise ContextRefusal("DISPLAY_TOO_LARGE")
    return frame


def _display_turn(row):
    turn = HistoryTurn(*row)
    _integer(turn.ordinal, 1)
    # Preserve normal multiline text exactly; refuse other control characters
    # and bidi overrides instead of silently altering journal content.
    if any((ord(c) < 32 and c not in "\n\t") or 0x7f <= ord(c) <= 0x9f
           or 0x202a <= ord(c) <= 0x202e or 0x2066 <= ord(c) <= 0x2069
           for c in turn.content):
        raise ContextRefusal("INVALID_DISPLAY_TEXT")
    return {"turn_id": turn.turn_id, "ordinal": turn.ordinal,
            "role": turn.role, "text": turn.content}


def history_public_fixture_in_transaction(journal, requested, *, current):
    """One revision-bound page of durable B1 rows, including completed replies.

    No runtime attempts, provisional deltas, tool activation or replay.
    Pages start after an exact ordinal and never silently skip or slice a row.
    Caller owns a single read transaction and checks current view at delivery.
    """
    context = _checked(journal, requested, current, HistoryPageRef)
    db = journal.db
    try:
        row = db.execute(
            "SELECT state,revision FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND session_id=?",
            (context.principal_key, context.tree_key, requested.session_id),
        ).fetchone()
        if row is None:
            raise ContextRefusal("SESSION_SCOPE_MISMATCH")
        if row[0] != "OPEN":
            raise ContextRefusal("SESSION_NOT_OPEN")
        if row[1] != requested.revision:
            raise ContextRefusal("STALE_REVISION")
        last = db.execute(
            "SELECT COALESCE(MAX(ordinal),0) FROM forest_turns WHERE session_id=?",
            (requested.session_id,),
        ).fetchone()[0]
        _integer(last)
        if last > requested.revision or requested.after > last:
            raise ContextRefusal("INVALID_CURSOR")
        rows = db.execute(
            "SELECT turn_id,ordinal,role,body,provider_key,model_key,recorded_at_ms "
            "FROM forest_turns WHERE session_id=? AND ordinal>? "
            "ORDER BY ordinal LIMIT ?",
            (requested.session_id, requested.after, requested.limit + 1),
        ).fetchall()
    except sqlite3.Error as exc:
        raise ContextRefusal("STORAGE_REFUSED") from exc

    if len(rows) != min(last - requested.after, requested.limit + 1):
        raise ContextRefusal("INVALID_HISTORY_ORDER")
    if any(r[1] != requested.after + i + 1 for i, r in enumerate(rows)):
        raise ContextRefusal("INVALID_HISTORY_ORDER")
    frame = _envelope(requested.view, HISTORY_SCHEMA)
    frame.update(sessionId=requested.session_id, revision=requested.revision,
                 messages=[], complete=False)
    for row in rows[:requested.limit]:
        message = _display_turn(row)
        frame["messages"].append(message)
        # Reserve the longer boolean representation for the final value.
        if _size(frame) > MAX_FRAME_BYTES:
            frame["messages"].pop()
            if not frame["messages"]:
                raise ContextRefusal("DISPLAY_TOO_LARGE")
            break
    frame["complete"] = requested.after + len(frame["messages"]) == last
    return frame
