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



def parse_tracking_measurement(raw, at_utc=None):
    """Interpret read-only chronyc tracking as a bounded, recent estimate.

    The tracking output can exist without a synchronized reference. Require
    a normal leap state, a real non-local source, recent reference time and
    usable root-delay/dispersion accuracy bounds before claiming a reading.
    """
    import math
    import re
    fields = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    if fields.get("Leap status") != "Normal":
        return result("unavailable", "CHRONY SOURCE NOT SYNCHRONIZED",
                      errorCode="TRACKING_UNSYNCED")
    reference = fields.get("Reference ID", "")
    if reference.startswith(("00000000", "7F7F0101")):
        return result("unavailable", "CHRONY HAS NO EXTERNAL REFERENCE",
                      errorCode="TRACKING_LOCAL")
    try:
        stratum = int(fields.get("Stratum", "0"))
        ref_time = datetime.datetime.strptime(
            fields["Ref time (UTC)"], "%a %b %d %H:%M:%S %Y"
        ).replace(tzinfo=datetime.timezone.utc)
        now = at_utc or datetime.datetime.now(datetime.timezone.utc)
        sample_age = (now - ref_time).total_seconds()
        offset = re.fullmatch(
            r"([+-]?\d+(?:\.\d+)?) seconds (fast|slow) of NTP time",
            fields["System time"]
        )
        delay = float(fields["Root delay"].split()[0])
        dispersion = float(fields["Root dispersion"].split()[0])
        if stratum < 1 or stratum > 15 or offset is None:
            raise ValueError("invalid tracking metadata")
        if not (0 <= sample_age <= 1800):
            return result("unavailable", "CHRONY REFERENCE IS STALE",
                          errorCode="TRACKING_STALE")
        system_seconds = float(offset.group(1))
        if offset.group(2) == "slow":
            system_seconds = -system_seconds
        bound = dispersion + abs(delay) / 2
        if (not all(math.isfinite(v) for v in
                    (system_seconds, bound, delay, dispersion))
                or bound < 0 or dispersion < 0 or abs(system_seconds) > 86400):
            raise ValueError("invalid clock sample")
    except (KeyError, ValueError, OverflowError):
        return result("unavailable", "CHRONY TRACKING UNVERIFIABLE",
                      errorCode="TRACKING_INVALID")
    return result("measured", "RECENT CHRONY TRACKING ESTIMATE // READ ONLY",
                  offsetMs=int(round(system_seconds * 1000)),
                  uncertaintyMs=int(math.ceil(bound * 1000)),
                  source="CHRONY_TRACKING")


def measure_clock():
    """Explicit reference check; never changes the system clock.

    With an active daemon read its latest bounded, recent tracking estimate
    (no new network request). With a stopped daemon use chronyd -Q to
    retrieve a fresh reference measurement (configured sources see the IP).
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
            if not os.path.isfile(CHRONYC):
                return result("unavailable", "CHRONY CONTROL CLIENT MISSING",
                              errorCode="NO_CHRONYC")
            tracking = subprocess.run(
                [CHRONYC, "tracking"], capture_output=True, text=True,
                timeout=TIMEOUT, check=False,
                env={**os.environ, "LC_ALL": "C"})
            if tracking.returncode:
                return result("unavailable", "CHRONY CONTROL SOCKET UNAVAILABLE",
                              errorCode="TRACKING_SOCKET")
            return parse_tracking_measurement(tracking.stdout)
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
        r"System clock wrong by\s+([+-]?\d+(?:\.\d+)?)\s+seconds", combined)
    if not matched:
        return result("unavailable", "NO TRUSTED OFFSET MEASUREMENT RETURNED",
                      errorCode="REFERENCE_NO_SAMPLE")
    try:
        seconds = float(matched.group(1))
        if not (-86400 <= seconds <= 86400):
            raise ValueError("invalid offset")
    except ValueError:
        return result("unavailable", "REFERENCE OFFSET OUT OF RANGE",
                      errorCode="REFERENCE_INVALID")
    return result("measured", "REFERENCE OFFSET MEASURED // NO CLOCK CHANGE",
                  offsetMs=int(round(seconds * 1000)),
                  uncertaintyMs=0, source="CHRONYD_ONESHOT",
                  note="CHRONY -Q READ ONLY; REFERENCE SOURCE CONTACTED")


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
