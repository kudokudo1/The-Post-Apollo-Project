"""R7c-b actual disposable B1/B3 transactions and reopen witness."""
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from turn_bridge_b3 import ForestTurnBridge, bootstrap_attempts_synthetic
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import SessionContextRef
from runtime_events_r3 import OperationRef
from heart_resource_custody_h2 import AttemptRef, ResourceCustody
from heart_dispatch_reference_h1 import TransportSettings, MAX_AGE_NS, DispatchSnapshot
from model_form_routing_i1 import TurnScope, ReasoningReference, RoutingInput, recommend
from resource_governor_p1 import ResourceRequest, ResourceRequirement, ResourceBudget, ResourceAvailability
from model_binding_i2 import ModelBinding, ModelIdentity, BindingRegistry, BindingEvidence, resolve_reference
from runtime_retirement_eligibility_r7b import RetirementRef, FixtureObservation
from runtime_retirement_transaction_r7c_fixture import (
    FIXTURE, TABLE, bootstrap_fixture, begin_pending, finish_winter, recover_original,
)


class RetirementTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="forest-r7c-public-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "fixture.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(lambda: self.db.close())
        bootstrap_synthetic(self.db)
        bootstrap_attempts_synthetic(self.db)
        self.journal = ForestSessionJournal(self.db)
        self.ctx = TaskContext("fixture-owner", "cherry", None, "fixture-task",
                               "fixture-execution", 3, "INTERACTIVE")
        self.session = self.journal.create_session(self.ctx.principal_key, "cherry",
                                         "Fixed public fixture", now_ms=1)["session_id"]
        user = self.journal.append_turn(self.ctx.principal_key, self.session,
                       expected_revision=0, role="user", body="Public fixture", now_ms=2)
        self.model = "fixture-model"
        self.bridge = ForestTurnBridge(self.journal, clock_ms=lambda:3, streamer=self.stream)
        events = list(self.bridge.exchange(owner=self.ctx.principal_key, session_id=self.session,
                                          expected_revision=1, model=self.model))
        ref = SessionContextRef(self.ctx, self.session, 1, user["turn_id"])
        op = OperationRef(ref, "fixture-operation")
        settings = TransportSettings(self.model, 2048, 32)
        binding = ModelBinding("fixture-binding", "small",
            ModelIdentity(self.model, "sha256:"+"a"*64, "ollama", "fixture-runtime",
                          "1.0", "sha256:"+"b"*64), settings.config_digest, 2048, 32)
        self.scope = RetirementRef(op, AttemptRef(self.ctx, user["turn_id"],
                                  op.operation_id, events[0]["attempt_id"], binding, settings), 2)
        self.observations = tuple(FixtureObservation(k, s, self.scope, "fixture-clock", 3, 10+i)
            for i,(k,s) in enumerate((("FREEZE","FROZEN"),("TERMINAL","COMMITTED"),
                ("QUIESCENCE","QUIESCENT"),("ACCOUNTING","ACCOUNTED"),
                ("SETTLEMENT","SETTLED"))))
        self.custody = ResourceCustody()
        # Hold the exact original H11 resource reference, not an unrelated
        # empty custody object. R7c must not release or mutate this fixture.
        turn_scope = TurnScope(self.ctx, user["turn_id"])
        recommendation = recommend(RoutingInput(turn_scope, "small",
            ReasoningReference(turn_scope, "normal", "explicit")))
        registry = BindingRegistry(self.ctx.principal_key, self.ctx.tree_key, 1, (binding,))
        evidence = BindingEvidence(turn_scope, binding, "fixture-producer",
                                   "fixture-observation", True, ("chat",), 2048)
        resolved = resolve_reference(recommendation, registry,
                                     required_features=("chat",), evidence=evidence)
        request = ResourceRequest(self.ctx.task_id, self.ctx.execution_context_id,
                                  "small", "normal", "interactive", "heart")
        dispatch = DispatchSnapshot(resolved, settings, op.operation_id,
            self.scope.attempt.attempt_id, "fixture-clock", 1, request,
            ResourceRequirement(request, "requirements", 512, 256, 2),
            ResourceBudget("budget", 1024, 512, 4),
            ResourceAvailability("available", 1024, 512, 4))
        self.assertEqual(self.custody.claim_reference(dispatch,
            replace(dispatch, captured_ns=2), now_ns=3), "REFERENCE_HELD")
        self.custody_before = self.custody.status()
        self.original_rows = self.snapshot()
        self.denied = []
        self.reads = []
        self.assert_status(bootstrap_fixture(self.journal, **self.args()), "FIXTURE_ACTIVE")
        self.guard()

    def stream(self, **kw):
        yield dict(event="STARTED", model=self.model, provider="ollama")
        yield dict(event="DELTA", text="Public reply")
        yield dict(event="COMPLETE", model=self.model, provider="ollama", text="Public reply")

    def snapshot(self):
        # Independent test-only witness reads fixed public rows, never called
        # inside eligibility or transition. Includes actual immutable bodies.
        return tuple(tuple(self.db.execute("SELECT * FROM "+table+" ORDER BY 1").fetchall())
                     for table in ("forest_sessions", "forest_turns", "forest_attempts_b3"))

    def guard(self):
        def authorizer(action, a, b, database, trigger):
            self.reads.append((action,a,b))
            if ((action == sqlite3.SQLITE_READ and b in ("body","title"))
                    or (action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE,
                                   sqlite3.SQLITE_DELETE) and a != TABLE)):
                self.denied.append((action,a,b))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(authorizer)

    def args(self, **changes):
        args = dict(fixture=FIXTURE, original=self.scope, current=self.scope)
        args.update(changes)
        return args

    def pending(self, **changes):
        args = self.args(effect_id="effect-one", expected_revision=1)
        args.update(changes)
        return begin_pending(self.journal, **args)

    def finish(self, **changes):
        args = self.args(effect_id="effect-one", expected_revision=2,
             observations=self.observations, clock_domain="fixture-clock",
             now_ns=20, retained_residency_accounted=True)
        args.update(changes)
        return finish_winter(self.journal, **args)

    def recover(self, **changes):
        args = self.args(effect_id="effect-one")
        args.update(changes)
        return recover_original(self.journal, **args)

    def row(self):
        return self.db.execute("SELECT state,lifecycle_revision,effect_id,outcome "
                               "FROM forest_retirement_r7c_fixture").fetchone()

    def assert_status(self, result, state):
        self.assertEqual(result["status"], state)
        self.assertIs(result["fixture_only"], True)
        self.assertEqual(result["safe_actions"], [])
        for key, value in result.items():
            if key not in ("status", "fixture_only", "safe_actions"):
                self.assertIs(value, False, key)

    def assert_pending(self):
        self.assertEqual(self.row(), ("PENDING",2,"effect-one",None))
        self.assertFalse(self.db.in_transaction)

    def unchanged(self):
        self.assertEqual(self.denied, [])
        self.assertEqual(self.custody.status(), self.custody_before)
        self.db.set_authorizer(None)
        self.assertEqual(self.snapshot(), self.original_rows)
        self.guard()

    def test_atomic_retirement_and_exact_preservation(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.assert_pending()
        self.unchanged()
        self.assert_status(self.finish(), "FIXTURE_RETIRED")
        self.assertEqual(self.row(), ("WINTER",3,"effect-one","FIXTURE_RETIRED"))
        self.assertFalse(self.db.in_transaction)
        self.unchanged()

    def test_competing_intents_and_replay_refused(self):
        self.assert_status(self.pending(effect_id="effect-two", expected_revision=True), "UNKNOWN_HOLD")
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        for effect in ("effect-one","effect-two"):
            self.assert_status(self.pending(effect_id=effect), "UNKNOWN_HOLD")
        self.assert_status(self.finish(effect_id="effect-two"), "UNKNOWN_HOLD")
        self.assert_pending()
        self.assert_status(self.finish(), "FIXTURE_RETIRED")
        for effect in ("effect-one","effect-two"):
            self.assert_status(self.finish(effect_id=effect), "UNKNOWN_HOLD")
            self.assert_status(self.pending(effect_id=effect), "UNKNOWN_HOLD")
        self.unchanged()

    def test_single_slot_and_duplicate_bootstrap(self):
        self.assert_status(bootstrap_fixture(self.journal, **self.args()), "UNKNOWN_HOLD")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO forest_retirement_r7c_fixture "
                "SELECT 2,task_key,session_id,scope,state,lifecycle_revision,effect_id,outcome "
                "FROM forest_retirement_r7c_fixture")
        self.db.rollback()
        self.assertEqual(self.row(), ("ACTIVE",1,None,None))
        self.unchanged()

    def test_pending_and_final_rollback_on_writer_failure(self):
        # Trigger injects failure after the candidate UPDATE. SQLite rollback
        # must restore the entire original state, including outcome and slot.
        self.db.set_authorizer(None)
        self.db.execute("CREATE TRIGGER fixture_failure AFTER UPDATE ON "
                        "forest_retirement_r7c_fixture BEGIN SELECT RAISE(ABORT,'fixture'); END")
        self.guard()
        self.assert_status(self.pending(), "UNKNOWN_HOLD")
        self.assertEqual(self.row(), ("ACTIVE",1,None,None))
        self.db.set_authorizer(None)
        self.db.execute("DROP TRIGGER fixture_failure")
        self.guard()
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.db.set_authorizer(None)
        self.db.execute("CREATE TRIGGER fixture_failure AFTER UPDATE ON "
                        "forest_retirement_r7c_fixture BEGIN SELECT RAISE(ABORT,'fixture'); END")
        self.guard()
        self.assert_status(self.finish(), "UNKNOWN_HOLD")
        self.assert_pending()
        self.unchanged()

    def reopen_read_only(self):
        self.db.close()
        self.db = sqlite3.connect(self.path.as_uri()+"?mode=ro", uri=True)
        self.journal = ForestSessionJournal(self.db)
        self.db.execute("PRAGMA query_only=ON")
        self.db.execute("BEGIN")
        self.guard()

    def test_lost_ack_reopen_exact_effect_no_retry(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.finish()  # Deliberately discard terminal response.
        self.reopen_read_only()
        self.assert_status(self.recover(), "FIXTURE_RETIRED")
        self.assert_status(self.recover(effect_id="effect-two"), "UNKNOWN_HOLD")
        self.assert_status(self.pending(), "UNKNOWN_HOLD")
        self.assert_status(self.finish(), "UNKNOWN_HOLD")
        self.assertTrue(self.db.in_transaction)
        self.unchanged()

    def test_pending_reopen_unknown_not_retry(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.reopen_read_only()
        self.assert_status(self.recover(), "UNKNOWN_HOLD")
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(self.row(), ("PENDING",2,"effect-one",None))
        self.unchanged()

    def test_alternate_exact_scope_and_coherent_settings_hold(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        a = self.scope.attempt
        settings = replace(a.settings, num_ctx=4096)
        binding = replace(a.binding, config_digest=settings.config_digest, context_tokens=4096)
        alternate = replace(self.scope, attempt=replace(a, settings=settings, binding=binding))
        for other in (alternate, replace(self.scope, attempt=replace(a, attempt_id="different"))):
            self.assert_status(self.finish(current=other), "UNKNOWN_HOLD")
            obs = tuple(replace(o,scope=other) for o in self.observations)
            self.assert_status(self.finish(original=other,current=other,observations=obs), "UNKNOWN_HOLD")
            values = list(self.observations)
            values[3] = replace(values[3], scope=other)
            self.assert_status(self.finish(observations=tuple(values)), "UNKNOWN_HOLD")
        self.assert_pending()
        self.unchanged()

    def test_unknown_or_stale_observations_preserve_pending(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        for i,state in enumerate(("UNKNOWN","STOP","ACTIVE","RETAINED_UNACCOUNTED","UNKNOWN_HOLD")):
            values = list(self.observations)
            values[i] = replace(values[i], state=state)
            self.assert_status(self.finish(observations=tuple(values)), "UNKNOWN_HOLD")
        for kwargs in (dict(observations=self.observations[:3]+self.observations[4:]),
                       dict(now_ns=MAX_AGE_NS+20),dict(clock_domain="different"),
                       dict(retained_residency_accounted=False),
                       dict(retained_residency_accounted=1)):
            self.assert_status(self.finish(**kwargs), "UNKNOWN_HOLD")
        self.assert_pending()
        self.unchanged()

    def test_owner_transaction_is_not_nested_or_reversed(self):
        self.db.execute("BEGIN IMMEDIATE")
        self.assert_status(self.pending(), "UNKNOWN_HOLD")
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.db.execute("PRAGMA query_only=ON")
        self.assert_status(self.pending(), "UNKNOWN_HOLD")
        self.assertEqual(self.db.execute("PRAGMA query_only").fetchone(),(1,))
        self.assertEqual(self.row(), ("ACTIVE",1,None,None))
        self.unchanged()

    def test_direct_legacy_append_and_reserve_bypass_is_blocker(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.db.set_authorizer(None)
        # Deliberately exercise unrestricted existing paths outside retirement.
        # This is a negative integration witness, not an authorized global fence.
        row = self.journal.append_turn(self.ctx.principal_key, self.session,
                    expected_revision=2, role="user", body="Fixed bypass witness", now_ms=4)
        self.assertEqual(row["revision"], 3)
        bridge = ForestTurnBridge(self.journal, clock_ms=lambda:5, streamer=self.stream)
        attempt, _ = bridge._reserve(self.ctx.principal_key,self.session,3,self.model)
        self.assertTrue(attempt)
        before = self.snapshot()
        self.guard()
        self.assert_status(self.finish(), "UNKNOWN_HOLD")
        self.assert_pending()
        self.assertEqual(self.denied, [])
        self.db.set_authorizer(None)
        self.assertEqual(self.snapshot(), before)

    def test_direct_legacy_state_change_bypasses_fixture(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.db.set_authorizer(None)
        row = self.journal.set_state(self.ctx.principal_key,self.session,
                                     expected_revision=2,next_state="PAUSED",now_ms=4)
        self.assertEqual(row["state"], "PAUSED")
        before = self.snapshot()
        self.guard()
        self.assert_status(self.finish(), "UNKNOWN_HOLD")
        self.assert_pending()
        self.assertEqual(self.denied, [])
        self.db.set_authorizer(None)
        self.assertEqual(self.snapshot(), before)


    # R7d-b: negative coverage of actual unrestricted direct writers.
    # Each unittest has a fresh R7c DB and an independently held H11/H2.
    def r7d_open_pending(self):
        self.assert_status(self.pending(), "FIXTURE_PENDING")
        self.assert_pending()
        self.db.set_authorizer(None)
        self.r7d_original = self.db.execute(
            "SELECT * FROM forest_retirement_r7c_fixture").fetchall()
        self.assertEqual(self.custody.status()["status"], "REFERENCE_HELD")

    def r7d_check_hold(self):
        self.db.set_authorizer(None)
        self.assertEqual(self.db.execute(
            "SELECT * FROM forest_retirement_r7c_fixture").fetchall(),
            self.r7d_original)
        self.assertEqual(self.custody.status(), self.custody_before)
        before = self.snapshot()
        self.guard()
        self.assert_status(self.finish(), "UNKNOWN_HOLD")
        self.assert_pending()
        self.assertEqual(self.denied, [])
        self.db.set_authorizer(None)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.db.execute(
            "SELECT * FROM forest_retirement_r7c_fixture").fetchall(),
            self.r7d_original)
        self.assertEqual(self.custody.status(), self.custody_before)

    def test_r7d_create_unmapped_open_is_not_activation(self):
        self.r7d_open_pending()
        new = self.journal.create_session(self.ctx.principal_key, "cherry",
                     "Fixed public unmapped session", now_ms=4)
        self.assertNotEqual(new["session_id"], self.session)
        self.assertEqual(new["state"], "OPEN")
        self.assertEqual(new["revision"], 0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forest_retirement_r7c_fixture WHERE session_id=?",
            (new["session_id"],)).fetchone(), (0,))
        self.assertEqual(self.db.execute(
            "SELECT * FROM forest_retirement_r7c_fixture").fetchall(),
            self.r7d_original)
        self.assert_pending()
        self.assertEqual(self.custody.status(), self.custody_before)
        # Unrelated session creation did not change original lineage.
        # Do not claim it activates a task, or that the fixture fences it.
        self.guard()
        self.assert_status(self.finish(), "FIXTURE_RETIRED")
        self.assertEqual(self.denied, [])
        self.assertEqual(self.custody.status(), self.custody_before)

    def r7d_append(self, role):
        kw = {"provider": "ollama", "model": self.model} if role == "assistant" else {}
        row = self.journal.append_turn(self.ctx.principal_key, self.session,
                 expected_revision=2, role=role, body="Fixed public bypass",
                 now_ms=4, **kw)
        self.assertEqual(row["revision"], 3)
        self.assertEqual(self.db.execute(
            "SELECT turn_id,role,ordinal FROM forest_turns WHERE session_id=? "
            "ORDER BY ordinal DESC LIMIT 1", (self.session,)).fetchone(),
            (row["turn_id"], role, 3))
        return row

    def test_r7d_direct_user_append_bypasses_pending(self):
        self.r7d_open_pending()
        self.r7d_append("user")
        self.r7d_check_hold()

    def test_r7d_direct_assistant_append_bypasses_pending(self):
        self.r7d_open_pending()
        self.r7d_append("assistant")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forest_attempts_b3").fetchone(), (1,))
        self.r7d_check_hold()

    def test_r7d_direct_pause_bypasses_pending(self):
        self.r7d_open_pending()
        row = self.journal.set_state(self.ctx.principal_key, self.session,
                    expected_revision=2, next_state="PAUSED", now_ms=4)
        self.assertEqual((row["state"], row["revision"]), ("PAUSED", 3))
        self.r7d_check_hold()

    def test_r7d_direct_resume_bypasses_pending(self):
        self.r7d_open_pending()
        paused = self.journal.set_state(self.ctx.principal_key, self.session,
                    expected_revision=2, next_state="PAUSED", now_ms=4)
        self.assertEqual((paused["state"], paused["revision"]), ("PAUSED", 3))
        resumed = self.journal.set_state(self.ctx.principal_key, self.session,
                    expected_revision=3, next_state="OPEN", now_ms=5)
        self.assertEqual((resumed["state"], resumed["revision"]), ("OPEN", 4))
        self.r7d_check_hold()

    def r7d_reserve(self, *, scoped):
        self.r7d_open_pending()
        user = self.r7d_append("user")
        ref = SessionContextRef(self.ctx, self.session, 3, user["turn_id"])
        events = []
        def audit(action, table, column, database, trigger):
            # Record only SQL operation/column labels, never content or SQL
            # expanded parameters. Authorizer observes statement preparation,
            # while the returned reservation row proves the durable write.
            if action == sqlite3.SQLITE_READ and column in ("title", "body"):
                events.append((column, self.db.in_transaction))
            elif action == sqlite3.SQLITE_INSERT and table == "forest_attempts_b3":
                events.append(("reserve_insert", self.db.in_transaction))
            return sqlite3.SQLITE_OK
        def forbidden_stream(**kw):
            self.fail("reservation must not invoke transport")
        bridge = ForestTurnBridge(self.journal, clock_ms=lambda:5,
                                  streamer=forbidden_stream)
        self.db.set_authorizer(audit)
        kw = {"context_ref": ref, "current_context_ref": ref} if scoped else {}
        attempt, messages = bridge._reserve(self.ctx.principal_key, self.session,
                                            3, self.model, **kw)
        self.db.set_authorizer(None)
        self.assertIn(("body", True), events)
        self.assertIn(("reserve_insert", True), events)
        index = events.index(("reserve_insert", True))
        self.assertLess(events.index(("body", True)), index)
        if scoped:
            self.assertNotIn(("title", True), events)
        else:
            self.assertLess(events.index(("title", True)), index)
        self.assertEqual(messages[-1]["role"], "user")
        self.assertNotEqual(attempt, self.scope.attempt.attempt_id)
        self.assertEqual(self.db.execute(
            "SELECT user_turn_id,expected_revision,status,reply_turn_id FROM "
            "forest_attempts_b3 WHERE attempt_id=?", (attempt,)).fetchone(),
            (user["turn_id"], 3, "RESERVED", None))
        self.assertEqual(self.db.execute(
            "SELECT revision FROM forest_sessions WHERE session_id=?",
            (self.session,)).fetchone(), (3,))
        self.r7d_check_hold()

    def test_r7d_legacy_reserve_reads_before_insert(self):
        self.r7d_reserve(scoped=False)

    def test_r7d_exact_m2_reserve_reads_before_insert(self):
        self.r7d_reserve(scoped=True)

    def test_r7d_reserved_precedes_transport_and_close_locally_aborts(self):
        self.r7d_open_pending()
        user = self.r7d_append("user")
        calls = []
        def fake_stream(**kw):
            # Ordinary function (not a generator) detects invocation itself.
            calls.append("called")
            return iter(())
        bridge = ForestTurnBridge(self.journal, clock_ms=lambda:5,
                                  streamer=fake_stream)
        stream = bridge.exchange(owner=self.ctx.principal_key,
            session_id=self.session, expected_revision=3, model=self.model)
        try:
            first = next(stream)
            self.assertEqual(first["event"], "RESERVED")
            self.assertEqual(calls, [])
            attempt = first["attempt_id"]
            self.assertNotEqual(attempt, self.scope.attempt.attempt_id)
            self.assertEqual(self.db.execute(
                "SELECT user_turn_id,status,reply_turn_id FROM forest_attempts_b3 "
                "WHERE attempt_id=?", (attempt,)).fetchone(),
                (user["turn_id"], "RESERVED", None))
            self.assertEqual(self.custody.status(), self.custody_before)
        finally:
            stream.close()
        self.assertEqual(calls, [])
        self.assertEqual(self.db.execute(
            "SELECT status,reply_turn_id FROM forest_attempts_b3 WHERE attempt_id=?",
            (attempt,)).fetchone(), ("ABORTED", None))
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?",
            (self.scope.attempt.attempt_id,)).fetchone(), ("COMMITTED",))
        self.r7d_check_hold()


class AdmittedOriginalSettlementTests(unittest.TestCase):
    """R7d-e: fixed-public local settlement, NOT an installed writer guard."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Original:
        operation: OperationRef
        attempt: AttemptRef
        lifetime: str
        lifecycle_revision: int
        pre_revision: int
        post_revision: int
        effect: str

    @dataclass(frozen=True)
    class Admission:
        original: object
        observed: int

    @dataclass(frozen=True)
    class Freeze:
        original: object
        intent: str
        lifecycle_revision: int
        observed: int

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="forest-r7de-public-")
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "settlement.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        bootstrap_synthetic(self.db)
        bootstrap_attempts_synthetic(self.db)
        self.journal = ForestSessionJournal(self.db)
        self.ctx = TaskContext("settlement-owner", "cherry", None,
                               "settlement-task", "settlement-execution", 3,
                               "INTERACTIVE")
        self.sid = self.journal.create_session(
            self.ctx.principal_key, self.ctx.tree_key,
            "Fixed public settlement", now_ms=1)["session_id"]
        self.user = self.journal.append_turn(
            self.ctx.principal_key, self.sid, expected_revision=0,
            role="user", body="Public fixture", now_ms=2)["turn_id"]
        self.ref = SessionContextRef(self.ctx, self.sid, 1, self.user)
        self.op = OperationRef(self.ref, "settlement-operation")
        self.settings = TransportSettings("fixture-model", 2048, 32)
        self.binding = ModelBinding("settlement-binding", "small",
            ModelIdentity(self.settings.model, "sha256:"+"a"*64, "ollama",
                          "fixture-runtime", "1.0", "sha256:"+"b"*64),
            self.settings.config_digest, 2048, 32)
        self.calls = []
        self.custody = ResourceCustody()
        self.bridge = ForestTurnBridge(self.journal, clock_ms=lambda:3,
                                       streamer=self.fake_stream)
        self.assertEqual(self.custody.status()["status"], "IDLE")

    def fake_stream(self, **kw):
        # Ordinary function records invocation, not merely generator creation.
        self.calls.append("fake-stream")
        self.assertEqual((kw["model"], kw["num_ctx"], kw["max_predict"]),
                         (self.settings.model, 2048, 32))
        return iter((
            dict(event="STARTED", model=self.settings.model, provider="ollama"),
            dict(event="DELTA", text="Public reply"),
            dict(event="COMPLETE", model=self.settings.model,
                 provider="ollama", text="Public reply"),
        ))

    def exchange(self, **kw):
        generator = self.bridge.exchange(
            owner=self.ctx.principal_key, session_id=self.sid,
            expected_revision=1, model=self.settings.model,
            num_ctx=self.settings.num_ctx, max_predict=self.settings.max_predict,
            context_ref=self.ref, current_context_ref=self.ref,
            resolve_current_context=lambda:self.ref, **kw)
        self.addCleanup(generator.close)
        return generator

    def reserve_and_hold(self, generator):
        first = next(generator)
        self.assertEqual(first["event"], "RESERVED")
        self.assertEqual(self.calls, [])
        attempt = AttemptRef(self.ctx, self.user, self.op.operation_id,
                             first["attempt_id"], self.binding, self.settings)
        self.original = self.Original(self.op, attempt, "original-lifetime",
                                      1, 1, 2, "original-modeled-effect")
        turn = TurnScope(self.ctx, self.user)
        recommendation = recommend(RoutingInput(turn, "small",
            ReasoningReference(turn, "normal", "explicit")))
        registry = BindingRegistry(self.ctx.principal_key, self.ctx.tree_key,
                                   1, (self.binding,))
        evidence = BindingEvidence(turn, self.binding, "fixture-producer",
                                   "fixture-observation", True, ("chat",), 2048)
        resolved = resolve_reference(recommendation, registry,
                                    required_features=("chat",), evidence=evidence)
        request = ResourceRequest(self.ctx.task_id, self.ctx.execution_context_id,
                                  "small", "normal", "interactive", "heart")
        dispatch = DispatchSnapshot(resolved, self.settings, self.op.operation_id,
            attempt.attempt_id, "fixture-clock", 1, request,
            ResourceRequirement(request, "requirements", 512, 256, 2),
            ResourceBudget("budget", 1024, 512, 4),
            ResourceAvailability("available", 1024, 512, 4))
        self.assertEqual(self.custody.claim_reference(
            dispatch, replace(dispatch, captured_ns=2), now_ns=3),
            "REFERENCE_HELD")
        self.held = self.custody.status()
        self.assert_held()
        self.assert_local("RESERVED", 1)

    def assert_held(self):
        # Inspect the exact local fixture claim, not authenticated custody.
        self.assertEqual(self.custody._active, self.original.attempt)
        self.assertEqual(self.custody.status(), self.held)
        self.assertEqual(self.held["status"], "REFERENCE_HELD")
        self.assertTrue(self.held["fixture_slot_occupied"])
        for key in ("physical_resources_reserved", "physical_resources_released",
                    "source_authenticated", "terminal_verified", "durable_recovery",
                    "safe_to_start_inference", "permission_granted",
                    "production_authority"):
            self.assertIs(self.held[key], False)
        self.assertEqual(self.held["safe_actions"], [])

    def rows(self):
        return (
            self.db.execute("SELECT state,revision FROM forest_sessions "
                            "WHERE session_id=?", (self.sid,)).fetchone(),
            self.db.execute("SELECT turn_id,role FROM forest_turns WHERE "
                            "session_id=? ORDER BY ordinal", (self.sid,)).fetchall(),
            self.db.execute("SELECT attempt_id,user_turn_id,expected_revision,"
                            "model_key,status,reply_turn_id FROM forest_attempts_b3 "
                            "WHERE session_id=?", (self.sid,)).fetchall(),
        )

    def assert_local(self, state, revision):
        session, turns, attempts = self.rows()
        self.assertEqual(session, ("OPEN", revision))
        self.assertEqual(len(attempts), 1)
        a = self.original.attempt
        self.assertEqual(attempts[0][:5],
                         (a.attempt_id, self.user, 1, a.binding.identity.model_name, state))
        self.assertEqual(turns[0], (self.user, "user"))
        if state == "COMMITTED":
            self.assertEqual(len(turns), 2)
            self.assertEqual(turns[1], (attempts[0][5], "assistant"))
            self.assertEqual(revision, self.original.post_revision)
        else:
            self.assertEqual(len(turns), 1)
            self.assertIsNone(attempts[0][5])
            self.assertEqual(revision, self.original.pre_revision)
        self.assertFalse(self.db.in_transaction)
        self.assert_held()

    def freeze(self, observed=20):
        return self.Freeze(self.original, "original-retirement-intent", 2, observed)

    def modeled_decision(self, admission, intent, current, current_intent):
        # Pure test-local comparison, NOT a production gate or writer wrapper.
        # Independent fixture observations are supplied explicitly; no B3
        # RESERVED/STARTED/DELTA state is used as admission evidence.
        o = self.original
        if (type(admission) is not self.Admission
                or type(intent) is not self.Freeze
                or type(current) is not self.Original
                or type(current_intent) is not self.Freeze
                or admission.original != o or current != o
                or intent.original != o or current_intent != intent
                or intent.intent != "original-retirement-intent"
                or type(intent.lifecycle_revision) is not int
                or intent.lifecycle_revision != o.lifecycle_revision+1
                or type(admission.observed) is not int
                or type(intent.observed) is not int
                or not 0 < admission.observed < intent.observed
                or self.custody._active != o.attempt
                or self.custody.status() != self.held):
            return "MODELED_HOLD"
        return "MODELED_ORIGINAL_ONLY"

    def admit_then_freeze(self, generator):
        self.reserve_and_hold(generator)
        # Independent fixture input, deliberately NOT inferred from stream.
        admission = self.Admission(self.original, 10)
        self.assertEqual(next(generator)["event"], "STARTED")
        self.assertEqual(next(generator)["event"], "DELTA")
        intent = self.freeze()
        self.assertEqual(self.modeled_decision(
            admission, intent, self.original, intent), "MODELED_ORIGINAL_ONLY")
        self.assert_local("RESERVED", 1)
        return admission, intent

    def recover(self, state):
        from recovery_inspect_b4d import ForestLocalRecoveryInspector
        before = self.rows()
        with sqlite3.connect(self.path.as_uri()+"?mode=ro", uri=True) as reader:
            try:
                reader.execute("PRAGMA query_only=ON")
                inspector = ForestLocalRecoveryInspector(ForestSessionJournal(reader))
                result = inspector.inspect(owner=self.ctx.principal_key,
                    session_id=self.sid, attempt_id=self.original.attempt.attempt_id)
                self.assertEqual(result["attemptId"], self.original.attempt.attempt_id)
                self.assertEqual(result["forestWriteState"], "FOREST_"+state)
                self.assertEqual(result["c5Settlement"], "UNKNOWN_HOLD")
                for key in ("c5EvidenceAuthenticated", "terminalReceiptAuthenticated",
                            "safeToRetryInference", "safeToReleaseRevocation",
                            "productionAuthority"):
                    self.assertIs(result[key], False)
            finally:
                reader.close()
        self.assertEqual(self.rows(), before)
        self.assert_held()

    def test_r7de_freeze_before_reserve_does_not_install_guard(self):
        # Fixture freeze is intentionally pre-attempt, so there is no H2
        # original claim yet. Actual B3 still bypasses this modeled refusal.
        pre_reserve_freeze = (self.op, "original-lifetime", 2, 20)
        self.assertEqual(pre_reserve_freeze[0], self.op)
        self.assertEqual(self.rows()[2], [])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.custody.status()["status"], "IDLE")
        generator = self.exchange()
        self.reserve_and_hold(generator)
        intent = self.freeze()
        self.assertEqual(intent.observed, pre_reserve_freeze[3])
        self.assertEqual(self.modeled_decision(
            None, intent, self.original, intent), "MODELED_HOLD")
        # Direct B3 reservation happened despite modeled freeze: no actual guard.
        generator.close()
        self.assert_local("ABORTED", 1)
        self.assertEqual(self.calls, [])

    def test_r7de_reserved_without_admission_remains_local_only(self):
        generator = self.exchange()
        self.reserve_and_hold(generator)
        intent = self.freeze()
        before = self.rows()
        self.assertEqual(self.modeled_decision(
            None, intent, self.original, intent), "MODELED_HOLD")
        self.assertEqual(self.rows(), before)
        self.recover("RESERVED")
        self.assertEqual(self.calls, [])
        # Explicit fixture cancellation, not automatic abort on ambiguity.
        generator.close()
        self.assert_local("ABORTED", 1)
        self.recover("ABORTED")
        self.assertEqual(self.calls, [])

    def test_r7de_original_local_commit_during_modeled_freeze(self):
        generator = self.exchange()
        self.admit_then_freeze(generator)
        self.assertEqual([e["event"] for e in generator], ["COMMITTED"])
        self.assert_local("COMMITTED", 2)
        self.recover("COMMITTED")
        self.assertEqual(self.calls, ["fake-stream"])

    def test_r7de_foreign_stale_aba_or_unknown_reference_stays_held(self):
        generator = self.exchange()
        admission, intent = self.admit_then_freeze(generator)
        o = self.original
        a = o.attempt
        other_settings = replace(a.settings, max_predict=31)
        other_binding = replace(a.binding, config_digest=other_settings.config_digest,
                                output_tokens=31)
        foreigns = (
            replace(o, lifetime="replacement-lifetime"),
            replace(o, lifecycle_revision=2),
            replace(o, pre_revision=2, post_revision=3),
            replace(o, effect="other-effect"),
            replace(o, attempt=replace(a, context=replace(a.context, generation=4))),
            replace(o, attempt=replace(a, operation_id="other-operation")),
            replace(o, attempt=replace(a, attempt_id="other-attempt")),
            replace(o, attempt=replace(a, settings=other_settings, binding=other_binding)),
        )
        before = self.rows()
        for foreign in foreigns:
            for supplied, current in ((replace(admission, original=foreign), o),
                                      (admission, foreign)):
                self.assertEqual(self.modeled_decision(
                    supplied, intent, current, intent), "MODELED_HOLD")
                self.assertEqual(self.rows(), before)
                self.assert_held()
        for bad in (None, replace(admission, observed=20),
                    replace(admission, observed=21)):
            self.assertEqual(self.modeled_decision(
                bad, intent, o, intent), "MODELED_HOLD")
        self.assertEqual(self.modeled_decision(admission, intent, o,
            replace(intent, intent="replacement-intent")), "MODELED_HOLD")
        self.assert_local("RESERVED", 1)
        self.recover("RESERVED")
        self.assertEqual(self.calls, ["fake-stream"])
        # No automatic terminal transition; registered test cleanup closes the
        # disposable generator AFTER all unknown-state observations.

    def test_r7de_denied_local_commit_keeps_pre_revision_and_custody(self):
        from turn_bridge_b3 import BridgeRefusal
        generator = self.exchange(pre_commit=lambda:False)
        self.admit_then_freeze(generator)
        with self.assertRaisesRegex(BridgeRefusal, "PRE_COMMIT_AUTHORIZATION_DENIED"):
            list(generator)
        self.assert_local("ABORTED", 1)
        self.recover("ABORTED")
        self.assertEqual(self.calls, ["fake-stream"])

    def test_r7de_lost_synthetic_receipt_reconciles_original_only(self):
        from turn_bridge_b3 import BridgeRefusal, SyntheticCommitBinding
        fixture = self

        class LostReceipt:
            def __init__(self, binding):
                self.binding = binding

            def __enter__(self):
                fixture.assertFalse(fixture.db.in_transaction)
                return self

            def terminal(self, result):
                fixture.assertFalse(fixture.db.in_transaction)
                fixture.assert_local("COMMITTED", 2)
                fixture.assertEqual(fixture.rows()[2][0][5], result["turn_id"])
                return False  # Explicit synthetic receipt loss, not C5 state.

            def __exit__(self, *args):
                return False

        def fence(binding):
            self.assertEqual(binding, SyntheticCommitBinding(
                self.ctx.principal_key, self.ctx.tree_key, self.sid, self.user,
                self.original.attempt.attempt_id, "fixture-receipt-request",
                self.settings.model, 1))
            return LostReceipt(binding)

        generator = self.exchange(pre_commit=lambda:True, fence_factory=fence,
                                  fence_request_id="fixture-receipt-request")
        self.admit_then_freeze(generator)
        with self.assertRaisesRegex(BridgeRefusal, "UNKNOWN_HOLD"):
            list(generator)
        self.assert_local("COMMITTED", 2)
        self.recover("COMMITTED")
        self.recover("COMMITTED")
        self.assert_local("COMMITTED", 2)
        self.assertEqual(self.calls, ["fake-stream"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
