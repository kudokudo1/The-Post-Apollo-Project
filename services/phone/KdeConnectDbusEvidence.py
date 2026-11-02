"""Offline KDE Connect D-Bus plugin evidence classifier, P1.

This module does not open D-Bus, inspect a phone, connect to KDE Connect,
or emit route-ready / authorized SMS or contact capabilities. Input values
are untrusted hypothetical reports until verified by a separate privileged
host boundary. Loaded desktop plugins are not phone permissions.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "post-apollo.phone.kdeconnect-dbus-evidence.v0"
FIELDS = frozenset({
    "schema", "isPaired", "isReachable", "deviceType",
    "supportedPlugins", "loadedPlugins", "activeProviderNames",
})
PLUGIN_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
MAX_PLUGINS = 64
MAX_PROVIDERS = 8

# Names come from the KDE Connect desktop plugin metadata. This is a
# classification of *desktop-side availability*, not Android permissions.
PLUGINS = {
    "sms": "kdeconnect_sms",
    "contacts": "kdeconnect_contacts",
    "telephonyEvents": "kdeconnect_telephony",
}


def _names(value: object, label: str, max_count: int) -> set[str]:
    if (
        not isinstance(value, list)
        or len(value) > max_count
        or any(not isinstance(v, str) or not PLUGIN_NAME.fullmatch(v) for v in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"{label} must contain bounded unique opaque names")
    return set(value)


def assess(observation: object) -> dict[str, Any]:
    """Assess *reported* KDE Connect properties without reading a D-Bus bus.

    Do not map these results to CapabilityPolicy's VERIFIED / READY route.
    A loaded plugin is only evidence that the Linux daemon instantiated it;
    it says nothing about Android-side permissions, available data, link
    transport, phone identity, delivery receipts or PC call audio.
    """
    if not isinstance(observation, dict) or set(observation) != FIELDS:
        raise ValueError("observation must contain exactly the expected keys")
    if observation["schema"] != SCHEMA:
        raise ValueError("unknown observation schema")
    if type(observation["isPaired"]) is not bool or type(observation["isReachable"]) is not bool:
        raise ValueError("pairing and reachability must be booleans")
    if not isinstance(observation["deviceType"], str) or not PLUGIN_NAME.fullmatch(
        observation["deviceType"]
    ):
        raise ValueError("deviceType must be a bounded identifier")
    supported = _names(observation["supportedPlugins"], "supportedPlugins", MAX_PLUGINS)
    loaded = _names(observation["loadedPlugins"], "loadedPlugins", MAX_PLUGINS)
    providers = _names(observation["activeProviderNames"], "activeProviderNames", MAX_PROVIDERS)

    paired, reachable = observation["isPaired"], observation["isReachable"]
    # Snapshot fields may originate from different instants while D-Bus state
    # changes. Prefer an inconsistent/untrusted result to asserting readiness.
    inconsistent = (bool(loaded - supported)
                    or (loaded and not (paired and reachable))
                    or (providers and not reachable))
    if inconsistent:
        state = "INCONSISTENT_REPORT"
    elif not paired:
        state = "NOT_PAIRED"
    elif not reachable:
        state = "NOT_REACHABLE"
    else:
        state = "PAIRED_REACHABLE_REPORTED"

    def plugin_status(name: str) -> str:
        if state != "PAIRED_REACHABLE_REPORTED":
            return "NOT_EVALUATED"
        if name in loaded:
            return "LOCAL_PLUGIN_LOADED"
        if name in supported:
            return "SUPPORTED_NOT_LOADED"
        return "NOT_ADVERTISED"

    return {
        "schema": SCHEMA,
        "provider": "kdeconnect",
        "execution": "ASSESS_ONLY",
        "state": state,
        "reportedPhoneType": observation["deviceType"].lower() == "phone",
        "reportedActiveLinkCount": len(providers),
        "transport": "UNVERIFIED",
        "devicePlatform": "UNVERIFIED",
        "sms": plugin_status(PLUGINS["sms"]),
        "contacts": plugin_status(PLUGINS["contacts"]),
        "telephonyEvents": plugin_status(PLUGINS["telephonyEvents"]),
        "smsPermission": "NOT_CHECKED",
        "contactsPermission": "NOT_CHECKED",
        "callAudio": "NOT_CHECKED",
        "routeEligible": False,
    }
