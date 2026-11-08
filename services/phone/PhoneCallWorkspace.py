#!/usr/bin/env python3
"""P25: bounded Personal CALLS workspace on already-running BlueFerry Calls1.

Only an explicit user click may request an action; --status is observation.
The remote provider and oFono remain the call-control authority.  This is a
same-Linux-user desktop bridge, NOT an authenticated Identity Center grant.
Never auto-start BlueFerry, oFono, Bluetooth, or alter WirePlumber/audio.
No call content, dial numbers, access tokens or D-Bus errors are logged.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Callable

from BlueFerryHostReadPort import (
    UniqueOwnerBlueFerrySource, _owner_valid, OBJECT, SERVICE,
)
from PhoneDeviceObservation import PROFILE, observe as observe_device

SCHEMA = "post-apollo.phone.calls-workspace.v0"
EXECUTION = "PERSONAL_SESSION_BLUEFERRY_CALLS1"
CALLS_IFACE = SERVICE + ".Calls1"
MAX_REPLY_BYTES = 65536
MAX_CALLS = 8
MAX_PEER = 96
CALL_STATES = frozenset({
    "incoming", "waiting", "dialing", "alerting", "active", "held",
    "disconnecting",
})
DIRECTIONS = frozenset({"incoming", "outgoing", "unknown"})
HFP_STATES = frozenset({
    "disabled", "unavailable", "searching", "connecting", "ready", "bluez_conflict",
})
CALL_ID = re.compile(r"^[A-Za-z0-9_./:-]{1,128}$")
DIAL = re.compile(r"^\+?[0-9]{3,18}$")
TONES = re.compile(r"^[0-9*#]{1,32}$")
KNOWN_EMERGENCY = frozenset({
    "000", "110", "112", "117", "118", "119", "144", "911", "999",
})


def _reply(state: str, **extra: object) -> dict[str, object]:
    return {
        "schema": SCHEMA, "execution": EXECUTION, "state": state,
        "scope": "PERSONAL_LOCAL_USER_ONLY",
        "organizationGrant": False, "faceTimeEnabled": False,
        "smsReplyEnabled": False, "autoCallingEnabled": False,
        **extra,
    }


def _connected(profile: str, observer: Callable[[], object]) -> bool:
    try:
        data = observer()
        return (
            type(data) is dict
            and data.get("schema") == "post-apollo.phone.device-observation.v0"
            and data.get("execution") == "READ_ONLY_DEVICE_OBSERVATION"
            and data.get("state") == "BLUETOOTH_CONNECTED"
            and data.get("bluetoothLink") == "CONNECTED"
            and type(data.get("profileId")) is str
            and data["profileId"] == profile
            and data.get("trustedPhoneLink") == "UNVERIFIED"
            and data.get("contentAccessEnabled") is False
        )
    except Exception:
        return False


def _peer(value: object) -> str:
    if type(value) is not str:
        return ""
    clean = value.strip()
    if not clean or len(clean) > MAX_PEER or not clean.isprintable():
        return ""
    return clean


def _masked_number(value: object) -> str:
    if type(value) is not str or len(value) > 64:
        return ""
    digits = "".join(c for c in value if c.isascii() and c.isdecimal())
    return "•••• " + digits[-4:] if len(digits) >= 4 else ""


def _calls(raw: object) -> list[dict[str, object]]:
    if type(raw) is not dict or raw.get("state") != "ready":
        raise ValueError("calls unavailable")
    records = raw.get("calls")
    if type(records) is not list or len(records) > MAX_CALLS:
        raise ValueError("invalid call count")
    seen: set[str] = set()
    output: list[dict[str, object]] = []
    for item in records:
        if type(item) is not dict:
            raise ValueError("invalid call")
        cid = item.get("call_id")
        state = item.get("state")
        direction = item.get("direction", "unknown")
        if (type(cid) is not str or not CALL_ID.fullmatch(cid)
                or cid in seen or type(state) is not str
                or state not in CALL_STATES or type(direction) is not str
                or direction not in DIRECTIONS
                or type(item.get("multiparty", False)) is not bool
                or type(item.get("emergency", False)) is not bool):
            raise ValueError("invalid call details")
        seen.add(cid)
        name = _peer(item.get("contact_name", ""))
        peer = name or _masked_number(item.get("number", "")) or "Unknown caller"
        output.append({
            "id": cid, "state": state, "direction": direction,
            "peer": peer, "multiparty": item.get("multiparty", False),
            "emergency": item.get("emergency", False),
        })
    return output


class BlueFerryCallsSource(UniqueOwnerBlueFerrySource):
    """Bind every Calls1 method to the same already-running unique D-Bus owner."""

    def _calls_iface(self, owner: str) -> Any:
        if not _owner_valid(owner):
            raise ValueError("unverified daemon owner")
        return self._dbus.Interface(
            self._bus.get_object(owner, OBJECT, introspect=False), CALLS_IFACE,
        )

    def calls(self, owner: str) -> dict[str, Any]:
        return self._json(
            self._calls_iface(owner).ListCalls(timeout=5),
            bound=MAX_REPLY_BYTES, kind=dict,
        )

    def perform(self, owner: str, action: str, arg: str = "") -> None:
        iface = self._calls_iface(owner)
        if action == "dial":
            iface.Dial(arg, timeout=25)
        elif action == "answer":
            iface.Answer(arg, timeout=25)
        elif action in ("decline", "hangup"):
            iface.Hangup(arg, timeout=25)
        elif action == "tones":
            call_id, tones = arg.split("\t", 1)
            iface.SendTones(call_id, tones, timeout=25)
        elif action == "swap":
            iface.SwapCalls(timeout=25)
        elif action == "hold-answer":
            iface.HoldAndAnswer(timeout=25)
        else:
            raise ValueError("unsupported call action")


def _status(source: Any, owner: str) -> tuple[str, str]:
    raw = source.status(owner)
    if (type(raw) is not dict
            or type(raw.get("api_version")) is not int
            or raw.get("api_version") != 2
            or raw.get("daemon") is not True):
        return "", ""
    profile = raw.get("phone_profile_id")
    if type(profile) is not str or PROFILE.fullmatch(profile) is None:
        return "", ""
    if type(raw.get("calls_enabled")) is not bool:
        return profile, "UNSUPPORTED"
    if not raw["calls_enabled"]:
        return profile, "DISABLED"
    state = raw.get("calls_state")
    if type(state) is not str or state not in HFP_STATES:
        return profile, "UNSUPPORTED"
    return profile, state.upper()


def _allowed(action: str, argument: str, calls: list[dict[str, object]]) -> bool:
    if action == "dial":
        return (bool(DIAL.fullmatch(argument))
                and argument.lstrip("+") not in KNOWN_EMERGENCY)
    by_id = {str(c["id"]): c for c in calls}
    if action in ("answer", "decline", "hangup"):
        call = by_id.get(argument)
        if call is None:
            return False
        if action in ("answer", "decline"):
            return call["state"] in ("incoming", "waiting")
        return call["state"] in ("active", "held", "dialing", "alerting")
    if action == "tones":
        if "\t" not in argument:
            return False
        cid, tones = argument.split("\t", 1)
        return bool(TONES.fullmatch(tones)) and cid in by_id and by_id[cid]["state"] == "active"
    if action == "swap":
        return sum(c["state"] == "active" for c in calls) == 1 and any(
            c["state"] == "held" for c in calls
        )
    if action == "hold-answer":
        return any(c["state"] == "active" for c in calls) and any(
            c["state"] == "waiting" for c in calls
        )
    return False


def run(
    argv: list[str], *,
    source_factory: Callable[[], Any] = BlueFerryCallsSource,
    observer: Callable[[], object] = observe_device,
) -> dict[str, object]:
    if not isinstance(argv, list):
        return _reply("REFUSED")
    reading = argv == ["--status"]
    action = argv[1] if len(argv) >= 2 and argv[0] == "--action" else ""
    argument = argv[2] if len(argv) == 3 else ""
    allowed_shapes = (
        len(argv) == 3 and action in ("dial", "answer", "decline", "hangup", "tones")
        or len(argv) == 2 and action in ("swap", "hold-answer")
    )
    if not reading and not allowed_shapes:
        return _reply("REFUSED")
    if type(argument) is not str or len(argument) > 128:
        return _reply("REFUSED")

    try:
        source = source_factory()
        owner = source.owner()
        if not _owner_valid(owner):
            return _reply("BACKEND_UNAVAILABLE")
        profile, state = _status(source, owner)
        if not profile:
            return _reply("BACKEND_UNAVAILABLE")
        if not _connected(profile, observer):
            return _reply("DEVICE_UNAVAILABLE")
        if state != "READY":
            return _reply(state)
        calls = _calls(source.calls(owner))
        if source.owner() != owner or not _connected(profile, observer):
            return _reply("DEVICE_UNAVAILABLE")
        if reading:
            return _reply("READY", calls=calls)
        if not _allowed(action, argument, calls):
            return _reply("ACTION_REFUSED")
        if source.owner() != owner:
            return _reply("DEVICE_UNAVAILABLE")
        # One explicitly requested backend-owned action. No hidden auto-dial,
        # auto-answer, call forwarding or modification of the audio stack.
        source.perform(owner, action, argument)
        after_profile, after_state = _status(source, owner)
        if (source.owner() != owner or after_profile != profile
                or not _connected(profile, observer)):
            return _reply("DEVICE_UNAVAILABLE")
        if after_state not in ("READY", "CONNECTING"):
            return _reply("ACTION_NOT_CONFIRMED")
        # Method reply means accepted; not proof of a connected call/audio.
        return _reply("ACTION_SUBMITTED", action=action)
    except Exception:
        return _reply("BACKEND_UNAVAILABLE" if reading else "ACTION_FAILED")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 2 if result["state"] == "REFUSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
