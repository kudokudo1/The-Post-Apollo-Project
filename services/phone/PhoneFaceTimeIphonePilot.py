#!/usr/bin/env python3
"""iPhone-only FaceTime V1 feasibility probe, not a FaceTime session client.

Uses existing BlueFerry *status* and local HFP *candidate* observations only.
No notification list, caller/contact data, CallKit, iOS app, call actions,
network server, account credential, microphone/video capture or state writes.
This is a one-shot user-invoked preflight, not an Apple device pairing grant.
"""
from __future__ import annotations

import json
import sys
from typing import Callable

import PhoneAudioControls as Audio
import PhoneFaceTimeAudioRouteProbe as Route

SCHEMA = "post-apollo.phone.facetime-iphone-only-preflight.v1"
EXECUTION = "READ_ONLY_EXPLICIT_USER_TEST"
def _provider_state(status: object) -> tuple[bool, str]:
    """Never infer that an optional cellular preference controls FaceTime."""
    if (type(status) is not dict
            or status.get("schema") != Audio.SCHEMA
            or status.get("execution") != "READ_ONLY"
            or status.get("result") != "OBSERVED"
            or status.get("trustedPhoneLink") != "UNVERIFIED"
            or status.get("contentAccessEnabled") is not False
            or type(status.get("ofonoActive")) is not bool):
        return False, "UNKNOWN"
    setting = status.get("callsEnabled")
    if setting is False:
        # Official BlueFerry CallsController.snapshot() omits calls_state
        # when calls_enabled is false. Do not mark its daemon broken.
        return True, "OFF"
    if setting is True:
        # Preference ON does not mean Calls1 HFP ready or FaceTime active.
        # A separate, independently validated calls_state is needed for
        # cellular readiness (handled by PhoneFaceTimeAudioRouteProbe).
        return True, "ON"
    return True, "UNKNOWN"


def _capability_flags(status: object) -> tuple[bool, bool]:
    """Only optional capability-marker presence and MAP/PBAP booleans.

    The app inventory marker does not mean a FaceTime notification was ever
    delivered. Never invoke ListNotificationApps or ListNotifications.
    """
    if (type(status) is not dict
            or type(status.get("api_version")) is not int
            or status.get("api_version") != 2
            or status.get("daemon") is not True):
        return False, False
    marker = status.get("notification_muted_app_count")
    apps_supported = type(marker) is int and 0 <= marker <= 1000000
    # MAP/PBAP is not an authenticated iPhone or an ANCS call signal.
    link_reported = status.get("map") is True or status.get("pbap") is True
    return apps_supported, link_reported


def _audio_flags(status: object) -> tuple[bool, bool]:
    if (type(status) is not dict
            or status.get("schema") != Route.SCHEMA
            or status.get("execution") != Route.EXECUTION
            or status.get("faceTimeAudioVerified") is not False
            or status.get("faceTimeConnected") is not False
            or status.get("faceTimeCallControl") is not False
            or status.get("microphoneVerified") is not False
            or status.get("speakerVerified") is not False
            or status.get("canChangeRoute") is not False
            or status.get("providerAuthenticated") is not False
            or status.get("personalDataAccess") is not False
            or type(status.get("systemAudioObserved")) is not bool
            or type(status.get("systemHfpProfileOffered")) is not bool
            or type(status.get("systemHfpProfileActive")) is not bool):
        return False, False
    if not status["systemAudioObserved"]:
        return False, False
    offered = status["systemHfpProfileOffered"]
    active = status["systemHfpProfileActive"]
    if active and not offered:
        return False, False
    return offered, active


def inspect(
    *, provider: Callable[[], object] = Audio.inspect,
    raw_status: Callable[[], object] = Audio._status_from_running_daemon,
    route: Callable[[], object] = Route.inspect,
) -> dict[str, object]:
    # Exact source states are checked at each observation boundary; races
    # produce only conservative booleans, not a connected/call-enabled claim.
    try:
        source_ok, cellular = _provider_state(provider())
    except Exception:
        source_ok, cellular = False, "UNKNOWN"
    apps_supported = link_reported = False
    if source_ok:
        try:
            apps_supported, link_reported = _capability_flags(raw_status())
        except Exception:
            pass
    try:
        hfp_offered, hfp_active = _audio_flags(route())
    except Exception:
        hfp_offered, hfp_active = False, False
    return {
        "schema": SCHEMA,
        "execution": EXECUTION,
        "blueferryResponding": source_ok,
        "cellularCallsPreference": cellular,
        "iphoneDataLinkSelfReported": link_reported,
        "notificationAppInventoryAdvertised": apps_supported,
        "localHfpOffered": hfp_offered,
        "localHfpActive": hfp_active,
        # Support on iPhone != a PC-side capability. These cannot be
        # promoted by status fields, local HFP or a self-reported test.
        "outboundIphoneShortcutVerified": False,
        "outboundPcDispatchAvailable": False,
        "incomingFaceTimeDetected": False,
        "answerFaceTimeAvailable": False,
        "endFaceTimeAvailable": False,
        "liveFaceTimeVideoAvailable": False,
        "twoWayFaceTimeAudioVerified": False,
        "iphoneCompanionAuthenticated": False,
        "faceTimeConnected": False,
        "canChangeRoute": False,
        "contentAccessEnabled": False,
        "personalSaveAuthorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--preflight"]:
        print(json.dumps({"schema": SCHEMA, "execution": EXECUTION,
                          "state": "EXPLICIT_ACTION_REQUIRED"}, sort_keys=True))
        return 2
    print(json.dumps(inspect(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
