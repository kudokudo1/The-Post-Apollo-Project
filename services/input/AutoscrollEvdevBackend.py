#!/usr/bin/env python3
"""EXPERIMENTAL mouse-only evdev/uinput driver for Post-Apollo autoscroll.

Not launched by Quickshell, not installed as a service, not run at startup.
--probe only checks host prerequisites; --live requires an exact physical
event-device selector AND explicit experimental opt-in. No privileges are
granted or installed here. The device is exclusively grabbed ONLY after
successfully creating its virtual replacement, and released on any exit.

Limitations: no compositor-global anchor coordinates/visual overlay yet,
no global Escape binding, and hardware behavior is NOT verified on SwayFX.
Never enable this automatically in CPU++ before independent live tests.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time

from AutoscrollMouseEngine import MouseAutoscroll, BTN_MIDDLE

MOUSE_MIN = 272
MOUSE_MAX = 287
REL_X = 0
REL_Y = 1
REL_HWHEEL = 6
REL_WHEEL = 8
REL_WHEEL_HI_RES = 11
REL_HWHEEL_HI_RES = 12
ALLOWED_REL = (REL_X, REL_Y, REL_HWHEEL, REL_WHEEL,
               REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES)
DEVICE_RE = re.compile(r"^/dev/input/event[0-9]{1,5}$")
TICK_SECONDS = 1.0 / 90.0
FOCUS_SECONDS = 0.30
RUN_MARKER = "POST_APOLLO_AUTOSCROLL_EXPERIMENTAL"
VIRTUAL_NAME = "Post-Apollo Autoscroll Virtual Pointer"


class DriverError(Exception):
    pass


def select_physical_device(path: str) -> Path:
    # A stable /dev/input/by-id symlink is allowed, but may point ONLY to an
    # actual kernel /dev/input/event device. No generic file reads.
    if not isinstance(path, str) or not path.startswith("/dev/input/"):
        raise DriverError("DEVICE_PATH_REQUIRED")
    raw = Path(path)
    try:
        resolved = raw.resolve(strict=True)
        info = resolved.stat()
    except (OSError, RuntimeError) as exc:
        raise DriverError("DEVICE_NOT_PRESENT") from exc
    if not DEVICE_RE.fullmatch(str(resolved)) or not stat.S_ISCHR(info.st_mode):
        raise DriverError("NOT_A_PHYSICAL_EVENT_DEVICE")
    return resolved


def import_evdev():
    if importlib.util.find_spec("evdev") is None:
        raise DriverError("PYTHON_EVDEV_MISSING")
    import evdev
    return evdev


def validate_mouse(caps: dict) -> tuple[list[int], list[int]]:
    """Reject keyboard-capable or synthetic devices before ever grabbing."""
    if not isinstance(caps, dict):
        raise DriverError("UNSUPPORTED_CAPABILITIES")
    key_codes = caps.get(1, [])
    rel_codes = caps.get(2, [])
    if not all(isinstance(c, int) for c in key_codes + rel_codes):
        raise DriverError("UNSUPPORTED_CAPABILITIES")
    if (not {272, 273, BTN_MIDDLE}.issubset(set(key_codes))
            or not {REL_X, REL_Y}.issubset(set(rel_codes))
            or any(c < MOUSE_MIN or c > MOUSE_MAX for c in key_codes)
            or any(c not in ALLOWED_REL for c in rel_codes)
            or 3 in caps):  # EV_ABS devices need a different preservation path
        raise DriverError("NOT_MOUSE_ONLY")
    return sorted(set(key_codes)), sorted(set(rel_codes).union({
        REL_WHEEL, REL_HWHEEL, REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES
    }))


def sway_focus() -> str | None:
    """Read-only focused node identity, fail closed on multiseat ambiguity."""
    try:
        p = subprocess.run(["swaymsg", "-t", "get_seats"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, check=False, timeout=1.5)
        if p.returncode or len(p.stdout) > 131072:
            return None
        seats = json.loads(p.stdout)
        if (not isinstance(seats, list) or len(seats) != 1
                or not isinstance(seats[0], dict)):
            return None
        node = seats[0].get("focus")
        if not isinstance(node, int) or isinstance(node, bool) or node <= 0:
            return None
        return str(seats[0].get("name", "seat0")) + ":" + str(node)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def no_native_lock() -> bool:
    # The separate Sway Scroll Lock module writes this known recovery record.
    # Refuse to compete for middle-click if a prior session owns the pointer.
    from SwayScrollLock import snapshot_path, read_owned
    try:
        return read_owned(snapshot_path()) is None
    except Exception:
        return False


def probe() -> dict:
    """No device opens, no raw input read, no writes."""
    module = importlib.util.find_spec("evdev") is not None
    return {
        "status": "prerequisites" if module else "unavailable",
        "evdev": module,
        "uinput_access": os.access("/dev/uinput", os.W_OK),
        "sway_ipc": bool(os.environ.get("SWAYSOCK")),
        "native_scroll_lock_clear": no_native_lock(),
        "enabled": False,
        "permission_changes": False,
        "global_overlay": False,
        "escape_binding": False,
        "hardware_verified": False
    }


def run_live(device_path: str) -> int:
    if (os.environ.get(RUN_MARKER) != "1" or os.getuid() == 0):
        raise DriverError("EXPERIMENTAL_NONROOT_OPTIN_REQUIRED")
    if not os.environ.get("SWAYSOCK") or not no_native_lock():
        raise DriverError("NO_COMPATIBLE_SWAY_INPUT_OWNER")
    if sway_focus() is None:
        raise DriverError("NO_VERIFIED_SINGLE_SEAT_FOCUS")
    physical = select_physical_device(device_path)
    evdev = import_evdev()
    from evdev import ecodes, InputDevice, UInput
    source = InputDevice(str(physical))
    virtual = None
    grabbed = False
    stop = False
    engine = MouseAutoscroll()
    focus = sway_focus()
    last_focus_check = time.monotonic()
    last_tick = last_focus_check
    coarse_v = coarse_h = 0

    def terminate(_signal, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    try:
        if (not source.name or VIRTUAL_NAME.casefold() in source.name.casefold()
                or getattr(source, "info", None) is None):
            raise DriverError("INVALID_PHYSICAL_DEVICE")
        keys, rels = validate_mouse(source.capabilities(absinfo=False))
        # Never advertise keyboard keys. The virtual device is a mouse only.
        virtual = UInput({ecodes.EV_KEY: keys, ecodes.EV_REL: rels},
                         name=VIRTUAL_NAME,
                         vendor=source.info.vendor,
                         product=source.info.product,
                         bustype=source.info.bustype)
        source.grab()  # Kernel releases automatically if daemon crashes.
        grabbed = True
        while not stop:
            now = time.monotonic()
            if now - last_focus_check >= FOCUS_SECONDS:
                focus = sway_focus()
                last_focus_check = now
                if not no_native_lock():
                    engine.cancel("native_lock_collision")
                    stop = True
            changed = False
            ready, _, _ = select.select([source.fd], [], [], TICK_SECONDS)
            if ready:
                try:
                    events = source.read()
                except OSError as exc:
                    raise DriverError("INPUT_DEVICE_DISCONNECTED") from exc
                for event in events:
                    if event.type == ecodes.EV_SYN:
                        if changed:
                            virtual.syn()
                            changed = False
                        continue
                    if event.type == ecodes.EV_KEY:
                        if event.code not in keys or event.value not in (0, 1):
                            raise DriverError("UNEXPECTED_INPUT_EVENT")
                        if engine.key_event(event.code, event.value,
                                            time.monotonic(), focus):
                            continue
                    elif event.type == ecodes.EV_REL:
                        if event.code not in rels:
                            raise DriverError("UNEXPECTED_REL_EVENT")
                        if event.code in (REL_X, REL_Y) and engine.active:
                            engine.motion(event.value if event.code == REL_X else 0,
                                          event.value if event.code == REL_Y else 0)
                            continue
                    else:
                        raise DriverError("UNSUPPORTED_EVENT_TYPE")
                    virtual.write(event.type, event.code, event.value)
                    changed = True
            if changed:
                virtual.syn()
            current = time.monotonic()
            if engine.active:
                # Clamped dt; prolonged scheduling stall safely cancels output.
                dt = (current - last_tick) * 1000.0
                hi_v, hi_h = engine.tick(current, dt, focus)
                for axis, units in ((REL_WHEEL_HI_RES, hi_v),
                                    (REL_HWHEEL_HI_RES, hi_h)):
                    if units:
                        virtual.write(ecodes.EV_REL, axis, units)
                coarse_v += hi_v
                coarse_h += hi_h
                v = math.trunc(coarse_v / 120)
                h = math.trunc(coarse_h / 120)
                coarse_v -= v * 120
                coarse_h -= h * 120
                if v:
                    virtual.write(ecodes.EV_REL, REL_WHEEL, v)
                if h:
                    virtual.write(ecodes.EV_REL, REL_HWHEEL, h)
                if hi_v or hi_h or v or h:
                    virtual.syn()
            else:
                coarse_v = coarse_h = 0
            last_tick = current
        return 0
    finally:
        engine.cancel("service_stopped")
        if grabbed:
            try:
                source.ungrab()
            except OSError:
                pass
        source.close()
        if virtual is not None:
            virtual.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Post-Apollo experimental mouse-only autoscroll")
    parser.add_argument("--probe", action="store_true", help="read-only prerequisites")
    parser.add_argument("--live", action="store_true", help="manual experimental run only")
    parser.add_argument("--device", help="exact /dev/input/eventN or /dev/input/by-id pointer")
    args = parser.parse_args(argv)
    try:
        if args.probe and not args.live and not args.device:
            out = probe()
        elif args.live and not args.probe and args.device:
            return run_live(args.device)
        else:
            raise DriverError("INVALID_ARGUMENT_COMBINATION")
        print(json.dumps(out, separators=(",", ":")))
        return 0
    except DriverError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
