#!/usr/bin/python3 -I
"""CI-only Silverblue guest recovery fault fixture; not a workstation tool."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys

HELPER = Path("/usr/local/libexec/postapollo-memory-ci-helper")
PIN = "eec7a83cc9068303c3fbc6f4ae9c98e78f7b67ad"
MARKER = Path("/etc/postapollo-memory-ci-only")
FAULT_MARKER = Path("/etc/postapollo-memory-native-fault-ci-only")
BASE = Path("/var/lib/post-apollo-memory-swap/swapfile")
EXT = Path("/var/lib/post-apollo-memory-extension")
EXTRA = EXT / "swapfile"
HISTORY = Path("/var/lib/post-apollo-memory-history")
WITNESS = Path("/var/lib/postapollo-memory-native-fault-witness.json")
UNIT = r"var-lib-post\x2dapollo\x2dmemory\x2dswap-swapfile.swap"
RECORD_NAMES = ("withdrawal.json", "withdrawal-result.json",
                "reactivation.json", "reactivation-result.json")
PENDING = EXT / "archive-pending.json"
GIB = 1024 ** 3

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def command(*argv):
    return subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, cwd="/").stdout

def protected_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o077 and info.st_nlink == 1
                and 0 < info.st_size <= 262144, "untrusted fixture record")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(262145)
        require(len(raw) == info.st_size, "fixture record changed")
        return raw
    finally:
        os.close(fd)

def guard():
    # The VM and its second dedicated marker are mandatory. Never install
    # either marker or run this script on the operator workstation.
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    require(protected_bytes(MARKER).strip() == b"DISPOSABLE_CPU_MEMORY_NATIVE_V1",
            "normal fixture marker absent")
    require(protected_bytes(FAULT_MARKER).strip() == b"DISPOSABLE_CPU_MEMORY_FAULT_V1",
            "fault fixture marker absent")
    require(command("/usr/bin/systemd-detect-virt", "--vm").strip() in ("kvm", "qemu"),
            "not an isolated VM")
    require(command("/usr/sbin/getenforce").strip() == "Enforcing",
            "SELinux is not enforcing")
    require(command("/usr/bin/findmnt", "-n", "-o", "FSTYPE", "-T", "/var/lib").strip() == "btrfs",
            "not Btrfs")
    source = protected_bytes(HELPER)
    digest = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(digest == PIN, "reviewed helper blob mismatch")

def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()

def rows():
    result = {}
    for line in Path("/proc/swaps").read_text().splitlines()[1:]:
        path, kind, size, used, priority = line.split()
        require(path not in result, "duplicate swap row")
        result[path] = (kind, int(size), int(used), int(priority))
    return result

def identity(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0
            and not info.st_mode & 0o077 and info.st_nlink == 1, "unexpected swap file identity")
    return [info.st_dev, info.st_ino, info.st_size]

def verify_swap(active):
    current = rows()
    for path, priority in ((BASE, 10), (EXTRA, 9)):
        if path == EXTRA and not active:
            require(str(path) not in current, "extension remains active")
        else:
            require(str(path) in current, "required active swap absent")
            kind, size, used, actual = current[str(path)]
            require(kind == "file" and actual == priority and 0 <= 4 * GIB // 1024 - size <= 1024,
                    "swap capacity or priority mismatch")
        require(identity(path)[2] == 4 * GIB, "retained file size mismatch")
    require(command("/usr/bin/systemctl", "is-enabled", UNIT).strip() == "enabled",
            "persistent base unit not enabled")

def digest_file(path):
    return hashlib.sha256(protected_bytes(path)).hexdigest()

def history():
    result = {}
    for path in sorted(HISTORY.glob("cycle-*.json")):
        raw = protected_bytes(path)
        bundle = json.loads(raw)
        digest = hashlib.sha256(json.dumps(bundle["records"], sort_keys=True,
                 separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
        require(bundle["state"] == "VERIFIED_ACTIVE_CYCLE" and len(bundle["records"]) == 4
                and bundle["digest"] == digest and path.name == "cycle-" + digest + ".json",
                "archive invalid")
        result[path.name] = hashlib.sha256(raw).hexdigest()
    return result

def helper(*args):
    return subprocess.run([str(HELPER), *args], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, cwd="/")

def success(*args, prefix):
    result = helper(*args)
    require(result.returncode == 0, "helper failed: " + args[0])
    lines = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
    require(len(lines) == 1, "receipt missing: " + args[0])
    return json.loads(lines[0][len(prefix):])

def fence():
    # Already-enabled persist is used as a harmless contention probe:
    # no swapon or swapoff is requested by this probe.
    result = helper("persist-authorized")
    require(result.returncode == 3, "ordinary mutation not fenced")
    require("RECOVERY_REQUIRED" in result.stdout, "unexpected recovery refusal")

def withdraw():
    ready = helper("reduction-preflight", "4")
    require(ready.returncode == 0 and json.loads(ready.stdout)["state"] == "READY_ADVISORY",
            "native withdrawal preflight not ready")
    receipt = success("withdraw-authorized", "4", prefix="VERIFIED REDUCTION: ")
    require(receipt["extensionActive"] is False and receipt["fileRetained"] is True,
            "withdrawal receipt mismatch")
    verify_swap(False)

def crash_archive():
    # Import the exact reviewed helper only inside the fixture process.
    # The sole injection occurs immediately after the first journal unlink.
    # No helper logic, kernel command or journal content is substituted.
    loader = importlib.machinery.SourceFileLoader("cpu_memory_ci", str(HELPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    original_unlink = Path.unlink
    def interrupted(path, *args, **kwargs):
        original_unlink(path, *args, **kwargs)
        if path == EXT / RECORD_NAMES[0]:
            os.kill(os.getpid(), signal.SIGKILL)
    Path.unlink = interrupted
    module.archive_cycle_authorized()
    raise RuntimeError("fault injection did not terminate archive")

def prepare():
    require(not os.path.lexists(WITNESS), "fixture already prepared")
    verify_swap(True)
    previous = history()
    require(len(previous) == 2, "normal cycle evidence absent")
    require(not any(os.path.lexists(EXT / name) for name in RECORD_NAMES)
            and not os.path.lexists(PENDING), "normal cycle not retired")
    original = [identity(BASE), identity(EXTRA)]
    withdraw()
    success("reactivate-authorized", "8", prefix="VERIFIED REACTIVATION: ")
    verify_swap(True)
    originals = {name: digest_file(EXT / name) for name in RECORD_NAMES}
    child = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                            "crash-archive"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(child.returncode == -signal.SIGKILL, "archive process did not die at injected boundary")
    require(not os.path.lexists(EXT / RECORD_NAMES[0]), "first retirement did not happen")
    pending = json.loads(protected_bytes(PENDING))
    require(pending["state"] == "ARCHIVE_PENDING", "archive fence missing")
    retained = history()
    require(len(retained) == 3 and all(retained.get(k) == v for k, v in previous.items()),
            "prior archive history changed")
    for name in RECORD_NAMES[1:]:
        require(digest_file(EXT / name) == originals[name], "surviving record changed")
    verify_swap(True)
    fence()
    observation = success("inspect-recovery-authorized", prefix="RECOVERY INSPECTION: ")
    require(observation["code"] == "ARCHIVE_PENDING" and observation["mutationAllowed"] is False,
            "pending archive inspection incorrect")
    print("CPU_MEM_FAULT_PASS // REAL_SIGKILL_PARTIAL_RETIREMENT_FENCED", flush=True)
    success("archive-cycle-authorized", prefix="VERIFIED CYCLE ARCHIVE: ")
    require(history() == retained and not os.path.lexists(PENDING)
            and not any(os.path.lexists(EXT / name) for name in RECORD_NAMES),
            "archive resume failed or replayed")
    verify_swap(True)
    print("CPU_MEM_FAULT_PASS // EXPLICIT_ARCHIVE_RESUME_HISTORY_INTACT", flush=True)
    withdraw()
    fence()
    require([identity(BASE), identity(EXTRA)] == original, "managed files replaced")
    witness = {"version": 1, "bootId": boot_id(), "identity": original,
               "history": retained, "withdrawal": {name: digest_file(EXT / name)
                                                   for name in RECORD_NAMES[:2]}}
    fd = os.open(WITNESS, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(witness, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(WITNESS.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    print("CPU_MEM_FAULT_PASS // REBOOT_WITNESS_DURABLE", flush=True)
    # Host harness controls VM shutdown/reboot. This script never calls reboot.

def after_reboot():
    witness = json.loads(protected_bytes(WITNESS))
    require(witness["version"] == 1 and witness["bootId"] != boot_id(), "real reboot not observed")
    verify_swap(False)
    current = [identity(BASE), identity(EXTRA)]
    # st_dev may legitimately change across boot. Require unchanged inode
    # and file size, but never reinterpret device mismatch as permission.
    require([row[1:] for row in current] == [row[1:] for row in witness["identity"]],
            "file inode/size changed across boot")
    require(history() == witness["history"], "archived history changed across reboot")
    require(all(digest_file(EXT / name) == digest for name, digest in witness["withdrawal"].items()),
            "withdrawal journal changed across reboot")
    require(not any(os.path.lexists(EXT / name) for name in RECORD_NAMES[2:])
            and not os.path.lexists(PENDING), "unexpected recovery journal")
    fence()
    observed = success("inspect-recovery-authorized", prefix="RECOVERY INSPECTION: ")
    expected = ("RECORDED_VERIFIED_INACTIVE" if current == witness["identity"]
                else "FILE_IDENTITY_MISMATCH")
    require(observed["code"] == expected and observed["mutationAllowed"] is False
            and observed["recordCleared"] is False, "postboot recovery observation not fail-closed")
    print("CPU_MEM_FAULT_PASS // REAL_REBOOT_BASE_ACTIVE_EXTENSION_INACTIVE", flush=True)
    print("CPU_MEM_FAULT_PASS // JOURNALS_AND_HISTORY_PRESERVED_NO_REPLAY", flush=True)

def main():
    guard()
    require(len(sys.argv) == 2, "explicit fixture phase required")
    phases = {"prepare": prepare, "after-reboot": after_reboot, "crash-archive": crash_archive}
    require(sys.argv[1] in phases, "unknown fixture phase")
    phases[sys.argv[1]]()

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print("CPU_MEM_FAULT_FAIL // " + type(error).__name__ + ": " + str(error), flush=True)
        sys.exit(2)
