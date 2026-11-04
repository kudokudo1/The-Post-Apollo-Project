"""Pure, fail-closed Social PHONE provider observation (P2).

Inputs are sanitized outputs from separate diagnostics, never trusted identity
or authorization. No host inspection, D-Bus, network, phone-content or writes.
KDE Connect does not by itself prove a device is Android.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "post-apollo.phone.provider-observation.v0"
BLUEFERRY_SCHEMA = "post-apollo.social.phone-readiness.v0"
KDE_SCHEMA = "post-apollo.phone.kdeconnect-dbus-probe.v0"
BLUEFERRY_FIELDS = frozenset({
    "schema", "execution", "blueferryInstalled", "bluetoothService",
    "controllerPowered", "configurationPresent", "backendService",
    "backendObservation", "mapSessionActive", "pbapSessionActive",
    "phoneLink", "contentAuthorized",
})
KDE_FIELDS = frozenset({
    "schema", "execution", "provider", "state",
    "reportedPairedReachableCount", "localSmsPluginCount",
    "localContactsPluginCount", "localTelephonyPluginCount",
    "devicePlatform", "transport", "smsPermission", "contactsPermission",
    "callAudio", "routeEligible",
})
SERVICE_STATES = frozenset({
    "active", "inactive", "failed", "activating", "deactivating", "unknown",
})
BLUEFERRY_STATES = frozenset({
    "NOT_RUNNING", "NO_OWNER", "UNAVAILABLE", "REPORTED",
})
KDE_STATES = frozenset({
    "BUSCTL_NOT_INSTALLED", "SERVICE_NOT_RUNNING",
    "NO_PAIRED_REACHABLE_DEVICES", "METADATA_REPORTED",
    "METADATA_UNAVAILABLE", "BUS_TIMEOUT", "EXPLICIT_FLAG_REQUIRED",
})


def _choice(value: object, choices: frozenset[str]) -> bool:
    return type(value) is str and value in choices


def _blueferry(value: object) -> dict[str, str]:
    unavailable = {
        "state": "UNAVAILABLE", "mapProfile": "UNVERIFIED",
        "pbapProfile": "UNVERIFIED",
    }
    if type(value) is not dict or set(value) != BLUEFERRY_FIELDS:
        return unavailable
    if (value["schema"] != BLUEFERRY_SCHEMA
            or value["execution"] != "READ_ONLY"
            or value["phoneLink"] != "UNVERIFIED"
            or value["contentAuthorized"] is not False
            or type(value["blueferryInstalled"]) is not bool
            or type(value["configurationPresent"]) is not bool
            or not _choice(value["bluetoothService"], SERVICE_STATES)
            or not _choice(value["backendService"], SERVICE_STATES)
            or (value["controllerPowered"] is not None
                and type(value["controllerPowered"]) is not bool)
            or not _choice(value["backendObservation"], BLUEFERRY_STATES)):
        return unavailable
    state = value["backendObservation"]
    if state == "REPORTED":
        if (value["backendService"] != "active"
                or type(value["mapSessionActive"]) is not bool
                or type(value["pbapSessionActive"]) is not bool):
            return unavailable
        return {
            "state": "REPORTED",
            "mapProfile": ("ACTIVE_BACKEND_REPORT" if value["mapSessionActive"]
                           else "INACTIVE_BACKEND_REPORT"),
            "pbapProfile": ("ACTIVE_BACKEND_REPORT" if value["pbapSessionActive"]
                            else "INACTIVE_BACKEND_REPORT"),
        }
    if (value["mapSessionActive"] is not None
            or value["pbapSessionActive"] is not None
            or (state == "NOT_RUNNING" and value["backendService"] == "active")
            or (state == "NO_OWNER" and value["backendService"] != "active")):
        return unavailable
    return {**unavailable, "state": state}


def _kde(value: object) -> dict[str, Any]:
    unavailable: dict[str, Any] = {
        "state": "UNAVAILABLE", "pairedReachableReported": None,
        "smsPluginReported": None, "contactsPluginReported": None,
        "telephonyPluginReported": None, "devicePlatform": "UNVERIFIED",
    }
    if type(value) is not dict or set(value) != KDE_FIELDS:
        return unavailable
    if (value["schema"] != KDE_SCHEMA
            or value["execution"] != "DIAGNOSTIC_ONLY"
            or value["provider"] != "kdeconnect"
            or not _choice(value["state"], KDE_STATES)
            or value["devicePlatform"] != "UNVERIFIED"
            or value["transport"] != "UNVERIFIED"
            or value["smsPermission"] != "NOT_CHECKED"
            or value["contactsPermission"] != "NOT_CHECKED"
            or value["callAudio"] != "NOT_CHECKED"
            or value["routeEligible"] is not False):
        return unavailable
    keys = (
        "reportedPairedReachableCount", "localSmsPluginCount",
        "localContactsPluginCount", "localTelephonyPluginCount",
    )
    counts = [value[key] for key in keys]
    if (any(type(count) is not int or not 0 <= count <= 4 for count in counts)
            or any(count > counts[0] for count in counts[1:])
            or (value["state"] == "METADATA_REPORTED" and counts[0] == 0)
            or (value["state"] != "METADATA_REPORTED" and any(counts))):
        return unavailable
    if value["state"] == "METADATA_REPORTED":
        unavailable.update({
            "pairedReachableReported": counts[0],
            "smsPluginReported": counts[1],
            "contactsPluginReported": counts[2],
            "telephonyPluginReported": counts[3],
        })
    return {**unavailable, "state": value["state"]}


def project(blueferry: object, kdeconnect: object) -> dict[str, object]:
    """Combine provider metadata, with all content authorization held false.

    A future privileged host must separately authenticate principal,
    device, phone line, organization, consent, and revocation.
    """
    return {
        "schema": SCHEMA,
        "execution": "PROJECTION_ONLY",
        "trustedPhoneLink": "UNVERIFIED",
        "personBinding": "UNVERIFIED",
        "deviceBinding": "UNVERIFIED",
        "lineBinding": "UNVERIFIED",
        "organizationBinding": "UNVERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
        "providers": {
            "BLUEFERRY": _blueferry(blueferry),
            "KDECONNECT": _kde(kdeconnect),
        },
    }
