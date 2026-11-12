#!/usr/bin/env python3
"""C3e-AB: deny-only interpretation of bounded C4b real-guest CI markers.

This checks whether an UNTRUSTED, unsealed GitHub log excerpt claims every
required stage of the C4b Identity Silverblue test, including two-boot
rollback. It does not authenticate where the lines came from. A positive
*consistency* verdict CANNOT grant host, release-root, consent or sign-in
authority. The workflow/job conclusion is also caller supplied.
"""
from __future__ import annotations

import re

SCHEMA = "postapollo.connections.c3eab-c4b-identity-run-diagnostic.ci-v1"
MAX_BYTES = 65536
MAX_LINES = 200
MAX_LINE_BYTES = 1536
RUN_CONCLUSIONS = frozenset((
    "success", "failure", "cancelled", "timed_out", "startup_failure",
    "skipped", "action_required", "neutral",
))
EXIT_CODE = re.compile(r"C4B_ID_VM_PROCESS_EXIT // (0|[1-9][0-9]{0,4})\Z", re.ASCII)

# Names are copied from the CURRENT C4b-owned guest_identity_ostree_cycle.sh,
# guest_identity_service_probe.sh and run_official_silverblue_identity.sh.
# Preserve both actual guest phases AND the final host-side rollback marker.
# A partial guest run may satisfy confinement yet still fail the rollback.
REQUIRED_ORDER = (
    "C4B_ID_STAGE // initial",
    "C4B_ID_PASS // SIGNED_IDENTITY_RPM_VERIFIED_OFFLINE_BEFORE_LAYER",
    "C4B_ID_PASS // REAL_IDENTITY_RPM_OSTREE_PENDING_DEPLOYMENT",
    "C4B_ID_STAGE // layer_pending",
    "C4B_ID_PASS // REAL_SILVERBLUE_BOOTED_SIGNED_IDENTITY_RPM_INERT",
    "C4B_ID_SELINUX_STAGE // enforcing_state=Enforcing",
    "C4B_ID_SELINUX_OBSERVED // system_u:system_r:postapollo_identity_ci_t:s0",
    "C4B_ID_PASS // REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED",
    "C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_BEGIN",
    "C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_STATUS",
    "C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_CANCEL",
    "C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_RECOVER",
    "C4B_ID_PASS // KERNEL_PEER_PID_START_AND_SUPERVISOR_RECHECKED_FOR_FOUR_SIGNED_DENIALS",
    "C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE",
    "C4B_ID_PASS // DEDICATED_SELINUX_MODULE_REMOVED_AFTER_SERVICE_STOP",
    "C4B_ID_PASS // REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP",
    "C4B_ID_PASS // REAL_IDENTITY_SERVICE_PROBE_FINISHED_BEFORE_ROLLBACK",
    "C4B_ID_STAGE // rollback_pending",
    "C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED",
    "C4B_ID_PASS // TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED",
    "C4B_ID_PASS // REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK",
)
NEGATIVE = {
    "artifactOriginCryptographicallyAuthenticated": False,
    "githubWorkflowResultIndependentlyAuthenticated": False,
    "installedIdentityHostAuthenticated": False,
    "independentReleaseWitnessVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "credentialActionsEnabled": False,
    "canBeginSignIn": False,
    "productionAuthority": False,
}
_REQUIRED_SET = frozenset(REQUIRED_ORDER)


class Refused(ValueError):
    """Malformed diagnostic input; no production authority is possible."""


def _deny(code: str):
    raise Refused(code)


def _tokens(artifact: bytes):
    if type(artifact) is not bytes or not 1 <= len(artifact) <= MAX_BYTES:
        _deny("C4B_ARTIFACT_SIZE_REFUSED")
    if b"\0" in artifact or b"\r" in artifact or not artifact.endswith(b"\n"):
        _deny("C4B_ARTIFACT_DELIMITER_REFUSED")
    lines = artifact.split(b"\n")[:-1]
    if not 1 <= len(lines) <= MAX_LINES:
        _deny("C4B_ARTIFACT_LINE_COUNT_REFUSED")
    tokens = []
    for line in lines:
        if not 0 < len(line) <= MAX_LINE_BYTES:
            _deny("C4B_ARTIFACT_LINE_LENGTH_REFUSED")
        try:
            decoded = line.decode("ascii")
        except UnicodeError as exc:
            raise Refused("C4B_ARTIFACT_NON_ASCII_REFUSED") from exc
        offset = decoded.find("C4B_ID_")
        if offset == -1:
            # No C4b marker means no positive evidence. Such lines may be
            # harmless serial noise, but the artifact contract is marker-only.
            _deny("C4B_ARTIFACT_NON_MARKER_LINE_REFUSED")
        # The first C4B_ID_ tag is authoritative for DIAGNOSTIC parsing.
        # A nested marker in a journal/detail line cannot satisfy a PASS.
        marker = decoded[offset:].strip()
        if "\n" in marker or "\r" in marker:
            _deny("C4B_ARTIFACT_MARKER_DELIMITER_REFUSED")
        tokens.append(marker)
    return tokens


def assess_untrusted_markers(*, artifact: bytes,
                             caller_reported_workflow_conclusion: str):
    """Check C4b stage completeness without claiming authentic log origin.

    The workflow conclusion and artifact are independent-caller INPUTS only.
    Passing merely means that these untrusted inputs are mutually consistent.
    Do not use this return value in a production broker or login decision.
    """
    if (type(caller_reported_workflow_conclusion) is not str or
            caller_reported_workflow_conclusion not in RUN_CONCLUSIONS):
        _deny("CALLER_WORKFLOW_CONCLUSION_INVALID")
    lines = _tokens(artifact)
    failures = tuple(
        x for x in lines
        if "C4B_ID_FAIL //" in x or "C4B_ID_BLOCKED //" in x)
    exit_positions = [idx for idx, line in enumerate(lines)
                      if line.startswith("C4B_ID_VM_PROCESS_EXIT //")]
    if len(exit_positions) != 1 or exit_positions[0] != len(lines) - 1:
        _deny("C4B_VM_EXIT_MARKER_MISSING_DUPLICATE_OR_NONTERMINAL")
    exits = [EXIT_CODE.fullmatch(lines[exit_positions[0]])]
    if exits[0] is None:
        _deny("C4B_VM_EXIT_MARKER_MALFORMED")
    vm_exit = int(exits[0].group(1))
    if vm_exit > 255:
        _deny("C4B_VM_EXIT_OUT_OF_RANGE")
    # Duplicated console/heartbeat records may be repeated; the first
    # valid ordered subsequence is the only source of a completeness claim.
    progress = 0
    found = set()
    for token in lines:
        if token in _REQUIRED_SET:
            found.add(token)
        if progress < len(REQUIRED_ORDER) and token == REQUIRED_ORDER[progress]:
            progress += 1
    missing = [name for name in REQUIRED_ORDER if name not in found]
    ordered = progress == len(REQUIRED_ORDER)
    complete = (not failures and not missing and ordered and vm_exit == 0
                and caller_reported_workflow_conclusion == "success")
    return {
        "schema": SCHEMA,
        "diagnosticState": (
            "COMPLETE_MARKER_SEQUENCE_ONLY_NO_HOST_ATTESTATION"
            if complete else "INCOMPLETE_OR_FAILED_NO_HOST_ATTESTATION"
        ),
        "completeMarkerSequenceConsistentInCI": complete,
        "missingRequiredMarkers": missing,
        "requiredMarkerOrderSatisfied": ordered,
        "guestFailureMarkerObserved": bool(failures),
        "guestVmProcessExit": vm_exit,
        "callerReportedWorkflowConclusion": caller_reported_workflow_conclusion,
        **NEGATIVE,
    }


def require_complete_untrusted_markers(*, artifact: bytes,
                                       caller_reported_workflow_conclusion: str):
    """Refuse any partial/failed CI input. Success is STILL NOT HOST TRUST."""
    result = assess_untrusted_markers(
        artifact=artifact,
        caller_reported_workflow_conclusion=caller_reported_workflow_conclusion)
    if result["completeMarkerSequenceConsistentInCI"] is not True:
        _deny("C4B_INCOMPLETE_GUEST_ROLLBACK_OR_FAILED_CI")
    return result
