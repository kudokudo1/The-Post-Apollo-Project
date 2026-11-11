"""Identity-owned mandatory composite native gateway gate (CI contract V1).

This is a *client-side* adapter, never a QML credential or authorization API.
A plain signed receipt or the optional origin check in the experimental client
is insufficient: this adapter requires BOTH independently constructed identity
origin and installed-package/supervisor witnesses, plus connected peer and seat
checks. Existing SignedIdentityCommandClient rechecks these before send and
after signed receipt verification, on EVERY command.

CURRENT SCOPE: InstalledGatewayWitness is explicitly a disposable dpkg/CI
witness. No production Silverblue release, independent key custody, logind
session check or genuine C5 operator intent is implemented here. Do not use
this adapter to enable CPU++ SIGN IN. Production needs separately reviewed
C4b/C5 admission interfaces; no test root, key, PID or seat callback may be
promoted to production authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from collections.abc import Callable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from desktop_command_gateway_v0 import KernelPeer
from desktop_signed_command_client_v0 import (
    HostCommandObservation, SignedIdentityCommandClient,
)
from installed_gateway_witness_v1 import InstalledGatewayWitness
from signed_gateway_origin_probe_v0 import SignedGatewayOriginProbe


class NativeAdapterRefused(ValueError):
    """Independent release/process/key/seat prerequisites were not provided."""


class InstalledIdentityCommandAdapterV1:
    """Mandatory combined read-only process and signed-receipt gate.

    The low-level signed client intentionally remains compatible with older
    isolated tests. The *adapter* cannot omit or replace either concrete
    Identity witness with a permissive callback. Callers supply independent
    peer and active-seat verifiers; the adapter never creates consent or grants.
    """

    def __init__(
        self, *,
        socket_path: Path,
        pinned_host_public_key: Ed25519PublicKey,
        origin_probe: SignedGatewayOriginProbe,
        installed_witness: InstalledGatewayWitness,
        trusted_server_peer: Callable[[KernelPeer], bool],
        active_seat: Callable[[], bool],
    ) -> None:
        if (type(origin_probe) is not SignedGatewayOriginProbe
                or type(installed_witness) is not InstalledGatewayWitness
                or not isinstance(pinned_host_public_key, Ed25519PublicKey)
                or not callable(trusted_server_peer)
                or not callable(active_seat)):
            raise NativeAdapterRefused(
                "Mandatory Identity origin, installed witness, peer and seat missing"
            )
        # The origin probe's test-only script mode must never back an
        # installed-native adapter. The installed witness itself is CI-only.
        if origin_probe._disposable:
            raise NativeAdapterRefused("Disposable script probe cannot attest installed host")

        policy = origin_probe._policy
        release = installed_witness.manifest
        receipt_key = pinned_host_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        fingerprint = hashlib.sha256(receipt_key).hexdigest()

        # Both signed releases must describe the *same* connected process,
        # installed entrypoint bytes, release version and receipt signer.
        # These are construction-time checks, not substitutes for on-command
        # remeasurement. Release-root custody and rollback policy are external.
        if (
            origin_probe._expected_pid != installed_witness.pid
            or origin_probe._expected_start_ticks != installed_witness.ticks
            or policy["uid"] != installed_witness.uid
            or policy["gid"] != installed_witness.gid
            or policy["releaseEpoch"] != release["epoch"]
            or policy["releaseSequence"] != release["sequence"]
            or release["files"].get(policy["entrypointPath"]) !=
                policy["entrypointSha256"]
            or fingerprint != policy["receiptKeySha256"]
            or fingerprint != release["receiptKeySha256"]
        ):
            raise NativeAdapterRefused(
                "Independent installed gateway observations disagree"
            )

        # Deliberately NO optional enrolled_origin_consistent argument in
        # this adapter's public constructor. A UI cannot opt out of either
        # signed-release/package witness while keeping signed status flowing.
        def complete_origin(peer: KernelPeer) -> bool:
            return (origin_probe.consistent(peer) is True
                    and installed_witness.consistent(peer) is True)

        self._client = SignedIdentityCommandClient(
            socket_path=socket_path,
            pinned_host_public_key=pinned_host_public_key,
            trusted_server_peer=trusted_server_peer,
            active_seat=active_seat,
            enrolled_origin_consistent=complete_origin,
        )

    @property
    def faulted(self) -> bool:
        return self._client.faulted

    def begin(self) -> HostCommandObservation:
        return self._client.begin()

    def status(self) -> HostCommandObservation:
        return self._client.status()

    def cancel(self) -> HostCommandObservation:
        return self._client.cancel()

    def recover(self) -> HostCommandObservation:
        return self._client.recover()
