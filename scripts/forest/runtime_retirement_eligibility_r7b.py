"""R7b: fixed-public disposable retirement eligibility witness ONLY.

No opener, writer, provider, task registry, freeze, retirement or authority.
The owner supplies an existing isolated journal and read transaction plus
independently retained synthetic references. Equality is not authentication.
"""
from dataclasses import dataclass
import sqlite3

from context_first_tree_m2 import SessionContextRef
from runtime_events_r3 import OperationRef
from heart_resource_custody_h2 import AttemptRef
from heart_dispatch_reference_h1 import MAX_AGE_NS, MAX_NS
from recovery_inspect_b4d import ForestLocalRecoveryInspector
from session_journal_v0 import ForestSessionJournal
from shared_context_b6r1 import TaskContext, _KEY

FIXTURE = "R7B_FIXED_PUBLIC_CHERRY"
MAX_REVISION = 2**53 - 1
_REQUIRED = (("FREEZE", "FROZEN"), ("TERMINAL", "COMMITTED"),
             ("QUIESCENCE", "QUIESCENT"), ("ACCOUNTING", "ACCOUNTED"),
             ("SETTLEMENT", "SETTLED"))


@dataclass(frozen=True, slots=True)
class RetirementRef:
    operation: OperationRef
    attempt: AttemptRef
    session_revision: int


@dataclass(frozen=True, slots=True)
class FixtureObservation:
    kind: str
    state: str
    scope: RetirementRef
    clock_domain: str
    generation: int
    observed_ns: int


def _result(eligible=False):
    return {
        "status": "FIXTURE_ELIGIBILITY_MATCHED" if eligible else "UNKNOWN_HOLD",
        "fixture_only": True,
        "actual_dispatch_frozen": False,
        "actual_retirement_permitted": False,
        "actual_retirement_written": False,
        "actual_restoration_permitted": False,
        "source_authenticated": False,
        "provider_terminal_verified": False,
        "physical_resources_released": False,
        "c5_settlement_verified": False,
        "permission_granted": False,
        "safe_to_retry": False,
        "safe_to_start_inference": False,
        "production_authority": False,
        "safe_actions": [],
    }


def _int(value, lower, upper):
    return type(value) is int and lower <= value <= upper


def _scope(ref):
    if type(ref) is not RetirementRef or type(ref.operation) is not OperationRef:
        return False
    a, o = ref.attempt, ref.operation
    if type(a) is not AttemptRef or type(o.context_ref) is not SessionContextRef:
        return False
    c = o.context_ref
    return (type(c.context) is TaskContext
            and c.context.tree_key == "cherry" and c.context.clone_key is None
            and c.context.origin == "INTERACTIVE"
            and a.context == c.context and a.turn_id == c.user_turn_id
            and a.operation_id == o.operation_id
            and _int(c.expected_revision, 1, MAX_REVISION - 1)
            and _int(ref.session_revision, 2, MAX_REVISION)
            and ref.session_revision == c.expected_revision + 1)


def inspect_fixture(journal, *, fixture, original, current, observations,
                    clock_domain, now_ns):
    """Read-only comparison, valid only for the supplied snapshot.

    Owner must independently hold original and current scope and maintain
    the fixture transaction. No lookup of a live task, no body/title access.
    Does not commit, rollback, mutate query_only, or change H2 custody.
    """
    try:
        if (type(fixture) is not str or fixture != FIXTURE
                or type(journal) is not ForestSessionJournal
                or not _scope(original) or not _scope(current)
                or current != original
                or type(clock_domain) is not str or not _KEY.fullmatch(clock_domain)
                or not _int(now_ns, 1, MAX_NS)
                or type(observations) is not tuple
                or len(observations) != len(_REQUIRED)):
            return _result()
        # Validate ALL separately held references before any database query.
        previous = 0
        for obs, (kind, state) in zip(observations, _REQUIRED):
            if (type(obs) is not FixtureObservation
                    or type(obs.kind) is not str or obs.kind != kind
                    or type(obs.state) is not str or obs.state != state
                    or not _scope(obs.scope) or obs.scope != original
                    or type(obs.clock_domain) is not str
                    or obs.clock_domain != clock_domain
                    or not _int(obs.generation, 1, MAX_REVISION)
                    or obs.generation != original.attempt.context.generation
                    or not _int(obs.observed_ns, 1, now_ns)
                    or obs.observed_ns <= previous
                    or now_ns - obs.observed_ns > MAX_AGE_NS):
                return _result()
            previous = obs.observed_ns

        db = journal.db
        if (type(db) is not sqlite3.Connection or not db.in_transaction
                or db.execute("PRAGMA query_only").fetchone() != (1,)):
            return _result()
        ref = original.operation.context_ref
        a = original.attempt
        owner, tree, session = ref.context.principal_key, ref.context.tree_key, ref.session_id
        if db.execute(
            "SELECT owner_key,tree_key,state,revision FROM forest_sessions WHERE session_id=?",
            (session,)).fetchone() != (owner, tree, "OPEN", original.session_revision):
            return _result()
        # Exact last committed attempt, with no other reserved work in session.
        row = db.execute(
            "SELECT owner_key,user_turn_id,expected_revision,model_key,status,reply_turn_id "
            "FROM forest_attempts_b3 WHERE session_id=? AND attempt_id=?",
            (session, a.attempt_id)).fetchone()
        if (row is None or row[:5] != (owner, ref.user_turn_id,
                ref.expected_revision, a.binding.identity.model_name, "COMMITTED")
                or type(row[5]) is not str):
            return _result()
        if db.execute(
            "SELECT 1 FROM forest_attempts_b3 WHERE session_id=? AND "
            "(status='RESERVED' OR expected_revision>=?) AND attempt_id<>? LIMIT 1",
            (session, ref.expected_revision, a.attempt_id)).fetchone() is not None:
            return _result()
        latest = db.execute(
            "SELECT turn_id,role FROM forest_turns WHERE session_id=? "
            "ORDER BY ordinal DESC LIMIT 2", (session,)).fetchall()
        if latest != [(row[5], "assistant"), (ref.user_turn_id, "user")]:
            return _result()
        evidence = ForestLocalRecoveryInspector(journal).inspect(
            owner=owner, session_id=session, attempt_id=a.attempt_id)
        if (evidence["forestWriteState"] != "FOREST_COMMITTED"
                or evidence["c5Settlement"] != "UNKNOWN_HOLD"
                or not db.in_transaction):
            return _result()
        # SETTLED above is a synthetic observation, never C5 verification.
        return _result(True)
    except Exception:
        # Static refusal only, no private metadata, diagnostics or retries.
        return _result()
