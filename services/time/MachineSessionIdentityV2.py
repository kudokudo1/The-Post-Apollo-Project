"""MACHINE M2b: strict, pure PROPOSED v2 session identity sidecar schema.

NO files, Sway IPC, browser/Kitty access, action runners, or migrations.
The current v1 checkpoint document/database remains the only implemented
persistent save. Parsed adapter identifiers are CLAIMS, never verified proof
of which live window, tab, process or browser profile is which.
"""
from __future__ import annotations

from collections import Counter
import json
import uuid

from MachineCheckpointStore import StoreError, validate as validate_v1

MAX_WINDOWS = 512
MAX_ITEMS = 4096
MAX_BYTES = 2_000_000
MAX_TEXT = 128
SIDECAR_KIND = "machine-session-identity-sidecar"
IDENTITY_STATES = frozenset((
    "not_requested", "denied", "unsupported", "partial", "reported"))
SOURCES = frozenset(("none", "brave", "kitty"))
ITEM_KINDS = frozenset(("browser_tab", "terminal_tab", "terminal_split"))


class SidecarError(ValueError):
    pass


def _fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise SidecarError("INVALID SIDECAR FIELDS")


def _id(value):
    if not isinstance(value, str):
        raise SidecarError("INVALID SIDECAR ID")
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise SidecarError("INVALID SIDECAR ID") from exc
    if value != canonical:
        raise SidecarError("NONCANONICAL SIDECAR ID")
    return canonical


def _maybe_id(value):
    return None if value is None else _id(value)


def _name(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= MAX_TEXT
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SidecarError("INVALID IDENTIFIER")
    return value


def _state(value):
    if not isinstance(value, str) or value not in IDENTITY_STATES:
        raise SidecarError("INVALID CAPABILITY STATE")
    return value


def _ordinal(value):
    if type(value) is not int or not 0 <= value < MAX_ITEMS:
        raise SidecarError("INVALID INNER ITEM POSITION")
    return value


def validate_sidecar(document, *, v1_checkpoint=None):
    """Strict allowlisted parser; never emits a claim of live session equality.

    Optional v1 document comparison binds this PROPOSAL to precisely the
    recorded window-placement multiset, without updating v1's schema or disk.
    """
    try:
        raw = json.dumps(document, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":"))
    except (TypeError, ValueError, RecursionError) as exc:
        raise SidecarError("INVALID SIDECAR JSON") from exc
    try:
        encoded_length = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise SidecarError("INVALID SIDECAR TEXT") from exc
    if encoded_length > MAX_BYTES:
        raise SidecarError("OVERSIZED SIDECAR")

    _fields(document, ("schema_version", "kind", "checkpoint_id", "windows"))
    if type(document["schema_version"]) is not int or document["schema_version"] != 2:
        raise SidecarError("UNSUPPORTED SIDECAR VERSION")
    if document["kind"] != SIDECAR_KIND:
        raise SidecarError("INVALID SIDECAR KIND")
    checkpoint_id = _id(document["checkpoint_id"])
    windows = document["windows"]
    if not isinstance(windows, list) or len(windows) > MAX_WINDOWS:
        raise SidecarError("INVALID WINDOW COLLECTION")

    cleaned = []
    window_keys = set()
    app_instance_refs = set()
    all_item_keys = set()
    total_items = 0
    for window in windows:
        _fields(window, ("window_key", "app_id", "workspace", "floating",
                         "identity", "capabilities", "items"))
        window_key = _id(window["window_key"])
        if window_key in window_keys:
            raise SidecarError("DUPLICATE CHECKPOINT WINDOW KEY")
        window_keys.add(window_key)
        app = _name(window["app_id"])
        workspace = _name(window["workspace"])
        if type(window["floating"]) is not bool:
            raise SidecarError("INVALID WINDOW FLAG")

        identity = window["identity"]
        _fields(identity, ("adapter", "status", "namespace_key",
                           "instance_key"))
        adapter = identity["adapter"]
        if not isinstance(adapter, str) or adapter not in SOURCES:
            raise SidecarError("UNRECOGNIZED ADAPTER")
        status = _state(identity["status"])
        namespace_key = _maybe_id(identity["namespace_key"])
        instance_key = _maybe_id(identity["instance_key"])
        if (adapter == "none" and (
                status not in ("not_requested", "denied", "unsupported")
                or namespace_key is not None or instance_key is not None)):
            raise SidecarError("UNSUPPORTED IDENTITY CLAIM")
        if status in ("not_requested", "denied", "unsupported") and (
                namespace_key is not None or instance_key is not None):
            raise SidecarError("IDENTITY REFERENCE WITHOUT CONSENT")
        if status == "reported" and (adapter == "none" or instance_key is None):
            raise SidecarError("INCOMPLETE REPORTED IDENTITY")
        if instance_key is not None:
            composite = (adapter, namespace_key, instance_key)
            if composite in app_instance_refs:
                raise SidecarError("DUPLICATE ADAPTER INSTANCE REFERENCE")
            app_instance_refs.add(composite)

        capabilities = window["capabilities"]
        _fields(capabilities, ("window_identity", "inner_items",
                               "reopen_window"))
        clean_caps = {key: _state(capabilities[key]) for key in
                      ("window_identity", "inner_items", "reopen_window")}
        if (adapter == "none" and
                any(value in ("partial", "reported")
                    for value in clean_caps.values())):
            raise SidecarError("CAPABILITY REQUIRES ADAPTER")
        if status in ("not_requested", "denied", "unsupported") and (
                clean_caps["window_identity"] in ("partial", "reported")):
            raise SidecarError("CONTRADICTORY IDENTITY CAPABILITY")

        items = window["items"]
        if not isinstance(items, list):
            raise SidecarError("INVALID INNER ITEM COLLECTION")
        total_items += len(items)
        if total_items > MAX_ITEMS:
            raise SidecarError("TOO MANY INNER ITEMS")
        if items and (adapter == "none" or
                      clean_caps["inner_items"] not in ("partial", "reported")):
            raise SidecarError("INNER ITEMS NOT AVAILABLE")
        cleaned_items = []
        seen_positions = set()
        seen_adapter_items = set()
        for item in items:
            _fields(item, ("item_key", "kind", "position", "adapter_item_key"))
            item_key = _id(item["item_key"])
            if item_key in all_item_keys:
                raise SidecarError("DUPLICATE INNER ITEM KEY")
            all_item_keys.add(item_key)
            kind = item["kind"]
            if not isinstance(kind, str) or kind not in ITEM_KINDS:
                raise SidecarError("UNSUPPORTED INNER ITEM KIND")
            if adapter == "brave" and kind != "browser_tab":
                raise SidecarError("WRONG INNER ITEM ADAPTER")
            if adapter == "kitty" and kind == "browser_tab":
                raise SidecarError("WRONG INNER ITEM ADAPTER")
            position = _ordinal(item["position"])
            if position in seen_positions:
                raise SidecarError("DUPLICATE INNER ITEM POSITION")
            seen_positions.add(position)
            adapter_item_key = _maybe_id(item["adapter_item_key"])
            if adapter_item_key is not None:
                if adapter_item_key in seen_adapter_items:
                    raise SidecarError("DUPLICATE ADAPTER INNER ITEM")
                seen_adapter_items.add(adapter_item_key)
            cleaned_items.append({
                "item_key": item_key, "kind": kind,
                "position": position, "adapter_item_key": adapter_item_key})

        cleaned.append({
            "window_key": window_key, "app_id": app,
            "workspace": workspace, "floating": window["floating"],
            "identity": {"adapter": adapter, "status": status,
                         "namespace_key": namespace_key,
                         "instance_key": instance_key},
            "capabilities": clean_caps, "items": cleaned_items,
        })
    if v1_checkpoint is not None:
        try:
            original = validate_v1(v1_checkpoint)
        except (StoreError, TypeError, KeyError) as exc:
            raise SidecarError("INVALID LEGACY CHECKPOINT") from exc
        original_windows = Counter((x["app_id"], x["workspace"], x["floating"])
                                   for x in original["windows"])
        sidecar_windows = Counter((x["app_id"], x["workspace"], x["floating"])
                                 for x in cleaned)
        if original_windows != sidecar_windows:
            raise SidecarError("V2 PROPOSAL DOES NOT MATCH V1 LAYOUT")

    return {"schema_version": 2, "kind": SIDECAR_KIND,
            "checkpoint_id": checkpoint_id, "windows": cleaned}


def describe_coverage(proposal):
    """Information summary only; adapter claims do not prove session equality."""
    valid = validate_sidecar(proposal)
    counts = Counter(x["identity"]["status"] for x in valid["windows"])
    return {
        "kind": "machine-v2-identity-coverage",
        "read_only": True, "executable": False,
        "checkpoint_id": valid["checkpoint_id"],
        "window_count": len(valid["windows"]),
        "inner_item_count": sum(len(w["items"]) for w in valid["windows"]),
        "identity_claims": {key: counts.get(key, 0)
                            for key in sorted(IDENTITY_STATES)},
        "per_window_identity_verified": False,
        "exact_session_match": False,
        "safe_actions": [],
        "v1_storage_unchanged": True,
    }
