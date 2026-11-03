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
CHRONYD_PATHS = ("/usr/sbin/chronyd", "/usr/bin/chronyd")
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


def classify_failure(exit_code, stderr="", stdout=""):
    """Summarize a privileged attempt without leaking arbitrary command logs."""
    # These two return codes are reserved by pkexec for authorization errors.
    # 127 can also indicate another execution error, so do not claim denial.
    if exit_code == 126:
        return result("cancelled", "AUTHENTICATION CANCELLED // NO VERIFIED SYNC",
                      errorCode="AUTH_CANCELLED")
    if exit_code == 127:
        return result("failed", "POLKIT AUTH OR EXECUTION ERROR // CHECK AUTH AGENT",
                      errorCode="POLKIT_OR_EXEC_ERROR")

    output = (stderr + "\n" + stdout).lower()
    if any(term in output for term in (
            "could not resolve", "unable to resolve",
            "temporary failure in name resolution", "name or service not known")):
        return result("failed", "TIME SOURCE DNS RESOLUTION FAILED",
                      errorCode="SOURCE_DNS")
    if any(term in output for term in (
            "no suitable source", "no sources online", "no reachable sources",
            "can't synchronise", "cannot synchronise", "not synchronised",
            "no source selected")):
        return result("failed", "NO USABLE TIME SERVER SAMPLE // CHECK SOURCES",
                      errorCode="SOURCE_UNAVAILABLE")
    if any(term in output for term in (
            "permission denied", "operation not permitted",
            "not authorised", "not authorized")):
        return result("failed", "CHRONY PERMISSION OR CAPABILITY ERROR",
                      errorCode="CHRONY_PERMISSION")
    if any(term in output for term in (
            "another chronyd", "already running", "address already in use")):
        return result("failed", "CHRONY INSTANCE CONFLICT // NO VERIFIED SYNC",
                      errorCode="CHRONY_CONFLICT")
    return result("failed", "CHRONY COMMAND FAILED // NO VERIFIED SYNC",
                  errorCode="CHRONY_FAILED", exitCode=exit_code)


def diagnose():
    """Read-only prerequisites. Does not contact time servers or change time."""
    chronyd = next((p for p in CHRONYD_PATHS if os.path.isfile(p)), None)
    if not os.path.isfile(PKEXEC):
        return result("unavailable", "POLKIT EXECUTABLE MISSING",
                      errorCode="NO_PKEXEC")
    if chronyd is None:
        return result("unavailable", "CHRONY DAEMON EXECUTABLE MISSING",
                      errorCode="NO_CHRONYD")
    try:
        service = subprocess.run(
            ["systemctl", "is-active", "chronyd.service"],
            capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return result("unavailable", "CANNOT READ CHRONY SERVICE STATE",
                      errorCode="SERVICE_UNKNOWN")
    state = service.stdout.strip()
    if service.returncode == 0 and state == "active":
        if not os.path.isfile(CHRONYC):
            return result("unavailable", "CHRONY CONTROL CLIENT MISSING",
                          errorCode="NO_CHRONYC")
        try:
            tracking = subprocess.run(
                [CHRONYC, "tracking"], capture_output=True, text=True,
                timeout=TIMEOUT, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return result("unavailable", "CHRONY CONTROL QUERY FAILED",
                          errorCode="CHRONYC_QUERY_FAILED")
        if tracking.returncode:
            return result("unavailable", "DAEMON ACTIVE // CONTROL SOCKET UNAVAILABLE",
                          errorCode="CHRONY_SOCKET_UNAVAILABLE")
        return result("ready", "DAEMON ACTIVE // BURST PATH READY",
                      errorCode="",
                      detail="TIME SERVER HEALTH AND AUTHORIZATION NOT VERIFIED")
    if state in ("inactive", "failed"):
        return result("ready", "DAEMON STOPPED // ONE-SHOT PATH READY",
                      errorCode="",
                      detail="TIME SERVER HEALTH AND AUTHORIZATION NOT VERIFIED")
    return result("unavailable", "UNEXPECTED CHRONY SERVICE STATE",
                  errorCode="SERVICE_UNKNOWN")


def privileged(command, success_status, success_message, timeout):
    try:
        proc = subprocess.run(
            [PKEXEC] + command, capture_output=True, text=True,
            timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return result("failed", "SYNC / AUTH TIMEOUT // VERIFY SYSTEM TIME")
    except OSError:
        return result("failed", "AUTHENTICATED SYNC COULD NOT START")
    if proc.returncode:
        return classify_failure(proc.returncode, proc.stderr, proc.stdout)
    return result(success_status, success_message)


def resync():
    # Explicitly confirmed by the Settings UI. Never toggle NTP enablement.
    if not os.path.isfile(PKEXEC):
        return result("unavailable", "POLKIT AUTH UNAVAILABLE // CLOCK UNCHANGED")

    # Preferred when the managed daemon is already running: ask for samples,
    # and let Chrony slew the correction rather than forcibly step the clock.
    if os.path.isfile(CHRONYC):
        try:
            probe = subprocess.run(
                [CHRONYC, "tracking"], capture_output=True, text=True,
                timeout=TIMEOUT, check=False)
        except (OSError, subprocess.TimeoutExpired):
            probe = None
        if probe is not None and probe.returncode == 0:
            return privileged(
                [CHRONYC, "burst", "4/4"], "requested",
                "FRESH CHRONY SAMPLES REQUESTED // CORRECTION NOT VERIFIED", 45)

    # When the user has turned automatic synchronization off, a separate
    # chronyd -q process can set the clock once and exit, without enabling
    # the background service. This CAN jump wall time, hence UI confirmation.
    # Do not start a second daemon if the service state is not clearly stopped.
    chronyd = next((name for name in CHRONYD_PATHS if os.path.isfile(name)), None)
    if chronyd is None:
        return result("unavailable", "CHRONY ONE-SHOT NOT INSTALLED")
    try:
        active = subprocess.run(
            ["systemctl", "is-active", "chronyd.service"],
            capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return result("unavailable", "CHRONY SERVICE STATE UNKNOWN // NO CHANGE")
    if active.returncode == 0 or active.stdout.strip() not in ("inactive", "failed"):
        return result("unavailable", "CHRONY SERVICE NOT SAFELY STOPPED // NO CHANGE")

    # -q exits after one correction. -t limits how long it waits for samples.
    # Uses the machine's configured Chrony sources, not invented servers.
    return privileged(
        [chronyd, "-q", "-t", "15"], "completed",
        "ONE-SHOT TIME CORRECTION COMPLETED // VERIFY SYSTEM TIME", 45)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "resync", "diagnose"):
        data = result("invalid", "EXPECTED STATUS OR RESYNC")
    elif sys.argv[1] == "status":
        data = status()
    elif sys.argv[1] == "diagnose":
        data = diagnose()
    else:
        data = resync()
    print(json.dumps(data, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
