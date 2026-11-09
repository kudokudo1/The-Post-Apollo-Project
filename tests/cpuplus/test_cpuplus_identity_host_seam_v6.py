#!/usr/bin/env python3
"""CPU++ V6: inspect ACTUAL merged Identity Center host/UI seam.

This is a read-only cross-owner integration readiness gate, not a login
test, fake Identity host, command server, or a claim of host attestation.
Host-owner code is inspected but never modified or launched by this test.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/identity/desktop_host_lifecycle_v0.py"
SESSION = ROOT / "services/identity/desktop_session_host_v0.py"
IPC = ROOT / "services/identity/private_context_ipc_v0.py"
READER = ROOT / "widgets/messanger/IdentityCenterOrganizationDisplayReader.qml"
CPU = ROOT / "widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml"
BOUNDARY = ROOT / "services/connections/ConnectionsSignInHostBoundary.js"
PROPOSAL = ROOT / "services/connections/ConnectionsSignInIntentProposal.js"
REQUEST = ROOT / "services/connections/ConnectionsRequestStatus.qml"
BROKER = ROOT / "services/connections/ConnectionsBroker.qml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def methods(path: Path, class_name: str) -> tuple[dict[str, ast.FunctionDef], str]:
    source = read(path)
    module = ast.parse(source, filename=str(path))
    target = next(
        (node for node in module.body
         if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if target is None:
        raise AssertionError(f"Missing existing owner class {class_name}")
    return {
        node.name: node for node in target.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }, source


class IdentityCenterRealSeamV6(unittest.TestCase):
    def test_merged_host_is_one_shot_internal_orchestration_not_ipc(self):
        funcs, source = methods(HOST, "DesktopHostLifecycle")
        for required in (
            "start", "begin_login", "logout", "close",
            "_accept_callback", "_display_snapshot",
        ):
            self.assertIn(required, funcs)
        begin = ast.get_source_segment(source, funcs["begin_login"])
        self.assertIn("self._status != \"STARTED\"", begin)
        self.assertIn("self._seat_ok()", begin)
        self.assertIn("self._attempted", begin)
        self.assertIn("self._session.start_login()", begin)
        self.assertIn('{"status": "LOGIN_PENDING"}', begin)
        # A host method is not a command API. The owner must add an
        # independent authenticated endpoint, scope/receipt and seat check.
        self.assertNotIn("handle_command", funcs)
        self.assertNotIn("request_sign_in", funcs)
        self.assertNotIn("cancel_login", funcs)
        self.assertNotIn("recover_login", funcs)
        self.assertIn("This object is not an IPC command handler", source)

    def test_logout_is_not_request_cancel_and_recover_needs_new_host(self):
        funcs, source = methods(HOST, "DesktopHostLifecycle")
        logout = ast.get_source_segment(source, funcs["logout"])
        self.assertIn("self._revoked.set()", logout)
        self.assertIn("self._revoke_locked()", logout)
        self.assertNotIn("request_id", logout.lower())
        self.assertNotIn("cancel", funcs)
        # The existing host owns one attempt per started lifecycle.
        self.assertIn("if self._attempted:", ast.get_source_segment(
            source, funcs["begin_login"]))
        session_methods, session_src = methods(SESSION, "DesktopSessionHost")
        self.assertIn("start_login", session_methods)
        self.assertIn("complete_callback", session_methods)
        self.assertIn("logout", session_methods)
        self.assertIn("Test-only native-host orchestration", session_src)
        self.assertNotIn("handle_command", session_methods)

    def test_actual_unix_display_endpoint_cannot_receive_commands(self):
        source = read(IPC)
        self.assertIn('_REQUEST = b"SNAPSHOT\\n"', source)
        self.assertIn("if request != _REQUEST:", source)
        self.assertIn("payload = empty_display()", source)
        self.assertIn("A same-UID hostile", source)
        self.assertIn("NOT sandboxing, production", source)
        self.assertNotIn("BEGIN", source)
        self.assertNotIn("RECOVER", source)
        self.assertNotIn("CANCEL", source)
        reader = read(READER)
        self.assertIn('snapshotProcess.command = [pythonPath, readerPath, "--json"]', reader)
        self.assertIn("read-only", reader)
        self.assertNotIn('["BEGIN"', reader)
        self.assertNotIn("requestSignIn(", reader)

    def test_current_cpuplus_remains_disabled_and_does_not_execute_v5(self):
        upper = read(CPU)
        bridge = read(BOUNDARY)
        proposal = read(PROPOSAL)
        request = read(REQUEST)
        broker = read(BROKER)
        self.assertIn("HostBoundary.offline()", upper)
        self.assertIn("available: upperSignIn.journey.canBeginSignIn", upper)
        self.assertIn("available: upperSignIn.signInFlow.canCancel", upper)
        self.assertIn("available: upperSignIn.signInFlow.canRetry", upper)
        self.assertNotIn("ConnectionsSignInIntentProposal.js", upper)
        self.assertNotIn("begin_login(", upper)
        self.assertNotIn("startLogin(", upper)
        self.assertIn("canBeginSignIn: false", bridge)
        self.assertIn("canCancel: false", bridge)
        self.assertIn("canRetry: false", bridge)
        self.assertIn("canDispatch: false", proposal)
        self.assertIn('authority: "NONE"', proposal)
        self.assertIn("readonly property bool hostAuthenticated: false", request)
        self.assertIn("readonly property bool canApprove: false", request)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)


if __name__ == "__main__":
    unittest.main()
