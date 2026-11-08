"""Host-internal BlueFerry read port, not an authorization or Social IPC service.

The provider port pins a *running* BlueFerry D-Bus unique owner, checks the
active opaque profile before/after each read, and normalizes bounded messages
or contact cards with the P18a mapper. This module intentionally has NO CLI,
QML binding, service start, consent grant or user-facing read endpoint.

A separately approved host MUST supply callable guard/release functions that
authenticate the actual caller, operation, consent, device/line/organization
and revocation generation, and perform release atomically with revocation.
Passing True to a Python callback is NOT authentication or OS isolation.

Importing this module does not connect to the bus or read private phone data.
"""
from __future__ import annotations

from collections.abc import Callable
import json
import re
import secrets
from typing import Any

from BlueFerrySocialProjection import (
    MAX_CARDS, MAX_THREADS, PROFILE, normalize_contact_page,
    normalize_legacy_contact_page, normalize_threads,
)

SERVICE = "io.weirdware.BlueFerry"
OBJECT = "/io/weirdware/BlueFerry"
INTERFACE = SERVICE + ".Messages1"
UNIQUE_OWNER = re.compile(r"^:[0-9]+\.[0-9]+$")
MAX_STATUS_BYTES = 32768
MAX_THREADS_BYTES = 2 * 1024 * 1024
MAX_CARDS_BYTES = 256 * 1024
SCHEMA = "post-apollo.phone.blueferry-host-read-port.v0"
OPERATIONS = frozenset({"messages.read", "contacts.read"})


def _response(state: str) -> dict[str, object]:
    # Deliberately no identity, phone number, owner, content, grant, or count.
    return {"schema": SCHEMA, "execution": "HOST_INTEGRATION_ONLY",
            "state": state, "contentInResponse": False,
            "authorization": "HOST_OWNED_UNVERIFIED"}


def _owner_valid(owner: object) -> bool:
    return type(owner) is str and UNIQUE_OWNER.fullmatch(owner) is not None


def _contact_mode(status: dict[str, Any]) -> str:
    """Choose exactly one provider contract; never guess from a failed read.

    BlueFerry 0.9.1 supports ListContacts(uu) but lacks both newer
    contact-card metadata fields. A *partially* present/invalid modern
    contract must fail closed, rather than silently downgrading.
    """
    if status.get("pbap") is not True:
        return ""
    epoch = status.get("contact_card_epoch")
    count = status.get("contact_card_count")
    if (type(epoch) is int and 0 <= epoch < 2 ** 63
            and type(count) is int and 0 <= count <= 100000):
        return "cards"
    if ("contact_card_epoch" not in status
            and "contact_card_count" not in status):
        return "legacy"
    return ""


def _status_ok(status: object, profile: str, operation: str) -> bool:
    if (type(status) is not dict or status.get("api_version") != 2
            or type(status.get("api_version")) is not int
            or status.get("daemon") is not True
            or status.get("phone_profile_id") != profile
            or type(status.get("map")) is not bool
            or type(status.get("pbap")) is not bool):
        return False
    if operation == "messages.read":
        return status["map"] is True
    return _contact_mode(status) in ("cards", "legacy")


class UniqueOwnerBlueFerrySource:
    """Explicit host-constructed provider transport, not a standalone client.

    No well-known-name method call is made: the destination is the unique
    owner obtained from an already-running daemon. BlueFerry still applies
    its own per-D-Bus-caller read policy. This layer is NOT a phone grant.
    """

    def __init__(self, *, dbus_api: Any = None, session_bus: Any = None) -> None:
        if dbus_api is None:
            import dbus  # type: ignore
            dbus_api = dbus
        self._dbus = dbus_api
        self._bus = session_bus if session_bus is not None else dbus_api.SessionBus(private=True)

    def owner(self) -> str:
        if not self._bus.name_has_owner(SERVICE):
            return ""
        value = str(self._bus.get_name_owner(SERVICE))
        return value if _owner_valid(value) else ""

    def _iface(self, owner: str) -> Any:
        if not _owner_valid(owner) or self.owner() != owner:
            raise ValueError("provider owner changed")
        proxy = self._bus.get_object(owner, OBJECT, introspect=False)
        return self._dbus.Interface(proxy, INTERFACE)

    @staticmethod
    def _json(raw: object, *, bound: int, kind: type) -> Any:
        # D-Bus signature 's' returns dbus.String (a str subclass) on Linux,
        # not necessarily an exact built-in str. Keep strict text-only input
        # while accepting that legitimate wire representation.
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > bound:
            raise ValueError("invalid provider response")
        parsed = json.loads(raw)
        if type(parsed) is not kind:
            raise ValueError("invalid provider response")
        return parsed

    def status(self, owner: str) -> dict[str, Any]:
        return self._json(self._iface(owner).GetStatus(timeout=3),
                          bound=MAX_STATUS_BYTES, kind=dict)

    def threads(self, owner: str) -> list[dict[str, Any]]:
        iface = self._iface(owner)
        return self._json(
            iface.ListThreads(self._dbus.UInt32(MAX_THREADS), timeout=10),
            bound=MAX_THREADS_BYTES, kind=list,
        )

    def contact_cards(self, owner: str) -> dict[str, Any]:
        iface = self._iface(owner)
        return self._json(
            iface.ListContactCards(
                self._dbus.UInt32(0), self._dbus.UInt32(MAX_CARDS), "",
                timeout=10,
            ),
            bound=MAX_CARDS_BYTES, kind=dict,
        )

    def legacy_contacts(self, owner: str) -> list[dict[str, Any]]:
        """One bounded page from 0.9.1 ListContacts(uu), not a card ID API."""
        iface = self._iface(owner)
        return self._json(
            iface.ListContacts(
                self._dbus.UInt32(0), self._dbus.UInt32(MAX_CARDS),
                timeout=10,
            ),
            bound=MAX_CARDS_BYTES, kind=list,
        )


def read_for_trusted_host(
    *,
    operation: str,
    profile_id: str,
    source: UniqueOwnerBlueFerrySource,
    host_guard: Callable[[str, str, str], bool],
    host_release: Callable[[str, str, str, dict[str, object]], bool],
) -> dict[str, object]:
    """Pass a snapshot only to the trusted host's *atomic release callback*.

    This is a host integration port, NOT an authorization implementation.
    The host must implement peer authentication, signed principal/session
    verification, exact device/line and per-capability consent, and a single
    serializable revocation/release barrier. A callback returning True does
    not itself prove any of those security conditions.

    The scope requested here is only a caller-supplied *selector*; never treat
    its UUID syntax as a permission. The release callback must not deliver
    to the UI without rechecking real host-owned grant state under its lock.
    """
    if (type(operation) is not str or operation not in OPERATIONS
            or type(profile_id) is not str or PROFILE.fullmatch(profile_id) is None
            or not callable(host_guard) or not callable(host_release)
            or source is None):
        return _response("REFUSED")
    try:
        owner = source.owner()
        if not _owner_valid(owner):
            return _response("PROVIDER_UNAVAILABLE")
        if host_guard(operation, profile_id, owner) is not True:
            return _response("HOST_DENIED")
        before = source.status(owner)
        if not _status_ok(before, profile_id, operation):
            return _response("PROVIDER_UNAVAILABLE")
        if operation == "messages.read":
            payload = source.threads(owner)
            snapshot = normalize_threads(payload, profile_id=profile_id)
        else:
            contact_mode = _contact_mode(before)
            if contact_mode == "cards":
                payload = source.contact_cards(owner)
                snapshot = normalize_contact_page(
                    payload, profile_id=profile_id,
                    daemon_epoch=before["contact_card_epoch"],
                )
            else:
                # No modern metadata exists at all. Legacy ListContacts has
                # no stable card IDs or cache epoch, so use a fresh random
                # read-only namespace for *this snapshot only*.
                legacy = source.legacy_contacts(owner)
                snapshot = normalize_legacy_contact_page(
                    legacy, profile_id=profile_id,
                    read_epoch=secrets.token_hex(16),
                )
        # Do not pass a payload forward if the daemon, phone profile,
        # capability, or ephemeral contact epoch changed while reading.
        if source.owner() != owner:
            return _response("PROVIDER_CHANGED")
        after = source.status(owner)
        if not _status_ok(after, profile_id, operation):
            return _response("PROVIDER_CHANGED")
        if operation == "contacts.read":
            if _contact_mode(after) != contact_mode:
                return _response("PROVIDER_CHANGED")
            if (contact_mode == "cards"
                    and after["contact_card_epoch"] != before["contact_card_epoch"]):
                return _response("PROVIDER_CHANGED")
        if host_guard(operation, profile_id, owner) is not True:
            return _response("HOST_DENIED")
        # IMPORTANT: the host_release callback itself must commit the
        # authorization check and delivery atomically against revoke.
        # A separate Python guard call here is not that transaction.
        released = host_release(operation, profile_id, owner, snapshot)
        return _response("HOST_HANDOFF_REPORTED" if released is True
                         else "HOST_RELEASE_REFUSED")
    except Exception:
        # Never include provider errors or raw content in status/error output.
        return _response("PROVIDER_UNAVAILABLE")
