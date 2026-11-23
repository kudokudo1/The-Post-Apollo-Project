#!/usr/bin/env python3
"""C5-H5 read-only SOURCE inventory of Hospital authorization entrypoints.

No execution of QML, PX, SQLite, issuer, Polkit, socket or workstation code.
Inputs are local checkout bytes including a separately pinned PX draft.
This recognizes known route tokens; it cannot certify all installed writers,
runtime routing, complete code execution or production authority.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re

LEGACY_PREFIXES = (
    ".local/share/post-apollo-dev-runtime/bin/px",
    ".local/bin/px",
)
LEGACY_RE = re.compile(r"\.local/(?:share/post-apollo-dev-runtime/bin/|bin/)px\b")
NATIVE_REQ = "/usr/libexec/post-apollo/hospital/hospital-room-request"
NATIVE_READ = "/usr/libexec/post-apollo/hospital/hospital-room-read"
EXPECTED_LEGACY = frozenset(
    "services/hospital/" + name + ".qml" for name in (
        "HospitalAssignmentService",
        "HospitalAuditService",
        "HospitalCertificationDriftService",
        "HospitalChartService",
        "HospitalDoctorNameService",
        "HospitalDoctorRuntimeService",
        "HospitalDoctorSuccessionCapabilityService",
        "HospitalPersistentDispatchService",
        "HospitalProviderService",
        "HospitalResponsibilityService",
        "HospitalRoomCheckpointService",
        "HospitalRoomContinuityService",
        "HospitalRoomConversationAdapter",
        "HospitalRoomNameService",
        "HospitalRoomReportCatalogService",
        "HospitalRoomReportService",
        "HospitalRoomService",
        "HospitalWorkerAttachmentActionService",
        "HospitalWorkerAttachmentPreviewService",
        "HospitalWorkerTranscriptService",
        "HospitalWorkforceRoomCreateService",
    )
)
EXPECTED_NATIVE = {
    "services/hospital/HospitalRoomLifecycleService.qml": frozenset(("request", "read")),
    "services/hospital/HospitalRoomBinService.qml": frozenset(("read",)),
    "services/hospital/HospitalDoctorService.qml": frozenset(("read",)),
}
APP_REQUIRED = frozenset((
    "services/hospital/native/hospital_room_request_client.c",
    "services/hospital/native/hospital_room_read_client.py",
    "services/connections/hospital/HospitalNativeIssuerService.py",
))
PX_REQUIRED = frozenset((
    "bin/px",
    "bin/px-hospital-store",
    "bin/px_hospital_room_writer.py",
    "bin/px_hospital_protected_store_bridge.py",
    "bin/px_hospital_connections_consent.py",
))
# These literal privileged routes must not appear in *desktop Hospital UI*
# source. This is a token tripwire, not a complete language/call-graph proof.
DIRECT_UI_TOKENS = (
    "px-hospital-store",
    "px-hospital-room-writerd",
    "px-hospital-consent-writerd",
    "store-command",
    '"room-lifecycle-trash"',
    '"room-lifecycle-restore"',
    "/run/post-apollo/hospital/px-writer.sock",
    "sqlite3.connect(",
)


class SourceHold(ValueError):
    pass


def hold(code: str):
    raise SourceHold("HOSPITAL_C5H5_SOURCE_HOLD // " + code)


def collect_sources(app_root: Path, px_root: Path):
    """Read only repository text; no scripts, imports or host processes run."""
    if not isinstance(app_root, Path) or not isinstance(px_root, Path):
        hold("ROOTS_MUST_BE_PATHS")
    services = app_root / "services/hospital"
    widgets = app_root / "widgets"
    if not services.is_dir() or not widgets.is_dir():
        hold("APPLICATION_CHECKOUT_UNAVAILABLE")
    files = (
        list(services.rglob("*.qml"))
        + list(services.rglob("*.js"))
        + list(widgets.glob("Hospital*.qml"))
    )
    if len(files) < 30:
        hold("HOSPITAL_UI_INVENTORY_INCOMPLETE")
    paths = set(str(p.relative_to(app_root)) for p in files)
    if len(paths) != len(files):
        hold("DUPLICATE_UI_SOURCE_PATH")
    paths.update(APP_REQUIRED)
    ui = {}
    for name in sorted(paths):
        try:
            ui[name] = (app_root / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SourceHold("HOSPITAL_C5H5_SOURCE_HOLD // APPLICATION_SOURCE_MISSING") from exc
    px = {}
    for name in sorted(PX_REQUIRED):
        try:
            px[name] = (px_root / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SourceHold("HOSPITAL_C5H5_SOURCE_HOLD // PINNED_PX_SOURCE_MISSING") from exc
    return ui, px


def _issuer_hard_gate(source: str):
    """Require actual AST body to contain only the unconditional denial."""
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        raise SourceHold("HOSPITAL_C5H5_SOURCE_HOLD // ISSUER_SYNTAX") from exc
    functions = {
        node.name: node for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    method = functions.get("_require_independent_room_consent")
    if not isinstance(method, ast.FunctionDef):
        hold("INDEPENDENT_CONSENT_GATE_MISSING")
    body = list(method.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Expr):
        hold("CONSENT_GATE_NOT_UNCONDITIONAL_DENIAL")
    call = body[0].value
    if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute)
            or not isinstance(call.func.value, ast.Name)
            or call.func.value.id != "C" or call.func.attr != "deny"
            or len(call.args) != 1 or call.keywords
            or not isinstance(call.args[0], ast.Constant)
            or call.args[0].value != "INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE"):
        hold("CONSENT_GATE_NOT_UNCONDITIONAL_DENIAL")
    step = functions.get("_native_step")
    if not isinstance(step, ast.FunctionDef):
        hold("NATIVE_SIGNING_ENTRYPOINT_MISSING")
    statements = source.split("def _native_step(client, policy):", 1)
    if len(statements) != 2:
        hold("NATIVE_STEP_CHANGED")
    text = statements[1]
    tokens = (
        "_polkit_approve(request, prepared, peer, first_seat)",
        "_require_independent_room_consent(request, prepared, peer, first_seat)",
        "key = C.load_installed_key()",
        "signed = C.sign_px_grant(",
        '"kind": "commit"',
    )
    offsets = [text.find(token) for token in tokens]
    if any(n < 0 for n in offsets) or offsets != sorted(offsets):
        hold("NATIVE_SIGNING_GATE_ORDER_CHANGED")


def audit_texts(application: dict[str, str], px_source: dict[str, str]):
    """Reject unknown or lost route tokens and ALWAYS report release HOLD."""
    if type(application) is not dict or type(px_source) is not dict:
        hold("UNTRUSTED_SOURCE_MAP")
    required = set(EXPECTED_LEGACY) | set(EXPECTED_NATIVE) | set(APP_REQUIRED)
    if not required <= set(application) or not PX_REQUIRED <= set(px_source):
        hold("MISSING_REQUIRED_REPOSITORY_SOURCE")
    if any(type(p) is not str or type(s) is not str for p, s in application.items()):
        hold("MALFORMED_APPLICATION_SOURCE_MAP")
    if any(type(p) is not str or type(s) is not str for p, s in px_source.items()):
        hold("MALFORMED_PX_SOURCE_MAP")

    ui_sources = {
        p: value for p, value in application.items()
        if (p.startswith("services/hospital/")
            and (p.endswith(".qml") or p.endswith(".js")))
        or (p.startswith("widgets/Hospital") and p.endswith(".qml"))
    }
    if len(ui_sources) < 30:
        hold("HOSPITAL_UI_INVENTORY_INCOMPLETE")
    legacy = frozenset(p for p, s in ui_sources.items() if LEGACY_RE.search(s))
    native = {
        p: frozenset(
            operation for operation, marker in
            (("request", NATIVE_REQ), ("read", NATIVE_READ))
            if marker in s
        ) for p, s in ui_sources.items()
        if NATIVE_REQ in s or NATIVE_READ in s
    }
    if legacy != EXPECTED_LEGACY:
        hold("UNRECONCILED_LEGACY_DESKTOP_PX_ENTRYPOINTS")
    if native != EXPECTED_NATIVE:
        hold("UNRECONCILED_NATIVE_HOSPITAL_UI_ENTRYPOINTS")
    for path, source in ui_sources.items():
        if any(token in source for token in DIRECT_UI_TOKENS):
            hold("DIRECT_PRIVILEGED_HOSPITAL_UI_ROUTE")
    lifecycle = application["services/hospital/HospitalRoomLifecycleService.qml"]
    for token in (
        "executeProcess.exec([nativeClientPath, action, room]);",
        'payload.status !== "COMMITTED"',
        'payload.action !== root.pendingAction',
        'payload.roomId !== root.pendingRoomId',
        "payload.originalPreserved !== true",
        "payload.burnAllowed !== false",
    ):
        if token not in lifecycle:
            hold("NATIVE_ROOM_REQUEST_OR_RECEIPT_GUARD_MISSING")
    doctor = application["services/hospital/HospitalDoctorService.qml"]
    if ('process.exec([nativeReaderPath, "doctor-directory"]);' not in doctor
            or "readonly property bool protectedDoctorWritesReady: false" not in doctor):
        hold("DOCTOR_READ_ONLY_CUTOVER_CHANGED")
    bin_source = application["services/hospital/HospitalRoomBinService.qml"]
    if NATIVE_READ not in bin_source or "item.burnAllowed === false" not in bin_source:
        hold("NATIVE_HOSPITAL_BIN_NO_BURN_GUARD_MISSING")

    request = application["services/hospital/native/hospital_room_request_client.c"]
    if ('#define CLIENT_PATH "' + NATIVE_REQ + '"' not in request
            or '#define ISSUER_SOCKET "/run/post-apollo/hospital/issuer.sock"' not in request):
        hold("FIXED_NATIVE_REQUEST_CLIENT_IDENTITY_CHANGED")
    reader = application["services/hospital/native/hospital_room_read_client.py"]
    if (NATIVE_READ not in reader or "SO_PEERCRED" not in reader):
        hold("FIXED_NATIVE_READER_IDENTITY_CHANGED")
    _issuer_hard_gate(application["services/connections/hospital/HospitalNativeIssuerService.py"])

    dispatcher = px_source["bin/px"]
    if (dispatcher.count('python3 "$ROOT/bin/px-hospital-store"') != 4
            or "hospital)" not in dispatcher):
        hold("PX_LEGACY_DISPATCHER_CHANGED")
    legacy_store = px_source["bin/px-hospital-store"]
    beginning = legacy_store.find("def connect()")
    ending = legacy_store.find("def current_schema_version(", beginning)
    if beginning < 0 or ending < 0:
        hold("PX_LEGACY_CONNECTOR_MISSING")
    connector = legacy_store[beginning:ending]
    if (not ("refuse_legacy_store_after_cutover()" in connector
             and "sqlite3.connect(" in connector
             and connector.index("refuse_legacy_store_after_cutover()")
             < connector.index("sqlite3.connect("))
            or "/etc/post-apollo/hospital/legacy-store-cutover.v1" not in legacy_store
            or "LEGACY_CUTOVER_MARKER.lstat()" not in legacy_store):
        hold("PX_LEGACY_CUTOVER_FENCE_CHANGED")
    writer = px_source["bin/px_hospital_room_writer.py"]
    if ('if action == "store-command" and peer_uid != self.runtime_uid:' not in writer
            or "socket.SO_PEERCRED" not in writer):
        hold("PROTECTED_PX_RUNTIME_UID_FENCE_CHANGED")
    bridge = px_source["bin/px_hospital_protected_store_bridge.py"]
    if ("READ_COMMANDS = frozenset((" not in bridge
            or "WRITE_COMMANDS = frozenset((" not in bridge
            or "EXCLUDED_COMMANDS = frozenset((" not in bridge):
        hold("PROTECTED_PX_COMMAND_ALLOWLIST_MISSING")
    exclusion = bridge.split("EXCLUDED_COMMANDS = frozenset((", 1)[1].split("))", 1)[0]
    for command in (
        '"room-lifecycle-trash"', '"room-lifecycle-restore"'
    ):
        if command not in exclusion:
            hold("ROOM_LIFECYCLE_MUTATION_ENTERED_GENERIC_PX_BRIDGE")
    consent = px_source["bin/px_hospital_connections_consent.py"]
    for token in (
        'CONSENT_SOCKET = Path("/run/post-apollo/hospital/px-writer.sock")',
        "signedGrant", "ROOT_ISSUER_ONLY", "lifecycle.transition(",
    ):
        if token not in consent:
            hold("PROTECTED_PX_CONSENT_WRITER_SOURCE_CHANGED")

    return {
        "schema": "postapollo.connections.hospital-c5h5-source-entrypoint-audit.v1",
        "sourceOnly": True,
        "legacyDesktopPxServiceCount": len(legacy),
        "legacyDesktopPxServices": sorted(legacy),
        "nativeHospitalUiServiceCount": len(native),
        "nativeHospitalUiServices": {
            name: sorted(actions) for name, actions in sorted(native.items())
        },
        "pxDirectLegacyStoreCallSites": 4,
        "protectedIssuerHardConsentHoldObserved": True,
        "sourceRouteTokensReconciled": True,
        "allWriterCompatibilityVerified": False,
        "allLegacyProcessesFenced": False,
        "installedHostObserved": False,
        "independentHumanConsentVerified": False,
        "protectedPxProductionWriterVerified": False,
        "productionAuthorized": False,
        "safeActions": [],
        "status": "UNMIGRATED_WRITER_ENTRYPOINTS_HOLD",
    }
