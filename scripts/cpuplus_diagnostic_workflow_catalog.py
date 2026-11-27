#!/usr/bin/env python3
"""Private bounded workflow configuration storage, never a launch API."""
import fcntl
import os
from pathlib import Path
import re
import sys

from cpuplus_diagnostic_archive import encode, open_private, private_fd
from cpuplus_diagnostic_workflow import decode

SCHEMA = "post-apollo-diagnostic-workflow-catalog-v1"
MAX_FILE = 65536
MAX_FRAME = 2 * MAX_FILE + 1024
MAX_ID = 2**53 - 1
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,31}")
USER = re.compile(r"user-([1-9][0-9]{0,15})")
DEFAULTS = {"default-memory": "configured", "default-inventory": "inventory",
            "default-threads": "configured", "default-census": "configured",
            "default-storage": "configured", "default-appcontrol": "appcontrol"}
ORDER = ("threads", "memory", "census", "storage", "stall",
         "hostcpu", "gpu", "diskio", "swapio", "netio")


# Only stable configured scopes; no process identity or executable metadata.
TARGET_KINDS = {
    "host-cpu": {"hostcpu"}, "host-gpu": {"gpu"}, "host-disk": {"diskio"},
    "host-swap": {"swapio"}, "host-network": {"netio"},
    "user-processes": {"census"}, "quickshell": {"threads", "memory"},
    "apollo-loop": {"stall"}, "apollo-files": {"storage"},
}


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate_plan(plan):
    # Storage boundary accepts only known instrument data and calibrated bounds.
    # The QML catalog policy still revalidates and canonicalizes on every load.
    if type(plan) is not dict or set(plan) != {"durationSeconds", "instruments"}:
        raise ValueError("plan shape")
    duration, items = plan["durationSeconds"], plan["instruments"]
    if not integer(duration, 1, 120) or type(items) is not list or not 1 <= len(items) <= 10:
        raise ValueError("plan bounds")
    seen = set()
    for item in items:
        if type(item) is not dict or type(item.get("kind")) is not str:
            raise ValueError("instrument shape")
        kind = item["kind"]
        if kind not in ORDER or kind in seen:
            raise ValueError("instrument kind")
        seen.add(kind)
        if kind == "storage":
            if duration > 30 or set(item) not in ({"kind"}, {"kind","sampleSeconds","reportSeconds"}):
                raise ValueError("storage shape")
            sample, report = item.get("sampleSeconds", 1), item.get("reportSeconds", 10)
            if (not integer(sample,1,min(5,duration)) or not integer(report,sample,30)
                    or report % sample or (duration+report-1)//report > 6):
                raise ValueError("storage cadence")
            continue
        if kind == "stall":
            if (set(item) != {"kind","thresholdMs"} or duration < 5
                    or not integer(item["thresholdMs"],150,2000) or item["thresholdMs"]%50):
                raise ValueError("stall calibration")
            continue
        keys = {"kind","intervalMs","topCount"} if kind == "threads" else {"kind","intervalMs"}
        if set(item) != keys or not integer(item["intervalMs"],100,min(60000,duration*1000)):
            raise ValueError("interval shape")
        ms = item["intervalMs"]
        n = (duration*1000+ms-1)//ms
        if kind == "threads":
            top = item["topCount"]
            if ms not in (100,250,500,1000,2000,5000) or not integer(top,1,12) or n>30 or n*(top+1)>150:
                raise ValueError("thread calibration")
        elif kind == "memory":
            if ms<5000 or ms%1000 or n>12:
                raise ValueError("memory calibration")
        elif kind == "census":
            if duration>60 or ms%1000 or n>3:
                raise ValueError("census calibration")
        elif duration>30 or ms<1000 or ms>5000 or ms%1000 or n>12:
            raise ValueError("hardware calibration")


def validate(document):
    if (type(document) is not dict or set(document) != {"schema","nextId","rows"}
            or document["schema"] != SCHEMA or not integer(document["nextId"],1,MAX_ID)
            or type(document["rows"]) is not list or len(document["rows"])>64):
        raise ValueError("catalog shape")
    ids, names = set(), set()
    for row in document["rows"]:
        if type(row) is not dict or row.get("execution") not in ("fixed","configured"):
            raise ValueError("row shape")
        fixed = row["execution"] == "fixed"
        fields = {"id","name","favorite","execution", "kind" if fixed else "plan"}
        explicit = not fixed and "targetId" in row
        if explicit:
            fields.add("targetId")
        if set(row) != fields:
            raise ValueError("row fields")
        ident, name = row["id"], row["name"]
        if (type(ident) is not str or type(name) is not str or not NAME.fullmatch(name)
                or name.strip()!=name or type(row["favorite"]) is not bool):
            raise ValueError("row values")
        match = USER.fullmatch(ident)
        seed = DEFAULTS.get(ident)
        if not seed and (not match or int(match[1]) >= document["nextId"]):
            raise ValueError("unallocated id")
        if ident in ids or name.lower() in names:
            raise ValueError("duplicate id or name")
        ids.add(ident)
        names.add(name.lower())
        if fixed:
            if seed not in ("inventory","appcontrol") or row["kind"] != seed:
                raise ValueError("fixed route")
        else:
            if seed in ("inventory","appcontrol"):
                raise ValueError("fixed identity")
            validate_plan(row["plan"])
            if explicit:
                target = row["targetId"]
                if (type(target) is not str or target not in TARGET_KINDS
                        or any(c["kind"] not in TARGET_KINDS[target] for c in row["plan"]["instruments"])):
                    raise ValueError("target scope")
    if len(encode(document)) > MAX_FILE:
        raise ValueError("catalog size")
    return document


def read_catalog(directory):
    try:
        fd = open_private(directory, "workflows.json", os.O_RDONLY)
    except FileNotFoundError:
        return None
    with os.fdopen(fd,"rb") as handle:
        raw = handle.read(MAX_FILE+1)
    if len(raw)>MAX_FILE:
        raise ValueError("catalog size")
    return validate(decode(raw))


def commit(directory, document):
    raw = encode(validate(document))
    name = ".workflows.pending"
    try:
        stale = open_private(directory,name,os.O_RDONLY)
    except FileNotFoundError:
        pass
    else:
        os.close(stale)
        os.unlink(name,dir_fd=directory)
    fd = open_private(directory,name,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
    try:
        with os.fdopen(fd,"wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name,"workflows.json",src_dir_fd=directory,dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(name,dir_fd=directory)
        except FileNotFoundError:
            pass


def execute(folder, request):
    if type(request) is not dict:
        raise ValueError("request")
    action = request.get("action")
    if action == "load" and set(request)=={"action"}:
        saving = False
    elif action == "save" and set(request)=={"action","expected","document"}:
        saving = True
        document = validate(request["document"])
        expected = request["expected"]
        if expected is not None:
            validate(expected)
    else:
        raise ValueError("unsupported request")
    folder = Path(folder)
    if saving:
        folder.parent.mkdir(parents=True,exist_ok=True)
        folder.mkdir(mode=0o700,exist_ok=True)
    try:
        directory = os.open(folder,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    except FileNotFoundError:
        if not saving:
            return {"status":"MISSING","document":None}
        raise
    try:
        private_fd(directory,directory=True)
        # Separate lock/file from the diagnostic report archive.
        lock = open_private(directory,"workflows.lock",os.O_RDWR|os.O_CREAT)
        try:
            fcntl.flock(lock,fcntl.LOCK_EX)
            current = read_catalog(directory)
            if not saving:
                return {"status":"MISSING" if current is None else "LOADED","document":current}
            if current != expected:
                return {"status":"CONFLICT","document":current}
            if current is not None and document["nextId"] < current["nextId"]:
                raise ValueError("identity counter regression")
            if current != document:
                commit(directory,document)
            return {"status":"SAVED","document":document}
        finally:
            os.close(lock)
    finally:
        os.close(directory)


def state_folder():
    configured = os.environ.get("XDG_STATE_HOME")
    parent = Path(configured) if configured and Path(configured).is_absolute() else Path.home()/".local/state"
    return parent/"post-apollo-cpuplus-workflows"


def main():
    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.readline(MAX_FRAME+1)
        if len(raw)>MAX_FRAME or not raw.endswith(b"\n"):
            raise ValueError("frame")
        result = execute(state_folder(),decode(raw))
        sys.stdout.buffer.write(encode(result)+b"\n")
        return 0
    except (OSError,ValueError,TypeError,RecursionError):
        print("Diagnostic workflow catalog unavailable.",file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
