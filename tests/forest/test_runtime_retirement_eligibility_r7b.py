"""Actual B1/B3 disposable records; no network, body read during inspection."""
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from turn_bridge_b3 import ForestTurnBridge, bootstrap_attempts_synthetic
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import SessionContextRef
from runtime_events_r3 import OperationRef
from heart_resource_custody_h2 import AttemptRef
from heart_dispatch_reference_h1 import TransportSettings, MAX_AGE_NS
from model_binding_i2 import ModelBinding, ModelIdentity
from runtime_retirement_eligibility_r7b import (
    FIXTURE, RetirementRef, FixtureObservation, inspect_fixture,
)


class RetirementTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
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
        def stream(**kw):
            yield dict(event="STARTED", model=self.model, provider="ollama")
            yield dict(event="DELTA", text="Public reply")
            yield dict(event="COMPLETE", model=self.model, provider="ollama", text="Public reply")
        bridge = ForestTurnBridge(self.journal, clock_ms=lambda:3, streamer=stream)
        events = list(bridge.exchange(owner=self.ctx.principal_key, session_id=self.session,
                      expected_revision=1, model=self.model))
        attempt = events[0]["attempt_id"]
        ref = SessionContextRef(self.ctx, self.session, 1, user["turn_id"])
        op = OperationRef(ref, "fixture-operation")
        settings = TransportSettings(self.model, 2048, 32)
        binding = ModelBinding("fixture-binding", "small",
            ModelIdentity(self.model, "sha256:"+"a"*64, "ollama", "fixture-runtime",
                          "1.0", "sha256:"+"b"*64), settings.config_digest, 2048, 32)
        self.scope = RetirementRef(op, AttemptRef(self.ctx, user["turn_id"],
                                 op.operation_id, attempt, binding, settings), 2)
        self.observations = tuple(FixtureObservation(k, s, self.scope, "fixture-clock", 3, 10+i)
            for i,(k,s) in enumerate((("FREEZE","FROZEN"),("TERMINAL","COMMITTED"),
                 ("QUIESCENCE","QUIESCENT"),("ACCOUNTING","ACCOUNTED"),
                 ("SETTLEMENT","SETTLED"))))
        self.reads = []
        self.denied = []

    def begin(self):
        self.db.execute("PRAGMA query_only=ON")
        self.db.execute("BEGIN")
        def authorizer(action, arg1, arg2, dbname, trigger):
            self.reads.append((action, arg1, arg2))
            if (action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE)
                    or (action == sqlite3.SQLITE_READ and arg2 in ("body","title"))):
                self.denied.append((action,arg1,arg2))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(authorizer)

    def inspect(self, **changes):
        args = dict(fixture=FIXTURE, original=self.scope, current=self.scope,
                    observations=self.observations, clock_domain="fixture-clock", now_ns=20)
        args.update(changes)
        return inspect_fixture(self.journal, **args)

    def assert_hold(self, **changes):
        out = self.inspect(**changes)
        self.assertEqual(out["status"], "UNKNOWN_HOLD")
        self.assert_no_authority(out)

    def assert_no_authority(self, out):
        for k,v in out.items():
            if k not in ("status","fixture_only","safe_actions"):
                self.assertIs(v, False, k)
        self.assertEqual(out["safe_actions"], [])
        self.assertIs(out["fixture_only"], True)

    def test_committed_fixed_fixture_no_body_reads_or_mutation(self):
        before = self.db.total_changes
        self.begin()
        result = self.inspect()
        self.assertEqual(result["status"], "FIXTURE_ELIGIBILITY_MATCHED")
        self.assert_no_authority(result)
        self.assertEqual(self.denied, [])
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(self.db.total_changes, before)
        self.assertNotIn(self.session, str(result))

    def test_requires_owner_transaction_and_read_only_connection(self):
        self.assert_hold()
        self.db.execute("BEGIN")
        self.assert_hold()
        self.assertTrue(self.db.in_transaction)

    def test_mismatch_rejected_before_any_sql(self):
        self.begin()
        a = self.scope.attempt
        for current in (replace(self.scope, session_revision=3),
                        replace(self.scope, attempt=replace(a, attempt_id="other")),
                        replace(self.scope, attempt=replace(a, operation_id="other")),
                        replace(self.scope, attempt=replace(a, context=replace(self.ctx, generation=4))),
                        replace(self.scope, attempt=replace(a, binding=replace(a.binding, binding_id="other"))),
                        replace(self.scope, attempt=replace(a, binding=replace(a.binding,
                            identity=replace(a.binding.identity, artifact_digest="sha256:"+"c"*64))))):
            self.assert_hold(current=current)
        self.assert_hold(fixture="unknown")
        self.assertEqual(self.reads, [])

    def test_observation_states_order_freshness_and_identity(self):
        self.begin()
        for i, state in enumerate(("UNKNOWN","STOP","ACTIVE","UNACCOUNTED","UNKNOWN_HOLD")):
            values=list(self.observations)
            values[i]=replace(values[i], state=state)
            self.assert_hold(observations=tuple(values))
        for i,state in ((1,"EOF"),(2,"UNKNOWN"),(3,"RETAINED_UNACCOUNTED"),(0,"NOT_FROZEN")):
            values=list(self.observations)
            values[i]=replace(values[i],state=state)
            self.assert_hold(observations=tuple(values))
        for changes in (dict(observed_ns=10), dict(observed_ns=21), dict(generation=True),
                        dict(generation=4), dict(clock_domain="other"),
                        dict(scope=replace(self.scope, attempt=replace(self.scope.attempt,attempt_id="other")))):
            self.assert_hold(observations=self.observations[:1]+
                             (replace(self.observations[1],**changes),)+self.observations[2:])
        self.assert_hold(observations=self.observations[:-1])
        self.assert_hold(now_ns=MAX_AGE_NS+20)
        self.assertEqual(self.reads, [])

    def test_local_aborted_or_reserved_holds_even_with_positive_references(self):
        for state in ("ABORTED","RESERVED"):
            with self.subTest(state=state):
                self.db.execute("UPDATE forest_attempts_b3 SET status=?,reply_turn_id=NULL",(state,))
                self.db.commit()
                self.begin()
                self.assert_hold()
                self.db.set_authorizer(None)
                self.db.rollback()
                self.db.execute("PRAGMA query_only=OFF")

    def test_other_reserved_attempt_holds(self):
        self.db.execute("INSERT INTO forest_turns VALUES (?,?,?,?,?,?,?,?)",
            ("other-user",self.session,3,"user","","","Fixed public",4))
        self.db.execute("INSERT INTO forest_attempts_b3 "
            "(attempt_id,session_id,user_turn_id,owner_key,expected_revision,model_key,status,created_at_ms,updated_at_ms) "
            "VALUES (?,?,?,?,?,?, 'RESERVED',?,?)",
            ("other-attempt",self.session,"other-user",self.ctx.principal_key,3,self.model,4,4))
        self.db.commit()
        self.begin()
        self.assert_hold()

    def test_stale_revision_wrong_tree_and_missing_row_hold(self):
        for sql in ("UPDATE forest_sessions SET revision=3",
                    "UPDATE forest_sessions SET tree_key='other'",
                    "DELETE FROM forest_attempts_b3"):
            with self.subTest(sql=sql):
                self.db.execute(sql)
                self.db.commit()
                self.begin()
                self.assert_hold()
                self.db.set_authorizer(None)
                self.db.rollback()
                self.db.execute("PRAGMA query_only=OFF")

    def test_equal_current_scope_cannot_override_durable_model(self):
        self.db.execute("UPDATE forest_attempts_b3 SET model_key='other'")
        self.db.commit()
        self.begin()
        self.assert_hold()


if __name__ == "__main__":
    unittest.main(verbosity=2)
