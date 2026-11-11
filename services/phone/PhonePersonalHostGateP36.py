"""P36 // Fixture-only one-action Personal contact vault coordination.

This is deliberately NOT a production authenticated host. Its injected
observer/gesture callbacks and dataclasses are forgeable by same-user Python,
so they MUST NOT be exported to QML, D-Bus, CLI, web, or real iPhone records.
The fixture demonstrates where a future privileged host MUST attest the
session, live BlueFerry owner, current contacts.read consent, and human action
before obtaining an encryption key, and recheck all of them before a write.

Key lookups are external, read-only, and do NOT grant permission by themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable

import PhonePersonalContactIdentity as Identity
import PhonePersonalContactVault as Vault

REF = re.compile(r"^[A-Za-z0-9_-]{12,64}$")
OWNER = re.compile(r"^:[0-9]+\.[0-9]+$")
INTENT = re.compile(r"^[0-9a-f]{32}$")
ACTIONS = frozenset({"LINK", "FAVORITE", "NOTE", "UNLINK"})


class FixtureRefused(Exception):
    """Content-free refusal; no contact, key, profile, note or token leaks."""


def _deny() -> None:
    raise FixtureRefused("P36_UNAUTHORIZED_OR_UNAVAILABLE")


@dataclass(frozen=True, slots=True)
class ObservedFixture:
    """Made by test host, NOT an OS-signed credential or permission proof."""
    profile: str
    provider_owner: str
    session: str
    snapshot_epoch: int
    expires_at: int
    personal_scope: bool
    contacts_approved: bool
    device_connected: bool
    cards: tuple[dict, ...]


@dataclass(frozen=True, slots=True)
class ActionFixture:
    """Test intent, NOT an authentic user gesture from a UI."""
    action: str
    selected_row: str
    expected_revision: int
    nonce: str
    favorite: bool | None = None
    note: str | None = None


def _valid_state(state: object, now: int) -> bool:
    return (
        type(state) is ObservedFixture
        and type(now) is int and now >= 0
        and type(state.profile) is str
        and Identity.PROFILE.fullmatch(state.profile) is not None
        and type(state.provider_owner) is str
        and OWNER.fullmatch(state.provider_owner) is not None
        and type(state.session) is str and REF.fullmatch(state.session) is not None
        and type(state.snapshot_epoch) is int and state.snapshot_epoch >= 0
        and type(state.expires_at) is int and now < state.expires_at
        and state.personal_scope is True and state.contacts_approved is True
        and state.device_connected is True
        and type(state.cards) is tuple
        and 0 < len(state.cards) <= 100
        and all(type(c) is dict for c in state.cards)
    )


def _selected(state: ObservedFixture, row: str) -> dict:
    if type(row) is not str or len(row) > 256 or not row:
        _deny()
    # Exactly one in the CURRENT approved bounded snapshot; ephemeral BlueFerry
    # IDs never leave this function or become metadata keys.
    matches = [c for c in state.cards if c.get("id") == row]
    if (len(matches) != 1
            or matches[0].get("deviceProfileId") != state.profile
            or matches[0].get("serviceId") != "blueferry"):
        _deny()
    return matches[0]


def _valid_intent(intent: object) -> bool:
    if (type(intent) is not ActionFixture or intent.action not in ACTIONS
            or type(intent.expected_revision) is not int
            or not 0 <= intent.expected_revision < 2**53 - 1
            or type(intent.nonce) is not str
            or INTENT.fullmatch(intent.nonce) is None):
        return False
    if intent.action == "LINK" or intent.action == "UNLINK":
        return intent.favorite is None and intent.note is None
    if intent.action == "FAVORITE":
        return type(intent.favorite) is bool and intent.note is None
    return intent.favorite is None and type(intent.note) is str


class FixtureCoordinator:
    """Exercises the exact P34/P35 encrypted save in synthetic-only tests.

    The injected observer and gesture verifier are NOT authenticated by this
    module. There is no registration, production key lifecycle or transport.
    """

    def __init__(self, *, observe: Callable[[], ObservedFixture],
                 verify_gesture: Callable[[ActionFixture, ObservedFixture], bool],
                 key_lookup: Callable[[], bytes], clock: Callable[[], int],
                 root: Path) -> None:
        if (not callable(observe) or not callable(verify_gesture)
                or not callable(key_lookup) or not callable(clock)
                or not isinstance(root, Path)
                or root.name != Vault.ROOT_NAME or not root.is_absolute()):
            _deny()
        self._observe = observe
        self._verify_gesture = verify_gesture
        self._lookup = key_lookup
        self._clock = clock
        self._root = root
        self._consumed: set[str] = set()

    def _current(self, intent: ActionFixture) -> tuple[ObservedFixture, dict]:
        now = self._clock()
        state = self._observe()
        if (not _valid_state(state, now)
                or self._verify_gesture(intent, state) is not True):
            _deny()
        return state, _selected(state, intent.selected_row)

    def apply(self, intent: ActionFixture) -> dict[str, object]:
        """One explicit fixture action; all output is content-free.

        NEVER interpret a passing synthetic test as authorized real PHONE UI.
        """
        if not _valid_intent(intent) or intent.nonce in self._consumed:
            _deny()
        try:
            before, card = self._current(intent)
            # Never request/unlock an encryption key before host+gesture checks.
            key = self._lookup()
            if type(key) is not bytes or len(key) != 32:
                _deny()
            # Recheck after key lookup, which may block on a locked keyring.
            observed, selected = self._current(intent)
            if observed != before or selected != card:
                _deny()
            document = Vault.read(key, before.profile, self._root)
            if document["revision"] != intent.expected_revision:
                _deny()
            cards = list(before.cards)
            matching_key = Vault.contact_matching_key(key)
            if intent.action == "LINK":
                result = Identity.link(document, card, cards, before.profile,
                                       matching_key, user_confirmed=True)
            else:
                found = Identity.resolve(document, card, cards, before.profile,
                                         matching_key)
                if found.get("ok") is not True or found.get("status") != "LINKED":
                    _deny()
                local_id = found["localId"]
                if intent.action == "FAVORITE":
                    result = Identity.edit(document, local_id,
                        intent.expected_revision, favorite=intent.favorite,
                        user_confirmed=True)
                elif intent.action == "NOTE":
                    result = Identity.edit(document, local_id,
                        intent.expected_revision, note=intent.note,
                        user_confirmed=True)
                else:
                    result = Identity.unlink(document, local_id,
                        intent.expected_revision, user_confirmed=True)
            if result.get("ok") is not True or result.get("changed") is False:
                _deny()
            new_doc = result["document"]
            # Last check immediately before durable commit. Even this only
            # demonstrates behavior: real permission checking must be held
            # under a verified host-owned lock in the production implementation.
            after, selected = self._current(intent)
            if after != before or selected != card:
                _deny()
            saved = Vault.commit(key, before.profile, self._root, new_doc,
                                 expected_revision=intent.expected_revision)
            self._consumed.add(intent.nonce)
            return {"status": "SYNTHETIC_SEALED", "revision": saved["revision"],
                    "productionEnabled": False}
        except FixtureRefused:
            raise
        except Exception:
            # Never surface notes, keys or raw provider exceptions.
            _deny()


# No main(), IPC endpoint, live key provisioning or production acceptance.
