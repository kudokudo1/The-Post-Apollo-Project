#!/usr/bin/env python3
"""Clock time status and guarded, one-shot chrony resync request.

Never changes NTP enablement, timezone, RTC mode, persistent chrony config,
or display calibration. A resync is NOT a proof of accurate time.
No shell=True, untrusted executable paths, or user-supplied commands.
"""
import datetime
import json
import os
import subprocess
import sys
import time

CHRONYC = "/usr/bin/chronyc"
PKEXEC = "/usr/bin/pkexec"
TIMEOUT = 5


def result(status, message="", **values):
    data = {"status": status, "message": message}
    data.update(values)
    return data


def system_properties():
    try:
        proc = subprocess.run(
            ["timedatectl", "show", "--property=Timezone", "--property=NTP",
             "--property=NTPSynchronized", "--property=LocalRTC"],
            capture_output=True, text=True, timeout=TIMEOUT, check=False)
        if proc.returncode:
            return {}
        return dict(line.strip().split("=", 1)
                    for line in proc.stdout.splitlines() if "=" in line)
    except (OSError, subprocess.TimeoutExpired):
        return {}


def status():
    props = system_properties()
    now = datetime.datetime.now().astimezone()
    local = time.localtime()
    offset = now.strftime("%z")
    label = ("UTC" + offset[:3] + ":" + offset[3:]) if len(offset) == 5 else "UNKNOWN"
    zone = props.get("Timezone") or "UNKNOWN"
    return result(
        "ready", "HOST TIME STATUS // READ ONLY",
        timezone=zone, abbreviation=local.tm_zone if hasattr(local, "tm_zone") else "",
        utcOffset=label, dstActive=local.tm_isdst > 0,
        ntpEnabled=props.get("NTP", "unknown"),
        ntpSynchronized=props.get("NTPSynchronized", "unknown"),
        rtcLocal=props.get("LocalRTC", "unknown")
    )


def resync():
    # This is not timedatectl set-ntp true: it must never persistently enable
    # synchronization behind the user's back.
    if not os.path.isfile(CHRONYC):
        return result("unavailable", "CHRONY NOT INSTALLED // CLOCK UNCHANGED")
    try:
        probe = subprocess.run(
            [CHRONYC, "tracking"], capture_output=True, text=True,
            timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return result("unavailable", "CHRONY NOT RESPONDING // CLOCK UNCHANGED")
    if probe.returncode:
        return result("unavailable",
                      "NO ACTIVE CHRONY CONNECTION // CLOCK UNCHANGED")
    if not os.path.isfile(PKEXEC):
        return result("unavailable",
                      "POLKIT AUTHENTICATION UNAVAILABLE // CLOCK UNCHANGED")
    try:
        # chronyc burst asks an already-running chronyd for fresh samples.
        # The daemon chooses safe correction. Do NOT force makestep: large
        # wall-clock jumps disrupt running apps, logs, and Machine timelines.
        proc = subprocess.run(
            [PKEXEC, CHRONYC, "burst", "4/4"],
            capture_output=True, text=True, timeout=45, check=False)
    except subprocess.TimeoutExpired:
        return result("failed", "AUTH / CHRONY TIMEOUT // VERIFY SYSTEM STATUS")
    except OSError:
        return result("failed", "RESYNC COMMAND COULD NOT START")
    if proc.returncode:
        return result("failed",
                      "RESYNC NOT AUTHORIZED OR CHRONY REFUSED // CLOCK UNCHANGED")
    return result("requested",
                  "FRESH TIME SAMPLES REQUESTED // CORRECTION NOT YET VERIFIED")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "resync"):
        data = result("invalid", "EXPECTED STATUS OR RESYNC")
    elif sys.argv[1] == "status":
        data = status()
    else:
        data = resync()
    print(json.dumps(data, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
