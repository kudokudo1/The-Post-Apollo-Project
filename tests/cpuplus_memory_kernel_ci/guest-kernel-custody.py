#!/usr/bin/python3 -I
"""Native util-linux custody at syscall entry; disposable CI guest only."""
import ctypes
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import stat
import struct
import time

RECOVERY = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
MARKER = Path("/etc/postapollo-memory-native-kernel-ci-only")
LOCK = Path("/run/post-apollo-memory.lock")
SWAPOFF = Path("/usr/sbin/swapoff")
TRACEME, CONT, SYSCALL = 0, 7, 24
SETOPTIONS, GETEVENTMSG, GET_SYSCALL_INFO = 0x4200, 0x4201, 0x420e
FORK, VFORK, CLONE, EXEC = 1, 2, 3, 4
TRACE_OPTIONS = 1 | 2 | 4 | 8 | 16
WALL = 0x40000000
AUDIT_ARCH_X86_64 = 0xc000003e
SYS_SWAPOFF = 168
libc = ctypes.CDLL(None, use_errno=True)
libc.ptrace.restype = ctypes.c_long
libc.ptrace.argtypes = (ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def stage(message):
    print("CPU_MEM_KERNEL_STAGE // " + message, flush=True)

def guard_guest():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    loader = importlib.machinery.SourceFileLoader("kernel_fixture_guard", str(RECOVERY))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    guard = importlib.util.module_from_spec(spec)
    loader.exec_module(guard)
    guard.guard()
    require(guard.protected_bytes(MARKER).strip() == b"DISPOSABLE_CPU_MEMORY_KERNEL_V1",
            "kernel fixture marker absent")
    require(platform.machine() == "x86_64", "unsupported syscall architecture")
    return guard

def ptrace(request, pid, address=0, data=0):
    def pointer(value):
        return ctypes.c_void_p(value) if isinstance(value, int) else ctypes.cast(value, ctypes.c_void_p)
    ctypes.set_errno(0)
    result = libc.ptrace(request, pid, pointer(address), pointer(data))
    if result == -1 and ctypes.get_errno():
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result

def decode_swapoff_entry(raw, length):
    # struct ptrace_syscall_info: op at 0, audit arch at 4, syscall
    # number at 24 for ENTRY (not EXIT or SECCOMP). x86-64 only.
    require(type(length) is int and 1 <= length <= len(raw), "invalid syscall info length")
    if raw[0] != 1:
        return False
    require(length >= 32, "truncated syscall entry")
    arch = struct.unpack_from("<I", raw, 4)[0]
    require(arch == AUDIT_ARCH_X86_64, "unexpected trace architecture")
    return struct.unpack_from("<Q", raw, 24)[0] == SYS_SWAPOFF

def wait_event(deadline):
    while time.monotonic() < deadline:
        pid, status = os.waitpid(-1, os.WNOHANG | WALL)
        if pid:
            return pid, status
        time.sleep(0.01)
    raise RuntimeError("trace boundary deadline")

def same_executable(pid, target):
    # Compare inode, not a guessed process name or argv.
    observed = os.stat("/proc/" + str(pid) + "/exe")
    expected = target.stat()
    return (observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino)

def inherited_lock_fds(pid):
    lock = LOCK.lstat()
    require(stat.S_ISREG(lock.st_mode) and lock.st_uid == 0
            and not lock.st_mode & 0o077 and lock.st_nlink == 1, "untrusted lock inode")
    result = []
    for path in Path("/proc/" + str(pid) + "/fd").iterdir():
        try:
            info = path.stat()
        except FileNotFoundError:
            continue
        if (info.st_dev, info.st_ino) == (lock.st_dev, lock.st_ino):
            result.append(path.name)
    return result

def signature(guard):
    return {path: (kind, size, priority)
            for path, (kind, size, used, priority) in guard.rows().items()}

def no_records(guard):
    return not any(os.path.lexists(guard.EXT / name)
                   for name in guard.RECORD_NAMES) and not os.path.lexists(guard.PENDING)

def trace_to_entry(guard):
    # Execute the original pinned helper unchanged; no monkeypatched run(),
    # synthetic proc records, command substitution or mocked kernel calls.
    root = os.fork()
    if root == 0:
        try:
            ptrace(TRACEME, 0)
            os.kill(os.getpid(), signal.SIGSTOP)
            os.execve(str(guard.HELPER), [str(guard.HELPER), "withdraw-authorized", "4"],
                      {"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"})
        except BaseException:
            os._exit(125)
    live = {root}
    newborn = set()
    swap = None
    deadline = time.monotonic() + 45
    pid, status = wait_event(deadline)
    require(pid == root and os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP,
            "initial trace stop not observed")
    ptrace(SETOPTIONS, root, 0, TRACE_OPTIONS)
    ptrace(CONT, root)
    while True:
        pid, status = wait_event(deadline)
        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
            live.discard(pid)
            require(pid != root and pid != swap, "helper or swapoff exited before boundary")
            continue
        require(os.WIFSTOPPED(status), "unexpected trace event")
        sig = os.WSTOPSIG(status)
        event = status >> 16
        if event in (FORK, VFORK, CLONE):
            require(pid in live, "fork event from unknown tracee")
            child = ctypes.c_ulong()
            ptrace(GETEVENTMSG, pid, 0, ctypes.byref(child))
            require(child.value > 0 and child.value not in live, "invalid fork identity")
            live.add(child.value)
            newborn.add(child.value)
            ptrace(SYSCALL if pid == swap else CONT, pid)
            continue
        # Linux may report a newly traced child's stop before the parent's
        # fork notification. Fail closed instead of guessing ancestry.
        require(pid in live, "unknown tracee stop")
        if sig == signal.SIGSTOP and pid in newborn and event == 0:
            newborn.remove(pid)
            ptrace(SETOPTIONS, pid, 0, TRACE_OPTIONS)
            ptrace(CONT, pid)
            continue
        if event == EXEC:
            require(sig == signal.SIGTRAP, "unexpected exec stop")
            if pid != root and same_executable(pid, SWAPOFF):
                require(swap is None, "duplicate swapoff process")
                swap = pid
                stage("REAL_UTIL_LINUX_EXEC_OBSERVED")
            ptrace(SYSCALL if pid == swap else CONT, pid)
            continue
        if sig == (signal.SIGTRAP | 0x80) and pid == swap and event == 0:
            raw = ctypes.create_string_buffer(128)
            length = ptrace(GET_SYSCALL_INFO, pid, len(raw), raw)
            if decode_swapoff_entry(raw.raw, length):
                require(live == {root, swap}, "unexpected live tracees at effect boundary")
                require(same_executable(swap, SWAPOFF), "swapoff executable changed")
                stage("REAL_SWAPOFF_SYSCALL_ENTRY_STOPPED")
                return root, swap
            ptrace(SYSCALL, pid)
            continue
        if sig == signal.SIGCHLD and event == 0 and pid != swap:
            ptrace(CONT, pid, 0, sig)
            continue
        raise RuntimeError("unexpected trace stop; native evidence unavailable")

def expect_busy(guard):
    # Ordinary helper lock acquisition is nonblocking and precedes persistence.
    result = guard.helper("persist-authorized")
    require(result.returncode == 2, "child did not retain exclusive operation lock")
    prefix = "REDUCTION BLOCKED: "
    lines = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
    require(len(lines) == 1 and json.loads(lines[0][len(prefix):])["code"] == "OPERATION_BUSY",
            "wrong contention result")

def run():
    guard = guard_guest()
    guard.verify_swap(True)
    require(no_records(guard), "requires unfenced active extension")
    original = signature(guard)
    identities = [guard.identity(guard.BASE), guard.identity(guard.EXTRA)]
    history = guard.history()
    require(len(history) == 2, "two normal cycles required")
    ready = guard.helper("reduction-preflight", "4")
    require(ready.returncode == 0 and json.loads(ready.stdout)["state"] == "READY_ADVISORY",
            "native preflight not ready")
    root, swap = trace_to_entry(guard)
    intent_path, result_path = (guard.EXT / name for name in guard.RECORD_NAMES[:2])
    intent = guard.protected_bytes(intent_path)
    require(json.loads(intent)["state"] == "PREPARED" and not os.path.lexists(result_path)
            and signature(guard) == original, "effect boundary not prepared")
    require(inherited_lock_fds(swap), "real util-linux did not preserve lock descriptor")
    # Actual syscall entry is stopped BEFORE kernel effect. Kill only the
    # exact traced helper parent; child remains stopped under our custody.
    os.kill(root, signal.SIGKILL)
    pid, status = wait_event(time.monotonic() + 10)
    require(pid == root and os.WIFSIGNALED(status)
            and os.WTERMSIG(status) == signal.SIGKILL, "helper death not confirmed")
    require(same_executable(swap, SWAPOFF) and inherited_lock_fds(swap),
            "child custody lost on parent death")
    expect_busy(guard)
    require(signature(guard) == original and guard.protected_bytes(intent_path) == intent
            and not os.path.lexists(result_path), "contention changed state")
    print("CPU_MEM_KERNEL_PASS // ACTUAL_UTIL_LINUX_LOCK_AFTER_PARENT_SIGKILL", flush=True)
    # Allow the already admitted original child to finish its actual syscall;
    # no retry, replacement or additional swapoff invocation.
    ptrace(CONT, swap)
    pid, status = wait_event(time.monotonic() + 30)
    require(pid == swap and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0,
            "original swapoff child did not exit successfully")
    guard.verify_swap(False)
    expected = dict(original)
    expected.pop(str(guard.EXTRA))
    require(signature(guard) == expected
            and [guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == identities
            and guard.history() == history and guard.protected_bytes(intent_path) == intent
            and not os.path.lexists(result_path), "unexpected post-child evidence")
    guard.fence()
    observed = guard.success("inspect-recovery-authorized", prefix="RECOVERY INSPECTION: ")
    require(observed["code"] == "INTENT_ONLY_INACTIVE" and observed["mutationAllowed"] is False
            and observed["recordCleared"] is False, "unknown result was upgraded")
    print("CPU_MEM_KERNEL_PASS // ORIGINAL_CHILD_COMPLETED_UNKNOWN_RESULT_FENCED", flush=True)
    # No replay, reactivation, recovery clearance or forced cleanup. The
    # disposable VM is destroyed by its host after evidence collection.

if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print("CPU_MEM_KERNEL_FAIL // " + type(error).__name__ + ": " + str(error), flush=True)
        # No retry or generic process kill. A failed fixture's VM is disposable.
        raise SystemExit(2)
