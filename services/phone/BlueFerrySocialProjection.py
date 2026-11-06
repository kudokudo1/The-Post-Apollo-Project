"""Pure BlueFerry Messages1 -> Social PHONE shape conversion (P18a).

This module NEVER opens D-Bus, reads device state, obtains grants, sends a
message, or returns content to QML. It transforms data *already supplied by a
future trusted caller*. An opaque BlueFerry profile ID is only a namespace;
it is not proof of a verified desktop user, phone line, or content consent.

Source shapes: BlueFerry Messages1.ListThreads(u) (list of thread dicts) and
Messages1.ListContactCards(uus) (paged dict). Contact IDs are valid within a
daemon epoch, not permanent address-book IDs.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

SCHEMA = "post-apollo.phone.blueferry-social-projection.v0"
SERVICE_ID = "blueferry"
PROFILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
MAX_THREADS = 64
MAX_MESSAGES = 256
MAX_CARDS = 100
MAX_KEY = 1024
MAX_BODY = 16384
MAX_DISPLAY = 256
MAX_SENDER = 254
MAX_EPOCH = 64


def _error() -> ValueError:
    # Never echo the private message, name, recipient, or provider payload.
    return ValueError("unsupported BlueFerry projection input")


def _profile(value: object) -> str:
    if type(value) is not str or PROFILE.fullmatch(value) is None:
        raise _error()
    return value


def _text(value: object, maximum: int, *, empty: bool = False,
          multiline: bool = False) -> str:
    if type(value) is not str or len(value) > maximum or (not empty and not value):
        raise _error()
    for char in value:
        number = ord(char)
        if number == 0 or number == 127 or (number < 32 and
            (not multiline or char not in "\n\r\t")):
            raise _error()
    return value


def _timestamp(value: object) -> tuple[str, datetime]:
    text = _text(value, 64)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise _error()
        return text, parsed
    except (TypeError, ValueError, OverflowError):
        raise _error() from None


def _natural(value: object, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise _error()
    return value


def _header(profile: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "execution": "OFFLINE_PROJECTION_ONLY",
        "serviceId": SERVICE_ID,
        "deviceProfileId": profile,
        # These are explicit reminders that syntactic profile scope is NOT
        # a content grant, and that this module provides no live I/O route.
        "authorization": "NOT_EVALUATED",
        "routeEligible": False,
    }


def normalize_threads(payload: object, *, profile_id: str) -> dict[str, object]:
    """Convert one already-authorized, decoded ListThreads reply.

    The caller owns verified person/device/line/organization binding,
    lifecycle, revocation, and any release of the result to the UI. Nothing
    in this function verifies those conditions; do not call it from a QML
    subprocess or another untrusted client.
    """
    profile = _profile(profile_id)
    if type(payload) is not list or len(payload) > MAX_THREADS:
        raise _error()
    conversations: list[dict[str, Any]] = []
    message_sets: list[dict[str, Any]] = []
    seen_conversations: set[str] = set()
    for thread in payload:
        if type(thread) is not dict:
            raise _error()
        native_key = _text(thread.get("key"), MAX_KEY)
        name = _text(thread.get("name"), MAX_DISPLAY, empty=True)
        is_group = thread.get("is_group")
        unread = thread.get("unread")
        reply_ready = thread.get("reply_ready")
        truncated = thread.get("messages_truncated")
        if any(type(item) is not bool
               for item in (is_group, unread, reply_ready, truncated)):
            raise _error()
        raw_messages = thread.get("messages")
        if type(raw_messages) is not list or len(raw_messages) > MAX_MESSAGES:
            raise _error()
        conversation_id = f"{profile}:{native_key}"
        if conversation_id in seen_conversations:
            raise _error()
        seen_conversations.add(conversation_id)

        rows: list[tuple[datetime, str, dict[str, object]]] = []
        seen_messages: dict[str, dict[str, object]] = {}
        for message in raw_messages:
            if type(message) is not dict:
                raise _error()
            handle = _text(message.get("handle"), MAX_KEY)
            body = _text(message.get("body"), MAX_BODY, empty=True, multiline=True)
            sent_at, sort_stamp = _timestamp(message.get("timestamp"))
            outgoing = message.get("outgoing")
            read = message.get("read")
            if type(outgoing) is not bool or type(read) is not bool:
                raise _error()
            sender = _text(message.get("sender", ""), MAX_SENDER, empty=True)
            message_id = f"{conversation_id}:message:{handle}"
            normalized: dict[str, object] = {
                "id": message_id,
                "conversationId": conversation_id,
                "body": body,
                "direction": "outgoing" if outgoing else "incoming",
                "sent_at": sent_at,
                "timestampUnit": "iso8601-offset",
                "read": read,
            }
            if is_group and not outgoing and sender:
                normalized["senderId"] = sender
            previous = seen_messages.get(message_id)
            if previous is not None:
                if previous != normalized:
                    raise _error()
                continue
            seen_messages[message_id] = normalized
            rows.append((sort_stamp, message_id, normalized))
        rows.sort(key=lambda item: (item[0], item[1]))
        messages = [entry[2] for entry in rows]
        # The provider's unread bool can include older omitted history. Do
        # not pretend this computed number is complete for truncated threads.
        visible_unread = sum(
            1 for m in messages
            if m["direction"] == "incoming" and m["read"] is False
        )
        unread_count = max(visible_unread, int(unread)) if truncated else visible_unread
        if not truncated and (unread_count > 0) != unread:
            raise _error()
        last = messages[-1]["body"] if messages else ""
        conversations.append({
            "id": conversation_id,
            "serviceId": SERVICE_ID,
            "type": "group" if is_group else "direct",
            "displayNameInProfile": name or "Unnamed conversation",
            "lastMessage": last,
            "unreadCount": unread_count,
            "unreadCountExact": not truncated,
            "nativeKey": native_key,
            "providerReplyReady": reply_ready,
            "historyPartial": truncated,
        })
        message_sets.append({
            "conversationId": conversation_id,
            "messages": messages,
            "historyPartial": truncated,
        })
    return {**_header(profile), "conversations": conversations,
            "messageSets": message_sets}


def normalize_contact_page(payload: object, *, profile_id: str,
                           daemon_epoch: object) -> dict[str, object]:
    """Convert one already-authorized ListContactCards page.

    Card IDs are temporary, tied to the provider's contact_card_epoch and
    active daemon. They must be discarded after any epoch, profile, session,
    or authorization change. No contact becomes a chat conversation.
    """
    profile = _profile(profile_id)
    if type(daemon_epoch) is int:
        if not 0 <= daemon_epoch < 2 ** 63:
            raise _error()
        epoch = str(daemon_epoch)
    else:
        epoch = _text(daemon_epoch, MAX_EPOCH)
    if (type(payload) is not dict
            or type(payload.get("contacts")) is not list
            or len(payload["contacts"]) > MAX_CARDS):
        raise _error()
    offset = _natural(payload.get("offset"), 1000000)
    total = _natural(payload.get("total"), 1000000)
    query = _text(payload.get("query"), MAX_DISPLAY, empty=True)
    cards: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in payload["contacts"]:
        if type(raw) is not dict:
            raise _error()
        card_id = _text(raw.get("id"), 256)
        if card_id in seen:
            raise _error()
        seen.add(card_id)
        name = _text(raw.get("name"), MAX_DISPLAY, empty=True)
        organization = _text(raw.get("organization", ""), MAX_DISPLAY, empty=True)
        primary = _text(raw.get("primary", ""), MAX_SENDER, empty=True)
        phones = _natural(raw.get("phone_count"), 10000)
        emails = _natural(raw.get("email_count"), 10000)
        has_photo = raw.get("has_photo")
        if type(has_photo) is not bool:
            raise _error()
        cards.append({
            # No assumption of a globally stable contact ID. The caller must
            # supply a fresh daemon epoch obtained with the same bus owner.
            "id": f"{profile}:{epoch}:{card_id}",
            "serviceId": SERVICE_ID,
            "deviceProfileId": profile,
            "nativeCardId": card_id,
            "displayNameInProfile": name or organization or primary or "Unnamed contact",
            "organization": organization,
            "primary": primary,
            "phoneCount": phones,
            "emailCount": emails,
            "hasPhoto": has_photo,
        })
    if offset + len(cards) > total:
        raise _error()
    return {
        **_header(profile), "daemonEpoch": epoch, "offset": offset,
        "total": total, "query": query, "contacts": cards,
    }
