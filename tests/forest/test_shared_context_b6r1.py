"""B6-R1 semantic contract regressions; no runtime or private data."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import (
    TaskContext, BarkAttachment, BarkListRequest, ListOperationReference,
    ContractRefusal, ReferenceResult, parse_list_fields,
    compare_list_reference, public_status,
)


class SharedContextTests(unittest.TestCase):
    def setUp(self):
        self.context = TaskContext("fixture-owner-a", "canonical-maple", None,
                                   "task-a", "context-a", 1, "BACKGROUND")
        self.surface = BarkAttachment(
            self.context, "camera-bark", "requester-a", "release-a",
            "seat-a", "recipient-a", "MAPLE", 1,
        )
        self.fields = {"requestId": "fixture_request_001", "treeKey": "MAPLE",
                       "generation": 1, "action": "LIST_SESSIONS"}
        self.request = parse_list_fields(self.fields)
        self.operation = ListOperationReference(self.surface, self.request, "op-a")

    def compare(self, request=None, attachment=None, context=None):
        result = compare_list_reference(
            self.operation, self.request if request is None else request,
            self.surface if attachment is None else attachment,
            self.context if context is None else context,
        )
        self.assertEqual(result.status, "UNKNOWN_HOLD")
        self.assertFalse(result.permission_granted)
        self.assertFalse(result.source_authenticated)
        self.assertFalse(result.production_authority)
        self.assertEqual(result.safe_actions, ())
        return result.reason

    def test_valid_request_is_only_a_reference(self):
        self.assertEqual(self.compare(), "REFERENCE_MATCH_AUTHORITY_HOLD")

    def test_bark_request_cannot_assert_owner_or_authority(self):
        for key in ("owner_key", "principal", "dbPath", "recipient", "clone",
                    "model", "permissionGranted", "grant", "task_id"):
            with self.subTest(key=key), self.assertRaises(ContractRefusal):
                parse_list_fields({**self.fields, key: "fixture"})

    def test_exact_request_fields(self):
        for key in self.fields:
            with self.subTest(key=key), self.assertRaises(ContractRefusal):
                parse_list_fields({k: v for k, v in self.fields.items() if k != key})
        for value in ([], None, "LIST_SESSIONS"):
            with self.assertRaises(ContractRefusal):
                parse_list_fields(value)

    def test_no_implicit_read_or_title_or_generation_entitlement(self):
        for action in ("READ_SESSION", "DISCLOSE_SESSION_TITLES", "GENERATE",
                       "SEND", "VOICE", "TOOL", "COMMIT_GENERATE"):
            with self.subTest(action=action), self.assertRaises(ContractRefusal):
                parse_list_fields({**self.fields, "action": action})

    def test_malformed_request_identifiers(self):
        for value in ("short", "x" * 97, "a" * 16 + "\n", None, 7):
            with self.assertRaises(ContractRefusal):
                parse_list_fields({**self.fields, "requestId": value})
        for value in ("../MAPLE", "Maple with spaces", "", "x" * 129):
            with self.assertRaises(ContractRefusal):
                parse_list_fields({**self.fields, "treeKey": value})

    def test_generation_bounds_and_bool_refusal(self):
        for value in (True, False, 0, -1, 1.5, 2**53, "1"):
            with self.assertRaises(ContractRefusal):
                parse_list_fields({**self.fields, "generation": value})

    def test_exact_tree_selection_and_generation_binding(self):
        for changes in ({"requested_tree": "CHERRY"}, {"view_generation": 2}):
            with self.assertRaisesRegex(ContractRefusal, "REQUEST_ATTACHMENT_MISMATCH"):
                ListOperationReference(self.surface, replace(self.request, **changes), "op-b")

    def test_two_bark_surfaces_same_tree_and_task(self):
        second = replace(self.surface, bark_id="forest-bark",
                         requester_id="requester-b", recipient_id="recipient-b")
        self.assertEqual(second.context, self.surface.context)
        self.assertNotEqual(second, self.surface)
        self.assertEqual(self.compare(attachment=second), "ATTACHMENT_CHANGED")
        other_op = ListOperationReference(second, self.request, "op-b")
        self.assertEqual(compare_list_reference(other_op, self.request, second,
                                                self.context).reason,
                         "REFERENCE_MATCH_AUTHORITY_HOLD")

    def test_background_context_does_not_require_bark(self):
        self.assertEqual(self.context.origin, "BACKGROUND")
        self.assertFalse(hasattr(self.context, "bark_id"))
        self.assertFalse(hasattr(self.context, "model"))

    def test_detach_does_not_mutate_task_or_other_surface(self):
        second = replace(self.surface, bark_id="forest-bark",
                         recipient_id="recipient-b")
        detached = self.surface.detach()
        self.assertFalse(detached.attached)
        self.assertTrue(self.surface.attached)
        self.assertTrue(second.attached)
        self.assertIs(detached.context, self.context)
        self.assertEqual(self.compare(attachment=detached), "DETACHED_BARK")

    def test_cannot_bind_detached_view(self):
        with self.assertRaisesRegex(ContractRefusal, "DETACHED_BARK"):
            ListOperationReference(self.surface.detach(), self.request, "op-b")

    def test_distinct_clone_contexts_share_tree_not_execution(self):
        clone = replace(self.context, clone_key="maple-camera",
                        task_id="task-b", execution_context_id="context-b")
        self.assertEqual(clone.tree_key, self.context.tree_key)
        self.assertEqual(clone.principal_key, self.context.principal_key)
        self.assertEqual(self.compare(context=clone), "TASK_CONTEXT_CHANGED")

    def test_context_mutations_refuse_original(self):
        for changes in ({"principal_key": "fixture-owner-b"},
                        {"tree_key": "canonical-cherry"},
                        {"clone_key": "clone-b"}, {"task_id": "task-b"},
                        {"execution_context_id": "context-b"},
                        {"generation": 2}, {"origin": "INTERACTIVE"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.compare(context=replace(self.context, **changes)),
                                 "TASK_CONTEXT_CHANGED")

    def test_attachment_bound_to_current_context(self):
        wrong = replace(self.surface, context=replace(self.context, generation=2))
        self.assertEqual(self.compare(attachment=wrong), "ATTACHMENT_CONTEXT_MISMATCH")

    def test_requester_release_seat_recipient_and_view_change(self):
        for name in ("bark_id", "requester_id", "release_id", "seat_id",
                     "recipient_id", "requested_tree", "view_generation"):
            with self.subTest(name=name):
                other = replace(self.surface, **{name: 2 if name == "view_generation"
                                                 else "other-fixture"})
                self.assertEqual(self.compare(attachment=other), "ATTACHMENT_CHANGED")

    def test_replayed_request_with_other_selection_or_generation_refuses(self):
        for changes in ({"request_id": "fixture_request_002"},
                        {"requested_tree": "CHERRY"}, {"view_generation": 2}):
            self.assertEqual(self.compare(request=replace(self.request, **changes)),
                             "REQUEST_CHANGED")

    def test_canonical_tree_not_identical_to_bark_hint(self):
        self.assertNotEqual(self.context.tree_key, self.request.requested_tree)
        self.assertEqual(self.compare(), "REFERENCE_MATCH_AUTHORITY_HOLD")

    def test_records_are_frozen(self):
        for obj, name in ((self.context, "principal_key"),
                          (self.surface, "recipient_id"),
                          (self.request, "requested_tree"),
                          (self.operation, "operation_id")):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, name, "fixture-other")

    def test_invalid_context_and_attachment(self):
        for changes in ({"principal_key": ""}, {"clone_key": False},
                        {"generation": True}, {"origin": "anything"}):
            with self.assertRaises(ContractRefusal):
                replace(self.context, **changes)
        for changes in ({"context": {}}, {"recipient_id": ""},
                        {"attached": 1}, {"view_generation": 0}):
            with self.assertRaises(ContractRefusal):
                replace(self.surface, **changes)

    def test_public_status_never_exposes_identifiers_or_private_data(self):
        result = compare_list_reference(self.operation, self.request,
                                        self.surface, self.context)
        status = public_status(result)
        self.assertEqual(status, {
            "schema": "post-apollo.forest.shared-reference.b6-r1",
            "status": "UNKNOWN_HOLD", "reason": "REFERENCE_MATCH_AUTHORITY_HOLD",
            "sourceAuthenticated": False, "permissionGranted": False,
            "productionAuthority": False, "privateTitleDisclosureGranted": False,
            "modelExecutionPermitted": False, "safeActions": [],
        })
        self.assertEqual(public_status(ReferenceResult("private synthetic data"))["reason"],
                         "INVALID_REFERENCE")

    def test_wrong_types_never_produce_matching_reference(self):
        result = compare_list_reference({}, self.request, self.surface, self.context)
        self.assertEqual(result.reason, "INVALID_REFERENCE")
        self.assertFalse(result.permission_granted)


if __name__ == "__main__":
    unittest.main()
