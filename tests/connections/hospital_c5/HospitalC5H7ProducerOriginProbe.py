#!/usr/bin/env python3
"""Hospital C5-H7 disposable native consent-producer origin preflight.

THIS FILE IS TEST-ONLY. It reuses the real C5 issuer's Linux packet-credential
read helper, but has no installed socket, policy, signer, root, agent, key,
display surface, challenge ledger or admission capability. A claimed receipt
is never promoted to actual operator consent. No production module imports it.
"""
from __future__ import annotations

import base64
import re

import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S

SCHEMA = "postapollo.hospital.c5h7.untrusted-producer-packet.v1"
REVIEW_SCHEMA = "postapollo.hospital.c5h6.exact-room-review.v2"
AUDIENCE = "postapollo.hospital.exact-room-consent"
MAX_FRAME = 4096
FIELDS = frozenset((
    "schema", "reviewSchema", "audience", "reviewDigest", "requestNonce",
    "writerInstance", "action", "roomId", "operatorUid", "seatId", "hostId",
    "producerPid", "producerUid", "producerGid", "producerStartTicks",
    "producerReleaseDigest", "historyHeadDigest", "claimedShown",
    "claimedConfirmed", "issuedAt", "shownAt", "confirmedAt", "expiresAt",
))
BASE64_NONCE = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)


def _nonce_is_canonical(value):
    if type(value) is not str or BASE64_NONCE.fullmatch(value) is None:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except (ValueError, TypeError):
        return False
    return (len(decoded) == 32
            and base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == value)


def inspect_untrusted_packet(raw, *, observed_peer, now):
    """Report only untrusted matching observations. Never return authority.

    observed_peer is (pid, uid, gid, start_ticks) from the actual native
    verifier, not a field in the packet. This CI helper does not authenticate
    the source of the supplied tuple; its caller can be a test fixture.
    """
    if (type(observed_peer) is not tuple or len(observed_peer) != 4
            or any(type(x) is not int for x in observed_peer)
            or observed_peer[0] <= 1 or observed_peer[1] <= 0
            or observed_peer[2] < 0 or observed_peer[3] <= 0
            or type(now) is not int or now <= 0):
        C.deny("C5H7_KERNEL_OBSERVATION_UNTRUSTED")

    value = C.parse_exact(raw, FIELDS, MAX_FRAME)
    if (value["schema"] != SCHEMA
            or value["reviewSchema"] != REVIEW_SCHEMA
            or value["audience"] != AUDIENCE
            or not _nonce_is_canonical(value["requestNonce"])
            or type(value["writerInstance"]) is not str
            or C.ID.fullmatch(value["writerInstance"]) is None
            or type(value["action"]) is not str
            or value["action"] not in ("TRASH", "RESTORE")
            or type(value["roomId"]) is not str
            or C.ID.fullmatch(value["roomId"]) is None
            or type(value["seatId"]) is not str
            or C.ID.fullmatch(value["seatId"]) is None
            or type(value["operatorUid"]) is not int
            or value["operatorUid"] <= 0
            or type(value["producerPid"]) is not int
            or value["producerPid"] <= 1
            or type(value["producerUid"]) is not int
            or value["producerUid"] <= 0
            or type(value["producerGid"]) is not int
            or value["producerGid"] < 0
            or type(value["producerStartTicks"]) is not int
            or value["producerStartTicks"] <= 0
            or any(type(value[k]) is not str
                   or C.SHA.fullmatch(value[k]) is None for k in (
                       "reviewDigest", "hostId", "producerReleaseDigest",
                       "historyHeadDigest"))
            or type(value["claimedShown"]) is not bool
            or type(value["claimedConfirmed"]) is not bool
            or any(type(value[k]) is not int for k in (
                "issuedAt", "shownAt", "confirmedAt", "expiresAt"))):
        C.deny("C5H7_CANDIDATE_SHAPE_REFUSED")

    source_match = (
        (value["producerPid"], value["producerUid"], value["producerGid"],
         value["producerStartTicks"]) == observed_peer
    )
    chronology = (
        value["issuedAt"] <= value["shownAt"] <= value["confirmedAt"] <= now
        < value["expiresAt"] <= value["issuedAt"] + 60
    )
    claim_match = source_match and chronology and (
        value["claimedShown"] is True
        and value["claimedConfirmed"] is True
    )
    return {
        "schema": "postapollo.hospital.c5h7.transport-diagnostic.v1",
        "status": ("UNTRUSTED_CLAIM_MATCHES_ORIGIN_HOLD" if claim_match
                   else "CROSSED_OR_STALE_CLAIM_HOLD"),
        "kernelPeerTupleMatchesClaim": source_match,
        "claimedChronologyFits": chronology,
        "claimedConfirmationFits": claim_match,
        "independentProducerReleaseEnrolled": False,
        "installedExecutableAuthenticated": False,
        "realDisplayObserved": False,
        "activeUnlockedSeatAuthenticated": False,
        "genuineOperatorGestureVerified": False,
        "rootAndRevocationCustodyVerified": False,
        "independentOneUseHistoryVerified": False,
        "protectedPxSourceAdmissionVerified": False,
        "canSatisfyNativeIssuerHardGate": False,
        "canLoadPrivateSigner": False,
        "canCommitHospitalRoom": False,
        "productionAuthorized": False,
        "safeActions": [],
    }


def receive_candidate_for_ci(sock, *, observed_peer, now):
    """Use existing C5 per-packet SCM_CREDENTIALS guard before diagnosis.

    This is NOT a listener, service endpoint, trusted process-enrollment
    check, active-seat check or approval. The caller must have an already
    connected disposable SOCK_SEQPACKET socket with SO_PASSCRED enabled
    BEFORE the producer sends its packet.
    """
    raw = S._packet_recv(sock, expected_sender=observed_peer[:3])
    return inspect_untrusted_packet(raw, observed_peer=observed_peer, now=now)


def authorize_human_consent(*_args, **_kwargs):
    C.deny("C5H7_INDEPENDENT_NATIVE_CONSENT_PRODUCER_NOT_ENROLLED")
