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
import select
import selectors
import time

PR_SET_PDEATHSIG = 1
FAILED = 125
# Development transport limits; do not reinterpret as installed policy.
MAX_FRAME = 16384  # includes newline, matches canonical Python encoder
READ_CHUNK = 4096
MAX_SESSION_BYTES = 16 * 1024 * 1024
MAX_WINDOW_BYTES = 256 * 1024
PARTIAL_SECONDS = 3
WRITE_SECONDS = 3
EXIT_DRAIN_SECONDS = 2


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
    return supervise(checked_path(owner), [generation], checkpoint=False)


def checkpoint(helper, operation, directory):
    if operation not in {"GEN_LOAD", "GEN_SAVE", "GEN_ADVANCE"}:
        raise ValueError("checkpoint operation")
    root = Path(directory)
    if not root.is_absolute() or str(root) != directory or root.resolve(strict=True) != root:
        raise ValueError("checkpoint directory path")
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("private checkpoint directory required")
    return supervise(checked_path(helper), [operation, directory], checkpoint=True)


def forward_frame(frame):
    # Parent output is nonblocking: backpressure cannot retain arbitrary
    # messages or silently release custody. Never forward a partial frame
    # from the child; a downstream broken pipe is terminal.
    deadline = time.monotonic() + WRITE_SECONDS
    view = memoryview(frame)
    while view:
        left = deadline - time.monotonic()
        if left <= 0 or not select.select([], [1], [], left)[1]:
            raise RuntimeError("output blocked")
        try:
            count = os.write(1, view)
        except BlockingIOError:
            continue
        if count <= 0:
            raise RuntimeError("output unavailable")
        view = view[count:]


def relay_output(stdout_fd, stderr_fd, pidfd, *, checkpoint):
    """Bound raw child output before Qt's SplitParser sees any bytes.

    At most one partial frame plus a fixed read chunk is held. Only
    newline-terminated printable ASCII records pass; semantic validation
    still belongs to the canonical host/adapter. No child stderr is relayed.
    """
    frame = bytearray()
    total = 0
    window_bytes = 0
    window = time.monotonic()
    partial = None
    retired = None
    frames = 0
    before = os.get_blocking(1)
    os.set_blocking(1, False)
    try:
        with selectors.DefaultSelector() as sel:
            for fd, name in ((stdout_fd,"stdout"),(stderr_fd,"stderr"),(pidfd,"exit")):
                if name != "exit":
                    os.set_blocking(fd, False)
                sel.register(fd, selectors.EVENT_READ, name)
            open_streams = 2
            while open_streams:
                now = time.monotonic()
                deadlines = [d for d in (partial, retired) if d is not None]
                if deadlines and min(deadlines) <= now:
                    raise RuntimeError("output deadline")
                ready = sel.select(min(deadlines)-now if deadlines else None)
                # Reject stderr and witness child exit before processing
                # stdout from the same poll cycle.
                for key, _ in sorted(ready, key=lambda item: {"stderr":0,"exit":1,"stdout":2}[item[0].data]):
                    if key.data == "exit":
                        sel.unregister(key.fd)
                        retired = time.monotonic() + EXIT_DRAIN_SECONDS
                        continue
                    try:
                        chunk = os.read(key.fd, READ_CHUNK)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        sel.unregister(key.fd)
                        open_streams -= 1
                        if key.data == "stdout" and frame:
                            raise RuntimeError("unterminated output")
                        continue
                    if key.data == "stderr":
                        raise RuntimeError("child stderr")
                    now = time.monotonic()
                    if partial is not None and now >= partial:
                        raise RuntimeError("partial output deadline")
                    if retired is not None and now >= retired:
                        raise RuntimeError("exit drain deadline")
                    total += len(chunk)
                    if now - window >= 1:
                        window = now
                        window_bytes = 0
                    window_bytes += len(chunk)
                    if total > MAX_SESSION_BYTES or window_bytes > MAX_WINDOW_BYTES:
                        raise RuntimeError("output budget")
                    # Reject non-ASCII/control bytes, including CR, prior
                    # to any forwarding of this chunk. LF is the only delimiter.
                    if any(b != 10 and not 32 <= b <= 126 for b in chunk):
                        raise RuntimeError("invalid output bytes")
                    for piece_index, piece in enumerate(chunk.split(b"\n")):
                        if piece_index:
                            if not frame:
                                raise RuntimeError("empty output")
                            frames += 1
                            if checkpoint and frames != 1:
                                raise RuntimeError("multiple checkpoint replies")
                            forward_frame(bytes(frame) + b"\n")
                            frame.clear()
                            partial = None
                        if piece:
                            if partial is None:
                                partial = time.monotonic() + PARTIAL_SECONDS
                            if len(frame) + len(piece) >= MAX_FRAME:
                                raise RuntimeError("oversized output")
                            frame.extend(piece)
            if checkpoint and frames != 1:
                raise RuntimeError("missing checkpoint reply")
    finally:
        os.set_blocking(1, before)


def supervise(script, arguments, *, checkpoint):
    python = checked_path(sys.executable, interpreter=True)
    # Isolated Python permits sibling imports only from the checked helper
    # directory; never from ambient PYTHONPATH or the working directory.
    if checkpoint:
        boot = ("import os,runpy,sys; p=sys.argv.pop(1); sys.argv[0]=p; "
                "sys.path.insert(0,os.path.dirname(p)); runpy.run_path(p,run_name='__main__')")
        argv = [python, "-I", "-B", "-c", boot, script, *arguments]
    else:
        argv = [python, "-I", "-B", script, *arguments]
    # Do not inherit loader injection, PYTHONPATH, user site or arbitrary
    # process configuration. The existing disposable test guard is the
    # only forwarded application variable; no installed provider selected.
    env = {"PATH": "/usr/bin", "LANG": "C.UTF-8"}
    if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE") == "CI_DISPOSABLE_ONLY":
        env["POST_APOLLO_QUEUE_PIPE_SMOKE"] = "CI_DISPOSABLE_ONLY"
    arm_parent_death(os.getppid())
    supervisor = os.getpid()
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    stdout_fd, child_stdout = os.pipe2(os.O_CLOEXEC)
    stderr_fd, child_stderr = os.pipe2(os.O_CLOEXEC)
    pid = os.fork()
    if pid == 0:
        try:
            os.close(write_fd)
            os.close(stdout_fd)
            os.close(stderr_fd)
            os.dup2(child_stdout, 1)
            os.dup2(child_stderr, 2)
            os.close(child_stdout)
            os.close(child_stderr)
            arm_parent_death(supervisor)
            if os.read(read_fd, 1) != b"1":
                os._exit(FAILED)
            os.close(read_fd)
            os.execve(python, argv, env)
        except BaseException:
            os._exit(FAILED)
    os.close(read_fd)
    os.close(child_stdout)
    os.close(child_stderr)
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
        relay_output(stdout_fd, stderr_fd, pidfd, checkpoint=checkpoint)
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
        os.close(stdout_fd)
        os.close(stderr_fd)


def main():
    try:
        if len(sys.argv) == 5 and sys.argv[1] == "--checkpoint":
            return checkpoint(*sys.argv[2:])
        if len(sys.argv) != 3:
            raise ValueError("arguments")
        return run(sys.argv[1], sys.argv[2])
    except (OSError, RuntimeError, ValueError, AttributeError):
        print("QUEUE_CUSTODY_UNAVAILABLE", file=sys.stderr)
        return FAILED


if __name__ == "__main__":
    raise SystemExit(main())
