#!/usr/bin/env python3
"""DOC 4 C5-H5: source-caller evidence, bypass tripwires, production HOLD.

The PX checkout is a pinned draft snapshot. The test never imports or runs PX,
does not use real Hospital data, open sockets, or claim installed compatibility.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import HospitalC5H5EntrypointAudit as A


class HospitalC5H5EntrypointAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.px_root = ROOT / "px-h1-source"
        cls.original_app, cls.original_px = A.collect_sources(ROOT, cls.px_root)

    def setUp(self):
        self.app = dict(self.original_app)
        self.px = dict(self.original_px)

    def run_audit(self):
        return A.audit_texts(self.app, self.px)

    def rejected(self, code):
        with self.assertRaisesRegex(A.SourceHold, code):
            self.run_audit()

    def change_ui(self, path, old, new):
        source = self.app[path]
        self.assertIn(old, source)
        self.app[path] = source.replace(old, new, 1)

    def change_px(self, path, old, new):
        source = self.px[path]
        self.assertIn(old, source)
        self.px[path] = source.replace(old, new, 1)

    def test_01_current_app_and_pinned_px_sources_are_reconciled_but_unreleased(self):
        result = self.run_audit()
        self.assertEqual(result["legacyDesktopPxServiceCount"], 21)
        self.assertEqual(result["nativeHospitalUiServiceCount"], 3)
        self.assertEqual(result["pxDirectLegacyStoreCallSites"], 4)
        self.assertEqual(result["status"], "UNMIGRATED_WRITER_ENTRYPOINTS_HOLD")
        self.assertTrue(result["sourceRouteTokensReconciled"])

    def test_02_native_paths_are_exactly_two_readers_and_one_room_requester(self):
        result = self.run_audit()
        self.assertEqual(result["nativeHospitalUiServices"], {
            "services/hospital/HospitalRoomLifecycleService.qml": ["read", "request"],
            "services/hospital/HospitalRoomBinService.qml": ["read"],
            "services/hospital/HospitalDoctorService.qml": ["read"],
        })

    def test_03_existing_legacy_writers_remain_observable_not_authorized(self):
        result = self.run_audit()
        for name in (
            "HospitalDoctorNameService",
            "HospitalRoomNameService",
            "HospitalWorkforceRoomCreateService",
            "HospitalChartService",
            "HospitalAssignmentService",
            "HospitalRoomConversationAdapter",
            "HospitalWorkerAttachmentActionService",
        ):
            self.assertIn(
                "services/hospital/" + name + ".qml",
                result["legacyDesktopPxServices"])

    def test_04_all_release_and_human_authority_flags_stay_false(self):
        report = self.run_audit()
        for key in (
            "allWriterCompatibilityVerified",
            "allLegacyProcessesFenced",
            "installedHostObserved",
            "independentHumanConsentVerified",
            "protectedPxProductionWriterVerified",
            "productionAuthorized",
        ):
            self.assertIs(report[key], False, key)
        self.assertEqual(report["safeActions"], [])
        self.assertTrue(report["sourceOnly"])

    def test_05_new_desktop_px_launcher_in_widget_is_unreconciled(self):
        self.app["widgets/HospitalW.qml"] += (
            '\nProcess { property var dangerous: "$HOME/.local/bin/px" }\n'
        )
        self.rejected("UNRECONCILED_LEGACY_DESKTOP_PX_ENTRYPOINTS")

    def test_06_new_native_requester_in_widget_is_unreconciled(self):
        self.app["widgets/HospitalW.qml"] += (
            '\nproperty string extra: "' + A.NATIVE_REQ + '"\n'
        )
        self.rejected("UNRECONCILED_NATIVE_HOSPITAL_UI_ENTRYPOINTS")

    def test_07_new_direct_legacy_store_entrypoint_denied(self):
        self.app["widgets/HospitalW.qml"] += (
            '\nproperty string unsafe: "px-hospital-store"\n'
        )
        self.rejected("DIRECT_PRIVILEGED_HOSPITAL_UI_ROUTE")

    def test_08_desktop_generic_privileged_store_command_denied(self):
        self.app["services/hospital/HospitalRoomService.qml"] += (
            '\nproperty string unsafe: "store-command"\n'
        )
        self.rejected("DIRECT_PRIVILEGED_HOSPITAL_UI_ROUTE")

    def test_09_direct_hospital_trash_or_restore_legacy_method_denied(self):
        for method in ('"room-lifecycle-trash"', '"room-lifecycle-restore"'):
            with self.subTest(method=method):
                self.app["widgets/HospitalW.qml"] += "\n" + method
                self.rejected("DIRECT_PRIVILEGED_HOSPITAL_UI_ROUTE")
                self.app["widgets/HospitalW.qml"] = self.original_app[
                    "widgets/HospitalW.qml"]

    def test_10_existing_desktop_launcher_disappearing_requires_reconciliation(self):
        name = "services/hospital/HospitalAssignmentService.qml"
        self.app[name] = self.app[name].replace(
            ".local/bin/px", ".local/bin/blocked")
        self.app[name] = self.app[name].replace(
            ".local/share/post-apollo-dev-runtime/bin/px",
            ".local/share/post-apollo-dev-runtime/bin/blocked")
        self.rejected("UNRECONCILED_LEGACY_DESKTOP_PX_ENTRYPOINTS")

    def test_11_downgraded_native_commit_receipt_is_detected(self):
        self.change_ui(
            "services/hospital/HospitalRoomLifecycleService.qml",
            'payload.status !== "COMMITTED"', 'payload.status !== "REQUESTED"')
        self.rejected("NATIVE_ROOM_REQUEST_OR_RECEIPT_GUARD_MISSING")

    def test_12_direct_room_native_client_changed_requires_review(self):
        self.change_ui(
            "services/hospital/native/hospital_room_request_client.c",
            '#define ISSUER_SOCKET "/run/post-apollo/hospital/issuer.sock"',
            '#define ISSUER_SOCKET "/tmp/hospital-issuer.sock"')
        self.rejected("FIXED_NATIVE_REQUEST_CLIENT_IDENTITY_CHANGED")

    def test_13_doctor_directory_read_cannot_silently_become_desktop_write(self):
        self.change_ui(
            "services/hospital/HospitalDoctorService.qml",
            "readonly property bool protectedDoctorWritesReady: false",
            "readonly property bool protectedDoctorWritesReady: true")
        self.rejected("DOCTOR_READ_ONLY_CUTOVER_CHANGED")

    def test_14_hospital_bin_cannot_accept_burn_metadata(self):
        self.change_ui(
            "services/hospital/HospitalRoomBinService.qml",
            "item.burnAllowed === false", "item.burnAllowed === true")
        self.rejected("NATIVE_HOSPITAL_BIN_NO_BURN_GUARD_MISSING")

    def test_15_unconditional_native_consent_denial_cannot_be_removed(self):
        path = "services/connections/hospital/HospitalNativeIssuerService.py"
        self.change_ui(
            path,
            'C.deny("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE")',
            "return True")
        self.rejected("CONSENT_GATE_NOT_UNCONDITIONAL_DENIAL")

    def test_16_displaced_signing_gate_is_detected(self):
        path = "services/connections/hospital/HospitalNativeIssuerService.py"
        value = self.app[path]
        exact = "_require_independent_room_consent(request, prepared, peer, first_seat)"
        self.assertIn(exact, value)
        # Removing the in-orchestration call while keeping the hard-deny
        # function must not pass as a protected signing entrypoint.
        self.app[path] = value.replace("    " + exact + "\n", "", 1)
        self.rejected("NATIVE_SIGNING_GATE_ORDER_CHANGED")

    def test_17_px_cli_legacy_dispatcher_change_detected(self):
        self.change_px(
            "bin/px", 'python3 "$ROOT/bin/px-hospital-store"',
            'python3 "$ROOT/bin/px-unreviewed-store"')
        self.rejected("PX_LEGACY_DISPATCHER_CHANGED")

    def test_18_old_px_store_cannot_move_cutover_fence_after_sqlite_open(self):
        path = "bin/px-hospital-store"
        self.change_px(path, "    refuse_legacy_store_after_cutover()",
                       "    pass # removed cutover marker")
        self.rejected("PX_LEGACY_CUTOVER_FENCE_CHANGED")

    def test_19_runtime_uid_gate_on_generic_protected_writer_is_required(self):
        path = "bin/px_hospital_room_writer.py"
        self.change_px(
            path, 'if action == "store-command" and peer_uid != self.runtime_uid:',
            'if action == "store-command" and False:')
        self.rejected("PROTECTED_PX_RUNTIME_UID_FENCE_CHANGED")

    def test_20_room_lifecycle_mutator_must_remain_excluded_from_generic_bridge(self):
        path = "bin/px_hospital_protected_store_bridge.py"
        self.change_px(path, '"room-lifecycle-trash"', '"room-lifecycle-foo"')
        self.rejected("ROOM_LIFECYCLE_MUTATION_ENTERED_GENERIC_PX_BRIDGE")

    def test_21_consent_bridge_root_issuer_boundary_change_detected(self):
        path = "bin/px_hospital_connections_consent.py"
        self.change_px(path, "ROOT_ISSUER_ONLY", "EVERYONE_IS_ISSUER")
        self.rejected("PROTECTED_PX_CONSENT_WRITER_SOURCE_CHANGED")

    def test_22_missing_pin_or_unreadable_source_cannot_be_misread_as_clean(self):
        del self.px["bin/px-hospital-store"]
        self.rejected("MISSING_REQUIRED_REPOSITORY_SOURCE")

    def test_23_no_mutation_of_supplied_source_maps(self):
        app = copy.deepcopy(self.app)
        px = copy.deepcopy(self.px)
        self.run_audit()
        self.assertEqual(app, self.app)
        self.assertEqual(px, self.px)

    def test_24_source_classification_never_creates_trust_from_user_claims(self):
        report = self.run_audit()
        self.assertNotIn("grant", json.dumps(report).lower())
        self.assertFalse(report["independentHumanConsentVerified"])
        self.assertFalse(report["productionAuthorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
