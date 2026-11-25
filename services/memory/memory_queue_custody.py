"""Linux direct-child custody for the unmounted recovery-only session.

Trusted shell selects the owner script; this is not an authorization boundary.
No protected memory operation, retry, detached process or arbitrary shell.
"""
import ctypes
import os
from pathlib import Path
import signal
import stat
import sys

PR_SET_PDEATHSIG = 1
FAILED = 125


def arm_parent_death(parent):
    if parent <= 1 or os.getppid() != parent:
        raise RuntimeError("parent unavailable")
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "prctl")
    if os.getppid() != parent:
        raise RuntimeError("parent changed")


def checked_path(value, *, interpreter=False):
    path = Path(value)
    if not path.is_absolute() or str(path) != value:
        raise ValueError("absolute normalized path required")
    real = path.resolve(strict=True)
    if not interpreter and real != path:
        raise ValueError("owner symlink refused")
    uid = os.getuid()
    for item in (real, *real.parents):
        s = item.stat()
        if s.st_uid not in (0, uid):
            raise ValueError("foreign path owner")
        # Permit only the standard root-owned sticky /tmp ancestor for
        # disposable/private roots. All other writable ancestors refused.
        if s.st_mode & 0o022 and not (item == Path("/tmp") and s.st_uid == 0
                and stat.S_ISDIR(s.st_mode) and s.st_mode & stat.S_ISVTX):
            raise ValueError("shared writable path")
    s = real.stat()
    if not stat.S_ISREG(s.st_mode):
        raise ValueError("regular file required")
    if interpreter and (s.st_uid != 0 or not s.st_mode & 0o111):
        raise ValueError("system interpreter required")
    return str(real)


def run(owner, generation):
    if not generation.isascii() or not generation.isdecimal() or str(int(generation)) != generation or not 1 <= int(generation) <= 2147483646:
        raise ValueError("generation")
    script = checked_path(owner)
    python = checked_path(sys.executable, interpreter=True)
    # Do not inherit loader injection, PYTHONPATH, user site or arbitrary
    # process configuration. The existing disposable test guard is the
    # only forwarded application variable; no installed provider selected.
    env = {"PATH": "/usr/bin", "LANG": "C.UTF-8"}
    if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE") == "CI_DISPOSABLE_ONLY":
        env["POST_APOLLO_QUEUE_PIPE_SMOKE"] = "CI_DISPOSABLE_ONLY"
    arm_parent_death(os.getppid())
    supervisor = os.getpid()
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    pid = os.fork()
    if pid == 0:
        try:
            os.close(write_fd)
            arm_parent_death(supervisor)
            if os.read(read_fd, 1) != b"1":
                os._exit(FAILED)
            os.close(read_fd)
            os.execve(python, [python, "-I", "-B", script, generation], env)
        except BaseException:
            os._exit(FAILED)
    os.close(read_fd)
    pidfd = None
    reaped = False
    try:
        # Child cannot execute the script before the exact kernel handle
        # is acquired. A pidfd remains bound even if the numeric PID recycles.
        pidfd = os.pidfd_open(pid, 0)
        if os.write(write_fd, b"1") != 1:
            raise RuntimeError("child gate")
        os.close(write_fd)
        write_fd = None
        witness = os.waitid(os.P_PIDFD, pidfd, os.WEXITED | os.WNOWAIT)
        waited, status = os.waitpid(pid, 0)
        reaped = True
        if (witness.si_pid != pid or waited != pid or witness.si_code != os.CLD_EXITED
                or witness.si_status != 0 or not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0):
            return FAILED
        return 0
    finally:
        if write_fd is not None:
            os.close(write_fd)
        if not reaped:
            # Own unreaped child only, never a name/PID search. Do not
            # permit a failed custody setup to report a clean retirement.
            try:
                if pidfd is None:
                    os.kill(pid, signal.SIGKILL)
                else:
                    signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        if pidfd is not None:
            os.close(pidfd)


def main():
    try:
        if len(sys.argv) != 3:
            raise ValueError("arguments")
        return run(sys.argv[1], sys.argv[2])
    except (OSError, RuntimeError, ValueError, AttributeError):
        print("QUEUE_CUSTODY_UNAVAILABLE", file=sys.stderr)
        return FAILED


if __name__ == "__main__":
    raise SystemExit(main())
