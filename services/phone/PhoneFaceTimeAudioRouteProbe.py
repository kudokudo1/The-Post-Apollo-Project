#!/usr/bin/env python3
"""Read-only FaceTime Audio HFP *candidate* observation for Social PHONE.

Apple can route an iPhone FaceTime call to a Bluetooth hands-free endpoint, but
the BlueFerry cellular Calls1 interface has no FaceTime session identity.
The PulseAudio-compatible (PipeWire) cards below may belong to other devices.
Thus the result cannot prove iPhone selection, mic/speaker transport, FaceTime
control, or any protected PHONE/Identity permission.

One explicit --status action; fixed read-only pactl command, no shell, no
pairing, service startup, mixer/device/profile changes, or raw device output.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Callable

import PhoneAudioControls as Audio

SCHEMA = "post-apollo.phone.facetime-audio-route.v1"
EXECUTION = "READ_ONLY_USER_INITIATED"
MAX_BYTES = 131072
MAX_CARDS = 32
MAX_PROFILES = 64

# PulseAudio/PipeWire profile names, not Bluetooth MACs or device identifiers.
# A2DP is intentionally excluded. Media preference != hands-free routing.
_HFP_PROFILE = re.compile(
    r"^(?:headset-head-unit|handsfree-head-unit|handsfree_head_unit"
    r"|headset_head_unit|hfp(?:_[a-z]+)?)(?:-[a-z0-9_+-]+)?$"
)
_ALLOWED = frozenset({
    "AUDIO_INSPECTION_UNAVAILABLE", "PHONE_BRIDGE_UNAVAILABLE",
    "PHONE_CALL_STATUS_UNREPORTED", "PHONE_CALLS_NOT_READY",
    "HFP_PROFILE_NOT_OBSERVED",
    "HFP_PROFILE_AVAILABLE_ONLY", "HFP_SYSTEM_PROFILE_ACTIVE",
})


def _profile_name(profile: object) -> str:
    name = profile.get("name") if type(profile) is dict else profile
    if type(name) is not str or len(name) > 64:
        return ""
    return name.lower() if name.isascii() else ""


def _is_hfp(name: str) -> bool:
    return bool(_HFP_PROFILE.fullmatch(name))


def project_audio_cards(payload: object) -> tuple[bool, bool] | None:
    """Aggregate a strict local BlueZ card view, never identify the iPhone.

    (some HFP profile offered, a HFP profile actively selected).
    Return None on malformed/oversized card data: missing data is not "no
    Bluetooth", nor is another headset sufficient for a FaceTime claim.
    """
    if type(payload) is not list or len(payload) > MAX_CARDS:
        return None
    offered = active = False
    for card in payload:
        if type(card) is not dict:
            return None
        props = card.get("properties")
        name = card.get("name")
        if type(name) is not str or len(name) > 128 or type(props) is not dict:
            return None
        # Do not treat an ordinary local ALSA headset as an iPhone HFP link.
        if not (name.startswith("bluez_card.")
                and (props.get("device.api") == "bluez5"
                     or props.get("device.bus") == "bluetooth")):
            continue
        profiles = card.get("profiles", [])
        if type(profiles) not in (list, dict) or len(profiles) > MAX_PROFILES:
            return None
        # pactl versions may serialize profiles as a JSON list of objects
        # or as a map keyed by profile name. Both are untrusted until parsed.
        choices = profiles.keys() if type(profiles) is dict else profiles
        for profile in choices:
            value = _profile_name(profile)
            if value and _is_hfp(value):
                offered = True
        current = _profile_name(card.get("active_profile"))
        if current and _is_hfp(current):
            active = True
            offered = True
    return offered, active


def _pactl_cards(
    *, find: Callable[[str], str | None] = shutil.which,
    run: Callable[..., object] = subprocess.run,
) -> tuple[bool, bool] | None:
    try:
        binary = find("pactl")
        if type(binary) is not str or not os.path.isabs(binary):
            return None
        env = os.environ.copy()
        env["PULSE_NO_AUTOSPAWN"] = "1"
        env["LC_ALL"] = "C"
        response = run(
            [binary, "-f", "json", "list", "cards"],
            capture_output=True, text=True, check=False, timeout=4, env=env,
        )
        output = getattr(response, "stdout", None)
        if (getattr(response, "returncode", None) != 0
                or type(output) is not str
                or len(output.encode("utf-8")) > MAX_BYTES):
            return None
        return project_audio_cards(json.loads(output))
    except (OSError, ValueError, TypeError, UnicodeError,
            subprocess.SubprocessError):
        return None


def _blueferry_ready(observation: object) -> tuple[bool, bool, bool]:
    """Separate a reachable BlueFerry daemon from its optional call status.

    PhoneAudioControls.inspect() explicitly projects missing/non-string
    calls_state as UNKNOWN. That is an observed *partial* provider response,
    not proof the D-Bus daemon is offline or cellular HFP is ready.
    Returns (provider_observed, cellular_hfp_ready, call_fields_reported).
    """
    if (type(observation) is not dict
            or observation.get("schema") != Audio.SCHEMA
            or observation.get("execution") != "READ_ONLY"
            or observation.get("result") != "OBSERVED"
            or observation.get("trustedPhoneLink") != "UNVERIFIED"
            or observation.get("contentAccessEnabled") is not False
            or type(observation.get("ofonoActive")) is not bool):
        return False, False, False
    reported = (
        type(observation.get("callsEnabled")) is bool
        and type(observation.get("callsState")) is str
        and observation.get("callsState") in (
            "READY", "SEARCHING", "CONNECTING", "BLUEZ_CONFLICT",
            "UNAVAILABLE", "DISABLED")
    )
    if not reported:
        return True, False, False
    return True, (
        observation["callsEnabled"] is True
        and observation["callsState"] == "READY"
        and observation["ofonoActive"] is True
    ), True


def _response(state: str, *, provider: bool = False,
              ready: bool = False, system: bool = False,
              offered: bool = False, active: bool = False) -> dict[str, object]:
    assert state in _ALLOWED
    # Only categorical facts. No MAC/address, process paths, microphone
    # content, Apple account, FaceTime join secret, or raw backend JSON.
    return {
        "schema": SCHEMA,
        "execution": EXECUTION,
        "state": state,
        "phoneBackendObserved": provider,
        "cellularHfpReadyReported": ready,
        "systemAudioObserved": system,
        "systemHfpProfileOffered": offered,
        "systemHfpProfileActive": active,
        "faceTimeAudioVerified": False,
        "faceTimeConnected": False,
        "faceTimeCallControl": False,
        "microphoneVerified": False,
        "speakerVerified": False,
        "canChangeRoute": False,
        "providerAuthenticated": False,
        "personalDataAccess": False,
    }


def inspect(
    *, provider: Callable[[], object] = Audio.inspect,
    cards: Callable[[], tuple[bool, bool] | None] = _pactl_cards,
) -> dict[str, object]:
    # Deliberately independent observations. They do not correlate BlueZ card
    # to the selected iPhone, so neither can ever become FaceTime verification.
    try:
        value = provider()
        observed, ready, call_fields_reported = _blueferry_ready(value)
    except Exception:
        observed, ready, call_fields_reported = False, False, False
    try:
        audio = cards()
    except Exception:
        audio = None
    if (type(audio) is not tuple or len(audio) != 2
            or type(audio[0]) is not bool or type(audio[1]) is not bool
            or (audio[1] and not audio[0])):
        return _response("AUDIO_INSPECTION_UNAVAILABLE", provider=observed,
                         ready=ready)
    offered, active = audio
    if not observed:
        state = "PHONE_BRIDGE_UNAVAILABLE"
    elif not call_fields_reported:
        state = "PHONE_CALL_STATUS_UNREPORTED"
    elif not ready:
        state = "PHONE_CALLS_NOT_READY"
    elif active:
        state = "HFP_SYSTEM_PROFILE_ACTIVE"
    elif offered:
        state = "HFP_PROFILE_AVAILABLE_ONLY"
    else:
        state = "HFP_PROFILE_NOT_OBSERVED"
    return _response(state, provider=observed, ready=ready, system=True,
                     offered=offered, active=active)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    value = inspect() if args == ["--status"] else _response(
        "AUDIO_INSPECTION_UNAVAILABLE")
    print(json.dumps(value, sort_keys=True))
    return 0 if args == ["--status"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
