#!/usr/bin/env python3
"""Clock BG1-B2B19: kernel-paired native/QML observation, NEVER actuation.

Only a disposable native rehearsal can construct this witness. A signed
Clock native process and a separately pinned *synthetic stand-in* for
Quickshell connect to two real AF_UNIX sockets. SO_PEERPIDFD and a signed
Clock origin are checked both before and after final V2 fsync. No connected
socket or caller can supply signing trust, peer pins or source paths.

The stand-in is NOT a verified installed Quickshell process. In particular,
this module does not authenticate the native-to-QML receiving channel.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import sys


def _module(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().with_name(filename))
    if spec is None or spec.loader is None:
        raise RuntimeError("Required Clock witness unavailable")
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


Peer = _module("AlarmPeerIdentity.py", "clock_b2b19_peer")
Origin = _module("AlarmInstalledRoleTrustPreflight.py", "clock_b2b19_origin")
Final = _module("AlarmFinalV2SourceWitness.py", "clock_b2b19_source")
Bridge = _module("AlarmBridgeChallengeLedger.py", "clock_b2b19_one_use")


class Refused(ValueError):
    """Fixed non-sensitive refusal; no alarm data or trusted paths."""


NO_AUTHORITY = {
    "ok": False,
    "qmlSenderAuthenticated": False,
    "nativeToQmlChannelAuthenticated": False,
    "qmlInstalledSourceAuthenticated": False,
    "quickshellDrainActivated": False,
    "writerStopped": False,
    "releaseAcknowledged": False,
    "oldWriterRestartPrevented": False,
    "sourceExclusive": False,
    "finalRevisionDurablyLocked": False,
    "ownsRealAlarmFile": False,
    "canTransferOwnership": False,
    "canRing": False,
    "canNotify": False,
}


@dataclass(frozen=True, slots=True)
class NativePin:
    """Controller-provided signed Clock origin; NEVER from a socket frame."""
    pid: int
    ticks: int
    executable: str
    trust_directory: str
    pinned_root_sha256: str
    epoch: int
    sequence: int


@dataclass(frozen=True, slots=True)
class QmlProcessPin:
    """Independently pinned process identity, NOT signed QML origin."""
    pid: int
    ticks: int
    executable: str


def _native_pin(pin):
    if (type(pin) is not NativePin
            or type(pin.pid) is not int or pin.pid <= 1
            or type(pin.ticks) is not int or pin.ticks <= 0
            or type(pin.executable) is not str
            or not os.path.isabs(pin.executable)
            or type(pin.trust_directory) is not str
            or type(pin.pinned_root_sha256) is not str
            or not Origin.HEX.fullmatch(pin.pinned_root_sha256)
            or type(pin.epoch) is not int or pin.epoch < 1
            or type(pin.sequence) is not int or pin.sequence < 1):
        raise Refused("INDEPENDENT_NATIVE_PIN_REQUIRED")
    return pin


def _qml_pin(pin):
    if (type(pin) is not QmlProcessPin
            or type(pin.pid) is not int or pin.pid <= 1
            or type(pin.ticks) is not int or pin.ticks <= 0
            or type(pin.executable) is not str
            or not os.path.isabs(pin.executable)):
        raise Refused("INDEPENDENT_QML_PROCESS_PIN_REQUIRED")
    return pin


class ClockKernelPairedFinalWitness:
    """Two independent kernel peers and one pinned V2 sync, all deny-only."""

    def __init__(self, *, native_pin, qml_pin, source_path,
                 source_digest, source_uid, synthetic_only=False):
        if synthetic_only is not True:
            raise Refused("PRODUCTION_QML_CONTROL_NOT_IMPLEMENTED")
        self.native_pin = _native_pin(native_pin)
        self.qml_pin = _qml_pin(qml_pin)
        if self.native_pin.pid == self.qml_pin.pid:
            raise Refused("CLOCK_PEER_ROLES_NOT_SEPARATE")
        try:
            self.final = Final.ClockFinalV2SourceWitness(
                source_path=source_path, pinned_sha256=source_digest,
                expected_uid=source_uid, synthetic_only=True)
        except Final.Refused as exc:
            raise Refused("INDEPENDENT_FINAL_SOURCE_PIN_REQUIRED") from exc
        self.native = None
        self.qml = None
        self.challenge = Bridge.ClockBridgeChallengeLedger()

    def _signed_probe(self, connection, witness):
        pin = self.native_pin
        try:
            probe = Origin.ClockInstalledRoleTrustPreflight(
                trust_directory=pin.trust_directory,
                pinned_root_sha256=pin.pinned_root_sha256,
                expected_role="clock-ui-bridge",
                minimum_epoch=pin.epoch,
                minimum_sequence=pin.sequence,
                disposable_test_mode=True)
            observed = probe.inspect(
                connection, witness, expected_pid=pin.pid,
                expected_start_ticks=pin.ticks)
            if (observed["originObserved"] is not True
                    or observed["releaseEpoch"] != pin.epoch
                    or observed["releaseSequence"] < pin.sequence
                    or observed["roleAuthenticated"] is not False):
                raise Refused("SIGNED_NATIVE_ORIGIN_NOT_OBSERVED")
        except (Origin.Refused, Peer.Refused, OSError, ValueError) as exc:
            raise Refused("SIGNED_NATIVE_ORIGIN_NOT_OBSERVED") from exc

    @staticmethod
    def _capture(connection, pin):
        witness = None
        try:
            witness = Peer.capture(connection, pin.executable)
            if ((witness["pid"], witness["ticks"]) !=
                    (pin.pid, pin.ticks)):
                raise Refused("KERNEL_PEER_DOES_NOT_MATCH_PIN")
            return witness
        except (Peer.Refused, OSError) as exc:
            raise Refused("KERNEL_PEER_NOT_OBSERVED") from exc
        except BaseException:
            if witness is not None:
                Peer.close(witness)
            raise

    def connect_native(self, connection):
        if self.native is not None:
            raise Refused("SIGNED_NATIVE_ALREADY_CONNECTED")
        witness = self._capture(connection, self.native_pin)
        try:
            self._signed_probe(connection, witness)
            self.native = (connection, witness)
        except BaseException:
            Peer.close(witness)
            raise

    def connect_qml_standin(self, connection):
        if self.native is None:
            raise Refused("SIGNED_NATIVE_REQUIRED_FIRST")
        if self.qml is not None:
            raise Refused("QML_STANDIN_ALREADY_CONNECTED")
        witness = self._capture(connection, self.qml_pin)
        try:
            if witness["pid"] == self.native[1]["pid"]:
                raise Refused("CLOCK_PEER_ROLES_NOT_SEPARATE")
            self.qml = (connection, witness)
        except BaseException:
            Peer.close(witness)
            raise

    def _check(self):
        if self.native is None or self.qml is None:
            raise Refused("BOTH_PINNED_PEERS_REQUIRED")
        try:
            Peer.verify(*self.native, self.native_pin.executable)
            self._signed_probe(*self.native)
            Peer.verify(*self.qml, self.qml_pin.executable)
            if self.native[1]["pid"] == self.qml[1]["pid"]:
                raise Refused("CLOCK_PEER_ROLES_NOT_SEPARATE")
        except (Peer.Refused, Refused, Origin.Refused, OSError) as exc:
            raise Refused("CLOCK_PAIRED_PROCESS_CONTINUITY_LOST") from exc

    def _native_binding(self):
        self._check()
        try:
            retained = os.fstat(self.native[1]["pidfd"])
        except OSError as exc:
            raise Refused("PINNED_NATIVE_PIDFD_UNAVAILABLE") from exc
        pin = self.native_pin
        return (pin.pid, pin.ticks, pin.epoch,
                pin.pinned_root_sha256, retained.st_dev, retained.st_ino)

    def prepare_pair_challenge(self):
        # Synthetic-only one-use token. Not a QML delivery/authentication.
        try:
            return self.challenge.issue(self._native_binding())
        except Bridge.Refused as exc:
            raise Refused(str(exc)) from exc

    def acknowledge_pair_challenge(self, token):
        # Must revalidate both real OS peers before consuming the token.
        try:
            self.challenge.acknowledge(self._native_binding(), token)
        except Bridge.Refused as exc:
            raise Refused(str(exc)) from exc
        return {
            "oneUseNativeRoundTripObserved": True,
            **NO_AUTHORITY,
        }

    def inspect_pair(self):
        self._check()
        return {
            "signedNativeOriginObserved": True,
            "qmlKernelPeerObserved": True,
            "pairedProcessesAlive": True,
            "oneUseNativeRoundTripObserved": self.challenge.round_trip_observed,
            "fixtureOnly": True,
            **NO_AUTHORITY,
        }

    def inspect_final_candidate(self, *, candidate_generation,
                                expected_generation, candidate_digest):
        """Receive only comparison DATA, not an ownership decision.

        expected_generation and source digest must be trusted independently
        by a future controller; currently only synthetic test code invokes it.
        The incoming candidate's digest and generation never supply source
        pins. Even equal values and real fsync do not lock the old writer.
        """
        self._check()
        if not self.challenge.round_trip_observed:
            raise Refused("ONE_USE_NATIVE_ROUND_TRIP_REQUIRED")
        if (type(candidate_generation) is not int
                or type(expected_generation) is not int
                or not 0 < candidate_generation == expected_generation
                or type(candidate_digest) is not str
                or candidate_digest != self.final.pinned_sha256):
            raise Refused("FINAL_CANDIDATE_NOT_INDEPENDENTLY_BOUND")
        try:
            observed = self.final.observe()
        except (Final.Refused, OSError) as exc:
            raise Refused("FINAL_SOURCE_SYNC_NOT_OBSERVED") from exc
        self._check()
        if (observed["fileSyncObserved"] is not True
                or observed["parentDirectorySyncObserved"] is not True
                or observed["sourceExclusive"] is not False
                or observed["canTransferOwnership"] is not False):
            raise Refused("FINAL_SOURCE_SYNC_NOT_OBSERVED")
        return {
            "signedNativeOriginObserved": True,
            "qmlKernelPeerObserved": True,
            "pairedProcessesAlive": True,
            "candidateGenerationMatchesPin": True,
            "oneUseNativeRoundTripObserved": True,
            "fileSyncObserved": True,
            "parentDirectorySyncObserved": True,
            "fixtureOnly": True,
            **NO_AUTHORITY,
        }

    def close(self):
        self.challenge.clear()
        # The caller retains ownership of accepted sockets. This component
        # owns and closes only the kernel pidfd witnesses.
        for name in ("native", "qml"):
            stored = getattr(self, name)
            if stored is not None:
                Peer.close(stored[1])
                setattr(self, name, None)
