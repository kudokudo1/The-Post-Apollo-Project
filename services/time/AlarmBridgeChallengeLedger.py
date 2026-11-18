#!/usr/bin/env python3
"""B2B17: single-use signed-bridge socket round-trip, NEVER a writer grant.

This is supervisor-memory-only preparatory evidence. A successful challenge
does not authenticate the QML engine, drain FileView, fsync a revision, fence
Quickshell restart, transfer ownership, ring, or notify. Production issuance
is intentionally disabled by the owning native supervisor.
"""
from __future__ import annotations

import re
import secrets
import time

HEX64 = re.compile(r"^[0-9a-f]{64}$")
TTL_SECONDS = 20.0


class Refused(ValueError):
    """Non-sensitive refusal suitable for socket responses."""


def _binding(key):
    """Process identity pinned OUTSIDE the untrusted socket request."""
    if (type(key) is not tuple or len(key) != 6
            or any(type(x) is not int or x <= 0 for x in
                   (key[0], key[1], key[2], key[4], key[5]))
            or type(key[3]) is not str or not HEX64.fullmatch(key[3])):
        raise Refused("CLOCK_BRIDGE_PEER_NOT_PINNED")
    return key


class ClockBridgeChallengeLedger:
    """One challenge for one pinned kernel process, one time per lifecycle."""

    def __init__(self):
        self._ever_issued = False
        self._pending = None
        self._acknowledged = False

    def issue(self, bound_process):
        key = _binding(bound_process)
        if self._ever_issued:
            raise Refused("CLOCK_BRIDGE_CHALLENGE_ALREADY_ISSUED")
        challenge = secrets.token_hex(32)
        self._pending = (key, challenge, time.monotonic() + TTL_SECONDS)
        self._ever_issued = True
        return challenge

    def acknowledge(self, bound_process, challenge):
        key = _binding(bound_process)
        # A failed attempt consumes the outstanding challenge too. No
        # guessing retries, fallback to a different process, or resurrection.
        pending = self._pending
        self._pending = None
        if pending is None:
            raise Refused("CLOCK_BRIDGE_CHALLENGE_NOT_PENDING")
        expected_key, expected_challenge, deadline = pending
        if time.monotonic() >= deadline:
            raise Refused("CLOCK_BRIDGE_CHALLENGE_EXPIRED")
        if (type(challenge) is not str or not HEX64.fullmatch(challenge)
                or not secrets.compare_digest(challenge, expected_challenge)):
            raise Refused("CLOCK_BRIDGE_CHALLENGE_MISMATCH")
        if not secrets.compare_digest(
                repr(key).encode("utf-8"), repr(expected_key).encode("utf-8")):
            raise Refused("CLOCK_BRIDGE_PEER_CHANGED")
        self._acknowledged = True
        return True

    def clear(self):
        self._pending = None

    @property
    def round_trip_observed(self):
        return self._acknowledged
