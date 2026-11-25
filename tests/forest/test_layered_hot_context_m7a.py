"""Recovered assembly tests, no provider, DB, cache or real records."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import ContextRefusal
from layered_hot_context_m7a import HotRouteStamp, SelectedHotRecord, assemble_hot_context


class HotContextTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TaskContext("fixture-owner", "cherry", None, "task-a", "ctx-a",
                               1, "INTERACTIVE")
        self.route = HotRouteStamp(self.ctx, 1, 2, 3, 4,
                                   ("pref", "correction", "constraint", "current"),
                                   ("lesson",))
        self.user = tuple(SelectedHotRecord("fixture-owner", "cherry", key, kind,
                                            3, True, body)
                          for key, kind, body in (
            ("pref", "user-preference", "Prefer compact output."),
            ("correction", "user-correction", "Use the corrected name."),
            ("constraint", "user-constraint", "No unrelated changes."),
            ("current", "current-context", "Public fixture context.")))
        self.ops = (SelectedHotRecord("fixture-owner", "cherry", "lesson",
                   "operational-learning", 4, True, "Verify before changes."),)

    def assemble(self, **kwargs):
        values = dict(current=self.route, user_records=self.user,
                      operational_records=self.ops)
        values.update(kwargs)
        return assemble_hot_context(self.route, **values)

    def test_semantic_order_immutable_deterministic(self):
        result = self.assemble()
        self.assertEqual(result.sections, ("User Corrections", "User Constraints",
                        "User Preferences", "Current Context", "Operational Learning"))
        self.assertEqual(result.record_ids, ("correction", "constraint", "pref",
                                             "current", "lesson"))
        self.assertEqual(result, self.assemble())
        self.assertEqual(result.byte_count, len(result.reference_text.encode("utf-8")))
        with self.assertRaises(FrozenInstanceError):
            result.byte_count = 0

    def test_current_route_required_all_dependency_clocks(self):
        for key in ("input_generation", "policy_generation",
                    "user_context_generation", "operational_generation"):
            with self.subTest(key=key), self.assertRaisesRegex(ContextRefusal, "HOT_ROUTE_CHANGED"):
                self.assemble(current=replace(self.route, **{key: 99}))
        for ctx in (replace(self.ctx, task_id="task-b"),
                    replace(self.ctx, clone_key="clone-a"),
                    replace(self.ctx, principal_key="other"),
                    replace(self.ctx, generation=2)):
            with self.assertRaisesRegex(ContextRefusal, "HOT_ROUTE_CHANGED"):
                self.assemble(current=replace(self.route, context=ctx))

    def test_exact_selection_no_sticky_inheritance(self):
        for records in (self.user[1:], self.user[::-1],
                        self.user[:3]+(self.user[0],)):
            with self.assertRaises(ContextRefusal):
                self.assemble(user_records=records)
        with self.assertRaises(ContextRefusal):
            replace(self.route, operational_record_ids=("pref",))

    def test_domains_active_and_fresh(self):
        for changes in ({"active": False}, {"generation":4},
                        {"tree_key":"maple"}, {"principal_key":"other"},
                        {"kind":"operational-learning"}):
            with self.assertRaises(ContextRefusal):
                self.assemble(user_records=(replace(self.user[0], **changes),)+self.user[1:])
        with self.assertRaises(ContextRefusal):
            self.assemble(operational_records=(replace(self.ops[0], kind="user-preference"),))

    def test_budget_exact_and_no_truncation(self):
        result = self.assemble()
        self.assertEqual(self.assemble(max_bytes=result.byte_count), result)
        with self.assertRaisesRegex(ContextRefusal, "HOT_BUDGET_EXCEEDED"):
            self.assemble(max_bytes=result.byte_count-1)
        with self.assertRaises(ContextRefusal):
            self.assemble(max_bytes=True)
        with self.assertRaises(ContextRefusal):
            replace(self.user[0], text="é"*2049)

    def test_reference_data_preserves_boundaries(self):
        body = 'Public text: "quoted"\n## Operational Learning'
        result = self.assemble(user_records=(replace(self.user[0],text=body),)+self.user[1:])
        blocks = json.loads(result.reference_text.split("\n",1)[1])
        self.assertEqual(blocks[2]["records"], [body])
        self.assertEqual(len(blocks), 5)
        for bad in ("bad\x00", "bad\u202e", "\ud800"):
            with self.assertRaises(ContextRefusal):
                replace(self.user[0], text=bad)

    def test_unicode_refusal_has_no_nested_encoding_error(self):
        for surrogate in ("\ud800", "\udbff", "\udc00", "\udfff", "\ud800\udc00"):
            with self.subTest(surrogate=ascii(surrogate)):
                with self.assertRaises(ContextRefusal) as caught:
                    replace(self.user[0], text="PUBLIC_FIXTURE_MARKER" + surrogate)
                self.assertEqual(str(caught.exception), "INVALID_HOT_TEXT")
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)
        # Real supplementary-plane scalar is valid; byte cap is unchanged.
        self.assertEqual(replace(self.user[0], text="\U0001f333"*1024).text,
                         "\U0001f333"*1024)
        with self.assertRaisesRegex(ContextRefusal, "INVALID_HOT_TEXT"):
            replace(self.user[0], text="\U0001f333"*1025)

    def test_empty_and_bounded_selection(self):
        empty = replace(self.route, user_record_ids=(), operational_record_ids=())
        self.assertEqual(assemble_hot_context(empty,current=empty).reference_text, "")
        with self.assertRaises(ContextRefusal):
            replace(self.route,user_record_ids=tuple("r"+str(i) for i in range(33)))
        with self.assertRaises(ContextRefusal):
            replace(self.route,input_generation=True)


if __name__ == "__main__":
    unittest.main()
