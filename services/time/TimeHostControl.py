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



def measure_clock():
    """Opt-in reference check. -Q never changes the system clock.

    Chrony can emit a valid measured offset even if it later fails to write
    drift.tmp as an unprivileged user. We use only the explicitly reported
    numeric measurement, never assume exit status alone proves accuracy.
    This contacts configured time sources and exposes the host IP to them.
    """
    import re
    chronyd = next((p for p in CHRONYD_PATHS if os.path.isfile(p)), None)
    if not chronyd:
        return result("unavailable", "CHRONY REFERENCE CHECK NOT INSTALLED",
                      errorCode="NO_CHRONYD")
    try:
        active = subprocess.run(
            ["systemctl", "is-active", "chronyd.service"],
            capture_output=True, text=True, timeout=TIMEOUT, check=False)
        if active.returncode == 0 and active.stdout.strip() == "active":
            return result("unavailable", "DAEMON ACTIVE // USE LIVE CHRONY TRACKING",
                          errorCode="DAEMON_ACTIVE")
        if active.stdout.strip() not in ("inactive", "failed"):
            return result("unavailable", "CHRONY SERVICE STATUS UNKNOWN",
                          errorCode="SERVICE_UNKNOWN")
        reading = subprocess.run(
            [chronyd, "-Q", "-t", "15"],
            capture_output=True, text=True, timeout=22, check=False)
    except subprocess.TimeoutExpired:
        return result("unavailable", "REFERENCE TIMEOUT // CLOCK NOT MEASURED",
                      errorCode="REFERENCE_TIMEOUT")
    except OSError:
        return result("unavailable", "REFERENCE PROCESS UNAVAILABLE",
                      errorCode="REFERENCE_PROCESS")
    combined = (reading.stdout + "\n" + reading.stderr)
    matched = re.search(
        r"System clock wrong by\\s+([+-]?\\d+(?:\\.\\d+)?)\\s+seconds", combined)
    if not matched:
        return result("unavailable", "NO TRUSTED OFFSET MEASUREMENT RETURNED",
                      errorCode="REFERENCE_NO_SAMPLE")
    seconds = float(matched.group(1))
    if not (-86400 <= seconds <= 86400):
        return result("unavailable", "REFERENCE OFFSET OUT OF RANGE",
                      errorCode="REFERENCE_INVALID")
    milliseconds = int(round(seconds * 1000))
    return result("measured", "REFERENCE OFFSET MEASURED // NO CLOCK CHANGE",
                  offsetMs=milliseconds,
                  note="REFERENCE SOURCE CONTACTED; CHRONY -Q DID NOT SET TIME")


def set_timezone(zone):
    """Set the real host timezone after systemd/Polkit authorization.

    The zone must be an exact member of the machine's installed tzdata.
    No shell, no password arguments, no manual /etc/localtime writes.
    """
    import re
    if not isinstance(zone, str) or len(zone) > 100 or not (
            zone == "UTC" or re.fullmatch(
                r"[A-Za-z][A-Za-z0-9._+-]*(?:/[A-Za-z0-9._+-]+)+", zone)):
        return result("invalid", "INVALID TIMEZONE IDENTIFIER",
                      errorCode="ZONE_INVALID")
    try:
        catalog = subprocess.run(
            ["timedatectl", "list-timezones", "--no-pager"],
            capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return result("unavailable", "TIMEZONE DIRECTORY UNAVAILABLE",
                      errorCode="ZONE_DIRECTORY")
    if catalog.returncode or zone not in catalog.stdout.splitlines():
        return result("invalid", "TIMEZONE NOT INSTALLED ON HOST",
                      errorCode="ZONE_NOT_INSTALLED")
    if system_properties().get("Timezone") == zone:
        return result("unchanged", "TIMEZONE ALREADY SELECTED",
                      timezone=zone)
    try:
        operation = subprocess.run(
            ["timedatectl", "set-timezone", zone],
            capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return result("failed", "TIMEZONE AUTHORIZATION TIMED OUT",
                      errorCode="ZONE_TIMEOUT")
    except OSError:
        return result("failed", "TIMEZONE SERVICE UNAVAILABLE",
                      errorCode="ZONE_SERVICE")
    if operation.returncode:
        output = (operation.stdout + "\n" + operation.stderr).lower()
        if "access denied" in output or "interactive authentication" in output or "authentication required" in output:
            return result("failed", "TIMEZONE AUTHENTICATION UNAVAILABLE",
                          errorCode="ZONE_AUTH")
        return result("failed", "HOST REJECTED TIMEZONE CHANGE",
                      errorCode="ZONE_REJECTED", exitCode=operation.returncode)
    verified = system_properties().get("Timezone")
    if verified != zone:
        return result("failed", "TIMEZONE CHANGE NOT VERIFIED",
                      errorCode="ZONE_VERIFY")
    return result("completed", "HOST TIMEZONE VERIFIED // " + zone,
                  timezone=zone)


def main():
    if len(sys.argv) < 2 or (sys.argv[1] == "set-timezone" and len(sys.argv) != 3) or (sys.argv[1] != "set-timezone" and (len(sys.argv) != 2 or sys.argv[1] not in ("status", "resync", "diagnose", "measure"))):
        data = result("invalid", "EXPECTED STATUS OR RESYNC")
    elif sys.argv[1] == "status":
        data = status()
    elif sys.argv[1] == "diagnose":
        data = diagnose()
    elif sys.argv[1] == "measure":
        data = measure_clock()
    elif sys.argv[1] == "set-timezone":
        data = set_timezone(sys.argv[2])
    else:
        data = resync()
    print(json.dumps(data, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
