"""P1 KDE Connect Android SMS packet -> isolated Social message records.

Pure, offline and read-only. Accepts *decoded* KDE Connect SMS packet message
maps (NOT raw QDBusArgument structures). No phone, D-Bus, network, database,
output, logging or SMS sending. The caller owns authentication, permission,
device+line binding and redaction of sensitive content outside the UI.
"""
from __future__ import annotations

import re
from typing import Any

SERVICE_ID = "kdeconnect-sms"
MAX_MESSAGES = 128
MAX_ADDRESSES = 24
MAX_ATTACHMENTS = 12
MAX_BODY_CHARS = 16384
ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ALLOWED_FIELDS = frozenset({
    "event", "body", "addresses", "date", "type", "read",
    "thread_id", "_id", "sub_id", "attachments",
})
REQUIRED_FIELDS = frozenset({
    "event", "body", "addresses", "date", "type", "read", "thread_id", "_id",
})
NATIVE_STATES = {
    1: ("incoming", "received"),
    2: ("outgoing", "sent"),
    3: ("outgoing", "draft"),
    4: ("outgoing", "outbox"),
    5: ("outgoing", "failed"),
    6: ("outgoing", "queued"),
}


def _ref(ref: object) -> str:
    if not isinstance(ref, str) or not ID.fullmatch(ref):
        raise ValueError("invalid opaque scope reference")
    return ref


def _integer(value: object, *, positive: bool = False,
             signed: bool = False, bits: int = 64) -> int:
    # KDE Connect packet numbers may arrive from Android as decimal strings;
    # QVariants may also surface integers. Never accept bool or floats.
    if type(value) is int:
        number = value
    elif isinstance(value, str) and re.fullmatch(
        r"-?(?:0|[1-9][0-9]*)" if signed else r"(?:0|[1-9][0-9]*)", value
    ):
        number = int(value)
    else:
        raise ValueError("invalid native integer field")
    low = -(2 ** (bits - 1)) if signed else 0
    high = (2 ** (bits - 1) - 1) if signed else (2 ** bits - 1)
    if not low <= number <= high or (positive and number <= 0):
        raise ValueError("native integer out of range")
    return number


def normalize_message(packet: object, *,
                      principal_ref: str, device_ref: str,
                      line_ref: str) -> dict[str, Any]:
    """Return a provider-scoped UI record from a decoded SMS *text* message.

    The trusted caller must separately verify phone ownership, user consent,
    Android SMS permission, exact line/subscription, and transport. Scope
    references are syntactically checked, NOT authenticated here.
    """
    principal, device, line = (
        _ref(principal_ref), _ref(device_ref), _ref(line_ref)
    )
    if not isinstance(packet, dict) or not REQUIRED_FIELDS <= packet.keys() or (
        set(packet) - ALLOWED_FIELDS
    ):
        raise ValueError("unexpected SMS packet fields")
    event = _integer(packet["event"], bits=32)
    if event not in (1, 3):
        raise ValueError("unsupported SMS event flags")
    kind = _integer(packet["type"], bits=32)
    if kind not in NATIVE_STATES:
        raise ValueError("unsupported native SMS message type")
    timestamp = _integer(packet["date"], positive=True, bits=64)
    thread = _integer(packet["thread_id"], positive=True, bits=64)
    message_id = _integer(packet["_id"], positive=True, bits=32)
    read = packet["read"]
    if type(read) is bool:
        read = bool(read)
    elif type(read) is int and read in (0, 1):
        read = bool(read)
    else:
        raise ValueError("unsupported read state")
    body = packet["body"]
    if not isinstance(body, str) or not body or len(body) > MAX_BODY_CHARS:
        raise ValueError("unsupported empty or oversized SMS text body")

    addresses = packet["addresses"]
    if (not isinstance(addresses, list)
        or not (1 <= len(addresses) <= MAX_ADDRESSES)
        or any(
            not isinstance(row, dict) or set(row) != {"address"}
            or not isinstance(row["address"], str)
            or not (1 <= len(row["address"]) <= 254)
            for row in addresses
        )):
        raise ValueError("invalid SMS address metadata")
    is_group = bool(event & 0x2)
    if (is_group and len(addresses) < 2) or (
        not is_group and len(addresses) != 1
    ):
        raise ValueError("address count disagrees with SMS group flag")
    # Subscription identity is not inferred from an untrusted packet value.
    # An eventual broker must prove sub_id maps to the authorized line_ref.
    if "sub_id" in packet:
        _integer(packet["sub_id"], signed=True, bits=64)
    attachments = packet.get("attachments", [])
    if (not isinstance(attachments, list) or len(attachments) > MAX_ATTACHMENTS
        or any(not isinstance(a, dict) for a in attachments)):
        raise ValueError("invalid SMS attachment metadata")
    direction, native_status = NATIVE_STATES[kind]
    conversation_id = f"{principal}:{device}:{line}:{thread}"
    return {
        "serviceId": SERVICE_ID,
        "id": f"{conversation_id}:{message_id}",
        "conversationId": conversation_id,
        "body": body,
        "direction": direction,
        "sent_at": timestamp,
        "timestampUnit": "unix_ms",
        "nativeStatus": native_status,
        "read": read,
        "isGroup": is_group,
        "hasAttachments": bool(attachments),
    }


def normalize_conversation(packets: object, *,
                           principal_ref: str, device_ref: str,
                           line_ref: str) -> list[dict[str, Any]]:
    """Stable oldest-first synthetic feed with exact-duplicate collapse.

    Mixed conversations and conflicting message records fail closed. This
    function never stores messages or calls KDE Connect.
    """
    if not isinstance(packets, list) or len(packets) > MAX_MESSAGES:
        raise ValueError("invalid SMS message collection")
    seen: dict[str, dict[str, Any]] = {}
    conversation_id = None
    for packet in packets:
        message = normalize_message(
            packet, principal_ref=principal_ref,
            device_ref=device_ref, line_ref=line_ref,
        )
        if conversation_id is None:
            conversation_id = message["conversationId"]
        elif message["conversationId"] != conversation_id:
            raise ValueError("messages span multiple SMS conversations")
        prev = seen.get(message["id"])
        if prev is not None and prev != message:
            raise ValueError("conflicting message ID")
        seen[message["id"]] = message
    return sorted(seen.values(), key=lambda x: (x["sent_at"], x["id"]))
