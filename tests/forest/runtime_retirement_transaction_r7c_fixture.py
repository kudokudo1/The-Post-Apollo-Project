"""R7c-b: owner-exclusive fixed-public disposable SQLite witness, TEST ONLY.

No live opener, migration, provider, permission, global dispatch fence,
physical release, restoration or installed entry point. The test owner
supplies its existing disposable B1/B3 connection. Do not use on user data.
"""
from dataclasses import asdict
import json
import sqlite3

from session_journal_v0 import ForestSessionJournal, _write
from runtime_retirement_eligibility_r7b import (
    RetirementRef, FixtureObservation, _scope, _int, _result, _REQUIRED,
    MAX_REVISION, MAX_AGE_NS, MAX_NS, _KEY,
)
from recovery_inspect_b4d import ForestLocalRecoveryInspector

FIXTURE = "R7C_FIXED_PUBLIC_CHERRY"
TABLE = "forest_retirement_r7c_fixture"

# One record/slot for the entire approved fixture. Slot ownership is derived
# from state, not a second mutable flag. Scope is immutable exact public
# metadata, not a grant. No production schema/version change.
DDL = """
CREATE TABLE forest_retirement_r7c_fixture (
    slot INTEGER PRIMARY KEY CHECK(slot=1),
    task_key TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL UNIQUE REFERENCES forest_sessions(session_id),
    scope TEXT NOT NULL,
    state TEXT NOT NULL,
    lifecycle_revision INTEGER NOT NULL,
    effect_id TEXT UNIQUE,
    outcome TEXT,
    CHECK ((state='ACTIVE' AND lifecycle_revision=1
            AND effect_id IS NULL AND outcome IS NULL)
        OR (state='PENDING' AND lifecycle_revision=2
            AND effect_id IS NOT NULL AND outcome IS NULL)
        OR (state='WINTER' AND lifecycle_revision=3
            AND effect_id IS NOT NULL AND outcome IS NOT NULL
            AND outcome='FIXTURE_RETIRED'))
)
"""


class FixtureRefusal(ValueError):
    pass


def _report(status="UNKNOWN_HOLD"):
    result = _result()
    result["status"] = status
    return result


def _require(condition):
    if not condition:
        raise FixtureRefusal("FIXTURE_HOLD")


def _exact(original, current):
    _require(_scope(original) and _scope(current) and original == current)
    c = original.attempt.context
    _require((c.principal_key, c.tree_key, c.task_id, c.execution_context_id,
              c.generation, c.origin) ==
             ("fixture-owner", "cherry", "fixture-task", "fixture-execution",
              3, "INTERACTIVE"))
    # Persist every exact reference field, not merely model label/operation
    # ID or a digest interpreted as authentication. No decode into authority.
    return json.dumps(asdict(original), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _db(journal, fixture, *, read_only):
    _require(type(fixture) is str and fixture == FIXTURE
             and type(journal) is ForestSessionJournal)
    db = journal.db
    _require(type(db) is sqlite3.Connection)
    _require(db.execute("PRAGMA query_only").fetchone() == (int(read_only),))
    _require(db.execute("PRAGMA foreign_keys").fetchone() == (1,))
    _require(db.execute("PRAGMA user_version").fetchone() == (1,))
    entries = db.execute("PRAGMA database_list").fetchall()
    _require(len(entries) == 1 and entries[0][1] == "main")
    return db


def _continuity(journal, scope):
    """Metadata predicate in the owner's existing transaction.

    R7b's public read-only entry point is NOT called or weakened here.
    Recheck its exact local predicate under this write transaction, using
    B4d for local lineage. This intentionally does not mutate B1/B3.
    """
    db = journal.db
    _require(db.in_transaction)
    ref, a = scope.operation.context_ref, scope.attempt
    owner, tree, session = ref.context.principal_key, ref.context.tree_key, ref.session_id
    _require(db.execute(
        "SELECT owner_key,tree_key,state,revision FROM forest_sessions WHERE session_id=?",
        (session,)).fetchone() == (owner, tree, "OPEN", scope.session_revision))
    row = db.execute(
        "SELECT owner_key,user_turn_id,expected_revision,model_key,status,reply_turn_id "
        "FROM forest_attempts_b3 WHERE session_id=? AND attempt_id=?",
        (session, a.attempt_id)).fetchone()
    _require(row is not None and row[:5] == (owner, ref.user_turn_id,
             ref.expected_revision, a.binding.identity.model_name, "COMMITTED")
             and type(row[5]) is str)
    _require(db.execute(
        "SELECT 1 FROM forest_attempts_b3 WHERE session_id=? AND "
        "(status='RESERVED' OR expected_revision>=?) AND attempt_id<>? LIMIT 1",
        (session, ref.expected_revision, a.attempt_id)).fetchone() is None)
    _require(db.execute(
        "SELECT turn_id,role FROM forest_turns WHERE session_id=? "
        "ORDER BY ordinal DESC LIMIT 2", (session,)).fetchall()
        == [(row[5], "assistant"), (ref.user_turn_id, "user")])
    evidence = ForestLocalRecoveryInspector(journal).inspect(
        owner=owner, session_id=session, attempt_id=a.attempt_id)
    _require(evidence["forestWriteState"] == "FOREST_COMMITTED"
             and evidence["c5Settlement"] == "UNKNOWN_HOLD")


def _observations(scope, observations, clock_domain, now_ns,
                  retained_residency_accounted):
    # The owner supplies explicit synthetic retained-residency accounting
    # alongside the exact ACCOUNTING observation; no bytes are credited.
    _require(type(retained_residency_accounted) is bool
             and retained_residency_accounted
             and type(clock_domain) is str and _KEY.fullmatch(clock_domain)
             and _int(now_ns, 1, MAX_NS)
             and type(observations) is tuple and len(observations) == len(_REQUIRED))
    previous = 0
    for obs, (kind, state) in zip(observations, _REQUIRED):
        _require(type(obs) is FixtureObservation and type(obs.kind) is str
                 and obs.kind == kind and type(obs.state) is str and obs.state == state
                 and _scope(obs.scope) and obs.scope == scope
                 and type(obs.clock_domain) is str and obs.clock_domain == clock_domain
                 and _int(obs.generation, 1, MAX_REVISION)
                 and obs.generation == scope.attempt.context.generation
                 and _int(obs.observed_ns, 1, now_ns)
                 and obs.observed_ns > previous
                 and now_ns - obs.observed_ns <= MAX_AGE_NS)
        previous = obs.observed_ns


def _effect(value):
    _require(type(value) is str and _KEY.fullmatch(value))
    return value


def _row(db, scope, encoded):
    row = db.execute(
        "SELECT task_key,session_id,scope,state,lifecycle_revision,effect_id,outcome "
        "FROM forest_retirement_r7c_fixture WHERE slot=1").fetchone()
    _require(row is not None and row[:3] == (
        scope.attempt.context.task_id, scope.operation.context_ref.session_id, encoded))
    return row[3:]


def bootstrap_fixture(journal, *, fixture, original, current):
    """Explicit setup on already-created, owner-exclusive disposable B1/B3."""
    try:
        encoded = _exact(original, current)
        db = _db(journal, fixture, read_only=False)
        with _write(db):
            _continuity(journal, original)
            _require(db.execute("SELECT COUNT(*) FROM forest_sessions").fetchone() == (1,))
            _require(db.execute("SELECT COUNT(*) FROM forest_attempts_b3").fetchone() == (1,))
            _require(db.execute(
                "SELECT 1 FROM sqlite_master WHERE name=?",
                (TABLE,)).fetchone() is None)
            db.execute(DDL)
            db.execute("INSERT INTO forest_retirement_r7c_fixture "
                       "(slot,task_key,session_id,scope,state,lifecycle_revision) "
                       "VALUES (1,?,?,?,'ACTIVE',1)",
                       (original.attempt.context.task_id,
                        original.operation.context_ref.session_id, encoded))
        return _report("FIXTURE_ACTIVE")
    except Exception:
        return _report()


def begin_pending(journal, *, fixture, original, current, effect_id, expected_revision):
    """Owner's separate BEGIN IMMEDIATE; one CAS, no automatic retry."""
    try:
        encoded = _exact(original, current)
        effect = _effect(effect_id)
        _require(type(expected_revision) is int and expected_revision == 1)
        db = _db(journal, fixture, read_only=False)
        with _write(db):
            _require(_row(db, original, encoded) == ("ACTIVE", 1, None, None))
            _continuity(journal, original)
            changed = db.execute(
                "UPDATE forest_retirement_r7c_fixture SET state='PENDING',"
                "lifecycle_revision=2,effect_id=? WHERE slot=1 AND scope=? "
                "AND state='ACTIVE' AND lifecycle_revision=1 AND effect_id IS NULL "
                "AND outcome IS NULL", (effect, encoded)).rowcount
            _require(changed == 1)
        return _report("FIXTURE_PENDING")
    except Exception:
        return _report()


def finish_winter(journal, *, fixture, original, current, effect_id,
                  expected_revision, observations, clock_domain, now_ns,
                  retained_residency_accounted):
    """Atomic synthetic WINTER/outcome; no actual freeze or release."""
    try:
        encoded = _exact(original, current)
        effect = _effect(effect_id)
        _require(type(expected_revision) is int and expected_revision == 2)
        _observations(original, observations, clock_domain, now_ns,
                      retained_residency_accounted)
        db = _db(journal, fixture, read_only=False)
        with _write(db):
            _observations(original, observations, clock_domain, now_ns,
                          retained_residency_accounted)
            _require(_row(db, original, encoded) == ("PENDING", 2, effect, None))
            _continuity(journal, original)
            # Same statement records the original effect outcome and releases
            # the synthetic active-slot claim derived from lifecycle state.
            changed = db.execute(
                "UPDATE forest_retirement_r7c_fixture SET state='WINTER',"
                "lifecycle_revision=3,outcome='FIXTURE_RETIRED' "
                "WHERE slot=1 AND scope=? AND state='PENDING' "
                "AND lifecycle_revision=2 AND effect_id=? AND outcome IS NULL",
                (encoded, effect)).rowcount
            _require(changed == 1)
        return _report("FIXTURE_RETIRED")
    except Exception:
        return _report()


def recover_original(journal, *, fixture, original, current, effect_id):
    """Read-only exact original effect outcome, NOT current admission.

    The owner supplies a read snapshot on a freshly reopened disposable
    database. Do not toggle query_only, close or resolve any transaction.
    Never interpret absent or pending as permission to retry.
    """
    try:
        encoded = _exact(original, current)
        effect = _effect(effect_id)
        db = _db(journal, fixture, read_only=True)
        _require(db.in_transaction)
        state = _row(db, original, encoded)
        if state == ("WINTER", 3, effect, "FIXTURE_RETIRED"):
            return _report("FIXTURE_RETIRED")
        # Pending, absent, contradictory or wrong effect is UNKNOWN_HOLD.
        return _report()
    except Exception:
        return _report()
