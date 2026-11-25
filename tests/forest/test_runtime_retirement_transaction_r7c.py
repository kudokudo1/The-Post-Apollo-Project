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


if __name__ == "__main__":
    unittest.main(verbosity=2)
