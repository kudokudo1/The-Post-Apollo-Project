#!/usr/bin/env python3
"""BG1-B2B7: compose independent signed *observations* for one old writer.

Disposable-only preflight. Neither an observed signed process origin nor its
signed challenge response can authorize a real Quickshell pause, claim owner
rights, write the V2 alarm document, ring or notify.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _clock_component(name, tag):
    path = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(tag, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing Clock component: " + name)
    module = importlib.util.module_from_spec(spec)
    # dataclasses on Python 3.12 require module lookup in sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


Role = _clock_component("AlarmSignedRoleOrigin", "clock_b2b7_origin")
Receipt = _clock_component("AlarmSignedWriterReleaseFixture", "clock_b2b7_receipt")


class Refused(ValueError):
    """A fixed non-private reason for failing a signed role/response chain."""


class RoleBoundReleasePreflight:
    """Bind two signed, denied-by-default observations to one live peer.

    Construction accepts only the audited experimental role-origin probe
    and the disposable signed-receipt fixture. The same kernel peer, role,
    epoch, sequence, interpreter, uid/gid and independently pinned PID/start
    must match in BOTH policies. Each stage rechecks signed executable
    identity; callers cannot substitute an arbitrary "verified" dict.
    """

    def __init__(self, *, role_probe, signed_receipt_fixture,
                 synthetic_only=False):
        if (synthetic_only is not True
                or type(role_probe) is not Role.SignedClockRoleProbe
                or type(signed_receipt_fixture) is not Receipt.SignedWriterReleaseFixture
                or role_probe._disposable is not True):
            raise Refused("DISPOSABLE_SIGNED_ROLE_CHAIN_ONLY")
        origin = role_probe._policy
        release = signed_receipt_fixture.policy
        if (origin["role"] != "clock-ui-bridge"
                or release["role"] != "clock-ui-bridge"
                or (origin["releaseEpoch"], origin["releaseSequence"])
                    != (release["releaseEpoch"], release["releaseSequence"])
                or origin["interpreterPath"] != release["interpreterPath"]
                or origin["uid"] != release["uid"]
                or origin["gid"] != release["gid"]
                or role_probe._expected_pid != signed_receipt_fixture.expected_pid
                or role_probe._expected_ticks != signed_receipt_fixture.expected_ticks):
            raise Refused("SIGNED_ROLE_RELEASE_PINS_MISMATCH")
        self._origin = role_probe
        self._release = signed_receipt_fixture

    def _same_live_origin(self, connection, witness):
        try:
            observed = self._origin.inspect(connection, witness)
        except (Role.Refused, OSError, ValueError) as exc:
            raise Refused("SIGNED_ORIGIN_LIFETIME_REFUSED") from exc
        if (type(observed) is not Role.ClockRoleOriginObservation
                or observed.role != "clock-ui-bridge"
                or observed.observed_pid != self._release.expected_pid
                or (observed.release_epoch, observed.release_sequence)
                    != (self._release.policy["releaseEpoch"],
                        self._release.policy["releaseSequence"])
                or observed.signature_verified is not True
                or observed.process_verified is not True
                or observed.role_authenticated is not False
                or observed.can_write_alarm_file is not False
                or observed.can_ring is not False
                or observed.can_notify is not False):
            raise Refused("ORIGIN_OBSERVATION_NOT_DENY_ONLY")
        return observed

    def issue_observation(self, connection, witness, *,
                          expected_source_digest, old_epoch, new_epoch):
        # The role inspection is NOT authorization. Real alarmFile writes
        # remain owned by the unchanged Quickshell singleton.
        self._same_live_origin(connection, witness)
        try:
            issued = self._release.issue(
                connection, witness,
                expected_source_digest=expected_source_digest,
                old_epoch=old_epoch, new_epoch=new_epoch)
        except (Receipt.Refused, OSError, ValueError) as exc:
            raise Refused("SIGNED_RELEASE_CHALLENGE_REFUSED") from exc
        self._same_live_origin(connection, witness)
        return {
            "challenge": issued["challenge"],
            "sourceDigest": issued["sourceDigest"],
            "oldEpoch": issued["oldEpoch"],
            "newEpoch": issued["newEpoch"],
            "signedRoleObserved": True,
            "writerStopped": False,
            "releaseAcknowledged": False,
            "canTransferOwnership": False,
            "canRing": False,
            "canNotify": False,
        }

    def observe_reply(self, connection, witness, *,
                      signed_reply, signature):
        # Repeat the full signed executable hash/argv/kernel PID witness
        # BEFORE and AFTER consuming the 1-use signed challenge.
        self._same_live_origin(connection, witness)
        try:
            observed = self._release.observe_signed_reply(
                connection, witness, signed_reply=signed_reply,
                signature=signature)
        except (Receipt.Refused, OSError, ValueError) as exc:
            raise Refused("SIGNED_RELEASE_REPLY_REFUSED") from exc
        self._same_live_origin(connection, witness)
        if (observed.get("signatureObserved") is not True
                or observed.get("independentlyPinnedSignerMatched") is not True
                or observed.get("peerProcessMatched") is not True
                or observed.get("writerStopped") is not False
                or observed.get("releaseAcknowledged") is not False
                or observed.get("canTransferOwnership") is not False
                or observed.get("ownsRealAlarmFile") is not False
                or observed.get("canRing") is not False
                or observed.get("canNotify") is not False):
            raise Refused("SIGNED_REPLY_ESCALATED_AUTHORITY")
        return {
            "signedRoleObserved": True,
            "signatureObserved": True,
            "sameKernelPeer": True,
            "roleAuthenticated": False,
            "writerStopped": False,
            "releaseAcknowledged": False,
            "canTransferOwnership": False,
            "ownsRealAlarmFile": False,
            "canRing": False,
            "canNotify": False,
        }
