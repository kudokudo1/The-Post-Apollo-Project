#!/usr/bin/env python3
"""Forest B4c // isolated revocation ordering reference, NEVER an issuer.

No imports from Forest's runtime, C5, C3e, systemd, identity, or personal
databases. Separate disposable SQLite *fixtures* let reviewers reproduce the
acknowledgment-vs-commit race; they are not an enrolled trust authority.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

AUDIENCE = "postapollo.forest.conversation.v1"
FENCE_REFERENCE_ONLY = True
PRODUCTION_AUTHORITY = False
C5_CONSENT_VERIFIED = False
INSTALLED_SOURCE_VERIFIED = False
SCOPE_ACTION = "GENERATE"

SCHEMA = """
CREATE TABLE IF NOT EXISTS fixture_scopes (
    principal TEXT NOT NULL,
    tree TEXT NOT NULL,
    audience TEXT NOT NULL,
    epoch INTEGER NOT NULL CHECK(epoch > 0),
    state TEXT NOT NULL CHECK(state IN ('ACTIVE','REVOKING','REVOKED')),
    PRIMARY KEY (principal, tree, audience)
);
CREATE TABLE IF NOT EXISTS fixture_permits (
    permit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    principal TEXT NOT NULL,
    tree TEXT NOT NULL,
    audience TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    intent_sha256 TEXT NOT NULL,
    attempt TEXT NOT NULL,
    grant TEXT NOT NULL,
    request TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN (
        'PENDING','UNKNOWN_HOLD','COMMIT_CONFIRMED','ROLLBACK_CONFIRMED')),
    UNIQUE (principal, tree, audience, attempt),
    UNIQUE (principal, tree, audience, grant),
    UNIQUE (principal, tree, audience, request)
);
CREATE UNIQUE INDEX IF NOT EXISTS fixture_one_unresolved
ON fixture_permits(principal, tree, audience)
WHERE state IN ('PENDING','UNKNOWN_HOLD');
"""


class FenceHold(Exception):
    """All authority and dispute outcomes are safe refusal in this fixture."""


def _key(s):
    if not isinstance(s, str) or not s.isascii() or not (1 <= len(s) <= 96):
        raise FenceHold("INVALID_BOUND_FIELD")
    if not all(c.isalnum() or c in "-_" for c in s):
        raise FenceHold("INVALID_BOUND_FIELD")
    return s


def _canonical_intent(data):
    required = {
        "audience", "principal", "tree", "userTurn", "attempt",
        "grant", "request", "action", "model", "revision", "epoch",
        "expiresAt", "issuerWitness",
    }
    if type(data) is not dict or set(data) != required:
        raise FenceHold("EXACT_INTENT_REQUIRED")
    if data["audience"] != AUDIENCE or data["action"] != SCOPE_ACTION:
        raise FenceHold("WRONG_AUDIENCE_OR_ACTION")
    # Audience is already checked against an exact dotted namespace above;
    # do not treat it as a human/fixture identifier.
    for name in required - {"revision", "epoch", "expiresAt", "audience"}:
        _key(data[name])
    if any(type(data[n]) is not int for n in ("revision", "epoch", "expiresAt")):
        raise FenceHold("INVALID_INTENT_COUNTER")
    if data["revision"] < 0 or data["epoch"] < 1 or data["expiresAt"] <= 0:
        raise FenceHold("INVALID_INTENT_COUNTER")
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("ascii")).hexdigest()


class UntrustedFenceReference:
    """Test-only SQLite state model for a hypothetical protected issuer.

    A caller of this class controls the fixture values, so no output may be
    interpreted as a C5 grant, signed receipt or real production permission.
    The *ordering invariant* is the only thing this reference exercises.
    """

    def __init__(self, path):
        self.db = sqlite3.connect(
            str(path), timeout=4.0, isolation_level=None,
            check_same_thread=False)
        self.db.execute("PRAGMA busy_timeout=4000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def _transaction(self, fn):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = fn()
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def seed_test_scope(self, principal, tree, epoch):
        """Disposable fixture setup, NEVER trusted operator enrollment."""
        _key(principal)
        _key(tree)
        if type(epoch) is not int or epoch < 1:
            raise FenceHold("BAD_EPOCH")
        self._transaction(lambda: self.db.execute(
            "INSERT INTO fixture_scopes VALUES(?,?,? ,?,'ACTIVE')",
            (principal, tree, AUDIENCE, epoch),
        ))

    def prepare_test_only(self, intent, now):
        intent_digest = _canonical_intent(intent)
        if type(now) is not int or now < 0 or now >= intent["expiresAt"]:
            raise FenceHold("EXPIRED_OR_INVALID_CLOCK")
        p, tree = intent["principal"], intent["tree"]

        def write():
            row = self.db.execute(
                "SELECT state,epoch FROM fixture_scopes "
                "WHERE principal=? AND tree=? AND audience=?",
                (p, tree, AUDIENCE),
            ).fetchone()
            if row is None or row != ("ACTIVE", intent["epoch"]):
                raise FenceHold("SCOPE_REVOKED_STALE_OR_MISSING")
            if self.db.execute(
                "SELECT 1 FROM fixture_permits WHERE principal=? "
                "AND tree=? AND audience=? AND state IN ('PENDING','UNKNOWN_HOLD')",
                (p, tree, AUDIENCE),
            ).fetchone():
                raise FenceHold("EXISTING_UNRESOLVED_FENCE")
            try:
                row = self.db.execute(
                    "INSERT INTO fixture_permits "
                    "(principal,tree,audience,epoch,intent_sha256,attempt,"
                    "grant,request,state) VALUES(?,?,?,?,?,?,?,?,'PENDING')",
                    (p, tree, AUDIENCE, intent["epoch"], intent_digest,
                     intent["attempt"], intent["grant"], intent["request"]),
                )
            except sqlite3.IntegrityError as exc:
                raise FenceHold("DUPLICATE_ATTEMPT_OR_GRANT") from exc
            return row.lastrowid

        return self._transaction(write)

    def request_revocation_test_only(self, principal, tree, epoch):
        _key(principal)
        _key(tree)
        if type(epoch) is not int or epoch < 1:
            raise FenceHold("BAD_EPOCH")

        def write():
            row = self.db.execute(
                "SELECT state,epoch FROM fixture_scopes "
                "WHERE principal=? AND tree=? AND audience=?",
                (principal, tree, AUDIENCE),
            ).fetchone()
            if row is None or row[1] != epoch:
                raise FenceHold("STALE_OR_MISSING_REVOCATION_SCOPE")
            # This update serializes with prepare_test_only under BEGIN IMMEDIATE.
            # It prevents issuance of *new* permits but is not itself an ACK.
            self.db.execute(
                "UPDATE fixture_scopes SET state='REVOKING' "
                "WHERE principal=? AND tree=? AND audience=? "
                "AND state='ACTIVE'",
                (principal, tree, AUDIENCE),
            )
            outstanding = self.db.execute(
                "SELECT COUNT(*) FROM fixture_permits WHERE "
                "principal=? AND tree=? AND audience=? "
                "AND state IN ('PENDING','UNKNOWN_HOLD')",
                (principal, tree, AUDIENCE),
            ).fetchone()[0]
            if outstanding:
                return "REVOCATION_WAITING_FOR_FENCE"
            self.db.execute(
                "UPDATE fixture_scopes SET state='REVOKED' "
                "WHERE principal=? AND tree=? AND audience=?",
                (principal, tree, AUDIENCE),
            )
            return "SIMULATED_REVOCATION_ACK"

        return self._transaction(write)

    def mark_unknown_on_recovery_test_only(self):
        """An issuer crash or lost receipt leaves pending fences unresolved."""
        def write():
            return self.db.execute(
                "UPDATE fixture_permits SET state='UNKNOWN_HOLD' "
                "WHERE state='PENDING'",
            ).rowcount
        return self._transaction(write)

    def fixture_terminal_receipt(self, permit, exact_intent, outcome):
        """ONLY simulated protected receipt; cannot authenticate a real caller."""
        digest = _canonical_intent(exact_intent)
        if outcome not in ("COMMIT_CONFIRMED", "ROLLBACK_CONFIRMED"):
            raise FenceHold("UNTRUSTED_TERMINAL_OUTCOME")

        def write():
            row = self.db.execute(
                "SELECT intent_sha256,state FROM fixture_permits "
                "WHERE permit_id=?", (permit,),
            ).fetchone()
            if (row is None or row[0] != digest or
                    row[1] not in ("PENDING", "UNKNOWN_HOLD")):
                raise FenceHold("RECEIPT_MISSING_MISMATCH_OR_REPLAYED")
            self.db.execute(
                "UPDATE fixture_permits SET state=? WHERE permit_id=?",
                (outcome, permit),
            )
            return "SIMULATED_TERMINAL_RECORDED"

        return self._transaction(write)

    def read_fixture(self, principal, tree):
        return self.db.execute(
            "SELECT state FROM fixture_scopes WHERE principal=? AND tree=? "
            "AND audience=?", (principal, tree, AUDIENCE),
        ).fetchone()[0]


def intent(**changes):
    data = {
        "audience": AUDIENCE, "principal": "alice", "tree": "treeA",
        "userTurn": "u100", "attempt": "a100", "grant": "g100",
        "request": "r100", "action": "GENERATE", "model": "localModel",
        "revision": 7, "epoch": 2, "expiresAt": 200,
        "issuerWitness": "fixtureOnly",
    }
    data.update(changes)
    return data


class ForestB4cIssuerOrderingReferenceTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "issuer.sqlite3"
        self.issue = UntrustedFenceReference(self.path)
        self.addCleanup(self.issue.close)
        self.issue.seed_test_scope("alice", "treeA", 2)

    def test_01_admit_first_revocation_waits_for_terminal(self):
        candidate = intent()
        permit = self.issue.prepare_test_only(candidate, 100)
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "REVOCATION_WAITING_FOR_FENCE")
        with self.assertRaises(FenceHold):
            self.issue.prepare_test_only(intent(attempt="a101"), 100)
        self.assertEqual(
            self.issue.fixture_terminal_receipt(permit, candidate, "COMMIT_CONFIRMED"),
            "SIMULATED_TERMINAL_RECORDED")
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "SIMULATED_REVOCATION_ACK")
        self.assertEqual(self.issue.read_fixture("alice", "treeA"), "REVOKED")

    def test_02_revoke_first_prevents_new_permit(self):
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "SIMULATED_REVOCATION_ACK")
        with self.assertRaisesRegex(FenceHold, "SCOPE_REVOKED"):
            self.issue.prepare_test_only(intent(), 100)

    def test_03_unknown_crash_cannot_earn_revocation_ack(self):
        permit = self.issue.prepare_test_only(intent(), 100)
        self.assertGreater(permit, 0)
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "REVOCATION_WAITING_FOR_FENCE")
        self.assertEqual(self.issue.mark_unknown_on_recovery_test_only(), 1)
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "REVOCATION_WAITING_FOR_FENCE")
        with self.assertRaisesRegex(FenceHold, "EXISTING_UNRESOLVED|SCOPE_REVOKED"):
            self.issue.prepare_test_only(intent(attempt="a101"), 100)

    def test_04_cross_store_commit_with_lost_receipt_is_unknown(self):
        permit = self.issue.prepare_test_only(intent(), 100)
        # THIS is a completely independent *synthetic* Forest store. There is
        # no SQLite cross-database atomicity with the issuer ledger.
        forest = sqlite3.connect(str(Path(self.tmp.name) / "forest-fixture.sqlite3"))
        self.addCleanup(forest.close)
        forest.execute("CREATE TABLE fake_responses(attempt TEXT PRIMARY KEY)")
        forest.execute("INSERT INTO fake_responses VALUES('a100')")
        forest.commit()
        self.issue.close()
        self.issue = UntrustedFenceReference(self.path)
        self.assertEqual(self.issue.mark_unknown_on_recovery_test_only(), 1)
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "REVOCATION_WAITING_FOR_FENCE")
        self.assertEqual(
            forest.execute("SELECT COUNT(*) FROM fake_responses").fetchone()[0], 1)
        with self.assertRaises(FenceHold):
            self.issue.fixture_terminal_receipt(
                permit, intent(model="otherModel"), "COMMIT_CONFIRMED")
        # The test deliberately does NOT infer a trusted issuer receipt from
        # a separate database row; only the absent native proof could settle it.

    def test_05_exact_binding_required_for_fake_receipt(self):
        p = self.issue.prepare_test_only(intent(), 100)
        for wrong in (intent(principal="bob"), intent(tree="treeB"),
                      intent(model="otherModel"), intent(userTurn="u101"),
                      intent(grant="g101"), intent(epoch=3),
                      intent(revision=8), intent(request="r101")):
            with self.assertRaises(FenceHold):
                self.issue.fixture_terminal_receipt(p, wrong, "COMMIT_CONFIRMED")
        self.assertEqual(self.issue.fixture_terminal_receipt(
            p, intent(), "ROLLBACK_CONFIRMED"), "SIMULATED_TERMINAL_RECORDED")
        with self.assertRaises(FenceHold):
            self.issue.fixture_terminal_receipt(p, intent(), "COMMIT_CONFIRMED")

    def test_06_no_duplicate_attempt_grant_or_request_even_after_terminal(self):
        p = self.issue.prepare_test_only(intent(), 100)
        self.issue.fixture_terminal_receipt(p, intent(), "COMMIT_CONFIRMED")
        for duplicate in (intent(), intent(attempt="a101"),
                          intent(grant="g101")):
            with self.assertRaisesRegex(FenceHold, "DUPLICATE"):
                self.issue.prepare_test_only(duplicate, 100)

    def test_07_wrong_scope_epoch_audience_expiry_and_fields_rejected(self):
        for bad in (intent(epoch=1), intent(principal="bob"),
                    intent(tree="treeB"), intent(expiresAt=100),
                    intent(action="READ_SESSION"),
                    intent(audience="postapollo.identity.signin"),
                    intent(model=""),
                    intent(issuerWitness="not/a/key")):
            with self.assertRaises(FenceHold):
                self.issue.prepare_test_only(bad, 100)
        with self.assertRaises(FenceHold):
            self.issue.prepare_test_only({**intent(), "productionAuthority": True}, 100)

    def test_08_one_pending_per_principal_tree_action_scope(self):
        self.issue.prepare_test_only(intent(), 100)
        with self.assertRaisesRegex(FenceHold, "EXISTING_UNRESOLVED"):
            self.issue.prepare_test_only(
                intent(attempt="a102", grant="g102", request="r102"), 100)

    def test_09_independent_tree_scope_does_not_lend_permission(self):
        self.issue.seed_test_scope("alice", "treeB", 5)
        self.assertEqual(
            self.issue.request_revocation_test_only("alice", "treeA", 2),
            "SIMULATED_REVOCATION_ACK")
        b = intent(tree="treeB", epoch=5, attempt="b100", grant="bGrant",
                   request="bRequest")
        permit = self.issue.prepare_test_only(b, 100)
        self.assertGreater(permit, 0)
        with self.assertRaises(FenceHold):
            self.issue.prepare_test_only(intent(), 100)

    def test_10_two_connections_serialize_admit_and_revoke(self):
        # Two real SQLite connections, two threads, independent transactions.
        # Their ordering may vary. Neither ordering is allowed to ack
        # revocation while a conflicting permit was issued.
        barrier = threading.Barrier(2)
        results = {}

        def admit():
            fixture = UntrustedFenceReference(self.path)
            try:
                barrier.wait(timeout=3)
                try:
                    results["admit"] = fixture.prepare_test_only(intent(), 100)
                except FenceHold as exc:
                    results["admit"] = str(exc)
            finally:
                fixture.close()

        def revoke():
            fixture = UntrustedFenceReference(self.path)
            try:
                barrier.wait(timeout=3)
                results["revoke"] = fixture.request_revocation_test_only(
                    "alice", "treeA", 2)
            finally:
                fixture.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            a = ex.submit(admit)
            b = ex.submit(revoke)
            a.result(timeout=7)
            b.result(timeout=7)
        if isinstance(results["admit"], int):
            self.assertEqual(results["revoke"], "REVOCATION_WAITING_FOR_FENCE")
        else:
            self.assertIn("SCOPE_REVOKED", results["admit"])
            self.assertEqual(results["revoke"], "SIMULATED_REVOCATION_ACK")

    def test_11_unknown_never_autoretries_after_recovery(self):
        self.issue.prepare_test_only(intent(), 100)
        self.issue.mark_unknown_on_recovery_test_only()
        with self.assertRaises(FenceHold):
            self.issue.prepare_test_only(intent(), 100)
        with self.assertRaises(FenceHold):
            self.issue.prepare_test_only(
                intent(attempt="a200", grant="g200", request="r200"), 100)

    def test_12_reference_cannot_claim_to_be_an_installed_issuer(self):
        self.assertTrue(FENCE_REFERENCE_ONLY)
        self.assertFalse(PRODUCTION_AUTHORITY)
        self.assertFalse(INSTALLED_SOURCE_VERIFIED)
        self.assertFalse(C5_CONSENT_VERIFIED)
        self.assertNotIn("authorize", dir(self.issue))
        self.assertNotIn("issue_signed_grant", dir(self.issue))


if __name__ == "__main__":
    unittest.main()
